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
from collections import Counter

from stable_baselines3 import DQN

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_env import SchedulerEnv  # noqa: E402
from workload_profiles import normalize_workload_profiles  # noqa: E402


def _mean(values):
    return statistics.mean(values) if values else 0.0


def _stddev(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


ACTION_NAMES = {
    0: "no_change",
    1: "round_robin",
    2: "priority",
    3: "mlfq",
    4: "boost_longest_waiting",
}


def _percentile_95(values):
    """Return the nearest-rank 95th percentile, or zero for no observations."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, (95 * len(ordered) + 99) // 100 - 1)
    return float(ordered[index])


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
    action_counts = Counter()
    terminated = False
    steps = 0

    while not terminated and steps < max_steps:
        action = int(action_for_step(observation, steps))
        if action not in ACTION_NAMES:
            raise ValueError(f"Policy selected unknown action: {action}")
        action_counts[ACTION_NAMES[action]] += 1
        observation, reward, terminated, truncated, info = env.step(action)
        total_reward += float(reward)
        steps += 1

        state = env.sim.get_state_summary()
        queue_age_samples.append(float(state["avg_wait_time"]))
        max_queue_age_samples.append(float(state["max_wait_time"]))
        starvation_steps += int(bool(state["is_starving"]))

        if truncated:
            break

    completed = env.sim.completed
    waiting_times = [process.waiting_time for process in completed]
    turnaround_times = [process.turnaround_time for process in completed]
    response_times = [process.response_time for process in completed]
    elapsed_time = env.sim.time
    processes_seen = (
        list(completed)
        + list(env.sim.pending)
        + list(env.sim.ready_queue)
        + [event[2] for event in env.sim.blocked]
    )
    if env.sim.running_process is not None:
        processes_seen.append(env.sim.running_process)

    return {
        "policy": policy_name,
        "workload_profile": workload_profile,
        "seed": seed,
        "episode_return": total_reward,
        "episode_steps": steps,
        "mean_observed_queue_age_ticks": _mean(queue_age_samples),
        "max_observed_queue_age_ticks": max(max_queue_age_samples, default=0.0),
        "starvation_steps": starvation_steps,
        "processes_completed": len(completed),
        "process_completion_rate": (
            len(completed) / env.max_processes if env.max_processes else 0.0
        ),
        "mean_process_waiting_time_ticks": _mean(waiting_times),
        "p95_process_waiting_time_ticks": _percentile_95(waiting_times),
        "mean_process_turnaround_time_ticks": _mean(turnaround_times),
        "mean_process_response_time_ticks": _mean(response_times),
        "throughput_processes_per_tick": (
            len(completed) / elapsed_time if elapsed_time else 0.0
        ),
        "cpu_utilization": (
            sum(process.cpu_execution_time for process in processes_seen) / elapsed_time
            if elapsed_time else 0.0
        ),
        "action_counts": {
            name: action_counts.get(name, 0) for name in ACTION_NAMES.values()
        },
        "episode_terminated": bool(terminated),
        "hit_step_limit": not terminated and steps >= max_steps,
    }


def summarize_runs(runs):
    action_counts = Counter()
    for run in runs:
        action_counts.update(run.get("action_counts", {}))
    total_actions = sum(action_counts.values())
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
        "mean_process_completion_rate": _mean(
            [run.get("process_completion_rate", 0.0) for run in runs]
        ),
        "mean_process_waiting_time_ticks": _mean(
            [run.get("mean_process_waiting_time_ticks", 0.0) for run in runs]
        ),
        "mean_p95_process_waiting_time_ticks": _mean(
            [run.get("p95_process_waiting_time_ticks", 0.0) for run in runs]
        ),
        "mean_process_turnaround_time_ticks": _mean(
            [run.get("mean_process_turnaround_time_ticks", 0.0) for run in runs]
        ),
        "mean_process_response_time_ticks": _mean(
            [run.get("mean_process_response_time_ticks", 0.0) for run in runs]
        ),
        "mean_throughput_processes_per_tick": _mean(
            [run.get("throughput_processes_per_tick", 0.0) for run in runs]
        ),
        "mean_cpu_utilization": _mean(
            [run.get("cpu_utilization", 0.0) for run in runs]
        ),
        "action_counts": {
            name: action_counts.get(name, 0) for name in ACTION_NAMES.values()
        },
        "action_fractions": {
            name: action_counts.get(name, 0) / total_actions if total_actions else 0.0
            for name in ACTION_NAMES.values()
        },
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
            "Completed-process waiting time is accumulated while READY; turnaround "
            "includes CPU and I/O time. CPU utilization uses simulated time from 0."
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

