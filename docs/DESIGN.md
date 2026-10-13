# AuditAgent Design

## Product goal

Demonstrate how an adaptive scheduling policy behaves on explicit workloads, compare it fairly with classical schedulers, and let a reader inspect the state and action behind each result.

The project should be described as a scheduler simulator and evaluation tool. It is not currently an operating-system scheduler.

## Core concepts

- **Arrival time:** when a process becomes eligible to run.
- **CPU burst:** total CPU service the process needs.
- **Ready queue:** processes ready for CPU service.
- **Waiting time:** time a process spends ready but not running. For completed work, total wait can be computed as completion time minus arrival time minus CPU service, if there is no I/O.
- **Turnaround time:** completion time minus arrival time.
- **Response time:** first CPU start minus arrival time.
- **Preemption:** pausing a running process so another process can run.
- **Starvation:** a process waiting unreasonably long while others continue to receive service.
- **Policy:** the scheduler rule that selects which ready process runs next.
- **RL reward:** a numeric training signal. It is not automatically equivalent to the project’s real-world success criteria.

## Scheduling policies

- **Round Robin:** serves ready processes in rotating order for a time quantum.
- **Priority:** chooses the highest-priority ready process. The standalone implementation is non-preemptive; the step simulator uses quantum-sized service and priority ordering.
- **MLFQ:** uses multiple priority queues. Processes that consume their quantum are demoted; new or interactive processes receive opportunities at higher levels. The current standalone implementation has levels, but the RL step simulator has not yet reproduced that behavior.

These policy descriptions are the target semantics. When code behavior differs, update the simulator and this document together.

## Current RL interface

### Observation

The environment currently sends a seven-number vector:

1. Ready queue length
2. Average ready-queue age
3. Maximum ready-queue age
4. Number of I/O-bound processes in the ready queue
5. Number of CPU-bound processes in the ready queue
6. Current scheduler ID
7. Starvation flag

This is a compact summary, but it hides per-process priority, remaining burst, future arrivals, and MLFQ level. It may therefore be partially observable: two different workloads can produce the same vector but require different actions.

### Actions

| ID | Meaning |
|---:|---|
| 0 | Keep the current scheduler |
| 1 | Switch to Round Robin |
| 2 | Switch to Priority |
| 3 | Switch to MLFQ |
| 4 | Boost priority of the longest-waiting ready process |

The state field `current_algo` is 0 = Round Robin, 1 = Priority, 2 = MLFQ. These IDs are not the same as the action IDs for switching policies.

### Reward

The current reward is:

- `-0.1 × avg_wait_time`
- an additional `-5` when the starvation flag is true
- `+1` when at least one process completes

This is a starting heuristic, not a validated objective. It is computed from the current queue summary and one completion event. It does not directly measure mean completed-job waiting time, turnaround, response time, throughput, context-switch overhead, or fairness. Compare policies using separate outcome metrics and tune the reward only after defining the desired trade-offs.

## Design requirements for the next version

### Simulator correctness

- Use one implementation for the policy semantics used by standalone baselines and the RL environment.
- Model ready, running, blocked-for-I/O, and completed states.
- Define time units and whether an environment step means one CPU tick or one quantum.
- Make arrivals and I/O completion events deterministic under a supplied seed.
- Define priority direction, tie-breaking, preemption, MLFQ demotion/promotion, and starvation prevention.
- Model the cost of switching policies if the agent is allowed to switch frequently.

### Evaluation

Report at least:

- Mean and 95th-percentile waiting time.
- Mean turnaround and response time.
- Throughput and CPU utilization.
- Maximum wait and a starvation count/rate.
- Fairness and results per workload class.

Compare Round Robin, Priority, MLFQ, and DQN on the exact same held-out workloads. Use multiple seeds and report variation, not only the best run. Do not publish percentage-improvement claims until this evaluation can reproduce them.

### Explainability

The explanation service receives a recorded state and chosen action and returns text. The UI should present it as an LLM-generated explanation, alongside the actual measured values. It is not a faithful explanation of the DQN's internal computation. The application should work when the API key is missing or the service fails.

### Dashboard

The dashboard should distinguish:

- A static example log.
- A completed, saved experiment.
- A live simulation, if live event delivery is later implemented.

Show run metadata and scheduler metrics in addition to the decision feed. Avoid presenting a hardcoded status as proof that a model or simulator is online.

## Acceptance criteria for a credible project result

- The step simulator implements distinct, documented policies.
- A fixed seed produces a reproducible workload and outcome.
- A benchmark report compares all baselines and the learned policy on held-out scenarios.
- Each reported metric can be traced to logged process outcomes.
- Dashboard records validate against a versioned schema.
- Documentation separates implemented behavior from planned behavior and measured claims from hypotheses.
