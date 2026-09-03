"""Render the Sensitivity-to-Lyapunov pedagogical figure.

Run from the repository root:

    uv run python -m development.chaos_content.prototypes.state_space_maps.runners.\
        render_sensitivity_to_lyapunov

Scientific calculations are provided by ``reference.py``. This module only
composes a structured result into the first visual deliverable of the strand,
written beneath the prototype-local ``outputs/lyapunov/`` directory.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ..src.lyapunov.reference import (
    SensitivityToLyapunovResult,
    run_sensitivity_to_lyapunov,
)


PROTOTYPE_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROTOTYPE_ROOT / "outputs" / "lyapunov"
DEFAULT_FIGURE_PATH = OUTPUT_DIRECTORY / "sensitivity_to_lyapunov.png"

PHYSICAL_COLOR = "#2A6F97"
FINITE_STATE_COLOR = "#C96D2D"
TANGENT_COLOR = "#2A9D8F"
LOG_STRETCH_COLOR = "#6A4C93"
RATE_COLOR = "#BC4749"


def build_figure(result: SensitivityToLyapunovResult) -> Figure:
    """Compose the four-stage pedagogical visual from a calculated result."""

    pair = result.finite_pair
    tangent = result.tangent
    time = pair.reference.time
    parameters = result.spec.parameters
    physical_bound = 2.0 * (parameters.length1 + parameters.length2)

    figure, axes = plt.subplots(
        2,
        2,
        figsize=(12, 8),
        constrained_layout=True,
    )
    cartesian, finite_state, local_tangent, log_rate = axes.ravel()

    cartesian.semilogy(
        time,
        pair.second_bob_separation,
        color=PHYSICAL_COLOR,
        linewidth=2.2,
        label=r"$d_{\mathrm{bob}}(t)$",
    )
    cartesian.text(
        0.04,
        0.92,
        rf"geometric bound: $d_{{\mathrm{{bob}}}}\leq {physical_bound:g}\,\mathrm{{m}}$",
        transform=cartesian.transAxes,
        va="top",
        color="0.35",
    )
    cartesian.set(
        title="1. Physical Cartesian separation",
        xlabel="time (s)",
        ylabel="second-bob distance (m)",
    )
    cartesian.legend(loc="lower right")

    finite_state.semilogy(
        time,
        pair.candidate_a_separation,
        color=FINITE_STATE_COLOR,
        linewidth=2.2,
        label=r"$d_{\mathrm{EL}}(t)$",
    )
    finite_state.axhline(
        result.spec.local_distance_ceiling,
        color="0.5",
        linestyle=":",
        linewidth=1.8,
        label="declared local ceiling",
    )
    finite_state.set(
        title="2. Finite Candidate-A state separation",
        xlabel="time (s)",
        ylabel="dimensionless distance",
    )
    finite_state.legend(loc="lower right")

    local_tangent.semilogy(
        time,
        tangent.candidate_a_norm,
        color=TANGENT_COLOR,
        linewidth=2.2,
        label=r"direct tangent $\|S\,\delta x(t)\|_2$",
    )
    local_tangent.semilogy(
        time,
        pair.normalized_candidate_a_separation,
        color=FINITE_STATE_COLOR,
        linestyle="--",
        linewidth=1.5,
        marker="o",
        markersize=3.5,
        markevery=12,
        label="normalised finite shadow",
    )
    local_tangent.set(
        title="3. Local tangent stretching",
        xlabel="time (s)",
        ylabel="Candidate-A magnitude",
    )
    local_tangent.legend(loc="upper left")

    log_line = log_rate.plot(
        time,
        tangent.log_stretch,
        color=LOG_STRETCH_COLOR,
        linewidth=2.2,
        label=r"$G(t)=\log[N(t)/N(0)]$",
    )
    log_rate.set(
        title="4. Finite-time logarithmic stretching and rate\n"
        "(not an asymptotic exponent)",
        xlabel="time (s)",
        ylabel="log stretch",
    )
    rate_axis = log_rate.twinx()
    rate_line = rate_axis.plot(
        time[1:],
        tangent.finite_time_rate[1:],
        color=RATE_COLOR,
        linewidth=2.0,
        label=r"$\Lambda(t)=G(t)/t$",
    )
    rate_axis.set_ylabel(r"finite-time rate (s$^{-1}$)")
    combined_lines = log_line + rate_line
    log_rate.legend(
        combined_lines,
        [line.get_label() for line in combined_lines],
        loc="lower right",
    )

    for axis in axes.ravel():
        axis.grid(alpha=0.2, linewidth=0.7)
    rate_axis.grid(False)

    figure.suptitle("Sensitivity to Lyapunov — validated local reference interval")
    return figure


def save_figure(result: SensitivityToLyapunovResult) -> Path:
    """Save the figure to the prototype-local untracked output directory."""

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    figure = build_figure(result)
    figure.savefig(DEFAULT_FIGURE_PATH, dpi=160)
    plt.close(figure)
    return DEFAULT_FIGURE_PATH


def main() -> int:
    result = run_sensitivity_to_lyapunov()
    save_figure(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
