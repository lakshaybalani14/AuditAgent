"""Vercel serverless inference endpoint for the saved 7-feature scheduler policy.

The small JSON export is the same trained DQN used by the local project. This
runner evaluates its MLP directly, avoiding training, PyTorch, and writable
server disk at deployment time.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_DIR = ROOT / "simulator"
sys.path.insert(0, str(SIMULATOR_DIR))

from simulator_core import SimulatorCore  # noqa: E402

POLICY_PATH = ROOT / "rl_agent" / "policy.json"
ACTION_NAMES = {
    0: "no change",
    1: "switch to Round Robin",
    2: "switch to Priority Scheduling",
    3: "switch to Multilevel Feedback Queue",
    4: "boost priority of the longest-waiting process",
}
OBSERVATION_NAMES = (
    "queue_length",
    "avg_wait_time",
    "max_wait_time",
    "num_io_bound",
    "num_cpu_bound",
    "current_algo",
    "is_starving",
)
MAX_DECISIONS = 50


def load_policy():
    with POLICY_PATH.open("r", encoding="utf-8") as file:
        policy = json.load(file)
    layers = policy.get("layers", [])
    if len(layers) != 3:
        raise ValueError("Expected a three-layer exported DQN policy.")
    if len(layers[0].get("weights", [])) != 64 or len(layers[-1].get("weights", [])) != 5:
        raise ValueError("The exported policy has an unexpected network shape.")
    return layers


def predict_q_values(layers, observation):
    values = [float(value) for value in observation]
    for layer_index, layer in enumerate(layers):
        weights = layer["weights"]
        biases = layer["biases"]
        if len(weights) != len(biases):
            raise ValueError("Policy weights and biases do not match.")
        next_values = []
        for row, bias in zip(weights, biases):
            if len(row) != len(values):
                raise ValueError("Policy input shape does not match the observation.")
            result = sum(float(weight) * value for weight, value in zip(row, values)) + float(bias)
            if layer_index < len(layers) - 1:
                result = max(0.0, result)
            next_values.append(result)
        values = next_values
    return values


def snapshot_processes(sim):
    levels = {
        id(process): level
        for level, queue in enumerate(sim.mlfq_queues)
        for process in queue
    }
    wakeups = {
        id(process): wake_time
        for wake_time, _sequence, process, _level in sim.blocked
    }
    return [
        {
            "pid": str(process.pid),
            "state": process.state,
            "arrival_time": process.arrival_time,
            "burst_time": process.burst_time,
            "remaining_time": process.remaining_time,
            "priority": process.priority,
            "waiting_time": process.waiting_time,
            "response_time": process.response_time,
            "turnaround_time": process.turnaround_time,
            "cpu_execution_time": process.cpu_execution_time,
            "io_time": process.io_time,
            "is_io_bound": process.is_io_bound,
            "queue_level": levels.get(id(process)),
            "io_wakeup_time": wakeups.get(id(process)),
        }
        for process in sim.processes
    ]


def local_explanation(state, action):
    name = ACTION_NAMES[action]
    if state["is_starving"]:
        return (
            f"The longest wait is {state['max_wait_time']:.1f} ticks, "
            f"so {name} is considered with starvation prevention in mind."
        )
    return (
        f"With {state['queue_length']} queued processes and an average wait "
        f"of {state['avg_wait_time']:.1f} ticks, the trained policy chose {name}."
    )


def run_simulation(seed=42, count=15):
    layers = load_policy()
    sim = SimulatorCore(max_processes=10, seed=seed)
    decisions = []
    episode = 1
    step = 0
    total_waiting_time = 0

    while len(decisions) < count:
        if sim.is_episode_done():
            episode += 1
            sim.reset(seed=seed + episode - 1)
            step = 0

        state = sim.get_state_summary()
        inputs = [
            float(state["queue_length"]),
            float(state["avg_wait_time"]),
            float(state["max_wait_time"]),
            float(state["num_io_bound"]),
            float(state["num_cpu_bound"]),
            float(state["current_algo"]),
            1.0 if state["is_starving"] else 0.0,
        ]
        q_values = predict_q_values(layers, inputs)
        action = max(range(len(q_values)), key=q_values.__getitem__)
        processes_before = snapshot_processes(sim)
        previous_algorithm = sim.current_algo
        previous_total_wait = sim.get_total_waiting_time()

        sim.apply_action(action)
        scheduler_changed = sim.current_algo != previous_algorithm
        finished = sim.tick()
        total_wait = sim.get_total_waiting_time()
        waiting_delta = max(0, total_wait - previous_total_wait)
        after = sim.get_state_summary()
        reward = -float(waiting_delta)
        if scheduler_changed:
            reward -= 0.1
        if after["is_starving"]:
            reward -= 25.0
        step += 1

        decisions.append({
            "episode": episode,
            "step": step,
            "workload_profile": sim.current_workload_profile,
            "state": state,
            "observation": {
                name: value for name, value in zip(OBSERVATION_NAMES, inputs)
            },
            "q_values": {
                ACTION_NAMES[index]: float(value)
                for index, value in enumerate(q_values)
            },
            "processes": processes_before,
            "action": action,
            "action_name": ACTION_NAMES[action],
            "reward": float(reward),
            "scheduler_changed": bool(scheduler_changed),
            "resulting_state": after,
            "explanation": local_explanation(state, action),
            "explanation_status": "offline",
            "time": int(state["time"]),
        })
        total_waiting_time = total_wait

    completed = len(sim.completed)
    return {
        "status": "succeeded",
        "modelAvailable": True,
        "modelPath": "rl_agent/policy.json (export of local trained_model.zip)",
        "message": f"Completed {len(decisions)} decisions with the saved trained policy.",
        "decisionsCompleted": len(decisions),
        "decisionsTotal": len(decisions),
        "explanationsCompleted": 0,
        "explanationsTotal": 0,
        "explanationProvider": "offline",
        "explanationReady": False,
        "latestAction": decisions[-1]["action_name"] if decisions else None,
        "latestSimulationTime": decisions[-1]["time"] if decisions else 0,
        "decisions": decisions,
        "summary": {
            "seed": seed,
            "processes": 10,
            "decisions": len(decisions),
            "totalWaitingTime": total_waiting_time,
            "completedProcesses": completed,
        },
    }


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            load_policy()
            self._send_json(200, {
                "status": "ready",
                "modelAvailable": True,
                "modelPath": "rl_agent/policy.json",
            })
        except Exception as error:
            self._send_json(503, {
                "status": "model_missing",
                "modelAvailable": False,
                "error": str(error),
            })

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16384:
                return self._send_json(413, {"error": "Request body is too large."})
            body = json.loads(self.rfile.read(length) or b"{}")
            seed = int(body.get("seed", 42))
            count = int(body.get("decisions", 15))
            if count < 1 or count > MAX_DECISIONS:
                return self._send_json(400, {
                    "error": f"decisions must be between 1 and {MAX_DECISIONS}."
                })
            return self._send_json(200, run_simulation(seed=seed, count=count))
        except Exception as error:
            return self._send_json(500, {
                "status": "failed",
                "modelAvailable": POLICY_PATH.is_file(),
                "message": "The Vercel simulator run failed.",
                "detail": str(error),
            })

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.end_headers()
