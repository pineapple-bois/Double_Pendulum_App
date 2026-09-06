"""Bounded long-horizon first-flip and energy-accessibility investigation.

This tool deliberately bypasses the production T=5 dispatch allowlist only at
an investigation-local call boundary.  It reuses the immutable corrected-v2
native DOP853 artifact, unchanged dynamics, solver tolerances, max-step policy,
event surfaces, diagnostics, and scientific gates.  No production eligibility
or fallback policy is changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import os
import platform
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Sequence

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ...src.first_flip.compiled import first_flip_compiled_eligibility
from ...src.first_flip.field_adapter import (
    ENERGY_DRIFT_LIMIT,
    EVENT_SURFACE_RESIDUAL_LIMIT,
    EVENT_TIME_CONVERGENCE_SECONDS,
    MAXIMUM_ACCEPTED_ANGULAR_INCREMENT,
)
from ...src.first_flip.native_artifacts import (
    FirstFlipNativeArtifact,
    ensure_first_flip_native_artifact,
    first_flip_native_artifact_identity,
    first_flip_native_support,
)
from ...src.first_flip.native_runtime import (
    NATIVE_STATS_SIZE,
    _library,
    _native_rhs_callback,
    _runtime_artifact,
    configure_first_flip_native_artifact,
    initialize_native_first_flip,
)
from ...src.first_flip.reference import (
    EVENT_IDENTITIES,
    FirstFlipStatus,
    _surface_value,
    default_solver_spec,
    energy_scale,
    first_flip_time,
    gravity_timescale,
)
from ...src.lyapunov.reference import (
    EulerLagrangeState,
    PendulumParameters,
    SolverSpec,
    simple_energy,
)
from ...src.state_space_fields import full_periodic_angle_axis


HERE = Path(__file__).resolve().parent
DEFAULT_EVIDENCE = HERE / "evidence" / "first_flip_horizon_128.json"
DEFAULT_ARRAYS = HERE / "evidence" / "first_flip_horizon_128.npz"
DEFAULT_RENDER = HERE / "evidence" / "first_flip_horizon_128.png"
INVESTIGATION_ROUTE = "investigation_native_dop853_first_flip_v2_long_horizon"
STATUS_CENSORED = np.uint8(0)
STATUS_OBSERVED = np.uint8(1)
STATUS_INVALID = np.uint8(2)
STATUS_ERROR = np.uint8(3)
STATUS_LABELS = {
    int(STATUS_CENSORED): "right_censored",
    int(STATUS_OBSERVED): "event_observed",
    int(STATUS_INVALID): "invalid_integration",
    int(STATUS_ERROR): "execution_error",
}
DEFAULT_POOL_CELL_LIMIT = 2048


@dataclass(frozen=True)
class NativeCellResult:
    index: int
    status: int
    event_time_seconds: float
    event_index: int
    event_state: tuple[float, float, float, float]
    integration_endpoint_seconds: float
    rhs_evaluations: int
    accepted_point_count: int
    maximum_normalized_energy_drift: float
    maximum_accepted_angular_increment: float
    triggering_surface_residual: float
    maximum_solver_step_seconds: float
    wall_seconds: float
    error: str | None = None


def potential_coefficients(
    parameters: PendulumParameters = PendulumParameters(),
) -> tuple[float, float]:
    """Return A and B in V=-A cos(theta1)-B cos(theta2)."""

    return (
        (parameters.mass1 + parameters.mass2)
        * parameters.gravity
        * parameters.length1,
        parameters.mass2 * parameters.gravity * parameters.length2,
    )


def winding_energy_barriers(
    parameters: PendulumParameters = PendulumParameters(),
) -> tuple[float, float]:
    """Return necessary total-energy barriers for arm-1 and arm-2 winding."""

    coefficient1, coefficient2 = potential_coefficients(parameters)
    return coefficient1 - coefficient2, -coefficient1 + coefficient2


def either_flip_energy_barrier(
    parameters: PendulumParameters = PendulumParameters(),
) -> float:
    """Return the lowest rigorous energy barrier for either link to wind."""

    return min(winding_energy_barriers(parameters))


def zero_velocity_energy(
    theta1: np.ndarray | float,
    theta2: np.ndarray | float,
    parameters: PendulumParameters = PendulumParameters(),
) -> np.ndarray:
    """Mechanical energy on the investigation's zero-velocity angle slice."""

    coefficient1, coefficient2 = potential_coefficients(parameters)
    return np.asarray(
        -coefficient1 * np.cos(theta1) - coefficient2 * np.cos(theta2),
        dtype=float,
    )


def energy_inaccessible_mask(
    theta1: np.ndarray,
    theta2: np.ndarray,
    parameters: PendulumParameters = PendulumParameters(),
) -> np.ndarray:
    """Mark cells rigorously unable to complete either net revolution.

    The inequality is intentionally strict.  Equality reaches a saddle-energy
    accessibility threshold and is not classified as energy-inaccessible.
    """

    return zero_velocity_energy(theta1, theta2, parameters) < either_flip_energy_barrier(
        parameters
    )


