#!/usr/bin/env python3
"""Build the drift-evidence exploration notebook and static figures.

This utility reads generated logs only. It does not rerun simulations.
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/double_pendulum_math_fidelity_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/double_pendulum_math_fidelity_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


LAB_ROOT = Path("development/math_fidelity")
LOG_DIR = LAB_ROOT / "logs"
TIMESERIES_CSV = LOG_DIR / "timeseries" / "simple_drift_timeseries_long.csv"
FIGURE_DIR = LAB_ROOT / "reports" / "figures"
NOTEBOOK_PATH = LAB_ROOT / "explore_drift_evidence.ipynb"

SOLVER_ORDER = ["solve_ivp_default", "rk45_strict", "dop853_strict", "dop853_reference"]
SOLVER_LABELS = {
    "solve_ivp_default": "default",
    "rk45_strict": "RK45 strict",
    "dop853_strict": "DOP853 strict",
    "dop853_reference": "DOP853 ref",
}
SOLVER_COLORS = {
    "solve_ivp_default": "#6b7280",
    "rk45_strict": "#2563eb",
    "dop853_strict": "#059669",
    "dop853_reference": "#dc2626",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_float(value: str | None) -> float:
    if value in (None, ""):
        return math.nan
    return float(value)


def case_order(rows: list[dict[str, str]]) -> list[str]:
    cases: list[str] = []
    for row in rows:
        if row["case_name"] not in cases:
            cases.append(row["case_name"])
    return cases


def grouped_metric_plot(rows: list[dict[str, str]], cases: list[str], metric: str, ylabel: str, title: str, filename: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.5))
    x_values = list(range(len(cases)))
    width = 0.18
    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
    for solver, offset in zip(SOLVER_ORDER, offsets):
        values = []
        for case in cases:
            match = next(row for row in rows if row["case_name"] == case and row["solver_config"] == solver)
            values.append(as_float(match[metric]))
        ax.bar([x + offset for x in x_values], values, width=width, label=SOLVER_LABELS[solver], color=SOLVER_COLORS[solver])
    ax.set_yscale("log")
    ax.set_xticks(x_values)
    ax.set_xticklabels(cases, rotation=18, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, axis="y", which="both", alpha=0.25)
    ax.legend(ncols=2)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / filename, dpi=160)
    plt.close(fig)


def grouped_second_bob_plot(timeseries: list[dict[str, str]], cases: list[str]) -> None:
    values_by_run: dict[tuple[str, str], float] = {}
    for row in timeseries:
        key = (row["case_name"], row["solver_config"])
        values_by_run[key] = max(values_by_run.get(key, 0.0), as_float(row["second_bob_position_diff"]))

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x_values = list(range(len(cases)))
    width = 0.18
    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
    for solver, offset in zip(SOLVER_ORDER, offsets):
        values = [values_by_run[(case, solver)] for case in cases]
        ax.bar([x + offset for x in x_values], values, width=width, label=SOLVER_LABELS[solver], color=SOLVER_COLORS[solver])
    ax.set_yscale("log")
    ax.set_xticks(x_values)
    ax.set_xticklabels(cases, rotation=18, ha="right")
    ax.set_ylabel("max second-bob position drift")
    ax.set_title("Max second-bob position drift by case and solver")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    ax.legend(ncols=2)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "max_second_bob_position_drift.png", dpi=160)
    plt.close(fig)


def cost_vs_accuracy(rows: list[dict[str, str]]) -> None:
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for solver in SOLVER_ORDER:
        x_values = []
        y_values = []
        for row in rows:
            if row["solver_config"] == solver:
                x_values.append(as_float(row["lagrangian_nfev"]) + as_float(row["hamiltonian_nfev"]))
                y_values.append(as_float(row["max_abs_theta_diff_rad"]))
        ax.scatter(x_values, y_values, label=SOLVER_LABELS[solver], color=SOLVER_COLORS[solver], s=48)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("total function evaluations (Lagrangian + Hamiltonian)")
    ax.set_ylabel("max angular drift (rad)")
    ax.set_title("Solver cost versus Lagrangian/Hamiltonian agreement")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "solver_cost_vs_accuracy.png", dpi=160)
    plt.close(fig)


def screenshot_timeseries(timeseries: list[dict[str, str]]) -> None:
    rows = [
        row for row in timeseries
        if row["case_name"] == "screenshot_like_simple_start"
        and row["solver_config"] in ("solve_ivp_default", "dop853_reference")
    ]
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for solver in ("solve_ivp_default", "dop853_reference"):
        solver_rows = [row for row in rows if row["solver_config"] == solver]
        t_values = [as_float(row["t"]) for row in solver_rows]
        theta = [as_float(row["max_abs_theta_diff_rad"]) for row in solver_rows]
        position = [as_float(row["second_bob_position_diff"]) for row in solver_rows]
        axes[0].plot(t_values, theta, label=SOLVER_LABELS[solver], color=SOLVER_COLORS[solver])
        axes[1].plot(t_values, position, label=SOLVER_LABELS[solver], color=SOLVER_COLORS[solver])
    axes[0].set_yscale("log")
    axes[1].set_yscale("log")
    axes[0].set_ylabel("max angular drift (rad)")
    axes[1].set_ylabel("second-bob drift")
    axes[1].set_xlabel("time (s)")
    axes[0].set_title("Screenshot-like simple case: default vs tight DOP853 reference")
    for ax in axes:
        ax.grid(True, which="both", alpha=0.25)
        ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "screenshot_like_default_vs_reference_timeseries.png", dpi=160)
    plt.close(fig)


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

This notebook inspects the existing simple-model drift evidence in `development/math_fidelity/logs/`. It treats the generated logs as the source of truth and does not rerun simulations by default."""
        ),
        md_cell(
            """## 1. Load Generated Logs

Load the compact run-level table and the long-format time-series table with pandas. If this cell fails with `ModuleNotFoundError: pandas`, use a notebook kernel with pandas installed. The production app runtime does not need pandas."""
        ),
        code_cell(
            """from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

LAB_ROOT = Path("development/math_fidelity")
LOG_DIR = LAB_ROOT / "logs"
FIGURE_DIR = LAB_ROOT / "reports" / "figures"

runs = pd.read_csv(LOG_DIR / "simple_drift_results.csv")
timeseries = pd.read_csv(LOG_DIR / "timeseries" / "simple_drift_timeseries_long.csv")

SOLVER_ORDER = ["solve_ivp_default", "rk45_strict", "dop853_strict", "dop853_reference"]
SOLVER_LABELS = {
    "solve_ivp_default": "default",
    "rk45_strict": "RK45 strict",
    "dop853_strict": "DOP853 strict",
    "dop853_reference": "DOP853 reference",
}

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
            """## 3. Summary Visualisations

These plots summarize the run-level evidence. Log-scaled y-axes make the tolerance-driven collapse in drift easier to see."""
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
            """## 7. Static Figures

A small set of PNG figures has been generated under `development/math_fidelity/reports/figures/` for quick sharing outside the notebook."""
        ),
        code_cell("""sorted(FIGURE_DIR.glob("*.png"))"""),
        md_cell(
            """## 8. Interpretation

The plots make the same pattern visible from several angles: default `solve_ivp` can produce substantial Lagrangian/Hamiltonian disagreement for the simple model, while strict RK45 and DOP853 configurations collapse that drift by many orders of magnitude. Position drift and energy drift follow the same broad tolerance pattern.

The evidence remains scoped: these logs cover short simple-model runs only. They support solver/tolerance sensitivity as the main explanation for the observed simple-model drift, but they do not settle compound-model fidelity, long-duration chaotic validity, or production solver-policy decisions."""
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
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_csv(LOG_DIR / "simple_drift_results.csv")
    timeseries = read_csv(TIMESERIES_CSV)
    cases = case_order(rows)
    grouped_metric_plot(rows, cases, "max_abs_theta_diff_rad", "max angular drift (rad)", "Max angular drift by case and solver", "max_angular_drift_by_case_solver.png")
    grouped_metric_plot(rows, cases, "lagrangian_max_abs_energy_drift", "max Lagrangian energy drift", "Lagrangian energy drift by case and solver", "lagrangian_energy_drift_by_case_solver.png")
    grouped_second_bob_plot(timeseries, cases)
    cost_vs_accuracy(rows)
    screenshot_timeseries(timeseries)
    build_notebook()
    print(f"Wrote notebook: {NOTEBOOK_PATH}")
    for figure in sorted(FIGURE_DIR.glob("*.png")):
        print(f"Wrote figure: {figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
