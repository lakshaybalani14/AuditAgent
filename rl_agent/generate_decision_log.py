"""
generate_decision_log.py — Runs a trained DQN model through
SchedulerEnv, greedily picking actions, and logs each (state, action)
pair. This replaces explainer.py's generate_fake_decisions() as the
source of real decisions once a model has been trained.

Run from the project root:
    python -m rl_agent.generate_decision_log
    python -m rl_agent.generate_decision_log --model-path runs/experiment-1/trained_model.zip

Writes decision_log.json directly (with action + action_name, no
explanation) if run standalone. If ANTHROPIC_API_KEY is set, it instead
hands the decisions to explainability/explainer.py so the log includes
real Claude explanations — this is the recommended path for the final
demo.
"""

import argparse
import json
import os
import sys

from stable_baselines3 import DQN

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_env import SchedulerEnv  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "explainability"))


def generate_real_decisions(model_path="trained_model", max_processes=10, n=15):
    """Runs one or more episodes of the trained model, greedily picking
    actions, and collects up to n (state, action) pairs — the same
    shape generate_fake_decisions() in explainer.py produces."""
    model = DQN.load(model_path)
    env = SchedulerEnv(max_processes=max_processes)

    decisions = []
    try:
        while len(decisions) < n:
            obs, info = env.reset()
            terminated = truncated = False
            while not (terminated or truncated) and len(decisions) < n:
                action, _ = model.predict(obs, deterministic=True)
                action = int(action)
                state = env.sim.get_state_summary()
                decisions.append({"state": state, "action": action})
                obs, reward, terminated, truncated, info = env.step(action)
    finally:
        env.close()

    return decisions


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
    args = parser.parse_args()
    if args.max_processes < 1:
        parser.error("--max-processes must be at least 1")
    if args.decisions < 1:
        parser.error("--decisions must be at least 1")
    return args


def main(model_path="trained_model", max_processes=10, n=15):
    decisions = generate_real_decisions(
        model_path=model_path, max_processes=max_processes, n=n
    )
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if api_key:
        import anthropic
        from explainer import ACTION_NAMES, explain_decision

        client = anthropic.Anthropic(api_key=api_key)
        log = []
        for d in decisions:
            explanation = explain_decision(d["state"], d["action"], client)
            log.append(
                {
                    "state": d["state"],
                    "action": d["action"],
                    "action_name": ACTION_NAMES[d["action"]],
                    "explanation": explanation,
                }
            )
            print(f"[t={d['state']['time']}] {ACTION_NAMES[d['action']]}: {explanation}")
    else:
        # ACTION_NAMES duplicated here so this script still works without
        # anthropic installed / no API key set.
        action_names = {
            0: "no change",
            1: "switch to Round Robin",
            2: "switch to Priority Scheduling",
            3: "switch to MLFQ",
            4: "boost the longest-waiting process's priority",
        }
        log = [
            {
                "state": d["state"],
                "action": d["action"],
                "action_name": action_names[d["action"]],
                "explanation": None,
            }
            for d in decisions
        ]
        print(
            "ANTHROPIC_API_KEY not set — wrote decisions without explanations. "
            "Set the key and re-run, or run explainability/explainer.py separately, "
            "to populate the 'explanation' field."
        )

    with open("decision_log.json", "w") as f:
        json.dump(log, f, indent=2)
    print(f"Wrote {len(log)} decisions to decision_log.json")


if __name__ == "__main__":
    args = parse_args()
    main(
        model_path=args.model_path,
        max_processes=args.max_processes,
        n=args.decisions,
    )
