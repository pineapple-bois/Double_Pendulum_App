"""Demonstrate the minimal full-matrix QR extension of Experiment 006.

The adjacent README fixes the single-run contract and primitive-only claim
boundary. This module deliberately performs no convergence sweep.
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
from typing import Any

RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT_006_ROOT = (
    EXPERIMENT_ROOT.parent / "006_variational_dynamics_validation"
)
for import_root in (REPOSITORY_ROOT, EXPERIMENT_006_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import numpy as np

import variational_dynamics_validation as experiment006


EXPERIMENT_NAME = "full_matrix_qr_tangent_dynamics"
FORMULATION = "Euler-Lagrange full tangent matrix with Candidate-A-scaled QR"
STATE_ORDER = experiment006.STATE_ORDER
TANGENT_DIMENSION = 4
RUN_DURATION_SECONDS = 5.0
QR_INTERVAL_SECONDS = 0.25
OUTPUT_INTERVAL_SECONDS = 0.01
QR_CYCLE_COUNT = int(round(RUN_DURATION_SECONDS / QR_INTERVAL_SECONDS))

SOLVER_POLICY = experiment006.SIMPLE_REFERENCE_SOLVER_POLICY
MAX_STEP_SECONDS = experiment006.BASELINE_MAX_STEP
ENERGY_DRIFT_LIMIT = experiment006.ENERGY_DRIFT_LIMIT

QR_ERROR_LIMIT = 1.0e-12
BOOKKEEPING_ERROR_LIMIT = 1.0e-12
REPRODUCIBILITY_ERROR_LIMIT = 1.0e-12
MINIMUM_R_DIAGONAL = 1.0e-14
MAXIMUM_PRE_QR_CONDITION_NUMBER = 1.0e12


def scaling_matrix() -> np.ndarray:
    """Return the constant Candidate-A coordinate scaling matrix ``S``."""

    characteristic_time = experiment006.characteristic_time()
    return np.diag([1.0, 1.0, characteristic_time, characteristic_time])


def inverse_scaling_matrix() -> np.ndarray:
    return np.linalg.inv(scaling_matrix())


def initial_physical_tangent_basis() -> np.ndarray:
    """Return ``Y0=S^-1`` so the initial scaled basis is exactly identity."""

    return inverse_scaling_matrix()


def unpack_augmented_state(augmented: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    augmented = np.asarray(augmented, dtype=float)
    expected_size = TANGENT_DIMENSION + TANGENT_DIMENSION**2
    if augmented.shape != (expected_size,):
        raise ValueError(f"Augmented QR state must have shape ({expected_size},).")
    return augmented[:4], augmented[4:].reshape(4, 4)


def pack_augmented_state(reference: np.ndarray, tangent_matrix: np.ndarray) -> np.ndarray:
    reference = np.asarray(reference, dtype=float)
    tangent_matrix = np.asarray(tangent_matrix, dtype=float)
    if reference.shape != (4,) or tangent_matrix.shape != (4, 4):
        raise ValueError("Expected one four-state and one 4x4 tangent matrix.")
    return np.concatenate((reference, tangent_matrix.reshape(16)))


def full_matrix_augmented_rhs(
    dynamics: experiment006.VariationalDynamics,
    time_value: float,
    augmented: np.ndarray,
) -> np.ndarray:
    """Evolve the physical reference and all four physical tangent columns."""

    reference, tangent_matrix = unpack_augmented_state(augmented)
    reference_rhs = dynamics.flow(reference, time_value)
    tangent_rhs = dynamics.jacobian(reference, time_value) @ tangent_matrix
    return pack_augmented_state(reference_rhs, tangent_rhs)


def positive_diagonal_qr(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return deterministic QR factors with strictly nonnegative R diagonal."""

    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("QR input must be a finite 4x4 matrix.")
    orthogonal, upper = np.linalg.qr(matrix, mode="reduced")
    diagonal = np.diag(upper)
    signs = np.where(diagonal < 0.0, -1.0, 1.0)
    orthogonal = orthogonal * signs[np.newaxis, :]
    upper = signs[:, np.newaxis] * upper
    return orthogonal, upper


