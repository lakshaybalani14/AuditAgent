# AuditAgent Adaptive Scheduler: Model and Evaluation Guide

**Purpose:** Explain what the trained scheduler does, how it was trained, what the evaluation numbers mean, and where it improved or regressed against the fixed schedulers.

**Scope:** These results come from AuditAgent's synthetic process simulator. They demonstrate a working reinforcement-learning prototype inside that simulator. They do not establish performance in a real operating-system kernel or on real user workloads.

## Summary for a demo

AuditAgent's DQN model observes process and queue conditions and chooses a scheduling action as the simulation runs. It can keep the current scheduler, select Round Robin, Priority, or MLFQ, or boost the longest-waiting process.

Two separately trained DQN checkpoints are worth showing because they make different tradeoffs:

- **Seed 42 checkpoint:** lowest average waiting time among the two DQN models. Across the held-out tests it lowered average wait by **6.5%** and turnaround by **5.5%** versus Round Robin. It had one brief starvation-threshold event, and its response time and long-wait P95 were worse than Round Robin.
- **Seed 123, switch penalty 1 checkpoint:** steadier results. It lowered average wait by **1.6%**, response time by **2.2%**, and turnaround by **1.3%** versus Round Robin, with **zero starvation episodes in 630 tests**. Its P95 waiting time was **2.7% higher** than Round Robin.

There is no single winner on every measure. Priority has the lowest average wait, but crossed the starvation threshold in 359 of 630 episodes. MLFQ has the quickest response time. Round Robin has the lowest average episode-level P95 wait. The DQN models offer different compromises among those goals.

## What the model is

DQN means **Deep Q-Network**. It is a reinforcement-learning method: the agent tries actions in the simulator, receives a score called a reward, and updates a neural network so it can estimate which actions are likely to lead to better future rewards.

At each simulation step, the agent receives a 20-value summary of the current situation. In everyday terms, these values describe:

- how many processes are finished, waiting to arrive, ready for CPU time, blocked on I/O, or running;
- how long ready processes have waited and how much work they have left;
- whether ready work is I/O-heavy and what its priorities look like; and
- which scheduling policy is currently active.

The agent chooses one of five actions:

1. keep the current scheduler;
2. use Round Robin;
3. use Priority;
4. use MLFQ; or
5. boost the priority of the longest-waiting process.

This makes the DQN a **scheduler controller**: it chooses or changes the scheduling strategy based on the simulator state. It does not directly choose every CPU instruction.

### What the reward teaches

The reward at each step is:

- a penalty for new time spent waiting in the READY queue;
- a penalty when the selected scheduling strategy changes; and
- a larger penalty when the oldest READY process passes the starvation threshold.

The DQN therefore learns a compromise between reducing queue waiting, avoiding excessive strategy changes, and preventing processes from being left waiting too long. It is not directly rewarded for every metric in the report. For example, response time and P95 waiting time are measured during evaluation, but they are not separate terms in the current reward. That is why a model can improve average waiting while still having a worse response time or P95.

## What the two checkpoints represent

These are **two independent training runs**, not two stages of one model. Both ran for 100,000 simulator steps and started without resuming a previous checkpoint. Their training seeds and scheduler-change penalties differed.

| Checkpoint used in evaluation | Training seed | Training steps | Switch penalty during training | Starvation penalty | Validation-selected checkpoint |
|---|---:|---:|---:|---:|---:|
| Seed 42, best model | 42 | 100,000 | 0.1 | 25 | Step 25,000 |
| Seed 123, switch penalty 1, best model | 123 | 100,000 | 1.0 | 25 | Step 100,000 |

The evaluation reports use each run's **best_model.zip**, selected from validation checkpoints. This is why the seed 42 evaluation uses the checkpoint selected at step 25,000 even though training continued to step 100,000. For seed 123, the selected checkpoint was at step 100,000.

Validation was small: three episodes for each of seven profiles, or 21 episodes at a checkpoint. The separate final comparison used many more episodes, so use the final evaluation results below to describe measured performance.

### What “timestep” and “seed” mean

- A **timestep** is one interaction between the agent and simulator. It is not one whole workload or one training episode. The 100,000 training timesteps contain many episodes.
- A **training seed** (42 or 123) initializes the separate run's randomness, including DQN initialization and workload generation. It is not a score or a level.
- The **evaluation seeds** (30,000, 40,000, and 50,000) choose repeatable test workloads. Each scheduler was tested on the same profile and episode seeds, making the comparisons matched.

## Evaluation setup

Each report evaluates four policies: the DQN checkpoint, Round Robin, Priority, and MLFQ.

