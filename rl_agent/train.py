"""
Train a DQN against SchedulerEnv and record the experiment settings.

Run from the repository root:
    python -m rl_agent.train
    python -m rl_agent.train --timesteps 50000 --seed 123 --output-dir runs/experiment-1
    python -m rl_agent.train --workload-profiles all --timesteps 50000
    python -m rl_agent.train --timesteps 200000 --seed 42 --workload-profiles all \
        --resume-from runs/dqn-learning-v2-seed-42/trained_model.zip \
        --output-dir runs/dqn-learning-v2-seed-42-continued

A positional timestep count remains supported for compatibility:
    python -m rl_agent.train 50000
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys

import gymnasium
import numpy as np
import stable_baselines3
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback, CallbackList, CheckpointCallback
from stable_baselines3.common.monitor import Monitor

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_env import (  # noqa: E402
    LEARNING_SPEC_VERSION, OBSERVATION_FEATURES, REWARD_DESCRIPTION, SchedulerEnv
)
from model_compatibility import validate_resume_metadata  # noqa: E402
from workload_profiles import normalize_workload_profiles  # noqa: E402


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
                f"profile={info.get('workload_profile')} "
                f"avg_queue_age={info.get('avg_wait')} "
                f"is_starving={info.get('is_starving')}"
            )
        return True


class BestValidationCallback(BaseCallback):
    """Evaluate on fixed, separate seeds and retain the best safe checkpoint."""

    def __init__(
        self,
        output_path,
        eval_every,
        episodes_per_profile,
        workload_profiles,
        max_processes,
        switch_penalty,
        starvation_penalty,
        verbose=0,
    ):
        super().__init__(verbose)
        if eval_every <= 0:
            raise ValueError("eval_every must be greater than zero")
        if episodes_per_profile <= 0:
            raise ValueError("episodes_per_profile must be greater than zero")
        self.output_path = Path(output_path)
        self.eval_every = eval_every
        self.episodes_per_profile = episodes_per_profile
        self.workload_profiles = tuple(workload_profiles)
        self.max_processes = max_processes
        self.next_eval = eval_every
        self.history = []
        self.best_key = None
        self.best_result = None
        self.best_model_path = self.output_path / "best_model"
        self.validation_env = SchedulerEnv(
            max_processes=max_processes,
            workload_profiles=self.workload_profiles,
            switch_penalty=switch_penalty,
            starvation_penalty=starvation_penalty,
        )

    def _evaluate_policy(self):
        records = []
        total_starvation_steps = 0
        total_switches = 0
        completed_count = 0
        expected_count = 0

        for profile_index, profile in enumerate(self.workload_profiles):
            for episode_index in range(self.episodes_per_profile):
                seed = 1_000_000 + profile_index * self.episodes_per_profile + episode_index
                observation, _ = self.validation_env.reset(
                    seed=seed, options={"workload_profile": profile}
                )
                terminated = truncated = False
                starvation_steps = 0
                switches = 0
                steps = 0
                while not (terminated or truncated):
                    action, _ = self.model.predict(observation, deterministic=True)
                    observation, _, terminated, truncated, info = self.validation_env.step(
                        int(action)
                    )
                    starvation_steps += int(bool(info["is_starving"]))
                    switches += int(bool(info["scheduler_changed"]))
                    steps += 1

                completed = self.validation_env.sim.completed
                completed_count += len(completed)
                expected_count += self.max_processes
                episode_complete = (
                    terminated and len(completed) == self.max_processes
                )
                records.append(
                    {
                        "profile": profile,
                        "seed": seed,
                        "terminated": bool(terminated),
                        "steps": steps,
                        "completed": len(completed),
                        "completion_rate": (
                            len(completed) / self.max_processes
                            if self.max_processes else 1.0
                        ),
                        "mean_process_waiting_time_ticks": (
                            sum(process.waiting_time for process in completed)
                            / len(completed)
                            if episode_complete and completed else None
                        ),
                        "starvation_steps": starvation_steps,
                        "scheduler_switches": switches,
                    }
                )
                total_starvation_steps += starvation_steps
                total_switches += switches

        all_complete = all(
            record["terminated"] and record["completed"] == self.max_processes
            for record in records
        )
        complete_waits = [
            record["mean_process_waiting_time_ticks"]
            for record in records
            if record["mean_process_waiting_time_ticks"] is not None
        ]
        return {
            "step": self.num_timesteps,
            "episodes": len(records),
            "all_episodes_completed": all_complete,
            "completion_rate": (
                completed_count / expected_count if expected_count else 1.0
            ),
            "mean_process_waiting_time_ticks": (
                float(np.mean(complete_waits))
                if all_complete and complete_waits else None
            ),
            "starvation_steps": total_starvation_steps,
            "mean_scheduler_switches": total_switches / len(records) if records else 0.0,
            "episodes_by_profile": records,
        }

    @staticmethod
    def _ranking(result):
        clean = result["all_episodes_completed"] and result["starvation_steps"] == 0
        mean_wait = result["mean_process_waiting_time_ticks"]
        return (
            0 if clean else 1,
            result["starvation_steps"],
            -result["completion_rate"],
            mean_wait if mean_wait is not None else float("inf"),
            result["mean_scheduler_switches"],
        )

    def _write_history(self):
        document = {
            "validation_seeds_start": 1_000_000,
            "episodes_per_profile": self.episodes_per_profile,
            "workload_profiles": list(self.workload_profiles),
            "selection_rule": (
                "prefer full completion with zero starvation; then fewer "
                "starvation steps, higher completion, lower mean process wait"
            ),
            "best": self.best_result,
            "history": self.history,
        }
        (self.output_path / "validation_history.json").write_text(
            json.dumps(document, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    def _on_step(self) -> bool:
        if self.num_timesteps < self.next_eval:
            return True
        result = self._evaluate_policy()
        self.history.append(result)
        key = self._ranking(result)
        if self.best_key is None or key < self.best_key:
            self.best_key = key
            self.best_result = result
            self.model.save(str(self.best_model_path))
            self.model.save_replay_buffer(
                str(self.output_path / "best_model_replay_buffer.pkl")
            )
            print(
                f"[validation step {self.num_timesteps}] new best: "
                f"complete={result['completion_rate']:.3f} "
                f"starvation_steps={result['starvation_steps']} "
                f"mean_wait={result['mean_process_waiting_time_ticks']}"
            )
        else:
            print(
                f"[validation step {self.num_timesteps}] "
                f"complete={result['completion_rate']:.3f} "
                f"starvation_steps={result['starvation_steps']} "
                f"mean_wait={result['mean_process_waiting_time_ticks']}"
            )
        self._write_history()
        while self.next_eval <= self.num_timesteps:
            self.next_eval += self.eval_every
        return True

    def close(self):
        self.validation_env.close()


def main(
    total_timesteps=100_000,
    learning_rate=1e-3,
    buffer_size=50_000,
    seed=42,
    output_dir=".",
    max_processes=10,
    print_every=1000,
    workload_profiles=None,
    resume_from=None,
    checkpoint_every=100_000,
    switch_penalty=0.1,
    starvation_penalty=25.0,
    validation_every=25_000,
    validation_episodes=3,
):
    """Train one model and save its checkpoint, logs, and metadata."""
    if total_timesteps <= 0:
        raise ValueError("total_timesteps must be greater than zero")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be greater than zero")
    if buffer_size <= 0:
        raise ValueError("buffer_size must be greater than zero")
    if max_processes <= 0:
        raise ValueError("max_processes must be greater than zero")
    if switch_penalty < 0:
        raise ValueError("switch_penalty must be zero or greater")
    if starvation_penalty < 0:
        raise ValueError("starvation_penalty must be zero or greater")
    if validation_every < 0:
        raise ValueError("validation_every must be zero or greater")
    if validation_episodes <= 0:
        raise ValueError("validation_episodes must be greater than zero")

    selected_profiles = normalize_workload_profiles(workload_profiles)
    if resume_from:
        validate_resume_metadata(resume_from)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    model_path = output_path / "trained_model"
    if (
        resume_from is None
        and (
            model_path.with_suffix(".zip").exists()
            or (output_path / "best_model.zip").exists()
        )
    ):
        raise ValueError(
            f"{model_path.with_suffix('.zip')} already exists. "
            "Choose a new --output-dir or explicitly use --resume-from; "
            "a fresh run must not overwrite an earlier model."
        )
    monitor_path = output_path / "training.monitor.csv"
    learning_spec = {
        "version": LEARNING_SPEC_VERSION,
        "observation_features": list(OBSERVATION_FEATURES),
        "reward": REWARD_DESCRIPTION,
    }
    (output_path / "learning_spec.json").write_text(
        json.dumps({"learning_spec": learning_spec}, indent=2) + "\n",
        encoding="utf-8",
    )

    # Gymnasium forwards the DQN seed to the simulator on the first reset.
    np.random.seed(seed)

    env = Monitor(
        SchedulerEnv(
            max_processes=max_processes,
            workload_profiles=selected_profiles,
            switch_penalty=switch_penalty,
            starvation_penalty=starvation_penalty,
        ),
        filename=str(monitor_path),
        info_keywords=("workload_profile",),
        # A resumed run may use a fresh output directory. In that case, ask
        # Monitor to create its header; append only when its log already exists.
        override_existing=resume_from is None or not monitor_path.exists(),
    )
    if resume_from:
        model = DQN.load(resume_from, env=env)
        model.seed = seed
        model.set_random_seed(seed)
        resumed_timesteps = model.num_timesteps
        checkpoint_path = Path(resume_from)
        replay_buffer_path = checkpoint_path.with_suffix("")
        replay_buffer_path = replay_buffer_path.with_name(
            replay_buffer_path.name + "_replay_buffer.pkl"
        )
        if replay_buffer_path.exists():
            model.load_replay_buffer(str(replay_buffer_path))
            print(f"Loaded replay buffer from {replay_buffer_path}")
        else:
            print(
                "No replay buffer was saved with this checkpoint; continuing "
                "with the learned model weights and collecting new experience."
            )
        print(
            f"Resuming from {resume_from} at {resumed_timesteps} environment steps"
        )
    else:
        model = DQN(
            "MlpPolicy",
            env,
            learning_rate=learning_rate,
            buffer_size=buffer_size,
            seed=seed,
            verbose=1,
        )
        resumed_timesteps = 0

    validation_callback = None
    try:
        callbacks = [ProgressCallback(print_every=print_every)]
        if checkpoint_every < 0:
            raise ValueError("checkpoint_every must be zero or greater")
        if checkpoint_every:
            callbacks.append(
                CheckpointCallback(
                    save_freq=checkpoint_every,
                    save_path=str(output_path),
                    name_prefix="trained_model",
                    save_replay_buffer=True,
                    save_vecnormalize=False,
                )
            )
        if validation_every:
            validation_callback = BestValidationCallback(
                output_path=output_path,
                eval_every=validation_every,
                episodes_per_profile=validation_episodes,
                workload_profiles=selected_profiles,
                max_processes=max_processes,
                switch_penalty=switch_penalty,
                starvation_penalty=starvation_penalty,
            )
            callbacks.append(validation_callback)
        model.learn(
            total_timesteps=total_timesteps,
            callback=CallbackList(callbacks),
            reset_num_timesteps=resume_from is None,
        )
        model.save(str(model_path))
        model.save_replay_buffer(str(output_path / "trained_model_replay_buffer.pkl"))
    finally:
        if validation_callback is not None:
            validation_callback.close()
        env.close()

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "algorithm": "DQN",
        "policy": "MlpPolicy",
        "learning_spec": learning_spec,
        "training": {
            "total_timesteps": total_timesteps,
            "cumulative_total_timesteps": model.num_timesteps,
            "resumed_from": str(resume_from) if resume_from else None,
            "resumed_from_timesteps": resumed_timesteps,
            "checkpoint_every": checkpoint_every,
            "switch_penalty": switch_penalty,
            "starvation_penalty": starvation_penalty,
            "validation_every": validation_every,
            "validation_episodes_per_profile": validation_episodes,
            "best_validation": (
                validation_callback.best_result
                if validation_callback is not None else None
            ),
            "learning_rate": learning_rate,
            "buffer_size": buffer_size,
            "seed": seed,
            "max_processes": max_processes,
            "progress_print_every": print_every,
            "workload_profiles": list(selected_profiles),
            "profile_sampling": "uniformly selected at each episode reset",
        },
        "artifacts": {
            "model": str(model_path.with_suffix(".zip")),
            "best_model": (
                str((output_path / "best_model.zip"))
                if validation_callback is not None
                and validation_callback.best_result is not None
                else None
            ),
            "monitor_csv": str(monitor_path),
            "validation_history": (
                str(output_path / "validation_history.json")
                if validation_callback is not None else None
            ),
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "gymnasium": gymnasium.__version__,
            "stable_baselines3": stable_baselines3.__version__,
        },
        "notes": [
            "The simulator uses synthetic workloads.",
            "Episode reward tracks total READY waiting time and adds explicit "
            "scheduler-change and starvation costs.",
            "The learning specification is versioned; older checkpoints "
            "must be evaluated with their matching environment and not resumed here.",
            "The seed initializes the DQN and reproducible workload generation.",
            "Reproducibility can still depend on the machine and library versions.",
            "Named profiles require the profile-aware SimulatorCore reset interface.",
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
        "--resume-from",
        default=None,
        help="Load a saved DQN checkpoint and continue its training.",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=100_000,
        help="Save a model and replay buffer every N added steps (0 disables checkpoints).",
    )
    parser.add_argument(
        "--starvation-penalty",
        type=float,
        default=25.0,
        help="Reward cost for each decision step with a starved ready process.",
    )
    parser.add_argument(
        "--validation-every",
        type=int,
        default=25_000,
        help="Run fixed-seed validation every N training steps (0 disables it).",
    )
    parser.add_argument(
        "--validation-episodes",
        type=int,
        default=3,
        help="Validation episodes per workload profile.",
    )
    parser.add_argument(
        "--switch-penalty",
        type=float,
        default=0.1,
        help="Reward cost for each actual scheduler change (default: 0.1).",
    )
    parser.add_argument(
        "--workload-profiles",
        default="legacy_random",
        help="Comma-separated profile names or 'all' (default: legacy_random).",
    )
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
    try:
        args.resolved_workload_profiles = normalize_workload_profiles(
            args.workload_profiles
        )
    except ValueError as exc:
        parser.error(str(exc))
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
        workload_profiles=args.resolved_workload_profiles,
        resume_from=args.resume_from,
        checkpoint_every=args.checkpoint_every,
        switch_penalty=args.switch_penalty,
        starvation_penalty=args.starvation_penalty,
        validation_every=args.validation_every,
        validation_episodes=args.validation_episodes,
    )