def qr_reset(tangent_matrix_pre: np.ndarray) -> dict[str, Any]:
    """Apply one Candidate-A-scaled QR reset and expose all consistency errors."""

    tangent_matrix_pre = np.asarray(tangent_matrix_pre, dtype=float)
    if tangent_matrix_pre.shape != (4, 4):
        raise ValueError("Pre-reset tangent matrix must be 4x4.")

    scale = scaling_matrix()
    inverse_scale = inverse_scaling_matrix()
    scaled_pre = scale @ tangent_matrix_pre
    orthogonal, upper = positive_diagonal_qr(scaled_pre)
    diagonal = np.diag(upper)
    tangent_matrix_post = inverse_scale @ orthogonal

    identity = np.eye(4)
    orthonormality_error = float(
        np.linalg.norm(orthogonal.T @ orthogonal - identity, ord=np.inf)
    )
    scaled_reconstruction_error = float(
        np.linalg.norm(scaled_pre - orthogonal @ upper, ord="fro")
        / max(1.0, float(np.linalg.norm(scaled_pre, ord="fro")))
    )
    physical_reconstruction_error = float(
        np.linalg.norm(
            tangent_matrix_pre - tangent_matrix_post @ upper, ord="fro"
        )
        / max(1.0, float(np.linalg.norm(tangent_matrix_pre, ord="fro")))
    )
    scaled_post = scale @ tangent_matrix_post
    post_metric_orthonormality_error = float(
        np.linalg.norm(scaled_post.T @ scaled_post - identity, ord=np.inf)
    )
    reset_map_error = float(
        np.linalg.norm(scaled_post - orthogonal, ord="fro")
    )
    condition_number = float(np.linalg.cond(scaled_pre))
    log_diagonal = np.log(np.abs(diagonal))

    checks = {
        "finite_input_and_factors": bool(
            np.all(np.isfinite(scaled_pre))
            and np.all(np.isfinite(orthogonal))
            and np.all(np.isfinite(upper))
            and np.all(np.isfinite(tangent_matrix_post))
        ),
        "positive_resolved_r_diagonal": bool(
            np.all(np.isfinite(diagonal))
            and np.all(diagonal >= MINIMUM_R_DIAGONAL)
        ),
        "q_orthonormal_within_limit": bool(
            orthonormality_error <= QR_ERROR_LIMIT
        ),
        "scaled_reconstruction_within_limit": bool(
            scaled_reconstruction_error <= QR_ERROR_LIMIT
        ),
        "physical_reconstruction_within_limit": bool(
            physical_reconstruction_error <= QR_ERROR_LIMIT
        ),
        "post_reset_metric_orthonormal_within_limit": bool(
            post_metric_orthonormality_error <= QR_ERROR_LIMIT
        ),
        "reset_map_within_limit": bool(reset_map_error <= QR_ERROR_LIMIT),
        "finite_log_diagonal": bool(np.all(np.isfinite(log_diagonal))),
        "pre_qr_condition_below_pathology_guard": bool(
            np.isfinite(condition_number)
            and condition_number <= MAXIMUM_PRE_QR_CONDITION_NUMBER
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "scaled_pre": scaled_pre,
        "orthogonal": orthogonal,
        "upper": upper,
        "diagonal": diagonal,
        "log_diagonal": log_diagonal,
        "tangent_matrix_post": tangent_matrix_post,
        "orthonormality_error": orthonormality_error,
        "scaled_reconstruction_relative_error": scaled_reconstruction_error,
        "physical_reconstruction_relative_error": physical_reconstruction_error,
        "post_metric_orthonormality_error": post_metric_orthonormality_error,
        "reset_map_error": reset_map_error,
        "pre_qr_condition_number": condition_number,
    }


def deterministic_cycle_times(duration: float = RUN_DURATION_SECONDS) -> np.ndarray:
    cycle_count = int(round(duration / QR_INTERVAL_SECONDS))
    if cycle_count <= 0 or not math.isclose(
        cycle_count * QR_INTERVAL_SECONDS,
        duration,
        rel_tol=0.0,
        abs_tol=1.0e-13,
    ):
        raise ValueError("Duration must contain an integer number of QR intervals.")
    return np.linspace(0.0, duration, cycle_count + 1)


def requested_cycle_times(start: float, end: float) -> np.ndarray:
    sample_count = int(round((end - start) / OUTPUT_INTERVAL_SECONDS)) + 1
    return np.linspace(start, end, sample_count)


def _public_qr_reset(reset: dict[str, Any]) -> dict[str, Any]:
    return {
        "checks": reset["checks"],
        "scaled_pre": reset["scaled_pre"].tolist(),
        "orthogonal_q": reset["orthogonal"].tolist(),
        "upper_r": reset["upper"].tolist(),
        "r_diagonal": reset["diagonal"].tolist(),
        "log_r_diagonal": reset["log_diagonal"].tolist(),
        "tangent_matrix_post": reset["tangent_matrix_post"].tolist(),
        "q_orthonormality_error": reset["orthonormality_error"],
        "scaled_reconstruction_relative_error": reset[
            "scaled_reconstruction_relative_error"
        ],
        "physical_reconstruction_relative_error": reset[
            "physical_reconstruction_relative_error"
        ],
        "post_metric_orthonormality_error": reset[
            "post_metric_orthonormality_error"
        ],
        "reset_map_error": reset["reset_map_error"],
        "pre_qr_condition_number": reset["pre_qr_condition_number"],
    }


def run_qr_primitive(
    dynamics: experiment006.VariationalDynamics,
    *,
    run_id: str,
    duration: float = RUN_DURATION_SECONDS,
) -> dict[str, Any]:
    """Run one fixed-policy full-matrix QR trajectory."""

    boundaries = deterministic_cycle_times(duration)
    current_reference = np.array(experiment006.BASE_STATE_RADIANS, copy=True)
    current_tangent = initial_physical_tangent_basis()
    initial_energy = float(experiment006.simple_energy(current_reference))
    cumulative_logs = np.zeros(4)
    cycles: list[dict[str, Any]] = []
    reference_times: list[np.ndarray] = []
    reference_states: list[np.ndarray] = []
    reference_energy_drifts: list[np.ndarray] = []
    solver_statuses: list[dict[str, Any]] = []

    for cycle_index, (start, end) in enumerate(
        zip(boundaries[:-1], boundaries[1:]), start=1
    ):
        reference_start = np.array(current_reference, copy=True)
        tangent_start = np.array(current_tangent, copy=True)
        augmented_start = pack_augmented_state(reference_start, tangent_start)
        requested_time = requested_cycle_times(float(start), float(end))
        segment = experiment006.solve_one_segment(
            lambda time_value, augmented: full_matrix_augmented_rhs(
                dynamics, time_value, augmented
            ),
            augmented_start,
            requested_time,
            SOLVER_POLICY,
            max_step=MAX_STEP_SECONDS,
        )
        solver_status = segment["solver_status"] | {
            "accepted": segment["accepted"]
        }
        solver_statuses.append(solver_status)
        if not segment["accepted"]:
            raise RuntimeError(
                f"QR cycle {cycle_index} integration failed: {segment['checks']}"
            )

        augmented_samples = segment["state"]
        segment_reference = augmented_samples[:, :4]
        reference_end_raw, tangent_pre = unpack_augmented_state(
            augmented_samples[-1]
        )
        reference_end = experiment006.canonicalize_state_angles(reference_end_raw)
        energy = experiment006.simple_energy(segment_reference)
        energy_drift = np.abs(energy - initial_energy) / experiment006.energy_scale()
        segment_max_energy_drift = float(np.max(energy_drift))

        reset = qr_reset(tangent_pre)
        cycle_logs = np.asarray(reset["log_diagonal"], dtype=float)
        cumulative_logs = cumulative_logs + cycle_logs
        finite_time_spectrum = cumulative_logs / float(end)
        bookkeeping_finite = bool(
            np.all(np.isfinite(cycle_logs))
            and np.all(np.isfinite(cumulative_logs))
            and np.all(np.isfinite(finite_time_spectrum))
        )
        checks = {
            "solver_segment_valid": segment["accepted"],
            "qr_reset_valid": reset["accepted"],
            "finite_accumulation": bookkeeping_finite,
            "reference_energy_within_limit": bool(
                segment_max_energy_drift <= ENERGY_DRIFT_LIMIT
            ),
        }
        cycle = {
            "cycle_index": cycle_index,
            "start_time_seconds": float(start),
            "end_time_seconds": float(end),
            "accepted": all(checks.values()),
            "checks": checks,
            "reference_start": reference_start.tolist(),
            "reference_end": reference_end.tolist(),
            "tangent_matrix_start": tangent_start.tolist(),
            "tangent_matrix_pre_qr": tangent_pre.tolist(),
            **_public_qr_reset(reset),
            "cycle_log_growth": cycle_logs.tolist(),
            "cumulative_log_growth": cumulative_logs.tolist(),
            "cumulative_finite_time_spectrum_per_second": (
                finite_time_spectrum.tolist()
            ),
            "segment_maximum_normalized_reference_energy_drift": (
                segment_max_energy_drift
            ),
            "solver_status": solver_status,
        }
        cycles.append(cycle)

        stored_reference = experiment006.canonicalize_state_angles(segment_reference)
        if cycle_index > 1:
            requested_time = requested_time[1:]
            stored_reference = stored_reference[1:]
            energy_drift = energy_drift[1:]
        reference_times.append(requested_time)
        reference_states.append(stored_reference)
        reference_energy_drifts.append(energy_drift)

        current_reference = reference_end
        current_tangent = reset["tangent_matrix_post"]

    all_reference_time = np.concatenate(reference_times)
    all_reference_state = np.concatenate(reference_states)
    all_energy_drift = np.concatenate(reference_energy_drifts)
    cycle_logs_array = np.asarray(
        [cycle["cycle_log_growth"] for cycle in cycles], dtype=float
    )
    recomputed_cumulative = np.cumsum(cycle_logs_array, axis=0)
    stored_cumulative = np.asarray(
        [cycle["cumulative_log_growth"] for cycle in cycles], dtype=float
    )
    end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in cycles], dtype=float
    )
    recomputed_spectrum = recomputed_cumulative / end_times[:, None]
    stored_spectrum = np.asarray(
        [
            cycle["cumulative_finite_time_spectrum_per_second"]
            for cycle in cycles
        ],
        dtype=float,
    )
    cumulative_bookkeeping_error = float(
        np.max(np.abs(recomputed_cumulative - stored_cumulative))
    )
    spectrum_bookkeeping_error = float(
        np.max(np.abs(recomputed_spectrum - stored_spectrum))
    )
    maximum_energy_drift = float(np.max(all_energy_drift))
    bookkeeping_checks = {
        "all_cycles_accepted": all(cycle["accepted"] for cycle in cycles),
        "cumulative_logs_recompute_within_limit": bool(
            cumulative_bookkeeping_error <= BOOKKEEPING_ERROR_LIMIT
        ),
        "finite_time_spectrum_recomputes_within_limit": bool(
            spectrum_bookkeeping_error <= BOOKKEEPING_ERROR_LIMIT
        ),
        "reference_energy_within_limit": bool(
            maximum_energy_drift <= ENERGY_DRIFT_LIMIT
        ),
        "global_times_strictly_monotonic": bool(
            np.all(np.diff(all_reference_time) > 0.0)
        ),
        "global_output_complete": bool(
            math.isclose(all_reference_time[0], 0.0)
            and math.isclose(all_reference_time[-1], duration)
            and len(all_reference_time)
            == int(round(duration / OUTPUT_INTERVAL_SECONDS)) + 1
        ),
    }
    return {
        "run_id": run_id,
        "accepted": all(bookkeeping_checks.values()),
        "duration_seconds": duration,
        "qr_interval_seconds": QR_INTERVAL_SECONDS,
        "cycle_count": len(cycles),
        "checks": bookkeeping_checks,
        "cycles": cycles,
        "final_cumulative_log_growth": stored_cumulative[-1].tolist(),
        "final_diagnostic_spectrum_per_second": stored_spectrum[-1].tolist(),
        "diagnostic_spectrum_sum_per_second": float(np.sum(stored_spectrum[-1])),
        "maximum_normalized_reference_energy_drift": maximum_energy_drift,
        "maximum_q_orthonormality_error": max(
            cycle["q_orthonormality_error"] for cycle in cycles
        ),
        "maximum_scaled_reconstruction_relative_error": max(
            cycle["scaled_reconstruction_relative_error"] for cycle in cycles
        ),
        "maximum_physical_reconstruction_relative_error": max(
            cycle["physical_reconstruction_relative_error"] for cycle in cycles
        ),
        "maximum_post_metric_orthonormality_error": max(
            cycle["post_metric_orthonormality_error"] for cycle in cycles
        ),
        "maximum_reset_map_error": max(cycle["reset_map_error"] for cycle in cycles),
        "minimum_r_diagonal": min(
            min(cycle["r_diagonal"]) for cycle in cycles
        ),
        "maximum_pre_qr_condition_number": max(
            cycle["pre_qr_condition_number"] for cycle in cycles
        ),
        "cumulative_bookkeeping_error": cumulative_bookkeeping_error,
        "spectrum_bookkeeping_error": spectrum_bookkeeping_error,
        "solver_statistics": {
            "segments": len(solver_statuses),
            "nfev": int(sum(item["nfev"] for item in solver_statuses)),
            "njev": int(sum(item["njev"] for item in solver_statuses)),
            "nlu": int(sum(item["nlu"] for item in solver_statuses)),
            "all_segments_accepted": all(item["accepted"] for item in solver_statuses),
            "max_step_seconds": MAX_STEP_SECONDS,
        },
        "_reference_time": all_reference_time,
        "_reference_state": all_reference_state,
        "_reference_energy_drift": all_energy_drift,
        "_cycle_logs": cycle_logs_array,
        "_cumulative_logs": stored_cumulative,
        "_finite_time_spectrum": stored_spectrum,
    }


