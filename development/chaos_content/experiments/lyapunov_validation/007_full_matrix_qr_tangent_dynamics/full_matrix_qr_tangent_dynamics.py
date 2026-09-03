"""Run the Experiment 007 QR primitive or its predeclared convergence study."""

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
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_006_ROOT = (
    EXPERIMENT_ROOT.parents[1]
    / "foundations"
    / "006_variational_dynamics_validation"
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

CONVERGENCE_DURATION_SECONDS = 80.0
DURATION_CHECKPOINTS_SECONDS = (20.0, 40.0, 80.0)
SHORT_QR_INTERVAL_SECONDS = 0.125
LONG_QR_INTERVAL_SECONDS = 0.5

SOLVER_POLICY = experiment006.SIMPLE_REFERENCE_SOLVER_POLICY
STRICTER_POLICY = experiment006.STRICTER_POLICY
MAX_STEP_SECONDS = experiment006.BASELINE_MAX_STEP
HALF_MAX_STEP_SECONDS = experiment006.REFINED_MAX_STEP
ENERGY_DRIFT_LIMIT = experiment006.ENERGY_DRIFT_LIMIT

QR_ERROR_LIMIT = 1.0e-12
BOOKKEEPING_ERROR_LIMIT = 1.0e-12
REPRODUCIBILITY_ERROR_LIMIT = 1.0e-12
MINIMUM_R_DIAGONAL = 1.0e-14
MAXIMUM_PRE_QR_CONDITION_NUMBER = 1.0e12

MAX_DURATION_CHANGE_20_TO_40_PER_SECOND = 0.10
MAX_DURATION_CHANGE_40_TO_80_PER_SECOND = 0.05
MAX_FINAL_QUARTER_RANGE_PER_SECOND = 0.05
CLEAR_NONCONVERGENCE_DURATION_DIFFERENCE_PER_SECOND = 0.10
MAX_TOLERANCE_SPECTRUM_DIFFERENCE_PER_SECOND = 0.01
MAX_STEP_SPECTRUM_DIFFERENCE_PER_SECOND = 0.01
MAX_QR_INTERVAL_SPECTRUM_DIFFERENCE_PER_SECOND = 0.02
MAX_ONE_VECTOR_DIFFERENCE_PER_SECOND = 0.01


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


def replay_cumulative_log_growth(
    initial_cumulative_log_growth: np.ndarray,
    cycle_log_growth: np.ndarray,
) -> np.ndarray:
    """Replay the runner's componentwise accumulation order exactly.

    A continued run begins with nonzero accumulated logs. Adding that initial
    vector after ``np.cumsum`` changes floating-point association and can make
    a correct restart fail the absolute bookkeeping check. The runner itself
    updates one cycle at a time, so its independent check must do the same.
    """

    running = np.asarray(initial_cumulative_log_growth, dtype=float).copy()
    rows = []
    for cycle_logs in np.asarray(cycle_log_growth, dtype=float):
        running = running + cycle_logs
        rows.append(running.copy())
    return np.asarray(rows, dtype=float)


def deterministic_cycle_times(
    duration: float = RUN_DURATION_SECONDS,
    qr_interval: float = QR_INTERVAL_SECONDS,
) -> np.ndarray:
    if not np.isfinite(qr_interval) or qr_interval <= 0.0:
        raise ValueError("QR interval must be positive and finite.")
    cycle_count = int(round(duration / qr_interval))
    if cycle_count <= 0 or not math.isclose(
        cycle_count * qr_interval,
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
    qr_interval: float = QR_INTERVAL_SECONDS,
    policy: Any = SOLVER_POLICY,
    max_step: float = MAX_STEP_SECONDS,
    initial_reference: np.ndarray | None = None,
    initial_tangent_matrix: np.ndarray | None = None,
    initial_cumulative_log_growth: np.ndarray | None = None,
    start_time_seconds: float = 0.0,
    completed_cycle_count: int = 0,
    diagnostic_energy_baseline: float | None = None,
) -> dict[str, Any]:
    """Run one fixed-policy full-matrix QR trajectory.

    The default path retains the original Experiment 007 semantics.  The
    optional boundary-state arguments resume a previously completed QR run;
    in that mode the saved locally canonical reference and post-QR tangent
    matrix are consumed without reconstruction.
    """

    if not np.isfinite(start_time_seconds) or start_time_seconds < 0.0:
        raise ValueError("start_time_seconds must be finite and nonnegative.")
    if not isinstance(completed_cycle_count, int) or completed_cycle_count < 0:
        raise ValueError("completed_cycle_count must be a nonnegative integer.")
    if not math.isclose(
        completed_cycle_count * qr_interval,
        start_time_seconds,
        rel_tol=0.0,
        abs_tol=1.0e-13,
    ):
        raise ValueError("Cycle count and elapsed time do not identify one QR boundary.")
    continuation_requested = bool(
        start_time_seconds > 0.0
        or completed_cycle_count > 0
        or initial_tangent_matrix is not None
        or initial_cumulative_log_growth is not None
        or diagnostic_energy_baseline is not None
    )
    if continuation_requested and initial_reference is None:
        raise ValueError("A continuation requires an explicit terminal EL reference.")
    boundaries = start_time_seconds + deterministic_cycle_times(duration, qr_interval)
    current_reference = np.array(
        experiment006.BASE_STATE_RADIANS
        if initial_reference is None
        else initial_reference,
        dtype=float,
        copy=True,
    )
    if current_reference.shape != (4,) or not np.all(np.isfinite(current_reference)):
        raise ValueError("Initial EL reference must be one finite four-state.")
    if continuation_requested:
        if np.any(current_reference[:2] <= -math.pi) or np.any(
            current_reference[:2] > math.pi
        ):
            raise ValueError("Restart EL angles must already use the local principal chart.")
    else:
        current_reference = experiment006.canonicalize_state_angles(current_reference)
    initial_reference_state = np.array(current_reference, copy=True)
    current_tangent = np.array(
        initial_physical_tangent_basis()
        if initial_tangent_matrix is None
        else initial_tangent_matrix,
        dtype=float,
        copy=True,
    )
    if current_tangent.shape != (4, 4) or not np.all(np.isfinite(current_tangent)):
        raise ValueError("Initial EL tangent matrix must be one finite 4x4 array.")
    initial_tangent_state = np.array(current_tangent, copy=True)
    initial_energy = float(
        experiment006.simple_energy(current_reference)
        if diagnostic_energy_baseline is None
        else diagnostic_energy_baseline
    )
    if not np.isfinite(initial_energy):
        raise ValueError("Diagnostic energy baseline must be finite.")
    cumulative_logs = np.array(
        np.zeros(4)
        if initial_cumulative_log_growth is None
        else initial_cumulative_log_growth,
        dtype=float,
        copy=True,
    )
    if cumulative_logs.shape != (4,) or not np.all(np.isfinite(cumulative_logs)):
        raise ValueError("Initial cumulative log growth must be one finite four-vector.")
    initial_cumulative_logs = np.array(cumulative_logs, copy=True)
    cycles: list[dict[str, Any]] = []
    reference_times: list[np.ndarray] = []
    reference_states: list[np.ndarray] = []
    reference_energy_drifts: list[np.ndarray] = []
    solver_statuses: list[dict[str, Any]] = []

    for local_cycle_index, (start, end) in enumerate(
        zip(boundaries[:-1], boundaries[1:]), start=1
    ):
        cycle_index = completed_cycle_count + local_cycle_index
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
            policy,
            max_step=max_step,
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
            "qr_interval_seconds": qr_interval,
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
        if local_cycle_index > 1:
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
    recomputed_cumulative = replay_cumulative_log_growth(
        initial_cumulative_logs, cycle_logs_array
    )
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
    expected_output_count = 1 + sum(
        len(requested_cycle_times(float(start), float(end))) - 1
        for start, end in zip(boundaries[:-1], boundaries[1:])
    )
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
            math.isclose(all_reference_time[0], start_time_seconds)
            and math.isclose(all_reference_time[-1], boundaries[-1])
            and len(all_reference_time) == expected_output_count
        ),
    }
    return {
        "run_id": run_id,
        "accepted": all(bookkeeping_checks.values()),
        "duration_seconds": float(boundaries[-1]),
        "integration_span_seconds": duration,
        "start_time_seconds": start_time_seconds,
        "elapsed_time_seconds": float(boundaries[-1]),
        "qr_interval_seconds": qr_interval,
        "solver_policy": experiment006.policy_dict(policy),
        "max_step_seconds": max_step,
        "cycle_count": completed_cycle_count + len(cycles),
        "segment_cycle_count": len(cycles),
        "completed_cycle_count_at_start": completed_cycle_count,
        "continued_from_qr_boundary": continuation_requested,
        "initial_reference": initial_reference_state.tolist(),
        "initial_tangent_basis": initial_tangent_state.tolist(),
        "initial_cumulative_log_growth": initial_cumulative_logs.tolist(),
        "diagnostic_energy_baseline_joules": initial_energy,
        "checks": bookkeeping_checks,
        "cycles": cycles,
        "final_cumulative_log_growth": stored_cumulative[-1].tolist(),
        "final_diagnostic_spectrum_per_second": stored_spectrum[-1].tolist(),
        "terminal_reference_state": current_reference.tolist(),
        "terminal_tangent_matrix_post_qr": current_tangent.tolist(),
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
            "max_step_seconds": max_step,
        },
        "_reference_time": all_reference_time,
        "_reference_state": all_reference_state,
        "_reference_energy_drift": all_energy_drift,
        "_cycle_logs": cycle_logs_array,
        "_cumulative_logs": stored_cumulative,
        "_finite_time_spectrum": stored_spectrum,
        "_terminal_reference_state": np.array(current_reference, copy=True),
        "_terminal_tangent_matrix_post_qr": np.array(current_tangent, copy=True),
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


