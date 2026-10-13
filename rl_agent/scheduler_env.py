"""
scheduler_env.py — Wraps SimulatorCore in the Gymnasium API so any
Gymnasium-compatible RL library (Stable-Baselines3) can train against it
without knowing anything about scheduling internals.
"""

import inspect
import os
import random
import sys

import numpy as np

# Stable-Baselines3's current releases expect Gymnasium's API, not
# classic OpenAI Gym.
import gymnasium as gym
from gymnasium import spaces

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "simulator"))
from simulator_core import SimulatorCore  # noqa: E402
from workload_profiles import (  # noqa: E402
    normalize_workload_profiles,
)


class SchedulerEnv(gym.Env):
    def __init__(self, max_processes=10, workload_profiles=None):
        super().__init__()
        self.max_processes = max_processes
        self.workload_profiles = normalize_workload_profiles(workload_profiles)
        self.current_workload_profile = None
        # Matches SimulatorCore.apply_action's 5 actions: 0=no change,
        # 1=Round Robin, 2=Priority, 3=MLFQ, 4=boost longest-waiting process.
        self.action_space = spaces.Discrete(5)
        self.observation_space = spaces.Box(
            low=0, high=np.inf, shape=(7,), dtype=np.float32
        )
        self.sim = SimulatorCore(max_processes=max_processes)

    def _reset_simulator(self, seed, workload_profile):
        """Use the profile-aware simulator contract, with legacy compatibility.

        The simulator-core task can implement reset(seed=..., options=...).
        Until then, the original random workload remains available under the
        legacy_random profile so existing training and evaluation still run.
        """
        reset_parameters = inspect.signature(self.sim.reset).parameters
        if "seed" in reset_parameters and "options" in reset_parameters:
            self.sim.reset(
                seed=seed,
                options={"workload_profile": workload_profile},
            )
            return

        if workload_profile != "legacy_random":
            raise RuntimeError(
                "Named workload profiles require SimulatorCore.reset(seed=None, "
                "options=None) support. The simulator-core integration is not "
                "available on this branch's base revision yet."
            )

        if seed is not None:
            random.seed(seed)
        self.sim.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
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

        self._reset_simulator(seed, selected_profile)
        self.current_workload_profile = selected_profile
        return self._state_to_array(), {
            "workload_profile": self.current_workload_profile
        }

    def step(self, action):
        self.sim.apply_action(action)
        finished_a_process = self.sim.tick()

        state = self.sim.get_state_summary()
        reward = self._compute_reward(state, finished_a_process)
        terminated = self.sim.is_episode_done()
        truncated = False
        info = {
            "avg_wait": state["avg_wait_time"],
            "is_starving": state["is_starving"],
            "workload_profile": self.current_workload_profile,
        }

        return self._state_to_array(), reward, terminated, truncated, info

    def _state_to_array(self):
        state = self.sim.get_state_summary()
        return np.array(
            [
                state["queue_length"],
                state["avg_wait_time"],
                state["max_wait_time"],
                state["num_io_bound"],
                state["num_cpu_bound"],
                state["current_algo"],
                1.0 if state["is_starving"] else 0.0,
            ],
            dtype=np.float32,
        )

    def _compute_reward(self, state_dict, finished_a_process):
        """Starting-point reward formula — expected to be iterated on,
        not treated as final."""
        reward = -0.1 * state_dict["avg_wait_time"]
        if state_dict["is_starving"]:
            # Must dominate the wait-time term, or the agent will let one
            # process starve to lower the average — a known RL failure mode.
            reward -= 5.0
        if finished_a_process:
            # Rewards actual progress, not just avoiding penalties by stalling.
            reward += 1.0
        return reward


if __name__ == "__main__":
    env = SchedulerEnv(max_processes=10)
    obs, info = env.reset()
    total_reward = 0.0
    terminated = truncated = False
    steps = 0
    while not (terminated or truncated) and steps < 500:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1
    print(f"Episode finished after {steps} steps. Total reward: {total_reward:.2f}")
