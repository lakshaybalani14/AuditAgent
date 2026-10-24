# Vercel scheduler inference API

This API runs the compact export of the existing 7-input scheduler DQN. It is inference-only: it does not install Stable-Baselines3 or PyTorch and does not train a model during a request.

## Routes

- `GET /api/run` checks that the exported policy is present and readable.
- `POST /api/run` runs the deterministic simulator and returns dashboard decision events.

The exported model lives at `rl_agent/policy.json`. It was created from the same locally trained `trained_model.zip`; the model consumes the legacy seven-field state summary still exposed by `SimulatorCore.get_state_summary()`.

The Python function only reads its bundled model and returns run results. Vercel's function filesystem is read-only, so run history is kept by the dashboard in each visitor's browser.