def compare_exact_repeats(
    primary: dict[str, Any], repeat: dict[str, Any]
) -> dict[str, Any]:
    if primary["cycle_count"] != repeat["cycle_count"]:
        raise ValueError("Repeat runs must contain the same number of QR cycles.")
    reference_difference = experiment006.wrapped_el_difference(
        primary["_reference_state"][-1], repeat["_reference_state"][-1]
    )
    final_reference_distance = float(
        experiment006.candidate_a_norm(reference_difference)
    )
    max_cycle_log_difference = float(
        np.max(np.abs(primary["_cycle_logs"] - repeat["_cycle_logs"]))
    )
    max_cumulative_log_difference = float(
        np.max(
            np.abs(primary["_cumulative_logs"] - repeat["_cumulative_logs"])
        )
    )
    max_spectrum_difference = float(
        np.max(
            np.abs(
                primary["_finite_time_spectrum"]
                - repeat["_finite_time_spectrum"]
            )
        )
    )
    checks = {
        "repeat_run_valid": repeat["accepted"],
        "cycle_logs_reproducible": bool(
            max_cycle_log_difference <= REPRODUCIBILITY_ERROR_LIMIT
        ),
        "cumulative_logs_reproducible": bool(
            max_cumulative_log_difference <= REPRODUCIBILITY_ERROR_LIMIT
        ),
        "finite_time_spectrum_reproducible": bool(
            max_spectrum_difference <= REPRODUCIBILITY_ERROR_LIMIT
        ),
        "reference_endpoint_reproducible": bool(
            final_reference_distance <= REPRODUCIBILITY_ERROR_LIMIT
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "maximum_cycle_log_difference": max_cycle_log_difference,
        "maximum_cumulative_log_difference": max_cumulative_log_difference,
        "maximum_finite_time_spectrum_difference": max_spectrum_difference,
        "final_reference_candidate_a_distance": final_reference_distance,
    }


def public_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in run.items() if not key.startswith("_") and key != "cycles"}


