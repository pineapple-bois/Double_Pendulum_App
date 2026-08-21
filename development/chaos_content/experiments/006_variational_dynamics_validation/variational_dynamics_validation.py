"""Validate direct variational dynamics against the established local shadow limit.

The adjacent README fixes the mathematical contract, numerical policies, and
acceptance thresholds. All tangent machinery remains experiment-local.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

import src.double_pendulum.models.lagrangian as lagrangian_module
from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_REFERENCE_SOLVER_POLICY,
    DoublePendulumLagrangian,
    SolverPolicy,
)


EXPERIMENT_NAME = "variational_dynamics_validation"
MODEL = "simple"
FORMULATION = "Euler-Lagrange variational dynamics"
STATE_ORDER = ("theta1", "theta2", "omega1", "omega2")
PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
BASE_STATE_DEGREES = np.array([179.0, 179.0, 0.0, 0.0])
BASE_STATE_RADIANS = np.deg2rad(BASE_STATE_DEGREES)
INITIAL_TANGENT_PHYSICAL = np.array([0.0, 1.0, 0.0, 0.0])

LC_BASELINE = 1.0
LOCAL_COMPARISON_END = 1.29
OUTPUT_INTERVAL = 0.01
CHART_REBASE_INTERVAL = 0.25
EPSILONS = (1.0e-4, 1.0e-5, 1.0e-6)
ENERGY_DRIFT_LIMIT = 1.0e-7

BASELINE_MAX_STEP = min(
    math.sqrt(LC_BASELINE / float(PARAMETERS[g])) / 32.0,
    CHART_REBASE_INTERVAL / 25.0,
)
REFINED_MAX_STEP = BASELINE_MAX_STEP / 2.0

STRICTER_POLICY = SolverPolicy(
    name="variational_dynamics_stricter_check",
    method="DOP853",
    rtol=1.0e-11,
    atol=1.0e-13,
    role="experiment-local tangent convergence comparison",
)

JACOBIAN_H_VALUES = tuple(10.0 ** -power for power in range(2, 9))
JACOBIAN_ASSESSMENT_H = 1.0e-6
MAX_JACOBIAN_DIRECTIONAL_RELATIVE_ERROR = 5.0e-5
MAX_PERIODICITY_ABSOLUTE_ERROR = 1.0e-9

MAX_LOCAL_LOG_ERROR_1E6 = 1.0e-2
MIN_LOCAL_DIRECTION_COSINE_1E6 = 0.999
MAX_POLICY_FINAL_RATE_RELATIVE_DIFFERENCE = 0.01
MAX_POLICY_LOG_GROWTH_ABSOLUTE_DIFFERENCE = 1.0e-3
MAX_POLICY_DIRECTION_COMPONENT_DIFFERENCE = 1.0e-3
MAX_POLICY_REFERENCE_DISTANCE = 1.0e-6
EXPERIMENT_005_REPAIRED_TOLERANCE_DISCREPANCY = 0.10767051889568337
MATERIAL_IMPROVEMENT_FACTOR = 5.0


def characteristic_time(length_metres: float = LC_BASELINE) -> float:
    return math.sqrt(float(length_metres) / float(PARAMETERS[g]))


def wrap_angle_difference(values: np.ndarray) -> np.ndarray:
    """Map finite angular differences deterministically to ``(-pi, pi]``."""

    values = np.asarray(values, dtype=float)
    wrapped = np.remainder(values + math.pi, 2.0 * math.pi) - math.pi
    return np.where(wrapped == -math.pi, math.pi, wrapped)


def canonicalize_state_angles(state: np.ndarray) -> np.ndarray:
    """Rebase only physical angular coordinates to ``(-pi, pi]``."""

    result = np.array(state, dtype=float, copy=True)
    if result.shape[-1] != 4:
        raise ValueError("Euler-Lagrange states must have four components.")
    result[..., :2] = wrap_angle_difference(result[..., :2])
    return result


def canonicalize_augmented_state(state: np.ndarray) -> np.ndarray:
    """Rebase reference angles while leaving tangent components untouched."""

    result = np.array(state, dtype=float, copy=True)
    if result.shape[-1] != 8:
        raise ValueError("Augmented reference/tangent states must have eight components.")
    result[..., :2] = wrap_angle_difference(result[..., :2])
    return result


def wrapped_el_difference(reference: np.ndarray, nearby: np.ndarray) -> np.ndarray:
    difference = np.asarray(nearby, dtype=float) - np.asarray(reference, dtype=float)
    result = np.array(difference, copy=True)
    result[..., :2] = wrap_angle_difference(result[..., :2])
    return result


def scaled_el_vector(
    physical_vector: np.ndarray, length_metres: float = LC_BASELINE
) -> np.ndarray:
    scaled = np.array(physical_vector, dtype=float, copy=True)
    scaled[..., 2:] *= characteristic_time(length_metres)
    return scaled


def candidate_a_norm(
    physical_vector: np.ndarray, length_metres: float = LC_BASELINE
) -> np.ndarray:
    return np.linalg.norm(scaled_el_vector(physical_vector, length_metres), axis=-1)


def normalized_scaled_direction(physical_vector: np.ndarray) -> np.ndarray:
    scaled = scaled_el_vector(physical_vector)
    magnitude = np.linalg.norm(scaled, axis=-1)
    if np.any(~np.isfinite(magnitude)) or np.any(magnitude <= 0.0):
        raise ValueError("Direction requires positive finite Candidate-A magnitudes.")
    return scaled / np.expand_dims(magnitude, axis=-1)


def direction_cosine(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    first_direction = normalized_scaled_direction(first)
    second_direction = normalized_scaled_direction(second)
    return np.sum(first_direction * second_direction, axis=-1)


def simple_energy(state: np.ndarray) -> np.ndarray:
    theta1, theta2, omega1, omega2 = np.moveaxis(
        np.asarray(state, dtype=float), -1, 0
    )
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


def energy_scale() -> float:
    return float(PARAMETERS[g]) * (
        (float(PARAMETERS[m1]) + float(PARAMETERS[m2])) * float(PARAMETERS[l1])
        + float(PARAMETERS[m2]) * float(PARAMETERS[l2])
    )


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


def policy_dict(policy: SolverPolicy) -> dict[str, Any]:
    return {
        "name": policy.name,
        "method": policy.method,
        "rtol": policy.rtol,
        "atol": policy.atol,
        "role": policy.role,
    }


def relative_difference(reference: float, comparison: float) -> float:
    if not np.isfinite(reference) or not np.isfinite(comparison) or reference == 0.0:
        return math.inf
    return float(abs(comparison - reference) / abs(reference))


class VariationalDynamics:
    """Production-derived EL flow plus its exact symbolic state Jacobian."""

    def __init__(self) -> None:
        _, equation1, equation2, equation3, equation4 = (
            DoublePendulumLagrangian._compute_and_cache_equations(MODEL)
        )
        self.flow_expressions = tuple(
            expression.subs(PARAMETERS)
            for expression in (equation1, equation2, equation3, equation4)
        )
        self.state_symbols = (
            lagrangian_module.theta1,
            lagrangian_module.theta2,
            lagrangian_module.omega1,
            lagrangian_module.omega2,
        )
        self.time_symbol = lagrangian_module.t
        self.jacobian_expression = sp.Matrix(self.flow_expressions).jacobian(
            self.state_symbols
        )
        arguments = (*self.state_symbols, self.time_symbol)
        self._flow_function = sp.lambdify(arguments, self.flow_expressions, "numpy")
        self._jacobian_function = sp.lambdify(
            arguments, self.jacobian_expression, "numpy"
        )

    def flow(self, state: np.ndarray, time_value: float) -> np.ndarray:
        values = (*np.asarray(state, dtype=float), float(time_value))
        return np.asarray(self._flow_function(*values), dtype=float).reshape(4)

    def jacobian(self, state: np.ndarray, time_value: float) -> np.ndarray:
        values = (*np.asarray(state, dtype=float), float(time_value))
        return np.asarray(self._jacobian_function(*values), dtype=float).reshape(4, 4)

    def augmented_rhs(self, time_value: float, augmented: np.ndarray) -> np.ndarray:
        augmented = np.asarray(augmented, dtype=float)
        reference = augmented[:4]
        tangent = augmented[4:]
        return np.concatenate(
            (self.flow(reference, time_value), self.jacobian(reference, time_value) @ tangent)
        )


def output_time_grid() -> np.ndarray:
    sample_count = int(round(LOCAL_COMPARISON_END / OUTPUT_INTERVAL)) + 1
    return np.linspace(0.0, LOCAL_COMPARISON_END, sample_count)


def segment_boundaries() -> np.ndarray:
    full_segments = int(math.floor(LOCAL_COMPARISON_END / CHART_REBASE_INTERVAL))
    boundaries = [index * CHART_REBASE_INTERVAL for index in range(full_segments + 1)]
    if not math.isclose(boundaries[-1], LOCAL_COMPARISON_END):
        boundaries.append(LOCAL_COMPARISON_END)
    return np.asarray(boundaries, dtype=float)


def solve_one_segment(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    initial_state: np.ndarray,
    requested_time: np.ndarray,
    policy: SolverPolicy,
    *,
    max_step: float,
) -> dict[str, Any]:
    requested_time = np.asarray(requested_time, dtype=float)
    if len(requested_time) < 2:
        raise ValueError("A segment requires at least two requested times.")
    if not np.isfinite(max_step) or max_step <= 0.0:
        raise ValueError("max_step must be positive and finite.")
    result = solve_ivp(
        rhs,
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
        "expected_state_shape": state.shape
        == (len(requested_time), len(initial_state)),
        "finite_state": bool(np.all(np.isfinite(state))),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
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
            "max_step_seconds": float(max_step),
        },
    }


def solve_piecewise(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    initial_state: np.ndarray,
    policy: SolverPolicy,
    *,
    max_step: float,
    augmented: bool,
) -> dict[str, Any]:
    global_time = output_time_grid()
    states: list[np.ndarray] = []
    times: list[np.ndarray] = []
    segment_status: list[dict[str, Any]] = []
    current = np.array(initial_state, dtype=float, copy=True)

    boundaries = segment_boundaries()
    for segment_index, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        mask = (global_time >= start - 1.0e-14) & (global_time <= end + 1.0e-14)
        requested = global_time[mask]
        if requested[0] != start:
            requested = np.insert(requested, 0, start)
        if requested[-1] != end:
            requested = np.append(requested, end)
        segment = solve_one_segment(
            rhs, current, requested, policy, max_step=max_step
        )
        segment_status.append(segment["solver_status"] | {"accepted": segment["accepted"]})
        if not segment["accepted"]:
            raise RuntimeError(f"Segment {segment_index} failed: {segment['checks']}")

        segment_time = segment["time"]
        segment_state = segment["state"]
        current = (
            canonicalize_augmented_state(segment_state[-1])
            if augmented
            else canonicalize_state_angles(segment_state[-1])
        )
        stored_state = (
            canonicalize_augmented_state(segment_state)
            if augmented
            else canonicalize_state_angles(segment_state)
        )
        if segment_index:
            segment_time = segment_time[1:]
            stored_state = stored_state[1:]
        times.append(segment_time)
        states.append(stored_state)

    combined_time = np.concatenate(times)
    combined_state = np.concatenate(states)
    if not np.allclose(combined_time, global_time, rtol=0.0, atol=1.0e-13):
        raise RuntimeError("Piecewise integration did not reproduce the requested global grid.")
    return {
        "time": combined_time,
        "state": combined_state,
        "segment_solver_status": segment_status,
        "solver_statistics": {
            "segments": len(segment_status),
            "nfev": int(sum(item["nfev"] for item in segment_status)),
            "njev": int(sum(item["njev"] for item in segment_status)),
            "nlu": int(sum(item["nlu"] for item in segment_status)),
            "max_step_seconds": float(max_step),
            "all_segments_accepted": all(item["accepted"] for item in segment_status),
        },
    }


def solve_variational_run(
    dynamics: VariationalDynamics,
    run_id: str,
    policy: SolverPolicy,
    max_step: float,
) -> dict[str, Any]:
    initial = np.concatenate((BASE_STATE_RADIANS, INITIAL_TANGENT_PHYSICAL))
    solution = solve_piecewise(
        dynamics.augmented_rhs,
        initial,
        policy,
        max_step=max_step,
        augmented=True,
    )
    state = solution["state"]
    reference = state[:, :4]
    tangent = state[:, 4:]
    tangent_norm = candidate_a_norm(tangent)
    tangent_direction = normalized_scaled_direction(tangent)
    log_growth = np.log(tangent_norm / tangent_norm[0])
    finite_time_rate = np.full_like(log_growth, np.nan)
    finite_time_rate[1:] = log_growth[1:] / solution["time"][1:]
    energy = simple_energy(reference)
    energy_drift = np.abs(energy - energy[0]) / energy_scale()
    accepted = bool(
        solution["solver_statistics"]["all_segments_accepted"]
        and np.all(np.isfinite(reference))
        and np.all(np.isfinite(tangent))
        and np.all(tangent_norm > 0.0)
        and np.max(energy_drift) <= ENERGY_DRIFT_LIMIT
    )
    return {
        "run_id": run_id,
        "accepted": accepted,
        "policy": policy_dict(policy),
        "max_step_seconds": max_step,
        "solver_statistics": solution["solver_statistics"],
        "segment_solver_status": solution["segment_solver_status"],
        "maximum_normalized_reference_energy_drift": float(np.max(energy_drift)),
        "initial_candidate_a_tangent_norm": float(tangent_norm[0]),
        "final_candidate_a_tangent_norm": float(tangent_norm[-1]),
        "final_log_growth": float(log_growth[-1]),
        "final_finite_time_rate_per_second": float(finite_time_rate[-1]),
        "_time": solution["time"],
        "_reference": reference,
        "_tangent": tangent,
        "_tangent_norm": tangent_norm,
        "_tangent_direction": tangent_direction,
        "_log_growth": log_growth,
        "_finite_time_rate": finite_time_rate,
        "_reference_energy_drift": energy_drift,
    }


def solve_finite_shadow(
    dynamics: VariationalDynamics,
    epsilon: float,
    policy: SolverPolicy,
    max_step: float,
) -> dict[str, Any]:
    initial = np.array(BASE_STATE_RADIANS, copy=True)
    initial[1] += epsilon
    solution = solve_piecewise(
        lambda time_value, state: dynamics.flow(state, time_value),
        initial,
        policy,
        max_step=max_step,
        augmented=False,
    )
    energy = simple_energy(solution["state"])
    energy_drift = np.abs(energy - energy[0]) / energy_scale()
    return {
        "epsilon": epsilon,
        "accepted": bool(
            solution["solver_statistics"]["all_segments_accepted"]
            and np.all(np.isfinite(solution["state"]))
            and np.max(energy_drift) <= ENERGY_DRIFT_LIMIT
        ),
        "solver_statistics": solution["solver_statistics"],
        "maximum_normalized_energy_drift": float(np.max(energy_drift)),
        "_time": solution["time"],
        "_state": solution["state"],
        "_energy_drift": energy_drift,
    }


def compare_policy_runs(
    baseline: dict[str, Any], comparison: dict[str, Any]
) -> dict[str, Any]:
    if not np.array_equal(baseline["_time"], comparison["_time"]):
        raise ValueError("Policy runs must share the same requested time grid.")
    reference_difference = wrapped_el_difference(
        baseline["_reference"], comparison["_reference"]
    )
    reference_distance = candidate_a_norm(reference_difference)
    log_difference = np.abs(baseline["_log_growth"] - comparison["_log_growth"])
    direction_difference = np.max(
        np.abs(baseline["_tangent_direction"] - comparison["_tangent_direction"]),
        axis=1,
    )
    signed_cosine = np.sum(
        baseline["_tangent_direction"] * comparison["_tangent_direction"], axis=1
    )
    norm_relative_difference = np.abs(
        comparison["_tangent_norm"] - baseline["_tangent_norm"]
    ) / baseline["_tangent_norm"]
    final_rate_relative_difference = relative_difference(
        baseline["final_finite_time_rate_per_second"],
        comparison["final_finite_time_rate_per_second"],
    )
    checks = {
        "final_rate_relative_difference_within_1_percent": bool(
            final_rate_relative_difference
            <= MAX_POLICY_FINAL_RATE_RELATIVE_DIFFERENCE
        ),
        "maximum_log_growth_difference_within_1e-3": bool(
            np.max(log_difference) <= MAX_POLICY_LOG_GROWTH_ABSOLUTE_DIFFERENCE
        ),
        "maximum_direction_component_difference_within_1e-3": bool(
            np.max(direction_difference)
            <= MAX_POLICY_DIRECTION_COMPONENT_DIFFERENCE
        ),
        "maximum_reference_distance_within_1e-6": bool(
            np.max(reference_distance) <= MAX_POLICY_REFERENCE_DISTANCE
        ),
    }
    return {
        "baseline_run_id": baseline["run_id"],
        "comparison_run_id": comparison["run_id"],
        "accepted": all(checks.values()),
        "checks": checks,
        "final_rate_relative_difference": final_rate_relative_difference,
        "maximum_absolute_log_growth_difference": float(np.max(log_difference)),
        "maximum_direction_component_difference": float(np.max(direction_difference)),
        "minimum_signed_direction_cosine": float(np.min(signed_cosine)),
        "maximum_tangent_norm_relative_difference": float(
            np.max(norm_relative_difference)
        ),
        "maximum_reference_candidate_a_distance": float(np.max(reference_distance)),
        "_time": baseline["_time"],
        "_reference_distance": reference_distance,
        "_log_difference": log_difference,
        "_direction_difference": direction_difference,
        "_signed_direction_cosine": signed_cosine,
        "_norm_relative_difference": norm_relative_difference,
    }


def compare_finite_shadows(
    baseline: dict[str, Any], shadows: list[dict[str, Any]]
) -> dict[str, Any]:
    comparisons: list[dict[str, Any]] = []
    tangent_scaled = scaled_el_vector(baseline["_tangent"])
    tangent_norm = baseline["_tangent_norm"]
    tangent_direction = baseline["_tangent_direction"]
    tangent_log_growth = baseline["_log_growth"]

    for shadow in shadows:
        epsilon = shadow["epsilon"]
        difference = wrapped_el_difference(baseline["_reference"], shadow["_state"])
        normalized_scaled = scaled_el_vector(difference) / epsilon
        normalized_physical = np.array(difference, copy=True) / epsilon
        finite_norm = np.linalg.norm(normalized_scaled, axis=1)
        finite_direction = normalized_scaled / finite_norm[:, None]
        finite_log_growth = np.log(finite_norm / finite_norm[0])
        signed_cosine = np.sum(finite_direction * tangent_direction, axis=1)
        log_error = finite_log_growth - tangent_log_growth
        direction_mismatch = 1.0 - signed_cosine
        comparisons.append(
            {
                "epsilon": epsilon,
                "accepted_shadow_run": shadow["accepted"],
                "rms_log_norm_error": float(np.sqrt(np.mean(log_error**2))),
                "maximum_absolute_log_norm_error": float(np.max(np.abs(log_error))),
                "endpoint_absolute_log_norm_error": float(abs(log_error[-1])),
                "rms_direction_mismatch": float(
                    np.sqrt(np.mean(direction_mismatch**2))
                ),
                "minimum_signed_direction_cosine": float(np.min(signed_cosine)),
                "endpoint_signed_direction_cosine": float(signed_cosine[-1]),
                "_normalized_physical": normalized_physical,
                "_normalized_scaled": normalized_scaled,
                "_finite_norm": finite_norm,
                "_finite_direction": finite_direction,
                "_finite_log_growth": finite_log_growth,
                "_signed_direction_cosine": signed_cosine,
                "_log_error": log_error,
            }
        )

    rms_log = [item["rms_log_norm_error"] for item in comparisons]
    rms_direction = [item["rms_direction_mismatch"] for item in comparisons]
    smallest = comparisons[-1]
    checks = {
        "all_finite_shadow_runs_valid": all(
            item["accepted_shadow_run"] for item in comparisons
        ),
        "rms_log_error_decreases_with_epsilon": bool(
            rms_log[0] > rms_log[1] > rms_log[2]
        ),
        "rms_direction_mismatch_decreases_with_epsilon": bool(
            rms_direction[0] > rms_direction[1] > rms_direction[2]
        ),
        "epsilon_1e-6_max_log_error_within_0.01": bool(
            smallest["maximum_absolute_log_norm_error"] <= MAX_LOCAL_LOG_ERROR_1E6
        ),
        "epsilon_1e-6_min_direction_cosine_at_least_0.999": bool(
            smallest["minimum_signed_direction_cosine"]
            >= MIN_LOCAL_DIRECTION_COSINE_1E6
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "comparisons": comparisons,
        "_time": baseline["_time"],
        "_tangent_scaled": tangent_scaled,
        "_tangent_norm": tangent_norm,
    }


def representative_jacobian_states(baseline: dict[str, Any]) -> list[dict[str, Any]]:
    time = baseline["_time"]
    reference = baseline["_reference"]
    sampled: list[dict[str, Any]] = [
        {"state_id": "baseline_initial", "time": 0.0, "state": reference[0]},
    ]
    for sample_time in (0.25, 0.75, 1.25):
        index = int(np.argmin(np.abs(time - sample_time)))
        sampled.append(
            {
                "state_id": f"baseline_t_{sample_time:g}",
                "time": float(time[index]),
                "state": reference[index],
            }
        )
    sampled.extend(
        (
            {
                "state_id": "branch_nontrivial_velocity",
                "time": 0.37,
                "state": np.array(
                    [math.pi - 1.0e-8, -math.pi + 2.0e-8, 2.0, -3.0]
                ),
            },
            {
                "state_id": "mixed_nontrivial_velocity",
                "time": 0.61,
                "state": np.array([-2.2, 1.7, -4.0, 3.0]),
            },
        )
    )
    return sampled


def validate_jacobian(
    dynamics: VariationalDynamics, baseline: dict[str, Any]
) -> dict[str, Any]:
    directions = (
        np.array([1.0, 0.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 0.0, 1.0]),
        np.array([0.3, -0.4, 0.5, -0.7]),
    )
    directions = tuple(direction / np.linalg.norm(direction) for direction in directions)
    records: list[dict[str, Any]] = []
    states = representative_jacobian_states(baseline)
    for state_record in states:
        state = np.asarray(state_record["state"], dtype=float)
        time_value = float(state_record["time"])
        jacobian = dynamics.jacobian(state, time_value)
        flow = dynamics.flow(state, time_value)
        for direction_index, direction in enumerate(directions):
            expected = jacobian @ direction
            for h_value in JACOBIAN_H_VALUES:
                finite_difference = (
                    dynamics.flow(state + h_value * direction, time_value) - flow
                ) / h_value
                absolute_error = float(np.linalg.norm(finite_difference - expected))
                relative_error = absolute_error / max(float(np.linalg.norm(expected)), 1.0e-12)
                records.append(
                    {
                        "state_id": state_record["state_id"],
                        "time_seconds": time_value,
                        "direction_index": direction_index,
                        "h": h_value,
                        "absolute_error": absolute_error,
                        "relative_error": relative_error,
                    }
                )

    assessment = [
        record
        for record in records
        if math.isclose(record["h"], JACOBIAN_ASSESSMENT_H)
    ]
    max_relative = max(record["relative_error"] for record in assessment)

    shifts = ((1, -1), (-7, 4), (23, -19))
    periodicity_records: list[dict[str, Any]] = []
    for state_record in states:
        state = np.asarray(state_record["state"], dtype=float)
        time_value = float(state_record["time"])
        expected_flow = dynamics.flow(state, time_value)
        expected_jacobian = dynamics.jacobian(state, time_value)
        expected_observables = cartesian_full_state(state)
        expected_energy = float(simple_energy(state))
        for shift1, shift2 in shifts:
            shifted = np.array(state, copy=True)
            shifted[:2] += 2.0 * math.pi * np.array([shift1, shift2])
            periodicity_records.append(
                {
                    "state_id": state_record["state_id"],
                    "theta1_turn_shift": shift1,
                    "theta2_turn_shift": shift2,
                    "flow_max_absolute_error": float(
                        np.max(np.abs(dynamics.flow(shifted, time_value) - expected_flow))
                    ),
                    "jacobian_max_absolute_error": float(
                        np.max(
                            np.abs(
                                dynamics.jacobian(shifted, time_value)
                                - expected_jacobian
                            )
                        )
                    ),
                    "observable_max_absolute_error": float(
                        np.max(np.abs(cartesian_full_state(shifted) - expected_observables))
                    ),
                    "energy_absolute_error": float(
                        abs(float(simple_energy(shifted)) - expected_energy)
                    ),
                }
            )
    max_flow_periodicity = max(
        record["flow_max_absolute_error"] for record in periodicity_records
    )
    max_jacobian_periodicity = max(
        record["jacobian_max_absolute_error"] for record in periodicity_records
    )
    max_observable_periodicity = max(
        record["observable_max_absolute_error"] for record in periodicity_records
    )
    max_energy_periodicity = max(
        record["energy_absolute_error"] for record in periodicity_records
    )
    checks = {
        "directional_finite_difference_error_within_limit": bool(
            max_relative <= MAX_JACOBIAN_DIRECTIONAL_RELATIVE_ERROR
        ),
        "flow_periodicity_within_limit": bool(
            max_flow_periodicity <= MAX_PERIODICITY_ABSOLUTE_ERROR
        ),
        "jacobian_periodicity_within_limit": bool(
            max_jacobian_periodicity <= MAX_PERIODICITY_ABSOLUTE_ERROR
        ),
        "physical_observable_periodicity_within_limit": bool(
            max_observable_periodicity <= MAX_PERIODICITY_ABSOLUTE_ERROR
        ),
        "energy_periodicity_within_limit": bool(
            max_energy_periodicity <= MAX_PERIODICITY_ABSOLUTE_ERROR
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "construction_method": (
            "SymPy differentiation of the parameter-substituted first-order expressions "
            "returned by DoublePendulumLagrangian._compute_and_cache_equations('simple')"
        ),
        "assessment_h": JACOBIAN_ASSESSMENT_H,
        "maximum_assessment_relative_error": max_relative,
        "maximum_flow_periodicity_absolute_error": max_flow_periodicity,
        "maximum_jacobian_periodicity_absolute_error": max_jacobian_periodicity,
        "maximum_observable_periodicity_absolute_error": max_observable_periodicity,
        "maximum_energy_periodicity_absolute_error": max_energy_periodicity,
        "tested_state_count": len(states),
        "tested_direction_count": len(directions),
        "h_values": list(JACOBIAN_H_VALUES),
        "records": records,
        "periodicity_records": periodicity_records,
    }


def public_variational_run(run: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in run.items() if not key.startswith("_")}


def public_finite_comparison(comparison: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in comparison.items() if not key.startswith("_")}


def public_policy_comparison(comparison: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in comparison.items() if not key.startswith("_")}


def run_investigation() -> dict[str, Any]:
    dynamics = VariationalDynamics()
    baseline = solve_variational_run(
        dynamics,
        "baseline",
        SIMPLE_REFERENCE_SOLVER_POLICY,
        BASELINE_MAX_STEP,
    )
    stricter = solve_variational_run(
        dynamics, "stricter_tolerance", STRICTER_POLICY, BASELINE_MAX_STEP
    )
    refined = solve_variational_run(
        dynamics,
        "half_max_step",
        SIMPLE_REFERENCE_SOLVER_POLICY,
        REFINED_MAX_STEP,
    )
    shadows = [
        solve_finite_shadow(
            dynamics, epsilon, SIMPLE_REFERENCE_SOLVER_POLICY, BASELINE_MAX_STEP
        )
        for epsilon in EPSILONS
    ]

    jacobian_validation = validate_jacobian(dynamics, baseline)
    finite_shadow_comparison = compare_finite_shadows(baseline, shadows)
    tolerance_comparison = compare_policy_runs(baseline, stricter)
    max_step_comparison = compare_policy_runs(baseline, refined)
    tolerance_materially_improved = bool(
        tolerance_comparison["final_rate_relative_difference"]
        < EXPERIMENT_005_REPAIRED_TOLERANCE_DISCREPANCY
        / MATERIAL_IMPROVEMENT_FACTOR
    )
    checks = {
        "jacobian_validated": jacobian_validation["accepted"],
        "finite_shadow_local_limit_validated": finite_shadow_comparison["accepted"],
        "baseline_numerically_valid": baseline["accepted"],
        "strict_numerically_valid": stricter["accepted"],
        "half_max_step_numerically_valid": refined["accepted"],
        "tolerance_comparison_accepted": tolerance_comparison["accepted"],
        "max_step_comparison_accepted": max_step_comparison["accepted"],
        "tolerance_materially_better_than_repaired_experiment_005": (
            tolerance_materially_improved
        ),
    }
    accepted = all(checks.values())
    if not jacobian_validation["accepted"]:
        status = "rejected_jacobian_not_validated"
        outcome = "Jacobian validation failed"
        strongest_claim = "The tangent formulation is not accepted because its Jacobian did not pass independent validation."
    elif not finite_shadow_comparison["accepted"]:
        status = "rejected_local_shadow_limit_not_reproduced"
        outcome = "Finite-shadow local limit not reproduced"
        strongest_claim = "The validated Jacobian did not reproduce the declared finite-shadow local-limit checks."
    elif not tolerance_comparison["accepted"] or not tolerance_materially_improved:
        status = "rejected_tangent_tolerance_convergence_unresolved"
        outcome = "Tangent tolerance convergence unresolved"
        strongest_claim = "Local tangent evolution is validated, but it remains numerically unresolved across tolerance policies."
    elif not max_step_comparison["accepted"]:
        status = "rejected_tangent_step_refinement_unresolved"
        outcome = "Tangent max-step convergence unresolved"
        strongest_claim = "Local tangent evolution is validated, but it remains numerically unresolved under max-step refinement."
    elif not accepted:
        status = "rejected_reference_or_solver_validity"
        outcome = "Reference or solver validity failed"
        strongest_claim = "The tangent comparison is not accepted because a declared numerical-validity check failed."
    else:
        status = "accepted_for_variational_local_dynamics_validation"
        outcome = "Accepted for the limited formulation-validation claim"
        strongest_claim = (
            "Direct variational evolution of the Euler-Lagrange tangent vector reproduces "
            "the finite-shadow local dynamics in the small-perturbation limit and is "
            "materially more numerically stable under solver refinement than repeated "
            "finite-shadow subtraction."
        )

    summary = {
        "experiment": EXPERIMENT_NAME,
        "status": status,
        "outcome": outcome,
        "accepted": accepted,
        "question": (
            "Does direct tangent-vector evolution reproduce the established short-time "
            "local growth while materially improving tolerance convergence under the same reference case?"
        ),
        "configuration": {
            "model": MODEL,
            "formulation": FORMULATION,
            "state_order": list(STATE_ORDER),
            "parameters_si": {str(key): float(value) for key, value in PARAMETERS.items()},
            "base_initial_state_degrees": BASE_STATE_DEGREES.tolist(),
            "initial_tangent_physical": INITIAL_TANGENT_PHYSICAL.tolist(),
            "initial_tangent_candidate_a_norm": float(
                candidate_a_norm(INITIAL_TANGENT_PHYSICAL)
            ),
            "characteristic_length_metres": LC_BASELINE,
            "characteristic_time_seconds": characteristic_time(),
            "candidate_a_scaled_vector": (
                "(delta_theta1,delta_theta2,Tc*delta_omega1,Tc*delta_omega2)"
            ),
            "local_comparison_end_seconds": LOCAL_COMPARISON_END,
            "output_interval_seconds": OUTPUT_INTERVAL,
            "finite_shadow_epsilons": list(EPSILONS),
            "angular_chart": "physical reference/shadow angles rebased to (-pi, pi] every 0.25 s",
            "tangent_angle_semantics": (
                "infinitesimal coordinate-basis components; never wrapped or used as winding history"
            ),
            "winding_history": "not a solver or tangent coordinate; not needed in the 1.29 s validation window",
            "baseline_solver_policy": policy_dict(SIMPLE_REFERENCE_SOLVER_POLICY),
            "stricter_solver_policy": policy_dict(STRICTER_POLICY),
            "baseline_max_step_seconds": BASELINE_MAX_STEP,
            "baseline_max_step_derivation": "min(Tc/32, 0.25/25)",
            "refined_max_step_seconds": REFINED_MAX_STEP,
            "solver_restarts": "at deterministic 0.25 s angular-chart boundaries",
            "long_time_tangent_renormalisation": False,
        },
        "thresholds": {
            "jacobian_assessment_h": JACOBIAN_ASSESSMENT_H,
            "jacobian_directional_relative_error": MAX_JACOBIAN_DIRECTIONAL_RELATIVE_ERROR,
            "periodicity_absolute_error": MAX_PERIODICITY_ABSOLUTE_ERROR,
            "epsilon_1e-6_max_log_error": MAX_LOCAL_LOG_ERROR_1E6,
            "epsilon_1e-6_min_direction_cosine": MIN_LOCAL_DIRECTION_COSINE_1E6,
            "policy_final_rate_relative_difference": MAX_POLICY_FINAL_RATE_RELATIVE_DIFFERENCE,
            "policy_log_growth_absolute_difference": MAX_POLICY_LOG_GROWTH_ABSOLUTE_DIFFERENCE,
            "policy_direction_component_difference": MAX_POLICY_DIRECTION_COMPONENT_DIFFERENCE,
            "policy_reference_candidate_a_distance": MAX_POLICY_REFERENCE_DISTANCE,
            "energy_drift": ENERGY_DRIFT_LIMIT,
            "material_improvement_over_experiment_005_factor": MATERIAL_IMPROVEMENT_FACTOR,
            "status": "predeclared in Experiment 006 README before numerical interpretation",
        },
        "jacobian_validation": jacobian_validation,
        "finite_shadow_comparison": {
            "accepted": finite_shadow_comparison["accepted"],
            "checks": finite_shadow_comparison["checks"],
            "comparisons": [
                public_finite_comparison(item)
                for item in finite_shadow_comparison["comparisons"]
            ],
        },
        "variational_runs": [
            public_variational_run(run) for run in (baseline, stricter, refined)
        ],
        "tolerance_comparison": public_policy_comparison(tolerance_comparison),
        "max_step_comparison": public_policy_comparison(max_step_comparison),
        "comparison_to_repaired_experiment_005": {
            "repaired_finite_shadow_tolerance_relative_difference": (
                EXPERIMENT_005_REPAIRED_TOLERANCE_DISCREPANCY
            ),
            "tangent_tolerance_relative_difference": tolerance_comparison[
                "final_rate_relative_difference"
            ],
            "material_improvement_factor_required": MATERIAL_IMPROVEMENT_FACTOR,
            "materially_improved": tolerance_materially_improved,
        },
        "acceptance_checks": checks,
        "strongest_claim": strongest_claim,
        "claim_boundary": (
            "This validates short-time direct variational evolution only. The descriptive "
            "finite-time tangent rate is not a maximal Lyapunov exponent. No common "
            "exponential interval, long-time convergence, tangent renormalisation, Lyapunov "
            "spectrum, coordinate invariance, Hamiltonian comparison, or chaos classification is established."
        ),
        "next_experiment_earned": (
            "a dedicated long-time tangent-Lyapunov convergence study" if accepted else None
        ),
    }
    return {
        "summary": summary,
        "baseline": baseline,
        "stricter": stricter,
        "refined": refined,
        "shadows": shadows,
        "jacobian_validation": jacobian_validation,
        "finite_shadow_comparison": finite_shadow_comparison,
        "tolerance_comparison": tolerance_comparison,
        "max_step_comparison": max_step_comparison,
    }


def json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_tangent_timeseries(path: Path, result: dict[str, Any]) -> None:
    labels = ("baseline", "stricter", "refined")
    runs = (result["baseline"], result["stricter"], result["refined"])
    fields = ["time_seconds"]
    for label in labels:
        fields.extend(
            [
                *[f"{label}_reference_{name}" for name in STATE_ORDER],
                *[f"{label}_tangent_{name}" for name in STATE_ORDER],
                *[f"{label}_scaled_tangent_{name}" for name in STATE_ORDER],
                *[f"{label}_direction_{name}" for name in STATE_ORDER],
                f"{label}_candidate_a_norm",
                f"{label}_log_growth",
                f"{label}_finite_time_rate_per_s",
                f"{label}_reference_energy_drift",
            ]
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, time_value in enumerate(runs[0]["_time"]):
            row: dict[str, Any] = {"time_seconds": time_value}
            for label, run in zip(labels, runs):
                for name, value in zip(STATE_ORDER, run["_reference"][index]):
                    row[f"{label}_reference_{name}"] = value
                for name, value in zip(STATE_ORDER, run["_tangent"][index]):
                    row[f"{label}_tangent_{name}"] = value
                for name, value in zip(
                    STATE_ORDER, scaled_el_vector(run["_tangent"][index])
                ):
                    row[f"{label}_scaled_tangent_{name}"] = value
                for name, value in zip(STATE_ORDER, run["_tangent_direction"][index]):
                    row[f"{label}_direction_{name}"] = value
                row[f"{label}_candidate_a_norm"] = run["_tangent_norm"][index]
                row[f"{label}_log_growth"] = run["_log_growth"][index]
                row[f"{label}_finite_time_rate_per_s"] = (
                    "" if index == 0 else run["_finite_time_rate"][index]
                )
                row[f"{label}_reference_energy_drift"] = run[
                    "_reference_energy_drift"
                ][index]
            writer.writerow(row)


def write_finite_shadow_timeseries(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "epsilon",
        "time_seconds",
        *[f"shadow_{name}" for name in STATE_ORDER],
        *[f"normalized_scaled_difference_{name}" for name in STATE_ORDER],
        "normalized_candidate_a_norm",
        "log_growth",
        "signed_direction_cosine_to_tangent",
        "log_growth_error_to_tangent",
        "shadow_energy_drift",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        comparisons = result["finite_shadow_comparison"]["comparisons"]
        for shadow, comparison in zip(result["shadows"], comparisons):
            for index, time_value in enumerate(shadow["_time"]):
                row: dict[str, Any] = {
                    "epsilon": shadow["epsilon"],
                    "time_seconds": time_value,
                    "normalized_candidate_a_norm": comparison["_finite_norm"][index],
                    "log_growth": comparison["_finite_log_growth"][index],
                    "signed_direction_cosine_to_tangent": comparison[
                        "_signed_direction_cosine"
                    ][index],
                    "log_growth_error_to_tangent": comparison["_log_error"][index],
                    "shadow_energy_drift": shadow["_energy_drift"][index],
                }
                for name, value in zip(STATE_ORDER, shadow["_state"][index]):
                    row[f"shadow_{name}"] = value
                for name, value in zip(
                    STATE_ORDER, comparison["_normalized_scaled"][index]
                ):
                    row[f"normalized_scaled_difference_{name}"] = value
                writer.writerow(row)


def write_jacobian_validation(path: Path, validation: dict[str, Any]) -> None:
    fields = [
        "state_id",
        "time_seconds",
        "direction_index",
        "h",
        "absolute_error",
        "relative_error",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(validation["records"])


def write_policy_comparison(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "comparison",
        "time_seconds",
        "reference_candidate_a_distance",
        "absolute_log_growth_difference",
        "direction_max_component_difference",
        "signed_direction_cosine",
        "tangent_norm_relative_difference",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for comparison in (
            result["tolerance_comparison"],
            result["max_step_comparison"],
        ):
            label = comparison["comparison_run_id"]
            for index, time_value in enumerate(comparison["_time"]):
                writer.writerow(
                    {
                        "comparison": label,
                        "time_seconds": time_value,
                        "reference_candidate_a_distance": comparison[
                            "_reference_distance"
                        ][index],
                        "absolute_log_growth_difference": comparison[
                            "_log_difference"
                        ][index],
                        "direction_max_component_difference": comparison[
                            "_direction_difference"
                        ][index],
                        "signed_direction_cosine": comparison[
                            "_signed_direction_cosine"
                        ][index],
                        "tangent_norm_relative_difference": comparison[
                            "_norm_relative_difference"
                        ][index],
                    }
                )


def load_pyplot():
    import matplotlib.pyplot as plt

    return plt


def save_figure(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    load_pyplot().close(fig)


def write_plots(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    plt = load_pyplot()
    paths: list[Path] = []

    path = output_dir / "01_jacobian_directional_finite_difference.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    records = result["jacobian_validation"]["records"]
    for state_id in sorted({record["state_id"] for record in records}):
        h_values = sorted({record["h"] for record in records})
        maxima = [
            max(
                record["relative_error"]
                for record in records
                if record["state_id"] == state_id and record["h"] == h_value
            )
            for h_value in h_values
        ]
        axis.loglog(h_values, maxima, marker="o", label=state_id)
    axis.axvline(JACOBIAN_ASSESSMENT_H, color="black", linestyle=":", label="assessment h")
    axis.axhline(
        MAX_JACOBIAN_DIRECTIONAL_RELATIVE_ERROR,
        color="red",
        linestyle="--",
        label="acceptance limit",
    )
    axis.set(xlabel="forward-difference h", ylabel="maximum relative error", title="Independent directional validation of J(x)v")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=7)
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "02_tangent_vs_finite_shadow_norm.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    time = result["baseline"]["_time"]
    axis.semilogy(time, result["baseline"]["_tangent_norm"], color="black", linewidth=2, label="direct tangent")
    for comparison in result["finite_shadow_comparison"]["comparisons"]:
        axis.semilogy(time, comparison["_finite_norm"], label=f"finite shadow {comparison['epsilon']:.0e}")
    axis.set(xlabel="time / s", ylabel="normalized Candidate-A norm", title="Local norm growth approaches direct tangent evolution")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "03_tangent_vs_finite_shadow_direction.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for comparison in result["finite_shadow_comparison"]["comparisons"]:
        axis.plot(time, comparison["_signed_direction_cosine"], label=f"finite shadow {comparison['epsilon']:.0e}")
    axis.axhline(MIN_LOCAL_DIRECTION_COSINE_1E6, color="red", linestyle="--", label="1e-6 minimum criterion")
    axis.set(xlabel="time / s", ylabel="signed direction cosine", title="Finite-shadow direction alignment with tangent")
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "04_tangent_norm_policy_comparison.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for run, label in (
        (result["baseline"], "baseline"),
        (result["stricter"], "strict tolerance"),
        (result["refined"], "half max_step"),
    ):
        axis.semilogy(time, run["_tangent_norm"], label=label)
    axis.set(xlabel="time / s", ylabel="Candidate-A tangent norm", title="Tangent norm across numerical policies")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "05_tangent_direction_policy_comparison.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for comparison, label in (
        (result["tolerance_comparison"], "baseline vs strict"),
        (result["max_step_comparison"], "baseline vs half max_step"),
    ):
        axis.semilogy(time, np.maximum(comparison["_direction_difference"], 1.0e-18), label=label)
    axis.axhline(MAX_POLICY_DIRECTION_COMPONENT_DIFFERENCE, color="red", linestyle="--", label="acceptance limit")
    axis.set(xlabel="time / s", ylabel="maximum direction-component difference", title="Tangent-direction numerical convergence")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "06_finite_time_tangent_growth.png"
    fig, axes = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    axes[0].plot(time, result["baseline"]["_log_growth"], label="log norm growth")
    axes[0].set(ylabel="log(d(t)/d(0))", title="Unrenormalised direct-tangent growth")
    axes[1].plot(time[1:], result["baseline"]["_finite_time_rate"][1:], label="descriptive finite-time rate")
    axes[1].set(xlabel="time / s", ylabel="rate / s^-1")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "07_reference_policy_agreement.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    axis.semilogy(time, np.maximum(result["tolerance_comparison"]["_reference_distance"], 1.0e-18), label="baseline vs strict")
    axis.semilogy(time, np.maximum(result["max_step_comparison"]["_reference_distance"], 1.0e-18), label="baseline vs half max_step")
    axis.axhline(MAX_POLICY_REFERENCE_DISTANCE, color="red", linestyle="--", label="acceptance limit")
    axis.set(xlabel="time / s", ylabel="Candidate-A reference distance", title="Reference trajectory agreement")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "08_energy_and_solver_validity.png"
    fig, axes = plt.subplots(2, 1, figsize=(8, 7))
    for run, label in (
        (result["baseline"], "baseline"),
        (result["stricter"], "strict tolerance"),
        (result["refined"], "half max_step"),
    ):
        axes[0].semilogy(time, np.maximum(run["_reference_energy_drift"], 1.0e-18), label=label)
    axes[0].axhline(ENERGY_DRIFT_LIMIT, color="red", linestyle="--", label="energy limit")
    axes[0].set(ylabel="normalized energy drift", title="Reference energy validity")
    labels = ["baseline", "strict", "half max_step"]
    nfev = [result[key]["solver_statistics"]["nfev"] for key in ("baseline", "stricter", "refined")]
    axes[1].bar(labels, nfev)
    axes[1].set(ylabel="RHS evaluations", title="Recorded solver work")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        if axis is axes[0]:
            axis.legend()
    save_figure(fig, path)
    paths.append(path)
    return paths


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_output_bundle(
    result: dict[str, Any], output_dir: Path, *, plots: bool
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    tangent_path = output_dir / "tangent_timeseries.csv"
    shadow_path = output_dir / "finite_shadow_comparison.csv"
    jacobian_path = output_dir / "jacobian_validation.csv"
    policy_path = output_dir / "policy_comparison.csv"
    json_write(summary_path, result["summary"])
    write_tangent_timeseries(tangent_path, result)
    write_finite_shadow_timeseries(shadow_path, result)
    write_jacobian_validation(jacobian_path, result["jacobian_validation"])
    write_policy_comparison(policy_path, result)
    paths = [summary_path, tangent_path, shadow_path, jacobian_path, policy_path]
    if plots:
        paths.extend(write_plots(output_dir, result))
    manifest_path = output_dir / "manifest.json"
    manifest = {
        "experiment": EXPERIMENT_NAME,
        "output_role": "exploratory Experiment 006 evidence; not production application data",
        "source": str(Path(__file__).relative_to(REPOSITORY_ROOT)),
        "files": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in paths
        ],
    }
    json_write(manifest_path, manifest)
    paths.append(manifest_path)
    return paths


def assert_self_check(result: dict[str, Any]) -> None:
    summary = result["summary"]
    assert summary["accepted"] == all(summary["acceptance_checks"].values())
    assert len(result["baseline"]["_time"]) == len(output_time_grid())
    assert np.array_equal(result["baseline"]["_time"], output_time_grid())
    assert math.isclose(
        result["baseline"]["initial_candidate_a_tangent_norm"],
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-15,
    )
    expected_records = (
        result["jacobian_validation"]["tested_state_count"]
        * result["jacobian_validation"]["tested_direction_count"]
        * len(JACOBIAN_H_VALUES)
    )
    assert len(result["jacobian_validation"]["records"]) == expected_records
    assert len(result["finite_shadow_comparison"]["comparisons"]) == len(EPSILONS)
    for run in (result["baseline"], result["stricter"], result["refined"]):
        assert np.all(np.isfinite(run["_reference"]))
        assert np.all(np.isfinite(run["_tangent"]))
        assert np.all(run["_tangent_norm"] > 0.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "development/chaos_content/outputs/variational_dynamics_validation/baseline"
        ),
    )
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_investigation()
    if args.self_check:
        assert_self_check(result)
    paths = write_output_bundle(result, args.output_dir, plots=not args.no_plots)
    summary = result["summary"]
    print(
        json.dumps(
            {
                "status": summary["status"],
                "accepted": summary["accepted"],
                "strongest_claim": summary["strongest_claim"],
                "output_dir": str(args.output_dir),
                "files_written": len(paths),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