def production_policy_rejects_horizon(
    horizon_seconds: float,
    parameters: PendulumParameters = PendulumParameters(),
) -> bool:
    """Expose the unchanged T=5 production guard as an evidence assertion."""

    return not first_flip_compiled_eligibility(
        parameters,
        default_solver_spec(parameters),
        horizon_seconds,
    ).eligible


def _initialize_worker(artifact: FirstFlipNativeArtifact) -> None:
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        os.environ.setdefault(name, "1")
    configure_first_flip_native_artifact(artifact)
    initialize_native_first_flip(PendulumParameters())


def _native_cell(task: tuple[int, float, float, float]) -> NativeCellResult:
    index, theta1, theta2, horizon = task
    parameters = PendulumParameters()
    solver = default_solver_spec(parameters)
    state0 = np.asarray((theta1, theta2, 0.0, 0.0), dtype=np.float64)
    state = np.ascontiguousarray(state0.copy())
    physical = np.ascontiguousarray(
        (
            parameters.length1,
            parameters.length2,
            parameters.mass1,
            parameters.mass2,
            parameters.gravity,
        ),
        dtype=np.float64,
    )
    stats = np.zeros(NATIVE_STATS_SIZE, dtype=np.float64)
    started = perf_counter()
    try:
        artifact = _runtime_artifact()
        assert solver.max_step is not None
        code = int(
            _library(artifact.key, artifact.directory or "").first_flip_loop(
                _native_rhs_callback().address,
                state,
                physical,
                float(horizon),
                solver.rtol,
                solver.atol,
                float(solver.max_step),
                stats,
            )
        )
        if code != 0:
            raise RuntimeError(
                f"native status {code}; DOP853 status {int(round(stats[11]))}"
            )
        if not np.all(np.isfinite(state)) or not np.all(np.isfinite(stats)):
            raise RuntimeError("non-finite native output")
        observed = bool(round(float(stats[0])))
        event_index = int(round(float(stats[1]))) if observed else -1
        if observed and not 0 <= event_index < len(EVENT_IDENTITIES):
            raise RuntimeError("invalid event identity")
        event_time = float(stats[2]) if observed else math.nan
        event_state = tuple(float(value) for value in state) if observed else (
            math.nan,
            math.nan,
            math.nan,
            math.nan,
        )
        residual = (
            abs(_surface_value(EVENT_IDENTITIES[event_index], state, state0))
            if observed
            else 0.0
        )
        energy_drift = float(stats[4])
        angular_increment = float(stats[5])
        maximum_step = float(stats[8])
        endpoint = float(stats[12])
        allowance = 2.0e-14
        issues: list[str] = []
        if energy_drift > ENERGY_DRIFT_LIMIT:
            issues.append("energy_drift_limit_exceeded")
        if angular_increment >= MAXIMUM_ACCEPTED_ANGULAR_INCREMENT:
            issues.append("accepted_angular_increment_limit_exceeded")
        if maximum_step > float(solver.max_step) + allowance:
            issues.append("maximum_solver_step_exceeded")
        if observed:
            if residual > EVENT_SURFACE_RESIDUAL_LIMIT:
                issues.append("event_surface_residual_limit_exceeded")
            triggering_velocity = float(state[EVENT_IDENTITIES[event_index].arm + 1])
            if triggering_velocity == 0.0:
                issues.append("nontransversal_event")
            if not event_time < horizon:
                issues.append("event_not_strictly_before_cap")
        elif abs(endpoint - horizon) > 2.0e-14:
            issues.append("censored_endpoint_mismatch")
        return NativeCellResult(
            index=index,
            status=int(STATUS_INVALID if issues else STATUS_OBSERVED if observed else STATUS_CENSORED),
            event_time_seconds=event_time,
            event_index=event_index,
            event_state=event_state,
            integration_endpoint_seconds=endpoint,
            rhs_evaluations=int(round(float(stats[6]))),
            accepted_point_count=int(round(float(stats[7]))),
            maximum_normalized_energy_drift=energy_drift,
            maximum_accepted_angular_increment=angular_increment,
            triggering_surface_residual=residual,
            maximum_solver_step_seconds=maximum_step,
            wall_seconds=perf_counter() - started,
            error=";".join(issues) if issues else None,
        )
    except Exception as error:
        return NativeCellResult(
            index=index,
            status=int(STATUS_ERROR),
            event_time_seconds=math.nan,
            event_index=-1,
            event_state=(math.nan, math.nan, math.nan, math.nan),
            integration_endpoint_seconds=math.nan,
            rhs_evaluations=0,
            accepted_point_count=0,
            maximum_normalized_energy_drift=math.nan,
            maximum_accepted_angular_increment=math.nan,
            triggering_surface_residual=math.nan,
            maximum_solver_step_seconds=math.nan,
            wall_seconds=perf_counter() - started,
            error=f"{type(error).__name__}: {error}",
        )


