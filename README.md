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
without letting anything starve. Every decision the RL agent makes is
sent to Claude (Anthropic's LLM), which returns a plain-English
explanation of why that decision made sense. A Next.js dashboard
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
decisions from the saved model. To generate Claude explanations instead, set
`ANTHROPIC_API_KEY` and run `python -m explainability.explainer`.

## Folder structure and ownership

```
agentic-scheduler/
├── simulator/            # Person A — pure OS logic, zero AI
│   ├── process.py
│   ├── scheduler_algorithms.py
│   └── simulator_core.py
├── rl_agent/             # Person B — RL agent, depends on simulator/
│   ├── scheduler_env.py
│   └── train.py
├── explainability/        # Person C — Claude API layer
│   └── explainer.py
├── dashboard/             # Person C — Next.js frontend
│   ├── pages/index.js
│   ├── pages/api/decisions.js
│   ├── components/QueueView.js
│   └── components/DecisionFeed.js
└── docs/
    └── writeup.md
```

Build order matters: `simulator/` has zero dependencies and must be
built first. `rl_agent/` depends on `simulator/`. `explainability/` and
`dashboard/` can be built in parallel with `rl_agent/`, using fake data,
and only need to be reconnected to real data at the end.

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
  - `reset()`: reinitializes `time = 0`, `current_algo = ALGO_ROUND_ROBIN`,
    empty `ready_queue`, empty `completed`, generates a fresh randomized
    batch of processes via `_generate_process_batch()`, and admits any
    that have already "arrived" at time 0.
  - `_generate_process_batch()`: returns `max_processes` random
    `Process` objects — random `arrival_time` (e.g. 0–20), `burst_time`
    (e.g. 2–15), `priority` (e.g. 0–3), and `is_io_bound` (~30% chance
    True). Sorted by arrival time. Randomization matters so the RL
    agent generalizes instead of memorizing one fixed scenario.
  - `_admit_arrivals()`: moves any pending processes whose
    `arrival_time <= self.time` from a pending list into `ready_queue`.
  - `get_state_summary()`: returns a dict with `time`, `queue_length`,
    `avg_wait_time`, `max_wait_time` (both computed from
    `time - p.last_ready_time` across the ready queue), `num_io_bound`,
    `num_cpu_bound`, `current_algo`, and `is_starving`
    (`max_wait_time > STARVATION_THRESHOLD`). This exact shape is what
    both `scheduler_env.py` and `explainer.py` depend on — don't rename
    keys without updating both.
  - `apply_action(action)`: interprets an integer 0–4:
    - `0` = no change
    - `1` = switch `current_algo` to Round Robin
    - `2` = switch to Priority
    - `3` = switch to MLFQ
    - `4` = find the longest-waiting process in `ready_queue` and lower
      its `priority` number by 1 (bounded at 0)
  - `tick()`: admits arrivals, then — if `ready_queue` is non-empty —
    picks the next process according to `current_algo` (sort by
    priority if `ALGO_PRIORITY`), runs it for
    `min(quantum, remaining_time)`, advances `self.time`, re-admits any
    new arrivals, and either marks it completed (compute
    `waiting_time`) or updates `last_ready_time` and pushes it to the
    back of the queue. Returns `True` if a process finished this tick,
    else `False`.
  - `is_episode_done()`: `True` when both `ready_queue` and any pending
    (not-yet-arrived) processes are empty.

**Expected behavior when run standalone:** loop calling `tick()` and
printing `get_state_summary()` until `is_episode_done()`, completing in
well under 100 ticks for `max_processes=5`.

---

## `rl_agent/scheduler_env.py`

**Purpose:** Wraps `SimulatorCore` in the Gym API (`reset()` / `step()`)
so any Gym-compatible RL library (Stable-Baselines3) can train against
it without knowing anything about scheduling internals.

**Build spec:**
- Class `SchedulerEnv(gym.Env)`:
  - `__init__(max_processes=10)`: sets `action_space = spaces.Discrete(5)`
    (matching `SimulatorCore.apply_action`'s 5 actions) and
    `observation_space = spaces.Box(low=0, high=np.inf, shape=(7,), dtype=np.float32)`.
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

**Purpose:** Given one state + one action (from the RL agent), calls
the Anthropic API and returns a plain-English explanation. No training,
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
- `explain_decision(state, action, client)`: calls
  `client.messages.create(model="claude-sonnet-5", max_tokens=200, messages=[...])`,
  extracts and concatenates all `type == "text"` blocks from the
  response's content list (a response can contain multiple content
  blocks; filtering by type rather than assuming position is required).
- `generate_fake_decisions(n=5)`: produces `n` random
  `{"state": {...}, "action": int}` dicts with plausible random field
  values, matching the exact shape `get_state_summary()` produces. This
  exists so the explainability layer can be built and tested **before**
  the RL agent has finished training — swap this out for a real
  decision log later without changing anything else in the file.
- `main()`: reads `ANTHROPIC_API_KEY` from the environment (raise a
  clear error if missing), generates fake decisions, calls
  `explain_decision` on each, prints each explanation, and writes the
  full list (state + action + action_name + explanation per entry) to
  `decision_log.json` — this exact file/shape is what the dashboard's
  API route reads.

**Expected behavior when run:** requires `ANTHROPIC_API_KEY` set and
`anthropic` installed; prints 5 explanations and writes
`decision_log.json`. (Needs your own API key — not run in this repo's
build/test pass.)

---

## `dashboard/pages/api/decisions.js`

**Purpose:** A Next.js API route (server-side endpoint) that reads
`decision_log.json` and returns it as JSON for the frontend to fetch.

**Build spec:**
- Default-exported `handler(req, res)` function (Next.js API route
  convention).
- Reads `decision_log.json` from the project root (`process.cwd()`)
  using Node's `fs.readFileSync`.
- Parses it as JSON and responds `res.status(200).json(decisions)`.
- If the file doesn't exist yet (explainer.py hasn't been run), catch
  the error and return an empty array with status 200 rather than
  crashing — the dashboard should render an empty state gracefully,
  not error out.

