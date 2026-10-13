# AuditAgent Team Workflow

## Work split and dependencies

Agree on the process, workload, state, action, and decision-log contracts before parallel implementation.

| Owner | Area | Suggested branch | Depends on |
|---|---|---|---|
| Person 1 — OS simulator | Process states, RR/Priority/MLFQ semantics, I/O, deterministic simulation | `feature/os-simulator` | Shared workload and state contract |
| Person 2 — Workloads and benchmarks | Trace importer, synthetic scenarios, baseline runner, metric definitions | `feature/workloads-benchmarks` | Shared workload schema; can start with fixtures |
| Person 3 — RL and evaluation | Gymnasium environment, DQN training, reward experiments, held-out comparisons | `feature/rl-evaluation` | Person 1 simulator API and Person 2 workload/benchmark API |
| Person 4 — Dashboard and explanations | Run API, dashboard views, decision explanations, saved/live run states | `feature/dashboard-live-runs` | Shared log schema; mock data initially, then Person 1/3 run output |

Dependency overview:

```text
Person 1: Simulator ───────┬──> Person 3: RL and evaluation
                           └──> Person 4: live run data
Person 2: Workloads ───────────> Person 3: held-out evaluation
Person 3: decision/run schema ──> Person 4: policy decisions in UI
```

Person 1 and Person 2 can build in parallel after agreeing on the workload schema. Person 4 can build the UI against mock records while the simulator and trainer are in progress. Person 3 can prototype with fixtures, but final results depend on the integrated simulator and workload scenarios.

## Recommended integration order

1. **Contract milestone:** document process/workload input, time units, state fields, action IDs, metric definitions, and versioned decision/run JSON.
2. **Parallel foundations:** Person 1 builds simulator behavior; Person 2 builds workload fixtures/import and baseline reporting; Person 4 builds UI against mock run records.
3. **RL integration:** Person 3 connects the stable simulator and workload scenarios, then trains and evaluates against the baselines.
4. **Dashboard integration:** Person 4 connects the run API or saved experiment format and presents metrics and decisions.
5. **Project integration:** reconcile contracts, run the project checks, update docs with measured results, and prepare a release/demo.

## Branch and pull-request process

1. Create each feature branch from the latest `main`.
2. Keep each branch focused on its owner’s files and responsibility. Coordinate before changing a shared schema.
3. Push work to the feature branch and open a pull request targeting `main`. Do not push feature work directly to `main`.
4. In each PR, explain the user-visible or research outcome, files changed, interface changes, how the change was checked, and any follow-up work.
5. Review cross-component contracts, simulation semantics, reproducibility, and evidence for performance claims.
6. Merge only after the owner/reviewer approves and required checks pass.

At the reviewed repository revision, only `main` was visible and branch protection was disabled. The repository also had no test or CI workflow files. Set up branch protection and automated checks before relying on required-review enforcement.

## Definition of done

A task is ready to merge when:

- Its behavior matches the shared contract and documentation.
- It includes focused tests or a reproducible manual verification appropriate to the change.
- It does not introduce unreported changes to the state/action/log schema.
- Training or benchmark changes record configuration, seed, and workload split.
- No credentials or large raw datasets are committed.
- The PR states what has actually been measured and does not present a hypothesis as a result.

## Release and demo checklist

- Start from a clean, integrated `main`.
- Reproduce the benchmark report from documented commands and seeds.
- Verify saved logs and dashboard schema compatibility.
- Ensure the dashboard can show a run without an Anthropic key.
- Add citations and license notes for any external workload traces.
- Update the project write-up only with results that the benchmark reproduces.
