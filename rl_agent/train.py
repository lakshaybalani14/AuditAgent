"""
Train a DQN against SchedulerEnv and record the experiment settings.

Run from the repository root:
    python -m rl_agent.train
    python -m rl_agent.train --timesteps 50000 --seed 123 --output-dir runs/experiment-1

A positional timestep count remains supported for compatibility:
    python -m rl_agent.train 50000
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import random
import sys

import gymnasium
import numpy as np
import stable_baselines3
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_env import SchedulerEnv  # noqa: E402


class ProgressCallback(BaseCallback):
    """Print a compact training snapshot every N environment steps."""

    def __init__(self, print_every=1000, verbose=0):
        super().__init__(verbose)
        if print_every <= 0:
            raise ValueError("print_every must be greater than zero")
        self.print_every = print_every

    def _on_step(self) -> bool:
        if self.num_timesteps % self.print_every == 0:
            infos = self.locals.get("infos", [{}])
            info = infos[0] if infos else {}
            print(
                f"[step {self.num_timesteps}] "
                f"avg_queue_age={info.get('avg_wait')} "
                f"is_starving={info.get('is_starving')}"
            )
        return True


def main(
    total_timesteps=100_000,
    learning_rate=1e-3,
    buffer_size=50_000,
    seed=42,
    output_dir=".",
    max_processes=10,
    print_every=1000,
):
    """Train one model and save its checkpoint, Monitor log, and metadata."""
    if total_timesteps <= 0:
        raise ValueError("total_timesteps must be greater than zero")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be greater than zero")
    if buffer_size <= 0:
        raise ValueError("buffer_size must be greater than zero")
    if max_processes <= 0:
        raise ValueError("max_processes must be greater than zero")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    model_path = output_path / "trained_model"
    monitor_path = output_path / "training.monitor.csv"

    # SimulatorCore currently uses Python's module-level random generator
    # to create process batches, so seed it here as well as the DQN.
    random.seed(seed)
    np.random.seed(seed)

    env = Monitor(
        SchedulerEnv(max_processes=max_processes),
        filename=str(monitor_path),
    )
    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        buffer_size=buffer_size,
        seed=seed,
        verbose=1,
    )

    try:
        callback = ProgressCallback(print_every=print_every)
        model.learn(total_timesteps=total_timesteps, callback=callback)
        model.save(str(model_path))
    finally:
        env.close()

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "algorithm": "DQN",
        "policy": "MlpPolicy",
        "training": {
            "total_timesteps": total_timesteps,
            "learning_rate": learning_rate,
            "buffer_size": buffer_size,
            "seed": seed,
            "max_processes": max_processes,
            "progress_print_every": print_every,
        },
        "artifacts": {
            "model": str(model_path.with_suffix(".zip")),
            "monitor_csv": str(monitor_path),
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "gymnasium": gymnasium.__version__,
            "stable_baselines3": stable_baselines3.__version__,
        },
        "notes": [
            "The simulator creates synthetic workloads.",
            "The seed initializes Python workload randomness and the DQN.",
            "Reproducibility can still depend on the machine and library versions.",
        ],
    }
    metadata_path = output_path / "training_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(f"Saved model to {model_path.with_suffix('.zip')}")
    print(f"Saved training metadata to {metadata_path}")
    print(f"Saved episode monitor log to {monitor_path}")
    return model


def parse_args():
    parser = argparse.ArgumentParser(description="Train the AuditAgent DQN.")
    parser.add_argument(
        "steps_positional",
        nargs="?",
        type=int,
        help="Timestep count in the legacy positional form.",
    )
    parser.add_argument("--timesteps", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--buffer-size", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-processes", type=int, default=10)
    parser.add_argument("--print-every", type=int, default=1000)
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for the model and run artifacts (default: project root).",
    )
    args = parser.parse_args()

    if args.timesteps is not None and args.steps_positional is not None:
        parser.error("provide either positional steps or --timesteps, not both")
    args.resolved_timesteps = (
        args.timesteps
        if args.timesteps is not None
        else args.steps_positional
        if args.steps_positional is not None
        else 100_000
    )
    return args


if __name__ == "__main__":
    args = parse_args()
    main(
        total_timesteps=args.resolved_timesteps,
        learning_rate=args.learning_rate,
        buffer_size=args.buffer_size,
        seed=args.seed,
        output_dir=args.output_dir,
        max_processes=args.max_processes,
        print_every=args.print_every,
    )
