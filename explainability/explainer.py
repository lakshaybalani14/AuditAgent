"""
explainer.py — Given one state + one action from the RL agent, calls
the Anthropic API and returns a plain-English explanation.

No training, no ML — this file is entirely prompt design and API
plumbing.

Run from the project root:
    ANTHROPIC_API_KEY=sk-... python -m explainability.explainer
"""

import json
import os
import random

import anthropic

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


def explain_decision(state, action, client):
    prompt = build_prompt(state, action)
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    # A response can contain multiple content blocks — filter by type
    # rather than assuming position.
    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "".join(text_blocks).strip()


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


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Export it before running this script, "
            "e.g.: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)
    decisions = generate_fake_decisions(n=5)

    log = []
    for d in decisions:
        explanation = explain_decision(d["state"], d["action"], client)
        entry = {
            "state": d["state"],
            "action": d["action"],
            "action_name": ACTION_NAMES[d["action"]],
            "explanation": explanation,
        }
        log.append(entry)
        print(f"[t={d['state']['time']}] {ACTION_NAMES[d['action']]}: {explanation}")

    with open("decision_log.json", "w") as f:
        json.dump(log, f, indent=2)
    print(f"\nWrote {len(log)} decisions to decision_log.json")


if __name__ == "__main__":
    main()
