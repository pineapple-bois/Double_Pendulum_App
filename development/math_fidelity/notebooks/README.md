# Math Fidelity Notebooks

This directory is reserved for exploratory notebooks that inspect Phase 8
mathematical fidelity evidence.

By user preference, the current main notebook lives at the evidence-lab root:

```text
development/math_fidelity/explore_drift_evidence.ipynb
```

Notebook workflow:

1. Read generated logs from `development/math_fidelity/logs/`.
2. Prefer `logs/timeseries/simple_drift_timeseries_long.csv` for graphing.
3. Use compact CSV/JSON files for summary tables and run filtering.
4. Rerun `development/math_fidelity/probes/investigate_simple_drift.py` only
   when intentionally refreshing the evidence after code or probe changes.

Additional notebooks can live here if the evidence lab grows beyond the main
root-level notebook.
