"""Interrogate nearby-state distance conventions without estimating an exponent.

The adjacent README is the experiment contract.  This is intentionally a
small, local script rather than reusable chaos-metric infrastructure.
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


EXPERIMENT_NAME = "el_nearby_state_distance_conventions"
MODEL = "simple"
FORMULATION = "Euler-Lagrange"
PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
BASE_INITIAL_STATE_DEGREES = np.array([179.0, 179.0, 0.0, 0.0])
BASE_INITIAL_STATE_RADIANS = np.deg2rad(BASE_INITIAL_STATE_DEGREES)
BASELINE_EPSILON_RADIANS = 1.0e-5
PERTURBATION_MAGNITUDES_RADIANS = (1.0e-4, 1.0e-5, 1.0e-6)
PERTURBED_COMPONENT = "theta2"
T_START = 0.0
T_STOP = 20.0
BASELINE_SAMPLE_COUNT = 2001  # 100 Hz, including both endpoints.
DENSE_SAMPLE_COUNT = 4001  # 200 Hz; output sampling only.
CHARACTERISTIC_LENGTH_METRES = 1.0
ALTERNATIVE_LENGTH_METRES = 2.0
MAX_NORMALIZED_ENERGY_DRIFT = 1.0e-7
LOCAL_DISTANCE_CEILING = 1.0e-2
SAMPLING_MAX_ABSOLUTE_DISTANCE_DIFFERENCE = 1.0e-10
LOG_TRACE_AGREEMENT_LIMIT = 1.0e-1
INITIAL_ABSOLUTE_TOLERANCE = 2.0e-12

STRICTER_SOLVER_POLICY = SolverPolicy(
    name="lyapunov_distance_stricter_check",
    method="DOP853",
    rtol=1.0e-11,
    atol=1.0e-13,
    role="experiment-local stricter comparison; not a production policy",
)


def wrap_angle_difference(values: np.ndarray) -> np.ndarray:
    """Map angular differences deterministically to (-pi, pi]."""

    values = np.asarray(values, dtype=float)
    wrapped = np.remainder(values + math.pi, 2.0 * math.pi) - math.pi
    return np.where(wrapped == -math.pi, math.pi, wrapped)


def wrapped_el_difference(reference: np.ndarray, nearby: np.ndarray) -> np.ndarray:
    """Return (wrapped angle differences, ordinary velocity differences)."""

    reference = np.asarray(reference, dtype=float)
    nearby = np.asarray(nearby, dtype=float)
    difference = nearby - reference
    result = np.array(difference, copy=True)
    result[..., :2] = wrap_angle_difference(difference[..., :2])
    return result


def characteristic_time(length_metres: float) -> float:
    return math.sqrt(float(length_metres) / float(PARAMETERS[g]))


def candidate_a_distance(
    wrapped_difference: np.ndarray, length_metres: float = CHARACTERISTIC_LENGTH_METRES
) -> np.ndarray:
    """Dimensionless generalized-coordinate EL full-state norm."""

    difference = np.asarray(wrapped_difference, dtype=float)
    scaled = np.array(difference, copy=True)
    scaled[..., 2:] *= characteristic_time(length_metres)
    return np.linalg.norm(scaled, axis=-1)


def cartesian_full_state(state: np.ndarray) -> np.ndarray:
    """Map EL states to (r1, r2, v1, v2) in the experiment's fixed order."""

    state = np.asarray(state, dtype=float)
    theta1 = state[..., 0]
    theta2 = state[..., 1]
    omega1 = state[..., 2]
    omega2 = state[..., 3]
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
    reference: np.ndarray,
    nearby: np.ndarray,
    length_metres: float = CHARACTERISTIC_LENGTH_METRES,
) -> np.ndarray:
    """Dimensionless Cartesian bob-position and bob-velocity full-state norm."""

    delta = cartesian_full_state(nearby) - cartesian_full_state(reference)
    scaled = np.array(delta, copy=True)
    scaled[..., :4] /= length_metres
    scaled[..., 4:] *= characteristic_time(length_metres) / length_metres
    return np.linalg.norm(scaled, axis=-1)


def second_bob_distance(reference: np.ndarray, nearby: np.ndarray) -> np.ndarray:
    """Dimensional display observable inherited from the sensitivity prototype."""

    delta = cartesian_full_state(nearby)[..., 2:4] - cartesian_full_state(reference)[..., 2:4]
    return np.linalg.norm(delta, axis=-1)


def _simple_energy(state: np.ndarray) -> np.ndarray:
    theta1, theta2, omega1, omega2 = np.asarray(state, dtype=float).T
    length1 = float(PARAMETERS[l1])
    length2 = float(PARAMETERS[l2])
    mass1 = float(PARAMETERS[m1])
    mass2 = float(PARAMETERS[m2])
    gravity = float(PARAMETERS[g])
    kinetic = (
        0.5 * (mass1 + mass2) * length1**2 * omega1**2
        + 0.5 * mass2 * length2**2 * omega2**2
        + mass2
        * length1
        * length2
        * omega1
        * omega2
        * np.cos(theta1 - theta2)
    )
    potential = -(
        (mass1 + mass2) * gravity * length1 * np.cos(theta1)
        + mass2 * gravity * length2 * np.cos(theta2)
    )
    return np.asarray(kinetic + potential, dtype=float)


def _energy_scale() -> float:
    return float(PARAMETERS[g]) * (
        (float(PARAMETERS[m1]) + float(PARAMETERS[m2])) * float(PARAMETERS[l1])
        + float(PARAMETERS[m2]) * float(PARAMETERS[l2])
    )


