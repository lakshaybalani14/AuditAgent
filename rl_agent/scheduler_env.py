"""Gymnasium environment for learning workload-aware scheduling choices.

The observation is a normalized summary of the current workload and scheduler
state. The episode return primarily minimizes the total READY waiting time,
which is the same quantity used by the evaluation's completed-process waiting
time metric; scheduler changes and starvation add small explicit costs.
"""

import os
import sys

import numpy as np
import gymnasium as gym
from gymnasium import spaces

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "simulator"))
from simulator_core import (  # noqa: E402
    ALGO_MLFQ,
    ALGO_PRIORITY,
    ALGO_ROUND_ROBIN,
    SimulatorCore,
)
from workload_profiles import normalize_workload_profiles  # noqa: E402


LEARNING_SPEC_VERSION = 2
REWARD_DESCRIPTION = (
    "negative increase in total accumulated READY waiting time, minus the "
    "scheduler-switch penalty and starvation-step penalty"
)
OBSERVATION_FEATURES = (
    "completed_fraction",
    "pending_fraction",
    "ready_fraction",
    "blocked_fraction",
    "running_present",
    "mean_ready_wait_fraction",
    "max_ready_wait_fraction",
    "mean_ready_remaining_fraction",
    "min_ready_remaining_fraction",
    "max_ready_remaining_fraction",
    "ready_io_fraction",
    "mean_ready_priority_fraction",
    "min_ready_priority_fraction",
    "running_remaining_fraction",
    "current_algorithm_round_robin",
    "current_algorithm_priority",
    "current_algorithm_mlfq",
    "running_algorithm_round_robin",
    "running_algorithm_priority",
    "running_algorithm_mlfq",
)


