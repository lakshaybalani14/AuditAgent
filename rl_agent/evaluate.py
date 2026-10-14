"""
Evaluate a saved DQN against fixed scheduler choices on matched workloads.

Run from the repository root:
    python -m rl_agent.evaluate --model-path trained_model.zip
    python -m rl_agent.evaluate --workload-profiles all --episodes 30 --seed 100
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys

from stable_baselines3 import DQN

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_env import SchedulerEnv  # noqa: E402
from workload_profiles import normalize_workload_profiles  # noqa: E402


def _mean(values):
    return statistics.mean(values) if values else 0.0


def _stddev(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def run_episode(env, policy_name, action_for_step, workload_profile, seed, max_steps):
    """Run one policy on one reproducible synthetic workload."""
    # Resetting the environment with this seed reproduces the workload.
    observation, _ = env.reset(
        seed=seed,
        options={"workload_profile": workload_profile},
    )

    total_reward = 0.0
    queue_age_samples = []
    max_queue_age_samples = []
    starvation_steps = 0
    terminated = False
    steps = 0

    while not terminated and steps < max_steps:
        action = int(action_for_step(observation, steps))
        observation, reward, terminated, truncated, info = env.step(action)
        total_reward += float(reward)
        steps += 1

        state = env.sim.get_state_summary()
        queue_age_samples.append(float(state["avg_wait_time"]))
        max_queue_age_samples.append(float(state["max_wait_time"]))
        starvation_steps += int(bool(state["is_starving"]))

        if truncated:
            break

    return {
        "policy": policy_name,
        "workload_profile": workload_profile,
        "seed": seed,
        "episode_return": total_reward,
        "episode_steps": steps,
        "mean_observed_queue_age_ticks": _mean(queue_age_samples),
        "max_observed_queue_age_ticks": max(max_queue_age_samples, default=0.0),
        "starvation_steps": starvation_steps,
        "processes_completed": len(env.sim.completed),
        "episode_terminated": bool(terminated),
        "hit_step_limit": not terminated and steps >= max_steps,
    }


def summarize_runs(runs):
    return {
        "episodes": len(runs),
        "mean_episode_return": _mean([run["episode_return"] for run in runs]),
        "std_episode_return": _stddev([run["episode_return"] for run in runs]),
        "mean_episode_steps": _mean([run["episode_steps"] for run in runs]),
        "mean_observed_queue_age_ticks": _mean(
            [run["mean_observed_queue_age_ticks"] for run in runs]
        ),
        "mean_max_observed_queue_age_ticks": _mean(
            [run["max_observed_queue_age_ticks"] for run in runs]
        ),
        "mean_starvation_steps": _mean([run["starvation_steps"] for run in runs]),
        "mean_processes_completed": _mean(
            [run["processes_completed"] for run in runs]
        ),
    }


def evaluate(
    model_path,
    episodes=30,
    seed=42,
    max_processes=10,
    max_steps=10_000,
    workload_profiles=None,
):
    if episodes <= 0:
        raise ValueError("episodes must be greater than zero")
    if max_processes <= 0:
        raise ValueError("max_processes must be greater than zero")
    if max_steps <= 0:
        raise ValueError("max_steps must be greater than zero")

    selected_profiles = normalize_workload_profiles(workload_profiles)
    model = DQN.load(model_path)
    env = SchedulerEnv(
        max_processes=max_processes,
        workload_profiles=selected_profiles,
    )
    policies = {
        "DQN": lambda observation, step: model.predict(
            observation, deterministic=True
        )[0],
        "Round Robin": lambda observation, step: 1 if step == 0 else 0,
        "Priority": lambda observation, step: 2 if step == 0 else 0,
        "MLFQ": lambda observation, step: 3 if step == 0 else 0,
    }

    results = {}
    try:
        for policy_name, action_for_step in policies.items():
            all_runs = []
            by_profile = {}
            for profile_name in selected_profiles:
                profile_runs = []
                for episode_index in range(episodes):
                    episode_seed = seed + episode_index
                    profile_runs.append(
                        run_episode(
                            env,
                            policy_name,
                            action_for_step,
                            profile_name,
                            episode_seed,
                            max_steps,
                        )
                    )
                by_profile[profile_name] = summarize_runs(profile_runs)
                all_runs.extend(profile_runs)

            results[policy_name] = {
                "summary": summarize_runs(all_runs),
                "by_profile": by_profile,
                "runs": all_runs,
            }
    finally:
        env.close()

    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_path": str(model_path),
        "workload_source": "seeded synthetic process profiles",
        "configuration": {
            "episodes_per_profile": episodes,
            "first_seed": seed,
            "max_processes": max_processes,
            "max_steps_per_episode": max_steps,
            "workload_profiles": list(selected_profiles),
        },
        "metrics_note": (
            "Queue-age metrics are sampled from the current ready-queue state. "
            "They are not completed-process total waiting times."
        ),
        "matched_workload_note": (
            "Each policy is evaluated on the same profile and episode seeds. "
            "Training and evaluation should use separate seed ranges."
        ),
        "policies": results,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate a saved DQN against fixed scheduler baselines."
    )
    parser.add_argument("--model-path", default="trained_model")
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-processes", type=int, default=10)
    parser.add_argument("--max-steps", type=int, default=10_000)
    parser.add_argument(
        "--workload-profiles",
        default="legacy_random",
        help="Comma-separated profile names or 'all' (default: legacy_random).",
    )
    parser.add_argument("--output", default="evaluation_results.json")
    args = parser.parse_args()
    try:
        args.resolved_workload_profiles = normalize_workload_profiles(
            args.workload_profiles
        )
    except ValueError as exc:
        parser.error(str(exc))
    return args


if __name__ == "__main__":
    args = parse_args()
    report = evaluate(
        model_path=args.model_path,
        episodes=args.episodes,
        seed=args.seed,
        max_processes=args.max_processes,
        max_steps=args.max_steps,
        workload_profiles=args.resolved_workload_profiles,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved evaluation report to {output_path}")
    for policy_name, result in report["policies"].items():
        summary = result["summary"]
        print(
            f"{policy_name}: "
            f"mean_return={summary['mean_episode_return']:.2f}, "
            f"mean_queue_age={summary['mean_observed_queue_age_ticks']:.2f}, "
            f"starvation_steps={summary['mean_starvation_steps']:.2f}"
        )
        for profile_name, profile_summary in result["by_profile"].items():
            print(
                f"  {profile_name}: "
                f"mean_return={profile_summary['mean_episode_return']:.2f}, "
                f"mean_queue_age="
                f"{profile_summary['mean_observed_queue_age_ticks']:.2f}"
            )

