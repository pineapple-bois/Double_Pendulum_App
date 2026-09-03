"""Investigate repeated local perturbation renormalisation without an exponent claim.

The adjacent README fixes the reset map, staged duration policy, convergence
diagnostics, and acceptance boundary before numerical interpretation. Helpers
remain local to Experiment 005.
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
from scipy.integrate import solve_ivp

from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_REFERENCE_SOLVER_POLICY,
    DoublePendulumLagrangian,
    SolverPolicy,
)


EXPERIMENT_NAME = "renormalised_local_stretching"
MODEL = "simple"
FORMULATION = "Euler-Lagrange"
PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
BASE_STATE_DEGREES = np.array([179.0, 179.0, 0.0, 0.0])
BASE_STATE_RADIANS = np.deg2rad(BASE_STATE_DEGREES)

LC_BASELINE = 1.0
LC_ALTERNATIVE = 2.0
BASELINE_EPSILON = 1.0e-5
EPSILONS = (1.0e-4, 1.0e-5, 1.0e-6)
BASELINE_RESET_INTERVAL = 0.25
RESET_INTERVALS = (0.125, 0.25, 0.5)
DURATION_STAGES = (20.0, 40.0, 80.0)
INITIAL_TRANSIENT_SECONDS = 2.0

REFERENCE_SAMPLE_INTERVAL = 0.01
SEGMENT_SAMPLE_COUNT = 11
LOCAL_DISTANCE_CEILING = 1.0e-2
ENERGY_DRIFT_LIMIT = 1.0e-7
RESET_RELATIVE_TOLERANCE = 1.0e-8
DIRECTION_ABSOLUTE_TOLERANCE = 1.0e-8
RECONSTRUCTION_ABSOLUTE_TOLERANCE = 1.0e-12

# Repaired numerical policy declared before the second Experiment 005 run.
# This resolves each characteristic time with at least 32 permitted steps and
# each baseline reset interval with at least 25 permitted steps.
BASELINE_MAX_STEP = min(
    math.sqrt(LC_BASELINE / float(PARAMETERS[g])) / 32.0,
    BASELINE_RESET_INTERVAL / 25.0,
)
REFINED_MAX_STEP = BASELINE_MAX_STEP / 2.0
MAX_MAX_STEP_RATE_DIFFERENCE = 0.01
MATERIAL_POLICY_LOG_DIFFERENCE = 0.1
MATERIAL_POLICY_DIRECTION_DIFFERENCE = 0.1

# Provisional convergence thresholds fixed in README before execution.
MAX_DURATION_CHANGE_20_TO_40 = 0.10
MAX_DURATION_CHANGE_40_TO_80 = 0.05
MAX_FINAL_QUARTER_CUMULATIVE_SPREAD = 0.05
MAX_LATE_QUARTER_RATE_DIFFERENCE = 0.10
MAX_INITIAL_TRANSIENT_RATE_DIFFERENCE = 0.05
MAX_RESET_MAGNITUDE_RATE_SPREAD = 0.05
MAX_RESET_INTERVAL_RATE_SPREAD = 0.10
MAX_TOLERANCE_RATE_DIFFERENCE = 0.01
MAX_SCALING_RATE_DIFFERENCE = 0.05

STRICTER_POLICY = SolverPolicy(
    name="renormalised_stretching_stricter_check",
    method="DOP853",
    rtol=1.0e-11,
    atol=1.0e-13,
    role="experiment-local numerical robustness comparison",
)


def characteristic_time(length_metres: float = LC_BASELINE) -> float:
    return math.sqrt(float(length_metres) / float(PARAMETERS[g]))


def wrap_angle_difference(values: np.ndarray) -> np.ndarray:
    """Map angular differences deterministically to (-pi, pi]."""

    values = np.asarray(values, dtype=float)
    wrapped = np.remainder(values + math.pi, 2.0 * math.pi) - math.pi
    return np.where(wrapped == -math.pi, math.pi, wrapped)


def canonicalize_state_angles(state: np.ndarray) -> np.ndarray:
    """Return an equivalent EL state with angles in the principal interval.

    The deterministic convention is ``(-pi, pi]``. Angular velocities are not
    modified. This is a coordinate rebase, not a physical trajectory reset.
    """

    canonical = np.array(state, dtype=float, copy=True)
    if canonical.shape[-1] != 4:
        raise ValueError("EL states must have four components.")
    canonical[..., :2] = wrap_angle_difference(canonical[..., :2])
    return canonical


def accumulate_lifted_angles(
    sampled_angles: np.ndarray, initial_lifted_angles: np.ndarray | None = None
) -> np.ndarray:
    """Reconstruct continuous winding history outside the ODE solver state.

    Consecutive samples must resolve motion to less than one half-turn. The
    experiment's 0.01 s diagnostic sampling and explicit step cap provide that
    resolution for the recorded run.
    """

    angles = np.asarray(sampled_angles, dtype=float)
    if angles.ndim != 2 or angles.shape[1] != 2 or len(angles) == 0:
        raise ValueError("Sampled angles must have shape (n, 2).")
    if np.any(~np.isfinite(angles)):
        raise ValueError("Sampled angles must be finite.")
    increments = wrap_angle_difference(np.diff(angles, axis=0))
    lifted = np.empty_like(angles)
    if initial_lifted_angles is None:
        lifted[0] = angles[0]
    else:
        initial = np.asarray(initial_lifted_angles, dtype=float)
        if initial.shape != (2,) or np.any(~np.isfinite(initial)):
            raise ValueError("Initial lifted angles must be a finite two-vector.")
        if np.max(np.abs(wrap_angle_difference(angles[0] - initial))) > 1.0e-10:
            raise ValueError("Initial lifted history is not equivalent to the first sample.")
        lifted[0] = initial
    if len(angles) > 1:
        lifted[1:] = lifted[0] + np.cumsum(increments, axis=0)
    return lifted


def wrapped_el_difference(reference: np.ndarray, nearby: np.ndarray) -> np.ndarray:
    difference = np.asarray(nearby, dtype=float) - np.asarray(reference, dtype=float)
    result = np.array(difference, copy=True)
    result[..., :2] = wrap_angle_difference(difference[..., :2])
    return result


def scaled_el_vector(
    physical_difference: np.ndarray, length_metres: float = LC_BASELINE
) -> np.ndarray:
    scaled = np.array(physical_difference, dtype=float, copy=True)
    scaled[..., 2:] *= characteristic_time(length_metres)
    return scaled


def physical_el_vector(
    scaled_difference: np.ndarray, length_metres: float = LC_BASELINE
) -> np.ndarray:
    physical = np.array(scaled_difference, dtype=float, copy=True)
    physical[..., 2:] /= characteristic_time(length_metres)
    return physical


def candidate_a_distance(
    physical_difference: np.ndarray, length_metres: float = LC_BASELINE
) -> np.ndarray:
    return np.linalg.norm(scaled_el_vector(physical_difference, length_metres), axis=-1)


def normalized_reset(
    physical_difference: np.ndarray,
    target_magnitude: float,
    length_metres: float = LC_BASELINE,
) -> tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    """Return scaled input, its norm, evolved direction, and physical reset vector."""

    scaled = scaled_el_vector(physical_difference, length_metres)
    magnitude = float(np.linalg.norm(scaled))
    if not np.isfinite(magnitude) or magnitude <= 0.0:
        raise ValueError("Cannot renormalise a non-positive or non-finite perturbation.")
    if not np.isfinite(target_magnitude) or target_magnitude <= 0.0:
        raise ValueError("Reset target must be positive and finite.")
    direction = scaled / magnitude
    reset_physical = physical_el_vector(target_magnitude * direction, length_metres)
    return scaled, magnitude, direction, reset_physical


def reconstruct_shadow_state(
    reference_state: np.ndarray,
    direction: np.ndarray,
    target_magnitude: float,
    length_metres: float = LC_BASELINE,
) -> np.ndarray:
    """Reconstruct the shadow around the current reference in scaled EL direction."""

    direction = np.asarray(direction, dtype=float)
    norm = float(np.linalg.norm(direction))
    if not np.isfinite(norm) or not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError("Reset direction must be a finite unit vector.")
    physical = physical_el_vector(target_magnitude * direction, length_metres)
    local_reference = canonicalize_state_angles(reference_state)
    return canonicalize_state_angles(local_reference + physical)


def growth_contribution(pre_reset_magnitude: float, previous_reset_magnitude: float) -> tuple[float, float]:
    if (
        not np.isfinite(pre_reset_magnitude)
        or not np.isfinite(previous_reset_magnitude)
        or pre_reset_magnitude <= 0.0
        or previous_reset_magnitude <= 0.0
    ):
        raise ValueError("Growth magnitudes must be positive and finite.")
    growth = float(pre_reset_magnitude / previous_reset_magnitude)
    return growth, float(math.log(growth))


def cumulative_rates(log_stretching: np.ndarray, end_times: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    logs = np.asarray(log_stretching, dtype=float)
    times = np.asarray(end_times, dtype=float)
    if logs.shape != times.shape or logs.ndim != 1:
        raise ValueError("Cycle logs and end times must be equal one-dimensional arrays.")
    if np.any(~np.isfinite(logs)) or np.any(~np.isfinite(times)) or np.any(times <= 0.0):
        raise ValueError("Cycle logs and positive end times must be finite.")
    cumulative = np.cumsum(logs)
    return cumulative, cumulative / times


def deterministic_cycle_times(duration: float, reset_interval: float) -> np.ndarray:
    cycle_count = int(round(duration / reset_interval))
    if cycle_count <= 0 or not math.isclose(
        cycle_count * reset_interval, duration, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError("Duration must be a positive integer multiple of reset interval.")
    return np.round(np.arange(cycle_count + 1, dtype=float) * reset_interval, 12)


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
    state = np.atleast_2d(np.asarray(state, dtype=float))
    theta1, theta2, omega1, omega2 = state.T
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


def normalized_segment_energy_drift(state: np.ndarray) -> np.ndarray:
    """Measure a physical segment from its own post-reset initial energy."""

    energy = simple_energy(state)
    return np.abs(energy - energy[0]) / energy_scale()


def policy_dict(policy: SolverPolicy) -> dict[str, Any]:
    return {
        "name": policy.name,
        "method": policy.method,
        "rtol": policy.rtol,
        "atol": policy.atol,
        "role": policy.role,
    }


def build_dynamics() -> DoublePendulumLagrangian:
    """Build the actual EL model once; direct segment solves reuse its RHS."""

    return DoublePendulumLagrangian(
        PARAMETERS,
        BASE_STATE_DEGREES,
        [0.0, 1.0e-6, 2],
        model=MODEL,
        solver_policy=SIMPLE_REFERENCE_SOLVER_POLICY,
    )


def solve_segment(
    dynamics: DoublePendulumLagrangian,
    initial_state: np.ndarray,
    requested_time: np.ndarray,
    policy: SolverPolicy,
    *,
    max_step: float,
) -> dict[str, Any]:
    requested_time = np.asarray(requested_time, dtype=float)
    if not np.isfinite(max_step) or max_step <= 0.0:
        raise ValueError("max_step must be positive and finite.")
    result = solve_ivp(
        lambda time_value, state: dynamics._system(state, time_value),
        (float(requested_time[0]), float(requested_time[-1])),
        np.asarray(initial_state, dtype=float),
        t_eval=requested_time,
        max_step=max_step,
        **policy.solve_ivp_kwargs(),
    )
    state = np.asarray(result.y.T, dtype=float)
    checks = {
        "solver_success": bool(result.success),
        "complete_requested_output": bool(
            result.t.shape == requested_time.shape
            and np.allclose(result.t, requested_time, rtol=0.0, atol=1.0e-13)
        ),
        "expected_state_shape": state.shape == (len(requested_time), 4),
        "finite_state": bool(np.all(np.isfinite(state))),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "issues": [name for name, passed in checks.items() if not passed],
        "time": np.asarray(result.t, dtype=float),
        "state": state,
        "solver_status": {
            "success": bool(result.success),
            "status": int(result.status),
            "message": str(result.message),
            "nfev": int(result.nfev),
            "njev": int(result.njev),
            "nlu": int(result.nlu),
            "requested_count": len(requested_time),
            "returned_count": len(result.t),
            "max_step_seconds": max_step,
        },
    }


def relative_difference(reference: float, comparison: float) -> float | None:
    if not np.isfinite(reference) or not np.isfinite(comparison) or abs(reference) <= 1.0e-12:
        return None
    return float(abs(comparison - reference) / abs(reference))


def relative_spread(values: list[float | None]) -> float | None:
    if any(value is None for value in values):
        return None
    array = np.asarray(values, dtype=float)
    median = float(np.median(array))
    if np.any(~np.isfinite(array)) or abs(median) <= 1.0e-12:
        return None
    return float((np.max(array) - np.min(array)) / abs(median))


def cycle_validity(
    *,
    solver_accepted: bool,
    pre_reset_a: float,
    pre_reset_b: float,
    achieved_reset_a: float,
    target_reset_a: float,
    direction_error: float,
    reconstruction_error: float,
    segment_energy_drift: float,
    finite_accumulation: bool,
) -> dict[str, bool]:
    reset_error = (
        abs(achieved_reset_a - target_reset_a) / target_reset_a
        if target_reset_a > 0.0
        else math.inf
    )
    return {
        "solver_and_state_valid": bool(solver_accepted),
        "candidate_a_pre_reset_positive_finite": bool(
            np.isfinite(pre_reset_a) and pre_reset_a > 0.0
        ),
        "candidate_b_pre_reset_positive_finite": bool(
            np.isfinite(pre_reset_b) and pre_reset_b > 0.0
        ),
        "inside_empirical_local_ceiling": bool(
            np.isfinite(pre_reset_a) and pre_reset_a <= LOCAL_DISTANCE_CEILING
        ),
        "reset_magnitude_recovered": bool(
            np.isfinite(reset_error) and reset_error <= RESET_RELATIVE_TOLERANCE
        ),
        "direction_preserved": bool(
            np.isfinite(direction_error)
            and direction_error <= DIRECTION_ABSOLUTE_TOLERANCE
        ),
        "wrapped_reconstruction_correct": bool(
            np.isfinite(reconstruction_error)
            and reconstruction_error <= RECONSTRUCTION_ABSOLUTE_TOLERANCE
        ),
        "segment_energy_valid": bool(
            np.isfinite(segment_energy_drift)
            and segment_energy_drift <= ENERGY_DRIFT_LIMIT
        ),
        "accumulation_finite": bool(finite_accumulation),
    }


def _segment_requested_times(start: float, end: float) -> np.ndarray:
    count = max(1, int(math.ceil((end - start) / REFERENCE_SAMPLE_INTERVAL)))
    return np.linspace(start, end, count + 1)


def aggregate_solver_statistics(statuses: list[dict[str, Any]]) -> dict[str, Any]:
    if not statuses:
        return {
            "solve_call_count": 0,
            "total_nfev": 0,
            "minimum_nfev_per_call": None,
            "maximum_nfev_per_call": None,
            "mean_nfev_per_call": None,
        }
    nfev = np.asarray([status["nfev"] for status in statuses], dtype=int)
    return {
        "solve_call_count": len(statuses),
        "total_nfev": int(np.sum(nfev)),
        "minimum_nfev_per_call": int(np.min(nfev)),
        "maximum_nfev_per_call": int(np.max(nfev)),
        "mean_nfev_per_call": float(np.mean(nfev)),
        "total_njev": int(sum(status["njev"] for status in statuses)),
        "total_nlu": int(sum(status["nlu"] for status in statuses)),
        "max_step_seconds": float(statuses[0]["max_step_seconds"]),
    }


def integrate_rebased_reference(
    dynamics: DoublePendulumLagrangian,
    cycle_times: np.ndarray,
    policy: SolverPolicy,
    *,
    max_step: float,
) -> dict[str, Any]:
    """Integrate one physical reference with coordinate rebases per cycle."""

    current_state = canonicalize_state_angles(BASE_STATE_RADIANS)
    current_lifted = np.array(current_state[:2], copy=True)
    boundary_states = [np.array(current_state, copy=True)]
    times = [float(cycle_times[0])]
    local_states = [np.array(current_state, copy=True)]
    lifted_angles = [np.array(current_lifted, copy=True)]
    statuses: list[dict[str, Any]] = []
    issues: list[str] = []
    maximum_abs_solver_angle = float(np.max(np.abs(current_state[:2])))

    for cycle_index in range(1, len(cycle_times)):
        requested = _segment_requested_times(
            float(cycle_times[cycle_index - 1]), float(cycle_times[cycle_index])
        )
        segment = solve_segment(
            dynamics, current_state, requested, policy, max_step=max_step
        )
        statuses.append(segment["solver_status"])
        if not segment["accepted"]:
            issues.extend(f"cycle_{cycle_index}:{issue}" for issue in segment["issues"])
            break
        raw_state = segment["state"]
        maximum_abs_solver_angle = max(
            maximum_abs_solver_angle, float(np.max(np.abs(raw_state[:, :2])))
        )
        local_segment = canonicalize_state_angles(raw_state)
        lifted_segment = accumulate_lifted_angles(local_segment[:, :2], current_lifted)
        times.extend(segment["time"][1:].tolist())
        local_states.extend(local_segment[1:])
        lifted_angles.extend(lifted_segment[1:])
        current_state = canonicalize_state_angles(raw_state[-1])
        current_lifted = np.array(lifted_segment[-1], copy=True)
        boundary_states.append(np.array(current_state, copy=True))

    accepted = len(boundary_states) == len(cycle_times) and not issues
    return {
        "accepted": accepted,
        "issues": issues,
        "time": np.asarray(times, dtype=float),
        "local_state": np.asarray(local_states, dtype=float),
        "lifted_angles": np.asarray(lifted_angles, dtype=float),
        "boundary_states": np.asarray(boundary_states, dtype=float),
        "solver_statistics": aggregate_solver_statistics(statuses),
        "maximum_abs_solver_angle_within_segment_radians": maximum_abs_solver_angle,
    }


def run_renormalised(
    dynamics: DoublePendulumLagrangian,
    *,
    run_id: str,
    duration: float,
    epsilon: float,
    reset_interval: float,
    length_metres: float,
    policy: SolverPolicy,
    max_step: float = BASELINE_MAX_STEP,
) -> dict[str, Any]:
    cycle_times = deterministic_cycle_times(duration, reset_interval)
    reference = integrate_rebased_reference(
        dynamics, cycle_times, policy, max_step=max_step
    )
    if not reference["accepted"]:
        return {
            "run_id": run_id,
            "accepted": False,
            "issues": [f"reference:{issue}" for issue in reference["issues"]],
            "cycles": [],
            "configuration": {
                "duration_seconds": duration,
                "epsilon_candidate_a_norm": epsilon,
                "reset_interval_seconds": reset_interval,
                "characteristic_length_metres": length_metres,
                "solver_policy": policy_dict(policy),
                "max_step_seconds": max_step,
                "requested_cycle_count": len(cycle_times) - 1,
            },
        }

    reference_time = reference["time"]
    reference_state = reference["local_state"]
    reference_energy = simple_energy(reference_state)
    reference_energy_drift = np.abs(reference_energy - reference_energy[0]) / energy_scale()
    reference_max_drift = float(np.max(reference_energy_drift))
    boundary_states = reference["boundary_states"]

    initial_scaled = np.array([0.0, epsilon, 0.0, 0.0])
    initial_physical = physical_el_vector(initial_scaled, length_metres)
    initial_direction = initial_scaled / np.linalg.norm(initial_scaled)
    shadow_state = reconstruct_shadow_state(
        boundary_states[0], initial_direction, epsilon, length_metres
    )
    achieved_initial_physical = wrapped_el_difference(boundary_states[0], shadow_state)
    previous_reset_a = float(
        candidate_a_distance(achieved_initial_physical, length_metres)
    )
    previous_reset_b = float(candidate_b_distance(boundary_states[0], shadow_state, length_metres))
    cumulative_log_a = 0.0
    cumulative_log_b = 0.0
    cycles: list[dict[str, Any]] = []
    run_issues: list[str] = []

    for cycle_index in range(1, len(cycle_times)):
        start_time = float(cycle_times[cycle_index - 1])
        end_time = float(cycle_times[cycle_index])
        reference_start = boundary_states[cycle_index - 1]
        reference_end = boundary_states[cycle_index]
        segment_time = np.linspace(start_time, end_time, SEGMENT_SAMPLE_COUNT)
        segment = solve_segment(
            dynamics, shadow_state, segment_time, policy, max_step=max_step
        )
        if not segment["accepted"]:
            cycles.append(
                {
                    "cycle_index": cycle_index,
                    "start_time_seconds": start_time,
                    "end_time_seconds": end_time,
                    "accepted": False,
                    "issues": segment["issues"],
                    "solver_status": segment["solver_status"],
                }
            )
            run_issues.append(f"cycle_{cycle_index}:segment_solver_or_state_failure")
            break

        pre_reset_state = canonicalize_state_angles(segment["state"][-1])
        physical_pre = wrapped_el_difference(reference_end, pre_reset_state)
        try:
            scaled_pre, pre_reset_a, direction, reset_physical = normalized_reset(
                physical_pre, epsilon, length_metres
            )
            growth_a, log_a = growth_contribution(pre_reset_a, previous_reset_a)
        except ValueError as exc:
            run_issues.append(f"cycle_{cycle_index}:candidate_a:{exc}")
            break

        pre_reset_b = float(candidate_b_distance(reference_end, pre_reset_state, length_metres))
        try:
            growth_b, log_b = growth_contribution(pre_reset_b, previous_reset_b)
        except ValueError as exc:
            run_issues.append(f"cycle_{cycle_index}:candidate_b:{exc}")
            break

        post_reset_state = reconstruct_shadow_state(
            reference_end, direction, epsilon, length_metres
        )
        achieved_physical = wrapped_el_difference(reference_end, post_reset_state)
        achieved_scaled = scaled_el_vector(achieved_physical, length_metres)
        achieved_reset_a = float(np.linalg.norm(achieved_scaled))
        achieved_direction = achieved_scaled / achieved_reset_a
        direction_error = float(np.max(np.abs(achieved_direction - direction)))
        reconstruction_error = float(np.max(np.abs(achieved_physical - reset_physical)))
        post_reset_b = float(candidate_b_distance(reference_end, post_reset_state, length_metres))

        segment_energy_drift = normalized_segment_energy_drift(segment["state"])
        max_segment_energy_drift = float(np.max(segment_energy_drift))
        reset_energy_change = float(
            (simple_energy(post_reset_state)[0] - simple_energy(pre_reset_state)[0])
            / energy_scale()
        )

        next_cumulative_a = cumulative_log_a + log_a
        next_cumulative_b = cumulative_log_b + log_b
        cumulative_rate_a = next_cumulative_a / end_time
        cumulative_rate_b = next_cumulative_b / end_time
        checks = cycle_validity(
            solver_accepted=segment["accepted"],
            pre_reset_a=pre_reset_a,
            pre_reset_b=pre_reset_b,
            achieved_reset_a=achieved_reset_a,
            target_reset_a=epsilon,
            direction_error=direction_error,
            reconstruction_error=reconstruction_error,
            segment_energy_drift=max_segment_energy_drift,
            finite_accumulation=bool(
                np.all(
                    np.isfinite(
                        [
                            growth_a,
                            log_a,
                            next_cumulative_a,
                            cumulative_rate_a,
                            growth_b,
                            log_b,
                            next_cumulative_b,
                            cumulative_rate_b,
                            reset_energy_change,
                        ]
                    )
                )
            ),
        )
        accepted = all(checks.values())
        issues = [name for name, passed in checks.items() if not passed]
        cycles.append(
            {
                "cycle_index": cycle_index,
                "start_time_seconds": start_time,
                "end_time_seconds": end_time,
                "reference_start_state": reference_start.tolist(),
                "reference_end_state": reference_end.tolist(),
                "shadow_start_state": shadow_state.tolist(),
                "pre_reset_shadow_state": pre_reset_state.tolist(),
                "wrapped_physical_perturbation": physical_pre.tolist(),
                "scaled_candidate_a_perturbation": scaled_pre.tolist(),
                "pre_reset_candidate_a_norm": pre_reset_a,
                "target_reset_candidate_a_norm": epsilon,
                "achieved_post_reset_candidate_a_norm": achieved_reset_a,
                "normalized_scaled_direction": direction.tolist(),
                "post_reset_shadow_state": post_reset_state.tolist(),
                "growth_factor_candidate_a": growth_a,
                "log_growth_candidate_a": log_a,
                "cumulative_log_candidate_a": next_cumulative_a,
                "cumulative_rate_candidate_a_per_second": cumulative_rate_a,
                "previous_post_reset_candidate_b_norm": previous_reset_b,
                "pre_reset_candidate_b_norm": pre_reset_b,
                "post_reset_candidate_b_norm": post_reset_b,
                "growth_factor_candidate_b_along_a_reset": growth_b,
                "log_growth_candidate_b_along_a_reset": log_b,
                "cumulative_log_candidate_b_along_a_reset": next_cumulative_b,
                "cumulative_rate_candidate_b_along_a_reset_per_second": cumulative_rate_b,
                "reset_relative_error": abs(achieved_reset_a - epsilon) / epsilon,
                "direction_max_component_error": direction_error,
                "wrapped_reconstruction_max_error": reconstruction_error,
                "segment_max_normalized_energy_drift": max_segment_energy_drift,
                "deliberate_reset_normalized_energy_change": reset_energy_change,
                "solver_status": segment["solver_status"],
                "checks": checks,
                "accepted": accepted,
                "issues": issues,
            }
        )
        if not accepted:
            run_issues.append(f"cycle_{cycle_index}:" + ",".join(issues))
            break

        cumulative_log_a = next_cumulative_a
        cumulative_log_b = next_cumulative_b
        shadow_state = post_reset_state
        previous_reset_a = achieved_reset_a
        previous_reset_b = post_reset_b

    requested_cycles = len(cycle_times) - 1
    all_cycles_valid = len(cycles) == requested_cycles and all(
        cycle.get("accepted", False) for cycle in cycles
    )
    reference_valid = reference_max_drift <= ENERGY_DRIFT_LIMIT
    if not reference_valid:
        run_issues.append(
            f"reference_energy_drift_exceeded:{reference_max_drift:.6e}>{ENERGY_DRIFT_LIMIT:.6e}"
        )
    accepted = all_cycles_valid and reference_valid and not run_issues

    logs_a = np.asarray([cycle["log_growth_candidate_a"] for cycle in cycles if cycle.get("accepted")])
    rates_a = np.asarray(
        [cycle["cumulative_rate_candidate_a_per_second"] for cycle in cycles if cycle.get("accepted")]
    )
    end_times = np.asarray([cycle["end_time_seconds"] for cycle in cycles if cycle.get("accepted")])
    last_valid_rate_a = float(rates_a[-1]) if len(rates_a) else None
    final_rate_a = last_valid_rate_a if accepted else None
    final_rate_b = (
        float(cycles[-1]["cumulative_rate_candidate_b_along_a_reset_per_second"])
        if accepted
        else None
    )
    contraction_count = int(np.count_nonzero(logs_a < 0.0))
    reference_lifted_angles = reference["lifted_angles"]
    reference_revolutions = (
        (reference_lifted_angles[-1] - reference_lifted_angles[0])
        / (2.0 * math.pi)
    ).tolist()
    detailed_cycles = [cycle for cycle in cycles if "pre_reset_candidate_a_norm" in cycle]
    return {
        "run_id": run_id,
        "accepted": accepted,
        "issues": run_issues,
        "configuration": {
            "duration_seconds": duration,
            "epsilon_candidate_a_norm": epsilon,
            "reset_interval_seconds": reset_interval,
            "characteristic_length_metres": length_metres,
            "characteristic_time_seconds": characteristic_time(length_metres),
            "solver_policy": policy_dict(policy),
            "max_step_seconds": max_step,
            "angular_rebasing_convention": "theta_i in (-pi, pi] at every cycle boundary",
            "requested_cycle_count": requested_cycles,
        },
        "reference": {
            "physical_trajectory_uninterrupted": True,
            "single_solve_call": False,
            "coordinate_rebased_at_cycle_boundaries": True,
            "solver_statistics": reference["solver_statistics"],
            "max_normalized_energy_drift": reference_max_drift,
            "total_signed_revolutions": reference_revolutions,
            "maximum_abs_local_angle_radians": float(
                np.max(np.abs(reference_state[:, :2]))
            ),
            "maximum_abs_solver_angle_within_segment_radians": reference[
                "maximum_abs_solver_angle_within_segment_radians"
            ],
            "winding_bookkeeping": (
                "wrapped increments of 0.01 s local samples accumulated outside solver state"
            ),
        },
        "valid_cycle_count": sum(cycle.get("accepted", False) for cycle in cycles),
        "contraction_cycle_count": contraction_count,
        "expansion_cycle_count": int(len(logs_a) - contraction_count),
        "minimum_cycle_log_stretching": float(np.min(logs_a)) if len(logs_a) else None,
        "maximum_cycle_log_stretching": float(np.max(logs_a)) if len(logs_a) else None,
        "mean_cycle_log_stretching": float(np.mean(logs_a)) if len(logs_a) else None,
        "final_cumulative_log_stretching": float(np.sum(logs_a)) if len(logs_a) else None,
        "final_cumulative_rate_candidate_a_per_second": final_rate_a,
        "last_valid_cumulative_rate_candidate_a_per_second": last_valid_rate_a,
        "final_cumulative_rate_candidate_b_along_a_reset_per_second": final_rate_b,
        "maximum_pre_reset_candidate_a_norm": (
            max(cycle["pre_reset_candidate_a_norm"] for cycle in detailed_cycles)
            if detailed_cycles
            else None
        ),
        "maximum_reset_relative_error": (
            max(cycle["reset_relative_error"] for cycle in detailed_cycles)
            if detailed_cycles
            else None
        ),
        "maximum_direction_component_error": (
            max(cycle["direction_max_component_error"] for cycle in detailed_cycles)
            if detailed_cycles
            else None
        ),
        "maximum_segment_energy_drift": (
            max(
                cycle["segment_max_normalized_energy_drift"]
                for cycle in detailed_cycles
            )
            if detailed_cycles
            else None
        ),
        "minimum_deliberate_reset_energy_change": (
            min(cycle["deliberate_reset_normalized_energy_change"] for cycle in detailed_cycles)
            if detailed_cycles
            else None
        ),
        "maximum_deliberate_reset_energy_change": (
            max(cycle["deliberate_reset_normalized_energy_change"] for cycle in detailed_cycles)
            if detailed_cycles
            else None
        ),
        "maximum_absolute_deliberate_reset_energy_change": (
            max(abs(cycle["deliberate_reset_normalized_energy_change"]) for cycle in detailed_cycles)
            if detailed_cycles
            else None
        ),
        "shadow_solver_statistics": aggregate_solver_statistics(
            [cycle["solver_status"] for cycle in cycles if "solver_status" in cycle]
        ),
        "first_failed_cycle_end_time_seconds": (
            next(
                (
                    cycle["end_time_seconds"]
                    for cycle in cycles
                    if not cycle.get("accepted", False)
                ),
                None,
            )
        ),
        "cycles": cycles,
        "_reference_time": reference_time,
        "_reference_energy_drift": reference_energy_drift,
        "_reference_local_state": reference_state,
        "_reference_lifted_angles": reference["lifted_angles"],
        "_cycle_end_times": end_times,
        "_cycle_logs_a": logs_a,
        "_cycle_rates_a": rates_a,
    }


def public_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in run.items() if not key.startswith("_") and key != "cycles"}


def _block_rate(run: dict[str, Any], start: float, end: float) -> float | None:
    cycles = [
        cycle
        for cycle in run["cycles"]
        if cycle.get("accepted")
        and cycle["end_time_seconds"] > start + 1.0e-12
        and cycle["end_time_seconds"] <= end + 1.0e-12
    ]
    if not cycles or not math.isclose(
        sum(cycle["end_time_seconds"] - cycle["start_time_seconds"] for cycle in cycles),
        end - start,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        return None
    return float(sum(cycle["log_growth_candidate_a"] for cycle in cycles) / (end - start))


def tolerance_policy_comparison(
    baseline: dict[str, Any], stricter: dict[str, Any]
) -> dict[str, Any]:
    """Compare like-timed baseline/strict cycles, directions, and references."""

    base_cycles = [cycle for cycle in baseline["cycles"] if cycle.get("accepted")]
    strict_cycles = [cycle for cycle in stricter["cycles"] if cycle.get("accepted")]
    count = min(len(base_cycles), len(strict_cycles))
    times = np.asarray(
        [base_cycles[index]["end_time_seconds"] for index in range(count)], dtype=float
    )
    strict_times = np.asarray(
        [strict_cycles[index]["end_time_seconds"] for index in range(count)], dtype=float
    )
    if not np.array_equal(times, strict_times):
        raise ValueError("Tolerance-policy cycles are not synchronized.")
    base_logs = np.asarray(
        [base_cycles[index]["log_growth_candidate_a"] for index in range(count)]
    )
    strict_logs = np.asarray(
        [strict_cycles[index]["log_growth_candidate_a"] for index in range(count)]
    )
    base_rates = np.asarray(
        [
            base_cycles[index]["cumulative_rate_candidate_a_per_second"]
            for index in range(count)
        ]
    )
    strict_rates = np.asarray(
        [
            strict_cycles[index]["cumulative_rate_candidate_a_per_second"]
            for index in range(count)
        ]
    )
    base_directions = np.asarray(
        [base_cycles[index]["normalized_scaled_direction"] for index in range(count)]
    )
    strict_directions = np.asarray(
        [strict_cycles[index]["normalized_scaled_direction"] for index in range(count)]
    )
    log_difference = np.abs(base_logs - strict_logs)
    direction_difference = np.max(
        np.abs(base_directions - strict_directions), axis=1
    )
    rate_relative_difference = np.abs(base_rates - strict_rates) / np.maximum(
        np.abs(base_rates), 1.0e-12
    )

    reference_times = baseline["_reference_time"]
    if not np.array_equal(reference_times, stricter["_reference_time"]):
        raise ValueError("Tolerance-policy reference samples are not synchronized.")
    reference_difference = candidate_a_distance(
        wrapped_el_difference(
            baseline["_reference_local_state"], stricter["_reference_local_state"]
        )
    )

    def first_crossing(values: np.ndarray, threshold: float) -> float | None:
        indices = np.flatnonzero(values > threshold)
        return float(times[indices[0]]) if len(indices) else None

    reference_crossings: dict[str, float | None] = {}
    for threshold in (1.0e-6, 1.0e-4, 1.0e-2, 1.0e-1, 1.0):
        indices = np.flatnonzero(reference_difference > threshold)
        reference_crossings[f"{threshold:.0e}"] = (
            float(reference_times[indices[0]]) if len(indices) else None
        )

    return {
        "comparison_cycle_count": count,
        "reference_paths": "independently integrated under each complete tolerance policy",
        "first_material_log_difference_time_seconds": first_crossing(
            log_difference, MATERIAL_POLICY_LOG_DIFFERENCE
        ),
        "first_material_direction_difference_time_seconds": first_crossing(
            direction_difference, MATERIAL_POLICY_DIRECTION_DIFFERENCE
        ),
        "first_one_percent_cumulative_rate_difference_time_seconds": first_crossing(
            rate_relative_difference, MAX_TOLERANCE_RATE_DIFFERENCE
        ),
        "maximum_absolute_cycle_log_difference": float(np.max(log_difference)),
        "maximum_direction_component_difference": float(np.max(direction_difference)),
        "maximum_cumulative_rate_relative_difference": float(
            np.max(rate_relative_difference)
        ),
        "final_cumulative_rate_relative_difference": float(
            rate_relative_difference[-1]
        ),
        "reference_candidate_a_first_crossing_seconds": reference_crossings,
        "reference_candidate_a_final_distance": float(reference_difference[-1]),
        "cumulative_rates_reconverged_within_one_percent_at_80s": bool(
            rate_relative_difference[-1] <= MAX_TOLERANCE_RATE_DIFFERENCE
        ),
        "_times": times,
        "_baseline_logs": base_logs,
        "_stricter_logs": strict_logs,
        "_baseline_rates": base_rates,
        "_stricter_rates": strict_rates,
        "_direction_difference": direction_difference,
        "_reference_time": reference_times,
        "_reference_difference": reference_difference,
    }


def convergence_analysis(
    duration_runs: dict[float, dict[str, Any]],
    magnitude_runs: dict[float, dict[str, Any]],
    interval_runs: dict[float, dict[str, Any]],
    scaling_run: dict[str, Any],
    stricter_run: dict[str, Any],
    refined_max_step_run: dict[str, Any],
    policy_comparison: dict[str, Any],
) -> dict[str, Any]:
    baseline_20 = duration_runs[20.0]
    baseline_40 = duration_runs[40.0]
    baseline_80 = duration_runs[80.0]
    rate_20 = baseline_20["final_cumulative_rate_candidate_a_per_second"]
    rate_40 = baseline_40["final_cumulative_rate_candidate_a_per_second"]
    rate_80 = baseline_80["final_cumulative_rate_candidate_a_per_second"]
    change_20_40 = relative_difference(rate_40, rate_20)
    change_40_80 = relative_difference(rate_80, rate_40)

    final_quarter_mask = baseline_80["_cycle_end_times"] >= 60.0 - 1.0e-12
    final_quarter_rates = baseline_80["_cycle_rates_a"][final_quarter_mask]
    final_quarter_spread = (
        float((np.max(final_quarter_rates) - np.min(final_quarter_rates)) / abs(rate_80))
        if len(final_quarter_rates) and abs(rate_80) > 1.0e-12
        else None
    )
    quarter_3_rate = _block_rate(baseline_80, 40.0, 60.0)
    quarter_4_rate = _block_rate(baseline_80, 60.0, 80.0)
    late_quarter_difference = relative_difference(quarter_4_rate, quarter_3_rate)

    post_transient_cycles = [
        cycle
        for cycle in baseline_80["cycles"]
        if cycle.get("accepted")
        and cycle["start_time_seconds"] >= INITIAL_TRANSIENT_SECONDS - 1.0e-12
    ]
    post_transient_rate = float(
        sum(cycle["log_growth_candidate_a"] for cycle in post_transient_cycles)
        / (80.0 - INITIAL_TRANSIENT_SECONDS)
    )
    transient_difference = relative_difference(rate_80, post_transient_rate)

    magnitude_rates = {
        f"{epsilon:.0e}": run["final_cumulative_rate_candidate_a_per_second"]
        for epsilon, run in magnitude_runs.items()
    }
    interval_rates = {
        f"{interval:g}": run["final_cumulative_rate_candidate_a_per_second"]
        for interval, run in interval_runs.items()
    }
    magnitude_spread = relative_spread(list(magnitude_rates.values()))
    interval_spread = relative_spread(list(interval_rates.values()))
    scaling_difference = relative_difference(
        rate_80, scaling_run["final_cumulative_rate_candidate_a_per_second"]
    )
    tolerance_difference = relative_difference(
        rate_80, stricter_run["final_cumulative_rate_candidate_a_per_second"]
    )
    max_step_difference = relative_difference(
        rate_80,
        refined_max_step_run["final_cumulative_rate_candidate_a_per_second"],
    )
    required_runs = [
        *duration_runs.values(),
        *magnitude_runs.values(),
        *interval_runs.values(),
        scaling_run,
        stricter_run,
        refined_max_step_run,
    ]
    checks = {
        "all_required_runs_valid": all(run["accepted"] for run in required_runs),
        "duration_change_20_to_40_within_10_percent": (
            change_20_40 is not None and change_20_40 <= MAX_DURATION_CHANGE_20_TO_40
        ),
        "duration_change_40_to_80_within_5_percent": (
            change_40_80 is not None and change_40_80 <= MAX_DURATION_CHANGE_40_TO_80
        ),
        "final_quarter_cumulative_spread_within_5_percent": (
            final_quarter_spread is not None
            and final_quarter_spread <= MAX_FINAL_QUARTER_CUMULATIVE_SPREAD
        ),
        "late_quarter_block_rates_within_10_percent": (
            late_quarter_difference is not None
            and late_quarter_difference <= MAX_LATE_QUARTER_RATE_DIFFERENCE
        ),
        "initial_transient_effect_within_5_percent": (
            transient_difference is not None
            and transient_difference <= MAX_INITIAL_TRANSIENT_RATE_DIFFERENCE
        ),
        "reset_magnitude_spread_within_5_percent": (
            magnitude_spread is not None
            and magnitude_spread <= MAX_RESET_MAGNITUDE_RATE_SPREAD
        ),
        "reset_interval_spread_within_10_percent": (
            interval_spread is not None
            and interval_spread <= MAX_RESET_INTERVAL_RATE_SPREAD
        ),
        "strict_tolerance_difference_within_1_percent": (
            tolerance_difference is not None
            and tolerance_difference <= MAX_TOLERANCE_RATE_DIFFERENCE
        ),
        "scaling_difference_within_5_percent": (
            scaling_difference is not None
            and scaling_difference <= MAX_SCALING_RATE_DIFFERENCE
        ),
        "max_step_refinement_difference_within_1_percent": (
            max_step_difference is not None
            and max_step_difference <= MAX_MAX_STEP_RATE_DIFFERENCE
        ),
    }
    return {
        "duration_final_rates_per_second": {
            "20": rate_20,
            "40": rate_40,
            "80": rate_80,
        },
        "relative_change_20_to_40": change_20_40,
        "relative_change_40_to_80": change_40_80,
        "final_quarter_cumulative_rate_range_relative_to_final": final_quarter_spread,
        "block_rate_40_to_60_per_second": quarter_3_rate,
        "block_rate_60_to_80_per_second": quarter_4_rate,
        "late_quarter_block_rate_relative_difference": late_quarter_difference,
        "post_2_second_transient_rate_per_second": post_transient_rate,
        "full_vs_post_transient_relative_difference": transient_difference,
        "reset_magnitude_final_rates_per_second": magnitude_rates,
        "reset_magnitude_relative_spread": magnitude_spread,
        "reset_interval_final_rates_per_second": interval_rates,
        "reset_interval_relative_spread": interval_spread,
        "alternative_scaling_final_rate_per_second": scaling_run[
            "final_cumulative_rate_candidate_a_per_second"
        ],
        "alternative_scaling_relative_difference": scaling_difference,
        "stricter_tolerance_final_rate_per_second": stricter_run[
            "final_cumulative_rate_candidate_a_per_second"
        ],
        "stricter_tolerance_relative_difference": tolerance_difference,
        "max_step_refinement_final_rate_per_second": refined_max_step_run[
            "final_cumulative_rate_candidate_a_per_second"
        ],
        "max_step_refinement_relative_difference": max_step_difference,
        "tolerance_policy_divergence": {
            key: value
            for key, value in policy_comparison.items()
            if not key.startswith("_")
        },
        "candidate_b_along_a_reset_final_rate_per_second": baseline_80[
            "final_cumulative_rate_candidate_b_along_a_reset_per_second"
        ],
        "candidate_a_b_along_a_reset_relative_difference": relative_difference(
            rate_80,
            baseline_80["final_cumulative_rate_candidate_b_along_a_reset_per_second"],
        ),
        "candidate_b_comparison_limitation": (
            "Candidate B measures the Candidate-A-renormalised shadow segments; "
            "Candidate B does not define the reset map."
        ),
        "checks": checks,
        "accepted": all(checks.values()),
        "rejection_reasons": [name for name, passed in checks.items() if not passed],
    }


def run_investigation(max_duration: float = 20.0) -> dict[str, Any]:
    if max_duration not in DURATION_STAGES:
        raise ValueError(f"max_duration must be one of {DURATION_STAGES}")
    dynamics = build_dynamics()
    duration_runs: dict[float, dict[str, Any]] = {}
    all_runs: list[dict[str, Any]] = []
    for duration in DURATION_STAGES:
        if duration > max_duration:
            break
        run = run_renormalised(
            dynamics,
            run_id=f"baseline_{duration:.0f}s",
            duration=duration,
            epsilon=BASELINE_EPSILON,
            reset_interval=BASELINE_RESET_INTERVAL,
            length_metres=LC_BASELINE,
            policy=SIMPLE_REFERENCE_SOLVER_POLICY,
            max_step=BASELINE_MAX_STEP,
        )
        duration_runs[duration] = run
        all_runs.append(run)
        if not run["accepted"]:
            break

    completed_duration = max(duration_runs) if duration_runs else None
    if not duration_runs or not all(run["accepted"] for run in duration_runs.values()):
        summary = _base_summary(max_duration, all_runs)
        summary.update(
            {
                "status": "rejected_numerical_or_cycle_failure",
                "accepted": False,
                "completed_duration_seconds": completed_duration,
                "failure_reason": "a staged baseline run failed; later stages were not executed",
                "strongest_claim": "No stretching interpretation is permitted after cycle rejection.",
            }
        )
        return {"summary": summary, "runs": all_runs, "convergence": None}

    if max_duration < 80.0:
        summary = _base_summary(max_duration, all_runs)
        summary.update(
            {
                "status": "intermediate_duration_stage_valid",
                "accepted": None,
                "completed_duration_seconds": completed_duration,
                "failure_reason": None,
                "strongest_claim": (
                    f"The baseline renormalisation algorithm passed through {completed_duration:.0f} s; "
                    "final convergence and robustness have not yet been evaluated."
                ),
            }
        )
        return {"summary": summary, "runs": all_runs, "convergence": None}

    baseline_80 = duration_runs[80.0]
    magnitude_runs: dict[float, dict[str, Any]] = {BASELINE_EPSILON: baseline_80}
    for epsilon in EPSILONS:
        if epsilon == BASELINE_EPSILON:
            continue
        run = run_renormalised(
            dynamics,
            run_id=f"magnitude_{epsilon:.0e}_80s",
            duration=80.0,
            epsilon=epsilon,
            reset_interval=BASELINE_RESET_INTERVAL,
            length_metres=LC_BASELINE,
            policy=SIMPLE_REFERENCE_SOLVER_POLICY,
            max_step=BASELINE_MAX_STEP,
        )
        magnitude_runs[epsilon] = run
        all_runs.append(run)

    interval_runs: dict[float, dict[str, Any]] = {BASELINE_RESET_INTERVAL: baseline_80}
    for interval in RESET_INTERVALS:
        if interval == BASELINE_RESET_INTERVAL:
            continue
        run = run_renormalised(
            dynamics,
            run_id=f"interval_{interval:g}s_80s",
            duration=80.0,
            epsilon=BASELINE_EPSILON,
            reset_interval=interval,
            length_metres=LC_BASELINE,
            policy=SIMPLE_REFERENCE_SOLVER_POLICY,
            max_step=BASELINE_MAX_STEP,
        )
        interval_runs[interval] = run
        all_runs.append(run)

    scaling_run = run_renormalised(
        dynamics,
        run_id="scaling_lc_2m_80s",
        duration=80.0,
        epsilon=BASELINE_EPSILON,
        reset_interval=BASELINE_RESET_INTERVAL,
        length_metres=LC_ALTERNATIVE,
        policy=SIMPLE_REFERENCE_SOLVER_POLICY,
        max_step=BASELINE_MAX_STEP,
    )
    stricter_run = run_renormalised(
        dynamics,
        run_id="stricter_80s",
        duration=80.0,
        epsilon=BASELINE_EPSILON,
        reset_interval=BASELINE_RESET_INTERVAL,
        length_metres=LC_BASELINE,
        policy=STRICTER_POLICY,
        max_step=BASELINE_MAX_STEP,
    )
    refined_max_step_run = run_renormalised(
        dynamics,
        run_id="refined_max_step_80s",
        duration=80.0,
        epsilon=BASELINE_EPSILON,
        reset_interval=BASELINE_RESET_INTERVAL,
        length_metres=LC_BASELINE,
        policy=SIMPLE_REFERENCE_SOLVER_POLICY,
        max_step=REFINED_MAX_STEP,
    )
    all_runs.extend((scaling_run, stricter_run, refined_max_step_run))
    policy_comparison = tolerance_policy_comparison(baseline_80, stricter_run)
    convergence = convergence_analysis(
        duration_runs,
        magnitude_runs,
        interval_runs,
        scaling_run,
        stricter_run,
        refined_max_step_run,
        policy_comparison,
    )
    accepted = convergence["accepted"]
    controls = convergence["checks"]
    numerically_controlled = all(
        controls[name]
        for name in (
            "all_required_runs_valid",
            "reset_magnitude_spread_within_5_percent",
            "reset_interval_spread_within_10_percent",
            "strict_tolerance_difference_within_1_percent",
            "scaling_difference_within_5_percent",
            "max_step_refinement_difference_within_1_percent",
        )
    )
    outcome = "Outcome A" if accepted else ("Outcome B" if numerically_controlled else "Outcome C")
    summary = _base_summary(max_duration, all_runs)
    summary.update(
        {
            "status": (
                "repaired_experiment_005_converged"
                if outcome == "Outcome A"
                else (
                    "repaired_numerically_controlled_but_not_duration_converged"
                    if outcome == "Outcome B"
                    else "repaired_nearby_shadow_method_numerically_unresolved"
                )
            ),
            "outcome_classification": outcome,
            "accepted": accepted,
            "completed_duration_seconds": 80.0,
            "failure_reason": None if accepted else "one_or_more_predeclared_convergence_checks_failed",
            "convergence": convergence,
            "strongest_claim": (
                "Repeated Candidate-A renormalisation preserves a valid local perturbation and the "
                "accumulated stretching rate stabilises under the declared robustness checks."
                if accepted
                else (
                    "The finite-shadow calculation is numerically controlled under the repaired "
                    "policy, but its accumulated rate has not converged over 20, 40, and 80 s."
                    if numerically_controlled
                    else "The repaired nearby-shadow calculation remains numerically unresolved "
                    "under at least one declared robustness comparison."
                )
            ),
        }
    )
    return {
        "summary": summary,
        "runs": all_runs,
        "convergence": convergence,
        "policy_comparison": policy_comparison,
    }


def _base_summary(max_duration: float, runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "experiment": EXPERIMENT_NAME,
        "iteration": "repaired_second_numerical_iteration_of_experiment_005",
        "historical_context": {
            "original_result": "renormalised_rate_not_robustly_stabilised",
            "original_baseline_80s_rate_per_second": 1.039930922101729,
            "original_strict_80s_rate_per_second": 0.7881667381880963,
            "original_rejected_comparisons": {
                "epsilon_1e-6": (
                    "rejected at 45 s; direction-component error 1.34013e-8"
                ),
                "reset_interval_0.125s": (
                    "rejected at 18.25 s; segment energy drift 2.27188e-6"
                ),
                "strict_tolerance_relative_difference": 0.2420970264109565,
            },
            "audit": "development/chaos_content/experiments/LYAPUNOV_REVIEW.md",
            "audit_verdict": "original method-level negative result not trustworthy because of identified defect",
            "audited_contamination_repaired": [
                "winding-dependent solver relative-error scaling",
                "unrestricted adaptive maximum step",
                "lifted-angle reset reconstruction precision loss",
            ],
            "original_outputs_preserved_at": (
                "development/chaos_content/experiments/outputs/005/baseline"
            ),
        },
        "question": (
            "Does repeated direction-preserving renormalisation keep the perturbation local and "
            "produce a more stable accumulated logarithmic stretching rate?"
        ),
        "requested_max_duration_seconds": max_duration,
        "configuration": {
            "model": MODEL,
            "formulation": FORMULATION,
            "state_order": ["theta1", "theta2", "omega1", "omega2"],
            "base_initial_state_degrees": BASE_STATE_DEGREES.tolist(),
            "initial_perturbation_direction": [0.0, 1.0, 0.0, 0.0],
            "baseline_reset_candidate_a_norm": BASELINE_EPSILON,
            "baseline_reset_interval_seconds": BASELINE_RESET_INTERVAL,
            "duration_stages_seconds": list(DURATION_STAGES),
            "reset_magnitude_comparison": list(EPSILONS),
            "reset_interval_comparison_seconds": list(RESET_INTERVALS),
            "characteristic_length_metres": LC_BASELINE,
            "alternative_characteristic_length_metres": LC_ALTERNATIVE,
            "characteristic_time_seconds": characteristic_time(),
            "parameters_si": {str(key): float(value) for key, value in PARAMETERS.items()},
            "baseline_solver_policy": policy_dict(SIMPLE_REFERENCE_SOLVER_POLICY),
            "stricter_solver_policy": policy_dict(STRICTER_POLICY),
            "angular_canonicalisation": "deterministic (-pi, pi] at cycle boundaries",
            "winding_bookkeeping": (
                "continuous lifted history reconstructed from wrapped 0.01 s sample increments; "
                "not supplied to solve_ivp or Candidate A"
            ),
            "baseline_max_step_seconds": BASELINE_MAX_STEP,
            "baseline_max_step_derivation": "min(Tc/32, baseline_tau_r/25)",
            "refined_max_step_seconds": REFINED_MAX_STEP,
            "reference_sample_interval_seconds": REFERENCE_SAMPLE_INTERVAL,
            "shadow_segment_requested_sample_count": SEGMENT_SAMPLE_COUNT,
            "dense_output_requested": False,
            "local_distance_ceiling": LOCAL_DISTANCE_CEILING,
            "energy_drift_limit": ENERGY_DRIFT_LIMIT,
        },
        "definitions": {
            "candidate_a_scaled_vector": "q=(delta_theta1,delta_theta2,Tc*delta_omega1,Tc*delta_omega2)",
            "reset": "q_plus=epsilon*q_minus/||q_minus||, mapped back with delta_omega=q_velocity/Tc",
            "cycle_growth": "g_k=d_k_minus/d_(k-1)_plus",
            "cycle_log_stretching": "ell_k=log(g_k), including negative contraction values",
            "cumulative_rate": "Lambda_N=sum(ell_k)/t_N; descriptive, not lambda_max",
            "candidate_b_role": "measured along Candidate-A resets; does not define reset direction",
            "reference_semantics": (
                "one uninterrupted physical trajectory, coordinate-rebased and solver-restarted "
                "at cycle boundaries"
            ),
        },
        "thresholds": {
            "duration_change_20_to_40": MAX_DURATION_CHANGE_20_TO_40,
            "duration_change_40_to_80": MAX_DURATION_CHANGE_40_TO_80,
            "final_quarter_cumulative_spread": MAX_FINAL_QUARTER_CUMULATIVE_SPREAD,
            "late_quarter_rate_difference": MAX_LATE_QUARTER_RATE_DIFFERENCE,
            "initial_transient_rate_difference": MAX_INITIAL_TRANSIENT_RATE_DIFFERENCE,
            "reset_magnitude_rate_spread": MAX_RESET_MAGNITUDE_RATE_SPREAD,
            "reset_interval_rate_spread": MAX_RESET_INTERVAL_RATE_SPREAD,
            "tolerance_rate_difference": MAX_TOLERANCE_RATE_DIFFERENCE,
            "scaling_rate_difference": MAX_SCALING_RATE_DIFFERENCE,
            "max_step_refinement_rate_difference": MAX_MAX_STEP_RATE_DIFFERENCE,
            "status": "provisional and fixed in README before execution",
        },
        "runs": [public_run_summary(run) for run in runs],
        "claim_boundary": (
            "Lambda_N is an accumulated renormalised finite-time stretching rate, not an accepted "
            "maximal Lyapunov exponent. No tangent dynamics, spectrum, Hamiltonian comparison, "
            "coordinate-invariant claim, phase-space generalisation, or chaos classification is supported."
        ),
    }


def json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_cycles_json(path: Path, runs: list[dict[str, Any]]) -> None:
    json_write(
        path,
        [
            {
                "run_id": run["run_id"],
                "configuration": run["configuration"],
                "accepted": run["accepted"],
                "cycles": run["cycles"],
            }
            for run in runs
        ],
    )


def write_cycles_csv(path: Path, runs: list[dict[str, Any]]) -> None:
    fields = [
        "run_id",
        "cycle_index",
        "start_time_s",
        "end_time_s",
        *[f"reference_end_{name}" for name in ("theta1", "theta2", "omega1", "omega2")],
        *[f"pre_reset_shadow_{name}" for name in ("theta1", "theta2", "omega1", "omega2")],
        *[f"wrapped_delta_{name}" for name in ("theta1", "theta2", "omega1", "omega2")],
        *[f"scaled_delta_{name}" for name in ("theta1", "theta2", "omega1", "omega2")],
        *[f"direction_{name}" for name in ("theta1", "theta2", "tc_omega1", "tc_omega2")],
        "pre_reset_a",
        "target_reset_a",
        "achieved_post_reset_a",
        "growth_a",
        "log_growth_a",
        "cumulative_log_a",
        "cumulative_rate_a_per_s",
        "pre_reset_b",
        "post_reset_b",
        "log_growth_b_along_a_reset",
        "cumulative_rate_b_along_a_reset_per_s",
        "segment_energy_drift",
        "reset_energy_change",
        "accepted",
        "issues",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            for cycle in run["cycles"]:
                if "reference_end_state" not in cycle:
                    writer.writerow(
                        {
                            "run_id": run["run_id"],
                            "cycle_index": cycle["cycle_index"],
                            "start_time_s": cycle["start_time_seconds"],
                            "end_time_s": cycle["end_time_seconds"],
                            "accepted": False,
                            "issues": ";".join(cycle["issues"]),
                        }
                    )
                    continue
                row: dict[str, Any] = {
                    "run_id": run["run_id"],
                    "cycle_index": cycle["cycle_index"],
                    "start_time_s": cycle["start_time_seconds"],
                    "end_time_s": cycle["end_time_seconds"],
                    "pre_reset_a": cycle["pre_reset_candidate_a_norm"],
                    "target_reset_a": cycle["target_reset_candidate_a_norm"],
                    "achieved_post_reset_a": cycle["achieved_post_reset_candidate_a_norm"],
                    "growth_a": cycle["growth_factor_candidate_a"],
                    "log_growth_a": cycle["log_growth_candidate_a"],
                    "cumulative_log_a": cycle["cumulative_log_candidate_a"],
                    "cumulative_rate_a_per_s": cycle["cumulative_rate_candidate_a_per_second"],
                    "pre_reset_b": cycle["pre_reset_candidate_b_norm"],
                    "post_reset_b": cycle["post_reset_candidate_b_norm"],
                    "log_growth_b_along_a_reset": cycle[
                        "log_growth_candidate_b_along_a_reset"
                    ],
                    "cumulative_rate_b_along_a_reset_per_s": cycle[
                        "cumulative_rate_candidate_b_along_a_reset_per_second"
                    ],
                    "segment_energy_drift": cycle["segment_max_normalized_energy_drift"],
                    "reset_energy_change": cycle["deliberate_reset_normalized_energy_change"],
                    "accepted": cycle["accepted"],
                    "issues": ";".join(cycle["issues"]),
                }
                for prefix, values, names in (
                    ("reference_end", cycle["reference_end_state"], ("theta1", "theta2", "omega1", "omega2")),
                    ("pre_reset_shadow", cycle["pre_reset_shadow_state"], ("theta1", "theta2", "omega1", "omega2")),
                    ("wrapped_delta", cycle["wrapped_physical_perturbation"], ("theta1", "theta2", "omega1", "omega2")),
                    ("scaled_delta", cycle["scaled_candidate_a_perturbation"], ("theta1", "theta2", "omega1", "omega2")),
                    ("direction", cycle["normalized_scaled_direction"], ("theta1", "theta2", "tc_omega1", "tc_omega2")),
                ):
                    row.update({f"{prefix}_{name}": value for name, value in zip(names, values)})
                writer.writerow(row)


def write_policy_comparison_csv(path: Path, result: dict[str, Any]) -> None:
    comparison = result["policy_comparison"]
    refined = _run_by_id(result, "refined_max_step_80s")
    fields = [
        "cycle_end_time_s",
        "baseline_log_growth",
        "stricter_log_growth",
        "baseline_cumulative_rate_per_s",
        "stricter_cumulative_rate_per_s",
        "direction_max_component_difference",
        "refined_max_step_cumulative_rate_per_s",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, time_value in enumerate(comparison["_times"]):
            writer.writerow(
                {
                    "cycle_end_time_s": time_value,
                    "baseline_log_growth": comparison["_baseline_logs"][index],
                    "stricter_log_growth": comparison["_stricter_logs"][index],
                    "baseline_cumulative_rate_per_s": comparison["_baseline_rates"][index],
                    "stricter_cumulative_rate_per_s": comparison["_stricter_rates"][index],
                    "direction_max_component_difference": comparison[
                        "_direction_difference"
                    ][index],
                    "refined_max_step_cumulative_rate_per_s": refined[
                        "_cycle_rates_a"
                    ][index],
                }
            )


def write_winding_history_csv(path: Path, baseline: dict[str, Any]) -> None:
    fields = [
        "time_s",
        "local_theta1",
        "local_theta2",
        "lifted_theta1",
        "lifted_theta2",
        "signed_revolutions_theta1",
        "signed_revolutions_theta2",
    ]
    lifted = baseline["_reference_lifted_angles"]
    initial = lifted[0]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, time_value in enumerate(baseline["_reference_time"]):
            turns = (lifted[index] - initial) / (2.0 * math.pi)
            writer.writerow(
                {
                    "time_s": time_value,
                    "local_theta1": baseline["_reference_local_state"][index, 0],
                    "local_theta2": baseline["_reference_local_state"][index, 1],
                    "lifted_theta1": lifted[index, 0],
                    "lifted_theta2": lifted[index, 1],
                    "signed_revolutions_theta1": turns[0],
                    "signed_revolutions_theta2": turns[1],
                }
            )


def load_pyplot():
    import matplotlib.pyplot as plt

    return plt


def save_figure(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    load_pyplot().close(fig)


def _run_by_id(result: dict[str, Any], run_id: str) -> dict[str, Any]:
    return next(run for run in result["runs"] if run["run_id"] == run_id)


def write_plots(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    if result["summary"].get("completed_duration_seconds") != 80.0:
        return []
    plt = load_pyplot()
    baseline = _run_by_id(result, "baseline_80s")
    paths: list[Path] = []
    times = baseline["_cycle_end_times"]
    logs = baseline["_cycle_logs_a"]

    path = output_dir / "01_cycle_stretching.png"
    fig, axis = plt.subplots(figsize=(11, 6))
    colors = np.where(logs < 0.0, "tab:red", "tab:blue")
    axis.scatter(times, logs, c=colors, s=13, alpha=0.8)
    axis.axhline(0.0, color="black", linewidth=1)
    axis.set(
        xlabel="cycle end time / s",
        ylabel=r"$\ell_k=\log g_k$",
        title="Signed cycle stretching; red cycles contract",
    )
    axis.grid(True, alpha=0.25)
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "02_cumulative_rate.png"
    fig, axis = plt.subplots(figsize=(11, 6))
    for duration in DURATION_STAGES:
        run = _run_by_id(result, f"baseline_{duration:.0f}s")
        axis.plot(run["_cycle_end_times"], run["_cycle_rates_a"], label=f"{duration:.0f} s run")
    axis.set(
        xlabel="elapsed time / s",
        ylabel=r"$\Lambda_N$ / s$^{-1}$",
        title="Accumulated renormalised stretching rate (all cycles included)",
    )
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "03_reset_magnitude_verification.png"
    fig, axis = plt.subplots(figsize=(11, 6))
    pre = np.asarray([cycle["pre_reset_candidate_a_norm"] for cycle in baseline["cycles"]])
    post = np.asarray(
        [cycle["achieved_post_reset_candidate_a_norm"] for cycle in baseline["cycles"]]
    )
    axis.semilogy(times, pre, label="pre-reset Candidate A")
    axis.semilogy(times, post, label="achieved post-reset Candidate A")
    axis.axhline(BASELINE_EPSILON, color="black", linestyle=":", label="target epsilon")
    axis.axhline(LOCAL_DISTANCE_CEILING, color="red", linestyle="--", label="local ceiling")
    axis.set(xlabel="cycle end time / s", ylabel="dimensionless magnitude", title="Reset magnitude audit")
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "04_direction_evolution.png"
    fig, axis = plt.subplots(figsize=(11, 6))
    directions = np.asarray([cycle["normalized_scaled_direction"] for cycle in baseline["cycles"]])
    labels = (r"$\Delta\theta_1$", r"$\Delta\theta_2$", r"$T_c\Delta\omega_1$", r"$T_c\Delta\omega_2$")
    for index, label in enumerate(labels):
        axis.plot(times, directions[:, index], label=label, linewidth=1)
    axis.set(
        xlabel="cycle end time / s",
        ylabel="unit-direction component",
        title="Evolved scaled EL perturbation direction",
    )
    axis.grid(True, alpha=0.25)
    axis.legend(ncol=2)
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "05_reset_magnitude_robustness.png"
    fig, axis = plt.subplots(figsize=(11, 6))
    for epsilon in EPSILONS:
        run_id = "baseline_80s" if epsilon == BASELINE_EPSILON else f"magnitude_{epsilon:.0e}_80s"
        run = _run_by_id(result, run_id)
        status = "" if run["accepted"] else f" [rejected at {run['cycles'][-1]['end_time_seconds']:g} s]"
        axis.plot(
            run["_cycle_end_times"],
            run["_cycle_rates_a"],
            linestyle="-" if run["accepted"] else "--",
            label=f"epsilon={epsilon:.0e}{status}",
        )
    axis.set(xlabel="elapsed time / s", ylabel=r"$\Lambda_N$ / s$^{-1}$", title="Reset-magnitude robustness")
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "06_reset_interval_robustness.png"
    fig, axis = plt.subplots(figsize=(11, 6))
    for interval in RESET_INTERVALS:
        run_id = "baseline_80s" if interval == BASELINE_RESET_INTERVAL else f"interval_{interval:g}s_80s"
        run = _run_by_id(result, run_id)
        status = "" if run["accepted"] else f" [rejected at {run['cycles'][-1]['end_time_seconds']:g} s]"
        axis.plot(
            run["_cycle_end_times"],
            run["_cycle_rates_a"],
            linestyle="-" if run["accepted"] else "--",
            label=f"tau={interval:g} s{status}",
        )
    axis.set(xlabel="elapsed time / s", ylabel=r"$\Lambda_N$ / s$^{-1}$", title="Reset-interval robustness")
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "07_numerical_validity.png"
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=False)
    axes[0].plot(
        baseline["_reference_time"],
        baseline["_reference_energy_drift"],
        label="uninterrupted reference",
    )
    axes[0].axhline(ENERGY_DRIFT_LIMIT, color="red", linestyle=":", label="energy limit")
    segment_drifts = [cycle["segment_max_normalized_energy_drift"] for cycle in baseline["cycles"]]
    axes[1].plot(times, segment_drifts, label="shadow segment drift")
    axes[1].axhline(ENERGY_DRIFT_LIMIT, color="red", linestyle=":", label="energy limit")
    axes[0].set(ylabel="normalized drift", title="Uninterrupted reference energy")
    axes[1].set(xlabel="cycle end time / s", ylabel="normalized drift", title="Within-segment shadow energy")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "08_representation_scaling_tolerance.png"
    fig, axis = plt.subplots(figsize=(11, 6))
    scaling = _run_by_id(result, "scaling_lc_2m_80s")
    stricter = _run_by_id(result, "stricter_80s")
    candidate_b_rates = np.asarray(
        [
            cycle["cumulative_rate_candidate_b_along_a_reset_per_second"]
            for cycle in baseline["cycles"]
        ]
    )
    axis.plot(times, baseline["_cycle_rates_a"], label="A reset, Lc=1 m")
    axis.plot(scaling["_cycle_end_times"], scaling["_cycle_rates_a"], label="A reset, Lc=2 m")
    axis.plot(stricter["_cycle_end_times"], stricter["_cycle_rates_a"], linestyle="--", label="A reset, strict tolerance")
    axis.plot(times, candidate_b_rates, linestyle=":", label="B measured along A reset")
    axis.set(
        xlabel="elapsed time / s",
        ylabel="accumulated rate / s$^{-1}$",
        title="Scaling, tolerance, and limited Candidate-B representation checks",
    )
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    comparison = result["policy_comparison"]
    refined = _run_by_id(result, "refined_max_step_80s")
    path = output_dir / "09_tolerance_direction_and_step_control.png"
    fig, axes = plt.subplots(3, 1, figsize=(11, 11), sharex=True)
    axes[0].plot(
        comparison["_times"], comparison["_baseline_logs"], label="baseline tolerance"
    )
    axes[0].plot(
        comparison["_times"],
        comparison["_stricter_logs"],
        linestyle="--",
        label="strict tolerance",
    )
    axes[1].plot(
        comparison["_times"], comparison["_baseline_rates"], label="baseline tolerance"
    )
    axes[1].plot(
        comparison["_times"],
        comparison["_stricter_rates"],
        linestyle="--",
        label="strict tolerance",
    )
    axes[1].plot(
        refined["_cycle_end_times"],
        refined["_cycle_rates_a"],
        linestyle=":",
        label="half max_step",
    )
    axes[2].plot(
        comparison["_times"], comparison["_direction_difference"], color="tab:purple"
    )
    axes[2].axhline(
        MATERIAL_POLICY_DIRECTION_DIFFERENCE,
        color="red",
        linestyle=":",
        label="material diagnostic threshold",
    )
    axes[0].set(ylabel=r"$\ell_k$", title="Tolerance-policy cycle stretching")
    axes[1].set(ylabel=r"$\Lambda_N$ / s$^{-1}$", title="Tolerance and max-step refinement")
    axes[2].set(
        xlabel="cycle end time / s",
        ylabel="max component difference",
        title="Baseline-versus-strict reset direction divergence",
    )
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "10_local_angles_and_winding.png"
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    local = baseline["_reference_local_state"][:, :2]
    lifted = baseline["_reference_lifted_angles"]
    turns = (lifted - lifted[0]) / (2.0 * math.pi)
    axes[0].plot(baseline["_reference_time"], local[:, 0], label=r"local $\theta_1$")
    axes[0].plot(baseline["_reference_time"], local[:, 1], label=r"local $\theta_2$")
    axes[0].axhline(math.pi, color="black", linestyle=":")
    axes[0].axhline(-math.pi, color="black", linestyle=":")
    axes[1].plot(baseline["_reference_time"], turns[:, 0], label=r"$\theta_1$ turns")
    axes[1].plot(baseline["_reference_time"], turns[:, 1], label=r"$\theta_2$ turns")
    axes[0].set(ylabel="principal angle / rad", title="Bounded solver-facing angle diagnostics")
    axes[1].set(
        xlabel="time / s", ylabel="signed revolutions", title="Separately reconstructed winding history"
    )
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend()
    save_figure(fig, path)
    paths.append(path)
    return paths


def write_output_bundle(result: dict[str, Any], output_dir: Path, plots: bool) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    cycles_json_path = output_dir / "cycles.json"
    cycles_csv_path = output_dir / "cycles.csv"
    policy_csv_path = output_dir / "policy_comparison.csv"
    winding_csv_path = output_dir / "winding_history.csv"
    json_write(summary_path, result["summary"])
    write_cycles_json(cycles_json_path, result["runs"])
    write_cycles_csv(cycles_csv_path, result["runs"])
    if result["summary"].get("completed_duration_seconds") == 80.0:
        write_policy_comparison_csv(policy_csv_path, result)
        write_winding_history_csv(
            winding_csv_path, _run_by_id(result, "baseline_80s")
        )
    plot_paths = write_plots(output_dir, result) if plots else []
    manifest_path = output_dir / "manifest.json"
    data_paths = [summary_path, cycles_json_path, cycles_csv_path]
    if result["summary"].get("completed_duration_seconds") == 80.0:
        data_paths.extend((policy_csv_path, winding_csv_path))
    created = [manifest_path, *data_paths, *plot_paths]
    json_write(
        manifest_path,
        {
            "artifact": EXPERIMENT_NAME,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": result["summary"]["status"],
            "accepted": result["summary"]["accepted"],
            "created_files": [path.name for path in created],
            "contract": "development/chaos_content/experiments/foundations/005_renormalised_local_stretching/README.md",
            "reproduction_command": (
                "uv run python development/chaos_content/experiments/"
                "005_renormalised_local_stretching/renormalised_local_stretching.py "
                "--max-duration 80 --self-check --output-dir development/chaos_content/experiments/outputs/005/"
                "repaired --plots"
            ),
            "claim_boundary": result["summary"]["claim_boundary"],
            "notes": [
                "Accumulated renormalised finite-time stretching only; not an accepted Lyapunov exponent.",
                "Negative cycle contributions are retained.",
                "This is the repaired second numerical iteration; the original baseline bundle is preserved.",
                "The reference is physically uninterrupted and coordinate-rebased at cycle boundaries.",
                "Winding is accumulated separately and is not supplied to solve_ivp or Candidate A.",
                f"Every solve uses explicit max_step; baseline={BASELINE_MAX_STEP:.17g} s.",
                "Candidate B is measured along Candidate-A resets and does not define them.",
            ],
        },
    )
    return created


def assert_self_check(result: dict[str, Any]) -> None:
    summary = result["summary"]
    if summary["experiment"] != EXPERIMENT_NAME:
        raise AssertionError("Unexpected experiment identity.")
    if not result["runs"]:
        raise AssertionError("No renormalised run was produced.")
    for run in result["runs"]:
        requested = run["configuration"]["requested_cycle_count"]
        if run["accepted"] and run["valid_cycle_count"] != requested:
            raise AssertionError(f"Accepted run has incomplete cycles: {run['run_id']}.")
        if not run["accepted"] and run["valid_cycle_count"] >= requested:
            raise AssertionError(f"Rejected run lacks an explicit failed cycle: {run['run_id']}.")
        if (
            run["maximum_pre_reset_candidate_a_norm"] is not None
            and run["maximum_pre_reset_candidate_a_norm"] > LOCAL_DISTANCE_CEILING
            and "inside_empirical_local_ceiling" not in ",".join(run["issues"])
        ):
            raise AssertionError(f"Local ceiling exceeded in {run['run_id']}.")
    baseline_runs = [run for run in result["runs"] if run["run_id"].startswith("baseline_")]
    if not baseline_runs or not all(run["accepted"] for run in baseline_runs):
        raise AssertionError("A staged baseline run failed numerical validity.")
    if summary["completed_duration_seconds"] == 80.0 and result["convergence"] is None:
        raise AssertionError("Final-duration convergence audit is missing.")
    if "not an accepted maximal Lyapunov exponent" not in summary["claim_boundary"]:
        raise AssertionError("Claim boundary is incomplete.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-duration", type=float, choices=DURATION_STAGES, default=20.0)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args()
    if args.plots and args.output_dir is None:
        parser.error("--plots requires --output-dir")
    result = run_investigation(args.max_duration)
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