def _run_cells(
    axis: np.ndarray,
    horizon_seconds: float,
    workers: int,
    artifact: FirstFlipNativeArtifact,
) -> tuple[dict[str, np.ndarray], dict[str, float | int | bool]]:
    theta1_grid, theta2_grid = np.meshgrid(axis, axis)
    flat_theta1 = theta1_grid.ravel()
    flat_theta2 = theta2_grid.ravel()
    cell_count = len(flat_theta1)
    results: list[NativeCellResult | None] = [None] * cell_count
    setup_seconds = 0.0
    evaluation_seconds = 0.0
    shutdown_seconds = 0.0
    pool_count = 0
    all_workers_stopped = True
    outer_started = perf_counter()
    context = multiprocessing.get_context("spawn")
    for start in range(0, cell_count, DEFAULT_POOL_CELL_LIMIT):
        stop = min(cell_count, start + DEFAULT_POOL_CELL_LIMIT)
        setup_started = perf_counter()
        executor = ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_initialize_worker,
            initargs=(artifact,),
        )
        pool_count += 1
        setup_seconds += perf_counter() - setup_started
        tasks = (
            (index, float(flat_theta1[index]), float(flat_theta2[index]), horizon_seconds)
            for index in range(start, stop)
        )
        evaluation_started = perf_counter()
        for item in executor.map(_native_cell, tasks, chunksize=1):
            results[item.index] = item
        evaluation_seconds += perf_counter() - evaluation_started
        process_ids = tuple(
            process.pid for process in (executor._processes or {}).values() if process.pid
        )
        shutdown_started = perf_counter()
        executor.shutdown(wait=True, cancel_futures=True)
        shutdown_seconds += perf_counter() - shutdown_started
        for process_id in process_ids:
            try:
                os.kill(process_id, 0)
            except ProcessLookupError:
                continue
            except PermissionError:
                continue
            all_workers_stopped = False
    completed = [item for item in results if item is not None]
    if len(completed) != cell_count:
        raise RuntimeError("worker result set is incomplete")

    def values(name: str, dtype: object = float) -> np.ndarray:
        return np.asarray([getattr(item, name) for item in completed], dtype=dtype).reshape(
            theta1_grid.shape
        )

    arrays = {
        "status": values("status", np.uint8),
        "event_time_seconds": values("event_time_seconds"),
        "event_index": values("event_index", np.int8),
        "event_state": np.asarray(
            [item.event_state for item in completed], dtype=float
        ).reshape((*theta1_grid.shape, 4)),
        "integration_endpoint_seconds": values("integration_endpoint_seconds"),
        "rhs_evaluations": values("rhs_evaluations", np.int64),
        "accepted_point_count": values("accepted_point_count", np.int64),
        "maximum_normalized_energy_drift": values("maximum_normalized_energy_drift"),
        "maximum_accepted_angular_increment": values(
            "maximum_accepted_angular_increment"
        ),
        "triggering_surface_residual": values("triggering_surface_residual"),
        "maximum_solver_step_seconds": values("maximum_solver_step_seconds"),
        "cell_wall_seconds": values("wall_seconds"),
    }
    errors = [item.error for item in completed if item.error]
    total_seconds = perf_counter() - outer_started
    timings: dict[str, float | int | bool] = {
        "wall_seconds": total_seconds,
        "setup_seconds": setup_seconds,
        "evaluation_seconds": evaluation_seconds,
        "shutdown_seconds": shutdown_seconds,
        "pool_count": pool_count,
        "recycling_events": max(0, pool_count - 1),
        "all_workers_stopped": all_workers_stopped,
        "wall_cells_per_second": cell_count / total_seconds,
        "evaluation_cells_per_second": cell_count / evaluation_seconds,
        "summed_cell_wall_seconds": float(np.sum(arrays["cell_wall_seconds"])),
        "error_message_count": len(errors),
    }
    return arrays, timings


def _quantiles(values: np.ndarray) -> dict[str, float | None]:
    if not len(values):
        return {key: None for key in ("minimum", "q25", "median", "q75", "q90", "q99", "maximum")}
    probabilities = (0.0, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0)
    return {
        key: float(value)
        for key, value in zip(
            ("minimum", "q25", "median", "q75", "q90", "q99", "maximum"),
            np.quantile(values, probabilities),
            strict=True,
        )
    }


