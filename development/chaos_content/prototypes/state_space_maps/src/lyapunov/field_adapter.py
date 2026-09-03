"""Bind the finite-time Lyapunov observable to neutral scalar-field execution."""

from __future__ import annotations

import platform
import subprocess
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Sequence

import h5py
import numba
import numpy as np
import scipy

from ..generation import (
    CellState,
    EvaluatorBinding,
    FieldDefinition,
    FieldRunSummary,
    ProcessExecutionSpec,
    ScalarCellTask,
    read_authoritative_field,
    run_scalar_field,
)
from ..state_space_fields import (
    EvaluationStatus,
    PeriodicAngularDomain,
    ScalarEvaluation,
)

from .compiled import run_renormalized_tangent_compiled
from .compiled_equivalence import (
    ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
    RATE_ABSOLUTE_TOLERANCE,
    compare_results,
)
from .compiled_dop853 import run_renormalized_tangent_compiled_dop853
from .hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_ERROR_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
    evaluate_renormalized_tangent_hybrid,
)
from .reference import RenormalizedTangentDiagnostics, RenormalizedTangentSpec


LYAPUNOV_ROUTE_VOCABULARY = (
    (0, "not_yet_computed"),
    (1, HYBRID_FAST_EVALUATOR),
    (2, HYBRID_FALLBACK_EVALUATOR),
    (3, HYBRID_FAST_ERROR_EVALUATOR),
)


@dataclass(frozen=True)
class LyapunovOracleValidation:
    accepted: bool
    selected_indices: tuple[tuple[int, int], ...]
    maximum_rate_error_per_second: float
    maximum_energy_diagnostic_error: float
    comparisons: tuple[dict[str, object], ...]


_WORKER_SPEC: RenormalizedTangentSpec | None = None


def specification_for_cell(
    task: ScalarCellTask,
    base_spec: RenormalizedTangentSpec,
) -> RenormalizedTangentSpec:
    """Substitute exact periodic coordinates without changing fixed policy."""

    return replace(
        base_spec,
        initial_state=replace(
            base_spec.initial_state,
            theta1=task.theta1_coordinate,
            theta2=task.theta2_coordinate,
            omega1=0.0,
            omega2=0.0,
        ),
    )


def initialize_lyapunov_field_worker(base_spec: RenormalizedTangentSpec) -> None:
    global _WORKER_SPEC
    _WORKER_SPEC = base_spec
    warm = evaluate_renormalized_tangent_hybrid(base_spec)
    if warm.status is not EvaluationStatus.COMPLETED_VALID:
        raise RuntimeError("Lyapunov worker warm-up was not numerically valid.")


def evaluate_lyapunov_field_cell(
    task: ScalarCellTask,
) -> ScalarEvaluation[RenormalizedTangentDiagnostics]:
    if _WORKER_SPEC is None:
        raise RuntimeError("Lyapunov field worker was not initialized.")
    return evaluate_renormalized_tangent_hybrid(
        specification_for_cell(task, _WORKER_SPEC)
    )


def summarize_lyapunov_tile(
    evaluations: Sequence[ScalarEvaluation[object]],
) -> dict[str, object]:
    diagnostics = [
        evaluation.diagnostics
        for evaluation in evaluations
        if isinstance(evaluation.diagnostics, RenormalizedTangentDiagnostics)
    ]
    return {
        "maximum_energy_drift": max(
            (
                item.maximum_normalized_reference_energy_drift
                for item in diagnostics
            ),
            default=0.0,
        ),
        "maximum_reset_norm_error": max(
            (item.maximum_post_renormalization_norm_error for item in diagnostics),
            default=0.0,
        ),
        "solver_function_evaluations": sum(
            item.solver_function_evaluations for item in diagnostics
        ),
    }


