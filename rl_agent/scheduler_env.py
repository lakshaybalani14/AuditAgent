"""
scheduler_env.py — Wraps SimulatorCore in the Gymnasium API so any
Gymnasium-compatible RL library (Stable-Baselines3) can train against it
without knowing anything about scheduling internals.
"""

import os
import sys

import numpy as np

# Stable-Baselines3's current releases expect Gymnasium's API, not
# classic OpenAI Gym.
import gymnasium as gym
from gymnasium import spaces

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "simulator"))
from simulator_core import SimulatorCore  # noqa: E402


class SchedulerEnv(gym.Env):
    def __init__(self, max_processes=10):
        super().__init__()
        self.max_processes = max_processes
        # Matches SimulatorCore.apply_action's 5 actions: 0=no change,
        # 1=Round Robin, 2=Priority, 3=MLFQ, 4=boost longest-waiting process.
        self.action_space = spaces.Discrete(5)
        self.observation_space = spaces.Box(
            low=0, high=np.inf, shape=(7,), dtype=np.float32
        )
        self.sim = SimulatorCore(max_processes=max_processes)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.sim.reset()
        return self._state_to_array(), {}

    def step(self, action):
        self.sim.apply_action(action)
        finished_a_process = self.sim.tick()

        state = self.sim.get_state_summary()
        reward = self._compute_reward(state, finished_a_process)
        terminated = self.sim.is_episode_done()
        truncated = False
        info = {"avg_wait": state["avg_wait_time"], "is_starving": state["is_starving"]}

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