def _bin_summary(event_times_hat: np.ndarray, cell_count: int) -> dict[str, dict[str, float | int]]:
    bins = (
        ("tau_hat_lt_1", -math.inf, 1.0),
        ("tau_hat_1_to_10", 1.0, 10.0),
        ("tau_hat_10_to_100", 10.0, 100.0),
        ("tau_hat_100_to_1000", 100.0, 1000.0),
        ("tau_hat_ge_1000", 1000.0, math.inf),
    )
    observed_count = len(event_times_hat)
    result: dict[str, dict[str, float | int]] = {}
    for label, lower, upper in bins:
        count = int(np.count_nonzero((event_times_hat >= lower) & (event_times_hat < upper)))
        result[label] = {
            "count": count,
            "fraction_of_grid": count / cell_count,
            "fraction_of_observed": count / observed_count if observed_count else 0.0,
        }
    return result


def _summarize_horizon(
    arrays: dict[str, np.ndarray],
    timings: dict[str, float | int | bool],
    horizon_hat: float,
    time_scale: float,
    inaccessible: np.ndarray,
    previous_observed: np.ndarray | None,
) -> tuple[dict[str, object], np.ndarray]:
    status = arrays["status"]
    observed = status == STATUS_OBSERVED
    censored = status == STATUS_CENSORED
    invalid = status == STATUS_INVALID
    errors = status == STATUS_ERROR
    cell_count = status.size
    event_times_hat = arrays["event_time_seconds"][observed] / time_scale
    newly_observed = observed if previous_observed is None else observed & ~previous_observed
    diagnostics_valid = ~(invalid | errors)
    maximum_step = float(np.nanmax(arrays["maximum_solver_step_seconds"]))
    return (
        {
            "physical_horizon_seconds": horizon_hat * time_scale,
            "dimensionless_horizon": horizon_hat,
            "outcomes": {
                "observed_count": int(np.count_nonzero(observed)),
                "observed_fraction": float(np.mean(observed)),
                "censored_count": int(np.count_nonzero(censored)),
                "censored_fraction": float(np.mean(censored)),
                "invalid_count": int(np.count_nonzero(invalid)),
                "invalid_fraction": float(np.mean(invalid)),
                "error_count": int(np.count_nonzero(errors)),
                "error_fraction": float(np.mean(errors)),
                "newly_observed_count": int(np.count_nonzero(newly_observed)),
                "newly_observed_fraction": float(np.mean(newly_observed)),
            },
            "observed_tau_hat_distribution": _quantiles(event_times_hat),
            "candidate_logarithmic_bins": _bin_summary(event_times_hat, cell_count),
            "energy_relationship": {
                "observed_energy_inaccessible_count": int(
                    np.count_nonzero(observed & inaccessible)
                ),
                "censored_energy_inaccessible_count": int(
                    np.count_nonzero(censored & inaccessible)
                ),
                "censored_energy_permitted_count": int(
                    np.count_nonzero(censored & ~inaccessible)
                ),
                "fraction_of_censored_energy_inaccessible": (
                    float(np.count_nonzero(censored & inaccessible) / np.count_nonzero(censored))
                    if np.any(censored)
                    else 0.0
                ),
            },
            "diagnostics": {
                "maximum_normalized_energy_drift": float(
                    np.nanmax(arrays["maximum_normalized_energy_drift"])
                ),
                "maximum_accepted_angular_increment": float(
                    np.nanmax(arrays["maximum_accepted_angular_increment"])
                ),
                "maximum_triggering_surface_residual": float(
                    np.nanmax(arrays["triggering_surface_residual"])
                ),
                "maximum_solver_step_seconds": maximum_step,
                "summed_rhs_evaluations": int(
                    np.sum(arrays["rhs_evaluations"][diagnostics_valid])
                ),
                "route_counts": {INVESTIGATION_ROUTE: int(np.count_nonzero(diagnostics_valid))},
                "fallback_count": 0,
            },
            "timings": timings,
        },
        observed,
    )


