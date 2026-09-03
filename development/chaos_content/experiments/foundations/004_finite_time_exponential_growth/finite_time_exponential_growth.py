"""Audit a finite approximately exponential growth interval without an exponent.

The adjacent README fixes the inference rule before this script is interpreted.
All helpers remain experiment-local; this is not reusable Lyapunov machinery.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import numpy as np

from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_REFERENCE_SOLVER_POLICY,
    DoublePendulumLagrangian,
    SolverPolicy,
)


EXPERIMENT_NAME = "finite_time_approximately_exponential_growth"
MODEL = "simple"
FORMULATION = "Euler-Lagrange"
PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
BASE_STATE_DEGREES = np.array([179.0, 179.0, 0.0, 0.0])
EPSILONS = (1.0e-4, 1.0e-5, 1.0e-6)
BASELINE_EPSILON = 1.0e-5
T_START = 0.0
T_STOP = 20.0
SAMPLE_COUNT = 2001
DENSE_SAMPLE_COUNT = 4001
LC_BASELINE = 1.0
LC_ALTERNATIVE = 2.0
LOCAL_DISTANCE_CEILING = 1.0e-2
LOCAL_COLLAPSE_LIMIT = 0.1
ENERGY_DRIFT_LIMIT = 1.0e-7
INITIAL_TOLERANCE = 2.0e-12
MOVING_WINDOW_SECONDS = 0.20
ENDPOINT_SHIFT_SECONDS = 0.10

# Provisional predeclared inference thresholds. See the README rationale.
MIN_DURATION_IN_TC = 2.0
MIN_LOG_GROWTH = 2.0
MIN_A_R_SQUARED = 0.98
MAX_A_ABS_RESIDUAL = 0.25
MAX_A_RATE_RELATIVE_SPREAD = 0.05
MAX_ENDPOINT_RATE_RELATIVE_DEVIATION = 0.10
MIN_B_R_SQUARED = 0.95
MAX_B_COLLAPSE_SPREAD = 0.15
MAX_A_B_MEDIAN_RATE_RELATIVE_DIFFERENCE = 0.30
MAX_TOLERANCE_RATE_RELATIVE_DIFFERENCE = 0.01
MAX_SAMPLING_RATE_RELATIVE_DIFFERENCE = 0.005
MIN_ALTERNATIVE_SCALE_R_SQUARED = 0.95

STRICTER_POLICY = SolverPolicy(
    name="finite_growth_stricter_check",
    method="DOP853",
    rtol=1.0e-11,
    atol=1.0e-13,
    role="experiment-local numerical robustness comparison",
)


def characteristic_time(length_metres: float = LC_BASELINE) -> float:
    return math.sqrt(float(length_metres) / float(PARAMETERS[g]))


def wrap_angle_difference(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    wrapped = np.remainder(values + math.pi, 2.0 * math.pi) - math.pi
    return np.where(wrapped == -math.pi, math.pi, wrapped)


def lifted_angle_history(angle_samples: np.ndarray) -> np.ndarray:
    """Lift sampled physical angles, assuming each inter-sample turn is below pi."""

    principal_angles = wrap_angle_difference(np.asarray(angle_samples, dtype=float))
    return np.unwrap(principal_angles, axis=0, period=2.0 * math.pi)


def revolution_history(lifted_angles: np.ndarray) -> np.ndarray:
    lifted_angles = np.asarray(lifted_angles, dtype=float)
    return (lifted_angles - lifted_angles[0]) / (2.0 * math.pi)


def first_absolute_revolution_difference_time(
    time: np.ndarray, revolution_difference: np.ndarray
) -> float | None:
    """Return the first sampled time at which ``abs(Delta R) >= 1``."""

    crossings = np.flatnonzero(np.abs(np.asarray(revolution_difference)) >= 1.0)
    return float(np.asarray(time)[crossings[0]]) if len(crossings) else None


def revolution_crossing_phase(
    crossing_time: float | None,
    primary_start: float | None,
    primary_end: float | None,
    locality_end: float | None,
) -> str:
    """Classify a winding-history crossing without changing locality policy."""

    if crossing_time is None:
        return "not_observed"
    if primary_start is None or primary_end is None or locality_end is None:
        return "not_classified_after_numerical_rejection"
    if crossing_time < primary_start:
        return "before_primary_candidate_interval"
    if crossing_time <= primary_end:
        return "inside_primary_candidate_interval"
    if crossing_time <= locality_end:
        return "after_primary_interval_inside_common_local_regime"
    return "after_common_local_regime"


def wrapped_el_difference(reference: np.ndarray, nearby: np.ndarray) -> np.ndarray:
    difference = np.asarray(nearby, dtype=float) - np.asarray(reference, dtype=float)
    result = np.array(difference, copy=True)
    result[..., :2] = wrap_angle_difference(difference[..., :2])
    return result


def candidate_a_distance(difference: np.ndarray, length_metres: float = LC_BASELINE) -> np.ndarray:
    scaled = np.array(difference, dtype=float, copy=True)
    scaled[..., 2:] *= characteristic_time(length_metres)
    return np.linalg.norm(scaled, axis=-1)


def cartesian_full_state(state: np.ndarray) -> np.ndarray:
    state = np.asarray(state, dtype=float)
    theta1, theta2, omega1, omega2 = np.moveaxis(state, -1, 0)
    length1 = float(PARAMETERS[l1])
    length2 = float(PARAMETERS[l2])
    x1 = length1 * np.sin(theta1)
    y1 = -length1 * np.cos(theta1)
    x2 = x1 + length2 * np.sin(theta2)
    y2 = y1 - length2 * np.cos(theta2)
    vx1 = length1 * np.cos(theta1) * omega1
    vy1 = length1 * np.sin(theta1) * omega1
    vx2 = vx1 + length2 * np.cos(theta2) * omega2
    vy2 = vy1 + length2 * np.sin(theta2) * omega2
    return np.stack((x1, y1, x2, y2, vx1, vy1, vx2, vy2), axis=-1)


def candidate_b_distance(
    reference: np.ndarray, nearby: np.ndarray, length_metres: float = LC_BASELINE
) -> np.ndarray:
    difference = cartesian_full_state(nearby) - cartesian_full_state(reference)
    scaled = np.array(difference, copy=True)
    scaled[..., :4] /= length_metres
    scaled[..., 4:] *= characteristic_time(length_metres) / length_metres
    return np.linalg.norm(scaled, axis=-1)


def simple_energy(state: np.ndarray) -> np.ndarray:
    theta1, theta2, omega1, omega2 = np.asarray(state, dtype=float).T
    length1 = float(PARAMETERS[l1])
    length2 = float(PARAMETERS[l2])
    mass1 = float(PARAMETERS[m1])
    mass2 = float(PARAMETERS[m2])
    gravity = float(PARAMETERS[g])
    kinetic = (
        0.5 * (mass1 + mass2) * length1**2 * omega1**2
        + 0.5 * mass2 * length2**2 * omega2**2
        + mass2 * length1 * length2 * omega1 * omega2 * np.cos(theta1 - theta2)
    )
    potential = -(
        (mass1 + mass2) * gravity * length1 * np.cos(theta1)
        + mass2 * gravity * length2 * np.cos(theta2)
    )
    return np.asarray(kinetic + potential)


def energy_scale() -> float:
    return float(PARAMETERS[g]) * (
        (float(PARAMETERS[m1]) + float(PARAMETERS[m2])) * float(PARAMETERS[l1])
        + float(PARAMETERS[m2]) * float(PARAMETERS[l2])
    )


def policy_dict(policy: SolverPolicy) -> dict[str, Any]:
    return {
        "name": policy.name,
        "method": policy.method,
        "rtol": policy.rtol,
        "atol": policy.atol,
        "role": policy.role,
    }


def nearby_state_degrees(epsilon_radians: float) -> np.ndarray:
    state = np.array(BASE_STATE_DEGREES, copy=True)
    state[1] += math.degrees(epsilon_radians)
    return state


def integrate_one(
    label: str, initial_state_degrees: np.ndarray, policy: SolverPolicy, sample_count: int
) -> dict[str, Any]:
    requested_time = np.linspace(T_START, T_STOP, sample_count)
    issues: list[str] = []
    try:
        model = DoublePendulumLagrangian(
            PARAMETERS,
            initial_state_degrees,
            [T_START, T_STOP, sample_count],
            model=MODEL,
            solver_policy=policy,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return {
            "label": label,
            "accepted": False,
            "issues": [f"integration_exception: {exc}"],
            "time": np.array([]),
            "state": np.empty((0, 4)),
            "energy_drift": np.array([]),
            "max_energy_drift": None,
            "solver_metadata": {},
        }

    state = np.asarray(model.sol, dtype=float)
    time = np.asarray(model.solver_time, dtype=float)
    metadata = model.solver_metadata
    if metadata.success is not True:
        issues.append(f"solver_failed: {metadata.message}")
    if metadata.returned_time_matches_requested is not True:
        issues.append("returned_time_does_not_match_requested")
    if time.shape != requested_time.shape or not np.array_equal(time, requested_time):
        issues.append("returned_time_array_is_incomplete_or_misaligned")
    if state.shape != (sample_count, 4):
        issues.append(f"unexpected_solution_shape: {state.shape}")
    if not np.all(np.isfinite(state)):
        issues.append("non_finite_state_values")

    drift = np.array([])
    max_drift: float | None = None
    if not issues:
        energy = simple_energy(state)
        drift = np.abs(energy - energy[0]) / energy_scale()
        if not np.all(np.isfinite(energy)) or not np.all(np.isfinite(drift)):
            issues.append("non_finite_energy_diagnostic")
        else:
            max_drift = float(np.max(drift))
            if max_drift > ENERGY_DRIFT_LIMIT:
                issues.append(
                    f"energy_drift_exceeded: {max_drift:.6e} > {ENERGY_DRIFT_LIMIT:.6e}"
                )
    return {
        "label": label,
        "accepted": not issues,
        "issues": issues,
        "time": time,
        "state": state,
        "energy_drift": drift,
        "max_energy_drift": max_drift,
        "solver_metadata": metadata.to_dict(),
    }


def positive_log_normalized(distance: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    distance = np.asarray(distance, dtype=float)
    values = np.full(distance.shape, np.nan)
    valid = np.isfinite(distance) & (distance > 0.0)
    if distance.size and valid[0]:
        values[valid] = np.log(distance[valid] / distance[0])
    return values, np.isfinite(values)


def derive_pair(
    run_id: str, epsilon: float, policy: SolverPolicy, sample_count: int
) -> dict[str, Any]:
    reference = integrate_one(f"{run_id}:reference", BASE_STATE_DEGREES, policy, sample_count)
    nearby = integrate_one(
        f"{run_id}:nearby", nearby_state_degrees(epsilon), policy, sample_count
    )
    issues = [
        f"{item['label']}: {issue}"
        for item in (reference, nearby)
        for issue in item["issues"]
    ]
    if issues:
        return {
            "run_id": run_id,
            "accepted": False,
            "issues": issues,
            "epsilon": epsilon,
            "policy": policy_dict(policy),
            "sample_count": sample_count,
            "reference": reference,
            "nearby": nearby,
            "series": None,
        }

    if not np.array_equal(reference["time"], nearby["time"]):
        issues.append("pair_time_arrays_are_not_identical")
    difference = wrapped_el_difference(reference["state"], nearby["state"])
    distance_a = candidate_a_distance(difference, LC_BASELINE)
    distance_a_alt = candidate_a_distance(difference, LC_ALTERNATIVE)
    distance_b = candidate_b_distance(reference["state"], nearby["state"], LC_BASELINE)
    reference_lifted = lifted_angle_history(reference["state"][:, :2])
    nearby_lifted = lifted_angle_history(nearby["state"][:, :2])
    reference_revolutions = revolution_history(reference_lifted)
    nearby_revolutions = revolution_history(nearby_lifted)
    lifted_difference = nearby_lifted - reference_lifted
    revolution_difference = nearby_revolutions - reference_revolutions
    reference_max_angle_step = float(
        np.max(np.abs(np.diff(reference["state"][:, :2], axis=0)))
    )
    nearby_max_angle_step = float(
        np.max(np.abs(np.diff(nearby["state"][:, :2], axis=0)))
    )
    y_a, valid_a = positive_log_normalized(distance_a)
    y_a_alt, valid_a_alt = positive_log_normalized(distance_a_alt)
    y_b, valid_b = positive_log_normalized(distance_b)
    expected_difference = np.array([0.0, epsilon, 0.0, 0.0])
    checks = {
        "both_integrations_accepted": reference["accepted"] and nearby["accepted"],
        "requested_perturbation_realised": bool(
            np.allclose(difference[0], expected_difference, rtol=0.0, atol=INITIAL_TOLERANCE)
        ),
        "all_distances_finite_positive": bool(
            all(np.all(np.isfinite(item) & (item > 0.0)) for item in (distance_a, distance_a_alt, distance_b))
        ),
        "all_logs_valid": bool(np.all(valid_a) and np.all(valid_a_alt) and np.all(valid_b)),
        "candidate_a_initial_value_matches": bool(
            math.isclose(distance_a[0], epsilon, rel_tol=0.0, abs_tol=INITIAL_TOLERANCE)
        ),
        "lifted_history_values_finite": bool(
            all(
                np.all(np.isfinite(item))
                for item in (
                    reference_lifted,
                    nearby_lifted,
                    reference_revolutions,
                    nearby_revolutions,
                    lifted_difference,
                    revolution_difference,
                )
            )
        ),
        "lifted_history_sampling_unambiguous": bool(
            reference_max_angle_step < math.pi and nearby_max_angle_step < math.pi
        ),
    }
    issues.extend(f"failed_check: {name}" for name, passed in checks.items() if not passed)
    return {
        "run_id": run_id,
        "accepted": not issues,
        "issues": issues,
        "epsilon": epsilon,
        "policy": policy_dict(policy),
        "sample_count": sample_count,
        "reference": reference,
        "nearby": nearby,
        "checks": checks,
        "series": {
            "time": reference["time"],
            "reference_state": reference["state"],
            "nearby_state": nearby["state"],
            "difference": difference,
            "distance_a": distance_a,
            "distance_b": distance_b,
            "distance_a_alt": distance_a_alt,
            "y_a": y_a,
            "y_b": y_b,
            "y_a_alt": y_a_alt,
            "reference_lifted_angles": reference_lifted,
            "nearby_lifted_angles": nearby_lifted,
            "reference_revolutions": reference_revolutions,
            "nearby_revolutions": nearby_revolutions,
            "lifted_angle_difference": lifted_difference,
            "revolution_difference": revolution_difference,
            "reference_max_angle_step": reference_max_angle_step,
            "nearby_max_angle_step": nearby_max_angle_step,
            "reference_energy_drift": reference["energy_drift"],
            "nearby_energy_drift": nearby["energy_drift"],
        },
    }


def rounded_time(value: float, sample_interval: float = 0.01) -> float:
    return round(value / sample_interval) * sample_interval


def primary_interval() -> tuple[float, float]:
    tc = characteristic_time()
    return rounded_time(tc), rounded_time(3.5 * tc)


def audit_intervals() -> list[tuple[float, float]]:
    tc = characteristic_time()
    starts = (0.0, 0.5 * tc, tc, 1.5 * tc)
    ends = (3.0 * tc, 3.5 * tc, 4.0 * tc)
    intervals: set[tuple[float, float]] = set()
    for start in starts:
        for end in ends:
            realised = (rounded_time(start), rounded_time(end))
            if realised[1] - realised[0] + 1.0e-12 >= MIN_DURATION_IN_TC * tc:
                intervals.add(realised)
    return sorted(intervals)


def endpoint_neighbours(start: float, end: float) -> list[tuple[float, float]]:
    intervals = {
        (rounded_time(start + delta_start), rounded_time(end + delta_end))
        for delta_start in (-ENDPOINT_SHIFT_SECONDS, 0.0, ENDPOINT_SHIFT_SECONDS)
        for delta_end in (-ENDPOINT_SHIFT_SECONDS, 0.0, ENDPOINT_SHIFT_SECONDS)
        if not (delta_start == 0.0 and delta_end == 0.0)
    }
    return sorted(intervals)


def interval_mask(time: np.ndarray, start: float, end: float) -> np.ndarray:
    return (np.asarray(time) >= start - 1.0e-12) & (np.asarray(time) <= end + 1.0e-12)


def linear_diagnostic(time: np.ndarray, values: np.ndarray, start: float, end: float) -> dict[str, Any]:
    mask = interval_mask(time, start, end) & np.isfinite(values)
    x = np.asarray(time)[mask]
    y = np.asarray(values)[mask]
    if len(x) < 3 or x[0] > start + 1.0e-9 or x[-1] < end - 1.0e-9:
        return {"valid": False, "reason": "incomplete_interval"}
    design = np.column_stack((np.ones_like(x), x))
    intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
    fitted = intercept + slope * x
    residual = y - fitted
    sum_squared_residual = float(np.sum(residual**2))
    sum_squared_total = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - sum_squared_residual / sum_squared_total if sum_squared_total > 0 else 0.0
    endpoint_rate = float((y[-1] - y[0]) / (x[-1] - x[0]))
    return {
        "valid": True,
        "start_seconds": float(x[0]),
        "end_seconds": float(x[-1]),
        "duration_seconds": float(x[-1] - x[0]),
        "sample_count": int(len(x)),
        "endpoint_rate_per_second": endpoint_rate,
        "fitted_slope_per_second": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_squared),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "max_abs_residual": float(np.max(np.abs(residual))),
        "log_growth": float(y[-1] - y[0]),
    }


def relative_spread(values: list[float]) -> float:
    median = float(np.median(values))
    return float((max(values) - min(values)) / abs(median)) if median != 0.0 else math.inf


def relative_difference(left: float, right: float) -> float:
    scale = abs(left)
    return abs(right - left) / scale if scale != 0.0 else math.inf


def common_locality(runs_by_epsilon: dict[float, dict[str, Any]]) -> dict[str, Any]:
    ordered = [runs_by_epsilon[value]["series"] for value in EPSILONS]
    time = ordered[0]["time"]
    distance_stack = np.stack([item["distance_a"] for item in ordered])
    y_stack = np.stack([item["y_a"] for item in ordered])
    spread = np.max(y_stack, axis=0) - np.min(y_stack, axis=0)
    admissible = (
        np.all(distance_stack <= LOCAL_DISTANCE_CEILING, axis=0)
        & np.all(np.isfinite(y_stack), axis=0)
        & (spread <= LOCAL_COLLAPSE_LIMIT)
    )
    violations = np.flatnonzero(~admissible)
    stop = int(violations[0]) if len(violations) else len(time)
    prefix = np.zeros(len(time), dtype=bool)
    prefix[:stop] = True
    end_time = float(time[stop - 1]) if stop else None
    reason = None
    if len(violations):
        index = int(violations[0])
        reasons = []
        if not np.all(distance_stack[:, index] <= LOCAL_DISTANCE_CEILING):
            reasons.append("candidate_a_distance_ceiling")
        if not np.all(np.isfinite(y_stack[:, index])):
            reasons.append("invalid_log_distance")
        if spread[index] > LOCAL_COLLAPSE_LIMIT:
            reasons.append("perturbation_collapse_spread")
        reason = reasons
    return {
        "time": time,
        "mask": prefix,
        "end_time": end_time,
        "first_violation_time": float(time[stop]) if stop < len(time) else None,
        "first_violation_reasons": reason,
        "spread": spread,
        "maximum_prefix_spread": float(np.max(spread[prefix])) if np.any(prefix) else None,
    }


def interval_analysis(
    start: float,
    end: float,
    runs_by_epsilon: dict[float, dict[str, Any]],
    locality: dict[str, Any],
) -> dict[str, Any]:
    time = next(iter(runs_by_epsilon.values()))["series"]["time"]
    local = locality["end_time"] is not None and end <= locality["end_time"] + 1.0e-12
    duration_ok = end - start + 1.0e-12 >= MIN_DURATION_IN_TC * characteristic_time()
    metrics: dict[str, dict[str, Any]] = {"candidate_a": {}, "candidate_b": {}, "candidate_a_lc2": {}}
    for epsilon in EPSILONS:
        series = runs_by_epsilon[epsilon]["series"]
        key = f"{epsilon:.0e}"
        metrics["candidate_a"][key] = linear_diagnostic(time, series["y_a"], start, end)
        metrics["candidate_b"][key] = linear_diagnostic(time, series["y_b"], start, end)
        metrics["candidate_a_lc2"][key] = linear_diagnostic(time, series["y_a_alt"], start, end)
    mask = interval_mask(time, start, end)
    a_rates = [metrics["candidate_a"][f"{value:.0e}"]["endpoint_rate_per_second"] for value in EPSILONS]
    b_rates = [metrics["candidate_b"][f"{value:.0e}"]["endpoint_rate_per_second"] for value in EPSILONS]
    a_y = np.stack([runs_by_epsilon[value]["series"]["y_a"] for value in EPSILONS])
    b_y = np.stack([runs_by_epsilon[value]["series"]["y_b"] for value in EPSILONS])
    a_collapse = float(np.max(np.max(a_y[:, mask], axis=0) - np.min(a_y[:, mask], axis=0)))
    b_collapse = float(np.max(np.max(b_y[:, mask], axis=0) - np.min(b_y[:, mask], axis=0)))
    core_checks = {
        "duration_at_least_2tc": duration_ok,
        "inside_common_local_regime": local,
        "baseline_log_growth_at_least_2": metrics["candidate_a"]["1e-05"]["log_growth"] >= MIN_LOG_GROWTH,
        "candidate_a_collapse_within_limit": a_collapse <= LOCAL_COLLAPSE_LIMIT,
        "candidate_a_r_squared": all(
            item["r_squared"] >= MIN_A_R_SQUARED for item in metrics["candidate_a"].values()
        ),
        "candidate_a_residual": all(
            item["max_abs_residual"] <= MAX_A_ABS_RESIDUAL for item in metrics["candidate_a"].values()
        ),
        "candidate_a_rate_spread": relative_spread(a_rates) <= MAX_A_RATE_RELATIVE_SPREAD,
        "candidate_b_positive_rates": all(value > 0.0 for value in b_rates),
        "candidate_b_r_squared": all(
            item["r_squared"] >= MIN_B_R_SQUARED for item in metrics["candidate_b"].values()
        ),
        "candidate_b_collapse_within_limit": b_collapse <= MAX_B_COLLAPSE_SPREAD,
        "candidate_a_b_rate_compatible": relative_difference(
            float(np.median(a_rates)), float(np.median(b_rates))
        )
        <= MAX_A_B_MEDIAN_RATE_RELATIVE_DIFFERENCE,
        "alternative_scaling_positive": metrics["candidate_a_lc2"]["1e-05"]["endpoint_rate_per_second"] > 0.0,
        "alternative_scaling_r_squared": metrics["candidate_a_lc2"]["1e-05"]["r_squared"]
        >= MIN_ALTERNATIVE_SCALE_R_SQUARED,
    }
    return {
        "interval_id": f"{start:.2f}_{end:.2f}",
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": end - start,
        "locality_end_seconds": locality["end_time"],
        "metrics": metrics,
        "candidate_a_log_collapse_spread": a_collapse,
        "candidate_b_log_collapse_spread": b_collapse,
        "candidate_a_rate_relative_spread": relative_spread(a_rates),
        "candidate_b_rate_relative_spread": relative_spread(b_rates),
        "candidate_a_median_rate_per_second": float(np.median(a_rates)),
        "candidate_b_median_rate_per_second": float(np.median(b_rates)),
        "candidate_a_b_median_rate_relative_difference": relative_difference(
            float(np.median(a_rates)), float(np.median(b_rates))
        ),
        "core_checks": core_checks,
        "core_accepted": all(core_checks.values()),
        "rejection_reasons": [name for name, passed in core_checks.items() if not passed],
    }


def moving_slope(time: np.ndarray, values: np.ndarray, locality_end: float) -> tuple[np.ndarray, np.ndarray]:
    half_width = MOVING_WINDOW_SECONDS / 2.0
    centers: list[float] = []
    slopes: list[float] = []
    for center in np.asarray(time):
        start = rounded_time(float(center - half_width))
        end = rounded_time(float(center + half_width))
        if start < T_START or end > locality_end or end - start < MOVING_WINDOW_SECONDS - 1.0e-12:
            continue
        diagnostic = linear_diagnostic(time, values, start, end)
        if diagnostic["valid"]:
            centers.append(float(center))
            slopes.append(diagnostic["fitted_slope_per_second"])
    return np.asarray(centers), np.asarray(slopes)


def run_summary(
    run: dict[str, Any],
    primary_start: float | None = None,
    primary_end: float | None = None,
    locality_end: float | None = None,
) -> dict[str, Any]:
    result = {
        "run_id": run["run_id"],
        "accepted": run["accepted"],
        "issues": run["issues"],
        "epsilon_radians": run["epsilon"],
        "policy": run["policy"],
        "sample_count": run["sample_count"],
        "sample_interval_seconds": (T_STOP - T_START) / (run["sample_count"] - 1),
        "checks": run.get("checks", {}),
        "reference_max_normalized_energy_drift": run["reference"]["max_energy_drift"],
        "nearby_max_normalized_energy_drift": run["nearby"]["max_energy_drift"],
        "reference_solver_status": run["reference"].get("solver_metadata", {}),
        "nearby_solver_status": run["nearby"].get("solver_metadata", {}),
    }
    if run.get("series") is not None:
        series = run["series"]
        first_crossings = [
            first_absolute_revolution_difference_time(
                series["time"], series["revolution_difference"][:, index]
            )
            for index in range(2)
        ]
        result["winding_history"] = {
            "convention": (
                "Theta_i is the continuously unwrapped physical angle; "
                "R_i=(Theta_i(t)-Theta_i(0))/(2*pi). Crossing is the first sampled "
                "time with abs(Delta R_i)>=1; this is a history diagnostic, not a distance."
            ),
            "reference_total_signed_revolutions": [
                float(value) for value in series["reference_revolutions"][-1]
            ],
            "nearby_total_signed_revolutions": [
                float(value) for value in series["nearby_revolutions"][-1]
            ],
            "final_lifted_angle_differences_radians": [
                float(value) for value in series["lifted_angle_difference"][-1]
            ],
            "final_revolution_differences": [
                float(value) for value in series["revolution_difference"][-1]
            ],
            "first_absolute_one_revolution_difference_seconds": first_crossings,
            "first_absolute_one_revolution_difference_phase": [
                revolution_crossing_phase(
                    crossing, primary_start, primary_end, locality_end
                )
                for crossing in first_crossings
            ],
            "maximum_inter_sample_angle_step_radians": {
                "reference": series["reference_max_angle_step"],
                "nearby": series["nearby_max_angle_step"],
            },
            "unwrapping_sampling_condition": (
                "Each raw EL angle changes by less than pi between output samples."
            ),
        }
    return result


def run_investigation() -> dict[str, Any]:
    baseline_runs = {
        epsilon: derive_pair(
            f"baseline_eps_{epsilon:.0e}", epsilon, SIMPLE_REFERENCE_SOLVER_POLICY, SAMPLE_COUNT
        )
        for epsilon in EPSILONS
    }
    stricter = derive_pair(
        "stricter_eps_1e-05", BASELINE_EPSILON, STRICTER_POLICY, SAMPLE_COUNT
    )
    dense = derive_pair(
        "dense_eps_1e-05", BASELINE_EPSILON, SIMPLE_REFERENCE_SOLVER_POLICY, DENSE_SAMPLE_COUNT
    )
    all_runs = [*baseline_runs.values(), stricter, dense]
    if not all(run["accepted"] and run["series"] is not None for run in all_runs):
        return {
            "summary": {
                "experiment": EXPERIMENT_NAME,
                "status": "rejected_numerical_failure",
                "accepted": False,
                "failure_reason": "one_or_more_required_runs_failed",
                "runs": [run_summary(run) for run in all_runs],
                "claim_boundary": "No growth interpretation is permitted after numerical rejection.",
            },
            "runs": all_runs,
            "audit": [],
            "local_slopes": {},
        }

    locality = common_locality(baseline_runs)
    primary_start, primary_end = primary_interval()
    primary = interval_analysis(primary_start, primary_end, baseline_runs, locality)
    audit = [interval_analysis(start, end, baseline_runs, locality) for start, end in audit_intervals()]

    baseline_series = baseline_runs[BASELINE_EPSILON]["series"]
    strict_fit = linear_diagnostic(
        stricter["series"]["time"], stricter["series"]["y_a"], primary_start, primary_end
    )
    dense_fit = linear_diagnostic(
        dense["series"]["time"], dense["series"]["y_a"], primary_start, primary_end
    )
    baseline_fit = primary["metrics"]["candidate_a"]["1e-05"]
    tolerance_difference = relative_difference(
        baseline_fit["endpoint_rate_per_second"], strict_fit["endpoint_rate_per_second"]
    )
    sampling_difference = relative_difference(
        baseline_fit["endpoint_rate_per_second"], dense_fit["endpoint_rate_per_second"]
    )

    endpoint_results: list[dict[str, Any]] = []
    admissible_endpoint_deviations: list[float] = []
    for start, end in endpoint_neighbours(primary_start, primary_end):
        duration_ok = end - start + 1.0e-12 >= MIN_DURATION_IN_TC * characteristic_time()
        local = locality["end_time"] is not None and end <= locality["end_time"] + 1.0e-12
        diagnostic = linear_diagnostic(
            baseline_series["time"], baseline_series["y_a"], start, end
        )
        admissible = duration_ok and local and diagnostic["valid"]
        deviation = None
        if admissible:
            deviation = relative_difference(
                baseline_fit["endpoint_rate_per_second"], diagnostic["endpoint_rate_per_second"]
            )
            admissible_endpoint_deviations.append(deviation)
        endpoint_results.append(
            {
                "start_seconds": start,
                "end_seconds": end,
                "duration_ok": duration_ok,
                "inside_common_local_regime": local,
                "admissible": admissible,
                "diagnostic": diagnostic,
                "relative_rate_deviation_from_primary": deviation,
                "rejection_reasons": [
                    name
                    for name, passed in {
                        "duration_at_least_2tc": duration_ok,
                        "inside_common_local_regime": local,
                        "complete_fit": diagnostic["valid"],
                    }.items()
                    if not passed
                ],
            }
        )
    endpoint_maximum = (
        max(admissible_endpoint_deviations) if admissible_endpoint_deviations else math.inf
    )

    numerical_checks = {
        "all_required_runs_numerically_accepted": all(run["accepted"] for run in all_runs),
        "tolerance_rate_difference_within_1_percent": tolerance_difference
        <= MAX_TOLERANCE_RATE_RELATIVE_DIFFERENCE,
        "sampling_rate_difference_within_half_percent": sampling_difference
        <= MAX_SAMPLING_RATE_RELATIVE_DIFFERENCE,
    }
    endpoint_check = endpoint_maximum <= MAX_ENDPOINT_RATE_RELATIVE_DEVIATION
    acceptance_checks = {
        **primary["core_checks"],
        "endpoint_rate_stability": endpoint_check,
        **numerical_checks,
    }
    accepted = all(acceptance_checks.values())

    slope_series: dict[str, dict[str, np.ndarray]] = {}
    for epsilon in EPSILONS:
        series = baseline_runs[epsilon]["series"]
        centers, slopes = moving_slope(series["time"], series["y_a"], locality["end_time"])
        slope_series[f"a_{epsilon:.0e}"] = {"time": centers, "slope": slopes}
    centers_b, slopes_b = moving_slope(
        baseline_series["time"], baseline_series["y_b"], locality["end_time"]
    )
    centers_alt, slopes_alt = moving_slope(
        baseline_series["time"], baseline_series["y_a_alt"], locality["end_time"]
    )
    slope_series["b_1e-05"] = {"time": centers_b, "slope": slopes_b}
    slope_series["a_lc2_1e-05"] = {"time": centers_alt, "slope": slopes_alt}

    summary = {
        "experiment": EXPERIMENT_NAME,
        "status": (
            "accepted_finite_approximately_exponential_interval"
            if accepted
            else "no_defensible_common_exponential_interval"
        ),
        "accepted": accepted,
        "failure_reason": None if accepted else "one_or_more_predeclared_checks_failed",
        "question": (
            "Does the controlled nearby-state divergence contain a reproducible finite "
            "interval of approximately exponential growth?"
        ),
        "configuration": {
            "model": MODEL,
            "formulation": FORMULATION,
            "state_order": ["theta1", "theta2", "omega1", "omega2"],
            "base_initial_state_degrees": BASE_STATE_DEGREES.tolist(),
            "perturbation_direction": [0.0, "epsilon", 0.0, 0.0],
            "perturbation_magnitudes_radians": list(EPSILONS),
            "parameters_si": {str(key): float(value) for key, value in PARAMETERS.items()},
            "characteristic_length_metres": LC_BASELINE,
            "alternative_length_metres": LC_ALTERNATIVE,
            "characteristic_time_seconds": characteristic_time(),
            "solver_policy": policy_dict(SIMPLE_REFERENCE_SOLVER_POLICY),
            "stricter_solver_policy": policy_dict(STRICTER_POLICY),
            "t_start_seconds": T_START,
            "t_stop_seconds": T_STOP,
            "sample_count": SAMPLE_COUNT,
            "sample_interval_seconds": 0.01,
            "dense_sample_count": DENSE_SAMPLE_COUNT,
            "energy_drift_limit": ENERGY_DRIFT_LIMIT,
        },
        "definitions": {
            "candidate_a": "||(delta_theta1,delta_theta2,Tc*delta_omega1,Tc*delta_omega2)||_2",
            "candidate_b": "||(delta_r/Lc,Tc*delta_v/Lc)||_2 for both bobs",
            "log_normalized_separation": "y(t)=log(d(t)/d(0))",
            "finite_window_rate": "Lambda(ta,tb)=(y(tb)-y(ta))/(tb-ta)",
            "fitted_slope": "OLS beta-hat diagnostic; not the reported Lambda",
            "moving_slope_window_seconds": MOVING_WINDOW_SECONDS,
            "lifted_angle_history": (
                "Theta_i(t) is a continuous unwrap of the physical angle; "
                "R_i(t)=(Theta_i(t)-Theta_i(0))/(2*pi)"
            ),
            "nearby_history_difference": (
                "DeltaTheta_i=Theta'_i-Theta_i and DeltaR_i=R'_i-R_i; "
                "neither enters Candidate A, Candidate B, locality, interval selection, "
                "or acceptance"
            ),
        },
        "thresholds": {
            "local_distance_ceiling": LOCAL_DISTANCE_CEILING,
            "local_log_collapse_limit": LOCAL_COLLAPSE_LIMIT,
            "minimum_duration_in_characteristic_times": MIN_DURATION_IN_TC,
            "minimum_log_growth": MIN_LOG_GROWTH,
            "candidate_a_minimum_r_squared": MIN_A_R_SQUARED,
            "candidate_a_maximum_absolute_residual": MAX_A_ABS_RESIDUAL,
            "candidate_a_maximum_rate_relative_spread": MAX_A_RATE_RELATIVE_SPREAD,
            "maximum_endpoint_rate_relative_deviation": MAX_ENDPOINT_RATE_RELATIVE_DEVIATION,
            "candidate_b_minimum_r_squared": MIN_B_R_SQUARED,
            "candidate_b_maximum_log_collapse_spread": MAX_B_COLLAPSE_SPREAD,
            "candidate_a_b_maximum_median_rate_relative_difference": MAX_A_B_MEDIAN_RATE_RELATIVE_DIFFERENCE,
            "maximum_tolerance_rate_relative_difference": MAX_TOLERANCE_RATE_RELATIVE_DIFFERENCE,
            "maximum_sampling_rate_relative_difference": MAX_SAMPLING_RATE_RELATIVE_DIFFERENCE,
            "alternative_scale_minimum_r_squared": MIN_ALTERNATIVE_SCALE_R_SQUARED,
            "threshold_status": "provisional and fixed in README before execution",
        },
        "locality": {
            "common_local_end_seconds": locality["end_time"],
            "first_violation_time_seconds": locality["first_violation_time"],
            "first_violation_reasons": locality["first_violation_reasons"],
            "maximum_log_collapse_spread_in_prefix": locality["maximum_prefix_spread"],
        },
        "primary_interval": primary,
        "endpoint_sensitivity": {
            "shift_seconds": ENDPOINT_SHIFT_SECONDS,
            "maximum_admissible_relative_rate_deviation": endpoint_maximum,
            "accepted": endpoint_check,
            "neighbours": endpoint_results,
        },
        "numerical_robustness": {
            "baseline_candidate_a": baseline_fit,
            "stricter_candidate_a": strict_fit,
            "relative_rate_difference_stricter": tolerance_difference,
            "dense_candidate_a": dense_fit,
            "relative_rate_difference_dense": sampling_difference,
            "checks": numerical_checks,
        },
        "acceptance_checks": acceptance_checks,
        "runs": [
            run_summary(run, primary_start, primary_end, locality["end_time"])
            for run in all_runs
        ],
        "audit_interval_count": len(audit),
        "candidate_interval_audit": audit,
        "strongest_claim": (
            "For this controlled state and perturbation direction, the predeclared finite "
            "interval supports approximately exponential full-state separation under "
            "Candidate A, with qualitatively compatible Candidate B behaviour."
            if accepted
            else "No defensible common approximately exponential interval was identified under the predeclared rule."
        ),
        "claim_boundary": (
            "Lambda(ta,tb) is a descriptive finite-window logarithmic growth rate, not a "
            "Lyapunov exponent. No renormalisation, tangent dynamics, asymptotic limit, "
            "coordinate-invariant rate, state-space generalisation, or chaos classification "
            "is computed or supported."
        ),
    }
    return {"summary": summary, "runs": all_runs, "audit": audit, "local_slopes": slope_series}


def json_write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def csv_number(value: float) -> float | str:
    return float(value) if np.isfinite(value) else ""


def write_timeseries(path: Path, runs: list[dict[str, Any]]) -> None:
    fields = (
        "run_id", "epsilon_rad", "time_s", "candidate_a", "candidate_b", "candidate_a_lc2",
        "log_candidate_a", "log_candidate_b", "log_candidate_a_lc2",
        "reference_theta1_lifted_rad", "reference_theta2_lifted_rad",
        "nearby_theta1_lifted_rad", "nearby_theta2_lifted_rad",
        "reference_revolutions_1", "reference_revolutions_2",
        "nearby_revolutions_1", "nearby_revolutions_2",
        "delta_theta1_lifted_rad", "delta_theta2_lifted_rad",
        "delta_revolutions_1", "delta_revolutions_2",
        "reference_energy_drift", "nearby_energy_drift",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            if run["series"] is None:
                continue
            series = run["series"]
            for index, time_value in enumerate(series["time"]):
                writer.writerow(
                    {
                        "run_id": run["run_id"],
                        "epsilon_rad": run["epsilon"],
                        "time_s": float(time_value),
                        "candidate_a": float(series["distance_a"][index]),
                        "candidate_b": float(series["distance_b"][index]),
                        "candidate_a_lc2": float(series["distance_a_alt"][index]),
                        "log_candidate_a": csv_number(series["y_a"][index]),
                        "log_candidate_b": csv_number(series["y_b"][index]),
                        "log_candidate_a_lc2": csv_number(series["y_a_alt"][index]),
                        "reference_theta1_lifted_rad": float(series["reference_lifted_angles"][index, 0]),
                        "reference_theta2_lifted_rad": float(series["reference_lifted_angles"][index, 1]),
                        "nearby_theta1_lifted_rad": float(series["nearby_lifted_angles"][index, 0]),
                        "nearby_theta2_lifted_rad": float(series["nearby_lifted_angles"][index, 1]),
                        "reference_revolutions_1": float(series["reference_revolutions"][index, 0]),
                        "reference_revolutions_2": float(series["reference_revolutions"][index, 1]),
                        "nearby_revolutions_1": float(series["nearby_revolutions"][index, 0]),
                        "nearby_revolutions_2": float(series["nearby_revolutions"][index, 1]),
                        "delta_theta1_lifted_rad": float(series["lifted_angle_difference"][index, 0]),
                        "delta_theta2_lifted_rad": float(series["lifted_angle_difference"][index, 1]),
                        "delta_revolutions_1": float(series["revolution_difference"][index, 0]),
                        "delta_revolutions_2": float(series["revolution_difference"][index, 1]),
                        "reference_energy_drift": float(series["reference_energy_drift"][index]),
                        "nearby_energy_drift": float(series["nearby_energy_drift"][index]),
                    }
                )


def write_audit(path: Path, audit: list[dict[str, Any]]) -> None:
    fields = (
        "interval_id", "start_s", "end_s", "duration_s", "local", "core_accepted",
        "rejection_reasons", "a_median_rate", "a_rate_spread", "a_min_r2", "a_max_residual",
        "b_median_rate", "b_rate_spread", "b_min_r2", "a_b_rate_difference",
        "a_lc2_baseline_rate", "a_lc2_baseline_r2",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in audit:
            a = item["metrics"]["candidate_a"]
            b = item["metrics"]["candidate_b"]
            alt = item["metrics"]["candidate_a_lc2"]["1e-05"]
            writer.writerow(
                {
                    "interval_id": item["interval_id"],
                    "start_s": item["start_seconds"],
                    "end_s": item["end_seconds"],
                    "duration_s": item["duration_seconds"],
                    "local": item["core_checks"]["inside_common_local_regime"],
                    "core_accepted": item["core_accepted"],
                    "rejection_reasons": ";".join(item["rejection_reasons"]),
                    "a_median_rate": item["candidate_a_median_rate_per_second"],
                    "a_rate_spread": item["candidate_a_rate_relative_spread"],
                    "a_min_r2": min(value["r_squared"] for value in a.values()),
                    "a_max_residual": max(value["max_abs_residual"] for value in a.values()),
                    "b_median_rate": item["candidate_b_median_rate_per_second"],
                    "b_rate_spread": item["candidate_b_rate_relative_spread"],
                    "b_min_r2": min(value["r_squared"] for value in b.values()),
                    "a_b_rate_difference": item["candidate_a_b_median_rate_relative_difference"],
                    "a_lc2_baseline_rate": alt["endpoint_rate_per_second"],
                    "a_lc2_baseline_r2": alt["r_squared"],
                }
            )


def write_local_slopes(path: Path, local_slopes: dict[str, dict[str, np.ndarray]]) -> None:
    names = tuple(local_slopes)
    fields = ["index", *[f"{name}_time_s" for name in names], *[f"{name}_slope_per_s" for name in names]]
    length = max(len(value["time"]) for value in local_slopes.values())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(length):
            row: dict[str, Any] = {"index": index}
            for name in names:
                item = local_slopes[name]
                row[f"{name}_time_s"] = float(item["time"][index]) if index < len(item["time"]) else ""
                row[f"{name}_slope_per_s"] = float(item["slope"][index]) if index < len(item["slope"]) else ""
            writer.writerow(row)


def load_pyplot():
    import matplotlib.pyplot as plt

    return plt


def save_figure(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    load_pyplot().close(fig)


def write_plots(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    if any(run["series"] is None for run in result["runs"]):
        return []
    plt = load_pyplot()
    baseline_runs = {run["epsilon"]: run for run in result["runs"][:3]}
    summary = result["summary"]
    start = summary["primary_interval"]["start_seconds"]
    end = summary["primary_interval"]["end_seconds"]
    local_end = summary["locality"]["common_local_end_seconds"]
    paths: list[Path] = []

    path = output_dir / "01_perturbation_collapse.png"
    fig, axis = plt.subplots(figsize=(10, 6))
    for epsilon in EPSILONS:
        series = baseline_runs[epsilon]["series"]
        axis.plot(series["time"], series["y_a"], label=fr"$\varepsilon={epsilon:.0e}$ rad")
    axis.axvspan(start, end, color="tab:green", alpha=0.12, label="predeclared primary interval")
    axis.axvline(local_end, color="black", linestyle=":", label="common locality end")
    axis.set(xlim=(0.0, min(2.0, local_end + 0.25)), xlabel="time / s", ylabel=r"$\log[d_\varepsilon(t)/d_\varepsilon(0)]$", title="Candidate A perturbation collapse")
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "02_local_slope.png"
    fig, axis = plt.subplots(figsize=(10, 6))
    for epsilon in EPSILONS:
        item = result["local_slopes"][f"a_{epsilon:.0e}"]
        axis.plot(item["time"], item["slope"], label=fr"A, $\varepsilon={epsilon:.0e}$")
    axis.axvspan(start, end, color="tab:green", alpha=0.12, label="primary interval")
    axis.set(xlabel="window centre / s", ylabel=r"local fitted $\widehat\beta$ / s$^{-1}$", title=f"Fixed {MOVING_WINDOW_SECONDS:.2f} s local-slope diagnostic")
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=8)
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "03_interval_audit.png"
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    labels = [f"{item['start_seconds']:.2f}–{item['end_seconds']:.2f}" for item in result["audit"]]
    x = np.arange(len(labels))
    for epsilon in EPSILONS:
        rates = [item["metrics"]["candidate_a"][f"{epsilon:.0e}"]["endpoint_rate_per_second"] for item in result["audit"]]
        axes[0].plot(x, rates, marker="o", label=f"A, eps={epsilon:.0e}")
    min_r2 = [min(value["r_squared"] for value in item["metrics"]["candidate_a"].values()) for item in result["audit"]]
    axes[1].plot(x, min_r2, marker="o", color="tab:purple", label="minimum A R²")
    axes[1].axhline(MIN_A_R_SQUARED, color="black", linestyle=":", label="provisional R² threshold")
    axes[0].set(ylabel=r"$\Lambda(t_a,t_b)$ / s$^{-1}$", title="All predeclared interval rates — no best-window optimisation")
    axes[1].set(ylabel="minimum R²", xlabel="candidate interval / s")
    axes[1].set_xticks(x, labels, rotation=45, ha="right")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=8)
    save_figure(fig, path)
    paths.append(path)

    baseline = baseline_runs[BASELINE_EPSILON]["series"]
    path = output_dir / "04_candidate_a_vs_b.png"
    fig, axis = plt.subplots(figsize=(10, 6))
    axis.plot(baseline["time"], baseline["y_a"], label="A: scaled EL")
    axis.plot(baseline["time"], baseline["y_b"], label="B: scaled Cartesian")
    axis.axvspan(start, end, color="tab:green", alpha=0.12, label="primary interval")
    axis.axvline(local_end, color="black", linestyle=":", label="A common locality end")
    axis.set(xlim=(0.0, min(2.0, local_end + 0.25)), xlabel="time / s", ylabel="log normalized distance", title="Full-state metric robustness")
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "05_scaling_sensitivity.png"
    fig, axis = plt.subplots(figsize=(10, 6))
    axis.plot(baseline["time"], baseline["y_a"], label="Candidate A, Lc=1 m")
    axis.plot(baseline["time"], baseline["y_a_alt"], label="Candidate A, Lc=2 m")
    axis.axvspan(start, end, color="tab:green", alpha=0.12, label="primary interval")
    axis.set(xlim=(0.0, min(2.0, local_end + 0.25)), xlabel="time / s", ylabel="log normalized distance", title="Fixed characteristic-scaling comparison")
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "06_numerical_validity.png"
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for epsilon in EPSILONS:
        series = baseline_runs[epsilon]["series"]
        axes[0].plot(series["time"], series["nearby_energy_drift"], label=f"nearby eps={epsilon:.0e}")
    axes[0].plot(baseline["time"], baseline["reference_energy_drift"], color="black", label="reference")
    axes[0].axhline(ENERGY_DRIFT_LIMIT, color="red", linestyle=":", label="rejection limit")
    endpoint = summary["endpoint_sensitivity"]["neighbours"]
    admissible = [item for item in endpoint if item["admissible"]]
    axes[1].bar(
        [f"{item['start_seconds']:.2f}–{item['end_seconds']:.2f}" for item in admissible],
        [item["relative_rate_deviation_from_primary"] for item in admissible],
    )
    axes[1].axhline(MAX_ENDPOINT_RATE_RELATIVE_DEVIATION, color="red", linestyle=":", label="endpoint threshold")
    axes[0].set(ylabel="normalized energy drift", title="Numerical validity cannot be overridden by plots")
    axes[1].set(ylabel="relative rate deviation", xlabel="admissible endpoint neighbour / s", title="Endpoint sensitivity")
    axes[1].tick_params(axis="x", rotation=45)
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=8)
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "07_winding_history.png"
    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    time = baseline["time"]
    for index, axis in enumerate(axes[:2]):
        axis.plot(
            time,
            baseline["reference_revolutions"][:, index],
            label=f"reference $R_{index + 1}$",
        )
        axis.plot(
            time,
            baseline["nearby_revolutions"][:, index],
            linestyle="--",
            label=f"nearby $R'_{index + 1}$",
        )
        axis.set_ylabel("signed revolutions")
        axis.grid(True, alpha=0.25)
        axis.legend(fontsize=8)
    axes[0].set_title(
        "Lifted angular histories (baseline $\\varepsilon=10^{-5}$ rad); not state-space distances"
    )
    axes[2].plot(time, baseline["revolution_difference"][:, 0], label=r"$\Delta R_1$")
    axes[2].plot(time, baseline["revolution_difference"][:, 1], label=r"$\Delta R_2$")
    axes[2].axhline(1.0, color="black", linestyle=":", linewidth=1)
    axes[2].axhline(-1.0, color="black", linestyle=":", linewidth=1)
    axes[2].set(
        xlabel="time / s",
        ylabel="revolution difference",
        title="Nearby-history difference; $|\\Delta R_i|=1$ crossing shown only as a history marker",
    )
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(fontsize=8)
    for axis in axes:
        axis.axvspan(start, end, color="tab:green", alpha=0.08)
        axis.axvline(local_end, color="black", linestyle="--", linewidth=0.8, alpha=0.6)
    save_figure(fig, path)
    paths.append(path)
    return paths


def write_output_bundle(result: dict[str, Any], output_dir: Path, plots: bool) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    json_write(summary_path, result["summary"])
    audit_json_path = output_dir / "interval_audit.json"
    json_write(audit_json_path, result["audit"])
    audit_csv_path = output_dir / "interval_audit.csv"
    write_audit(audit_csv_path, result["audit"])
    timeseries_path = output_dir / "growth_timeseries.csv"
    write_timeseries(timeseries_path, result["runs"])
    slopes_path = output_dir / "local_slopes.csv"
    write_local_slopes(slopes_path, result["local_slopes"])
    plot_paths = write_plots(output_dir, result) if plots else []
    manifest_path = output_dir / "manifest.json"
    created = [
        manifest_path,
        summary_path,
        audit_json_path,
        audit_csv_path,
        timeseries_path,
        slopes_path,
        *plot_paths,
    ]
    json_write(
        manifest_path,
        {
            "artifact": EXPERIMENT_NAME,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": result["summary"]["status"],
            "accepted": result["summary"]["accepted"],
            "created_files": [path.name for path in created],
            "contract": "development/chaos_content/experiments/foundations/004_finite_time_exponential_growth/README.md",
            "reproduction_command": (
                "uv run python development/chaos_content/experiments/"
                "004_finite_time_exponential_growth/finite_time_exponential_growth.py "
                "--self-check "
                "--output-dir development/chaos_content/outputs/"
                "finite_time_exponential_growth/baseline --plots"
            ),
            "claim_boundary": result["summary"]["claim_boundary"],
            "notes": [
                "Finite-window inference audit only; no Lyapunov exponent.",
                "No perturbation renormalisation or tangent dynamics.",
                "The predeclared primary interval cannot be replaced by a better-looking audit interval.",
                "Lifted angles and signed revolutions are history diagnostics, not distance components.",
            ],
        },
    )
    return created


def assert_self_check(result: dict[str, Any]) -> None:
    summary = result["summary"]
    if summary["experiment"] != EXPERIMENT_NAME:
        raise AssertionError("Unexpected experiment identity.")
    if any(run["series"] is None for run in result["runs"]):
        raise AssertionError("A required run lacks diagnostic series.")
    if len(result["audit"]) != len(audit_intervals()):
        raise AssertionError("Candidate interval audit is incomplete.")
    if tuple(primary_interval()) != (0.32, 1.12):
        raise AssertionError("Predeclared primary interval changed.")
    if summary["status"] not in {
        "accepted_finite_approximately_exponential_interval",
        "no_defensible_common_exponential_interval",
    }:
        raise AssertionError(f"Unexpected completed status: {summary['status']}")
    if "Lyapunov exponent" not in summary["claim_boundary"]:
        raise AssertionError("Claim boundary is incomplete.")
    for run in summary["runs"]:
        if "winding_history" not in run:
            raise AssertionError("A required run lacks winding-history evidence.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args()
    if args.plots and args.output_dir is None:
        parser.error("--plots requires --output-dir")
    result = run_investigation()
    if args.self_check:
        assert_self_check(result)
        print(f"self-check: passed ({result['summary']['status']})")
    if args.output_dir is not None:
        for path in write_output_bundle(result, args.output_dir, args.plots):
            print(path)
    if not args.self_check and args.output_dir is None:
        print(json.dumps(result["summary"], indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
