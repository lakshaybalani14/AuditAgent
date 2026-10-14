# AuditAgent Team Workflow

## Current project status

PR #2 established configurable DQN training and evaluation. PR #4 delivered Person 1's process lifecycle, I/O blocking and wakeups, functional Round Robin, Priority, and MLFQ scheduling, seeded workloads, and scheduling metrics. PR #3 adds seven seeded synthetic profiles plus profile-aware RL training and matched-seed evaluation. This integration connects those profiles to SimulatorCore and generates real I/O requests for I/O-bound processes.

The simulator-to-agent loop is ready for model-training experiments. Training runs must use held-out seeds and report measured results before making performance claims.

## Four-person task split

| Owner | Task | Main files or outputs | Status/dependencies |
|---|---|---|---|
| Person 1 — Simulator and OS behavior | MLFQ behavior, scheduler actions, seeded profile-aware reset, process lifecycle, I/O blocking/wakeup, and scheduling metrics. | simulator/simulator_core.py and related simulator files | Delivered in PR #4 and integrated with Person 3's profile generator and Gymnasium environment |
| Person 2 — Workload data and validation | Investigate suitable external workload traces, data formats, and licenses; review synthetic profile assumptions and document limitations. | Trace source/license notes and workload review | Follow-up research |
| Person 3 — RL training, profiles, and evaluation | Generate seeded profiles; select and record profiles during training; evaluate DQN and baselines on identical held-out workloads; report by profile and review reward behavior. | simulator/workload_profiles.py, rl_agent/scheduler_env.py, rl_agent/train.py, rl_agent/evaluate.py, docs/WORKLOAD_PROFILES.md | Profile-aware simulator and training/evaluation path integrated |
| Person 4 — Dashboard and explanations | Display experiment configuration, workload profile, policy metrics, and decisions; keep the dashboard usable without an Anthropic key. | Dashboard and explainability files | Connect to reproducible experiment output and shared report schema |

Person 2 can research traces while Person 4 builds against mock reports. Training can now use named profiles through the integrated simulator reset API.

## Recommended implementation order

1. Maintain the shared contract for profile identifiers, process fields, seed handling, simulator actions, reward and metric definitions, and run/report JSON.
2. Run reproducible training across varied profiles.
3. Evaluate DQN and baselines on identical held-out seeds/workloads. Report results by profile and distinguish ready-queue age samples from completed-process total waiting time.
4. Connect actual reports to the dashboard, reconcile schemas, record reproducible results, and prepare the demo.

MLFQ now has behavior distinct from Round Robin through queues, demotion, and periodic boosts. Longer training alone does not guarantee better performance; reward and simulator behavior must represent the intended scheduling goals.

## Branch and pull-request process

1. Create feature branches from the latest main.
2. Keep branches focused and coordinate shared interfaces.
3. Open pull requests targeting main.
4. Explain outcomes, changed files, interfaces, verification, and follow-up work.
5. Review cross-component contracts, simulation semantics, reproducibility, and evidence for performance claims.
6. Merge after review and required checks pass. The repository currently has no reported CI workflow/status checks; add automated checks and configure branch protection before relying on required-review enforcement.

## Definition of done

- Behavior matches the shared contract and documentation.
- Focused tests or reproducible manual verification pass.
- State, action, workload, and run-log schema changes are reported.
- Training and benchmark changes record configuration, seed, and workload split.
- External traces have documented sources and license notes; no credentials or large raw datasets are committed.
- Performance claims reflect reproduced measurements.

## Release and demo checklist

- Start from a clean, integrated main.
- Reproduce benchmark reports from documented commands and seeds.
- Verify saved logs and dashboard schema compatibility.
- Ensure the dashboard can show a run without an Anthropic key.
- Cite and license any external workload traces.
- Update project claims only with reproducible results.