def _comparison(
    name: str,
    theta1: float,
    theta2: float,
    horizon_seconds: float,
    native: NativeCellResult,
) -> dict[str, object]:
    parameters = PendulumParameters()
    solver = default_solver_spec(parameters)
    trusted = first_flip_time(
        EulerLagrangeState(theta1, theta2, 0.0, 0.0),
        parameters=parameters,
        solver_spec=solver,
        observation_horizon=horizon_seconds,
    )
    native_observed = native.status == int(STATUS_OBSERVED)
    trusted_observed = trusted.status is FirstFlipStatus.EVENT_OBSERVED
    native_censored = native.status == int(STATUS_CENSORED)
    trusted_censored = trusted.status is FirstFlipStatus.RIGHT_CENSORED
    time_difference = (
        abs(native.event_time_seconds - float(trusted.event_time_seconds))
        if native_observed and trusted.event_time_seconds is not None
        else 0.0
    )
    state_difference = (
        float(
            np.max(
                np.abs(
                    np.asarray(native.event_state)
                    - np.asarray(trusted.event_state, dtype=float)
                )
            )
        )
        if native_observed and trusted.event_state is not None
        else 0.0
    )
    native_identity = EVENT_IDENTITIES[native.event_index].label if native_observed else None
    trusted_identity = (
        trusted.event_identities[0].label if len(trusted.event_identities) == 1 else None
    )
    checks = {
        "classification": (native_observed and trusted_observed)
        or (native_censored and trusted_censored),
        "unique_attribution": native_identity == trusted_identity,
        "event_time": time_difference <= EVENT_TIME_CONVERGENCE_SECONDS,
        "event_state": state_difference <= 5.0e-7,
        "native_energy": native.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT,
        "trusted_energy": trusted.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT,
        "native_angular_increment": native.maximum_accepted_angular_increment
        < MAXIMUM_ACCEPTED_ANGULAR_INCREMENT,
        "trusted_angular_increment": trusted.maximum_accepted_angular_increment
        < MAXIMUM_ACCEPTED_ANGULAR_INCREMENT,
        "native_event_residual": native.triggering_surface_residual
        <= EVENT_SURFACE_RESIDUAL_LIMIT,
        "trusted_event_residual": max(
            (
                abs(item.residual)
                for item in trusted.event_surface_residuals
                if item.identity in trusted.event_identities
            ),
            default=0.0,
        )
        <= EVENT_SURFACE_RESIDUAL_LIMIT,
        "censored_endpoint": (
            abs(native.integration_endpoint_seconds - horizon_seconds) <= 2.0e-14
            and abs(trusted.integration_endpoint_seconds - horizon_seconds) <= 2.0e-14
        )
        if native_censored and trusted_censored
        else True,
        "max_step": native.maximum_solver_step_seconds
        <= float(solver.max_step) + 2.0e-14,
    }
    return {
        "name": name,
        "theta1_radians": theta1,
        "theta2_radians": theta2,
        "physical_horizon_seconds": horizon_seconds,
        "dimensionless_horizon": horizon_seconds / gravity_timescale(parameters),
        "native_status": STATUS_LABELS[native.status],
        "trusted_status": trusted.status.value,
        "native_event_identity": native_identity,
        "trusted_event_identity": trusted_identity,
        "event_time_difference_seconds": time_difference,
        "event_state_maximum_component_difference": state_difference,
        "native_maximum_normalized_energy_drift": native.maximum_normalized_energy_drift,
        "trusted_maximum_normalized_energy_drift": trusted.maximum_normalized_energy_drift,
        "checks": checks,
        "accepted": all(checks.values()),
    }


def _preflight(horizon_hats: Sequence[float]) -> list[dict[str, object]]:
    parameters = PendulumParameters()
    time_scale = gravity_timescale(parameters)
    fixed_cases = (
        ("downward_equilibrium", 0.0, 0.0),
        ("known_arm1_event", math.radians(-150.0), math.radians(-150.0)),
        ("known_arm2_event", math.radians(179.0), math.radians(179.0)),
        ("known_delayed_event", math.radians(-180.0), math.radians(-13.84615384615384)),
    )
    selected_hats = tuple(dict.fromkeys((horizon_hats[0], 10.0, horizon_hats[-1])))
    records: list[dict[str, object]] = []
    for horizon_hat in selected_hats:
        if horizon_hat not in horizon_hats and horizon_hat != 10.0:
            continue
        horizon = horizon_hat * time_scale
        for case_index, (name, theta1, theta2) in enumerate(fixed_cases):
            native = _native_cell((case_index, theta1, theta2, horizon))
            comparison = _comparison(name, theta1, theta2, horizon, native)
            records.append(comparison)
    if not all(item["accepted"] for item in records):
        raise RuntimeError("long-horizon native preflight failed an existing scientific gate")
    return records


