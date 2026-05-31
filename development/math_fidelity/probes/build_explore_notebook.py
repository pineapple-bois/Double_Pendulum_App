#!/usr/bin/env python3
"""Build the drift-evidence exploration notebook.

This utility reads generated logs only. It does not rerun simulations and does
not generate static figure artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path


LAB_ROOT = Path("development/math_fidelity")
NOTEBOOK_PATH = LAB_ROOT / "explore_drift_evidence.ipynb"


def md_cell(source: str) -> dict[str, object]:
    return {"cell_type": "markdown", "metadata": {}, "source": source.strip("\n").splitlines(True)}


def code_cell(source: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip("\n").splitlines(True),
    }


def build_notebook() -> None:
    cells = [
        md_cell(
            """# Phase 8 Drift Evidence Exploration

This notebook inspects the existing simple-model drift evidence in `development/math_fidelity/logs/`. It treats generated logs as the source of truth and does not rerun simulations by default.

Path handling is intentionally portable: the notebook can be run from the repository root or from `development/math_fidelity/`, where the notebook file lives. Inline notebook plots are the inspection surface; static PNG generation is intentionally out of scope for this evidence workflow."""
        ),
        md_cell(
            """## 1. Load Generated Logs

Load the compact run-level table and the long-format time-series table with pandas. The setup cell locates the evidence-lab root before constructing log paths; later cells use `LOG_DIR` rather than hard-coded repository-relative paths."""
        ),
        code_cell(
            """import os
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/double_pendulum_math_fidelity_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/double_pendulum_math_fidelity_cache")
import matplotlib.pyplot as plt

def find_lab_root(start=None):
    start = Path.cwd() if start is None else Path(start)
    candidates = [start, start / "development" / "math_fidelity"]
    candidates.extend(parent / "development" / "math_fidelity" for parent in start.parents)
    for candidate in candidates:
        if (
            (candidate / "logs").is_dir()
            and (candidate / "BASELINE_REVIEW.md").is_file()
            and (candidate / "DRIFT_INVESTIGATION.md").is_file()
        ):
            return candidate.resolve()
    raise FileNotFoundError(
        "Could not locate development/math_fidelity. Run this notebook from the repository root "
        "or from the evidence-lab directory."
    )

LAB_ROOT = find_lab_root()
LOG_DIR = LAB_ROOT / "logs"

runs = pd.read_csv(LOG_DIR / "simple_drift_results.csv")
timeseries = pd.read_csv(LOG_DIR / "timeseries" / "simple_drift_timeseries_long.csv")

SOLVER_ORDER = ["solve_ivp_default", "rk45_strict", "dop853_strict", "dop853_reference"]
SOLVER_LABELS = {
    "solve_ivp_default": "default",
    "rk45_strict": "RK45 strict",
    "dop853_strict": "DOP853 strict",
    "dop853_reference": "DOP853 reference",
}

print("evidence lab:", LAB_ROOT)
print("run-level rows/columns:", runs.shape)
print("time-series rows/columns:", timeseries.shape)
runs.head()"""
        ),
        md_cell(
            """## 2. Data Inventory

Check available cases, solvers, tolerance configurations, row counts, missing values, and basic run coverage before plotting."""
        ),
        code_cell(
            """inventory = {
    "run_rows": len(runs),
    "timeseries_rows": len(timeseries),
    "cases": sorted(runs["case_name"].unique()),
    "solver_configs": list(runs["solver_config"].drop_duplicates()),
    "methods": list(runs["method"].drop_duplicates()),
}
inventory"""
        ),
        code_cell(
            """tolerances = runs[["solver_config", "method", "rtol", "atol"]].drop_duplicates().sort_values("solver_config")
coverage = runs.groupby(["case_name", "solver_config"]).size().unstack(fill_value=0)
missing_runs = runs.isna().sum().loc[lambda s: s > 0]
missing_timeseries = timeseries.isna().sum().loc[lambda s: s > 0]

display(tolerances)
display(coverage)
print("Missing values in run-level log:")
display(missing_runs)
print("Missing values in time-series log:")
display(missing_timeseries)
print("Time-series rows per run:")
display(timeseries.groupby(["case_name", "solver_config"]).size().unstack(fill_value=0))"""
        ),
        md_cell(
            """## 3. Drift Summary Visualisations

