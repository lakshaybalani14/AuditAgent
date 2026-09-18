"""
train.py — Trains a DQN agent against SchedulerEnv and saves it to disk.

DQN ("Deep Q-Network") is a neural-network-based extension of
Q-learning, needed here because the 7-dimensional continuous state
space is too large for a plain lookup table.

Run from the project root:
    python -m rl_agent.train
"""

import os
import sys

from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_env import SchedulerEnv  # noqa: E402


class ProgressCallback(BaseCallback):
    """Prints avg_wait and is_starving from the info dict every N steps,
    so training progress is visible instead of a silent black box."""

    def __init__(self, print_every=1000, verbose=0):
        super().__init__(verbose)
        self.print_every = print_every

    def _on_step(self) -> bool:
        if self.num_timesteps % self.print_every == 0:
            infos = self.locals.get("infos", [{}])
            info = infos[0] if infos else {}
            avg_wait = info.get("avg_wait")
            is_starving = info.get("is_starving")
            print(
                f"[step {self.num_timesteps}] avg_wait={avg_wait} "
                f"is_starving={is_starving}"
            )
        return True


def main(total_timesteps=100_000):
    env = Monitor(SchedulerEnv(max_processes=10))

    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=1e-3,
        buffer_size=50_000,
        verbose=1,
    )

    callback = ProgressCallback(print_every=1000)
    model.learn(total_timesteps=total_timesteps, callback=callback)

    model.save("trained_model")
    print("Saved trained_model.zip")


if __name__ == "__main__":
    # total_timesteps is a starting point — likely needs tuning up or
    # down based on how quickly the reward curve stabilizes. It can be
    # overridden via: python -m rl_agent.train <timesteps>
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    main(total_timesteps=steps)
