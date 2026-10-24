# Deploying AuditAgent on Vercel

The dashboard is a Next.js project rooted at `dashboard/`. The inference API is a Python Vercel Function rooted at the repository root. Both Vercel projects use this same GitHub repository:

- `auditagent`: dashboard, root directory `dashboard`
- `auditagent-api`: Python function `api/run.py`

## Existing model

`rl_agent/policy.json` is the compact inference export from the locally trained `trained_model.zip`. It preserves the trained 7-input, 64-by-64 hidden-layer, 5-action DQN. The runner evaluates that network directly and uses the simulator's legacy summary fields in this order: queue length, average wait, maximum wait, I/O-bound count, CPU-bound count, current algorithm, starvation flag. This avoids training and PyTorch on Vercel.

The current Gymnasium environment also has a newer 20-feature observation space. The deployed compatibility runner deliberately uses the seven fields the exported checkpoint was trained on; it does not claim the old checkpoint was trained on the 20-feature representation.

## Connect the dashboard to the API

In the `auditagent` Vercel project's environment settings, set `SCHEDULER_MODEL_API_URL` to the base URL of the public `auditagent-api` project for Production, Preview, and Development. Do not include `/api/run` in the value. Redeploy after changing it.

`POST /api/run` runs the deterministic 15-decision preview and returns full decision events. The dashboard stores that user's latest run in browser local storage. Runs are not written to Vercel's read-only function filesystem; shared durable run history would require a database or Vercel Blob.

## Public access

Disable Vercel Authentication / SSO protection on both projects after the model API is linked and validated, then make sure `auditagent-one.vercel.app` is assigned to the dashboard production deployment.