def spectrum_at_time(run: dict[str, Any], time_seconds: float) -> np.ndarray:
    end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in run["cycles"]], dtype=float
    )
    matches = np.flatnonzero(
        np.isclose(end_times, time_seconds, rtol=0.0, atol=1.0e-13)
    )
    if len(matches) != 1:
        raise ValueError(f"Run does not contain one QR boundary at {time_seconds} s.")
    return np.asarray(
        run["cycles"][int(matches[0])][
            "cumulative_finite_time_spectrum_per_second"
        ],
        dtype=float,
    )


def hamiltonian_structure_diagnostics(spectrum: np.ndarray) -> dict[str, Any]:
    """Return non-acceptance structural diagnostics for one four-vector."""

    sorted_spectrum = np.sort(np.asarray(spectrum, dtype=float))[::-1]
    return {
        "sorted_spectrum_per_second": sorted_spectrum.tolist(),
        "sum_per_second": float(np.sum(sorted_spectrum)),
        "outer_pair_sum_per_second": float(
            sorted_spectrum[0] + sorted_spectrum[3]
        ),
        "inner_pair_sum_per_second": float(
            sorted_spectrum[1] + sorted_spectrum[2]
        ),
        "middle_absolute_values_per_second": [
            float(abs(sorted_spectrum[1])),
            float(abs(sorted_spectrum[2])),
        ],
        "acceptance_role": "interpretive only; not a finite-time convergence target",
    }