- Seven synthetic workload profiles: legacy random, light load, bursty arrivals, CPU-heavy, short-job-heavy, I/O-heavy, and long-job-heavy.
- 30 episodes per profile for each test seed.
- Three test seed ranges: 30,000, 40,000, and 50,000.
- **630 episodes per policy per checkpoint**: 30 × 7 × 3.
- Up to 10 processes per episode.
- The evaluation used a switch penalty of 1.0 and starvation penalty of 25 for every policy.

The evaluation report says each policy uses the same generated episode seeds within a comparison. This is a fairer comparison than testing each policy on different random workloads.

## What each metric means

All times are simulator ticks. Lower is better for time measurements.

- **Average waiting time:** average time completed processes spent READY and waiting for CPU time. It excludes time spent blocked on I/O.
- **P95 waiting time:** the report calculates the 95th-percentile wait within each episode, then averages those episode values. It gives a sense of the long waits experienced by the slowest-waiting processes.
- **Response time:** time from a process arriving until it first gets CPU time.
- **Turnaround time:** time from arrival until completion. It includes CPU work and I/O time.
- **Starvation step:** one simulator step where the oldest READY process has waited more than 50 ticks. An episode can have multiple starvation steps.
- **Completion rate:** share of the episode's processes that completed before the episode ended.
- **Throughput:** completed processes per simulator tick.
- **CPU utilization:** share of simulated time when the CPU was busy.
- **Scheduler switches:** changes recorded by the simulator to the active scheduling strategy. This is not the number of CPU context switches.

The simulator completed all processes for every policy in these tests. Priority still crossed the starvation threshold often: completion means every process eventually finished, not that every process received service promptly.

## Results across 630 matched episodes

The table shows the average across the three evaluation seed ranges. The P95 column is the average of the episode-level P95 values described above.

| Policy | Average wait ↓ | Average episode P95 wait ↓ | Response time ↓ | Turnaround ↓ | Starvation episodes / 630 | Starvation steps | Scheduler switches / episode |
|---|---:|---:|---:|---:|---:|---:|---:|
| DQN, seed 42 | **54.39** | 75.35 | 8.18 | **65.11** | 1 | 2 | 5.06 |
| DQN, seed 123 / switch penalty 1 | 57.25 | 74.76 | 5.36 | 67.98 | **0** | **0** | 3.50 |
| Round Robin | 58.17 | **72.82** | 5.48 | 68.89 | **0** | **0** | 0.00 |
| Priority | **37.12** | 76.84 | 33.97 | **47.85** | 359 | 13,284 | 1.00 |
| MLFQ | 58.50 | 75.32 | **2.66** | 69.23 | **0** | **0** | 1.00 |

All policies completed 100% of processes. Average throughput was about **0.155 processes per tick** and average CPU utilization about **94%** for all of them, so the main differences in this experiment were latency and fairness rather than how many processes eventually completed.

### How much better or worse was each DQN checkpoint?

The percentages below compare aggregate means. For time metrics, **lower is better**. A positive “lower” value means the DQN metric was that much lower than the baseline; “higher” means it was that much worse on that metric. Values are rounded.

| DQN checkpoint compared with | Average wait | P95 wait | Response time | Turnaround |
|---|---:|---:|---:|---:|
| Seed 42 vs Round Robin | **6.50% lower** | 3.48% higher | 49.37% higher | **5.49% lower** |
| Seed 42 vs MLFQ | **7.04% lower** | 0.04% higher (effectively tied) | 207.10% higher | **5.95% lower** |
| Seed 42 vs Priority | 46.51% higher | **1.94% lower** | **75.92% lower** | 36.08% higher |
| Seed 123 / switch 1 vs Round Robin | **1.57% lower** | 2.67% higher | **2.16% lower** | **1.33% lower** |
| Seed 123 / switch 1 vs MLFQ | **2.13% lower** | **0.74% lower** | 101.16% higher | **1.80% lower** |
| Seed 123 / switch 1 vs Priority | 54.24% higher | **2.70% lower** | **84.23% lower** | 42.08% higher |

These comparisons show the tradeoffs plainly:

- **Against Round Robin:** both DQN models lowered mean waiting and turnaround. Seed 42 made the larger improvement, while its response time and P95 were worse. The switch-penalty-1 model had a small response-time improvement and no starvation in these tests, with a modest P95 regression.
- **Against MLFQ:** both DQN models lowered mean waiting and turnaround. MLFQ still had much quicker response time. Seed 42's P95 was effectively tied with MLFQ; seed 123's was slightly lower.
- **Against Priority:** Priority had the shortest average wait and turnaround, but its results were unfair: 359 episodes crossed the starvation threshold, accumulating 13,284 starvation steps. Both DQN models had much lower response times and P95 waits, and seed 123 had no starvation episodes. The DQN models did not beat Priority on average wait or turnaround.

