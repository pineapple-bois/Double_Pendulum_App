"""Minimal Hamiltonian Poincare-section sandbox experiment.

This module is intentionally self-contained under development/chaos_content.
It does not import the production Dash app and does not import historic
development/chaos_branch code.

The experiment is fidelity-first rather than feature-rich:

- simple double pendulum only;
- canonical Hamiltonian state: (theta1, theta2, p_theta1, p_theta2);
- Poincare section: theta1 mod 2*pi = 0 with theta1 increasing;
- section point: (wrapped theta2, p_theta2);
- solver and energy-drift failures are explicit.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class SimplePendulumParameters:
    """Physical parameters for the simple double pendulum."""

    m1: float = 1.0
    m2: float = 1.0
    l1: float = 1.0
    l2: float = 1.0
    g: float = 9.81


@dataclass(frozen=True)
class SolverPolicy:
    """Numerical integration policy for this sandbox experiment."""

    method: str = "DOP853"
    rtol: float = 1e-11
    atol: float = 1e-13
    t_start: float = 0.0
    t_stop: float = 30.0
    sample_count: int = 3001
    max_relative_energy_drift: float = 1e-7


@dataclass(frozen=True)
class InitialConditionPolicy:
    """Initial state policy stated in angles/velocities, then converted to p."""

    theta1_degrees: float = 120.0
    theta2_degrees: float = -10.0
    theta1_dot: float = 0.0
    theta2_dot: float = 0.0


@dataclass(frozen=True)
class PoincareSectionPolicy:
    """Poincare section convention."""

    section_coordinate: str = "theta1"
    section_value: float = 0.0
    event_function: str = "sin(theta1)"
    angular_filter: str = "cos(theta1) > 0"
    crossing_direction: str = "increasing"
    discard_before: float = 0.0
    min_crossings_for_plot: int = 50
    plotted_coordinate: str = "theta2_wrapped"
    plotted_momentum: str = "p_theta2"


@dataclass(frozen=True)
class PoincarePoint:
    """One accepted interpolated section point."""

    time: float
    theta2_wrapped: float
    p_theta2: float
    energy: float
    relative_energy_drift: float


@dataclass(frozen=True)
class ExperimentResult:
    """Serializable summary of one experiment run."""

    success: bool
    failure_reason: str | None
    parameters: dict[str, float]
    solver_policy: dict[str, float | int | str]
    initial_condition_policy: dict[str, float]
    section_policy: dict[str, float | str]
    initial_state: list[float]
    initial_energy: float
    max_relative_energy_drift: float | None
    accepted_crossing_count: int
    rejected_crossing_count: int
    raw_event_count: int
    first_points: list[dict[str, float]]


@dataclass(frozen=True)
class ExperimentRun:
    """Internal run data retained for diagnostics and output bundles."""

    summary: ExperimentResult
    times: np.ndarray
    states: np.ndarray
    energies: np.ndarray
    relative_energy_drifts: np.ndarray
    poincare_points: list[PoincarePoint]
    raw_event_count: int
    rejected_crossing_count: int
    plot_met_minimum_crossing_threshold: bool


def inertia_matrix(theta1: float, theta2: float, params: SimplePendulumParameters) -> np.ndarray:
    """Return the 2x2 simple-pendulum inertia matrix B(q)."""

    delta = theta1 - theta2
    return np.array(
        [
            [(params.m1 + params.m2) * params.l1**2, params.m2 * params.l1 * params.l2 * math.cos(delta)],
            [params.m2 * params.l1 * params.l2 * math.cos(delta), params.m2 * params.l2**2],
        ],
        dtype=float,
    )


def momenta_from_angles_and_velocities(
    theta1: float,
    theta2: float,
    theta1_dot: float,
    theta2_dot: float,
    params: SimplePendulumParameters,
) -> tuple[float, float]:
    """Convert angular velocities to canonical momenta using p = B(q) qdot."""

    momenta = inertia_matrix(theta1, theta2, params) @ np.array([theta1_dot, theta2_dot], dtype=float)
    return float(momenta[0]), float(momenta[1])


def initial_state_from_policy(
    policy: InitialConditionPolicy,
    params: SimplePendulumParameters,
) -> np.ndarray:
    """Build the canonical Hamiltonian state from the stated initial policy."""

    theta1 = math.radians(policy.theta1_degrees)
    theta2 = math.radians(policy.theta2_degrees)
    p_theta1, p_theta2 = momenta_from_angles_and_velocities(
        theta1,
        theta2,
        policy.theta1_dot,
        policy.theta2_dot,
        params,
    )
    return np.array([theta1, theta2, p_theta1, p_theta2], dtype=float)


def hamiltonian(state: Iterable[float], params: SimplePendulumParameters) -> float:
    """Return H(q, p) = 0.5 * p.T * B(q)^-1 * p + V(q)."""

    theta1, theta2, p_theta1, p_theta2 = [float(value) for value in state]
    momenta = np.array([p_theta1, p_theta2], dtype=float)
    velocities = np.linalg.solve(inertia_matrix(theta1, theta2, params), momenta)
    kinetic = 0.5 * float(momenta @ velocities)
    potential = (
        -(params.m1 + params.m2) * params.g * params.l1 * math.cos(theta1)
        - params.m2 * params.g * params.l2 * math.cos(theta2)
    )
    return kinetic + potential


def angular_velocities(state: Iterable[float], params: SimplePendulumParameters) -> tuple[float, float]:
    """Return (theta1_dot, theta2_dot) from canonical momenta."""

    theta1, theta2, p_theta1, p_theta2 = [float(value) for value in state]
    velocities = np.linalg.solve(
        inertia_matrix(theta1, theta2, params),
        np.array([p_theta1, p_theta2], dtype=float),
    )
    return float(velocities[0]), float(velocities[1])


def hamiltonian_rhs(_time: float, state: np.ndarray, params: SimplePendulumParameters) -> np.ndarray:
    """Analytical Hamiltonian right-hand side for the simple double pendulum."""

    theta1, theta2, p_theta1, p_theta2 = [float(value) for value in state]
    theta1_dot, theta2_dot = angular_velocities(state, params)

    delta = theta1 - theta2
    sin_delta = math.sin(delta)
    cos_delta = math.cos(delta)
    d = params.m1 + params.m2 * sin_delta**2

    numerator = (
        params.m2 * params.l2**2 * p_theta1**2
        - 2.0 * params.m2 * params.l1 * params.l2 * cos_delta * p_theta1 * p_theta2
        + (params.m1 + params.m2) * params.l1**2 * p_theta2**2
    )
    numerator_prime = 2.0 * params.m2 * params.l1 * params.l2 * sin_delta * p_theta1 * p_theta2
    d_prime = 2.0 * params.m2 * sin_delta * cos_delta
    denominator_factor = 2.0 * params.m2 * params.l1**2 * params.l2**2

    kinetic_delta_gradient = (
        (numerator_prime * d - numerator * d_prime)
        / (denominator_factor * d**2)
    )

    p_theta1_dot = (
        -kinetic_delta_gradient
        - (params.m1 + params.m2) * params.g * params.l1 * math.sin(theta1)
    )
    p_theta2_dot = (
        kinetic_delta_gradient
        - params.m2 * params.g * params.l2 * math.sin(theta2)
    )

    return np.array([theta1_dot, theta2_dot, p_theta1_dot, p_theta2_dot], dtype=float)


def wrap_angle_pi(angle: float) -> float:
    """Wrap an angle to [-pi, pi)."""

    return (float(angle) + math.pi) % (2.0 * math.pi) - math.pi


def relative_energy_drift(energy: float, initial_energy: float) -> float:
    """Compute a scale-safe relative Hamiltonian drift."""

    return abs(float(energy) - float(initial_energy)) / max(abs(float(initial_energy)), 1.0)


def extract_poincare_points(
    crossing_times: np.ndarray,
    crossing_states: np.ndarray,
    params: SimplePendulumParameters,
    section_policy: PoincareSectionPolicy,
    initial_energy: float,
) -> tuple[list[PoincarePoint], int]:
    """Convert solver-located sin(theta1)=0 events into Poincare points."""

    if section_policy.section_coordinate != "theta1":
        raise ValueError("Only theta1 section extraction is implemented.")
    if section_policy.crossing_direction != "increasing":
        raise ValueError("Only increasing crossings are implemented.")
    if section_policy.event_function != "sin(theta1)":
        raise ValueError("Only sin(theta1) section events are implemented.")

    points: list[PoincarePoint] = []
    rejected_count = 0

    for crossing_time, crossing_state in zip(crossing_times, crossing_states):
        theta1_dot, _theta2_dot = angular_velocities(crossing_state, params)
        if crossing_time < section_policy.discard_before:
            rejected_count += 1
            continue
        if math.cos(float(crossing_state[0])) <= 0.0:
            rejected_count += 1
            continue
        if theta1_dot <= 0.0:
            rejected_count += 1
            continue

        energy = hamiltonian(crossing_state, params)
        points.append(
            PoincarePoint(
                time=crossing_time,
                theta2_wrapped=wrap_angle_pi(crossing_state[1]),
                p_theta2=float(crossing_state[3]),
                energy=energy,
                relative_energy_drift=relative_energy_drift(energy, initial_energy),
            )
        )

    return points, rejected_count


def _empty_series() -> tuple[np.ndarray, np.ndarray]:
    """Return empty energy and drift series for failed early runs."""

    return np.array([], dtype=float), np.array([], dtype=float)


def _summary(
    *,
    success: bool,
    failure_reason: str | None,
    max_relative_energy_drift: float | None,
    points: list[PoincarePoint],
    rejected_crossing_count: int,
    raw_event_count: int,
    base_result: dict[str, object],
) -> ExperimentResult:
    """Build the compact public result summary."""

    return ExperimentResult(
        success=success,
        failure_reason=failure_reason,
        max_relative_energy_drift=max_relative_energy_drift,
        accepted_crossing_count=len(points) if success else 0,
        rejected_crossing_count=rejected_crossing_count,
        raw_event_count=raw_event_count,
        first_points=[asdict(point) for point in points[:5]] if success else [],
        **base_result,
    )


def run_experiment_data(
    params: SimplePendulumParameters | None = None,
    solver_policy: SolverPolicy | None = None,
    initial_condition_policy: InitialConditionPolicy | None = None,
    section_policy: PoincareSectionPolicy | None = None,
) -> ExperimentRun:
    """Run the experiment and retain full diagnostic data internally."""

    params = params or SimplePendulumParameters()
    solver_policy = solver_policy or SolverPolicy()
    initial_condition_policy = initial_condition_policy or InitialConditionPolicy()
    section_policy = section_policy or PoincareSectionPolicy()

    initial_state = initial_state_from_policy(initial_condition_policy, params)
    initial_energy = hamiltonian(initial_state, params)
    times = np.linspace(solver_policy.t_start, solver_policy.t_stop, solver_policy.sample_count)

    def section_event(_time: float, state: np.ndarray) -> float:
        return math.sin(float(state[0] - section_policy.section_value))

    section_event.terminal = False
    section_event.direction = 0.0

    solution = solve_ivp(
        fun=lambda time, state: hamiltonian_rhs(time, state, params),
        t_span=(solver_policy.t_start, solver_policy.t_stop),
        y0=initial_state,
        method=solver_policy.method,
        t_eval=times,
        rtol=solver_policy.rtol,
        atol=solver_policy.atol,
        events=section_event,
    )

    base_result = {
        "parameters": asdict(params),
        "solver_policy": asdict(solver_policy),
        "initial_condition_policy": asdict(initial_condition_policy),
        "section_policy": asdict(section_policy),
        "initial_state": initial_state.tolist(),
        "initial_energy": initial_energy,
    }

    states = solution.y.T if solution.y.size else np.empty((0, 4), dtype=float)
    if not solution.success:
        energies, drifts = _empty_series()
        return ExperimentRun(
            summary=_summary(
                success=False,
                failure_reason=f"solver_failed: {solution.message}",
                max_relative_energy_drift=None,
                points=[],
                rejected_crossing_count=0,
                raw_event_count=0,
                base_result=base_result,
            ),
            times=solution.t,
            states=states,
            energies=energies,
            relative_energy_drifts=drifts,
            poincare_points=[],
            raw_event_count=0,
            rejected_crossing_count=0,
            plot_met_minimum_crossing_threshold=False,
        )

    if not np.all(np.isfinite(states)):
        energies, drifts = _empty_series()
        return ExperimentRun(
            summary=_summary(
                success=False,
                failure_reason="non_finite_state_values",
                max_relative_energy_drift=None,
                points=[],
                rejected_crossing_count=0,
                raw_event_count=0,
                base_result=base_result,
            ),
            times=solution.t,
            states=states,
            energies=energies,
            relative_energy_drifts=drifts,
            poincare_points=[],
            raw_event_count=0,
            rejected_crossing_count=0,
            plot_met_minimum_crossing_threshold=False,
        )

    energies = np.array([hamiltonian(state, params) for state in states], dtype=float)
    drifts = np.array([relative_energy_drift(energy, initial_energy) for energy in energies], dtype=float)
    max_drift = float(np.max(drifts))

    crossing_times = solution.t_events[0] if solution.t_events else np.array([], dtype=float)
    crossing_states = solution.y_events[0] if solution.y_events else np.empty((0, 4), dtype=float)
    raw_event_count = int(len(crossing_times))
    points, rejected_crossing_count = extract_poincare_points(
        crossing_times,
        crossing_states,
        params,
        section_policy,
        initial_energy,
    )
    point_drifts = [point.relative_energy_drift for point in points]
    max_point_drift = max(point_drifts) if point_drifts else 0.0
    max_drift = max(max_drift, float(max_point_drift))
    plot_met_minimum = len(points) >= section_policy.min_crossings_for_plot

    if max_drift > solver_policy.max_relative_energy_drift:
        return ExperimentRun(
            summary=_summary(
                success=False,
                failure_reason=(
                    "energy_drift_exceeded: "
                    f"{max_drift:.3e} > {solver_policy.max_relative_energy_drift:.3e}"
                ),
                max_relative_energy_drift=max_drift,
                points=points,
                rejected_crossing_count=rejected_crossing_count,
                raw_event_count=raw_event_count,
                base_result=base_result,
            ),
            times=solution.t,
            states=states,
            energies=energies,
            relative_energy_drifts=drifts,
            poincare_points=points,
            raw_event_count=raw_event_count,
            rejected_crossing_count=rejected_crossing_count,
            plot_met_minimum_crossing_threshold=plot_met_minimum,
        )

    if not points:
        return ExperimentRun(
            summary=_summary(
                success=False,
                failure_reason="no_accepted_poincare_crossings",
                max_relative_energy_drift=max_drift,
                points=[],
                rejected_crossing_count=rejected_crossing_count,
                raw_event_count=raw_event_count,
                base_result=base_result,
            ),
            times=solution.t,
            states=states,
            energies=energies,
            relative_energy_drifts=drifts,
            poincare_points=[],
            raw_event_count=raw_event_count,
            rejected_crossing_count=rejected_crossing_count,
            plot_met_minimum_crossing_threshold=False,
        )

    return ExperimentRun(
        summary=_summary(
            success=True,
            failure_reason=None,
            max_relative_energy_drift=max_drift,
            points=points,
            rejected_crossing_count=rejected_crossing_count,
            raw_event_count=raw_event_count,
            base_result=base_result,
        ),
        times=solution.t,
        states=states,
        energies=energies,
        relative_energy_drifts=drifts,
        poincare_points=points,
        raw_event_count=raw_event_count,
        rejected_crossing_count=rejected_crossing_count,
        plot_met_minimum_crossing_threshold=plot_met_minimum,
    )


def run_experiment(
    params: SimplePendulumParameters | None = None,
    solver_policy: SolverPolicy | None = None,
    initial_condition_policy: InitialConditionPolicy | None = None,
    section_policy: PoincareSectionPolicy | None = None,
) -> ExperimentResult:
    """Run the minimal experiment and return the compact public summary."""

    return run_experiment_data(
        params=params,
        solver_policy=solver_policy,
        initial_condition_policy=initial_condition_policy,
        section_policy=section_policy,
    ).summary


def _write_json(path: Path, data: object) -> None:
    """Write deterministic JSON for sandbox diagnostics."""

    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_poincare_points_csv(path: Path, points: list[PoincarePoint]) -> None:
    """Write all accepted section points to CSV."""

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["time", "theta2_wrapped", "p_theta2", "energy", "relative_energy_drift"],
        )
        writer.writeheader()
        for point in points:
            writer.writerow(asdict(point))


def _load_pyplot():
    """Load matplotlib with a non-interactive backend."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _write_poincare_plot(path: Path, run: ExperimentRun) -> None:
    """Write wrapped theta2 against p_theta2 for all accepted points."""

    plt = _load_pyplot()
    theta2 = [point.theta2_wrapped for point in run.poincare_points]
    p_theta2 = [point.p_theta2 for point in run.poincare_points]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(theta2, p_theta2, s=4, alpha=0.75, linewidths=0)
    ax.set_xlabel("theta2 wrapped / radians")
    ax.set_ylabel("p_theta2")
    plot_kind = "long-run" if run.plot_met_minimum_crossing_threshold else "smoke-test"
    ax.set_title(f"Sandbox diagnostic: {plot_kind} Poincare section")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _write_energy_drift_plot(path: Path, run: ExperimentRun) -> None:
    """Write relative Hamiltonian drift over solver sample time."""

    plt = _load_pyplot()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(run.times, run.relative_energy_drifts, linewidth=1.25)
    ax.set_xlabel("time / seconds")
    ax.set_ylabel("relative Hamiltonian drift")
    ax.set_title("Sandbox diagnostic: relative energy drift")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _write_theta_timeseries_plot(path: Path, run: ExperimentRun) -> None:
    """Write raw theta1 and theta2 over solver sample time."""

    plt = _load_pyplot()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(run.times, run.states[:, 0], label="theta1", linewidth=1.0)
    ax.plot(run.times, run.states[:, 1], label="theta2", linewidth=1.0)
    ax.set_xlabel("time / seconds")
    ax.set_ylabel("raw angle / radians")
    ax.set_title("Sandbox diagnostic: raw theta time series")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_output_bundle(run: ExperimentRun, output_dir: Path, include_plots: bool) -> list[Path]:
    """Write a reproducible sandbox output bundle."""

    output_dir.mkdir(parents=True, exist_ok=True)
    created_files: list[Path] = []

    summary_path = output_dir / "summary.json"
    _write_json(summary_path, asdict(run.summary))
    created_files.append(summary_path)

    csv_path = output_dir / "poincare_points.csv"
    _write_poincare_points_csv(csv_path, run.poincare_points if run.summary.success else [])
    created_files.append(csv_path)

    if include_plots:
        if not run.plot_met_minimum_crossing_threshold:
            print(
                "WARNING: accepted Poincare crossings "
                f"({run.summary.accepted_crossing_count}) are below min_crossings_for_plot "
                f"({run.summary.section_policy['min_crossings_for_plot']}); "
                "plots are smoke-test diagnostics only.",
                file=sys.stderr,
            )

        mpl_config_dir = output_dir / ".matplotlib"
        xdg_cache_dir = output_dir / ".cache"
        mpl_config_dir.mkdir(exist_ok=True)
        xdg_cache_dir.mkdir(exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(mpl_config_dir))
        os.environ.setdefault("XDG_CACHE_HOME", str(xdg_cache_dir))

        plot_writers = [
            ("poincare_section.png", _write_poincare_plot),
            ("energy_drift.png", _write_energy_drift_plot),
            ("theta_timeseries.png", _write_theta_timeseries_plot),
        ]
        for filename, writer in plot_writers:
            plot_path = output_dir / filename
            writer(plot_path, run)
            created_files.append(plot_path)

    manifest_path = output_dir / "manifest.json"
    manifest = {
        "artifact": "minimal_hamiltonian_poincare",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_succeeded": run.summary.success,
        "failure_reason": run.summary.failure_reason,
        "run_classification": (
            "long_run_diagnostic"
            if run.plot_met_minimum_crossing_threshold
            else "smoke_test_output"
        ),
        "accepted_crossing_count": run.summary.accepted_crossing_count,
        "rejected_crossing_count": run.rejected_crossing_count,
        "raw_event_count": run.raw_event_count,
        "discard_before": run.summary.section_policy["discard_before"],
        "max_relative_energy_drift": run.summary.max_relative_energy_drift,
        "min_crossings_for_plot": run.summary.section_policy["min_crossings_for_plot"],
        "plot_met_minimum_crossing_threshold": run.plot_met_minimum_crossing_threshold,
        "created_files": [path.name for path in [manifest_path, *created_files]],
        "policies": {
            "parameters": run.summary.parameters,
            "solver": run.summary.solver_policy,
            "initial_conditions": run.summary.initial_condition_policy,
            "section": run.summary.section_policy,
        },
        "conventions": {
            "state": "(theta1, theta2, p_theta1, p_theta2)",
            "angles": "raw radians from downward vertical; theta2 is wrapped only for section output",
            "momenta": "canonical Hamiltonian momenta from p = B(q) qdot",
            "event_convention": "sin(theta1 - section_value) = 0",
            "crossing_filter": "cos(theta1 - section_value) > 0 and theta1_dot > 0",
            "section": "theta1 mod 2*pi = 0 with theta1 increasing",
            "transient_discard": "events with time < discard_before are rejected before plotting",
            "energy_drift": "abs(H(t) - H0) / max(abs(H0), 1.0)",
        },
        "notes": [
            "Sandbox diagnostic output only; not a production app asset.",
            "Generated files are reproducible and ignored by development/chaos_content/outputs/.gitignore.",
        ],
    }
    _write_json(manifest_path, manifest)
    return [manifest_path, *created_files]