def duration_convergence_analysis(baseline: dict[str, Any]) -> dict[str, Any]:
    spectra = {
        f"{int(time_seconds)}s": spectrum_at_time(baseline, time_seconds)
        for time_seconds in DURATION_CHECKPOINTS_SECONDS
    }
    change_20_to_40 = np.abs(spectra["40s"] - spectra["20s"])
    change_40_to_80 = np.abs(spectra["80s"] - spectra["40s"])
    late_cycles = [
        cycle
        for cycle in baseline["cycles"]
        if cycle["end_time_seconds"] >= 60.0 - 1.0e-13
    ]
    late_spectrum = np.asarray(
        [
            cycle["cumulative_finite_time_spectrum_per_second"]
            for cycle in late_cycles
        ],
        dtype=float,
    )
    final_quarter_ranges = np.ptp(late_spectrum, axis=0)
    checks = {
        "20_to_40_max_component_change_within_0.10_per_second": bool(
            np.max(change_20_to_40)
            <= MAX_DURATION_CHANGE_20_TO_40_PER_SECOND
        ),
        "40_to_80_max_component_change_within_0.05_per_second": bool(
            np.max(change_40_to_80)
            <= MAX_DURATION_CHANGE_40_TO_80_PER_SECOND
        ),
        "all_final_quarter_component_ranges_within_0.05_per_second": bool(
            np.all(final_quarter_ranges <= MAX_FINAL_QUARTER_RANGE_PER_SECOND)
        ),
    }
    clearly_not_converged = bool(
        np.max(change_40_to_80)
        > CLEAR_NONCONVERGENCE_DURATION_DIFFERENCE_PER_SECOND
        or np.max(final_quarter_ranges)
        > CLEAR_NONCONVERGENCE_DURATION_DIFFERENCE_PER_SECOND
    )
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "checkpoint_spectra_per_second": {
            key: value.tolist() for key, value in spectra.items()
        },
        "absolute_component_change_20_to_40_per_second": (
            change_20_to_40.tolist()
        ),
        "maximum_component_change_20_to_40_per_second": float(
            np.max(change_20_to_40)
        ),
        "absolute_component_change_40_to_80_per_second": (
            change_40_to_80.tolist()
        ),
        "maximum_component_change_40_to_80_per_second": float(
            np.max(change_40_to_80)
        ),
        "final_quarter_component_ranges_per_second": final_quarter_ranges.tolist(),
        "maximum_final_quarter_range_per_second": float(
            np.max(final_quarter_ranges)
        ),
        "clearly_not_converged_by_predeclared_rule": clearly_not_converged,
        "hamiltonian_diagnostics": {
            key: hamiltonian_structure_diagnostics(value)
            for key, value in spectra.items()
        },
    }


def compare_spectrum_runs(
    baseline: dict[str, Any],
    comparison: dict[str, Any],
    *,
    absolute_limit_per_second: float,
) -> dict[str, Any]:
    if not math.isclose(
        baseline["duration_seconds"],
        comparison["duration_seconds"],
        rel_tol=0.0,
        abs_tol=1.0e-13,
    ):
        raise ValueError("Spectrum comparisons require equal durations.")
    baseline_spectrum = np.asarray(
        baseline["final_diagnostic_spectrum_per_second"], dtype=float
    )
    comparison_spectrum = np.asarray(
        comparison["final_diagnostic_spectrum_per_second"], dtype=float
    )
    component_difference = np.abs(comparison_spectrum - baseline_spectrum)
    reference_difference = experiment006.wrapped_el_difference(
        baseline["_reference_state"][-1], comparison["_reference_state"][-1]
    )
    reference_distance = float(
        experiment006.candidate_a_norm(reference_difference)
    )
    checks = {
        "comparison_run_numerically_valid": comparison["accepted"],
        "whole_spectrum_within_absolute_limit": bool(
            np.max(component_difference) <= absolute_limit_per_second
        ),
    }
    return {
        "baseline_run_id": baseline["run_id"],
        "comparison_run_id": comparison["run_id"],
        "accepted": all(checks.values()),
        "checks": checks,
        "absolute_limit_per_second": absolute_limit_per_second,
        "comparison_spectrum_per_second": comparison_spectrum.tolist(),
        "absolute_component_differences_per_second": component_difference.tolist(),
        "maximum_absolute_component_difference_per_second": float(
            np.max(component_difference)
        ),
        "final_reference_candidate_a_distance": reference_distance,
        "hamiltonian_diagnostics": hamiltonian_structure_diagnostics(
            comparison_spectrum
        ),
    }


