# AuditAgent Tech Stack

This document records the technologies present in the repository and the role each plays. Version ranges below reflect the checked-in manifests, not a claim that every dependency combination has been freshly installed or tested.

## Current stack

| Area | Technology | Repository evidence and use |
|---|---|---|
| Language | Python | Simulator, Gymnasium environment, training, decision logging, and explanation client |
| Numerical arrays | NumPy `>=1.26` | Encodes the observation vector |
| RL environment API | Gymnasium `>=0.29` | Defines the observation/action spaces and reset/step contract |
| RL algorithm | Stable-Baselines3 `>=2.3` | Provides DQN and training callbacks |
| Explanation API | Anthropic Python SDK `>=0.40` | Optional generated explanations; needs `ANTHROPIC_API_KEY` |
| Data interchange | JSON | Decision logs consumed by the dashboard |
| Frontend framework | Next.js `^14.2.0` | Page application and API route |
| UI library | React / React DOM `^18.3.0` | Dashboard components |
| JavaScript runtime/package manager | Node.js and npm | Required to install and run the dashboard; no Node version is pinned in the repository |
| Python environment | `venv` and pip | Setup instructions use a local virtual environment |

The exact Python dependency declarations are in `requirements.txt`; JavaScript dependencies and the npm lockfile are in `dashboard/package.json` and `dashboard/package-lock.json`.

## What is not currently in the stack

The repository does not currently include:

- A database or persistent run store.
- A live event transport such as WebSockets or server-sent events.
- A production API service between the Python simulator and dashboard.
- A workload-trace ingestion package or checked-in workload dataset.
- An OS kernel module, eBPF scheduler, or system-call integration.
- A tracked trained model. `trained_model.zip` is ignored by Git.
- A Python lockfile or pinned Python dependency versions.

## Data and model roles

There are two different AI-related functions:

1. **DQN policy:** Trained locally with simulator-generated episodes. This is the component that chooses actions.
2. **Anthropic explanation call:** Optional API inference after a decision. It turns a recorded state/action into prose; it is not fine-tuned in this project and does not train the DQN.

Public workload traces should be converted into simulator scenarios. They are useful for training distribution and held-out evaluation, but they do not by themselves tell the DQN which action is optimal.

Potential workload sources:

- [Parallel Workloads Archive](https://www.cs.huji.ac.il/labs/parallel/workload/) for scheduler-oriented workload logs and models.
- [Alibaba Cluster Trace Program](https://github.com/alibaba/clusterdata) for larger production cluster workloads that require preprocessing.
- [Microsoft Azure Public Dataset](https://github.com/Azure/AzurePublicDataset) for VM and function workload traces.
- [Google Cluster Data](https://github.com/google/cluster-data) for large Borg workload traces; the 2019 trace is very large and should be considered after a smaller dataset pipeline exists.

Before using a trace, document its schema, license/citation requirements, transformations, and limitations. Do not commit large raw trace files or credentials.

## Recommended stack improvements

1. Pin compatible Python versions and dependencies, and record the Python and Node versions used for reproducible runs.
2. Add a small workload schema and versioned decision-log schema.
3. Add a run-results interface so the dashboard can load saved results now and live events later.
4. Add experiment metadata: seed, workload source/split, policy version, reward configuration, dependency versions, and timestamp.
5. Keep the Anthropic key in environment configuration; never place it in source code, logs, or the browser bundle.
