# Phase 8 Mathematical Fidelity Evidence Lab

This directory contains diagnostic evidence for Phase 8 mathematical fidelity
work. It is a self-contained evidence lab, not a production package, and must
not become a runtime dependency of the Dash app.

- [Baseline review](BASELINE_REVIEW.md)
- [Drift investigation](DRIFT_INVESTIGATION.md)
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

## Interactive Inspection

Open `development/math_fidelity/explore_drift_evidence.ipynb` for the current
interactive inspection entry point. It loads existing CSV logs with pandas and
does not rerun simulations by default.

Static PNG figures generated from the same logs are under
`development/math_fidelity/reports/figures/`.

## Notebook Readiness

Future notebooks should read from generated logs rather than rerunning
simulations by default. Start with:

```python
import pandas as pd

runs = pd.read_csv("development/math_fidelity/logs/simple_drift_results.csv")
timeseries = pd.read_csv(
    "development/math_fidelity/logs/timeseries/simple_drift_timeseries_long.csv"
)
```