def _representative_validation(
    axis: np.ndarray,
    horizons_hat: Sequence[float],
    horizon_arrays: Sequence[dict[str, np.ndarray]],
    inaccessible: np.ndarray,
) -> list[dict[str, object]]:
    parameters = PendulumParameters()
    time_scale = gravity_timescale(parameters)
    records: list[dict[str, object]] = []
    used: set[tuple[int, int, int]] = set()
    for horizon_index, (horizon_hat, arrays) in enumerate(
        zip(horizons_hat, horizon_arrays, strict=True)
    ):
        status = arrays["status"]
        candidates: list[tuple[str, tuple[int, int]]] = []
        observed_indices = np.argwhere(status == STATUS_OBSERVED)
        if len(observed_indices):
            times = arrays["event_time_seconds"][status == STATUS_OBSERVED]
            order = np.argsort(times)
            candidates.append(
                ("observed_median", tuple(observed_indices[order[len(order) // 2]]))
            )
            candidates.append(("observed_latest", tuple(observed_indices[order[-1]])))
        inaccessible_indices = np.argwhere((status == STATUS_CENSORED) & inaccessible)
        if len(inaccessible_indices):
            candidates.append(("energy_inaccessible_censored", tuple(inaccessible_indices[0])))
        permitted_indices = np.argwhere((status == STATUS_CENSORED) & ~inaccessible)
        if len(permitted_indices):
            candidates.append(("energy_permitted_censored", tuple(permitted_indices[len(permitted_indices) // 2])))
        valid_drift = np.where(
            np.isfinite(arrays["maximum_normalized_energy_drift"]),
            arrays["maximum_normalized_energy_drift"],
            -math.inf,
        )
        candidates.append(
            (
                "maximum_energy_drift",
                tuple(np.unravel_index(np.argmax(valid_drift), valid_drift.shape)),
            )
        )
        for role, (theta2_index, theta1_index) in candidates:
            key = (horizon_index, int(theta2_index), int(theta1_index))
            if key in used:
                continue
            used.add(key)
            native = NativeCellResult(
                index=int(theta2_index * len(axis) + theta1_index),
                status=int(status[theta2_index, theta1_index]),
                event_time_seconds=float(arrays["event_time_seconds"][theta2_index, theta1_index]),
                event_index=int(arrays["event_index"][theta2_index, theta1_index]),
                event_state=tuple(float(value) for value in arrays["event_state"][theta2_index, theta1_index]),
                integration_endpoint_seconds=float(arrays["integration_endpoint_seconds"][theta2_index, theta1_index]),
                rhs_evaluations=int(arrays["rhs_evaluations"][theta2_index, theta1_index]),
                accepted_point_count=int(arrays["accepted_point_count"][theta2_index, theta1_index]),
                maximum_normalized_energy_drift=float(arrays["maximum_normalized_energy_drift"][theta2_index, theta1_index]),
                maximum_accepted_angular_increment=float(arrays["maximum_accepted_angular_increment"][theta2_index, theta1_index]),
                triggering_surface_residual=float(arrays["triggering_surface_residual"][theta2_index, theta1_index]),
                maximum_solver_step_seconds=float(arrays["maximum_solver_step_seconds"][theta2_index, theta1_index]),
                wall_seconds=float(arrays["cell_wall_seconds"][theta2_index, theta1_index]),
            )
            records.append(
                _comparison(
                    f"H{horizon_hat:g}_{role}",
                    float(axis[theta1_index]),
                    float(axis[theta2_index]),
                    horizon_hat * time_scale,
                    native,
                )
            )
    if not all(item["accepted"] for item in records):
        raise RuntimeError("representative native/reference validation failed")
    return records


def _save_arrays(
    path: Path,
    axis: np.ndarray,
    horizons_hat: Sequence[float],
    energy: np.ndarray,
    inaccessible: np.ndarray,
    horizon_arrays: Sequence[dict[str, np.ndarray]],
) -> None:
    payload: dict[str, np.ndarray] = {
        "theta_axis_radians": axis,
        "horizons_hat": np.asarray(horizons_hat, dtype=float),
        "zero_velocity_energy_joules": energy,
        "energy_inaccessible": inaccessible,
    }
    for index, arrays in enumerate(horizon_arrays):
        for name, values in arrays.items():
            payload[f"h{index}_{name}"] = values
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **payload)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(HERE))
    except ValueError:
        return str(path)


def _render(
    path: Path,
    axis: np.ndarray,
    horizons_hat: Sequence[float],
    horizon_arrays: Sequence[dict[str, np.ndarray]],
    inaccessible: np.ndarray,
) -> None:
    final_status = horizon_arrays[-1]["status"]
    final_times = horizon_arrays[-1]["event_time_seconds"] / gravity_timescale(
        PendulumParameters()
    )
    categories = np.full(final_status.shape, 5, dtype=np.uint8)
    categories[(final_status == STATUS_CENSORED) & inaccessible] = 0
    categories[(final_status == STATUS_CENSORED) & ~inaccessible] = 1
    categories[(final_status == STATUS_OBSERVED) & (final_times < 10.0)] = 2
    categories[
        (final_status == STATUS_OBSERVED)
        & (final_times >= 10.0)
        & (final_times < 100.0)
    ] = 3
    categories[
        (final_status == STATUS_OBSERVED)
        & (final_times >= 100.0)
        & (final_times < 1000.0)
    ] = 4
    observed_fractions = [float(np.mean(item["status"] == STATUS_OBSERVED)) for item in horizon_arrays]
    permitted_censored = [
        float(np.mean((item["status"] == STATUS_CENSORED) & ~inaccessible))
        for item in horizon_arrays
    ]
    inaccessible_fraction = float(np.mean(inaccessible))

    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.7), constrained_layout=True)
    colourmap = ListedColormap(
        ("#25324b", "#c8c4b7", "#ef8a62", "#67a9cf", "#2166ac", "#7b3294")
    )
    axes[0].imshow(
        categories,
        origin="lower",
        extent=(-math.pi, math.pi, -math.pi, math.pi),
        interpolation="nearest",
        cmap=colourmap,
        vmin=-0.5,
        vmax=5.5,
        aspect="equal",
    )
    axes[0].set_title(f"Outcome classes at $\\widehat{{T}}={horizons_hat[-1]:g}$")
    axes[0].set_xlabel(r"$\theta_1(0)$")
    axes[0].set_ylabel(r"$\theta_2(0)$")
    axes[0].set_xticks((-math.pi, 0.0, math.pi), (r"$-\pi$", "0", r"$\pi$"))
    axes[0].set_yticks((-math.pi, 0.0, math.pi), (r"$-\pi$", "0", r"$\pi$"))
    labels = (
        "energy-inaccessible",
        "energy-permitted, censored",
        r"observed $\widehat{\tau}<10$",
        r"observed $10\leq\widehat{\tau}<100$",
        r"observed $100\leq\widehat{\tau}<1000$",
        "invalid/error",
    )
    axes[0].legend(
        handles=[Patch(color=colourmap(index), label=label) for index, label in enumerate(labels)],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.13),
        fontsize=8,
        ncol=2,
    )
    axes[1].semilogx(horizons_hat, observed_fractions, "o-", label="observed flip")
    axes[1].semilogx(
        horizons_hat,
        permitted_censored,
        "s-",
        label="energy-permitted but censored",
    )
    axes[1].axhline(
        inaccessible_fraction,
        color="#25324b",
        linestyle="--",
        label="rigorous inaccessible fraction",
    )
    axes[1].set_ylim(0.0, 1.0)
    axes[1].set_xlabel(r"dimensionless horizon $\widehat{T}$")
    axes[1].set_ylabel("fraction of 128×128 grid")
    axes[1].set_title("Survival decomposition")
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=8)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def run_investigation(
    samples_per_axis: int = 128,
    horizons_hat: Sequence[float] | None = None,
    workers: int = 4,
    evidence_path: Path = DEFAULT_EVIDENCE,
    arrays_path: Path = DEFAULT_ARRAYS,
    render_path: Path = DEFAULT_RENDER,
) -> dict[str, object]:
    parameters = PendulumParameters()
    solver = default_solver_spec(parameters)
    time_scale = gravity_timescale(parameters)
    horizons = tuple(
        sorted(
            float(value)
            for value in (
                horizons_hat
                or (1.0, 10.0, 5.0 / time_scale, 100.0)
            )
        )
    )
    if samples_per_axis <= 0 or workers <= 0:
        raise ValueError("resolution and worker count must be positive")
    if not horizons or any(not math.isfinite(value) or value <= 0.0 for value in horizons):
        raise ValueError("dimensionless horizons must be positive and finite")
    if samples_per_axis > 256:
        raise ValueError("this bounded investigation refuses resolutions above 256")
    if not first_flip_native_support()["supported"]:
        raise RuntimeError("the corrected-v2 native artifact is unavailable on this host")
    non_t5 = [value * time_scale for value in horizons if value * time_scale != 5.0]
    if not all(production_policy_rejects_horizon(value) for value in non_t5):
        raise RuntimeError("production eligibility unexpectedly accepted a long horizon")

    artifact = ensure_first_flip_native_artifact()
    configure_first_flip_native_artifact(artifact)
    initialize_native_first_flip(parameters)
    preflight = _preflight(horizons)

    axis = full_periodic_angle_axis(samples_per_axis)
    theta1_grid, theta2_grid = np.meshgrid(axis, axis)
    energy = zero_velocity_energy(theta1_grid, theta2_grid, parameters)
    inaccessible = energy_inaccessible_mask(theta1_grid, theta2_grid, parameters)
    horizon_arrays: list[dict[str, np.ndarray]] = []
    horizon_summaries: list[dict[str, object]] = []
    previous_observed: np.ndarray | None = None
    for horizon_hat in horizons:
        arrays, timings = _run_cells(
            axis,
            horizon_hat * time_scale,
            workers,
            artifact,
        )
        summary, previous_observed = _summarize_horizon(
            arrays,
            timings,
            horizon_hat,
            time_scale,
            inaccessible,
            previous_observed,
        )
        horizon_arrays.append(arrays)
        horizon_summaries.append(summary)
        if summary["outcomes"]["invalid_count"] or summary["outcomes"]["error_count"]:
            raise RuntimeError(
                f"long-horizon field failed closed at T_hat={horizon_hat:g}"
            )
        print(
            json.dumps(
                {
                    "T_hat": horizon_hat,
                    "T_seconds": horizon_hat * time_scale,
                    "outcomes": summary["outcomes"],
                    "wall_seconds": timings["wall_seconds"],
                    "evaluation_seconds": timings["evaluation_seconds"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    representative = _representative_validation(
        axis, horizons, horizon_arrays, inaccessible
    )
    _save_arrays(arrays_path, axis, horizons, energy, inaccessible, horizon_arrays)
    _render(render_path, axis, horizons, horizon_arrays, inaccessible)
    t5_index = min(range(len(horizons)), key=lambda index: abs(horizons[index] - 5.0 / time_scale))
    final_index = len(horizons) - 1
    t5_wall = float(horizon_summaries[t5_index]["timings"]["wall_seconds"])
    final_wall = float(horizon_summaries[final_index]["timings"]["wall_seconds"])
    coefficient1, coefficient2 = potential_coefficients(parameters)
    arm1_barrier, arm2_barrier = winding_energy_barriers(parameters)
    payload: dict[str, object] = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "investigation": "first_flip_horizon_and_energy_accessibility",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "process_start_method": "spawn",
            "workers": workers,
            "maximum_cells_per_pool": DEFAULT_POOL_CELL_LIMIT,
        },
        "grid": {
            "samples_per_axis": samples_per_axis,
            "cell_count": samples_per_axis**2,
            "periodic_interval": "[-pi, pi)",
            "stored_orientation": "[theta2_index, theta1_index]",
            "zero_initial_angular_velocities": True,
        },
        "physical_and_numerical_contract": {
            "parameters": asdict(parameters),
            "solver": asdict(solver),
            "gravity_timescale_seconds": time_scale,
            "event": "first |theta_i(t)-theta_i(0)| = 2*pi; lifted absolute angles",
            "censoring": "no event strictly before the finite horizon",
            "route": INVESTIGATION_ROUTE,
            "production_eligibility_changed": False,
            "production_non_t5_rejection_verified": True,
            "native_artifact_identity": first_flip_native_artifact_identity(),
            "scientific_gates": {
                "event_time_difference_seconds": EVENT_TIME_CONVERGENCE_SECONDS,
                "event_state_component_difference": 5.0e-7,
                "maximum_normalized_energy_drift": ENERGY_DRIFT_LIMIT,
                "maximum_event_surface_residual": EVENT_SURFACE_RESIDUAL_LIMIT,
                "maximum_accepted_angular_increment_strict": MAXIMUM_ACCEPTED_ANGULAR_INCREMENT,
                "maximum_step_allowance_seconds": 2.0e-14,
                "censored_endpoint_allowance_seconds": 2.0e-14,
            },
        },
        "energy_accessibility": {
            "potential": "V=-A*cos(theta1)-B*cos(theta2)",
            "A_joules": coefficient1,
            "B_joules": coefficient2,
            "arm1_winding_necessary_barrier_joules": arm1_barrier,
            "arm2_winding_necessary_barrier_joules": arm2_barrier,
            "either_flip_necessary_barrier_joules": either_flip_energy_barrier(parameters),
            "zero_velocity_inaccessible_rule": "E0 < either_flip barrier (strict)",
            "logical_status": "necessary for a flip, not sufficient; strict failure is sufficient for no flip",
            "energy_inaccessible_count": int(np.count_nonzero(inaccessible)),
            "energy_inaccessible_fraction": float(np.mean(inaccessible)),
        },
        "horizons": horizon_summaries,
        "native_vs_trusted_preflight": {
            "case_count": len(preflight),
            "accepted": all(item["accepted"] for item in preflight),
            "cases": preflight,
        },
        "native_vs_trusted_representative": {
            "case_count": len(representative),
            "accepted": all(item["accepted"] for item in representative),
            "maximum_event_time_difference_seconds": max(
                item["event_time_difference_seconds"] for item in representative
            ),
            "maximum_event_state_component_difference": max(
                item["event_state_maximum_component_difference"]
                for item in representative
            ),
            "cases": representative,
        },
        "runtime_scaling": {
            "t5_dimensionless_horizon": horizons[t5_index],
            "t5_wall_seconds": t5_wall,
            "maximum_horizon_hat": horizons[final_index],
            "maximum_horizon_wall_seconds": final_wall,
            "maximum_horizon_relative_wall_cost_vs_t5": final_wall / t5_wall,
        },
        "artifacts": {
            "arrays_path": _display_path(arrays_path),
            "arrays_sha256": hashlib.sha256(arrays_path.read_bytes()).hexdigest(),
            "render_path": _display_path(render_path),
            "render_sha256": hashlib.sha256(render_path.read_bytes()).hexdigest(),
        },
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-axis", type=int, default=128)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--horizons-hat",
        type=float,
        nargs="+",
        help="Dimensionless horizons. Default: 1, 10, exact T=5, 100.",
    )
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--arrays", type=Path, default=DEFAULT_ARRAYS)
    parser.add_argument("--render", type=Path, default=DEFAULT_RENDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    payload = run_investigation(
        samples_per_axis=arguments.samples_per_axis,
        horizons_hat=arguments.horizons_hat,
        workers=arguments.workers,
        evidence_path=arguments.evidence,
        arrays_path=arguments.arrays,
        render_path=arguments.render,
    )
    print(
        json.dumps(
            {
                "evidence": str(arguments.evidence),
                "arrays": str(arguments.arrays),
                "render": str(arguments.render),
                "horizon_count": len(payload["horizons"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
