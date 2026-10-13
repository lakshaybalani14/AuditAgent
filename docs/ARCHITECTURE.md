# AuditAgent Architecture

## Purpose and scope

AuditAgent is a research and learning prototype for adaptive CPU scheduling. It simulates processes, lets a reinforcement-learning policy choose scheduler actions, records decisions, optionally generates natural-language explanations, and displays a saved run in a web dashboard.

The current repository is a Python simulation. It does not replace or modify a Linux, Windows, or other operating-system kernel scheduler. Any future kernel integration is a separate project phase.

## Current system flow

```text
Synthetic process batch
        |
        v
SimulatorCore <---- Gymnasium SchedulerEnv <---- Stable-Baselines3 DQN
        |                         |                         |
        +---- state/action ------>+---- reward/next state <-+
                                  |
                                  v
                       generate_decision_log.py
                                  |
                                  v
                         decision_log.json
                          /             \
             optional Anthropic API     Next.js API route
                 explanation                  |
                                              v
                                      React dashboard
```

Training and dashboard display are separate runs today. The dashboard reads a JSON file; it is not connected to a running training process or simulator stream.

## Components

### Simulator: `simulator/`

- `process.py` defines a process with arrival time, CPU burst, remaining time, priority, and an I/O-bound flag.
- `scheduler_algorithms.py` contains standalone run-to-completion implementations for Round Robin, non-preemptive Priority, and MLFQ.
- `simulator_core.py` provides a step interface for the RL environment: it holds ready, pending, and completed processes, emits a state summary, applies actions, and advances execution.

The standalone algorithms and the step simulator are separate implementations. Their behavior must be kept consistent. At the reviewed revision, the step simulator does not implement distinct MLFQ levels; its MLFQ mode behaves like its fixed-quantum queue. The I/O-bound flag also does not yet cause blocking or I/O completion events.

### RL: `rl_agent/`

- `scheduler_env.py` wraps `SimulatorCore` in Gymnasium's reset/step API.
- `train.py` trains a DQN and saves `trained_model.zip` (ignored by Git).
- `generate_decision_log.py` loads a saved model, runs it deterministically over newly generated episodes, and writes state/action records.

The DQN learns from reward through simulated interaction. Workload traces are intended to define realistic scenarios and evaluation inputs; they do not automatically provide action labels.

### Explanations: `explainability/`

`explainer.py` sends a state and selected action to Anthropic's API and returns text. It is an optional, post-decision explanation step. Claude does not select actions, update the DQN, or provide training labels in the current design.

### Dashboard: `dashboard/`

The Next.js API route reads `decision_log.json`; the React page displays the latest saved state and the decision feed. Refresh is manual or page-load based. The current UI is a run viewer, not a live monitor.

### Data and documentation

- `decision_log.json` and `decision_log_real_demo.json` are example data.
- `docs/writeup.md` contains project narrative and results that should be treated as unverified until reproduced by the evaluation workflow.
- The README is the existing project build specification and is intentionally not replaced by this architecture guide.

## Shared contracts

Keep these contracts synchronized across the simulator, environment, logger, explainer, and dashboard.

### State summary

```json
{
  "time": 0,
  "queue_length": 0,
  "avg_wait_time": 0.0,
  "max_wait_time": 0.0,
  "num_io_bound": 0,
  "num_cpu_bound": 0,
  "current_algo": 0,
  "is_starving": false
}
```

In the current implementation, the wait metrics in a state summary describe time spent in the ready queue since a process most recently entered it. They are not the same as each completed process's total waiting time. The state omits details such as pending arrivals, per-process burst remainder, and MLFQ level.

### Action IDs and scheduler IDs

| Value | Action meaning |
|---:|---|
| 0 | Keep the current scheduler |
| 1 | Switch to Round Robin |
| 2 | Switch to Priority |
| 3 | Switch to MLFQ |
| 4 | Boost the priority of the longest-waiting ready process |

The `current_algo` state field uses a different, zero-based mapping: 0 = Round Robin, 1 = Priority, 2 = MLFQ. Do not interpret that field as an action ID.

### Decision log

The dashboard and explainer consume records shaped like:

```json
{
  "state": {},
  "action": 0,
  "action_name": "no change",
  "explanation": null
}
```

Treat `explanation` as optional. A log without Anthropic credentials should still render.

## Target architecture milestones

1. Make the step simulator the single source of truth for each scheduling policy.
2. Add realistic process states, I/O blocking, deterministic seeds, and trace-driven workloads.
3. Train and evaluate policies against classical baselines on identical held-out workloads.
4. Store run metadata and metrics with decision logs.
5. Connect the dashboard to a run API or event stream, while retaining a saved-run mode.
6. Consider real kernel integration only after the simulator results are validated and the scope is explicitly redefined.