These plots summarize the run-level evidence. Log-scaled axes make the tolerance-driven collapse in drift easier to see."""
        ),
        code_cell(
            """def ordered_bar(metric, ylabel, title):
    pivot = (
        runs.pivot(index="case_name", columns="solver_config", values=metric)
        .reindex(columns=SOLVER_ORDER)
    )
    ax = pivot.plot(kind="bar", figsize=(11, 5), logy=True)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, axis="y", which="both", alpha=0.25)
    ax.legend([SOLVER_LABELS.get(c, c) for c in pivot.columns], ncols=2)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    return ax

ordered_bar("max_abs_theta_diff_rad", "max angular drift (rad)", "Max angular drift by case and solver");"""
        ),
        code_cell(
            """second_bob_summary = (
    timeseries.groupby(["case_name", "solver_config"], as_index=False)["second_bob_position_diff"]
    .max()
    .pivot(index="case_name", columns="solver_config", values="second_bob_position_diff")
    .reindex(columns=SOLVER_ORDER)
)
ax = second_bob_summary.plot(kind="bar", figsize=(11, 5), logy=True)
ax.set_ylabel("max second-bob position drift")
ax.set_title("Max second-bob position drift by case and solver")
ax.grid(True, axis="y", which="both", alpha=0.25)
ax.legend([SOLVER_LABELS.get(c, c) for c in second_bob_summary.columns], ncols=2)
plt.xticks(rotation=20, ha="right")
plt.tight_layout();"""
        ),
        code_cell(
            """ordered_bar("lagrangian_max_abs_energy_drift", "max absolute energy drift", "Lagrangian energy drift by case and solver");
ordered_bar("hamiltonian_max_abs_energy_drift", "max absolute energy drift", "Hamiltonian energy drift by case and solver");"""
        ),
        code_cell(
            """cost = runs.assign(total_nfev=runs["lagrangian_nfev"] + runs["hamiltonian_nfev"])
fig, ax = plt.subplots(figsize=(8, 5))
for solver, group in cost.groupby("solver_config", sort=False):
    ax.scatter(group["total_nfev"], group["max_abs_theta_diff_rad"], label=SOLVER_LABELS.get(solver, solver), s=50)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("total function evaluations (Lagrangian + Hamiltonian)")
ax.set_ylabel("max angular drift (rad)")
ax.set_title("Solver cost versus Lagrangian/Hamiltonian agreement")
ax.grid(True, which="both", alpha=0.25)
ax.legend()
plt.tight_layout();"""
        ),
        md_cell(
            """## 4. Time-Series Visualisations