---

## `dashboard/components/QueueView.js`

**Purpose:** Displays the most recent system state as a small stat
panel.

**Build spec:**
- React functional component `QueueView({ state })`.
- If `state` is falsy, render a placeholder message instead of
  crashing on undefined field access.
- Otherwise render: time, queue length, average wait, longest wait,
  I/O-bound count, CPU-bound count, and a starvation-risk line whose
  text color changes (e.g. red vs green) based on `state.is_starving`.

---

## `dashboard/components/DecisionFeed.js`

**Purpose:** Displays the full list of logged decisions, each with its
Claude-generated explanation — the centerpiece of the demo.

**Build spec:**
- React functional component `DecisionFeed({ decisions })`.
- If `decisions` is empty/undefined, render a placeholder message.
- Otherwise map over the array and render one bordered card per entry
  showing: time (`entry.state.time`), the action name
  (`entry.action_name`), and the explanation text
  (`entry.explanation`). Use the array index as the React `key`.

---

## `dashboard/pages/index.js`

**Purpose:** The dashboard's main page — fetches the decision log once
on load and passes it down into `QueueView` and `DecisionFeed`.

**Build spec:**
- Functional component using `useState` (holds `decisions`, initialized
  to `[]`) and `useEffect` (with an empty dependency array, so it runs
  exactly once on mount) to `fetch("/api/decisions")`, parse the JSON,
  and store it in state.
- Derive `latestState` as `decisions[decisions.length - 1]?.state` (or
  `null` if empty) and pass it to `QueueView`.
- Pass the full `decisions` array to `DecisionFeed`.
- Simple two-column layout: `QueueView` on one side, `DecisionFeed` on
  the other.

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