def run_investigation() -> dict[str, Any]:
    dynamics = experiment006.VariationalDynamics()
    primary = run_qr_primitive(dynamics, run_id="baseline_primary")
    repeat = run_qr_primitive(dynamics, run_id="baseline_exact_repeat")
    reproducibility = compare_exact_repeats(primary, repeat)
    checks = {
        "primary_run_valid": primary["accepted"],
        "exact_repeat_reproducible": reproducibility["accepted"],
    }
    accepted = all(checks.values())
    status = (
        "accepted_for_full_matrix_qr_primitive"
        if accepted
        else "rejected_full_matrix_qr_primitive"
    )
    strongest_claim = (
        "The validated Experiment 006 Euler-Lagrange tangent dynamics admits an "
        "internally coherent four-vector Candidate-A-scaled periodic QR extension "
        "for the declared modest deterministic run."
        if accepted
        else "The full-matrix Candidate-A-scaled QR primitive failed one or more "
        "declared internal-consistency checks."
    )
    summary = {
        "experiment": EXPERIMENT_NAME,
        "status": status,
        "accepted": accepted,
        "question": (
            "Can the validated Euler-Lagrange tangent dynamics be extended from "
            "one tangent vector to a four-vector basis with periodic Candidate-A-scaled "
            "QR renormalisation and self-consistent bookkeeping?"
        ),
        "configuration": {
            "formulation": FORMULATION,
            "state_order": list(STATE_ORDER),
            "reference_initial_state_degrees": (
                experiment006.BASE_STATE_DEGREES.tolist()
            ),
            "tangent_matrix_storage": "physical-coordinate columns",
            "initial_physical_tangent_basis": initial_physical_tangent_basis().tolist(),
            "scaling_matrix_s": scaling_matrix().tolist(),
            "scaled_initial_basis": (
                scaling_matrix() @ initial_physical_tangent_basis()
            ).tolist(),
            "candidate_a_geometry": "||delta_x||_EL=||S delta_x||_2",
            "jacobian_dependency": (
                "Experiment 006 VariationalDynamics; production-derived symbolic "
                "Euler-Lagrange Jacobian independently validated there"
            ),
            "experiment_006_source": (
                "development/chaos_content/experiments/006_variational_dynamics_validation/"
                "variational_dynamics_validation.py"
            ),
            "duration_seconds": RUN_DURATION_SECONDS,
            "qr_interval_seconds": QR_INTERVAL_SECONDS,
            "qr_cycle_count": QR_CYCLE_COUNT,
            "output_interval_seconds": OUTPUT_INTERVAL_SECONDS,
            "solver_policy": experiment006.policy_dict(SOLVER_POLICY),
            "max_step_seconds": MAX_STEP_SECONDS,
            "angular_chart": "reference angles rebased to (-pi, pi] at QR boundaries",
            "qr_sign_convention": "R diagonal forced positive; columns not sorted",
            "exact_repeat_role": "deterministic reproducibility only; not a policy sweep",
        },
        "definitions": {
            "physical_tangent_evolution": "dot(Y)=J(x)Y",
            "scaled_pre_qr_basis": "Z_minus=S Y_minus",
            "qr_factorization": "Z_minus=Q R with positive R diagonal",
            "physical_reset_basis": "Y_plus=S^-1 Q",
            "cycle_growth": "ell_(k,i)=log(abs(R_(k,ii)))",
            "cumulative_diagnostic": "Lambda_(N,i)=sum_k ell_(k,i)/t_N",
        },
        "thresholds": {
            "qr_and_reconstruction_error": QR_ERROR_LIMIT,
            "bookkeeping_error": BOOKKEEPING_ERROR_LIMIT,
            "reproducibility_error": REPRODUCIBILITY_ERROR_LIMIT,
            "minimum_r_diagonal": MINIMUM_R_DIAGONAL,
            "maximum_pre_qr_condition_number": MAXIMUM_PRE_QR_CONDITION_NUMBER,
            "reference_energy_drift": ENERGY_DRIFT_LIMIT,
            "role": "primitive consistency guards, not convergence thresholds",
        },
        "primary_run": public_run_summary(primary),
        "reproducibility": reproducibility,
        "acceptance_checks": checks,
        "strongest_claim": strongest_claim,
        "claim_boundary": (
            "The four finite-time values are diagnostic outputs in fixed basis-column "
            "order. No duration, tolerance, max-step, QR-interval, or basis-initialization "
            "convergence was tested. No maximal Lyapunov exponent, converged spectrum, "
            "Hamiltonian pairing, neutral direction, or chaos classification is established."
        ),
        "next_question": (
            "In a separate experiment, do the full-matrix QR estimates converge under "
            "predeclared duration and numerical refinements?"
            if accepted
            else "Diagnose the failed QR primitive before any convergence study."
        ),
    }
    return {
        "summary": summary,
        "primary": primary,
        "repeat": repeat,
        "reproducibility": reproducibility,
    }


