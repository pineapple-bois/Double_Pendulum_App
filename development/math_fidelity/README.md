# Phase 8 Mathematical Fidelity Evidence Lab

This directory contains diagnostic evidence for Phase 8 mathematical fidelity
work. It is a self-contained evidence lab, not a production package, and must
not become a runtime dependency of the Dash app.

- [Baseline review](BASELINE_REVIEW.md)
- [Drift investigation](DRIFT_INVESTIGATION.md)
- [Solver cost benchmark](SOLVER_COST_BENCHMARK.md)
- [App-like cost benchmark](APP_LIKE_COST_BENCHMARK.md)
- [Solver policy recommendation](SOLVER_POLICY_RECOMMENDATION.md)
- [Source snapshot manifest](snapshots/SNAPSHOT_MANIFEST.md)
- [Probe scripts](probes/)
- [Generated logs](logs/)
- [Interactive drift notebook](explore_drift_evidence.ipynb)
- [Notebook workspace](notebooks/)

## Rerun Drift Investigation

From the repository root:

```bash
.venv/bin/python development/math_fidelity/probes/investigate_simple_drift.py
```

The probe imports the diagnostic source snapshot under
`development/math_fidelity/snapshots/simple_model_source/` and writes compact
logs plus notebook-ready time-series CSVs under `development/math_fidelity/logs/`.
The current drift investigation includes `solve_ivp_default`, `rk45_strict`,
`dop853_moderate`, `dop853_strict`, and `dop853_reference`.

## Rerun Solver Cost Benchmark

From the repository root:

```bash
.venv/bin/python development/math_fidelity/probes/benchmark_solver_cost.py
```

The benchmark imports the same diagnostic source snapshot and writes:

- `development/math_fidelity/logs/solver_cost_benchmark.csv`
- `development/math_fidelity/logs/solver_cost_benchmark.json`

See [Solver cost benchmark](SOLVER_COST_BENCHMARK.md) for design notes,
headline findings, limitations, and recommended next actions.

## Rerun App-Like Cost Benchmark

From the repository root:

```bash
.venv/bin/python development/math_fidelity/probes/benchmark_app_like_cost.py
```

The app-like benchmark imports the diagnostic source snapshot and writes:

- `development/math_fidelity/logs/app_like_cost_benchmark.csv`
- `development/math_fidelity/logs/app_like_cost_benchmark.json`

See [App-like cost benchmark](APP_LIKE_COST_BENCHMARK.md) for payload-size,
serialization, and app-like timing observations.

## Interactive Inspection

Open `development/math_fidelity/explore_drift_evidence.ipynb` for the current
interactive inspection entry point. It loads existing CSV logs with pandas and
does not rerun simulations by default. The notebook can be run from either the
repository root or `development/math_fidelity/`, and it includes an optional
section for solver-cost and app-like cost logs when those CSVs exist.

Static PNG figures are not part of the required evidence workflow. The notebook
displays plots inline, generated logs are the source of truth, and
`reports/figures/` is intentionally not part of the evidence contract.

## Notebook Readiness

Future notebooks should read from generated logs rather than rerunning
simulations by default. Start with:

```python
import pandas as pd

runs = pd.read_csv("development/math_fidelity/logs/simple_drift_results.csv")
timeseries = pd.read_csv(
    "development/math_fidelity/logs/timeseries/simple_drift_timeseries_long.csv"
)
benchmark = pd.read_csv(
    "development/math_fidelity/logs/solver_cost_benchmark.csv"
)
app_like = pd.read_csv(
    "development/math_fidelity/logs/app_like_cost_benchmark.csv"
)
```

If running from inside `development/math_fidelity/`, use paths relative to that
directory or reuse the `LAB_ROOT` detection cell from
`explore_drift_evidence.ipynb`.

## Evidence Boundary

All code in this directory is diagnostic and self-contained. Production app
code, Canvas payload code, callbacks, UI, and solver defaults must not import
from `development/math_fidelity/`.
