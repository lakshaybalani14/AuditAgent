# AuditAgent Team Workflow

## Current project status

PR #2 is merged into main. It added configurable DQN training, saved experiment metadata and logs, policy evaluation against fixed baselines, and custom model paths for decision logging.

The next work is to make simulator workloads more varied and realistic, implement distinct MLFQ behavior, then train and evaluate the DQN across workload profiles it has not seen during training.

## Four-person task split

| Owner | Task | Main files or outputs | Dependencies |
|---|---|---|---|
| Person 1 — Simulator and OS behavior | Implement real MLFQ behavior; make scheduler actions change behavior as intended; expose an agreed, seeded interface for selecting a workload profile; report reliable process and scheduling metrics. | simulator/simulator_core.py and related simulator files | Agree on workload-profile and seed contract with Person 2 |
| Person 2 — Workload profiles and data | Create reusable synthetic profiles: light, bursty arrivals, CPU-heavy, short-job-heavy, I/O-heavy, and mixed. Define the profile schema; optionally investigate licensed workload traces and how to map them into simulator processes. | A separate workload-generation module, profile fixtures, trace/license notes | Agree on profile names, fields, and seed behavior with Person 1 |
| Person 3 — RL training and evaluation | Build on the merged training/evaluation tools. Let training select and record profiles; evaluate DQN and baselines on the same held-out workloads; report results by profile; review whether rewards match the project goals. | rl_agent/scheduler_env.py, rl_agent/train.py, rl_agent/evaluate.py, experiment reports | Can prepare selection, metadata, and report handling with fixtures. End-to-end runs depend on the Person 1 simulator interface and Person 2 profile generator |
| Person 4 — Dashboard and explanations | Display experiment configuration, workload profile, policy metrics, and decisions; use mock reports until real experiment output is available; keep the dashboard usable without an Anthropic key. | Dashboard and explainability files | Shared, versioned run/decision-log schema; real data integration follows Person 3 output |

### Parallel work and dependencies

~~~
Person 1: Simulator and MLFQ ──────┐
                                   ├──> Person 3: integrated RL training/evaluation
Person 2: Workload profiles ───────┘
Person 3: versioned run/report schema ──> Person 4: dashboard integration
Person 4: can build against mock reports while the other work proceeds
~~~

Person 1 and Person 2 can work in parallel after agreeing on a small interface. Keep profile generation in its own module so Person 1 can integrate it into the simulator without both people editing the same implementation. Person 3 can prepare profile selection, metadata, and grouped reports using fixtures while the simulator work continues. Person 3 should wait for the agreed interface before wiring the final end-to-end path.

The interface agreement should specify profile identifiers, process fields, seed behavior, and how a selected profile reaches a simulator episode. A seed should make a workload repeatable; training and evaluation should use separate seed sets.

## Recommended implementation order

1. **Agree on contracts:** profile identifiers and process fields, seed handling, simulator state/action meanings, reward and metric definitions, and the run/report JSON schema.
2. **Work in parallel:** Person 1 implements distinct simulator behavior and the profile-selection interface; Person 2 creates profile recipes and optional trace-import notes; Person 3 prepares RL-side profile selection/reporting with fixtures; Person 4 builds against mock run reports.
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
