"""
generate_decision_log.py — Runs a trained DQN model through
SchedulerEnv, greedily picking actions, and logs each (state, action)
pair. This replaces explainer.py's generate_fake_decisions() as the
source of real decisions once a model has been trained.

Run from the project root:
    python -m rl_agent.generate_decision_log
    python -m rl_agent.generate_decision_log --model-path runs/experiment-1/trained_model.zip

Writes decision_log.json with action + action_name. Cloud explanations
are opt-in: set EXPLANATION_PROVIDER=gemini and GEMINI_API_KEY to use
Gemini, or EXPLANATION_PROVIDER=claude and ANTHROPIC_API_KEY to use Claude.
With no explicit provider, the script runs offline and makes no API calls.
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from stable_baselines3 import DQN
import torch

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_env import OBSERVATION_FEATURES, SchedulerEnv  # noqa: E402
from model_compatibility import validate_model_environment  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "explainability"))
from explainer import ACTION_NAMES, create_client, explain_decision, explanation_error_message  # noqa: E402


def snapshot_processes(sim):
    """Return a JSON-safe, per-process view of the simulator at this tick."""
    mlfq_levels = {
        id(process): level
        for level, queue in enumerate(sim.mlfq_queues)
        for process in queue
    }
    io_wakeups = {
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
            "queue_level": mlfq_levels.get(id(process)),
            "io_wakeup_time": io_wakeups.get(id(process)),
        }
        for process in sim.processes
    ]


def iter_real_decisions(model_path="trained_model", max_processes=10, n=15, seed=42):
    """Yield the real model action and before/after simulator state per step."""
    model = DQN.load(model_path)
    env = SchedulerEnv(max_processes=max_processes, seed=seed)
    try:
        validate_model_environment(model, model_path, env)
        emitted = 0
        episode = 0
        while emitted < n:
            obs, reset_info = env.reset(seed=seed if episode == 0 else None)
            episode += 1
            terminated = truncated = False
            episode_step = 0
            while not (terminated or truncated) and emitted < n:
                state = env.sim.get_state_summary()
                processes_before = snapshot_processes(env.sim)
                observation_tensor, _ = model.policy.obs_to_tensor(obs)
                with torch.no_grad():
                    q_values = model.q_net(observation_tensor).squeeze(0).cpu().tolist()
                action, _ = model.predict(obs, deterministic=True)
                action = int(action)
                obs, reward, terminated, truncated, info = env.step(action)
                episode_step += 1
                emitted += 1
                yield {
                    "episode": episode,
                    "step": episode_step,
                    "workload_profile": reset_info.get("workload_profile"),
                    "state": state,
                    "observation": {
                        name: float(value)
                        for name, value in zip(OBSERVATION_FEATURES, observation_tensor.squeeze(0).cpu().tolist())
                    },
                    "q_values": {
                        ACTION_NAMES[index]: float(value)
                        for index, value in enumerate(q_values)
                    },
                    "processes": processes_before,
                    "action": action,
                    "reward": float(reward),
                    "scheduler_changed": bool(info.get("scheduler_changed")),
                    "resulting_state": env.sim.get_state_summary(),
                    "processes_after": snapshot_processes(env.sim),
                }
    finally:
        env.close()


def generate_real_decisions(model_path="trained_model", max_processes=10, n=15, seed=42):
    """Compatibility helper that collects real policy decisions into a list."""
    return list(iter_real_decisions(model_path, max_processes, n, seed))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate scheduler decisions from a trained DQN model."
    )
    parser.add_argument(
        "--model-path",
        default="trained_model",
        help="Path to the saved model (default: trained_model).",
    )
    parser.add_argument(
        "--max-processes",
        type=int,
        default=10,
        help="Maximum processes in the simulator (default: 10).",
    )
    parser.add_argument(
        "--decisions",
        type=int,
        default=15,
        help="Number of decisions to log (default: 15).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for a repeatable simulated workload sequence (default: 42).",
    )
    parser.add_argument(
        "--output",
        default="decision_log.json",
        help="Path for the generated JSON decision log.",
    )
    parser.add_argument(
        "--stream-jsonl",
        action="store_true",
        help="Emit a machine-readable progress event after every simulator step.",
    )
    parser.add_argument(
        "--step-delay-ms",
        type=int,
        default=0,
        help="Pause after each decision so a live dashboard can show the simulation.",
    )
    args = parser.parse_args()
    if args.max_processes < 1:
        parser.error("--max-processes must be at least 1")
    if args.decisions < 1:
        parser.error("--decisions must be at least 1")
    if args.step_delay_ms < 0:
        parser.error("--step-delay-ms must be zero or greater")
    return args


def write_decision_log(decisions, output_path):
    """Atomically write a log so dashboard polling never sees partial JSON."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(destination.parent),
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(decisions, temporary_file, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _emit_event(event):
    print(json.dumps(event, separators=(",", ":")), flush=True)


def main(
    model_path="trained_model",
    max_processes=10,
    n=15,
    output_path="decision_log.json",
    seed=42,
    stream_jsonl=False,
    step_delay_ms=0,
):
    provider = os.environ.get("EXPLANATION_PROVIDER", "offline").strip().lower()
    client = None
    provider_error = None
    if provider not in {"offline", "gemini", "claude"}:
        provider_error = "EXPLANATION_PROVIDER must be offline, gemini, or claude."
        provider = "offline"
    elif provider != "offline":
        try:
            client = create_client(provider)
        except Exception as exc:
            provider_error = f"{provider.title()} setup failed ({type(exc).__name__}): {exc}"

    log = []
    for decision in iter_real_decisions(
        model_path=model_path,
        max_processes=max_processes,
        n=n,
        seed=seed,
    ):
        action = decision["action"]
        explanation = None
        error_message = None
        if client is not None and stream_jsonl:
            entry_status = "pending"
        elif client is not None:
            try:
                explanation = explain_decision(
                    decision["state"],
                    action,
                    client,
                    provider=provider,
                    observation=decision["observation"],
                    q_values=decision["q_values"],
                )
                entry_status = "available"
            except Exception as exc:
                entry_status = "unavailable"
                error_message = explanation_error_message(exc, provider)
                if str(getattr(exc, "code", "")) == "429":
                    provider_error = error_message + " Further explanation requests in this run were skipped."
                    client = None
                print(
                    f"[episode {decision['episode']} step {decision['step']}] "
                    f"{provider.title()} explanation unavailable; keeping the real decision.",
                    file=sys.stderr if stream_jsonl else sys.stdout,
                    flush=True,
                )
        elif provider_error:
            entry_status = "unavailable"
            error_message = provider_error
        else:
            entry_status = "not_configured"

        entry = {
            **decision,
            "action_name": ACTION_NAMES[action],
            "explanation_provider": provider,
            "explanation": explanation,
            "explanation_status": entry_status,
        }
        if error_message:
            entry["explanation_error"] = error_message
        log.append(entry)

        if stream_jsonl:
            # Finish the simulator timeline before making optional network
            # requests. A slow explanation must not pause the DQN's actions.
            write_decision_log(log, output_path)
            _emit_event(
                {
                    "type": "decision",
                    "index": len(log),
                    "total": n,
                    "episode": decision["episode"],
                    "step": decision["step"],
                    "time": decision["state"]["time"],
                    "action": action,
                    "action_name": entry["action_name"],
                    "explanation_provider": provider,
                    "explanation_status": entry_status,
                }
            )
            if step_delay_ms:
                time.sleep(step_delay_ms / 1000)
        elif explanation:
            print(
                f"[episode {decision['episode']} step {decision['step']}] "
                f"{entry['action_name']}: {explanation}"
            )

    if not stream_jsonl:
        write_decision_log(log, output_path)
        if client is None:
            print("No cloud explanation client is active — saved real decisions without Gemini/Claude explanations.")
        print(f"Wrote {len(log)} decisions to {output_path}")
    else:
        _emit_event({"type": "decisions_complete", "total": len(log)})
        if client is not None:
            for index, entry in enumerate(log, start=1):
                try:
                    if provider_error:
                        entry["explanation_status"] = "unavailable"
                        entry["explanation_error"] = provider_error
                    else:
                        entry["explanation"] = explain_decision(
                            entry["state"],
                            entry["action"],
                            client,
                            provider=provider,
                            observation=entry["observation"],
                            q_values=entry["q_values"],
                        )
                        entry["explanation_status"] = "available"
                        entry.pop("explanation_error", None)
                except Exception as exc:
                    entry["explanation_status"] = "unavailable"
                    entry["explanation_error"] = explanation_error_message(exc, provider)
                    if str(getattr(exc, "code", "")) == "429":
                        provider_error = entry["explanation_error"] + " Further explanation requests in this run were skipped."
                    print(
                        f"[episode {entry['episode']} step {entry['step']}] "
                        f"{provider.title()} explanation unavailable; keeping the real decision.",
                        file=sys.stderr,
                        flush=True,
                    )
                write_decision_log(log, output_path)
                _emit_event(
                    {
                        "type": "explanation",
                        "index": index,
                        "total": len(log),
                        "explanation_status": entry["explanation_status"],
                    }
                )
        _emit_event({"type": "complete", "total": len(log)})

    return log


if __name__ == "__main__":
    args = parse_args()
    main(
        model_path=args.model_path,
        max_processes=args.max_processes,
        n=args.decisions,
        output_path=args.output,
        seed=args.seed,
        stream_jsonl=args.stream_jsonl,
        step_delay_ms=args.step_delay_ms,
    )