def lyapunov_evaluator_binding(
    spec: RenormalizedTangentSpec | None = None,
) -> EvaluatorBinding:
    fixed_spec = spec or RenormalizedTangentSpec()
    return EvaluatorBinding(
        name="targeted_hybrid_lyapunov",
        initialize_worker=initialize_lyapunov_field_worker,
        initializer_arguments=(fixed_spec,),
        evaluate_cell=evaluate_lyapunov_field_cell,
        execution_routes=tuple(label for code, label in LYAPUNOV_ROUTE_VOCABULARY if code),
        summarize_tile=summarize_lyapunov_tile,
    )


def _git_head() -> str:
    repository_root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def periodic_lyapunov_field_definition(
    samples_per_axis: int,
    spec: RenormalizedTangentSpec | None = None,
) -> FieldDefinition:
    fixed_spec = spec or RenormalizedTangentSpec()
    domain = PeriodicAngularDomain.square(samples_per_axis)
    return FieldDefinition(
        theta1_axis=tuple(float(value) for value in domain.theta1_axis_radians),
        theta2_axis=tuple(float(value) for value in domain.theta2_axis_radians),
        coordinate_unit="radians",
        periodic=True,
        periodic_interval="[-pi, pi)",
        nominal_tile_shape=(8, 8),
        observable_provenance={
            "name": "one_vector_finite_time_tangent_stretching_rate",
            "symbol": "Lambda_T^(1)",
            "definition": "sum(log(r_k)) / T",
            "authoritative_meaning": (
                "fixed-horizon finite-time tangent stretching observable; "
                "no asymptotic exponent is implied"
            ),
            "field_consumer": "full-periodic initial-angle field",
        },
        physical_parameters=asdict(fixed_spec.parameters),
        numerical_parameters={
            "duration_seconds": fixed_spec.duration,
            "renormalization_interval_seconds": fixed_spec.renormalization_interval,
            "sampling_interval_seconds": fixed_spec.sampling_interval,
            "initial_tangent": list(fixed_spec.initial_tangent),
            "initial_angular_velocities_radians_per_second": [0.0, 0.0],
            "candidate_a_characteristic_length": fixed_spec.characteristic_length,
            "energy_drift_limit": fixed_spec.energy_drift_limit,
            "renormalization_norm_tolerance": (
                fixed_spec.renormalization_norm_tolerance
            ),
            "solver": asdict(fixed_spec.solver),
        },
        evaluator_provenance={
            "policy": "targeted_hybrid",
            "normal_route": HYBRID_FAST_EVALUATOR,
            "fallback_route": HYBRID_FALLBACK_EVALUATOR,
            "bounded_error_route": HYBRID_FAST_ERROR_EVALUATOR,
            "scientific_oracles": [
                "numpy_sympy_solve_ivp",
                "numba_rhs_jvp_solve_ivp",
            ],
        },
        software_provenance={
            "prototype": "state_space_maps",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "numba": numba.__version__,
            "h5py": h5py.__version__,
            "hdf5": h5py.version.hdf5_version,
            "platform": platform.platform(),
            "git_head": _git_head(),
        },
        route_vocabulary=LYAPUNOV_ROUTE_VOCABULARY,
    )


def run_periodic_lyapunov_field(
    output_path: Path,
    samples_per_axis: int,
    *,
    mode: str,
    spec: RenormalizedTangentSpec | None = None,
    execution: ProcessExecutionSpec | None = None,
) -> FieldRunSummary:
    fixed_spec = spec or RenormalizedTangentSpec()
    return run_scalar_field(
        output_path,
        periodic_lyapunov_field_definition(samples_per_axis, fixed_spec),
        lyapunov_evaluator_binding(fixed_spec),
        execution=execution,
        mode=mode,
    )


