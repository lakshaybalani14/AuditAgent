# AuditAgent Scheduler Demo Guide

## What the prototype does

AuditAgent is a **scheduler controller in a simulated operating system**. It
does not yet control a real computer's CPU. The simulator creates fake process
workloads, runs the scheduling policies, and lets a trained DQN agent choose a
policy or intervention while the simulation advances.

## How the pieces connect

1. **Workload profiles** create repeatable kinds of process mixes, such as
   CPU-heavy, I/O-heavy, short-job-heavy, and bursty arrivals. A seed lets the
   same workload be recreated for a fair comparison.
2. **The simulator** moves processes through arrival, ready, running, blocked
   for I/O, and completed states. It implements Round Robin, Priority, and
   MLFQ as fixed scheduling policies.
3. **The Gymnasium environment** translates simulator state into 20 normalized
   values for the agent. The agent chooses among five actions: keep the current
   policy, select Round Robin, select Priority, select MLFQ, or boost the
   longest-waiting process.
4. **DQN training** tries these actions in many simulated steps. Its reward
   penalizes READY-queue waiting, changing policies, and starvation. The saved
   `best_model.zip` is selected using separate validation workloads.
5. **Evaluation** runs the saved DQN and all three fixed policies on matched
   seeded workloads. It reports waiting time, P95 wait, response and turnaround
   time, completion, throughput, CPU utilization, and starvation.
6. **Live decision generation** loads the selected checkpoint, creates a seeded
   process workload, asks the DQN for one action, applies that action in the
   simulator, and records the process list before and after the step. This
   repeats across episodes until the demo has 15 decisions. The dashboard can
   ask Gemini or Claude to explain each recorded state/action after the DQN
   acts. That text is post-decision commentary, not the DQN's internal
   reasoning and not part of the training reward.
7. **The Next.js dashboard** streams progress from the Python process and
   refreshes the action timeline and per-process table while the run advances.
   It also displays the selected checkpoint, the exact action, simulator time,
   current scheduler, process state, and explanation-provider status.

## Dashboard sections

- **Experiment / Run configuration:** says which report, model, workload
  profiles, seed range, process count, and evaluation time are being shown.
- **Held-out policy comparison:** compares DQN with Round Robin, Priority, and
  MLFQ. Lower wait and response times are better; higher completion,
  throughput, and CPU use are generally better. Read starvation alongside
  average wait so a low average does not hide a process left waiting too long.
- **By workload profile:** shows where the policies behave differently. A
  model may help on short jobs and struggle on long CPU jobs, so one overall
  average is not the whole story.
- **Metric cards and Live simulator state:** show the latest simulated queue
  and process snapshot after the DQN's most recent action. These are simulated
  processes, not processes from the host operating system.
- **Decision timeline:** records the state the DQN observed, the action it
  actually selected, the reward returned for that step, and the resulting
  process snapshot. Expand an entry to see the exact 20 normalized values fed
  to the network and its Q-value estimate for each possible action.
- **Run live simulation:** advances a fresh seeded workload using the selected
  saved model and publishes decisions as they happen. It does not retrain the
  model; training remains a separate command.
- **Gemini status:** indicates whether Gemini is configured. Gemini text is
  generated after the DQN action from that action and its observed state; it
  explains the decision but does not choose it.

## How to explain one live decision

Point to one timeline entry and walk through this sequence:

1. The process table is the simulator's workload. It shows process state,
   remaining CPU time, waiting time, and priority.
2. The DQN receives the 20 normalized features listed under **Exact 20-feature
   input**. The raw process rows are the simulator evidence; the feature values
   are the actual numbers presented to the neural network.
3. The network estimates a Q-value for each of its five actions. A Q-value is
   an estimate of future reward, not a probability or a guarantee. The action
   highlighted in the timeline is the one the deterministic policy selected
   from those values.
4. The simulator applies that action, advances CPU/I/O/process events, and
   publishes the after-state and reward. Training uses rewards to adjust the
   network over many episodes; clicking the dashboard button only runs the
   saved model and does not train it.
5. If enabled, Gemini receives the recorded observation and action values and
   writes a short explanation afterward. It does not select the action.

## Current local defaults

The dashboard chooses `runs/dqn-learning-v2-seed-42/best_model.zip` when it is
present. It looks for an `evaluation.json` beside that model. Every live run
gets its own `runs/live-simulator/decision_log.generated.live-<run-id>.json` file, so the original
sample log and earlier runs remain available. A small ignored pointer in
`.dashboard-data/` selects the latest run for the dashboard. You can override
the model and evaluation report before starting Next.js:

```powershell
$env:SCHEDULER_MODEL_PATH = "runs/dqn-learning-v2-seed-123-switch-1/best_model.zip"
$env:SCHEDULER_EVALUATION_PATH = "runs/dqn-learning-v2-seed-123-switch-1/evaluation-seed-50000.json"
$env:SCHEDULER_DECISION_LOG_PATH = "decision_log.generated.json"
```

The dashboard automatically uses `.venv/Scripts/python.exe` on Windows or
`.venv/bin/python` on Linux/macOS. An explicit `PYTHON` environment variable
overrides that choice.

Start it with one Next.js server at a time. From the repository root:

```powershell
cd dashboard
npm run dev
```

Open the local URL printed by Next.js. If port 3000 is busy, Next.js may choose
3001 or another port. **Run live simulation** writes to a unique file based on
the configured decision-log path; it does not overwrite the original sample
log or an earlier run.

If Gemini is configured, the simulator first saves all 15 DQN decisions, then
asks Gemini for one short explanation per decision. To enable it, put the following in the ignored
`dashboard/.env.local` file and restart the dashboard:

```dotenv
EXPLANATION_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash
GEMINI_TIMEOUT_MS=15000
```

Keep the key in that local file or your environment; do not put it in source
control or chat. The timeout is in milliseconds. The dashboard's configured
badge only checks that a key is present; the Decision log shows whether each
request actually succeeded. Without the key, the DQN simulation still runs.

The current default seed-42 report contains 30 episodes for each of seven
profiles, or 210 matched workload episodes per policy. It reports DQN mean
wait of 53.83 ticks versus 57.27 for Round Robin (about 6.0% lower). Priority
has a lower mean wait in this report, 36.83 ticks, while MLFQ has the quickest
mean response time, 2.49 ticks versus DQN's 8.15. All four policies completed
all processes. This is a trade-off, not a claim that DQN wins every metric.
State this report's episode count and seed range when presenting it; don't mix
this 210-episode report with multi-seed aggregate results.

## A short presentation script

> “The simulator generates repeatable workloads, and three traditional
> schedulers provide baselines. Our DQN watches a summary of the queue and can
> switch policies or boost the longest-waiting process. We train it to reduce
> waiting while discouraging excessive switching and starvation. The report
> tests the learned controller and each baseline on the same seeded workloads.
> The dashboard shows both the measured results and the actions the model took.
> This is a working simulator prototype; real operating-system integration is
> future work.”

When presenting a percentage improvement, state the metric, workload set,
episode count, and baseline. The DQN is not expected to win every metric or
every workload. Report the measured trade-offs from the displayed evaluation,
not just the average waiting time.
