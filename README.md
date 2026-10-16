Warning: truncated output (original token count: 5695)
Total output lines: 459

# Agentic Adaptive Process Scheduler — Build Spec

This README describes every file in this project in enough detail that
it can be used as a prompt/spec to (re)build each one from scratch —
what it must do, what it takes as input, what it must return, and how
it connects to the other files. The actual working implementations
already exist in this repo; this document is the spec they were built
against, kept in sync so it can be handed to a teammate or an AI agent
as a build instruction.

## What this project is

A simulated OS scheduler runs real scheduling algorithms (Round Robin,
Priority Scheduling, Multilevel Feedback Queue) on a stream of fake
processes. A Reinforcement Learning agent watches the live system state
and decides, tick by tick, whether to switch algorithms or intervene
(e.g. boost a starving process's priority) to keep average wait time low
without letting anything starve. Decisions can be sent to Gemini or
Claude for plain-English explanations; cloud use is opt-in and the default
path makes no external API calls. A Next.js dashboard
displays the live queue state and the decision-explanation feed.

## Run the project

From the project root, create the Python environment and install the packages:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the dashboard:

```powershell
cd dashboard
npm install
npm run dev
```

Then open `http://localhost:3000`. The dashboard includes a sample
`decision_log.json` so it has useful content before a model is trained. Run
`python -m rl_agent.train` to train a DQN, then
`python -m rl_agent.generate_decision_log` to replace the sample log with
decisions from the saved model.

For a safe, offline preview of the explanation timeline, run
`python -m explainability.explainer`. It writes random sample decisions to
`decision_log.explanation-preview.json` and never replaces the live log. To show
that preview in the dashboard, start Next.js with
`DASHBOARD_USE_EXPLANATION_PREVIEW=1`. These entries have no cloud response;
they exercise the dashboard's no-key fallback.

To request Gemini explanations for sample decisions, first set
`GEMINI_API_KEY` and then run
`python -m explainability.explainer --provider gemini`. This sends up to five
requests and uses your Gemini API quota. Use `--provider claude` with
`ANTHROPIC_API_KEY` only if you want Claude. The default provider is offline;
an existing output file is not replaced unless `--force` is provided.

While the dashboard is running locally, **Run live simulation** starts a new
15-step simulator run through `POST /api/run`. It uses the saved
`runs/dqn-learning-v2-seed-42/best_model.zip` checkpoint when available, then
checks the seed-123 checkpoint and project-root model paths. Set
`SCHEDULER_MODEL_PATH` before starting Next.js to choose another checkpoint.
The matching report is loaded from that model's run folder; override it with
`SCHEDULER_EVALUATION_PATH` when needed. Fresh dashboard decisions go to
unique `runs/live-simulator/decision_log.generated.live-<run-id>.json` files, preserving both the
sample log and earlier generated runs. `.dashboard-data/active-decision-log.json`
points the dashboard to the latest run. Set `SCHEDULER_DECISION_LOG_PATH` to
choose the directory and filename prefix for those run files. While a run is
active, the timeline polls every 0.8 seconds and the queue panel shows process
states after each actual DQN action. Expanded events include before/after state,
exact 20 normalized inputs and the DQN's estimated Q-value for every action.
On Windows the dashboard
automatically uses `.venv\Scripts\python.exe`;
on Linux/macOS it uses `.venv/bin/python`. `PYTHON` overrides this choice.
The API reports a clear missing-model message when no checkpoint is found.
Each run is saved separately, so failed or partial runs do not overwrite older
logs or model checkpoints. Explanations are optional.
To use Gemini during a real model run, put these entries in the ignored
`dashboard/.env.local` file, then restart Next.js:

```dotenv
EXPLANATION_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash
GEMINI_TIMEOUT_MS=15000
```

The dashboard shows whether Gemini is configured or whether its key is missing;
that badge does not verify that a request will succeed. All 15 DQN decisions
are saved first, then Gemini is called to explain each observed state and
chosen action. The default 15-second request timeout keeps slow explanations
from delaying the simulator. These explanations are post-decision commentary,
not the DQN's internal reasoning. The default `offline` provider makes no cloud API calls. Set
`EXPLANATION_PROVIDER=claude` and `ANTHROPIC_API_KEY` only if your team needs
Claude compatibility.

## Folder structure and ownership

The current repository layout is documented in [docs/REPOSITORY_GUIDE.md](docs/REPOSITORY_GUIDE.md). The main application areas are:

- `simulator/` — process model, scheduling policies, and tick-by-tick simulator.
- `rl_agent/` — Gymnasium environment, training, evaluation, and decision-log generation.
- `dashboard/` — Next.js pages, API routes, UI components, and client-side hooks.
- `explainability/` — optional Gemini and offline decision explanations.
- `tests/` — Python tests for simulator, agent, APIs, and workflow behavior.
- `docs/` — architecture, workflows, training, demo, design, and workload documentation.

Generated checkpoints and experiment outputs belong under the ignored root `runs/` directory. Live simulator decision logs are grouped in `runs/live-simulator/`; active-run metadata remains under `.dashboard-data/`. These runtime paths are intentionally ignored by Git and managed by the application.
---

## `simulator/process.py`

**Purpose:** Defines the `Process` data class. Holds data only — no
scheduling logic.

**Build spec:**
- A `Process` class with constructor args: `pid` (string/int identifier),
  `arrival_time` (int, when it enters the system), `burst_time` (int,
  total CPU time needed), `priority` (int, default 0, lower number =
  higher priority), `is_io_bound` (bool, default False).
- On construction, also set `remaining_time = burst_time` (mutated as
  the process runs), `start_time = None`, `completion_time = None`,
  `waiting_time = 0`, and `last_ready_time = arrival_time` (used to
  compute wait time increments as time passes while queued).
- Method `is_finished()` → `True` if `remaining_time <= 0`.
- `__repr__` should print all key fields for debugging.
- Include a `generate_sample_processes()` helper that returns a fixed
  list of ~4 hand-picked `Process` objects for manual testing (not used
  by the RL environment — testing only).
- A `if __name__ == "__main__":` block that prints the sample processes
  when the file is run directly.

**Expected behavior when run standalone:** prints 4 `Process(...)` reprs
with no errors.

---

## `simulator/scheduler_algorithms.py`

**Purpose:** Implements the three scheduling algorithms as complete,
standalone, run-to-completion functions. This file must work with zero
knowledge of RL, Gym, or Claude — pure OS coursework logic, testable in
isolation.

**Build spec — three functions, each taking `(processes: list[Process], ...)` and returning a stats dict:**

1. `simulate_round_robin(processes, quantum=2, verbose=False)`
   - Give each ready process a CPU slice of at most `quantum`.
   - If not finished after its slice, it goes to the back of the ready
     queue.
   - Must correctly admit newly-arrived processes into the queue as
     simulated time passes, including processes that arrive *while*
     another process is mid-slice.
   - On completion, set `completion_time` and compute
     `waiting_time = completion_time - arrival_time - burst_time`.

2. `simulate_priority_scheduling(processes, verbose=False)`
   - Non-preemptive: always pick the ready process with the lowest
     `priority` number and run it to completion before picking the next.
   - Intentionally does **not** prevent starvation — that's a known,
     deliberate gap the RL agent is meant to later notice and fix.

3. `simulate_mlfq(processes, quantums=(2, 4, 8), verbose=False)`
   - Multiple queues, one per entry in `quantums`, ordered fastest
     (shortest quantum, index 0) to slowest.
   - New arrivals enter queue level 0.
   - Always run from the lowest non-empty queue level first.
   - If a process doesn't finish within its current level's quantum,
     demote it to the next slower level (capped at the last level).

**Shared helper:** `_summarize(completed_processes)` → returns
`{"avg_wait_time": float, "max_wait_time": float, "completed": [...]}`.
Must handle the empty-list case without dividing by zero.

**Also needed:** `_reset_processes(processes)` that deep-copies the
input list, so running the same process list through multiple
algorithms in the same script doesn't leak mutated state between runs.

**Expected behavior when run standalone:** imports
`generate_sample_processes` from `process.py`, runs all three
algorithms with `verbose=True`, and prints a per-tick trace plus final
avg/max wait time for each. Should complete with no exceptions.

---

## `simulator/simulator_core.py`

**Purpose:** The "steppable" version of the scheduler — instead of
running an algorithm start-to-finish like `scheduler_algorithms.py`
does, this class advances **one tick at a time** and can switch which
algorithm is active mid-run. This is the bridge the RL environment
wraps. This is the main Operating-Systems deliverable.

**Build spec:**
- Constants: `ALGO_ROUND_ROBIN = 0`, `ALGO_PRIORITY = 1`, `ALGO_MLFQ = 2`,
  `STARVATION_THRESHOLD = 50` (ticks; tune based on process sizes).
- Class `SimulatorCore(max_processes=10, quantum=2)`:
  - `reset()`: reinitializes…695 tokens truncated…at32)`.
    Instantiates a `SimulatorCore`.
  - `reset()`: calls `self.sim.reset()`, returns `_state_to_array()`.
  - `step(action)`: calls `self.sim.apply_action(action)`, then
    `self.sim.tick()`, then builds `(state_array, reward, done, info)`
    — the mandatory 4-tuple Gym/Stable-Baselines3 expects every call.
    `info` should include at least `avg_wait` and `is_starving` for
    logging/debugging.
  - `_state_to_array()`: packs `get_state_summary()`'s 7 relevant
    fields, in a fixed consistent order, into a `numpy.float32` array:
    `[queue_length, avg_wait_time, max_wait_time, num_io_bound, num_cpu_bound, current_algo, is_starving_as_0_or_1]`.
  - `_compute_reward(state_dict, finished_a_process)`: starting-point
    formula —
    `reward = -0.1 * avg_wait_time`, then `-= 5.0` if `is_starving`
    (must dominate the wait-time term, or the agent will let one
    process starve to lower the average — a known RL failure mode),
    then `+= 1.0` if a process finished this tick (rewards actual
    progress, not just avoiding penalties by stalling). **This is
    expected to be iterated on, not treated as final.**

**Compatibility note to build in:** if the environment for whoever
builds this only has `gymnasium` installed (not classic `gym`), the
import line should become `import gymnasium as gym` — Stable-Baselines3's
current releases expect Gymnasium's API.

**Expected behavior when run standalone:** run one episode with random
actions (`env.action_space.sample()`), print total accumulated reward,
completes with no exceptions.

---

## `rl_agent/train.py`

**Purpose:** Actually trains an RL agent against `SchedulerEnv` using
Stable-Baselines3, and saves the trained model to disk.

**Build spec:**
- Import `SchedulerEnv`, wrap it in `stable_baselines3.common.monitor.Monitor`
  (adds episode-stat tracking Stable-Baselines3's logger uses).
- Use `DQN` ("Deep Q-Network" — a neural-network-based extension of
  Q-learning, needed because the 7-dimensional continuous state space
  is too large for a plain lookup table) with policy `"MlpPolicy"`
  (small feedforward neural net), reasonable defaults:
  `learning_rate=1e-3`, `buffer_size=50_000`, `verbose=1`.
- Include a custom `BaseCallback` subclass that prints `avg_wait` and
  `is_starving` from the `info` dict every N steps (e.g. every 1000),
  so training progress is visible instead of a silent black box.
- Call `model.learn(total_timesteps=100_000, callback=...)` — flag this
  number as a starting point, likely to need tuning up or down based on
  how quickly the reward curve stabilizes.
- `model.save("trained_model")` at the end.

**Expected behavior when run:** prints periodic progress lines showing
`avg_wait` trending downward over training, ends with
`trained_model.zip` written to disk. (This step needs `stable-baselines3`
installed and meaningful CPU time — it's the one file in this repo not
yet run end-to-end here.)

---

## `explainability/explainer.py`

**Purpose:** Given one state + one action (from the RL agent), optionally calls
the Gemini or Anthropic API and returns a plain-English explanation. No training,
no machine learning — this file is entirely prompt design and API
plumbing.

**Build spec:**
- `ACTION_NAMES` dict mapping the 5 action integers (0–4) to short
  human-readable phrases matching `SimulatorCore.apply_action`'s
  meanings exactly (e.g. `1: "switch to Round Robin"`).
- `build_prompt(state, action)`: formats the state dict's fields
  (time, queue_length, avg_wait_time, max_wait_time, num_io_bound,
  num_cpu_bound, current_algo, is_starving) plus the action's name into
  a prompt that ends with an explicit instruction: explain in 1-2
  sentences why the action makes sense given the specific numbers, and
  say so honestly if the action looks questionable rather than
  rationalizing it. Being specific with exact numbers in the prompt
  produces materially better explanations than vague descriptions.
- `explain_decision(state, action, client, provider)`: uses Google's
  `google-genai` client when `provider="gemini"`, or the Anthropic client
  when `provider="claude"`; rejects empty responses and reports provider
  failures without losing the decision.
- `generate_fake_decisions(n=5)`: produces `n` random
  `{"state": {...}, "action": int}` dicts with plausible random field
  values, matching the exact shape `get_state_summary()` produces. This
  exists so the explainability layer can be built and tested **before**
  the RL agent has finished training — swap this out for a real
  decision log later without changing anything else in the file.
- `main()`: defaults to offline fake decisions and writes them to a
  separate preview file. Cloud use requires an explicit `--provider`
  choice and its corresponding key. The preview file is only read by the
  dashboard when `DASHBOARD_USE_EXPLANATION_PREVIEW=1` is set.

**Expected behavior when run:** with no provider selected, prints that it
wrote five offline sample decisions to `decision_log.explanation-preview.json`.
Selecting `--provider gemini` or `--provider claude` requires that provider's
key and may use its API quota.

---

## `dashboard/pages/api/decisions.js`

**Purpose:** A Next.js API route that serves the newest live decision log,
falling back to the original sample `decision_log.json` before a live run.

**Build spec:**
- Default-exported `handler(req, res)` function (Next.js API route
  convention).
- Reads the latest run path from the ignored `.dashboard-data/` pointer;
  before any live run, it reads the original sample file.
- Parses it as JSON and responds `res.status(200).json(decisions)`.
- Live files are replaced atomically by Python after each decision, so polling
  never reads half-written JSON. If no log exists, the route returns an empty
  array rather than crashing.

---

## `dashboard/components/QueueView.js`

**Purpose:** Displays the latest simulator state plus its individual simulated
processes.

**Build spec:**
- React component `QueueView({ state, decisions })` using the last decision's
  resulting state and process snapshot.
- Shows current scheduling policy, ready queue, wait, process status, remaining
  CPU, waiting time, and priority.
- Displays simulated processes only; it does not inspect host OS processes.

---

## `dashboard/components/DecisionFeed.js`

**Purpose:** Shows the actions the saved DQN actually selected and the model
data behind each action, with optional post-decision Gemini/Claude commentary.

**Build spec:**
- React functional component `DecisionFeed({ decisions })`.
- If `decisions` is empty/undefined, render a placeholder message.
- Otherwise render one event per simulator step. Expand it to see the exact 20
  normalized network inputs, all five Q-values, the chosen action, reward,
  observed processes, and any LLM explanation. Q-values estimate future reward;
  they are not probabilities.

---

## `dashboard/pages/index.js`

**Purpose:** The dashboard's main page — loads the report and current run, then
polls live decisions while the Python simulator runs.

**Build spec:**
- Polls the decision, evaluation, and run APIs every 0.8 seconds during a run
  and every 5 seconds while idle.
- The Run live simulation button launches the selected checkpoint through
  `POST /api/run`; its Python child emits progress after every action.
- Derives `latestState` from the last resulting simulator state and passes the
  full event list to `QueueView`.
- Pass the full `decisions` array to `DecisionFeed`.
- Shows whether Gemini is enabled. The run is independent of Gemini and works
  offline when no API key is configured.

---

## `docs/writeup.md`

**Purpose:** The project documentation deliverable. Not code — a
structured markdown template with section headers to fill in as the
project develops (problem statement, architecture, per-component
design decisions and why they were made, training results, example
explanations, challenges/learnings, team contributions). Should be
written progressively, not left until the end.

---

## Cross-file contracts (do not break these without updating every file listed)

- **State dict shape**, produced by `SimulatorCore.get_state_summary()`,
  consumed by `scheduler_env.py` (`_state_to_array`) and
  `explainer.py` (`build_prompt`):
  `{time, queue_length, avg_wait_time, max_wait_time, num_io_bound, num_cpu_bound, current_algo, is_starving}`
- **Action integers 0–4**, defined by `SimulatorCore.apply_action`,
  mirrored in `scheduler_env.py`'s `action_space` and
  `explainer.py`'s `ACTION_NAMES` — all three must agree on what each
  integer means.
- **`decision_log.json` shape**, written by `explainer.py`, read by
  `dashboard/pages/api/decisions.js`: a list of
  `{state, action, action_name, explanation}` objects.

## Build/run order for an agent building this from scratch

1. `simulator/process.py` → `simulator/scheduler_algorithms.py` → test
   standalone → `simulator/simulator_core.py` → test standalone.
2. `rl_agent/scheduler_env.py` (depends on `simulator_core.py`) → test
   standalone with random actions.
3. `rl_agent/train.py` → run training, produces `trained_model.zip`.
4. `explainability/explainer.py`, buildable and testable in parallel
   with step 3 using `generate_fake_decisions()` — produces
   `decision_log.json`.
5. `dashboard/*` — buildable and testable in parallel with step 3,
   pointed at the `decision_log.json` from step 4.
6. Replace `generate_fake_decisions()` with real logged decisions from
   the trained model (requires adding a small script that runs the
   trained model through `SchedulerEnv` and logs each
   `state`/`action` pair — not yet built in this repo).
7. `docs/writeup.md`, filled in last, once real results exist to
   describe.
