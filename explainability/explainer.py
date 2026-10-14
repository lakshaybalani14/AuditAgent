"""
explainer.py — Explain one scheduler decision with Gemini or Claude.

No training, no ML — this file is entirely prompt design and API
plumbing.

Run from the project root:
    python -m explainability.explainer                         # offline preview
    GEMINI_API_KEY=... python -m explainability.explainer --provider gemini
"""

import argparse
import json
import os
import random
from pathlib import Path

# Must match SimulatorCore.apply_action's meanings exactly.
ACTION_NAMES = {
    0: "no change",
    1: "switch to Round Robin",
    2: "switch to Priority Scheduling",
    3: "switch to MLFQ",
    4: "boost the longest-waiting process's priority",
}


def build_prompt(state, action):
    action_name = ACTION_NAMES[action]
    return (
        "You are explaining the decisions of a reinforcement-learning agent "
        "that manages an operating system's process scheduler.\n\n"
        "Current system state:\n"
        f"- time: {state['time']}\n"
        f"- queue_length: {state['queue_length']}\n"
        f"- avg_wait_time: {state['avg_wait_time']}\n"
        f"- max_wait_time: {state['max_wait_time']}\n"
        f"- num_io_bound: {state['num_io_bound']}\n"
        f"- num_cpu_bound: {state['num_cpu_bound']}\n"
        f"- current_algo (0=Round Robin, 1=Priority, 2=MLFQ): {state['current_algo']}\n"
        f"- is_starving: {state['is_starving']}\n\n"
        f"The agent chose to: {action_name}.\n\n"
        "In 1-2 sentences, explain why this action makes sense given these "
        "specific numbers. If the action looks questionable given the state, "
        "say so honestly rather than rationalizing it."
    )


def explain_decision(state, action, client, provider="gemini"):
    prompt = build_prompt(state, action)
    if provider == "gemini":
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=prompt,
        )
        explanation = (response.text or "").strip()
    elif provider == "claude":
        response = client.messages.create(
            model=os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text_blocks = [block.text for block in response.content if block.type == "text"]
        explanation = "".join(text_blocks).strip()
    else:
        raise ValueError(f"Unsupported explanation provider: {provider}")

    if not explanation:
        raise ValueError("The explanation provider returned an empty response.")
    return explanation


def create_client(provider):
    """Create an explicitly requested provider client; never auto-select a paid API."""
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY is required when --provider gemini is selected.")
        from google import genai

        return genai.Client(api_key=api_key)
    if provider == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is required when --provider claude is selected.")
        import anthropic

        return anthropic.Anthropic(api_key=api_key)
    if provider == "offline":
        return None
    raise ValueError(f"Unsupported explanation provider: {provider}")


def generate_fake_decisions(n=5):
    """Random (state, action) pairs matching get_state_summary()'s exact
    shape, so the explainability layer can be built and tested before
    the RL agent has finished training."""
    decisions = []
    for _ in range(n):
        queue_length = random.randint(0, 10)
        max_wait = random.randint(0, 60)
        state = {
            "time": random.randint(0, 200),
            "queue_length": queue_length,
            "avg_wait_time": round(random.uniform(0, max_wait), 1),
            "max_wait_time": max_wait,
            "num_io_bound": random.randint(0, queue_length),
            "num_cpu_bound": queue_length,
            "current_algo": random.randint(0, 2),
            "is_starving": max_wait > 50,
        }
        state["num_cpu_bound"] = max(0, queue_length - state["num_io_bound"])
        action = random.randint(0, 4)
        decisions.append({"state": state, "action": action})
    return decisions


def build_decision_log(n=5, client=None, provider="offline"):
    """Build sample entries and optionally request explanations from a provider."""
    decisions = generate_fake_decisions(n=n)

    log = []
    for d in decisions:
        entry = {
            "state": d["state"],
            "action": d["action"],
            "action_name": ACTION_NAMES[d["action"]],
            "source": "sample_preview",
            "explanation": None,
            "explanation_status": "not_configured",
        }
        if client is not None:
            try:
                entry["explanation"] = explain_decision(
                    d["state"], d["action"], client, provider=provider
                )
                entry["explanation_status"] = "available"
            except Exception as error:
                entry["explanation_status"] = "unavailable"
                entry["explanation_error"] = f"{provider.title()} request failed ({type(error).__name__})."
        log.append(entry)
        if entry["explanation"]:
            print(f"[t={d['state']['time']}] {ACTION_NAMES[d['action']]}: {entry['explanation']}")
        elif entry["explanation_status"] == "unavailable":
            print(f"[t={d['state']['time']}] {provider.title()} explanation unavailable; keeping the decision.")

    return log


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create sample decision entries to preview the dashboard explanation flow."
    )
    parser.add_argument(
        "--output",
        default="decision_log.explanation-preview.json",
        help="Output path (default: decision_log.explanation-preview.json; separate from the live decision log).",
    )
    parser.add_argument("--decisions", type=int, default=5, help="Number of sample decisions (default: 5).")
    parser.add_argument(
        "--provider",
        choices=("offline", "gemini", "claude"),
        default="offline",
        help="Explanation provider. Offline is the safe default; cloud providers may consume API credits.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing the selected output file.",
    )
    args = parser.parse_args()
    if args.decisions < 1:
        parser.error("--decisions must be at least 1")
    return args


def main(output_path="decision_log.explanation-preview.json", n=5, provider="offline", force=False):
    output = Path(output_path)
    if output.exists() and not force:
        raise FileExistsError(
            f"{output} already exists. Choose another --output path or pass --force to replace it."
        )

    client = create_client(provider)

    log = build_decision_log(n=n, client=client, provider=provider)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w" if force else "x", encoding="utf-8") as output_file:
        json.dump(log, output_file, indent=2)
    print(f"\nWrote {len(log)} sample decisions to {output}")


if __name__ == "__main__":
    args = parse_args()
    main(
        output_path=args.output,
        n=args.decisions,
        provider=args.provider,
        force=args.force,
    )
