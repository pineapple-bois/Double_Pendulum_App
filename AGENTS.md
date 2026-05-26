# AGENTS.md

Guidance for coding agents working in this repository. Read `README.md` for setup/current usage and `ROADMAP.md` for active modernization direction before editing.

## Project Overview

- This repository serves a legacy Plotly Dash app built on Flask for simulating and visualizing double pendulum motion.
- The public app is documented as `http://www.double-pendulum.net`.
- The app models simple and compound double pendulums, derives equations with `SymPy`, numerically integrates with `SciPy`, and renders graphs/animations with Plotly and Matplotlib.
- Main runtime: Python Dash app with a Flask `server` object for Gunicorn/Heroku deployment.
- The active direction is modernization first and redeployment later. Do not optimize for preserving an old Heroku dyno at the expense of the roadmap.
- Project identity is now the Nonlinear Dynamics / Chaos Companion App, with the double pendulum as the only concrete physical system in scope.

## Repository Structure

- `pendulum_app.py` - thin Dash app entrypoint. Defines `server`, `app`, the top-level app shell, and callback registration calls.
- `app/` - Dash-facing application layer.
  - `callbacks/` - app-shell routing and simulation callback registration.
  - `components/` - shared UI shell, footer, graph, reference, figure-style, card, and simulation-control helpers.
  - `content/` - page metadata, labels, copy, markdown paths, and reference data.
  - `pages/` - route-level page layout ownership and route registry.
- `src/double_pendulum/` - reusable non-Dash logic extracted from root modules.
  - `validation/` - input validation sections, constants, and Dash error rendering wrapper.
  - `math/` - symbolic mechanics helpers used by pendulum model classes.
  - `models/` - Lagrangian and Hamiltonian model classes.
  - `plotting/` - shared figure/display helpers.
- `assets/` - Dash-served static assets:
  - `assets/styles.css` - primary app styling.
  - `assets/nav-bar.js` and `assets/scroll.js` - client-side behavior.
  - `assets/custom-header.html` - loaded by `pendulum_app.py` as `app.index_string`.
  - `assets/MarkdownScripts/` - markdown/LaTeX content referenced by content modules.
  - `assets/Images/` - tracked app images used by the README and UI.
  - `assets/Heros/` - future visual inspiration for the redesign.
- `development/` - exploratory/prototype/reference work for chaos features and earlier double-pendulum model development; do not import from it in production code without review and tests.
- `legacy/` - historical reference material, including the old architecture guide.
- `tests/unit/` - validation and lightweight symbolic fidelity tests.
- `tests/integration/` - Dash app import, public route layout smoke, and Flask `server` tests.
- `tests/numerical/` - basic Lagrangian/Hamiltonian simulation shape, finite-value, position, and initial-condition tests.
- `pytest.ini` - pytest discovery/configuration for the test suite.
- `requirements-dev.txt` - test-only dependencies such as `pytest`.
- `ROADMAP.md` - active modernization and product/architecture planning document.
- `legacy/requirements-old-freeze.txt` - backup of the previous fully frozen dependency set.
- Deployment/runtime files: `Procfile`, `.python-version`, `requirements.txt`.

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
- Python 3.12 is the active development runtime. `.python-version` is the Python runtime source of truth for future Heroku deployment.
- `runtime.txt` has intentionally been removed and must not be reintroduced.
- `requirements.txt` intentionally lists only top-level application/runtime dependencies. It is not a full freeze.
- The previous frozen dependency list is preserved in `legacy/requirements-old-freeze.txt`; do not edit it unless explicitly asked to refresh that backup.
- Development/test-only dependencies are listed separately in `requirements-dev.txt`.
- No required environment variables, `.env` file, database config, or credential files were found in tracked repo files.
- The README notes that the HTTPS redirect block in `pendulum_app.py` should be commented out for local development. Verify the current state before changing it.

## Testing and Validation

There is no Makefile, lint config, formatter config, or type-check config in the tracked repo.

Install test-only dependencies into the activated Python 3.12 `.venv/` when needed:

```bash
pip install -r requirements-dev.txt
```

Run the full test suite with:

```bash
python -m pytest
```

Current validation note: top-level dependencies and `requirements-dev.txt` install into the Python 3.12 `.venv/`; `python -m pytest` passes with the Phase 2 test foundation. Coverage is still foundational and should not be treated as a complete numerical validation project.

Minimal Dash smoke test before finalizing changes:

- Install dependencies from `requirements.txt`.
- Start the app with `python pendulum_app.py`.
- Open `/`, `/lagrangian`, `/hamiltonian`, and `/chaos`.
- Run a simple simulation and confirm the time graph, phase graph, and animation render.
- Try invalid inputs and confirm validation messages appear instead of a server error.
- Check browser console for missing asset or JavaScript errors.

## Deployment Notes

- Future deployment is expected to remain Heroku-style based on:
  - `Procfile`: `web: gunicorn pendulum_app:server`
  - `.python-version`: Python runtime source of truth
  - `requirements.txt`: top-level Python dependencies including `gunicorn`.
- No `Dockerfile`, `heroku.yml`, `app.json`, or CI/CD config was found in tracked files.
- Do not rename `pendulum_app.py` or the Flask `server` object without also updating `Procfile`.
- Do not restore `runtime.txt`. Validate deployment with `.python-version` after local modernization is stable.
- Be cautious with local-only changes such as debug mode and HTTPS redirects; move them toward explicit configuration rather than commented code when that work is in scope.

## Coding Guidelines for Agents

- Keep changes small and repo-specific. Avoid large rewrites unless explicitly requested.
- Use `ROADMAP.md` to sequence modernization work. Architecture extraction, tests, UI redesign, chaos expansion, and deployment refresh should happen in that order unless the user explicitly redirects.
- Preserve public routes (`/`, `/lagrangian`, `/hamiltonian`, `/chaos`) unless the task is to change routing.
- Preserve Dash component IDs used by callbacks unless updating every dependent callback and layout reference together.
- Be careful with Dash callback dependencies, `suppress_callback_exceptions=True`, and pseudo-multipage layouts; missing IDs may only fail at runtime.
- Watch for circular imports between `pendulum_app.py`, `app/pages/`, `app/components/`, and callback modules.
- Keep UI changes compatible with the existing app style in `assets/styles.css`.
- Preserve data schemas, markdown file paths, image paths, and environment-variable names if any are added later.
- Prefer adding reusable non-Dash logic under `src/double_pendulum/`; root-level compatibility wrappers have been retired.
- Preserve existing `DoublePendulumLagrangian` and `DoublePendulumHamiltonian` behavior initially. Avoid model rewrites before meaningful numerical tests exist.

## Data and Secrets

- Local content/data appears to live in `assets/MarkdownScripts/` and static images under `assets/Images/`.
- No tracked `.env`, secrets, credentials, API tokens, or database files were found.
- Never commit secrets. Use environment variables or a local untracked config file if secrets are introduced.
- The local workspace may contain untracked/generated items such as `.venv/`, `__pycache__/`, and `.idea/`; do not rely on them as source of truth.

## Agent Workflow

- Read `README.md` and `ROADMAP.md` first.
- Inspect the relevant source, layout, asset, dependency, and deployment files before editing.
- Check `git status --short` before making changes and do not overwrite unrelated user edits.
- Run the available tests and, for UI changes, perform the Dash smoke test above.
- In the final response, summarize changed files and validation performed. Mark unknowns explicitly rather than guessing.
