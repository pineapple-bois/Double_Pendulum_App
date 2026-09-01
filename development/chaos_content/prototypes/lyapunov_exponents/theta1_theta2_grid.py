"""Render and persist the bounded initial-angle reference grid."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from grid import (
    Theta1Theta2GridResult,
    Theta1Theta2GridSpec,
    run_theta1_theta2_grid,
)
from development.chaos_content.prototypes.state_space_fields import (
    EvaluationStatus,
    RectangularCell,
)


PROTOTYPE_ROOT = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = PROTOTYPE_ROOT / "outputs"
DEFAULT_FIGURE_PATH = OUTPUT_DIRECTORY / "theta1_theta2_finite_time_grid.png"
DEFAULT_DATA_PATH = OUTPUT_DIRECTORY / "theta1_theta2_finite_time_grid.json"

SMOKE_SPEC = Theta1Theta2GridSpec(
    theta1_degrees=tuple(float(value) for value in np.linspace(169.0, 189.0, 4)),
    theta2_degrees=tuple(float(value) for value in np.linspace(169.0, 189.0, 4)),
)
DEMONSTRATION_SPEC = Theta1Theta2GridSpec(
    theta1_degrees=tuple(float(value) for value in np.linspace(169.0, 189.0, 9)),
    theta2_degrees=tuple(float(value) for value in np.linspace(169.0, 189.0, 9)),
)


def build_heatmap(result: Theta1Theta2GridResult) -> Figure:
    """Render theta1 horizontally and theta2 vertically without implicit flips."""

    theta1 = result.theta1_axis_degrees
    theta2 = result.theta2_axis_degrees
    valid_values = np.ma.masked_where(~result.valid_mask, result.values)
    colormap = plt.get_cmap("viridis").with_extremes(bad="#ECECEC")

    figure, axis = plt.subplots(figsize=(8.2, 6.8), constrained_layout=True)
    field = axis.pcolormesh(
        theta1,
        theta2,
        valid_values,
        shading="nearest",
        cmap=colormap,
    )
    figure.colorbar(
        field,
        ax=axis,
        label=r"$\Lambda_T^{(1)}$ (s$^{-1}$)",
    )

    invalid = result.statuses == EvaluationStatus.COMPLETED_INVALID.value
    failed = result.statuses == EvaluationStatus.EXECUTION_ERROR.value
    if np.any(invalid):
        invalid_theta2, invalid_theta1 = np.nonzero(invalid)
        axis.scatter(
            theta1[invalid_theta1],
            theta2[invalid_theta2],
            marker="x",
            color="#D97706",
            s=55,
            label="completed but numerically invalid",
        )
    if np.any(failed):
        failed_theta2, failed_theta1 = np.nonzero(failed)
        axis.scatter(
            theta1[failed_theta1],
            theta2[failed_theta2],
            marker="x",
            color="#B91C1C",
            s=55,
            label="execution error",
        )
    if np.any(invalid) or np.any(failed):
        axis.legend(loc="best")

    observable = result.spec.observable_spec
    tangent = ",".join(f"{component:g}" for component in observable.initial_tangent)
    axis.set(
        title=(
            "Initial-angle finite-time stretching reference grid "
            rf"($T={observable.duration:g}\,\mathrm{{s}}$; not asymptotic)"
            "\n"
            rf"fixed: $(\omega_1(0),\omega_2(0))="
            rf"({observable.initial_state.omega1:g},{observable.initial_state.omega2:g})$, "
            rf"$\delta x_0=({tangent})$, "
            rf"$\tau={observable.renormalization_interval:g}\,\mathrm{{s}}$"
        ),
        xlabel=r"initial angle $\theta_1(0)$ (degrees)",
        ylabel=r"initial angle $\theta_2(0)$ (degrees)",
    )
    axis.set_xlim(theta1[0], theta1[-1])
    axis.set_ylim(theta2[0], theta2[-1])
    return figure


def result_payload(result: Theta1Theta2GridResult) -> dict[str, object]:
    """Return a JSON-ready scalar field with provenance and cell diagnostics."""

    values = [
        [
            cell.evaluation.value
            for cell in row
        ]
        for row in result.cells
    ]
    return {
        "observable": (
            "one-vector Candidate-A fixed-horizon finite-time stretching rate"
        ),
        "asymptotic_convergence_claimed": False,
        "array_convention": (
            "values_per_second[theta2_index][theta1_index]"
        ),
        "shape": list(result.shape),
        "theta1_axis_degrees": list(result.spec.theta1_degrees),
        "theta2_axis_degrees": list(result.spec.theta2_degrees),
        "values_per_second": values,
        "statuses": result.statuses.tolist(),
        "fixed_observable_specification": asdict(result.spec.observable_spec),
        "timing": {
            "total_elapsed_seconds": result.elapsed_seconds,
            "mean_seconds_per_cell": result.mean_seconds_per_cell,
            "cell_count": result.cell_count,
        },
        "cells": [
            _cell_payload(result, cell) for row in result.cells for cell in row
        ],
    }


def _cell_payload(
    result: Theta1Theta2GridResult,
    cell: RectangularCell,
) -> dict[str, object]:
    evaluation = cell.evaluation
    diagnostics = evaluation.diagnostics
    initial_state = replace(
        result.spec.observable_spec.initial_state,
        theta1=math.radians(cell.x_coordinate),
        theta2=math.radians(cell.y_coordinate),
    )
    return {
        "theta2_index": cell.y_index,
        "theta1_index": cell.x_index,
        "theta2_degrees": cell.y_coordinate,
        "theta1_degrees": cell.x_coordinate,
        "initial_state_radians": asdict(initial_state),
        "status": evaluation.status.value,
        "finite_time_stretching_rate_per_second": evaluation.value,
        "elapsed_seconds": evaluation.elapsed_seconds,
        "evaluator": evaluation.evaluator,
        "maximum_normalized_reference_energy_drift": (
            None
            if diagnostics is None
            else diagnostics.maximum_normalized_reference_energy_drift
        ),
        "maximum_post_renormalization_norm_error": (
            None
            if diagnostics is None
            else diagnostics.maximum_post_renormalization_norm_error
        ),
        "solver_function_evaluations": (
            None if diagnostics is None else diagnostics.solver_function_evaluations
        ),
        "validity_issues": list(evaluation.validity_issues),
        "error_type": evaluation.error_type,
        "error_message": evaluation.error_message,
    }


def save_grid_data(
    result: Theta1Theta2GridResult,
    path: Path = DEFAULT_DATA_PATH,
) -> Path:
    """Persist the scalar field independently of any rendering."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        json.dump(result_payload(result), output, indent=2, allow_nan=False)
        output.write("\n")
    return path


def load_grid_data(path: Path = DEFAULT_DATA_PATH) -> dict[str, object]:
    """Reload one inspectable grid record without running the observable."""

    with path.open(encoding="utf-8") as source:
        return json.load(source)


def save_heatmap(
    result: Theta1Theta2GridResult,
    path: Path = DEFAULT_FIGURE_PATH,
) -> Path:
    """Render the heatmap independently from scalar-field persistence."""

    path.parent.mkdir(parents=True, exist_ok=True)
    figure = build_heatmap(result)
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return path


def main() -> int:
    result = run_theta1_theta2_grid(DEMONSTRATION_SPEC)
    save_grid_data(result)
    save_heatmap(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
