# Math Fidelity Notebooks

This directory is reserved for exploratory notebooks that inspect Phase 8
mathematical fidelity evidence.

Notebook workflow:

1. Read generated logs from `development/math_fidelity/logs/`.
2. Prefer `logs/timeseries/simple_drift_timeseries_long.csv` for graphing.
3. Use compact CSV/JSON files for summary tables and run filtering.
4. Rerun `development/math_fidelity/probes/investigate_simple_drift.py` only
   when intentionally refreshing the evidence after code or probe changes.

No notebook is required for the current drift pass.