def _assert_self_check(run: ExperimentRun) -> None:
    """Run lightweight assertions suitable for this sandbox artifact."""

    result = run.summary
    if not result.success:
        raise AssertionError(f"Experiment failed: {result.failure_reason}")
    if result.accepted_crossing_count < 1:
        raise AssertionError("Expected at least one accepted Poincare crossing.")
    if result.max_relative_energy_drift is None:
        raise AssertionError("Expected an energy-drift measurement.")
    if result.max_relative_energy_drift > result.solver_policy["max_relative_energy_drift"]:
        raise AssertionError("Energy drift exceeded the stated solver policy.")
    first = result.first_points[0]
    if not (-math.pi <= first["theta2_wrapped"] < math.pi):
        raise AssertionError("Wrapped theta2 is outside [-pi, pi).")


def run_self_check() -> ExperimentResult:
    """Run the experiment, assert expected diagnostics, and return the summary."""

    run = run_experiment_data()
    _assert_self_check(run)
    return run.summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="run lightweight assertions")
    parser.add_argument("--output-dir", type=Path, help="optional directory for a sandbox output bundle")
    parser.add_argument("--plots", action="store_true", help="write diagnostic PNG plots with --output-dir")
    parser.add_argument("--t-stop", type=float, default=SolverPolicy.t_stop, help="integration stop time")
    parser.add_argument("--sample-count", type=int, default=SolverPolicy.sample_count, help="number of solver samples")
    parser.add_argument(
        "--discard-before",
        type=float,
        default=PoincareSectionPolicy.discard_before,
        help="discard accepted section events before this time",
    )
    parser.add_argument(
        "--min-crossings-for-plot",
        type=int,
        default=PoincareSectionPolicy.min_crossings_for_plot,
        help="minimum accepted crossings before plot is classified as long-run diagnostic",
    )
    args = parser.parse_args()

    if args.plots and not args.output_dir:
        parser.error("--plots requires --output-dir")

    if args.t_stop <= 0:
        parser.error("--t-stop must be positive")
    if args.sample_count < 2:
        parser.error("--sample-count must be at least 2")
    if args.discard_before < 0:
        parser.error("--discard-before must be non-negative")
    if args.discard_before >= args.t_stop:
        parser.error("--discard-before must be less than --t-stop")
    if args.min_crossings_for_plot < 1:
        parser.error("--min-crossings-for-plot must be at least 1")

    solver_policy = SolverPolicy(t_stop=args.t_stop, sample_count=args.sample_count)
    section_policy = PoincareSectionPolicy(
        discard_before=args.discard_before,
        min_crossings_for_plot=args.min_crossings_for_plot,
    )

    run = run_experiment_data(solver_policy=solver_policy, section_policy=section_policy)
    if args.self_check:
        _assert_self_check(run)
    if args.output_dir:
        write_output_bundle(run, args.output_dir, include_plots=args.plots)

    print(json.dumps(asdict(run.summary), indent=2, sort_keys=True))
    return 0 if run.summary.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