def _oracle_axis_indices(samples: int) -> tuple[int, ...]:
    return tuple(dict.fromkeys((0, samples // 2, samples - 1)))


def validate_lyapunov_oracle_spots(
    dataset_path: Path,
    spec: RenormalizedTangentSpec | None = None,
) -> LyapunovOracleValidation:
    """Recompute mechanically selected cells through established oracle gates."""

    fixed_spec = spec or RenormalizedTangentSpec()
    snapshot = read_authoritative_field(dataset_path)
    if snapshot.values.shape[0] != snapshot.values.shape[1]:
        raise ValueError("The first Lyapunov oracle selector requires a square field.")
    axis_indices = _oracle_axis_indices(snapshot.values.shape[0])
    selected = tuple(
        (theta2_index, theta1_index)
        for theta2_index in axis_indices
        for theta1_index in axis_indices
    )
    route_labels = {
        int(code): label
        for code, label in snapshot.metadata["execution_route_vocabulary"].items()
    }
    status_labels = {
        int(CellState.COMPLETED_VALID): EvaluationStatus.COMPLETED_VALID,
        int(CellState.COMPLETED_INVALID): EvaluationStatus.COMPLETED_INVALID,
        int(CellState.EXECUTION_ERROR): EvaluationStatus.EXECUTION_ERROR,
    }
    comparisons: list[dict[str, object]] = []
    for theta2_index, theta1_index in selected:
        task = ScalarCellTask(
            linear_index=theta2_index * snapshot.values.shape[1] + theta1_index,
            theta2_index=theta2_index,
            theta1_index=theta1_index,
            theta2_coordinate=float(snapshot.theta2_axis[theta2_index]),
            theta1_coordinate=float(snapshot.theta1_axis[theta1_index]),
        )
        cell_spec = specification_for_cell(task, fixed_spec)
        oracle = run_renormalized_tangent_compiled(cell_spec)
        hybrid = evaluate_renormalized_tangent_hybrid(cell_spec)
        stored_value = float(snapshot.values[theta2_index, theta1_index])
        stored_status = status_labels[int(snapshot.status[theta2_index, theta1_index])]
        stored_route = route_labels[
            int(snapshot.execution_route[theta2_index, theta1_index])
        ]
        rate_error = abs(stored_value - oracle.finite_time_stretching_rate)
        energy_error = (
            abs(
                hybrid.diagnostics.maximum_normalized_reference_energy_drift
                - oracle.diagnostics.maximum_normalized_reference_energy_drift
            )
            if hybrid.diagnostics is not None
            else float("inf")
        )
        expected_status = (
            EvaluationStatus.COMPLETED_VALID
            if oracle.diagnostics.numerically_valid
            else EvaluationStatus.COMPLETED_INVALID
        )
        fast_comparison = None
        if stored_route == HYBRID_FAST_EVALUATOR:
            fast_comparison = compare_results(
                oracle,
                run_renormalized_tangent_compiled_dop853(cell_spec),
            )
        accepted = bool(
            rate_error <= RATE_ABSOLUTE_TOLERANCE
            and energy_error <= ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
            and stored_status is expected_status
            and hybrid.status is stored_status
            and hybrid.value == stored_value
            and hybrid.evaluator == stored_route
            and hybrid.validity_issues == oracle.diagnostics.validity_issues
            and (fast_comparison is None or fast_comparison["accepted"])
        )
        comparisons.append(
            {
                "theta2_index": theta2_index,
                "theta1_index": theta1_index,
                "theta2_radians": task.theta2_coordinate,
                "theta1_radians": task.theta1_coordinate,
                "execution_route": stored_route,
                "status": stored_status.value,
                "absolute_rate_error_per_second": rate_error,
                "energy_diagnostic_absolute_error": energy_error,
                "fast_full_comparison": fast_comparison,
                "accepted": accepted,
            }
        )
    return LyapunovOracleValidation(
        accepted=all(item["accepted"] for item in comparisons),
        selected_indices=selected,
        maximum_rate_error_per_second=max(
            item["absolute_rate_error_per_second"] for item in comparisons
        ),
        maximum_energy_diagnostic_error=max(
            item["energy_diagnostic_absolute_error"] for item in comparisons
        ),
        comparisons=tuple(comparisons),
    )
