# Development Workflow

This document records the safe local development workflow for the current Dash
app.

## Setup

Use Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

If `python` is not available until the virtual environment is active, use
`.venv/bin/python` or `python3`.

## Tests

Run the full suite with:

```bash
python -m pytest
```

Current test layers:

- unit tests: validation, content, components, and symbolic fidelity checks;
- numerical tests: model shape/finite-value checks, solver metadata,
  initial-condition conventions, and Canvas payload contract checks;
- integration tests: app import, route/layout smoke checks, and Simulation
  interaction shell/callback-level behavior.

Browser smoke checks are separate from the automated pytest suite.

## Dash smoke testing

Codex may start the Dash development server only when a browser or manual smoke
check is needed. If Codex starts the server, it must capture the process ID,
stop that exact process after testing, and verify that it has not left port
8050 occupied by its own process. If port 8050 was already occupied before
testing, Codex must not blindly kill the process.

This rule is more important than completing a browser smoke check.

## Port 8050 handling

Before starting the app, check whether port `8050` is occupied.

Suggested macOS/Linux check:

```bash
lsof -nP -iTCP:8050 -sTCP:LISTEN
```

If the port is already occupied:

- do not kill the process blindly;
- identify the process if possible;
- report that the port was occupied before testing;
- use a different temporary port only when appropriate and clearly record it.

If starting the app for a smoke check:

```bash
python pendulum_app.py
```

or run Dash on a deliberate temporary port only when the app entrypoint and
local command support it.

Capture the process ID for the exact process started. After testing, terminate
that PID and verify it is gone. Do not leave a Flask/Dash server running.

## Smoke-check procedure

When a browser smoke check is needed:

1. Check port `8050`.
2. Start the app and record the PID.
3. Open `http://127.0.0.1:8050/` or the explicit temporary port used.
4. Check `/`, `/simulation`, `/equations`, `/lagrangian`, `/hamiltonian`, and
   `/chaos` as relevant to the change.
5. For Simulation UI changes, run a simple valid simulation and confirm the
   Canvas motion, angular displacement, projection, playback controls, and
   diagnostics respond.
6. Try an invalid input and confirm validation/failure state appears without
   leaving drawable success arrays as current output.
7. Check the browser console for missing assets or JavaScript errors when a
   browser tool is available.
8. Stop the exact PID started for the smoke check.
9. Verify no Dash process started by the task remains running.

If a server cannot be started safely, skip the browser check and document why.

## Documentation maintenance

Update `documentation/` when changing:

- Canvas payload schema or renderer responsibility boundaries;
- Simulation result statuses;
- callback-bound IDs;
- Dash store shape;
- safe test/smoke workflow;
- production architecture that future agents need to preserve.
