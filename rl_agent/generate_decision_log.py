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

from stable_baselines3 import DQN

sys.path.insert(0, os.path.dirname(__file__))
from scheduler_env import SchedulerEnv  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "explainability"))
from explainer import create_client, explain_decision  # noqa: E402


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
    provider = os.environ.get("EXPLANATION_PROVIDER", "offline").strip().lower()

    # Keep the log useful when no provider is configured or a cloud request
    # fails. The simulator decisions are the primary run output.
    action_names = {
        0: "no change",
        1: "switch to Round Robin",
        2: "switch to Priority Scheduling",
        3: "switch to MLFQ",
        4: "boost the longest-waiting process's priority",
    }
    client = None
    explanation_status = "not_configured"
    if provider not in {"offline", "gemini", "claude"}:
        explanation_status = "unavailable"
        print("EXPLANATION_PROVIDER must be offline, gemini, or claude; saving decisions without explanations.")
        provider = "offline"
    elif provider != "offline":
        try:
            client = create_client(provider)
            explanation_status = "available"
        except EnvironmentError as exc:
            print(f"{exc} Saving decisions without explanations.")
        except Exception as exc:
            explanation_status = "unavailable"
            print(f"{provider.title()} explanations unavailable ({type(exc).__name__}); saving decisions without them.")

    log = []
    for decision in decisions:
        action_name = action_names[decision["action"]]
        explanation = None
        entry_status = explanation_status
        error_message = None
        if client is not None:
            try:
                explanation = explain_decision(
                    decision["state"], decision["action"], client, provider=provider
                )
                entry_status = "available"
            except Exception as exc:
                entry_status = "unavailable"
                error_message = f"{provider.title()} request failed ({type(exc).__name__})."
                print(f"[t={decision['state']['time']}] {provider.title()} explanation unavailable; keeping the decision.")

        entry = {
            "state": decision["state"],
            "action": decision["action"],
            "action_name": action_name,
            "explanation": explanation,
            "explanation_status": entry_status,
        }
        if error_message:
            entry["explanation_error"] = error_message
        log.append(entry)
        if explanation:
            print(f"[t={decision['state']['time']}] {action_name}: {explanation}")

    if client is None:
        print("No cloud explanation client is active — saved decisions without explanations.")

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