The long-format CSV lets us inspect when each run drifts, instead of looking only at end-state or maximum summaries."""
        ),
        code_cell(
            """def plot_metric_over_time(case_name, metric, ylabel, title=None):
    subset = timeseries[timeseries["case_name"] == case_name]
    fig, ax = plt.subplots(figsize=(10, 5))
    for solver in SOLVER_ORDER:
        group = subset[subset["solver_config"] == solver]
        if group.empty:
            continue
        ax.plot(group["t"], group[metric], label=SOLVER_LABELS.get(solver, solver))
    ax.set_yscale("log")
    ax.set_xlabel("time (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title or f"{metric} over time: {case_name}")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
    plt.tight_layout()
    return ax

plot_metric_over_time("screenshot_like_simple_start", "max_abs_theta_diff_rad", "max angular drift (rad)", "Angular drift over time: screenshot-like case");"""
        ),
        code_cell(
            """plot_metric_over_time("screenshot_like_simple_start", "second_bob_position_diff", "second-bob position drift", "Second-bob drift over time: screenshot-like case");"""
        ),
        code_cell(
            """case_name = "screenshot_like_simple_start"
fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
for ax, solver in zip(axes, ["solve_ivp_default", "dop853_reference"]):
    subset = timeseries[(timeseries["case_name"] == case_name) & (timeseries["solver_config"] == solver)]
    for theta in ("theta1", "theta2"):
        ax.plot(subset["t"], subset[f"lagrangian_{theta}_rad"], label=f"Lagrangian {theta}")
        ax.plot(subset["t"], subset[f"hamiltonian_{theta}_rad"], "--", label=f"Hamiltonian {theta}")
    ax.set_ylabel("angle (rad)")
    ax.set_title(f"Theta overlays: {SOLVER_LABELS[solver]}")
    ax.grid(True, alpha=0.25)
    ax.legend(ncols=2)
axes[-1].set_xlabel("time (s)")
plt.tight_layout();"""
        ),
        code_cell(
            """subset = timeseries[timeseries["case_name"] == "screenshot_like_simple_start"]
fig, ax = plt.subplots(figsize=(10, 5))
for solver in SOLVER_ORDER:
    group = subset[subset["solver_config"] == solver]
    ax.plot(group["t"], group["lagrangian_energy_abs_drift"], label=f"L {SOLVER_LABELS.get(solver, solver)}")
    ax.plot(group["t"], group["hamiltonian_energy_abs_drift"], "--", label=f"H {SOLVER_LABELS.get(solver, solver)}")
ax.set_yscale("log")
ax.set_xlabel("time (s)")
ax.set_ylabel("absolute energy drift")
ax.set_title("Energy drift over time: screenshot-like case")
ax.grid(True, which="both", alpha=0.25)
ax.legend(ncols=2, fontsize=8)
plt.tight_layout();"""
        ),
        md_cell(
            """## 5. Focus: Screenshot-Like Simple Case `[0, 60, 0, 0]`

This section compares default solver behavior with the tight DOP853 reference configuration for the case that most closely matches the historical discrepancy note."""
        ),
        code_cell(
            """focus = timeseries[
    (timeseries["case_name"] == "screenshot_like_simple_start")
    & (timeseries["solver_config"].isin(["solve_ivp_default", "dop853_reference"]))
]
fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
for solver, group in focus.groupby("solver_config", sort=False):
    axes[0].plot(group["t"], group["max_abs_theta_diff_rad"], label=SOLVER_LABELS.get(solver, solver))
    axes[1].plot(group["t"], group["second_bob_position_diff"], label=SOLVER_LABELS.get(solver, solver))
axes[0].set_yscale("log")
axes[1].set_yscale("log")
axes[0].set_ylabel("max angular drift (rad)")
axes[1].set_ylabel("second-bob drift")
axes[1].set_xlabel("time (s)")
axes[0].set_title("Default vs DOP853 reference: screenshot-like case")
for ax in axes:
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
plt.tight_layout()

runs[runs["case_name"].eq("screenshot_like_simple_start")][[
    "solver_config", "max_abs_theta_diff_rad", "max_bob_position_abs_diff",
    "lagrangian_max_abs_energy_drift", "hamiltonian_max_abs_energy_drift",
    "lagrangian_nfev", "hamiltonian_nfev"
]]"""
        ),
        md_cell(
            """## 6. Divergence Thresholds

Compute the first logged time each run crosses practical angular-drift thresholds. `NaN` means the run never crossed that threshold in the logged interval."""
        ),
        code_cell(
            """thresholds = [1e-6, 1e-4, 1e-2]
rows = []
for (case_name, solver_config), group in timeseries.groupby(["case_name", "solver_config"]):
    row = {"case_name": case_name, "solver_config": solver_config}
    for threshold in thresholds:
        crossed = group[group["max_abs_theta_diff_rad"] >= threshold]
        row[f"first_crossing_{threshold:g}_s"] = crossed["t"].iloc[0] if not crossed.empty else np.nan
    rows.append(row)
threshold_table = pd.DataFrame(rows).sort_values(["case_name", "solver_config"])
display(threshold_table)"""
        ),
        md_cell(
            """## 7. Optional Solver-Cost Benchmark Logs

If `solver_cost_benchmark.csv` exists, inspect it here. If it does not exist, the rest of the notebook still runs because the drift logs remain the source of truth for the drift investigation."""
        ),
        code_cell(
            """SOLVER_BENCHMARK_CSV = LOG_DIR / "solver_cost_benchmark.csv"

if SOLVER_BENCHMARK_CSV.exists():
    benchmark = pd.read_csv(SOLVER_BENCHMARK_CSV)
    print("solver benchmark rows/columns:", benchmark.shape)
    display(benchmark.head())
else:
    benchmark = None
    print("Solver-cost benchmark log not found.")
    print("Generate it from the repository root with:")
    print(".venv/bin/python development/math_fidelity/probes/benchmark_solver_cost.py")"""
        ),
        code_cell(
            """if benchmark is None:
    print("No solver-cost benchmark log loaded.")
else:
    runtime_summary = benchmark.pivot_table(
        index=["duration_s", "formulation"],
        columns="solver_config",
        values="median_runtime_s",
        aggfunc="median",
    )
    display(runtime_summary)

    fig, ax = plt.subplots(figsize=(10, 5))
    for (formulation, solver_config), group in benchmark.groupby(["formulation", "solver_config"]):
        grouped = group.groupby("duration_s", as_index=False)["median_runtime_s"].median()
        ax.plot(grouped["duration_s"], grouped["median_runtime_s"], marker="o", label=f"{formulation} / {solver_config}")
    ax.set_yscale("log")
    ax.set_xlabel("duration (s)")
    ax.set_ylabel("median runtime (s)")
    ax.set_title("Solver runtime by duration, formulation, and policy")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8, ncols=2)
    plt.tight_layout();"""
        ),
        md_cell(
            """## 8. Optional App-Like Cost Benchmark Logs