def json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_cycles_json(path: Path, primary: dict[str, Any]) -> None:
    json_write(
        path,
        {
            "experiment": EXPERIMENT_NAME,
            "run_id": primary["run_id"],
            "cycle_count": primary["cycle_count"],
            "cycles": primary["cycles"],
        },
    )


def _matrix_fields(prefix: str) -> list[str]:
    return [f"{prefix}_{row + 1}{column + 1}" for row in range(4) for column in range(4)]


def write_cycles_csv(path: Path, primary: dict[str, Any]) -> None:
    fields = [
        "cycle_index",
        "start_time_seconds",
        "end_time_seconds",
        "accepted",
        *[f"reference_start_{name}" for name in STATE_ORDER],
        *[f"reference_end_{name}" for name in STATE_ORDER],
        *_matrix_fields("y_start"),
        *_matrix_fields("y_pre"),
        *_matrix_fields("z_pre"),
        *_matrix_fields("q"),
        *_matrix_fields("r"),
        *_matrix_fields("y_post"),
        *[f"r_diagonal_{index + 1}" for index in range(4)],
        *[f"cycle_log_{index + 1}" for index in range(4)],
        *[f"cumulative_log_{index + 1}" for index in range(4)],
        *[f"finite_time_value_{index + 1}_per_s" for index in range(4)],
        "q_orthonormality_error",
        "scaled_reconstruction_relative_error",
        "physical_reconstruction_relative_error",
        "post_metric_orthonormality_error",
        "reset_map_error",
        "pre_qr_condition_number",
        "reference_energy_drift",
        "solver_nfev",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for cycle in primary["cycles"]:
            row: dict[str, Any] = {
                "cycle_index": cycle["cycle_index"],
                "start_time_seconds": cycle["start_time_seconds"],
                "end_time_seconds": cycle["end_time_seconds"],
                "accepted": cycle["accepted"],
                "q_orthonormality_error": cycle["q_orthonormality_error"],
                "scaled_reconstruction_relative_error": cycle[
                    "scaled_reconstruction_relative_error"
                ],
                "physical_reconstruction_relative_error": cycle[
                    "physical_reconstruction_relative_error"
                ],
                "post_metric_orthonormality_error": cycle[
                    "post_metric_orthonormality_error"
                ],
                "reset_map_error": cycle["reset_map_error"],
                "pre_qr_condition_number": cycle["pre_qr_condition_number"],
                "reference_energy_drift": cycle[
                    "segment_maximum_normalized_reference_energy_drift"
                ],
                "solver_nfev": cycle["solver_status"]["nfev"],
            }
            for prefix, values in (
                ("reference_start", cycle["reference_start"]),
                ("reference_end", cycle["reference_end"]),
            ):
                for name, value in zip(STATE_ORDER, values):
                    row[f"{prefix}_{name}"] = value
            for prefix, matrix in (
                ("y_start", cycle["tangent_matrix_start"]),
                ("y_pre", cycle["tangent_matrix_pre_qr"]),
                ("z_pre", cycle["scaled_pre"]),
                ("q", cycle["orthogonal_q"]),
                ("r", cycle["upper_r"]),
                ("y_post", cycle["tangent_matrix_post"]),
            ):
                for field, value in zip(_matrix_fields(prefix), np.ravel(matrix)):
                    row[field] = value
            for prefix, values in (
                ("r_diagonal", cycle["r_diagonal"]),
                ("cycle_log", cycle["cycle_log_growth"]),
                ("cumulative_log", cycle["cumulative_log_growth"]),
                (
                    "finite_time_value",
                    cycle["cumulative_finite_time_spectrum_per_second"],
                ),
            ):
                suffix = "_per_s" if prefix == "finite_time_value" else ""
                for index, value in enumerate(values, start=1):
                    row[f"{prefix}_{index}{suffix}"] = value
            writer.writerow(row)


def write_reference_csv(path: Path, primary: dict[str, Any]) -> None:
    fields = ["time_seconds", *STATE_ORDER, "normalized_energy_drift"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for time_value, state, drift in zip(
            primary["_reference_time"],
            primary["_reference_state"],
            primary["_reference_energy_drift"],
        ):
            row = {
                "time_seconds": time_value,
                "normalized_energy_drift": drift,
            }
            row.update(dict(zip(STATE_ORDER, state)))
            writer.writerow(row)


def load_pyplot():
    import matplotlib.pyplot as plt

    return plt


def save_figure(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    load_pyplot().close(fig)


def write_plots(output_dir: Path, primary: dict[str, Any]) -> list[Path]:
    plt = load_pyplot()
    end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in primary["cycles"]]
    )
    spectrum = primary["_finite_time_spectrum"]
    paths: list[Path] = []

    path = output_dir / "01_cumulative_finite_time_spectrum.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for column in range(4):
        axis.plot(
            end_times,
            spectrum[:, column],
            marker="o",
            markersize=3,
            label=f"basis column {column + 1}",
        )
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set(
        xlabel="time / s",
        ylabel="cumulative finite-time value / s$^{-1}$",
        title="Diagnostic full-matrix QR values (not a converged spectrum)",
    )
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "02_qr_consistency_and_reference_validity.png"
    fig, axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
    error_fields = (
        ("q_orthonormality_error", "Q orthonormality"),
        ("scaled_reconstruction_relative_error", "scaled reconstruction"),
        ("physical_reconstruction_relative_error", "physical reconstruction"),
        ("post_metric_orthonormality_error", "post-reset metric"),
    )
    for field, label in error_fields:
        axes[0].semilogy(
            end_times,
            np.maximum([cycle[field] for cycle in primary["cycles"]], 1.0e-18),
            label=label,
        )
    axes[0].axhline(QR_ERROR_LIMIT, color="red", linestyle="--", label="limit")
    axes[0].set(ylabel="error", title="QR and reset consistency")
    axes[0].legend(fontsize=8)

    axes[1].semilogy(
        end_times,
        [cycle["pre_qr_condition_number"] for cycle in primary["cycles"]],
        marker="o",
        markersize=3,
    )
    axes[1].axhline(
        MAXIMUM_PRE_QR_CONDITION_NUMBER, color="red", linestyle="--"
    )
    axes[1].set(ylabel="condition number", title="Pre-QR scaled basis conditioning")

    axes[2].semilogy(
        primary["_reference_time"],
        np.maximum(primary["_reference_energy_drift"], 1.0e-18),
    )
    axes[2].axhline(ENERGY_DRIFT_LIMIT, color="red", linestyle="--")
    axes[2].set(
        xlabel="time / s",
        ylabel="normalized drift",
        title="Reference energy validity",
    )
    for axis in axes:
        axis.grid(True, which="both", alpha=0.25)
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
    cycles_json_path = output_dir / "cycles.json"
    cycles_csv_path = output_dir / "cycles.csv"
    reference_path = output_dir / "reference_timeseries.csv"
    json_write(summary_path, result["summary"])
    write_cycles_json(cycles_json_path, result["primary"])
    write_cycles_csv(cycles_csv_path, result["primary"])
    write_reference_csv(reference_path, result["primary"])
    paths = [summary_path, cycles_json_path, cycles_csv_path, reference_path]
    if plots:
        paths.extend(write_plots(output_dir, result["primary"]))

    manifest_path = output_dir / "manifest.json"
    manifest = {
        "experiment": EXPERIMENT_NAME,
        "output_role": (
            "exploratory Experiment 007 QR-primitive evidence; not a converged "
            "Lyapunov spectrum or production data"
        ),
        "source": str(Path(__file__).relative_to(REPOSITORY_ROOT)),
        "experiment_006_dependency": str(
            (EXPERIMENT_006_ROOT / "variational_dynamics_validation.py").relative_to(
                REPOSITORY_ROOT
            )
        ),
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
    primary = result["primary"]
    assert summary["accepted"] == all(summary["acceptance_checks"].values())
    assert primary["cycle_count"] == QR_CYCLE_COUNT
    assert len(primary["cycles"]) == QR_CYCLE_COUNT
    np.testing.assert_allclose(
        scaling_matrix() @ initial_physical_tangent_basis(),
        np.eye(4),
        rtol=0.0,
        atol=1.0e-15,
    )
    recomputed_logs = np.cumsum(primary["_cycle_logs"], axis=0)
    np.testing.assert_allclose(
        recomputed_logs,
        primary["_cumulative_logs"],
        rtol=0.0,
        atol=BOOKKEEPING_ERROR_LIMIT,
    )
    end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in primary["cycles"]]
    )
    np.testing.assert_allclose(
        recomputed_logs / end_times[:, None],
        primary["_finite_time_spectrum"],
        rtol=0.0,
        atol=BOOKKEEPING_ERROR_LIMIT,
    )
    if summary["accepted"]:
        assert primary["accepted"]
        assert result["reproducibility"]["accepted"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "development/chaos_content/outputs/full_matrix_qr_tangent_dynamics/baseline"
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
                "diagnostic_spectrum_per_second": summary["primary_run"][
                    "final_diagnostic_spectrum_per_second"
                ],
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
