# AuditAgent Team Workflow

## Current project status

PR #2 is merged into main. It added configurable DQN training, saved experiment metadata and logs, policy evaluation against fixed baselines, and custom model paths for decision logging.

The next work is to make simulator workloads more varied and realistic, implement distinct MLFQ behavior, then train and evaluate the DQN across workload profiles it has not seen during training.

## Four-person task split

| Owner | Task | Main files or outputs | Dependencies |
|---|---|---|---|
| Person 1 — Simulator and OS behavior | Implement real MLFQ behavior; make scheduler actions change behavior as intended; accept a workload profile and episode seed through SimulatorCore.reset(seed=None, options=None); report reliable process and scheduling metrics. | simulator/simulator_core.py and related simulator files | Agree on the profile/reset contract with Person 3 |
| Person 2 — Workload data and validation | Investigate suitable external workload traces, data formats, and licenses; review whether the synthetic profile ranges represent useful workload patterns; document limitations and mapping guidance. | Trace source/license notes and workload review | Coordinate process fields with Persons 1 and 3 |
| Person 3 — RL training, profiles, and evaluation | Build on the merged training/evaluation tools. Own the seeded synthetic profile generator; let training select and record profiles; evaluate DQN and baselines on the same held-out workloads; report results by profile; review whether rewards match project goals. | simulator/workload_profiles.py, rl_agent/scheduler_env.py, rl_agent/train.py, rl_agent/evaluate.py, docs/WORKLOAD_PROFILES.md | Can prepare selection, metadata, and report handling now. End-to-end named-profile runs require Person 1's reset integration |
| Person 4 — Dashboard and explanations | Display experiment configuration, workload profile, policy metrics, and decisions; use mock reports until real experiment output is available; keep the dashboard usable without an Anthropic key. | Dashboard and explainability files | Shared, versioned run/decision-log schema; real data integration follows Person 3 output |

### Parallel work and dependencies

~~~
Person 1: Simulator and MLFQ ───────> Person 3: integrated profile-aware RL runs
Person 2: Trace research/review ─────> Person 3: future trace-based workloads
Person 3: versioned run/report schema ──> Person 4: dashboard integration
Person 4: can build against mock reports while the other work proceeds
~~~

Person 1 and Person 3 can work in parallel after agreeing on the reset/profile contract. Person 3 keeps profile generation in its own module so Person 1 can integrate it without both people editing SimulatorCore. Person 2 can research traces and review the profile assumptions in parallel. Person 4 can build against mock run reports. Person 3 can prepare RL selection and reporting now, but named-profile runs require Person 1's integration.

The simulator contract should specify profile identifiers, process fields, seed behavior, and how a selected profile reaches an episode. A seed should make a workload repeatable; training and evaluation should use separate seed sets.

## Recommended implementation order

1. **Agree on contracts:** profile identifiers and process fields, seed handling, simulator state/action meanings, reward and metric definitions, and the run/report JSON schema.
2. **Work in parallel:** Person 1 implements distinct simulator behavior and the profile-aware reset; Person 2 researches trace sources and validates profile assumptions; Person 3 prepares RL-side profile selection/reporting; Person 4 builds against mock run reports.
3. **Integrate workloads:** connect the profile generator to the simulator and expose profile selection through SchedulerEnv.
4. **Train and evaluate:** train across varied profiles; evaluate on held-out seeds/workloads using the same workloads for DQN and each baseline. Report results by profile and do not treat queue-age metrics as total completed-process waiting time.
5. **Integrate and review:** connect actual reports to the dashboard, reconcile shared schemas, record reproducible results, and prepare the demo/release.

MLFQ must have behavior distinct from Round Robin before its baseline comparison can be interpreted. Longer training alone does not guarantee better performance; reward and simulator behavior must first represent the intended scheduling goals.

## Branch and pull-request process

1. Create each feature branch from the latest main.
2. Keep each branch focused on its owner's files and responsibility. Coordinate before changing a shared schema or interface.
3. Push work to the feature branch and open a pull request targeting main. Do not push feature work directly to main.
4. In each PR, explain the outcome, files changed, interface changes, verification performed, and follow-up work.
5. Review cross-component contracts, simulation semantics, reproducibility, and evidence for performance claims.
6. Merge after review and required checks pass. PR #2 received static review; no CI status checks or workflow runs were reported for it. Add automated checks and configure branch protection before relying on required-review enforcement.

## Definition of done

A task is ready to merge when:

- Its behavior matches the shared contract and documentation.
- It includes focused tests or reproducible manual verification appropriate to the change.
- It does not introduce unreported changes to the state, action, workload, or run-log schema.
- Training and benchmark changes record configuration, seed, and workload split.
- External traces have documented sources and license notes; no credentials or large raw datasets are committed.
- The PR states what has actually been measured and does not present a hypothesis as a result.

## Release and demo checklist

- Start from a clean, integrated main.
- Reproduce benchmark reports from documented commands and seeds.
- Verify saved logs and dashboard schema compatibility.
- Ensure the dashboard can show a run without an Anthropic key.
- Add citations and license notes for any external workload traces.
- Update the project write-up only with results that the benchmark reproduces.