def run_one_vector_renormalisation(
    dynamics: experiment006.VariationalDynamics,
    *,
    duration: float = CONVERGENCE_DURATION_SECONDS,
    qr_interval: float = QR_INTERVAL_SECONDS,
    policy: Any = SOLVER_POLICY,
    max_step: float = MAX_STEP_SECONDS,
) -> dict[str, Any]:
    """Conventional one-vector check using the first QR basis column."""

    boundaries = deterministic_cycle_times(duration, qr_interval)
    reference = np.array(experiment006.BASE_STATE_RADIANS, copy=True)
    tangent = initial_physical_tangent_basis()[:, 0]
    initial_energy = float(experiment006.simple_energy(reference))
    cumulative_log = 0.0
    cycles: list[dict[str, Any]] = []
    maximum_energy_drift = 0.0
    solver_statuses: list[dict[str, Any]] = []

    for cycle_index, (start, end) in enumerate(
        zip(boundaries[:-1], boundaries[1:]), start=1
    ):
        augmented_start = np.concatenate((reference, tangent))

        def one_vector_rhs(time_value: float, augmented: np.ndarray) -> np.ndarray:
            state = augmented[:4]
            vector = augmented[4:]
            return np.concatenate(
                (
                    dynamics.flow(state, time_value),
                    dynamics.jacobian(state, time_value) @ vector,
                )
            )

        segment = experiment006.solve_one_segment(
            one_vector_rhs,
            augmented_start,
            requested_cycle_times(float(start), float(end)),
            policy,
            max_step=max_step,
        )
        solver_status = segment["solver_status"] | {
            "accepted": segment["accepted"]
        }
        solver_statuses.append(solver_status)
        if not segment["accepted"]:
            raise RuntimeError(f"One-vector cycle {cycle_index} integration failed.")
        reference_raw = segment["state"][-1, :4]
        tangent_pre = segment["state"][-1, 4:]
        scaled_pre = scaling_matrix() @ tangent_pre
        magnitude = float(np.linalg.norm(scaled_pre))
        cycle_log = float(math.log(magnitude))
        cumulative_log += cycle_log
        tangent = inverse_scaling_matrix() @ (scaled_pre / magnitude)
        reference = experiment006.canonicalize_state_angles(reference_raw)
        energy = experiment006.simple_energy(segment["state"][:, :4])
        segment_energy_drift = float(
            np.max(np.abs(energy - initial_energy) / experiment006.energy_scale())
        )
        maximum_energy_drift = max(maximum_energy_drift, segment_energy_drift)
        cycles.append(
            {
                "cycle_index": cycle_index,
                "end_time_seconds": float(end),
                "pre_reset_candidate_a_norm": magnitude,
                "cycle_log_growth": cycle_log,
                "cumulative_log_growth": cumulative_log,
                "cumulative_rate_per_second": cumulative_log / float(end),
                "post_reset_candidate_a_norm": float(
                    experiment006.candidate_a_norm(tangent)
                ),
                "segment_maximum_normalized_reference_energy_drift": (
                    segment_energy_drift
                ),
                "solver_status": solver_status,
            }
        )
    accepted = bool(
        all(item["accepted"] for item in solver_statuses)
        and np.all(np.isfinite([cycle["cycle_log_growth"] for cycle in cycles]))
        and maximum_energy_drift <= ENERGY_DRIFT_LIMIT
        and max(
            abs(cycle["post_reset_candidate_a_norm"] - 1.0) for cycle in cycles
        )
        <= QR_ERROR_LIMIT
    )
    return {
        "accepted": accepted,
        "duration_seconds": duration,
        "qr_interval_seconds": qr_interval,
        "solver_policy": experiment006.policy_dict(policy),
        "max_step_seconds": max_step,
        "cycle_count": len(cycles),
        "initial_direction": initial_physical_tangent_basis()[:, 0].tolist(),
        "final_cumulative_log_growth": cumulative_log,
        "final_cumulative_rate_per_second": cumulative_log / duration,
        "maximum_normalized_reference_energy_drift": maximum_energy_drift,
        "maximum_post_reset_candidate_a_norm_error": max(
            abs(cycle["post_reset_candidate_a_norm"] - 1.0) for cycle in cycles
        ),
        "solver_statistics": {
            "segments": len(solver_statuses),
            "nfev": int(sum(item["nfev"] for item in solver_statuses)),
            "all_segments_accepted": all(item["accepted"] for item in solver_statuses),
        },
        "cycles": cycles,
    }