If `app_like_cost_benchmark.csv` exists, inspect end-to-end model construction, position reconstruction, payload preparation, JSON serialization, and payload-size evidence here."""
        ),
        code_cell(
            """APP_LIKE_CSV = LOG_DIR / "app_like_cost_benchmark.csv"

if APP_LIKE_CSV.exists():
    app_like = pd.read_csv(APP_LIKE_CSV)
    print("app-like benchmark rows/columns:", app_like.shape)
    display(app_like.head())
else:
    app_like = None
    print("App-like benchmark log not found.")
    print("Generate it from the repository root with:")
    print(".venv/bin/python development/math_fidelity/probes/benchmark_app_like_cost.py")"""
        ),
        code_cell(
            """if app_like is None:
    print("No app-like benchmark log loaded.")
else:
    app_runtime = app_like.pivot_table(
        index=["duration_s", "formulation"],
        columns="solver_config",
        values="median_total_runtime_s",
        aggfunc="median",
    )
    display(app_runtime)

    fig, ax = plt.subplots(figsize=(10, 5))
    for (formulation, solver_config), group in app_like.groupby(["formulation", "solver_config"]):
        grouped = group.groupby("duration_s", as_index=False)["median_total_runtime_s"].median()
        ax.plot(grouped["duration_s"], grouped["median_total_runtime_s"], marker="o", label=f"{formulation} / {solver_config}")
    ax.set_yscale("log")
    ax.set_xlabel("duration (s)")
    ax.set_ylabel("median total runtime (s)")
    ax.set_title("App-like runtime by duration, formulation, and solver policy")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8, ncols=2)
    plt.tight_layout();"""
        ),
        code_cell(
            """if app_like is None:
    print("No app-like benchmark log loaded.")
else:
    payload_summary = app_like.pivot_table(
        index=["duration_s", "formulation"],
        columns="solver_config",
        values="median_json_payload_bytes",
        aggfunc="median",
    )
    display(payload_summary)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(app_like["median_total_runtime_s"], app_like["median_json_payload_bytes"], s=45)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("median total runtime (s)")
    ax.set_ylabel("JSON payload size (bytes)")
    ax.set_title("App-like runtime versus serialized payload size")
    ax.grid(True, which="both", alpha=0.25)
    plt.tight_layout();"""
        ),
        md_cell(
            """## 9. Interpretation

The drift plots show that default `solve_ivp` can produce substantial Lagrangian/Hamiltonian disagreement for the simple model, while stricter RK45 and DOP853 configurations collapse that drift by many orders of magnitude. Position drift and energy drift follow the same broad tolerance pattern.

The benchmark sections are optional evidence layers. They help compare solver and app-like costs, but the generated CSV logs remain the source of truth. The evidence remains scoped to simple-model runs and does not settle compound-model fidelity or production callback contracts."""
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    build_notebook()
    print(f"Wrote notebook: {NOTEBOOK_PATH}")
    print("Static figure generation is intentionally out of scope.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
