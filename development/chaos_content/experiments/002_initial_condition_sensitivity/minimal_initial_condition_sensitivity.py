"""Run the fixed Stage 1 paired-trajectory sensitivity experiment.

The experiment contract is authoritative in the adjacent README.md. This file
implements that one contract; it is not a reusable Chaos framework.
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

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import numpy as np

from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_DEFAULT_SOLVER_POLICY,
    SIMPLE_REFERENCE_SOLVER_POLICY,
    DoublePendulumLagrangian,
)


EXPERIMENT_NAME = "theta2_120_vs_120.001_deg"
MODEL = "simple"
FORMULATION = "lagrangian"
PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
BASE_INITIAL_STATE_DEGREES = np.array([0.0, 120.0, 0.0, 0.0], dtype=float)
PERTURBED_INITIAL_STATE_DEGREES = np.array([0.0, 120.001, 0.0, 0.0], dtype=float)
PERTURBED_COMPONENT = "theta2"
PERTURBATION_DEGREES = 0.001
T_START = 0.0
T_STOP = 20.0
SAMPLE_COUNT = 4001
SUBSTANTIAL_SEPARATION = 0.1
MAX_CROSSING_TIME_DIFFERENCE_SECONDS = 0.5
MIN_PHYSICAL_TO_NUMERICAL_RATIO = 100.0
PRINCIPAL_MAX_ENERGY_DRIFT = 1e-5
REFERENCE_MAX_ENERGY_DRIFT = 1e-7
INITIAL_SEPARATION_ABSOLUTE_TOLERANCE = 1e-12


def _json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _policy_dict(policy: Any) -> dict[str, Any]:
    return {
        "name": policy.name,
        "method": policy.method,
        "rtol": policy.rtol,
        "atol": policy.atol,
        "role": policy.role,
    }


def _parameter_dict() -> dict[str, float]:
    return {str(symbol): float(value) for symbol, value in PARAMETERS.items()}


def _wrap_to_pi(values: np.ndarray) -> np.ndarray:
    return (np.asarray(values, dtype=float) + math.pi) % (2.0 * math.pi) - math.pi


def _simple_energy(state: np.ndarray) -> np.ndarray:
    theta1 = state[:, 0]
    theta2 = state[:, 1]
    omega1 = state[:, 2]
    omega2 = state[:, 3]
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
    length1 = float(PARAMETERS[l1])
    length2 = float(PARAMETERS[l2])
    mass1 = float(PARAMETERS[m1])
    mass2 = float(PARAMETERS[m2])
    gravity = float(PARAMETERS[g])
    return gravity * ((mass1 + mass2) * length1 + mass2 * length2)


def _energy_drift(energies: np.ndarray) -> np.ndarray:
    return np.abs(energies - energies[0]) / _energy_scale()


def _integrate_trajectory(
    label: str,
    initial_state_degrees: np.ndarray,
    policy: Any,
    max_energy_drift: float,
) -> dict[str, Any]:
    requested_time = np.linspace(T_START, T_STOP, SAMPLE_COUNT)
    issues: list[str] = []

    try:
        pendulum = DoublePendulumLagrangian(
            PARAMETERS,
            initial_state_degrees,
            [T_START, T_STOP, SAMPLE_COUNT],
            model=MODEL,
            solver_policy=policy,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return {
            "label": label,
            "accepted": False,
            "issues": [f"integration_exception: {exc}"],
            "policy": _policy_dict(policy),
            "initial_state_degrees": initial_state_degrees.tolist(),
            "time": np.array([], dtype=float),
            "state": np.empty((0, 4), dtype=float),
            "positions": np.empty((4, 0), dtype=float),
            "energies": np.array([], dtype=float),
            "energy_drifts": np.array([], dtype=float),
            "max_energy_drift": None,
            "solver_metadata": {},
        }

    metadata = pendulum.solver_metadata
    metadata_dict = metadata.to_dict()
    state = np.asarray(pendulum.sol, dtype=float)
    returned_time = np.asarray(pendulum.solver_time, dtype=float)

    if metadata.success is not True:
        issues.append(f"solver_failed: {metadata.message}")
    if metadata.returned_time_matches_requested is not True:
        issues.append("returned_time_does_not_match_requested")
    if returned_time.shape != requested_time.shape or not np.array_equal(returned_time, requested_time):
        issues.append("returned_time_array_is_incomplete_or_misaligned")
    if state.shape != (SAMPLE_COUNT, 4):
        issues.append(f"unexpected_solution_shape: {state.shape}")
    if not np.all(np.isfinite(state)):
        issues.append("non_finite_state_values")

    positions = np.empty((4, 0), dtype=float)
    energies = np.array([], dtype=float)
    drifts = np.array([], dtype=float)
    observed_max_drift: float | None = None

    if not issues:
        pendulum.precompute_positions()
        positions = np.asarray(pendulum.precomputed_positions, dtype=float)
        if positions.shape != (4, SAMPLE_COUNT):
            issues.append(f"unexpected_position_shape: {positions.shape}")
        elif not np.all(np.isfinite(positions)):
            issues.append("non_finite_position_values")

    if not issues:
        energies = _simple_energy(state)
        drifts = _energy_drift(energies)
        if not np.all(np.isfinite(energies)) or not np.all(np.isfinite(drifts)):
            issues.append("non_finite_energy_values")
        else:
            observed_max_drift = float(np.max(drifts))
            if observed_max_drift > max_energy_drift:
                issues.append(
                    "energy_drift_exceeded: "
                    f"{observed_max_drift:.6e} > {max_energy_drift:.6e}"
                )

    return {
        "label": label,
        "accepted": not issues,
        "issues": issues,
        "policy": _policy_dict(policy),
        "initial_state_degrees": initial_state_degrees.tolist(),
        "time": returned_time,
        "state": state,
        "positions": positions,
        "energies": energies,
        "energy_drifts": drifts,
        "max_energy_drift": observed_max_drift,
        "max_allowed_energy_drift": max_energy_drift,
        "solver_metadata": metadata_dict,
    }


def _normalized_tip_distance(positions_a: np.ndarray, positions_b: np.ndarray) -> np.ndarray:
    total_length = float(PARAMETERS[l1] + PARAMETERS[l2])
    delta_x2 = positions_a[2] - positions_b[2]
    delta_y2 = positions_a[3] - positions_b[3]
    return np.hypot(delta_x2, delta_y2) / total_length


def _normalized_configuration_distance(
    positions_a: np.ndarray,
    positions_b: np.ndarray,
) -> np.ndarray:
    total_length = float(PARAMETERS[l1] + PARAMETERS[l2])
    delta_r1_squared = (positions_a[0] - positions_b[0]) ** 2 + (
        positions_a[1] - positions_b[1]
    ) ** 2
    delta_r2_squared = (positions_a[2] - positions_b[2]) ** 2 + (
        positions_a[3] - positions_b[3]
    ) ** 2
    return np.sqrt((delta_r1_squared + delta_r2_squared) / 2.0) / total_length


def _angular_configuration_distance(state_a: np.ndarray, state_b: np.ndarray) -> np.ndarray:
    angular_delta = _wrap_to_pi(state_a[:, :2] - state_b[:, :2])
    return np.linalg.norm(angular_delta, axis=1)


def _first_threshold_index(values: np.ndarray) -> int | None:
    indices = np.flatnonzero(values >= SUBSTANTIAL_SEPARATION)
    return int(indices[0]) if len(indices) else None


def _trajectory_summary(trajectory: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": trajectory["label"],
        "accepted": trajectory["accepted"],
        "issues": list(trajectory["issues"]),
        "policy": dict(trajectory["policy"]),
        "initial_state_degrees": list(trajectory["initial_state_degrees"]),
        "max_energy_drift": trajectory["max_energy_drift"],
        "max_allowed_energy_drift": trajectory.get("max_allowed_energy_drift"),
        "solver_metadata": dict(trajectory["solver_metadata"]),
    }


def _early_rejection_summary(trajectories: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "experiment": EXPERIMENT_NAME,
        "status": "rejected",
        "accepted": False,
        "failure_reason": "one_or_more_trajectories_failed_numerical_acceptance",
        "permitted_claim_supported": False,
        "trajectories": [_trajectory_summary(item) for item in trajectories],
        "acceptance_checks": {
            "all_trajectories_numerically_accepted": False,
        },
        "claim_boundary": (
            "No sensitivity claim is supported because the numerical trajectory contract failed."
        ),
    }


def run_experiment() -> dict[str, Any]:
    trajectories = [
        _integrate_trajectory(
            "base_principal",
            BASE_INITIAL_STATE_DEGREES,
            SIMPLE_DEFAULT_SOLVER_POLICY,
            PRINCIPAL_MAX_ENERGY_DRIFT,
        ),
        _integrate_trajectory(
            "perturbed_principal",
            PERTURBED_INITIAL_STATE_DEGREES,
            SIMPLE_DEFAULT_SOLVER_POLICY,
            PRINCIPAL_MAX_ENERGY_DRIFT,
        ),
        _integrate_trajectory(
            "base_reference",
            BASE_INITIAL_STATE_DEGREES,
            SIMPLE_REFERENCE_SOLVER_POLICY,
            REFERENCE_MAX_ENERGY_DRIFT,
        ),
        _integrate_trajectory(
            "perturbed_reference",
            PERTURBED_INITIAL_STATE_DEGREES,
            SIMPLE_REFERENCE_SOLVER_POLICY,
            REFERENCE_MAX_ENERGY_DRIFT,
        ),
    ]

    if not all(item["accepted"] for item in trajectories):
        return {
            "summary": _early_rejection_summary(trajectories),
            "trajectories": trajectories,
            "series": None,
        }

    base_principal, perturbed_principal, base_reference, perturbed_reference = trajectories
    times = base_principal["time"]
    time_aligned = all(np.array_equal(times, item["time"]) for item in trajectories[1:])

    tip_principal = _normalized_tip_distance(
        base_principal["positions"], perturbed_principal["positions"]
    )
    tip_reference = _normalized_tip_distance(
        base_reference["positions"], perturbed_reference["positions"]
    )
    configuration_principal = _normalized_configuration_distance(
        base_principal["positions"], perturbed_principal["positions"]
    )
    configuration_reference = _normalized_configuration_distance(
        base_reference["positions"], perturbed_reference["positions"]
    )
    angle_principal = _angular_configuration_distance(
        base_principal["state"], perturbed_principal["state"]
    )
    angle_reference = _angular_configuration_distance(
        base_reference["state"], perturbed_reference["state"]
    )

    base_numerical_error = _normalized_tip_distance(
        base_principal["positions"], base_reference["positions"]
    )
    perturbed_numerical_error = _normalized_tip_distance(
        perturbed_principal["positions"], perturbed_reference["positions"]
    )
    numerical_envelope = np.maximum(base_numerical_error, perturbed_numerical_error)

    diagnostic_arrays = (
        tip_principal,
        tip_reference,
        configuration_principal,
        configuration_reference,
        angle_principal,
        angle_reference,
        base_numerical_error,
        perturbed_numerical_error,
        numerical_envelope,
    )
    diagnostics_finite = all(np.all(np.isfinite(values)) for values in diagnostic_arrays)

    declared_delta = PERTURBED_INITIAL_STATE_DEGREES - BASE_INITIAL_STATE_DEGREES
    changed_indices = np.flatnonzero(declared_delta != 0.0)
    exactly_one_declared_component = (
        changed_indices.tolist() == [1]
        and math.isclose(float(declared_delta[1]), PERTURBATION_DEGREES, rel_tol=0.0, abs_tol=1e-12)
    )

    perturbation_radians = math.radians(PERTURBATION_DEGREES)
    expected_initial_tip_separation = (
        2.0 * float(PARAMETERS[l2]) * math.sin(abs(perturbation_radians) / 2.0)
        / float(PARAMETERS[l1] + PARAMETERS[l2])
    )
    principal_initial_matches = math.isclose(
        float(tip_principal[0]),
        expected_initial_tip_separation,
        rel_tol=0.0,
        abs_tol=INITIAL_SEPARATION_ABSOLUTE_TOLERANCE,
    )
    reference_initial_matches = math.isclose(
        float(tip_reference[0]),
        expected_initial_tip_separation,
        rel_tol=0.0,
        abs_tol=INITIAL_SEPARATION_ABSOLUTE_TOLERANCE,
    )

    principal_crossing_index = _first_threshold_index(tip_principal)
    reference_crossing_index = _first_threshold_index(tip_reference)
    principal_crossing_time = (
        float(times[principal_crossing_index]) if principal_crossing_index is not None else None
    )
    reference_crossing_time = (
        float(times[reference_crossing_index]) if reference_crossing_index is not None else None
    )
    crossing_time_difference = (
        abs(principal_crossing_time - reference_crossing_time)
        if principal_crossing_time is not None and reference_crossing_time is not None
        else None
    )

    numerical_error_at_reference_crossing: float | None = None
    reference_separation_at_crossing: float | None = None
    physical_to_numerical_ratio: float | None = None
    if reference_crossing_index is not None:
        numerical_error_at_reference_crossing = float(
            numerical_envelope[reference_crossing_index]
        )
        reference_separation_at_crossing = float(tip_reference[reference_crossing_index])
        if numerical_error_at_reference_crossing == 0.0:
            physical_to_numerical_ratio = 1e300
        else:
            physical_to_numerical_ratio = (
                reference_separation_at_crossing / numerical_error_at_reference_crossing
            )

    wrapped_delta_principal = _wrap_to_pi(
        base_principal["state"][:, :2] - perturbed_principal["state"][:, :2]
    )
    wrapped_delta_reference = _wrap_to_pi(
        base_reference["state"][:, :2] - perturbed_reference["state"][:, :2]
    )
    wrapped_angles_valid = bool(
        np.all(wrapped_delta_principal >= -math.pi)
        and np.all(wrapped_delta_principal < math.pi)
        and np.all(wrapped_delta_reference >= -math.pi)
        and np.all(wrapped_delta_reference < math.pi)
    )

    checks = {
        "exactly_one_declared_component_perturbed": exactly_one_declared_component,
        "all_trajectories_numerically_accepted": all(
            item["accepted"] for item in trajectories
        ),
        "all_trajectory_times_are_aligned": time_aligned,
        "all_diagnostics_are_finite": diagnostics_finite,
        "principal_initial_separation_matches_geometry": principal_initial_matches,
        "reference_initial_separation_matches_geometry": reference_initial_matches,
        "principal_pair_reaches_substantial_separation": principal_crossing_index is not None,
        "reference_pair_reaches_substantial_separation": reference_crossing_index is not None,
        "crossing_times_agree_within_limit": (
            crossing_time_difference is not None
            and crossing_time_difference <= MAX_CROSSING_TIME_DIFFERENCE_SECONDS
        ),
        "physical_separation_exceeds_numerical_disagreement_ratio": (
            physical_to_numerical_ratio is not None
            and physical_to_numerical_ratio >= MIN_PHYSICAL_TO_NUMERICAL_RATIO
        ),
        "periodic_angular_differences_are_valid": wrapped_angles_valid,
    }
    accepted = all(checks.values())

    max_principal_index = int(np.argmax(tip_principal))
    max_reference_index = int(np.argmax(tip_reference))
    initial_energy_difference = float(
        abs(perturbed_principal["energies"][0] - base_principal["energies"][0])
    )

    summary = {
        "experiment": EXPERIMENT_NAME,
        "status": "accepted" if accepted else "rejected",
        "accepted": accepted,
        "failure_reason": None if accepted else "one_or_more_acceptance_checks_failed",
        "permitted_claim_supported": accepted,
        "question": (
            "Can two simple-double-pendulum trajectories differing in exactly one declared "
            "user-facing initial-state component exhibit finite-time physical separation "
            "that remains credible under an explicit numerical acceptance policy?"
        ),
        "configuration": {
            "model": MODEL,
            "formulation": FORMULATION,
            "parameters_si": _parameter_dict(),
            "base_initial_state_degrees": BASE_INITIAL_STATE_DEGREES.tolist(),
            "perturbed_initial_state_degrees": PERTURBED_INITIAL_STATE_DEGREES.tolist(),
            "perturbed_component": PERTURBED_COMPONENT,
            "perturbation_degrees": PERTURBATION_DEGREES,
            "perturbation_radians": perturbation_radians,
            "equal_initial_energy_required": False,
            "t_start_seconds": T_START,
            "t_stop_seconds": T_STOP,
            "sample_count": SAMPLE_COUNT,
            "sample_interval_seconds": float(times[1] - times[0]),
            "principal_policy": _policy_dict(SIMPLE_DEFAULT_SOLVER_POLICY),
            "reference_policy": _policy_dict(SIMPLE_REFERENCE_SOLVER_POLICY),
        },
        "acceptance_policy": {
            "substantial_normalized_tip_separation": SUBSTANTIAL_SEPARATION,
            "substantial_tip_separation_metres": (
                SUBSTANTIAL_SEPARATION * float(PARAMETERS[l1] + PARAMETERS[l2])
            ),
            "max_crossing_time_difference_seconds": MAX_CROSSING_TIME_DIFFERENCE_SECONDS,
            "minimum_physical_to_numerical_ratio": MIN_PHYSICAL_TO_NUMERICAL_RATIO,
            "principal_max_normalized_energy_drift": PRINCIPAL_MAX_ENERGY_DRIFT,
            "reference_max_normalized_energy_drift": REFERENCE_MAX_ENERGY_DRIFT,
            "energy_scale_joules": _energy_scale(),
        },
        "acceptance_checks": checks,
        "measurements": {
            "expected_initial_normalized_tip_separation": expected_initial_tip_separation,
            "principal_initial_normalized_tip_separation": float(tip_principal[0]),
            "reference_initial_normalized_tip_separation": float(tip_reference[0]),
            "initial_energy_difference_joules": initial_energy_difference,
            "initial_energy_difference_normalized": initial_energy_difference / _energy_scale(),
            "principal_first_substantial_separation_time_seconds": principal_crossing_time,
            "reference_first_substantial_separation_time_seconds": reference_crossing_time,
            "crossing_time_difference_seconds": crossing_time_difference,
            "reference_separation_at_reference_crossing": reference_separation_at_crossing,
            "numerical_error_at_reference_crossing": numerical_error_at_reference_crossing,
            "physical_to_numerical_ratio_at_reference_crossing": physical_to_numerical_ratio,
            "principal_max_normalized_tip_separation": float(tip_principal[max_principal_index]),
            "principal_max_separation_time_seconds": float(times[max_principal_index]),
            "reference_max_normalized_tip_separation": float(tip_reference[max_reference_index]),
            "reference_max_separation_time_seconds": float(times[max_reference_index]),
            "principal_final_normalized_tip_separation": float(tip_principal[-1]),
            "reference_final_normalized_tip_separation": float(tip_reference[-1]),
            "principal_max_normalized_configuration_separation": float(
                np.max(configuration_principal)
            ),
            "reference_max_normalized_configuration_separation": float(
                np.max(configuration_reference)
            ),
            "principal_max_periodic_angular_separation_radians": float(
                np.max(angle_principal)
            ),
            "reference_max_periodic_angular_separation_radians": float(
                np.max(angle_reference)
            ),
            "max_base_principal_to_reference_numerical_error": float(
                np.max(base_numerical_error)
            ),
            "max_perturbed_principal_to_reference_numerical_error": float(
                np.max(perturbed_numerical_error)
            ),
            "max_numerical_error_envelope": float(np.max(numerical_envelope)),
        },
        "trajectories": [_trajectory_summary(item) for item in trajectories],
        "claim_boundary": (
            "For this named initial-condition pair and declared numerical policies, a small "
            "declared initial difference produced substantial finite-time physical trajectory "
            "separation. This is not proof of chaos, exponential divergence, a Lyapunov "
            "exponent, a general sensitivity law, or solver-independent long-time dynamics."
            if accepted
            else "The fixed experiment did not satisfy its predeclared acceptance policy, so no "
            "sensitivity claim is supported."
        ),
    }

    series = {
        "time": times,
        "base_principal_state": base_principal["state"],
        "perturbed_principal_state": perturbed_principal["state"],
        "base_principal_positions": base_principal["positions"],
        "perturbed_principal_positions": perturbed_principal["positions"],
        "base_principal_energy": base_principal["energies"],
        "perturbed_principal_energy": perturbed_principal["energies"],
        "base_principal_energy_drift": base_principal["energy_drifts"],
        "perturbed_principal_energy_drift": perturbed_principal["energy_drifts"],
        "base_reference_energy_drift": base_reference["energy_drifts"],
        "perturbed_reference_energy_drift": perturbed_reference["energy_drifts"],
        "tip_principal": tip_principal,
        "tip_reference": tip_reference,
        "configuration_principal": configuration_principal,
        "configuration_reference": configuration_reference,
        "angle_principal": angle_principal,
        "angle_reference": angle_reference,
        "base_numerical_error": base_numerical_error,
        "perturbed_numerical_error": perturbed_numerical_error,
        "numerical_envelope": numerical_envelope,
    }
    return {"summary": summary, "trajectories": trajectories, "series": series}


CSV_FIELDS = (
    "time_s",
    "base_theta1_rad",
    "base_theta2_rad",
    "base_omega1_rad_per_s",
    "base_omega2_rad_per_s",
    "perturbed_theta1_rad",
    "perturbed_theta2_rad",
    "perturbed_omega1_rad_per_s",
    "perturbed_omega2_rad_per_s",
    "base_x1_m",
    "base_y1_m",
    "base_x2_m",
    "base_y2_m",
    "perturbed_x1_m",
    "perturbed_y1_m",
    "perturbed_x2_m",
    "perturbed_y2_m",
    "base_energy_j",
    "perturbed_energy_j",
    "base_normalized_energy_drift",
    "perturbed_normalized_energy_drift",
    "reference_base_normalized_energy_drift",
    "reference_perturbed_normalized_energy_drift",
    "normalized_tip_separation_principal",
    "normalized_tip_separation_reference",
    "normalized_configuration_separation_principal",
    "normalized_configuration_separation_reference",
    "periodic_angular_separation_principal_rad",
    "periodic_angular_separation_reference_rad",
    "base_principal_to_reference_numerical_error",
    "perturbed_principal_to_reference_numerical_error",
    "numerical_error_envelope",
)


def _write_csv(path: Path, series: dict[str, np.ndarray] | None) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        if series is None:
            return

        for index, time_value in enumerate(series["time"]):
            base_state = series["base_principal_state"][index]
            perturbed_state = series["perturbed_principal_state"][index]
            base_positions = series["base_principal_positions"][:, index]
            perturbed_positions = series["perturbed_principal_positions"][:, index]
            writer.writerow(
                {
                    "time_s": float(time_value),
                    "base_theta1_rad": float(base_state[0]),
                    "base_theta2_rad": float(base_state[1]),
                    "base_omega1_rad_per_s": float(base_state[2]),
                    "base_omega2_rad_per_s": float(base_state[3]),
                    "perturbed_theta1_rad": float(perturbed_state[0]),
                    "perturbed_theta2_rad": float(perturbed_state[1]),
                    "perturbed_omega1_rad_per_s": float(perturbed_state[2]),
                    "perturbed_omega2_rad_per_s": float(perturbed_state[3]),
                    "base_x1_m": float(base_positions[0]),
                    "base_y1_m": float(base_positions[1]),
                    "base_x2_m": float(base_positions[2]),
                    "base_y2_m": float(base_positions[3]),
                    "perturbed_x1_m": float(perturbed_positions[0]),
                    "perturbed_y1_m": float(perturbed_positions[1]),
                    "perturbed_x2_m": float(perturbed_positions[2]),
                    "perturbed_y2_m": float(perturbed_positions[3]),
                    "base_energy_j": float(series["base_principal_energy"][index]),
                    "perturbed_energy_j": float(series["perturbed_principal_energy"][index]),
                    "base_normalized_energy_drift": float(
                        series["base_principal_energy_drift"][index]
                    ),
                    "perturbed_normalized_energy_drift": float(
                        series["perturbed_principal_energy_drift"][index]
                    ),
                    "reference_base_normalized_energy_drift": float(
                        series["base_reference_energy_drift"][index]
                    ),
                    "reference_perturbed_normalized_energy_drift": float(
                        series["perturbed_reference_energy_drift"][index]
                    ),
                    "normalized_tip_separation_principal": float(
                        series["tip_principal"][index]
                    ),
                    "normalized_tip_separation_reference": float(
                        series["tip_reference"][index]
                    ),
                    "normalized_configuration_separation_principal": float(
                        series["configuration_principal"][index]
                    ),
                    "normalized_configuration_separation_reference": float(
                        series["configuration_reference"][index]
                    ),
                    "periodic_angular_separation_principal_rad": float(
                        series["angle_principal"][index]
                    ),
                    "periodic_angular_separation_reference_rad": float(
                        series["angle_reference"][index]
                    ),
                    "base_principal_to_reference_numerical_error": float(
                        series["base_numerical_error"][index]
                    ),
                    "perturbed_principal_to_reference_numerical_error": float(
                        series["perturbed_numerical_error"][index]
                    ),
                    "numerical_error_envelope": float(series["numerical_envelope"][index]),
                }
            )


def _load_pyplot():
    import matplotlib.pyplot as plt

    return plt


def _write_plot(path: Path, run: dict[str, Any]) -> None:
    series = run["series"]
    if series is None:
        return

    plt = _load_pyplot()
    summary = run["summary"]
    time = series["time"]
    base_positions = series["base_principal_positions"]
    perturbed_positions = series["perturbed_principal_positions"]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    axes[0, 0].plot(base_positions[2], base_positions[3], linewidth=0.8, label="base")
    axes[0, 0].plot(
        perturbed_positions[2],
        perturbed_positions[3],
        linewidth=0.8,
        alpha=0.8,
        label="perturbed",
    )
    axes[0, 0].set_title("Second-bob paths: principal policy")
    axes[0, 0].set_xlabel("x2 / m")
    axes[0, 0].set_ylabel("y2 / m")
    axes[0, 0].set_aspect("equal", adjustable="box")
    axes[0, 0].legend()

    axes[0, 1].plot(time, series["tip_principal"], label="pair: principal")
    axes[0, 1].plot(time, series["tip_reference"], linestyle="--", label="pair: reference")
    axes[0, 1].axhline(
        SUBSTANTIAL_SEPARATION,
        color="black",
        linestyle=":",
        label="substantial threshold",
    )
    axes[0, 1].set_title("Normalized physical separation")
    axes[0, 1].set_xlabel("time / s")
    axes[0, 1].set_ylabel("end-bob distance / total length (log scale)")
    axes[0, 1].set_yscale("log")
    axes[0, 1].legend()

    plot_floor = 1e-12
    axes[1, 0].semilogy(
        time,
        np.maximum(series["tip_reference"], plot_floor),
        label="physical pair separation",
    )
    axes[1, 0].semilogy(
        time,
        np.maximum(series["numerical_envelope"], plot_floor),
        label="principal/reference disagreement",
    )
    axes[1, 0].set_title("Physical difference versus exposed numerical disagreement")
    axes[1, 0].set_xlabel("time / s")
    axes[1, 0].set_ylabel("normalized distance (log scale)")
    axes[1, 0].legend()

    axes[1, 1].semilogy(
        time,
        np.maximum(series["base_principal_energy_drift"], plot_floor),
        label="base principal",
    )
    axes[1, 1].semilogy(
        time,
        np.maximum(series["perturbed_principal_energy_drift"], plot_floor),
        label="perturbed principal",
    )
    axes[1, 1].semilogy(
        time,
        np.maximum(series["base_reference_energy_drift"], plot_floor),
        linestyle="--",
        label="base reference",
    )
    axes[1, 1].semilogy(
        time,
        np.maximum(series["perturbed_reference_energy_drift"], plot_floor),
        linestyle="--",
        label="perturbed reference",
    )
    axes[1, 1].axhline(PRINCIPAL_MAX_ENERGY_DRIFT, color="black", linestyle=":")
    axes[1, 1].axhline(REFERENCE_MAX_ENERGY_DRIFT, color="gray", linestyle=":")
    axes[1, 1].set_title("Independent normalized energy drift")
    axes[1, 1].set_xlabel("time / s")
    axes[1, 1].set_ylabel("|E(t)-E(0)| / E_scale")
    axes[1, 1].legend(fontsize=8)

    status = summary["status"].upper()
    fig.suptitle(f"Stage 1 sensitivity diagnostic: {EXPERIMENT_NAME} — {status}")
    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_output_bundle(run: dict[str, Any], output_dir: Path, include_plots: bool) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    summary_path = output_dir / "summary.json"
    _json_write(summary_path, run["summary"])
    created.append(summary_path)

    csv_path = output_dir / "trajectory_separation.csv"
    _write_csv(csv_path, run["series"])
    created.append(csv_path)

    if include_plots and run["series"] is not None:
        plot_path = output_dir / "sensitivity_diagnostics.png"
        _write_plot(plot_path, run)
        created.append(plot_path)

    manifest_path = output_dir / "manifest.json"
    manifest = {
        "artifact": "minimal_initial_condition_sensitivity",
        "experiment": EXPERIMENT_NAME,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": run["summary"]["status"],
        "accepted": run["summary"]["accepted"],
        "failure_reason": run["summary"]["failure_reason"],
        "created_files": [manifest_path.name, *[path.name for path in created]],
        "reproduction_command": (
            "uv run python development/chaos_content/experiments/"
            "002_initial_condition_sensitivity/minimal_initial_condition_sensitivity.py "
            "--output-dir development/chaos_content/outputs/"
            "initial_condition_sensitivity/principal --plots"
        ),
        "contract": (
            "development/chaos_content/experiments/"
            "002_initial_condition_sensitivity/README.md"
        ),
        "configuration": run["summary"].get("configuration", {}),
        "acceptance_policy": run["summary"].get("acceptance_policy", {}),
        "acceptance_checks": run["summary"].get("acceptance_checks", {}),
        "claim_boundary": run["summary"]["claim_boundary"],
        "notes": [
            "Sandbox diagnostic only; not a production asset or general chaos classification.",
            "The tighter policy comparison is included in the same fixed named run.",
        ],
    }
    _json_write(manifest_path, manifest)
    return [manifest_path, *created]


def _assert_self_check(run: dict[str, Any]) -> None:
    summary = run["summary"]
    if summary["experiment"] != EXPERIMENT_NAME:
        raise AssertionError("Unexpected experiment name.")
    if run["series"] is None:
        raise AssertionError(f"No diagnostic series: {summary['failure_reason']}")
    if len(run["series"]["time"]) != SAMPLE_COUNT:
        raise AssertionError("Unexpected self-check sample count.")
    checks = summary["acceptance_checks"]
    expected_true = (
        "exactly_one_declared_component_perturbed",
        "all_trajectories_numerically_accepted",
        "all_trajectory_times_are_aligned",
        "all_diagnostics_are_finite",
        "principal_initial_separation_matches_geometry",
        "reference_initial_separation_matches_geometry",
        "periodic_angular_differences_are_valid",
    )
    failed_expected_true = [name for name in expected_true if checks.get(name) is not True]
    if failed_expected_true:
        raise AssertionError(f"Numerical contract checks failed: {failed_expected_true}")

    expected_false = (
        "principal_pair_reaches_substantial_separation",
        "reference_pair_reaches_substantial_separation",
        "crossing_times_agree_within_limit",
        "physical_separation_exceeds_numerical_disagreement_ratio",
    )
    unexpected_passes = [name for name in expected_false if checks.get(name) is not False]
    if unexpected_passes:
        raise AssertionError(
            "Fixed rejected-result checks changed unexpectedly: "
            f"{unexpected_passes}"
        )
    if summary["accepted"] or summary["status"] != "rejected":
        raise AssertionError("Fixed named experiment should retain its rejected evidence status.")
    if summary["permitted_claim_supported"]:
        raise AssertionError("Rejected experiment must not advertise a supported sensitivity claim.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="assert the fixed experiment contract")
    parser.add_argument("--output-dir", type=Path, help="optional ignored sandbox output directory")
    parser.add_argument("--plots", action="store_true", help="write the static diagnostic plot")
    args = parser.parse_args()

    if args.plots and args.output_dir is None:
        parser.error("--plots requires --output-dir")

    run = run_experiment()
    if args.self_check:
        _assert_self_check(run)
    if args.output_dir is not None:
        write_output_bundle(run, args.output_dir, include_plots=args.plots)

    print(json.dumps(run["summary"], indent=2, sort_keys=True, allow_nan=False))
    if args.self_check:
        return 0
    return 0 if run["summary"]["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