def compare_one_vector_to_qr(
    baseline: dict[str, Any], one_vector: dict[str, Any]
) -> dict[str, Any]:
    qr_first = float(baseline["final_diagnostic_spectrum_per_second"][0])
    vector_rate = float(one_vector["final_cumulative_rate_per_second"])
    difference = abs(vector_rate - qr_first)
    checks = {
        "one_vector_run_valid": one_vector["accepted"],
        "first_qr_component_within_0.01_per_second": bool(
            difference <= MAX_ONE_VECTOR_DIFFERENCE_PER_SECOND
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "qr_first_component_per_second": qr_first,
        "one_vector_rate_per_second": vector_rate,
        "absolute_difference_per_second": difference,
        "absolute_limit_per_second": MAX_ONE_VECTOR_DIFFERENCE_PER_SECOND,
    }


def public_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in run.items() if not key.startswith("_") and key != "cycles"}


def run_primitive_investigation() -> dict[str, Any]:
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
                "development/chaos_content/experiments/foundations/"
                "006_variational_dynamics_validation/"
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
        "mode": "primitive",
        "summary": summary,
        "primary": primary,
        "repeat": repeat,
        "reproducibility": reproducibility,
    }


def run_convergence_investigation() -> dict[str, Any]:
    """Execute exactly the compact convergence matrix declared in the README."""

    dynamics = experiment006.VariationalDynamics()
    run_specs = {
        "baseline": ("baseline_80s", SOLVER_POLICY, MAX_STEP_SECONDS, QR_INTERVAL_SECONDS),
        "strict_tolerance": (
            "strict_tolerance_80s",
            STRICTER_POLICY,
            MAX_STEP_SECONDS,
            QR_INTERVAL_SECONDS,
        ),
        "half_max_step": (
            "half_max_step_80s",
            SOLVER_POLICY,
            HALF_MAX_STEP_SECONDS,
            QR_INTERVAL_SECONDS,
        ),
        "short_qr_interval": (
            "short_qr_interval_80s",
            SOLVER_POLICY,
            MAX_STEP_SECONDS,
            SHORT_QR_INTERVAL_SECONDS,
        ),
        "long_qr_interval": (
            "long_qr_interval_80s",
            SOLVER_POLICY,
            MAX_STEP_SECONDS,
            LONG_QR_INTERVAL_SECONDS,
        ),
    }
    runs = {
        name: run_qr_primitive(
            dynamics,
            run_id=run_id,
            duration=CONVERGENCE_DURATION_SECONDS,
            qr_interval=qr_interval,
            policy=policy,
            max_step=max_step,
        )
        for name, (run_id, policy, max_step, qr_interval) in run_specs.items()
    }
    baseline = runs["baseline"]
    one_vector = run_one_vector_renormalisation(
        dynamics,
        duration=CONVERGENCE_DURATION_SECONDS,
        qr_interval=QR_INTERVAL_SECONDS,
        policy=SOLVER_POLICY,
        max_step=MAX_STEP_SECONDS,
    )
    duration_analysis = duration_convergence_analysis(baseline)
    comparison_limits = {
        "strict_tolerance": MAX_TOLERANCE_SPECTRUM_DIFFERENCE_PER_SECOND,
        "half_max_step": MAX_STEP_SPECTRUM_DIFFERENCE_PER_SECOND,
        "short_qr_interval": MAX_QR_INTERVAL_SPECTRUM_DIFFERENCE_PER_SECOND,
        "long_qr_interval": MAX_QR_INTERVAL_SPECTRUM_DIFFERENCE_PER_SECOND,
    }
    comparisons = {
        name: compare_spectrum_runs(
            baseline,
            runs[name],
            absolute_limit_per_second=limit,
        )
        for name, limit in comparison_limits.items()
    }
    one_vector_comparison = compare_one_vector_to_qr(baseline, one_vector)
    validity_checks = {
        f"{name}_primitive_valid": run["accepted"]
        for name, run in runs.items()
    } | {"one_vector_valid": one_vector["accepted"]}
    numerical_policy_checks = {
        f"{name}_comparison_accepted": comparison["accepted"]
        for name, comparison in comparisons.items()
    } | {"one_vector_comparison_accepted": one_vector_comparison["accepted"]}
    validity_accepted = all(validity_checks.values())
    policy_accepted = all(numerical_policy_checks.values())

    if not validity_accepted or not policy_accepted:
        classification = "numerically_unresolved"
        status = "unresolved_numerical_policy_convergence"
        strongest_claim = (
            "The accepted QR primitive remains executable, but the tested long-time "
            "spectrum is numerically unresolved under at least one declared policy "
            "or validity comparison."
        )
        next_question = (
            "Do substantially longer, still predeclared Euler-Lagrange QR runs "
            "cause the policy-separated cumulative spectra to approach one common "
            "asymptotic vector, or does their separation persist?"
        )
    elif duration_analysis["accepted"]:
        classification = "converged_sufficiently_for_controlled_reference_case"
        status = "accepted_controlled_reference_qr_spectrum_convergence"
        strongest_claim = (
            "For the single declared Euler-Lagrange reference trajectory and "
            "Candidate-A geometry, the cumulative four-component QR spectrum is "
            "stable under the predeclared duration and numerical refinements."
        )
        next_question = (
            "Does an independently formulated canonical/Hamiltonian tangent "
            "calculation reproduce the controlled Euler-Lagrange spectrum?"
        )
    elif duration_analysis["clearly_not_converged_by_predeclared_rule"]:
        classification = "clearly_not_converged"
        status = "rejected_duration_convergence"
        strongest_claim = (
            "The full-matrix QR calculation is numerically controlled under the "
            "declared policies, but its cumulative spectrum is clearly not converged "
            "over 20--80 seconds."
        )
        next_question = (
            "Do substantially longer cumulative runs reduce the observed slow "
            "duration drift without reintroducing numerical-policy disagreement?"
        )
    else:
        classification = "unresolved_at_tested_durations"
        status = "unresolved_duration_convergence"
        strongest_claim = (
            "The full-matrix QR calculation is numerically controlled under the "
            "declared policies, but spectrum convergence remains unresolved through "
            "80 seconds."
        )
        next_question = (
            "Does one predeclared duration extension resolve the remaining slow "
            "finite-time drift while preserving numerical-policy agreement?"
        )

    accepted = classification == "converged_sufficiently_for_controlled_reference_case"
    summary = {
        "experiment": EXPERIMENT_NAME,
        "iteration": "convergence investigation following accepted QR primitive",
        "status": status,
        "classification": classification,
        "accepted": accepted,
        "question": (
            "Does periodic QR renormalisation of the validated Euler-Lagrange tangent "
            "flow yield a four-dimensional cumulative finite-time spectrum that "
            "converges under appropriate numerical refinement?"
        ),
        "configuration": {
            "formulation": FORMULATION,
            "state_order": list(STATE_ORDER),
            "reference_initial_state_degrees": experiment006.BASE_STATE_DEGREES.tolist(),
            "candidate_a_geometry": "||delta_x||_EL=||S delta_x||_2",
            "scaling_matrix_s": scaling_matrix().tolist(),
            "tangent_matrix_storage": "physical-coordinate columns",
            "initial_physical_tangent_basis": initial_physical_tangent_basis().tolist(),
            "jacobian_dependency": "validated Experiment 006 VariationalDynamics",
            "angular_chart": "reference angles rebased to (-pi, pi] at QR boundaries",
            "qr_sign_convention": "R diagonal forced positive; columns not sorted",
            "baseline_duration_seconds": CONVERGENCE_DURATION_SECONDS,
            "duration_checkpoints_seconds": list(DURATION_CHECKPOINTS_SECONDS),
            "baseline_solver_policy": experiment006.policy_dict(SOLVER_POLICY),
            "strict_solver_policy": experiment006.policy_dict(STRICTER_POLICY),
            "baseline_max_step_seconds": MAX_STEP_SECONDS,
            "half_max_step_seconds": HALF_MAX_STEP_SECONDS,
            "baseline_qr_interval_seconds": QR_INTERVAL_SECONDS,
            "short_qr_interval_seconds": SHORT_QR_INTERVAL_SECONDS,
            "long_qr_interval_seconds": LONG_QR_INTERVAL_SECONDS,
            "one_vector_role": "independent check of the first QR column only",
        },
        "convergence_criteria": {
            "duration": {
                "maximum_component_change_20_to_40_per_second": MAX_DURATION_CHANGE_20_TO_40_PER_SECOND,
                "maximum_component_change_40_to_80_per_second": MAX_DURATION_CHANGE_40_TO_80_PER_SECOND,
                "maximum_each_component_range_60_to_80_per_second": MAX_FINAL_QUARTER_RANGE_PER_SECOND,
                "clear_nonconvergence_threshold_per_second": CLEAR_NONCONVERGENCE_DURATION_DIFFERENCE_PER_SECOND,
            },
            "numerical_policy_at_80_seconds": {
                "strict_tolerance_max_component_difference_per_second": MAX_TOLERANCE_SPECTRUM_DIFFERENCE_PER_SECOND,
                "half_max_step_max_component_difference_per_second": MAX_STEP_SPECTRUM_DIFFERENCE_PER_SECOND,
                "each_qr_interval_max_component_difference_per_second": MAX_QR_INTERVAL_SPECTRUM_DIFFERENCE_PER_SECOND,
                "one_vector_first_component_difference_per_second": MAX_ONE_VECTOR_DIFFERENCE_PER_SECOND,
            },
            "criteria_provenance": "predeclared in README before convergence runs",
            "comparison_geometry": "absolute differences in fixed QR-column order",
            "hamiltonian_structure_role": "interpretive only",
        },
        "refinement_matrix": {
            name: public_run_summary(run) for name, run in runs.items()
        },
        "duration_convergence": duration_analysis,
        "numerical_policy_comparisons": comparisons,
        "one_vector_run": public_run_summary(one_vector),
        "one_vector_comparison": one_vector_comparison,
        "numerical_validity_checks": validity_checks,
        "numerical_policy_checks": numerical_policy_checks,
        "numerical_validity_accepted": validity_accepted,
        "numerical_policy_accepted": policy_accepted,
        "strongest_claim": strongest_claim,
        "claim_boundary": (
            "The values remain cumulative finite-time QR estimates for one reference "
            "trajectory in Candidate A. No basis-initialization independence, canonical "
            "cross-check, multiple-state robustness, maximal Lyapunov exponent, or "
            "broader chaos classification is established."
        ),
        "next_question": next_question,
    }
    return {
        "mode": "convergence",
        "summary": summary,
        "primary": baseline,
        "runs": runs,
        "one_vector": one_vector,
        "comparisons": comparisons,
        "duration_analysis": duration_analysis,
        "one_vector_comparison": one_vector_comparison,
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


def write_refinement_csv(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "case",
        "accepted",
        "duration_seconds",
        "rtol",
        "atol",
        "max_step_seconds",
        "qr_interval_seconds",
        *[f"lambda_{index}_per_s" for index in range(1, 5)],
        "spectrum_sum_per_s",
        "maximum_difference_from_baseline_per_s",
        "comparison_limit_per_s",
        "comparison_accepted",
        "reference_endpoint_distance",
        "solver_nfev",
        "maximum_energy_drift",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name, run in result["runs"].items():
            policy = run["solver_policy"]
            comparison = result["comparisons"].get(name)
            row: dict[str, Any] = {
                "case": name,
                "accepted": run["accepted"],
                "duration_seconds": run["duration_seconds"],
                "rtol": policy["rtol"],
                "atol": policy["atol"],
                "max_step_seconds": run["max_step_seconds"],
                "qr_interval_seconds": run["qr_interval_seconds"],
                "spectrum_sum_per_s": run["diagnostic_spectrum_sum_per_second"],
                "solver_nfev": run["solver_statistics"]["nfev"],
                "maximum_energy_drift": run[
                    "maximum_normalized_reference_energy_drift"
                ],
            }
            for index, value in enumerate(
                run["final_diagnostic_spectrum_per_second"], start=1
            ):
                row[f"lambda_{index}_per_s"] = value
            if comparison is not None:
                row.update(
                    {
                        "maximum_difference_from_baseline_per_s": comparison[
                            "maximum_absolute_component_difference_per_second"
                        ],
                        "comparison_limit_per_s": comparison[
                            "absolute_limit_per_second"
                        ],
                        "comparison_accepted": comparison["accepted"],
                        "reference_endpoint_distance": comparison[
                            "final_reference_candidate_a_distance"
                        ],
                    }
                )
            else:
                row.update(
                    {
                        "maximum_difference_from_baseline_per_s": 0.0,
                        "comparison_limit_per_s": "",
                        "comparison_accepted": True,
                        "reference_endpoint_distance": 0.0,
                    }
                )
            writer.writerow(row)


def write_refinement_timeseries_csv(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "case",
        "time_seconds",
        *[f"lambda_{index}_per_s" for index in range(1, 5)],
        "spectrum_sum_per_s",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name, run in result["runs"].items():
            for cycle in run["cycles"]:
                values = cycle["cumulative_finite_time_spectrum_per_second"]
                row: dict[str, Any] = {
                    "case": name,
                    "time_seconds": cycle["end_time_seconds"],
                    "spectrum_sum_per_s": sum(values),
                }
                for index, value in enumerate(values, start=1):
                    row[f"lambda_{index}_per_s"] = value
                writer.writerow(row)


def write_one_vector_json(path: Path, one_vector: dict[str, Any]) -> None:
    json_write(
        path,
        {
            "experiment": EXPERIMENT_NAME,
            "role": "independent first-column accumulated-growth check",
            **one_vector,
        },
    )


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


def write_convergence_plots(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    plt = load_pyplot()
    paths: list[Path] = []
    run_names = list(result["runs"])
    spectra = np.asarray(
        [
            result["runs"][name]["final_diagnostic_spectrum_per_second"]
            for name in run_names
        ],
        dtype=float,
    )

    path = output_dir / "03_numerical_refinement_spectra.png"
    fig, axis = plt.subplots(figsize=(9, 5))
    x_positions = np.arange(4)
    for name, values in zip(run_names, spectra):
        axis.plot(x_positions, values, marker="o", label=name.replace("_", " "))
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set_xticks(x_positions, ["column 1", "column 2", "column 3", "column 4"])
    axis.set(
        ylabel="80 s cumulative value / s$^{-1}$",
        title="Whole-spectrum numerical refinements",
    )
    axis.grid(True, alpha=0.25)
    axis.legend(fontsize=8)
    save_figure(fig, path)
    paths.append(path)

    baseline = result["primary"]
    time_values = np.asarray(
        [cycle["end_time_seconds"] for cycle in baseline["cycles"]], dtype=float
    )
    sorted_spectra = np.sort(baseline["_finite_time_spectrum"], axis=1)[:, ::-1]
    structure = {
        "sum": np.sum(sorted_spectra, axis=1),
        "outer pair": sorted_spectra[:, 0] + sorted_spectra[:, 3],
        "inner pair": sorted_spectra[:, 1] + sorted_spectra[:, 2],
    }
    path = output_dir / "04_hamiltonian_structure_diagnostics.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for label, values in structure.items():
        axis.plot(time_values, values, label=label)
    axis.axhline(0.0, color="black", linewidth=0.8)
    axis.set(
        xlabel="time / s",
        ylabel="diagnostic / s$^{-1}$",
        title="Hamiltonian-structure diagnostics (interpretive only)",
    )
    axis.grid(True, alpha=0.25)
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
    if result["mode"] == "convergence":
        refinement_path = output_dir / "refinement_matrix.csv"
        refinement_timeseries_path = output_dir / "refinement_timeseries.csv"
        one_vector_path = output_dir / "one_vector_cycles.json"
        write_refinement_csv(refinement_path, result)
        write_refinement_timeseries_csv(refinement_timeseries_path, result)
        write_one_vector_json(one_vector_path, result["one_vector"])
        paths.extend(
            [refinement_path, refinement_timeseries_path, one_vector_path]
        )
        if plots:
            paths.extend(write_convergence_plots(output_dir, result))

    manifest_path = output_dir / "manifest.json"
    manifest = {
        "experiment": EXPERIMENT_NAME,
        "output_role": (
            "Experiment 007 convergence evidence for cumulative QR estimates"
            if result["mode"] == "convergence"
            else "exploratory Experiment 007 QR-primitive evidence"
        ),
        "claim_boundary": (
            "not production data; scientific interpretation is bounded by summary.json"
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


def assert_common_bookkeeping(run: dict[str, Any]) -> None:
    expected_cycles = int(
        round(run["duration_seconds"] / run["qr_interval_seconds"])
    )
    assert run["cycle_count"] == expected_cycles
    assert len(run["cycles"]) == expected_cycles
    recomputed_logs = np.cumsum(run["_cycle_logs"], axis=0)
    np.testing.assert_allclose(
        recomputed_logs,
        run["_cumulative_logs"],
        rtol=0.0,
        atol=BOOKKEEPING_ERROR_LIMIT,
    )
    end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in run["cycles"]]
    )
    np.testing.assert_allclose(
        recomputed_logs / end_times[:, None],
        run["_finite_time_spectrum"],
        rtol=0.0,
        atol=BOOKKEEPING_ERROR_LIMIT,
    )


def assert_self_check(result: dict[str, Any]) -> None:
    summary = result["summary"]
    primary = result["primary"]
    np.testing.assert_allclose(
        scaling_matrix() @ initial_physical_tangent_basis(),
        np.eye(4),
        rtol=0.0,
        atol=1.0e-15,
    )
    assert_common_bookkeeping(primary)
    if result["mode"] == "primitive":
        assert summary["accepted"] == all(summary["acceptance_checks"].values())
        assert primary["cycle_count"] == QR_CYCLE_COUNT
        if summary["accepted"]:
            assert primary["accepted"]
            assert result["reproducibility"]["accepted"]
        return

    assert set(result["runs"]) == {
        "baseline",
        "strict_tolerance",
        "half_max_step",
        "short_qr_interval",
        "long_qr_interval",
    }
    for run in result["runs"].values():
        assert_common_bookkeeping(run)
        assert np.all(np.isfinite(run["_finite_time_spectrum"]))
    duration = duration_convergence_analysis(primary)
    assert duration["accepted"] == result["duration_analysis"]["accepted"]
    assert summary["numerical_validity_accepted"] == all(
        summary["numerical_validity_checks"].values()
    )
    assert summary["numerical_policy_accepted"] == all(
        summary["numerical_policy_checks"].values()
    )
    assert summary["accepted"] == (
        summary["classification"]
        == "converged_sufficiently_for_controlled_reference_case"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("primitive", "convergence"),
        default="convergence",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
    )
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = (
        run_primitive_investigation()
        if args.mode == "primitive"
        else run_convergence_investigation()
    )
    output_dir = args.output_dir or (
        REPOSITORY_ROOT
        / "development/chaos_content/outputs/full_matrix_qr_tangent_dynamics"
        / ("baseline" if args.mode == "primitive" else "convergence")
    )
    if args.self_check:
        assert_self_check(result)
    paths = write_output_bundle(result, output_dir, plots=not args.no_plots)
    summary = result["summary"]
    primary_summary = summary.get(
        "primary_run", summary.get("refinement_matrix", {}).get("baseline", {})
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "accepted": summary["accepted"],
                "diagnostic_spectrum_per_second": primary_summary[
                    "final_diagnostic_spectrum_per_second"
                ],
                "strongest_claim": summary["strongest_claim"],
                "classification": summary.get("classification", "primitive_only"),
                "output_dir": str(output_dir),
                "files_written": len(paths),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