A composite episode reward is also recorded. It combines total READY waiting with scheduler-change and starvation penalties, so it is useful for understanding the training objective but should not replace the separate user-facing metrics above. The reports average this reward at approximately -549 for DQN seed 42, -576 for DQN seed 123 / switch 1, -582 for Round Robin, -586 for MLFQ, and -899 for Priority. For this negative reward, closer to zero is better.

## Evidence that the DQN adapts

The seed 123 / switch-penalty-1 report shows different action mixes for different workloads. Across the test episodes:

| Workload | Most common DQN actions |
|---|---|
| Light load | Round Robin 61%; keep current strategy 20% |
| Short-job-heavy | Round Robin 76%; keep current strategy 10% |
| CPU-heavy | MLFQ 49%; Round Robin 22% |
| Long-job-heavy | MLFQ 55%; Round Robin 20% |
| I/O-heavy | Round Robin 43%; MLFQ 37% |

These are action frequencies across decision steps, not a rule that each workload always gets one fixed scheduler. The changing mix is evidence of state-responsive behavior in the simulator. The performance table then measures whether that behavior helps.

## What to say in the demo

> “AuditAgent has a learned scheduler controller that observes the process queue and changes scheduling actions as workload conditions change. We tested two separately trained DQN checkpoints against Round Robin, Priority, and MLFQ on 630 matched synthetic episodes. The seed 42 checkpoint reduced average waiting by 6.5% versus Round Robin, with one brief starvation event and slower response. The switch-penalty-1 checkpoint reduced average waiting by 1.6%, improved response by 2.2%, and had no starvation in those tests. Priority had the lowest average wait but crossed the starvation threshold in 359 episodes; MLFQ gave the fastest response. The prototype demonstrates adaptation and measurable tradeoffs, rather than a scheduler that is best on every metric.”

For a cautious live demo, use **seed 123 / switch penalty 1** as the main DQN checkpoint because it had zero starvation in the held-out tests and modest improvements over Round Robin. Show seed 42 as the alternate checkpoint with a larger average-wait gain and its response-time/P95 tradeoffs.

## Limits and next evaluation standard

- These results are from synthetic simulator profiles, not real operating-system workloads or a production kernel.
- The 630 episodes are repeatable simulator scenarios. No confidence intervals or statistical-significance tests were calculated, so describe the percentage differences as measured results for these runs.
- The model was trained to reduce READY waiting while charging for strategy changes and starvation. If response time or P95 becomes the main product goal, first agree on that objective, then update the reward and rerun the same fixed evaluation protocol.
- Keep test seed ranges separate from training and validation. Compare every future model with all four policies on the same test seeds and report the same metrics.

## Files used

The evaluated model files are runs/dqn-learning-v2-seed-42/best_model.zip and runs/dqn-learning-v2-seed-123-switch-1/best_model.zip.

Evaluation reports:
- [Seed 42, test seed 30,000](C:/Users/laksh/OneDrive/Desktop/AuditAgent-git/runs/dqn-learning-v2-seed-42/evaluation-seed-30000-switch-1.json)
- [Seed 42, test seed 40,000](C:/Users/laksh/OneDrive/Desktop/AuditAgent-git/runs/dqn-learning-v2-seed-42/evaluation-seed-40000-switch-1.json)
- [Seed 42, test seed 50,000](C:/Users/laksh/OneDrive/Desktop/AuditAgent-git/runs/dqn-learning-v2-seed-42/evaluation-seed-50000-switch-1.json)
- [Seed 123 / switch 1, test seed 30,000](C:/Users/laksh/OneDrive/Desktop/AuditAgent-git/runs/dqn-learning-v2-seed-123-switch-1/evaluation-seed-30000.json)
- [Seed 123 / switch 1, test seed 40,000](C:/Users/laksh/OneDrive/Desktop/AuditAgent-git/runs/dqn-learning-v2-seed-123-switch-1/evaluation-seed-40000.json)
- [Seed 123 / switch 1, test seed 50,000](C:/Users/laksh/OneDrive/Desktop/AuditAgent-git/runs/dqn-learning-v2-seed-123-switch-1/evaluation-seed-50000.json)

The definitions are implemented in the repository's rl_agent/scheduler_env.py, rl_agent/train.py, rl_agent/evaluate.py, simulator/process.py, and simulator/simulator_core.py.

---

**Interpretation rule:** Present the exact metric, comparison policy, and test scope together. For example: “average waiting was 6.5% lower than Round Robin across 630 matched synthetic episodes.” Avoid saying “6.5% better overall.”
