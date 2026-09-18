# Agentic Adaptive Process Scheduler — Project Writeup

_Fill this in progressively as the project develops, not all at once at
the end._

## 1. Problem Statement

- What problem does this project solve?
- Why is scheduling a good fit for an RL + LLM-explainability approach?

## 2. Architecture

- High-level system diagram (link to the C4-style diagram here).
- Four tiers: Presentation (dashboard), Data Store (decision_log.json),
  Intelligence (RL agent + Claude explainer), Simulation (OS scheduler
  core).
- Data flow: simulator → RL agent → decision → Claude explanation →
  decision_log.json → dashboard.

## 3. Component Design Decisions

### 3.1 Simulator (`simulator/`)
- Why three algorithms (Round Robin, Priority, MLFQ)?
- Why is Priority Scheduling intentionally non-starvation-safe?

### 3.2 RL Agent (`rl_agent/`)
- Why DQN over other algorithms?
- State/action space design rationale.
- Reward function design and any iterations made on it.

### 3.3 Explainability Layer (`explainability/`)
- Prompt design choices.
- Why Claude, and how the explanation is used to build trust/interpretability
  into an otherwise opaque RL policy.

### 3.4 Dashboard (`dashboard/`)
- Why Next.js.
- UI/UX decisions.

## 4. Training Results

- Reward curve over training (paste plot or numbers).
- Before/after avg wait time comparison across algorithms.
- Example of the agent recovering from a starvation scenario.

## 5. Example Explanations

- Paste 3-5 real entries from `decision_log.json`, including the state,
  action, and Claude's explanation.

## 6. Challenges & Learnings

- What was hard? What would you do differently?

## 7. Team Contributions

- Person A (simulator):
- Person B (RL agent):
- Person C (explainability + dashboard + docs):
