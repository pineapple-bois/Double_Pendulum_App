"""Render the bounded initial-theta1 finite-time stretching sweep."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from sweep import (
    SweepSampleStatus,
    Theta1SweepResult,
    Theta1SweepSpec,
    run_theta1_sweep,
)


PROTOTYPE_ROOT = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = PROTOTYPE_ROOT / "outputs"
DEFAULT_FIGURE_PATH = OUTPUT_DIRECTORY / "theta1_finite_time_sweep.png"
DEFAULT_DATA_PATH = OUTPUT_DIRECTORY / "theta1_finite_time_sweep.json"

DEMONSTRATION_SPEC = Theta1SweepSpec(
    theta1_degrees=tuple(np.linspace(169.0, 189.0, 15))
)


def build_figure(result: Theta1SweepResult) -> Figure:
    """Plot valid rates and visibly distinguish invalid or failed samples."""

    theta1 = result.theta1_degrees
    rates = result.finite_time_stretching_rates
    valid = result.valid_mask
    completed_invalid = np.asarray(
        [
            sample.status is SweepSampleStatus.COMPLETED_INVALID
            for sample in result.samples
        ]
    )
    execution_error = np.asarray(
        [sample.status is SweepSampleStatus.EXECUTION_ERROR for sample in result.samples]
    )
    invalid_with_rate = completed_invalid & np.isfinite(rates)
    invalid_without_rate = completed_invalid & ~np.isfinite(rates)

    figure, axis = plt.subplots(figsize=(9.5, 5.5), constrained_layout=True)
    valid_rates = np.where(valid, rates, np.nan)
    axis.plot(
        theta1,
        valid_rates,
        color="#386FA4",
        marker="o",
        markersize=5,
        linewidth=1.6,
        label="completed and numerically valid",
    )
    if np.any(invalid_with_rate):
        axis.scatter(
            theta1[invalid_with_rate],
            rates[invalid_with_rate],
            color="#D97706",
            marker="x",
            s=60,
            label="completed but numerically invalid",
            zorder=3,
        )
    if np.any(invalid_without_rate):
        axis.scatter(
            theta1[invalid_without_rate],
            np.full(np.count_nonzero(invalid_without_rate), 0.08),
            transform=axis.get_xaxis_transform(),
            color="#D97706",
            marker="x",
            s=60,
            label="numerically invalid without finite rate (axis marker)",
            zorder=3,
        )
    if np.any(execution_error):
        axis.scatter(
            theta1[execution_error],
            np.full(np.count_nonzero(execution_error), 0.04),
            transform=axis.get_xaxis_transform(),
            color="#B91C1C",
            marker="x",
            s=60,
            label="execution error (axis marker)",
            zorder=3,
        )

    observable = result.spec.observable_spec
    fixed = observable.initial_state
    tangent = ",".join(f"{component:g}" for component in observable.initial_tangent)
    axis.axhline(0.0, color="0.5", linewidth=0.8, linestyle=":")
    axis.set(
        title=(
            "One-vector finite-time stretching sweep "
            rf"($T={observable.duration:g}\,\mathrm{{s}}$; not asymptotic)"
            "\n"
            rf"fixed: $\theta_2(0)={np.rad2deg(fixed.theta2):g}^\circ$, "
            rf"$(\omega_1(0),\omega_2(0))=({fixed.omega1:g},{fixed.omega2:g})$, "
            rf"$\delta x_0=({tangent})$, "
            rf"$\tau={observable.renormalization_interval:g}\,\mathrm{{s}}$"
        ),
        xlabel=r"initial angle $\theta_1(0)$ (degrees)",
        ylabel=r"$\Lambda_T^{(1)}$ (s$^{-1}$)",
    )
    axis.grid(alpha=0.22, linewidth=0.7)
    axis.legend(loc="best")
    return figure


def result_payload(result: Theta1SweepResult) -> dict[str, object]:
    """Return a JSON-ready record of values, provenance, validity, and timing."""

    return {
        "observable": (
            "one-vector Candidate-A fixed-horizon finite-time stretching rate"
        ),
        "asymptotic_convergence_claimed": False,
        "sweep_coordinate": result.spec.coordinate_name,
        "sweep_coordinate_unit": result.spec.coordinate_unit,
        "theta1_degrees": list(result.spec.theta1_degrees),
        "fixed_observable_specification": asdict(result.spec.observable_spec),
        "timing": {
            "total_elapsed_seconds": result.elapsed_seconds,
            "mean_seconds_per_sample": result.mean_seconds_per_sample,
            "sample_count": result.sample_count,
        },
        "samples": [
            {
                "index": sample.index,
                "theta1_degrees": sample.theta1_degrees,
                "initial_state_radians": asdict(sample.initial_state),
                "status": sample.status.value,
                "finite_time_stretching_rate_per_second": (
                    sample.finite_time_stretching_rate
                ),
                "elapsed_seconds": sample.elapsed_seconds,
                "maximum_normalized_reference_energy_drift": (
                    sample.maximum_normalized_reference_energy_drift
                ),
                "maximum_post_renormalization_norm_error": (
                    sample.maximum_post_renormalization_norm_error
                ),
                "solver_function_evaluations": sample.solver_function_evaluations,
                "validity_issues": list(sample.validity_issues),
                "error_type": sample.error_type,
                "error_message": sample.error_message,
            }
            for sample in result.samples
        ],
    }


def save_deliverables(
    result: Theta1SweepResult,
    *,
    figure_path: Path = DEFAULT_FIGURE_PATH,
    data_path: Path = DEFAULT_DATA_PATH,
) -> tuple[Path, Path]:
    """Write the diagnostic figure and inspectable data record."""

    figure_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    figure = build_figure(result)
    figure.savefig(figure_path, dpi=160)
    plt.close(figure)
    with data_path.open("w", encoding="utf-8") as output:
        json.dump(result_payload(result), output, indent=2, allow_nan=False)
        output.write("\n")
    return figure_path, data_path


def main() -> int:
    result = run_theta1_sweep(DEMONSTRATION_SPEC)
    save_deliverables(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
