# AGENTS.md

Guidance for coding agents working in this repository. Read `README.md` first; it is the primary source of truth, then verify against the files listed here before editing.

## Project Overview

- This repository serves a legacy-but-deployed Plotly Dash app built on Flask for simulating and visualizing double pendulum motion.
- The public app is documented as `http://www.double-pendulum.net`.
- The app models simple and compound double pendulums, derives equations with `SymPy`, numerically integrates with `SciPy`, and renders graphs/animations with Plotly and Matplotlib.
- Main runtime: Python Dash app with a Flask `server` object for Gunicorn/Heroku deployment.
- Because the app is live, keep modernization changes conservative and validate them carefully before deployment.

## Modernization Priorities

This is an early Dash project that is already deployed, so modernization should be incremental and conservative. The first modernization priorities are:

- Upgrade local development from Python 3.9 to Python 3.12. Completed locally; deployment runtime remains pinned to Python 3.9 in `runtime.txt`.
- Move local development instructions and tooling from `env/` to `.venv/`. Completed locally.
- Create `.gitignore` at root with the usual suspects (macOS and JetBrains specific files also). Completed locally.
- Migrate deployment runtime configuration carefully. Heroku now prefers `.python-version` over `runtime.txt`; do not remove or replace deployment runtime files without confirming the target Heroku stack/buildpack behavior.
- Keep changes incremental because the app is currently deployed.
- Review `requirements.txt` as part of the Python upgrade, but do not blindly upgrade all dependencies at once. Upgrade Dash, Flask, Plotly, NumPy, SciPy, SymPy, Matplotlib, and Gunicorn incrementally, running tests and the Dash smoke test after changes.

## Repository Structure

- `pendulum_app.py` - main Dash app entrypoint. Defines `server`, `app`, URL routing, and Dash callbacks.
- `AppFunctions.py` - input validation and shared figure/display helpers.
- `MathFunctions.py` - symbolic mechanics helpers used by pendulum model classes.
- `DoublePendulumLagrangian.py` - Lagrangian model class and plotting/animation behavior.
- `DoublePendulumHamiltonian.py` - Hamiltonian model class and plotting/animation behavior.
- `layouts/` - pseudo-multipage Dash layout functions:
  - `layout_main.py` - home page layout and main input UI.
  - `layout_math.py` - Lagrangian/Hamiltonian derivation pages.
  - `layout_chaos.py` - work-in-progress chaos page.
  - `layout_404.py` - not-found page.
  - `layout_matplotlib.py` - shared Plotly layout styling for converted Matplotlib figures.
- `assets/` - Dash-served static assets:
  - `assets/styles.css` - primary app styling.
  - `assets/nav-bar.js` and `assets/scroll.js` - client-side behavior.
  - `assets/custom-header.html` - loaded by `pendulum_app.py` as `app.index_string`.
  - `assets/MarkdownScripts/` - markdown/LaTeX content loaded by layouts.
  - `assets/Images/` - tracked app images used by the README and UI.
- `tests/validate_input_test.py` - existing `unittest` tests for `AppFunctions.validate_inputs`.
- Deployment/runtime files: `Procfile`, `runtime.txt`, `requirements.txt`.

## Setup and Local Development

Current supported setup from the README:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pendulum_app.py
```

On systems where `python` is not available, use the activated venv's Python or `python3`:

```bash
python3 pendulum_app.py
```

- Local URL: `http://127.0.0.1:8050/`.
- Python version for current deployment is still pinned in `runtime.txt` as `python-3.9.12`; local development has moved to Python 3.12 with `.venv/`.
- Dependencies are pinned in `requirements.txt`; no other package manager files were found.
- No required environment variables, `.env` file, database config, or credential files were found in tracked repo files.
- The README notes that the HTTPS redirect block in `pendulum_app.py` should be commented out for local development. Verify the current state before changing it.

## Testing and Validation

There is no Makefile, pytest config, lint config, formatter config, or type-check config in the tracked repo.

The existing tests use `unittest` and the filename pattern is `*_test.py`, so use:

```bash
python -m unittest discover -s tests -p '*_test.py'
```

or:

```bash
python3 -m unittest discover -s tests -p '*_test.py'
```

Current validation note: pinned dependencies install into the Python 3.12 `.venv/`, and the Dash app starts locally. The existing unittest file currently fails against the app's validation message output, so treat those failures as a test-suite maintenance issue to investigate before relying on the suite as a release gate.

Minimal Dash smoke test before finalizing changes:

- Install dependencies from `requirements.txt`.
- Start the app with `python pendulum_app.py`.
- Open `/`, `/lagrangian`, `/hamiltonian`, and `/chaos`.
- Run a simple simulation and confirm the time graph, phase graph, and animation render.
- Try invalid inputs and confirm validation messages appear instead of a server error.
- Check browser console for missing asset or JavaScript errors.

## Deployment Notes

- Deployment appears to be Heroku-style based on:
  - `Procfile`: `web: gunicorn pendulum_app:server`
  - `runtime.txt`: `python-3.9.12`
  - `requirements.txt`: pinned Python dependencies including `gunicorn`.
- No `Dockerfile`, `heroku.yml`, `app.json`, or CI/CD config was found in tracked files.
- Do not rename `pendulum_app.py` or the Flask `server` object without also updating `Procfile`.
- When upgrading deployment to Python 3.12, migrate runtime config cautiously. Heroku's current Python buildpack preference is `.python-version`; verify whether `runtime.txt` is still honored on the active stack before changing or deleting it.
- Be cautious with local-only changes such as debug mode and HTTPS redirects; they can affect the deployed app.

## Coding Guidelines for Agents

- Keep changes small and repo-specific. Avoid large rewrites unless explicitly requested.
- Treat Python 3.12, `.venv/`, and Heroku runtime-file migration as staged modernization work, not a reason to rewrite app architecture.
- Preserve public routes (`/`, `/lagrangian`, `/hamiltonian`, `/chaos`) unless the task is to change routing.
- Preserve Dash component IDs used by callbacks unless updating every dependent callback and layout reference together.
- Be careful with Dash callback dependencies, `suppress_callback_exceptions=True`, and pseudo-multipage layouts; missing IDs may only fail at runtime.
- Watch for circular imports between `pendulum_app.py`, `layouts/`, and helper modules.
- Keep UI changes compatible with the existing app style in `assets/styles.css`.
- Preserve data schemas, markdown file paths, image paths, and environment-variable names if any are added later.
- The README mentions `DoublePendulum.py`, but the actual tracked model files are `DoublePendulumLagrangian.py` and `DoublePendulumHamiltonian.py`.

## Data and Secrets

- Local content/data appears to live in `assets/MarkdownScripts/` and static images under `assets/Images/`.
- No tracked `.env`, secrets, credentials, API tokens, or database files were found.
- Never commit secrets. Use environment variables or a local untracked config file if secrets are introduced.
- The local workspace contains untracked/generated items such as `env/`, `__pycache__/`, and `.idea/`; do not rely on them as source of truth.

## Agent Workflow

- Read `README.md` first.
- Inspect the relevant source, layout, asset, dependency, and deployment files before editing.
- Check `git status --short` before making changes and do not overwrite unrelated user edits.
- Run the available tests and, for UI changes, perform the Dash smoke test above.
- In the final response, summarize changed files and validation performed. Mark unknowns explicitly rather than guessing.