def _policy_dict(policy: SolverPolicy) -> dict[str, Any]:
    return {
        "name": policy.name,
        "method": policy.method,
        "rtol": policy.rtol,
        "atol": policy.atol,
        "role": policy.role,
    }


def _nearby_initial_state_degrees(epsilon_radians: float) -> np.ndarray:
    nearby = np.array(BASE_INITIAL_STATE_DEGREES, copy=True)
    nearby[1] += math.degrees(epsilon_radians)
    return nearby


def _integrate_one(
    label: str,
    initial_state_degrees: np.ndarray,
    policy: SolverPolicy,
    sample_count: int,
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
    except Exception as exc:  # pragma: no cover - defensive command boundary
        return {
            "label": label,
            "accepted": False,
            "issues": [f"integration_exception: {exc}"],
            "time": np.array([]),
            "state": np.empty((0, 4)),
            "energy": np.array([]),
            "energy_drift": np.array([]),
            "max_energy_drift": None,
            "solver_metadata": {},
        }

    state = np.asarray(model.sol, dtype=float)
    returned_time = np.asarray(model.solver_time, dtype=float)
    metadata = model.solver_metadata
    if metadata.success is not True:
        issues.append(f"solver_failed: {metadata.message}")
    if metadata.returned_time_matches_requested is not True:
        issues.append("returned_time_does_not_match_requested")
    if returned_time.shape != requested_time.shape or not np.array_equal(
        returned_time, requested_time
    ):
        issues.append("returned_time_array_is_incomplete_or_misaligned")
    if state.shape != (sample_count, 4):
        issues.append(f"unexpected_solution_shape: {state.shape}")
    if not np.all(np.isfinite(state)):
        issues.append("non_finite_state_values")

    energy = np.array([])
    drift = np.array([])
    maximum_drift: float | None = None
    if not issues:
        energy = _simple_energy(state)
        drift = np.abs(energy - energy[0]) / _energy_scale()
        if not np.all(np.isfinite(energy)) or not np.all(np.isfinite(drift)):
            issues.append("non_finite_energy_diagnostic")
        else:
            maximum_drift = float(np.max(drift))
            if maximum_drift > MAX_NORMALIZED_ENERGY_DRIFT:
                issues.append(
                    "energy_drift_exceeded: "
                    f"{maximum_drift:.6e} > {MAX_NORMALIZED_ENERGY_DRIFT:.6e}"
                )

    return {
        "label": label,
        "accepted": not issues,
        "issues": issues,
        "time": returned_time,
        "state": state,
        "energy": energy,
        "energy_drift": drift,
        "max_energy_drift": maximum_drift,
        "solver_metadata": metadata.to_dict(),
    }


def _safe_normalized_distance(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    ratios = np.full(values.shape, np.nan)
    logs = np.full(values.shape, np.nan)
    valid = np.isfinite(values) & (values > 0.0)
    if values.size and np.isfinite(values[0]) and values[0] > 0.0:
        ratios[valid] = values[valid] / values[0]
        log_valid = valid & (ratios > 0.0)
        logs[log_valid] = np.log(ratios[log_valid])
    return ratios, logs, np.isfinite(logs)


def _derive_pair(
    run_id: str,
    epsilon_radians: float,
    policy: SolverPolicy,
    sample_count: int,
) -> dict[str, Any]:
    reference = _integrate_one(
        f"{run_id}:reference", BASE_INITIAL_STATE_DEGREES, policy, sample_count
    )
    nearby = _integrate_one(
        f"{run_id}:nearby",
        _nearby_initial_state_degrees(epsilon_radians),
        policy,
        sample_count,
    )
    issues = [
        f"{trajectory['label']}: {issue}"
        for trajectory in (reference, nearby)
        for issue in trajectory["issues"]
    ]
    if issues:
        return {
            "run_id": run_id,
            "accepted": False,
            "issues": issues,
            "epsilon_radians": epsilon_radians,
            "policy": _policy_dict(policy),
            "sample_count": sample_count,
            "reference": reference,
            "nearby": nearby,
            "series": None,
            "checks": {"both_integrations_accepted": False},
        }

    if not np.array_equal(reference["time"], nearby["time"]):
        issues.append("pair_time_arrays_are_not_identical")

    raw_difference = wrapped_el_difference(reference["state"], nearby["state"])
    distance_a = candidate_a_distance(raw_difference)
    distance_a_alternative = candidate_a_distance(raw_difference, ALTERNATIVE_LENGTH_METRES)
    distance_b = candidate_b_distance(reference["state"], nearby["state"])
    distance_bob = second_bob_distance(reference["state"], nearby["state"])
    a_ratio, a_log, a_log_valid = _safe_normalized_distance(distance_a)
    b_ratio, b_log, b_log_valid = _safe_normalized_distance(distance_b)
    bob_ratio, bob_log, bob_log_valid = _safe_normalized_distance(distance_bob)
    alt_ratio, alt_log, alt_log_valid = _safe_normalized_distance(distance_a_alternative)

    realised_initial = raw_difference[0]
    requested_initial = np.array([0.0, epsilon_radians, 0.0, 0.0])
    expected_a = abs(epsilon_radians)
    expected_bob = 2.0 * float(PARAMETERS[l2]) * math.sin(abs(epsilon_radians) / 2.0)
    expected_b = expected_bob / CHARACTERISTIC_LENGTH_METRES
    geometric_bound = 2.0 * float(PARAMETERS[l1] + PARAMETERS[l2])
    distance_arrays = (distance_a, distance_a_alternative, distance_b, distance_bob)
    checks = {
        "both_integrations_accepted": reference["accepted"] and nearby["accepted"],
        "requested_initial_perturbation_realised": bool(
            np.allclose(
                realised_initial,
                requested_initial,
                rtol=0.0,
                atol=INITIAL_ABSOLUTE_TOLERANCE,
            )
        ),
        "wrapped_difference_is_deterministic": bool(
            np.array_equal(
                raw_difference,
                wrapped_el_difference(reference["state"], nearby["state"]),
            )
        ),
        "all_distances_finite": bool(all(np.all(np.isfinite(item)) for item in distance_arrays)),
        "all_distances_non_negative": bool(all(np.all(item >= 0.0) for item in distance_arrays)),
        "candidate_a_initial_value_matches": bool(
            math.isclose(distance_a[0], expected_a, rel_tol=0.0, abs_tol=INITIAL_ABSOLUTE_TOLERANCE)
        ),
        "candidate_b_initial_value_matches": bool(
            math.isclose(distance_b[0], expected_b, rel_tol=0.0, abs_tol=INITIAL_ABSOLUTE_TOLERANCE)
        ),
        "second_bob_initial_value_matches": bool(
            math.isclose(
                distance_bob[0], expected_bob, rel_tol=0.0, abs_tol=INITIAL_ABSOLUTE_TOLERANCE
            )
        ),
        "second_bob_respects_geometric_bound": bool(
            np.all(distance_bob <= geometric_bound + INITIAL_ABSOLUTE_TOLERANCE)
        ),
        "log_values_only_where_valid": bool(
            np.array_equal(a_log_valid, np.isfinite(a_log))
            and np.array_equal(b_log_valid, np.isfinite(b_log))
            and np.array_equal(bob_log_valid, np.isfinite(bob_log))
            and np.array_equal(alt_log_valid, np.isfinite(alt_log))
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    issues.extend(f"failed_check: {name}" for name in failed_checks)
    series = {
        "time": reference["time"],
        "reference_state": reference["state"],
        "nearby_state": nearby["state"],
        "wrapped_difference": raw_difference,
        "candidate_a": distance_a,
        "candidate_a_alternative_scaling": distance_a_alternative,
        "candidate_b": distance_b,
        "second_bob_metres": distance_bob,
        "candidate_a_ratio": a_ratio,
        "candidate_b_ratio": b_ratio,
        "second_bob_ratio": bob_ratio,
        "candidate_a_alternative_ratio": alt_ratio,
        "candidate_a_log_ratio": a_log,
        "candidate_b_log_ratio": b_log,
        "second_bob_log_ratio": bob_log,
        "candidate_a_alternative_log_ratio": alt_log,
        "candidate_a_log_valid": a_log_valid,
        "candidate_b_log_valid": b_log_valid,
        "second_bob_log_valid": bob_log_valid,
        "candidate_a_alternative_log_valid": alt_log_valid,
        "reference_energy_drift": reference["energy_drift"],
        "nearby_energy_drift": nearby["energy_drift"],
    }
    return {
        "run_id": run_id,
        "accepted": not issues,
        "issues": issues,
        "epsilon_radians": epsilon_radians,
        "policy": _policy_dict(policy),
        "sample_count": sample_count,
        "reference": reference,
        "nearby": nearby,
        "series": series,
        "checks": checks,
        "initial_values": {
            "candidate_a": float(distance_a[0]),
            "candidate_a_alternative_scaling": float(distance_a_alternative[0]),
            "candidate_b": float(distance_b[0]),
            "second_bob_metres": float(distance_bob[0]),
        },
    }


def _first_crossing_time(time: np.ndarray, values: np.ndarray, level: float) -> float | None:
    indices = np.flatnonzero(values >= level)
    return float(time[indices[0]]) if len(indices) else None


def _finite_max_abs_difference(left: np.ndarray, right: np.ndarray, mask: np.ndarray) -> float:
    valid = mask & np.isfinite(left) & np.isfinite(right)
    return float(np.max(np.abs(left[valid] - right[valid]))) if np.any(valid) else math.inf


def _prefix_mask_before_first_exceedance(*values: np.ndarray) -> np.ndarray:
    """Return one contiguous prefix ending before any distance exceeds the ceiling."""

    if not values:
        raise ValueError("At least one distance trace is required.")
    count = len(values[0])
    if any(len(value) != count for value in values):
        raise ValueError("Distance traces must share one output grid.")
    exceeds = np.zeros(count, dtype=bool)
    for value in values:
        exceeds |= np.asarray(value) > LOCAL_DISTANCE_CEILING
    first = np.flatnonzero(exceeds)
    stop = int(first[0]) if len(first) else count
    mask = np.zeros(count, dtype=bool)
    mask[:stop] = True
    return mask


def _run_summary(run: dict[str, Any]) -> dict[str, Any]:
    result = {
        "run_id": run["run_id"],
        "accepted": run["accepted"],
        "issues": run["issues"],
        "epsilon_radians": run["epsilon_radians"],
        "epsilon_degrees": math.degrees(run["epsilon_radians"]),
        "policy": run["policy"],
        "sample_count": run["sample_count"],
        "sample_interval_seconds": (T_STOP - T_START) / (run["sample_count"] - 1),
        "checks": run["checks"],
        "reference_solver_status": run["reference"].get("solver_metadata", {}),
        "nearby_solver_status": run["nearby"].get("solver_metadata", {}),
        "reference_max_normalized_energy_drift": run["reference"]["max_energy_drift"],
        "nearby_max_normalized_energy_drift": run["nearby"]["max_energy_drift"],
    }
    if run["series"] is None:
        return result
    series = run["series"]
    result.update(
        {
            "initial_values": run["initial_values"],
            "maximum_values": {
                "candidate_a": float(np.max(series["candidate_a"])),
                "candidate_b": float(np.max(series["candidate_b"])),
                "second_bob_metres": float(np.max(series["second_bob_metres"])),
            },
            "zero_or_invalid_log_counts": {
                "candidate_a": int(np.count_nonzero(~series["candidate_a_log_valid"])),
                "candidate_b": int(np.count_nonzero(~series["candidate_b_log_valid"])),
                "second_bob": int(np.count_nonzero(~series["second_bob_log_valid"])),
            },
            "normalized_ratio_crossing_times_seconds": {
                "candidate_a_10x": _first_crossing_time(
                    series["time"], series["candidate_a_ratio"], 10.0
                ),
                "candidate_a_100x": _first_crossing_time(
                    series["time"], series["candidate_a_ratio"], 100.0
                ),
                "candidate_b_10x": _first_crossing_time(
                    series["time"], series["candidate_b_ratio"], 10.0
                ),
                "candidate_b_100x": _first_crossing_time(
                    series["time"], series["candidate_b_ratio"], 100.0
                ),
            },
        }
    )
    return result


def run_investigation() -> dict[str, Any]:
    baseline = _derive_pair(
        "baseline_eps_1e-5",
        BASELINE_EPSILON_RADIANS,
        SIMPLE_REFERENCE_SOLVER_POLICY,
        BASELINE_SAMPLE_COUNT,
    )
    epsilon_large = _derive_pair(
        "perturbation_eps_1e-4",
        1.0e-4,
        SIMPLE_REFERENCE_SOLVER_POLICY,
        BASELINE_SAMPLE_COUNT,
    )
    epsilon_small = _derive_pair(
        "perturbation_eps_1e-6",
        1.0e-6,
        SIMPLE_REFERENCE_SOLVER_POLICY,
        BASELINE_SAMPLE_COUNT,
    )
    stricter = _derive_pair(
        "stricter_tolerance_eps_1e-5",
        BASELINE_EPSILON_RADIANS,
        STRICTER_SOLVER_POLICY,
        BASELINE_SAMPLE_COUNT,
    )
    dense = _derive_pair(
        "dense_sampling_eps_1e-5",
        BASELINE_EPSILON_RADIANS,
        SIMPLE_REFERENCE_SOLVER_POLICY,
        DENSE_SAMPLE_COUNT,
    )
    runs = [baseline, epsilon_large, epsilon_small, stricter, dense]
    if not all(run["accepted"] and run["series"] is not None for run in runs):
        summary = {
            "experiment": EXPERIMENT_NAME,
            "status": "rejected",
            "accepted": False,
            "failure_reason": "one_or_more_runs_failed_numerical_or_distance_checks",
            "runs": [_run_summary(run) for run in runs],
        }
        return {"summary": summary, "runs": runs}

    base = baseline["series"]
    large = epsilon_large["series"]
    small = epsilon_small["series"]
    strict = stricter["series"]
    dense_at_baseline_times = {key: value[::2] for key, value in dense["series"].items()}

    sampling_differences = {
        name: float(np.max(np.abs(base[name] - dense_at_baseline_times[name])))
        for name in ("candidate_a", "candidate_b", "second_bob_metres")
    }
    sampling_maximum = max(sampling_differences.values())

    common_local_mask = (
        _prefix_mask_before_first_exceedance(
            base["candidate_a"], large["candidate_a"], small["candidate_a"]
        )
        & base["candidate_a_log_valid"]
        & large["candidate_a_log_valid"]
        & small["candidate_a_log_valid"]
    )
    magnitude_log_spread = np.max(
        np.stack(
            (
                base["candidate_a_log_ratio"],
                large["candidate_a_log_ratio"],
                small["candidate_a_log_ratio"],
            )
        ),
        axis=0,
    ) - np.min(
        np.stack(
            (
                base["candidate_a_log_ratio"],
                large["candidate_a_log_ratio"],
                small["candidate_a_log_ratio"],
            )
        ),
        axis=0,
    )
    maximum_magnitude_log_spread = float(np.max(magnitude_log_spread[common_local_mask]))

    baseline_local_mask = (
        _prefix_mask_before_first_exceedance(base["candidate_a"])
        & base["candidate_a_log_valid"]
        & base["candidate_b_log_valid"]
    )
    tolerance_log_difference = _finite_max_abs_difference(
        base["candidate_a_log_ratio"],
        strict["candidate_a_log_ratio"],
        baseline_local_mask & strict["candidate_a_log_valid"],
    )
    scaling_log_difference = _finite_max_abs_difference(
        base["candidate_a_log_ratio"],
        base["candidate_a_alternative_log_ratio"],
        baseline_local_mask & base["candidate_a_alternative_log_valid"],
    )
    candidate_log_difference = _finite_max_abs_difference(
        base["candidate_a_log_ratio"],
        base["candidate_b_log_ratio"],
        baseline_local_mask,
    )
    candidate_log_correlation = float(
        np.corrcoef(
            base["candidate_a_log_ratio"][baseline_local_mask],
            base["candidate_b_log_ratio"][baseline_local_mask],
        )[0, 1]
    )
    local_end_time = float(base["time"][np.flatnonzero(baseline_local_mask)[-1]])
    common_local_end_time = float(base["time"][np.flatnonzero(common_local_mask)[-1]])
    geometric_bound = 2.0 * float(PARAMETERS[l1] + PARAMETERS[l2])
    saturation_time = _first_crossing_time(
        base["time"], base["second_bob_metres"], 0.9 * geometric_bound
    )
    velocity_scaled = base["wrapped_difference"][:, 2:] * characteristic_time(
        CHARACTERISTIC_LENGTH_METRES
    )
    velocity_contribution = np.linalg.norm(velocity_scaled, axis=1)

    comparisons = {
        "sampling": {
            "maximum_absolute_distance_differences": sampling_differences,
            "maximum_over_candidates": sampling_maximum,
            "limit": SAMPLING_MAX_ABSOLUTE_DISTANCE_DIFFERENCE,
            "accepted": sampling_maximum <= SAMPLING_MAX_ABSOLUTE_DISTANCE_DIFFERENCE,
        },
        "perturbation_magnitude": {
            "magnitudes_radians": list(PERTURBATION_MAGNITUDES_RADIANS),
            "common_local_interval_end_seconds": common_local_end_time,
            "maximum_candidate_a_log_ratio_spread": maximum_magnitude_log_spread,
            "provisional_agreement_limit": LOG_TRACE_AGREEMENT_LIMIT,
            "accepted": maximum_magnitude_log_spread <= LOG_TRACE_AGREEMENT_LIMIT,
        },
        "solver_tolerance": {
            "local_interval_end_seconds": local_end_time,
            "maximum_candidate_a_log_ratio_difference": tolerance_log_difference,
            "provisional_agreement_limit": LOG_TRACE_AGREEMENT_LIMIT,
            "accepted": tolerance_log_difference <= LOG_TRACE_AGREEMENT_LIMIT,
        },
        "characteristic_scaling": {
            "baseline_length_metres": CHARACTERISTIC_LENGTH_METRES,
            "alternative_length_metres": ALTERNATIVE_LENGTH_METRES,
            "maximum_candidate_a_log_ratio_difference": scaling_log_difference,
            "accepted_as_robustness_observation": math.isfinite(scaling_log_difference),
        },
        "candidate_a_vs_b": {
            "local_interval_end_seconds": local_end_time,
            "log_ratio_correlation": candidate_log_correlation,
            "maximum_log_ratio_difference": candidate_log_difference,
            "provisional_correlation_threshold": 0.8,
            "qualitatively_compatible": candidate_log_correlation >= 0.8,
        },
    }
    acceptance_checks = {
        "angular_topology_checks_pass": _topology_self_checks(),
        "all_runs_numerically_accepted": all(run["accepted"] for run in runs),
        "at_least_two_dimensionally_coherent_full_state_norms": True,
        "sampling_comparison_passes": comparisons["sampling"]["accepted"],
        "tolerance_comparison_passes": comparisons["solver_tolerance"]["accepted"],
        "perturbation_comparison_supports_local_regime": comparisons[
            "perturbation_magnitude"
        ]["accepted"],
        "full_state_candidates_qualitatively_compatible": comparisons[
            "candidate_a_vs_b"
        ]["qualitatively_compatible"],
        "display_distance_distinction_exposed": bool(
            np.max(base["second_bob_metres"]) > 0.5 * geometric_bound
            and np.max(base["candidate_a"]) > LOCAL_DISTANCE_CEILING
        ),
    }
    accepted = all(acceptance_checks.values())
    baseline_summary = _run_summary(baseline)
    baseline_summary["local_interval_end_seconds_by_distance_ceiling"] = local_end_time
    baseline_summary["second_bob_geometric_bound_metres"] = geometric_bound
    baseline_summary["second_bob_90_percent_bound_time_seconds"] = saturation_time
    local_indices = np.flatnonzero(baseline_local_mask)
    baseline_summary["maximum_scaled_velocity_component_norm"] = float(
        np.max(velocity_contribution)
    )
    baseline_summary["local_maximum_scaled_velocity_component_norm"] = float(
        np.max(velocity_contribution[baseline_local_mask])
    )
    baseline_summary["local_end_component_norms"] = {
        "wrapped_angles": float(
            np.linalg.norm(base["wrapped_difference"][local_indices[-1], :2])
        ),
        "scaled_angular_velocities": float(velocity_contribution[local_indices[-1]]),
    }
    baseline_summary["wrapped_angle_step_maxima_radians"] = [
        float(value)
        for value in np.max(np.abs(np.diff(base["wrapped_difference"][:, :2], axis=0)), axis=0)
    ]
    baseline_summary["local_wrapped_angle_step_maxima_radians"] = [
        float(value)
        for value in np.max(
            np.abs(np.diff(base["wrapped_difference"][local_indices, :2], axis=0)), axis=0
        )
    ]
    summary = {
        "experiment": EXPERIMENT_NAME,
        "status": "accepted_for_distance_convention_findings" if accepted else "rejected",
        "accepted": accepted,
        "failure_reason": None if accepted else "one_or_more_acceptance_checks_failed",
        "question": (
            "How do explicit dimensionally coherent EL and Cartesian full-state distances "
            "compare for one controlled nearby Euler-Lagrange trajectory pair?"
        ),
        "configuration": {
            "model": MODEL,
            "formulation": FORMULATION,
            "state_order": ["theta1", "theta2", "omega1", "omega2"],
            "parameters_si": {str(key): float(value) for key, value in PARAMETERS.items()},
            "base_initial_state_degrees": BASE_INITIAL_STATE_DEGREES.tolist(),
            "base_initial_state_radians": BASE_INITIAL_STATE_RADIANS.tolist(),
            "perturbation_vector_radians": [0.0, BASELINE_EPSILON_RADIANS, 0.0, 0.0],
            "perturbation_direction_status": "controlled manual reference; not privileged",
            "t_start_seconds": T_START,
            "t_stop_seconds": T_STOP,
            "sample_count": BASELINE_SAMPLE_COUNT,
            "sample_interval_seconds": (T_STOP - T_START) / (BASELINE_SAMPLE_COUNT - 1),
            "solver_policy": _policy_dict(SIMPLE_REFERENCE_SOLVER_POLICY),
            "maximum_normalized_energy_drift": MAX_NORMALIZED_ENERGY_DRIFT,
            "energy_scale_joules": _energy_scale(),
            "characteristic_length_metres": CHARACTERISTIC_LENGTH_METRES,
            "characteristic_time_seconds": characteristic_time(
                CHARACTERISTIC_LENGTH_METRES
            ),
        },
        "distance_definitions": {
            "angular_difference": "wrap_(−pi,pi](theta_nearby - theta_reference)",
            "velocity_difference": "omega_nearby - omega_reference",
            "candidate_a": "||(delta_theta1, delta_theta2, Tc*delta_omega1, Tc*delta_omega2)||_2",
            "candidate_b": "||(delta_r/Lc, Tc*delta_v/Lc)||_2 for both bobs",
            "second_bob": "||r2_nearby-r2_reference||_2 in metres; comparison observable only",
            "raw_mixed_units_norm": "rejected a priori and not implemented",
        },
        "baseline": baseline_summary,
        "comparisons": comparisons,
        "acceptance_checks": acceptance_checks,
        "runs": [_run_summary(run) for run in runs],
        "claim_boundary": (
            "No slope, exponent, renormalisation, tangent dynamics, Hamiltonian comparison, "
            "or chaos classification is computed or supported."
        ),
    }
    return {"summary": summary, "runs": runs}


def _topology_self_checks() -> bool:
    across_boundary = wrapped_el_difference(
        np.array([math.pi - 1.0e-9, -math.pi + 1.0e-9, 0.0, 0.0]),
        np.array([-math.pi + 1.0e-9, math.pi - 1.0e-9, 0.0, 0.0]),
    )
    physically_identical = wrapped_el_difference(
        np.deg2rad(np.array([179.0, -179.0, 0.0, 0.0])),
        np.deg2rad(np.array([-181.0, 181.0, 0.0, 0.0])),
    )
    endpoint = wrap_angle_difference(np.array([-math.pi, math.pi]))
    return bool(
        np.allclose(across_boundary[:2], [2.0e-9, -2.0e-9], atol=1.0e-12)
        and np.allclose(physically_identical, 0.0, atol=1.0e-14)
        and np.array_equal(endpoint, np.array([math.pi, math.pi]))
    )


CSV_FIELDS = (
    "run_id",
    "time_s",
    "reference_theta1_rad",
    "reference_theta2_rad",
    "reference_omega1_rad_per_s",
    "reference_omega2_rad_per_s",
    "nearby_theta1_rad",
    "nearby_theta2_rad",
    "nearby_omega1_rad_per_s",
    "nearby_omega2_rad_per_s",
    "delta_theta1_wrapped_rad",
    "delta_theta2_wrapped_rad",
    "delta_omega1_rad_per_s",
    "delta_omega2_rad_per_s",
    "candidate_a_dimensionless",
    "candidate_b_dimensionless",
    "second_bob_distance_m",
    "candidate_a_normalized",
    "candidate_b_normalized",
    "second_bob_normalized",
    "candidate_a_log_normalized",
    "candidate_b_log_normalized",
    "second_bob_log_normalized",
    "candidate_a_log_valid",
    "candidate_b_log_valid",
    "second_bob_log_valid",
    "candidate_a_alternative_scaling_dimensionless",
    "candidate_a_alternative_scaling_normalized",
    "candidate_a_alternative_scaling_log_normalized",
    "reference_normalized_energy_drift",
    "nearby_normalized_energy_drift",
)


def _csv_number(value: float) -> float | str:
    return float(value) if np.isfinite(value) else ""


def _write_csv(path: Path, runs: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for run in runs:
            series = run["series"]
            if series is None:
                continue
            for index, time_value in enumerate(series["time"]):
                reference = series["reference_state"][index]
                nearby = series["nearby_state"][index]
                delta = series["wrapped_difference"][index]
                writer.writerow(
                    {
                        "run_id": run["run_id"],
                        "time_s": float(time_value),
                        "reference_theta1_rad": float(reference[0]),
                        "reference_theta2_rad": float(reference[1]),
                        "reference_omega1_rad_per_s": float(reference[2]),
                        "reference_omega2_rad_per_s": float(reference[3]),
                        "nearby_theta1_rad": float(nearby[0]),
                        "nearby_theta2_rad": float(nearby[1]),
                        "nearby_omega1_rad_per_s": float(nearby[2]),
                        "nearby_omega2_rad_per_s": float(nearby[3]),
                        "delta_theta1_wrapped_rad": float(delta[0]),
                        "delta_theta2_wrapped_rad": float(delta[1]),
                        "delta_omega1_rad_per_s": float(delta[2]),
                        "delta_omega2_rad_per_s": float(delta[3]),
                        "candidate_a_dimensionless": float(series["candidate_a"][index]),
                        "candidate_b_dimensionless": float(series["candidate_b"][index]),
                        "second_bob_distance_m": float(series["second_bob_metres"][index]),
                        "candidate_a_normalized": _csv_number(series["candidate_a_ratio"][index]),
                        "candidate_b_normalized": _csv_number(series["candidate_b_ratio"][index]),
                        "second_bob_normalized": _csv_number(series["second_bob_ratio"][index]),
                        "candidate_a_log_normalized": _csv_number(
                            series["candidate_a_log_ratio"][index]
                        ),
                        "candidate_b_log_normalized": _csv_number(
                            series["candidate_b_log_ratio"][index]
                        ),
                        "second_bob_log_normalized": _csv_number(
                            series["second_bob_log_ratio"][index]
                        ),
                        "candidate_a_log_valid": bool(series["candidate_a_log_valid"][index]),
                        "candidate_b_log_valid": bool(series["candidate_b_log_valid"][index]),
                        "second_bob_log_valid": bool(series["second_bob_log_valid"][index]),
                        "candidate_a_alternative_scaling_dimensionless": float(
                            series["candidate_a_alternative_scaling"][index]
                        ),
                        "candidate_a_alternative_scaling_normalized": _csv_number(
                            series["candidate_a_alternative_ratio"][index]
                        ),
                        "candidate_a_alternative_scaling_log_normalized": _csv_number(
                            series["candidate_a_alternative_log_ratio"][index]
                        ),
                        "reference_normalized_energy_drift": float(
                            series["reference_energy_drift"][index]
                        ),
                        "nearby_normalized_energy_drift": float(
                            series["nearby_energy_drift"][index]
                        ),
                    }
                )


def _load_pyplot():
    import matplotlib.pyplot as plt

    return plt


def _save_figure(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    _load_pyplot().close(fig)


def _write_plots(output_dir: Path, investigation: dict[str, Any]) -> list[Path]:
    plt = _load_pyplot()
    runs = {run["run_id"]: run for run in investigation["runs"]}
    baseline = runs["baseline_eps_1e-5"]
    series = baseline["series"]
    if series is None:
        return []
    time = series["time"]
    paths: list[Path] = []

    path = output_dir / "01_component_perturbations.png"
    fig, axes = plt.subplots(2, 1, figsize=(10, 9), sharex=False)
    labels = (r"$\Delta\theta_1$", r"$\Delta\theta_2$", r"$T_c\Delta\omega_1$", r"$T_c\Delta\omega_2$")
    components = np.array(series["wrapped_difference"], copy=True)
    components[:, 2:] *= characteristic_time(CHARACTERISTIC_LENGTH_METRES)
    for index, label in enumerate(labels):
        axes[0].plot(time, components[:, index], label=label, linewidth=1.0)
        axes[1].plot(time, components[:, index], label=label, linewidth=1.0)
    local_end = investigation["summary"]["comparisons"]["candidate_a_vs_b"][
        "local_interval_end_seconds"
    ]
    local_values = components[time <= local_end]
    local_minimum = float(np.min(local_values))
    local_maximum = float(np.max(local_values))
    local_padding = max(0.05 * (local_maximum - local_minimum), 1.0e-6)
    axes[0].set(
        title="Full 20 s trace: branch-cut jumps appear after local separation",
        xlabel="time / s",
        ylabel="dimensionless component",
    )
    axes[1].set(
        title="Contiguous local-distance interval",
        xlabel="time / s",
        ylabel="dimensionless component",
        xlim=(T_START, local_end),
        ylim=(local_minimum - local_padding, local_maximum + local_padding),
    )
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend(ncol=2)
    fig.suptitle("Wrapped and scaled EL perturbation components")
    _save_figure(fig, path)
    paths.append(path)

    path = output_dir / "02_candidate_distance_comparison.png"
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(time, series["candidate_a"], label="A: scaled EL full state")
    axes[0].plot(time, series["candidate_b"], label="B: scaled Cartesian full state")
    axes[0].set(ylabel="dimensionless distance", title="Dimensionally coherent full-state candidates")
    axes[0].legend()
    axes[1].plot(time, series["second_bob_metres"], color="tab:green", label="second bob")
    axes[1].set(xlabel="time / s", ylabel="distance / m", title="Dimensional display observable (separate axis)")
    axes[1].legend()
    for axis in axes:
        axis.grid(True, alpha=0.25)
    _save_figure(fig, path)
    paths.append(path)

    path = output_dir / "03_normalized_separation.png"
    fig, axis = plt.subplots(figsize=(10, 6))
    axis.plot(time, series["candidate_a_ratio"], label="A: scaled EL")
    axis.plot(time, series["candidate_b_ratio"], label="B: scaled Cartesian")
    axis.set(title="Normalized full-state separation (diagnostic only)", xlabel="time / s", ylabel=r"$d(t)/d(0)$")
    axis.grid(True, alpha=0.25)
    axis.legend()
    _save_figure(fig, path)
    paths.append(path)

    path = output_dir / "04_log_normalized_separation.png"
    fig, axis = plt.subplots(figsize=(10, 6))
    axis.plot(time, series["candidate_a_log_ratio"], label="A: scaled EL")
    axis.plot(time, series["candidate_b_log_ratio"], label="B: scaled Cartesian")
    axis.axvline(
        investigation["summary"]["comparisons"]["candidate_a_vs_b"]["local_interval_end_seconds"],
        color="black",
        linestyle=":",
        label="declared local-distance ceiling",
    )
    axis.set(title="Log normalized separation — no slope fitted", xlabel="time / s", ylabel=r"$\log(d(t)/d(0))$")
    axis.grid(True, alpha=0.25)
    axis.legend()
    _save_figure(fig, path)
    paths.append(path)

    path = output_dir / "05_second_bob_saturation.png"
    fig, axis = plt.subplots(figsize=(10, 6))
    bound = 2.0 * float(PARAMETERS[l1] + PARAMETERS[l2])
    axis.plot(time, series["second_bob_metres"], label="second-bob display distance")
    axis.axhline(bound, color="black", linestyle="--", label=f"geometric maximum = {bound:g} m")
    axis.axhline(0.9 * bound, color="gray", linestyle=":", label="90% of maximum")
    axis.set(title="Bounded display distance and saturation", xlabel="time / s", ylabel="distance / m", ylim=(0.0, 1.05 * bound))
    axis.grid(True, alpha=0.25)
    axis.legend()
    _save_figure(fig, path)
    paths.append(path)

    path = output_dir / "06_energy_validity.png"
    fig, axis = plt.subplots(figsize=(10, 6))
    axis.plot(time, series["reference_energy_drift"], label="reference")
    axis.plot(time, series["nearby_energy_drift"], label="nearby")
    axis.axhline(MAX_NORMALIZED_ENERGY_DRIFT, color="black", linestyle=":", label="acceptance limit")
    axis.set(title="Independent energy validity", xlabel="time / s", ylabel=r"$|E(t)-E(0)|/E_{scale}$")
    axis.grid(True, alpha=0.25)
    axis.legend()
    _save_figure(fig, path)
    paths.append(path)

    path = output_dir / "07_controlled_comparisons.png"
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharex=True)
    for run_id in ("perturbation_eps_1e-4", "baseline_eps_1e-5", "perturbation_eps_1e-6"):
        run = runs[run_id]
        axes[0, 0].plot(run["series"]["time"], run["series"]["candidate_a_log_ratio"], label=f"epsilon={run['epsilon_radians']:.0e} rad")
    axes[0, 0].set(title="Perturbation magnitude", ylabel="log normalized A")
    axes[0, 0].legend(fontsize=8)
    strict = runs["stricter_tolerance_eps_1e-5"]["series"]
    axes[0, 1].plot(time, series["candidate_a_log_ratio"], label="rtol 1e-9 / atol 1e-11")
    axes[0, 1].plot(time, strict["candidate_a_log_ratio"], linestyle="--", label="rtol 1e-11 / atol 1e-13")
    axes[0, 1].set(title="Solver tolerance")
    axes[0, 1].legend(fontsize=8)
    dense = runs["dense_sampling_eps_1e-5"]["series"]
    axes[1, 0].plot(time, series["candidate_a"], label="100 Hz")
    axes[1, 0].plot(dense["time"], dense["candidate_a"], linestyle="--", label="200 Hz")
    axes[1, 0].set(title="Output sampling", xlabel="time / s", ylabel="candidate A")
    axes[1, 0].legend(fontsize=8)
    axes[1, 1].plot(time, series["candidate_a_log_ratio"], label="Lc=1 m")
    axes[1, 1].plot(time, series["candidate_a_alternative_log_ratio"], linestyle="--", label="Lc=2 m")
    axes[1, 1].set(title="Candidate A scaling sensitivity", xlabel="time / s")
    axes[1, 1].legend(fontsize=8)
    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    fig.suptitle("Controlled comparisons — no fitted growth rate")
    _save_figure(fig, path)
    paths.append(path)
    return paths


def _json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_output_bundle(
    investigation: dict[str, Any], output_dir: Path, include_plots: bool
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    _json_write(summary_path, investigation["summary"])
    csv_path = output_dir / "distance_timeseries.csv"
    _write_csv(csv_path, investigation["runs"])
    plot_paths = _write_plots(output_dir, investigation) if include_plots else []
    manifest_path = output_dir / "manifest.json"
    created_names = [manifest_path.name, summary_path.name, csv_path.name] + [
        path.name for path in plot_paths
    ]
    _json_write(
        manifest_path,
        {
            "artifact": EXPERIMENT_NAME,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": investigation["summary"]["status"],
            "accepted": investigation["summary"]["accepted"],
            "created_files": created_names,
            "reproduction_command": (
                "uv run python development/chaos_content/experiments/"
                "003_lyapunov_distance_contract/lyapunov_distance_investigation.py "
                "--output-dir development/chaos_content/outputs/"
                "lyapunov_distance_contract/baseline --plots"
            ),
            "contract": (
                "development/chaos_content/experiments/"
                "003_lyapunov_distance_contract/README.md"
            ),
            "notes": [
                "Exploratory sandbox evidence; not a production asset.",
                "No slope, exponent, renormalisation, or chaos classification is computed.",
                "Blank log CSV cells mean the corresponding positive-distance precondition failed; values are not clipped.",
            ],
        },
    )
    return [manifest_path, summary_path, csv_path, *plot_paths]


def _assert_self_check(investigation: dict[str, Any]) -> None:
    summary = investigation["summary"]
    if summary["experiment"] != EXPERIMENT_NAME:
        raise AssertionError("Unexpected experiment identity.")
    if not _topology_self_checks():
        raise AssertionError("Angular topology self-check failed.")
    if any(run["series"] is None for run in investigation["runs"]):
        raise AssertionError("A controlled run did not produce diagnostic series.")
    failed = [name for name, passed in summary["acceptance_checks"].items() if not passed]
    if failed:
        raise AssertionError(f"Distance investigation acceptance checks failed: {failed}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args()
    if args.plots and args.output_dir is None:
        parser.error("--plots requires --output-dir")

    investigation = run_investigation()
    if args.self_check:
        _assert_self_check(investigation)
        print("self-check: passed")
    if args.output_dir is not None:
        created = write_output_bundle(investigation, args.output_dir, args.plots)
        for path in created:
            print(path)
    if args.output_dir is None and not args.self_check:
        print(json.dumps(investigation["summary"], indent=2, sort_keys=True, allow_nan=False))
    return 0 if investigation["summary"].get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