class SchedulerEnv(gym.Env):
    """Wrap SimulatorCore so Stable-Baselines3 can train on scheduler choices."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        max_processes=10,
        seed=None,
        scenario="mixed_cpu_io",
        workload_config=None,
        workload_profiles=None,
        switch_penalty=0.1,
        starvation_penalty=25.0,
        max_episode_steps=10_000,
    ):
        super().__init__()
        if switch_penalty < 0:
            raise ValueError("switch_penalty must be zero or greater")
        if starvation_penalty < 0:
            raise ValueError("starvation_penalty must be zero or greater")
        if max_episode_steps <= 0:
            raise ValueError("max_episode_steps must be greater than zero")
        self.max_processes = max_processes
        self.switch_penalty = float(switch_penalty)
        self.starvation_penalty = float(starvation_penalty)
        self.max_episode_steps = int(max_episode_steps)
        self.episode_steps = 0
        self.workload_profiles = normalize_workload_profiles(workload_profiles)
        self.current_workload_profile = None
        # 0=no change, 1=Round Robin, 2=Priority, 3=MLFQ,
        # 4=boost the longest-waiting process's priority.
        self.action_space = spaces.Discrete(5)
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(len(OBSERVATION_FEATURES),),
            dtype=np.float32,
        )
        self.sim = SimulatorCore(
            max_processes=max_processes,
            seed=seed,
            scenario=scenario,
            workload_config=workload_config,
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary or None")
        options = options or {}
        requested_profile = options.get("workload_profile")
        if requested_profile is not None:
            if requested_profile not in self.workload_profiles:
                raise ValueError(
                    f"Profile {requested_profile!r} is not among configured "
                    f"profiles: {self.workload_profiles}"
                )
            selected_profile = requested_profile
        else:
            selected_profile = self.workload_profiles[
                int(self.np_random.integers(len(self.workload_profiles)))
            ]

        simulator_options = dict(options)
        simulator_options["workload_profile"] = selected_profile
        self.sim.reset(seed=seed, options=simulator_options)
        self.current_workload_profile = selected_profile
        self.episode_steps = 0
        return self._state_to_array(), {
            "workload_profile": self.current_workload_profile
        }

    def step(self, action):
        previous_algorithm = self.sim.current_algo
        previous_waiting_time = self.sim.get_total_waiting_time()
        self.sim.apply_action(action)
        scheduler_changed = self.sim.current_algo != previous_algorithm
        finished_a_process = self.sim.tick()

        self.episode_steps += 1
        total_waiting_time = self.sim.get_total_waiting_time()
        waiting_delta = max(0, total_waiting_time - previous_waiting_time)
        state = self.sim.get_state_summary()
        reward = self._compute_reward(
            waiting_delta,
            state["is_starving"],
            scheduler_changed=scheduler_changed,
        )
        terminated = self.sim.is_episode_done()
        truncated = not terminated and self.episode_steps >= self.max_episode_steps
        info = {
            "avg_wait": state["avg_wait_time"],
            "is_starving": state["is_starving"],
            "workload_profile": self.current_workload_profile,
            "scheduler_changed": scheduler_changed,
            "waiting_delta": waiting_delta,
            "total_waiting_time": total_waiting_time,
            "finished_a_process": finished_a_process,
        }
        return self._state_to_array(), reward, terminated, truncated, info

    @staticmethod
    def _ratio(value, scale):
        return float(np.clip(value / scale, 0.0, 1.0)) if scale else 0.0

    def _state_to_array(self):
        state = self.sim.get_state_summary()
        processes = self.sim.processes
        total_processes = max(1, len(processes))
        ready = self.sim.ready_queue
        pending = self.sim.pending
        blocked = self.sim.blocked
        running = self.sim.running_process
        max_burst = max((process.burst_time for process in processes), default=1)
        max_priority = max((process.priority for process in processes), default=1)
        wait_scale = max(
            1,
            max((process.arrival_time for process in processes), default=0)
            + sum(
                process.burst_time
                + sum(request.duration for request in process.io_requests)
                for process in processes
            ),
        )
        ready_ages = [self.sim.time - process.last_ready_time for process in ready]
        ready_remaining = [process.remaining_time for process in ready]
        ready_priorities = [process.priority for process in ready]
        ready_count = max(1, len(ready))

        features = [
            len(self.sim.completed) / total_processes,
            len(pending) / total_processes,
            len(ready) / total_processes,
            len(blocked) / total_processes,
            1.0 if running is not None else 0.0,
            self._ratio(float(np.mean(ready_ages)) if ready_ages else 0.0, wait_scale),
            self._ratio(max(ready_ages, default=0), wait_scale),
            self._ratio(float(np.mean(ready_remaining)) if ready_remaining else 0.0, max_burst),
            self._ratio(min(ready_remaining, default=0), max_burst),
            self._ratio(max(ready_remaining, default=0), max_burst),
            sum(process.is_io_bound for process in ready) / ready_count
            if ready else 0.0,
            self._ratio(
                float(np.mean(ready_priorities)) if ready_priorities else 0.0,
                max_priority,
            ),
            self._ratio(min(ready_priorities, default=0), max_priority),
            self._ratio(running.remaining_time if running is not None else 0, max_burst),
            1.0 if state["current_algo"] == ALGO_ROUND_ROBIN else 0.0,
            1.0 if state["current_algo"] == ALGO_PRIORITY else 0.0,
            1.0 if state["current_algo"] == ALGO_MLFQ else 0.0,
            1.0 if self.sim.running_algorithm == ALGO_ROUND_ROBIN else 0.0,
            1.0 if self.sim.running_algorithm == ALGO_PRIORITY else 0.0,
            1.0 if self.sim.running_algorithm == ALGO_MLFQ else 0.0,
        ]
        return np.asarray(np.clip(features, 0.0, 1.0), dtype=np.float32)

    def _compute_reward(self, waiting_delta, is_starving, scheduler_changed=False):
        """Reward reductions in total job waiting; charge churn and starvation."""
        reward = -float(waiting_delta)
        if scheduler_changed:
            reward -= self.switch_penalty
        if is_starving:
            reward -= self.starvation_penalty
        return reward


if __name__ == "__main__":
    env = SchedulerEnv(max_processes=10)
    obs, info = env.reset()
    total_reward = 0.0
    terminated = truncated = False
    steps = 0
    while not (terminated or truncated):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1
    print(
        f"Episode finished after {steps} steps. "
        f"Total reward: {total_reward:.2f}; "
        f"total process waiting: {env.sim.get_total_waiting_time()}"
    )
    env.close()
