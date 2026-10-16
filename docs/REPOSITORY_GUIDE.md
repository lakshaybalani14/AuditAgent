# Repository guide

This guide maps the active source tree and explains where project files and local runtime data belong.

## Source and documentation

| Path | Contents |
| --- | --- |
| `simulator/` | Process model, scheduling policies, and tick-by-tick scheduling engine. |
| `rl_agent/` | Gymnasium environment, DQN training, evaluation, and decision-log generation. |
| `explainability/` | Offline and Gemini-backed explanations of recorded decisions. |
| `dashboard/` | Next.js application: `pages/` and `pages/api/` for routes, `components/` for UI, `hooks/` for client behavior, `lib/` for server/application logic, `styles/` for styling, and `sample-data/` for demo fixtures. Use this folder's `package.json` for frontend commands and dependencies. |
| `tests/` | Python tests covering the simulator, RL environment, evaluation, and dashboard integration. |
| `docs/` | Project documentation. `ARCHITECTURE.md` describes components; `WORKFLOW.md` describes the end-to-end flow; `RL_TRAINING_AND_EVALUATION.md` covers model work; `DEMO_GUIDE.md` supports demonstrations; `WORKLOAD_PROFILES.md` defines workload cases. |
| `requirements.txt` | Python dependencies for the simulator, agent, and API integration. |
| `README.md` | Setup, common commands, and runtime configuration. |

## Local runtime data

These locations are generated or machine-specific and are intentionally ignored by Git:

- `runs/` — checkpoints, training metadata, evaluation reports, monitor CSV files, and simulator output. Keep each experiment in its own named subfolder so seeds and training runs remain distinguishable; live dashboard runs go in `runs/live-simulator/`.
- `runs/live-simulator/decision_log.generated.live-<run-id>.json` — a separate decision log for each live simulator run.
- `.dashboard-data/` — active live-run pointer and dashboard runtime state.
- `.venv/`, `dashboard/node_modules/`, and `dashboard/.next/` — local Python/Node dependencies and Next.js build output.
- `dashboard/.env.local` — local API credentials and settings. Never commit this file or put credentials in source files.

Keep the runtime paths above stable: the dashboard and backend resolve them directly. To add a new source module, place it with its owning area above; put durable explanations and project guides in `docs/`.

## Preserved root npm files

In this local checkout, `local-artifacts/unrelated-root-npm-manifests/` holds the pre-existing root `package.json` and lockfile. They declared an unrelated package named `i`; the active frontend manifest is `dashboard/package.json`. The files were moved here intact so their contents remain available without looking like the frontend's package configuration.
