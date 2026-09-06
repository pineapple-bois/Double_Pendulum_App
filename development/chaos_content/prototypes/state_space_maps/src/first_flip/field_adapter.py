"""Bind first completed link revolution to neutral scalar-field execution."""

from __future__ import annotations

import json
import math
import platform
import subprocess
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Sequence

import h5py
import numpy as np
import scipy

from ..generation import (
    CellState,
    EvaluatorBinding,
    FieldDefinition,
    FieldRunSummary,
    ProcessExecutionSpec,
    ProgressCallback,
    ScalarCellTask,
    read_authoritative_field,
    run_scalar_field,
)
from ..lyapunov.reference import EulerLagrangeState, PendulumParameters, SolverSpec
from ..state_space_fields import EvaluationStatus, PeriodicAngularDomain, ScalarEvaluation
from .reference import (
    EventAttribution,
    FirstFlipResult,
    FirstFlipStatus,
    default_solver_spec,
    first_flip_time,
    gravity_timescale,
    initialize_reference_dynamics,
)
from .compiled import (
    FIRST_FLIP_COMPILED_EVALUATOR,
    FirstFlipCompiledUnavailableError,
    first_flip_compiled_eligibility,
    first_flip_compiled_provenance,
    first_flip_compiled_support,
    first_flip_time_compiled,
    initialize_compiled_rhs,
)
from .native_artifacts import (
    FIRST_FLIP_NATIVE_EVALUATOR,
    FirstFlipNativeArtifact,
    FirstFlipNativeUnavailableError,
    first_flip_native_support,
    prepare_first_flip_native_artifact_for_workers,
)
from .native_runtime import (
    FirstFlipNativeNumericalError,
    configure_first_flip_native_artifact,
    first_flip_native_provenance,
    first_flip_time_native,
    initialize_native_first_flip,
)


FIRST_FLIP_REFERENCE_EVALUATOR = "solve_ivp_first_flip_reference"
FIRST_FLIP_ROUTE_VOCABULARY = (
    (0, "not_yet_computed"),
    (1, FIRST_FLIP_REFERENCE_EVALUATOR),
    (2, FIRST_FLIP_COMPILED_EVALUATOR),
    (3, FIRST_FLIP_NATIVE_EVALUATOR),
)

# These are Experiment 020's evidence-derived numerical gates.  They are not
# tie or grazing tolerances.  Those unsupported cases fail closed below.
EVENT_SURFACE_RESIDUAL_LIMIT = 1.0e-10
ENERGY_DRIFT_LIMIT = 5.0e-9
MAXIMUM_ACCEPTED_ANGULAR_INCREMENT = 0.5
EVENT_TIME_CONVERGENCE_SECONDS = 5.0e-8


@dataclass(frozen=True)
class FirstFlipFieldSpec:
    """Fixed equal-link policy for one capped first-flip-time field."""

    parameters: PendulumParameters = field(default_factory=PendulumParameters)
    observation_horizon_seconds: float = 5.0
    solver: SolverSpec | None = None
    energy_drift_limit: float = ENERGY_DRIFT_LIMIT
    event_surface_residual_limit: float = EVENT_SURFACE_RESIDUAL_LIMIT
    maximum_accepted_angular_increment: float = MAXIMUM_ACCEPTED_ANGULAR_INCREMENT

    def __post_init__(self) -> None:
        gravity_timescale(self.parameters)
        values = (
            self.observation_horizon_seconds,
            self.energy_drift_limit,
            self.event_surface_residual_limit,
            self.maximum_accepted_angular_increment,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("First-flip field limits and horizon must be positive and finite.")
        if self.solver is None:
            object.__setattr__(self, "solver", default_solver_spec(self.parameters))

    @property
    def gravity_timescale_seconds(self) -> float:
        return gravity_timescale(self.parameters)

    @property
    def dimensionless_observation_horizon(self) -> float:
        return self.observation_horizon_seconds / self.gravity_timescale_seconds


@dataclass(frozen=True)
class FirstFlipFieldDiagnostics:
    """Compact per-cell diagnostics retained until tile compaction."""

    outcome: str
    raw_status: str
    event_identity: str | None
    event_time_seconds: float | None
    dimensionless_event_time: float | None
    integration_endpoint_seconds: float
    rhs_evaluations: int
    accepted_point_count: int
    maximum_normalized_energy_drift: float
    maximum_accepted_angular_increment: float
    triggering_surface_residual: float | None
    triggering_angular_speed: float | None
    minimum_competing_surface_margin: float | None


@dataclass(frozen=True)
class CappedFirstFlipFieldSummary:
    """Evidence summary derived from a closed authoritative HDF5 field."""

    cell_count: int
    observed_count: int
    censored_count: int
    completed_invalid_count: int
    execution_error_count: int
    dimensionless_horizon: float
    observed_time_seconds_minimum: float | None
    observed_time_seconds_median: float | None
    observed_time_seconds_maximum: float | None
    observed_time_dimensionless_minimum: float | None
    observed_time_dimensionless_median: float | None
    observed_time_dimensionless_maximum: float | None
    tile_evaluation_seconds_minimum: float
    tile_evaluation_seconds_median: float
    tile_evaluation_seconds_maximum: float
    tile_maximum_to_median_ratio: float
    summed_rhs_evaluations: int
    rhs_evaluations_minimum: int
    rhs_evaluations_tile_median_median: float
    rhs_evaluations_maximum: int
    cell_wall_seconds_minimum: float
    cell_wall_seconds_tile_median_median: float
    cell_wall_seconds_maximum: float
    maximum_triggering_surface_residual: float
    maximum_normalized_energy_drift: float
    maximum_accepted_angular_increment: float
    minimum_event_crossing_speed: float | None
    minimum_competing_surface_margin: float | None

    @property
    def observed_fraction(self) -> float:
        return self.observed_count / self.cell_count

    @property
    def censored_fraction(self) -> float:
        return self.censored_count / self.cell_count


@dataclass(frozen=True)
class FirstFlipSpotValidation:
    """Mechanically selected persisted-cell comparison with a stricter solve."""

    accepted: bool
    selected_indices: tuple[tuple[int, int], ...]
    maximum_event_time_difference_seconds: float
    comparisons: tuple[dict[str, object], ...]


_WORKER_SPEC: FirstFlipFieldSpec | None = None
_WORKER_ROUTE = FIRST_FLIP_REFERENCE_EVALUATOR
_WORKER_COMPILED_FAILURE: FirstFlipCompiledUnavailableError | None = None
_WORKER_NATIVE_FAILURE: BaseException | None = None


def initial_state_for_cell(task: ScalarCellTask) -> EulerLagrangeState:
    """Use exact periodic coordinates and the field's fixed zero velocities."""

    return EulerLagrangeState(
        theta1=task.theta1_coordinate,
        theta2=task.theta2_coordinate,
        omega1=0.0,
        omega2=0.0,
    )


def initialize_first_flip_field_worker(
    spec: FirstFlipFieldSpec,
    force_trusted: bool = False,
    force_compiled: bool = False,
    native_artifact: FirstFlipNativeArtifact | None = None,
) -> None:
    global _WORKER_SPEC, _WORKER_ROUTE, _WORKER_COMPILED_FAILURE, _WORKER_NATIVE_FAILURE
    _WORKER_SPEC = spec
    assert spec.solver is not None
    eligible = first_flip_compiled_eligibility(
        spec.parameters,
        spec.solver,
        spec.observation_horizon_seconds,
        energy_drift_limit=spec.energy_drift_limit,
        event_residual_limit=spec.event_surface_residual_limit,
        angular_increment_limit=spec.maximum_accepted_angular_increment,
    ).eligible
    _WORKER_ROUTE = FIRST_FLIP_REFERENCE_EVALUATOR
    _WORKER_COMPILED_FAILURE = None
    _WORKER_NATIVE_FAILURE = None
    if force_trusted or not eligible:
        initialize_reference_dynamics(spec.parameters)
        return
    if not force_compiled and first_flip_native_support()["supported"]:
        try:
            configure_first_flip_native_artifact(native_artifact)
            initialize_native_first_flip(spec.parameters)
            _WORKER_ROUTE = FIRST_FLIP_NATIVE_EVALUATOR
            try:
                initialize_compiled_rhs(spec.parameters)
            except FirstFlipCompiledUnavailableError as error:
                _WORKER_COMPILED_FAILURE = error
            return
        except FirstFlipNativeUnavailableError as error:
            _WORKER_NATIVE_FAILURE = error
    if first_flip_compiled_support().supported:
        try:
            initialize_compiled_rhs(spec.parameters)
            _WORKER_ROUTE = FIRST_FLIP_COMPILED_EVALUATOR
            return
        except FirstFlipCompiledUnavailableError as error:
            _WORKER_COMPILED_FAILURE = error
    initialize_reference_dynamics(spec.parameters)


def _diagnostics(result: FirstFlipResult, outcome: str) -> FirstFlipFieldDiagnostics:
    triggering_residual = None
    if result.event_identities:
        triggering_residual = max(
            abs(item.residual)
            for item in result.event_surface_residuals
            if item.identity in result.event_identities
        )
    crossing_speed = (
        min(abs(value) for value in result.triggering_angular_velocities)
        if result.triggering_angular_velocities
        else None
    )
    identity = (
        result.event_identities[0].label
        if len(result.event_identities) == 1
        else None
    )
    return FirstFlipFieldDiagnostics(
        outcome=outcome,
        raw_status=result.status.value,
        event_identity=identity,
        event_time_seconds=result.event_time_seconds,
        dimensionless_event_time=result.dimensionless_event_time,
        integration_endpoint_seconds=result.integration_endpoint_seconds,
        rhs_evaluations=result.rhs_evaluations,
        accepted_point_count=result.accepted_point_count,
        maximum_normalized_energy_drift=result.maximum_normalized_energy_drift,
        maximum_accepted_angular_increment=result.maximum_accepted_angular_increment,
        triggering_surface_residual=triggering_residual,
        triggering_angular_speed=crossing_speed,
        minimum_competing_surface_margin=result.minimum_competing_surface_margin,
    )


def adapt_first_flip_result(
    result: FirstFlipResult,
    spec: FirstFlipFieldSpec,
    *,
    evaluator: str = FIRST_FLIP_REFERENCE_EVALUATOR,
    implementation_provenance: dict[str, object] | None = None,
) -> ScalarEvaluation[FirstFlipFieldDiagnostics]:
    """Convert a physical result into the authoritative capped scalar contract."""

    issues = list(result.validation_issues)
    if result.maximum_normalized_energy_drift > spec.energy_drift_limit:
        issues.append("energy_drift_limit_exceeded")
    if result.maximum_accepted_angular_increment >= spec.maximum_accepted_angular_increment:
        issues.append("accepted_angular_increment_limit_exceeded")

    if result.status is FirstFlipStatus.SOLVER_FAILURE:
        return ScalarEvaluation(
            status=EvaluationStatus.EXECUTION_ERROR,
            value=None,
            diagnostics=_diagnostics(result, "solver_failure"),
            elapsed_seconds=result.wall_seconds,
            evaluator=evaluator,
            implementation_provenance=implementation_provenance or {},
            error_type="FirstFlipSolverFailure",
            error_message=result.solver_message,
        )
    if result.status is FirstFlipStatus.INVALID_INTEGRATION:
        issues.extend(result.validation_issues or ("invalid_integration",))

    if result.status is FirstFlipStatus.EVENT_OBSERVED:
        if result.attribution is not EventAttribution.UNIQUE:
            issues.append("unsupported_nonunique_event_attribution")
        if result.event_time_seconds is None or result.dimensionless_event_time is None:
            issues.append("observed_event_missing_time")
        triggering_residual = _diagnostics(result, "event_observed").triggering_surface_residual
        if (
            triggering_residual is None
            or triggering_residual > spec.event_surface_residual_limit
        ):
            issues.append("event_surface_residual_limit_exceeded")
        if any(value == 0.0 for value in result.triggering_angular_velocities):
            issues.append("nontransversal_event")

    if issues:
        return ScalarEvaluation(
            status=EvaluationStatus.COMPLETED_INVALID,
            value=None,
            diagnostics=_diagnostics(result, "numerically_invalid"),
            elapsed_seconds=result.wall_seconds,
            evaluator=evaluator,
            implementation_provenance=implementation_provenance or {},
            validity_issues=tuple(dict.fromkeys(issues)),
        )

    cap = spec.dimensionless_observation_horizon
    if result.status is FirstFlipStatus.RIGHT_CENSORED:
        outcome = "right_censored"
        value = cap
    elif result.status is FirstFlipStatus.EVENT_OBSERVED:
        assert result.event_time_seconds is not None
        assert result.dimensionless_event_time is not None
        if result.event_time_seconds < spec.observation_horizon_seconds:
            outcome = "event_observed"
            value = result.dimensionless_event_time
        else:
            # Experiment 020's recommended strict capped-field convention.
            outcome = "right_censored_at_cap"
            value = cap
    else:
        return ScalarEvaluation(
            status=EvaluationStatus.COMPLETED_INVALID,
            value=None,
            diagnostics=_diagnostics(result, "unexpected_status"),
            elapsed_seconds=result.wall_seconds,
            evaluator=evaluator,
            implementation_provenance=implementation_provenance or {},
            validity_issues=("unexpected_first_flip_status",),
        )

    return ScalarEvaluation(
        status=EvaluationStatus.COMPLETED_VALID,
        value=float(value),
        diagnostics=_diagnostics(result, outcome),
        elapsed_seconds=result.wall_seconds,
        evaluator=evaluator,
        implementation_provenance=implementation_provenance or {},
    )


def evaluate_first_flip_field_cell(
    task: ScalarCellTask,
) -> ScalarEvaluation[FirstFlipFieldDiagnostics]:
    if _WORKER_SPEC is None:
        raise RuntimeError("First-flip field worker was not initialized.")
    assert _WORKER_SPEC.solver is not None
    initial_state = initial_state_for_cell(task)
    if _WORKER_ROUTE == FIRST_FLIP_NATIVE_EVALUATOR:
        try:
            native_result = first_flip_time_native(
                initial_state,
                parameters=_WORKER_SPEC.parameters,
                solver_spec=_WORKER_SPEC.solver,
                observation_horizon=_WORKER_SPEC.observation_horizon_seconds,
            )
        except FirstFlipNativeNumericalError as error:
            native_candidate = None
            native_failure: BaseException | None = error
        else:
            native_candidate = adapt_first_flip_result(
                native_result,
                _WORKER_SPEC,
                evaluator=FIRST_FLIP_NATIVE_EVALUATOR,
                implementation_provenance=first_flip_native_provenance(),
            )
            if native_candidate.status is EvaluationStatus.COMPLETED_VALID:
                return native_candidate
            native_failure = None
        if _WORKER_COMPILED_FAILURE is None:
            compiled_result = first_flip_time_compiled(
                initial_state, _WORKER_SPEC.parameters, _WORKER_SPEC.solver,
                _WORKER_SPEC.observation_horizon_seconds,
            )
            compiled_candidate = adapt_first_flip_result(
                compiled_result, _WORKER_SPEC,
                evaluator=FIRST_FLIP_COMPILED_EVALUATOR,
                implementation_provenance=first_flip_compiled_provenance(),
            )
            if compiled_candidate.status is EvaluationStatus.COMPLETED_VALID:
                return replace(
                    compiled_candidate,
                    attempted_evaluators=(FIRST_FLIP_NATIVE_EVALUATOR,),
                    recovery_reason="native_first_flip_numerical_rejection",
                    attempt_provenance={FIRST_FLIP_NATIVE_EVALUATOR: (
                        first_flip_native_provenance(native_failure)
                        if native_candidate is None else native_candidate.implementation_provenance
                    )},
                )
        trusted_result = first_flip_time(
            initial_state, _WORKER_SPEC.parameters, _WORKER_SPEC.solver,
            _WORKER_SPEC.observation_horizon_seconds,
        )
        trusted = adapt_first_flip_result(trusted_result, _WORKER_SPEC)
        attempts = (FIRST_FLIP_NATIVE_EVALUATOR, FIRST_FLIP_COMPILED_EVALUATOR)
        return replace(
            trusted,
            attempted_evaluators=attempts,
            recovery_reason="native_and_compiled_first_flip_recovery",
            attempt_provenance={
                FIRST_FLIP_NATIVE_EVALUATOR: (
                    first_flip_native_provenance(native_failure)
                    if native_candidate is None else native_candidate.implementation_provenance
                ),
                FIRST_FLIP_COMPILED_EVALUATOR: (
                    first_flip_compiled_provenance(_WORKER_COMPILED_FAILURE)
                    if _WORKER_COMPILED_FAILURE else compiled_candidate.implementation_provenance
                ),
            },
        )
    if _WORKER_ROUTE == FIRST_FLIP_COMPILED_EVALUATOR:
        candidate_result = first_flip_time_compiled(
            initial_state,
            parameters=_WORKER_SPEC.parameters,
            solver_spec=_WORKER_SPEC.solver,
            observation_horizon=_WORKER_SPEC.observation_horizon_seconds,
        )
        candidate = adapt_first_flip_result(
            candidate_result,
            _WORKER_SPEC,
            evaluator=FIRST_FLIP_COMPILED_EVALUATOR,
            implementation_provenance=first_flip_compiled_provenance(),
        )
        if candidate.status is EvaluationStatus.COMPLETED_VALID:
            if _WORKER_NATIVE_FAILURE is None:
                return candidate
            return replace(
                candidate,
                attempted_evaluators=(FIRST_FLIP_NATIVE_EVALUATOR,),
                recovery_reason="native_first_flip_initialization_unavailable",
                attempt_provenance={
                    FIRST_FLIP_NATIVE_EVALUATOR: first_flip_native_provenance(_WORKER_NATIVE_FAILURE)
                },
            )
        trusted_result = first_flip_time(
            initial_state,
            parameters=_WORKER_SPEC.parameters,
            solver_spec=_WORKER_SPEC.solver,
            observation_horizon=_WORKER_SPEC.observation_horizon_seconds,
        )
        trusted = adapt_first_flip_result(trusted_result, _WORKER_SPEC)
        return replace(
            trusted,
            attempted_evaluators=((FIRST_FLIP_NATIVE_EVALUATOR, FIRST_FLIP_COMPILED_EVALUATOR) if _WORKER_NATIVE_FAILURE else (FIRST_FLIP_COMPILED_EVALUATOR,)),
            recovery_reason=("native_initialization_unavailable_and_compiled_numerical_rejection" if _WORKER_NATIVE_FAILURE else "compiled_first_flip_numerical_rejection"),
            attempt_provenance={
                **({FIRST_FLIP_NATIVE_EVALUATOR: first_flip_native_provenance(_WORKER_NATIVE_FAILURE)} if _WORKER_NATIVE_FAILURE else {}),
                FIRST_FLIP_COMPILED_EVALUATOR: candidate.implementation_provenance,
            },
        )
    result = first_flip_time(
        initial_state,
        parameters=_WORKER_SPEC.parameters,
        solver_spec=_WORKER_SPEC.solver,
        observation_horizon=_WORKER_SPEC.observation_horizon_seconds,
    )
    trusted = adapt_first_flip_result(result, _WORKER_SPEC)
    if _WORKER_COMPILED_FAILURE is None and _WORKER_NATIVE_FAILURE is None:
        return trusted
    if _WORKER_NATIVE_FAILURE is not None:
        return replace(
            trusted,
            attempted_evaluators=(FIRST_FLIP_NATIVE_EVALUATOR, FIRST_FLIP_COMPILED_EVALUATOR),
            recovery_reason="native_and_compiled_first_flip_initialization_unavailable",
            attempt_provenance={
                FIRST_FLIP_NATIVE_EVALUATOR: first_flip_native_provenance(_WORKER_NATIVE_FAILURE),
                FIRST_FLIP_COMPILED_EVALUATOR: first_flip_compiled_provenance(_WORKER_COMPILED_FAILURE),
            },
        )
    return replace(
        trusted,
        attempted_evaluators=(FIRST_FLIP_COMPILED_EVALUATOR,),
        recovery_reason="compiled_first_flip_initialization_unavailable",
        attempt_provenance={
            FIRST_FLIP_COMPILED_EVALUATOR: first_flip_compiled_provenance(
                _WORKER_COMPILED_FAILURE
            )
        },
    )


def summarize_first_flip_tile(
    evaluations: Sequence[ScalarEvaluation[object]],
) -> dict[str, object]:
    diagnostics = [
        evaluation.diagnostics
        for evaluation in evaluations
        if isinstance(evaluation.diagnostics, FirstFlipFieldDiagnostics)
    ]
    observed = [item for item in diagnostics if item.outcome == "event_observed"]
    crossing_speeds = [
        item.triggering_angular_speed
        for item in observed
        if item.triggering_angular_speed is not None
    ]
    margins = [
        item.minimum_competing_surface_margin
        for item in observed
        if item.minimum_competing_surface_margin is not None
    ]
    triggering_residuals = [
        item.triggering_surface_residual
        for item in observed
        if item.triggering_surface_residual is not None
    ]
    rhs_evaluations = [item.rhs_evaluations for item in diagnostics]
    elapsed_seconds = [evaluation.elapsed_seconds for evaluation in evaluations]
    return {
        "first_flip_outcome_counts": {
            outcome: sum(item.outcome == outcome for item in diagnostics)
            for outcome in sorted({item.outcome for item in diagnostics})
        },
        "solver_function_evaluations": sum(item.rhs_evaluations for item in diagnostics),
        "solver_function_evaluations_minimum": min(rhs_evaluations, default=0),
        "solver_function_evaluations_median": (
            float(np.median(rhs_evaluations)) if rhs_evaluations else 0.0
        ),
        "solver_function_evaluations_maximum": max(rhs_evaluations, default=0),
        "cell_wall_seconds_minimum": min(elapsed_seconds, default=0.0),
        "cell_wall_seconds_median": (
            float(np.median(elapsed_seconds)) if elapsed_seconds else 0.0
        ),
        "cell_wall_seconds_maximum": max(elapsed_seconds, default=0.0),
        "maximum_normalized_energy_drift": max(
            (item.maximum_normalized_energy_drift for item in diagnostics), default=0.0
        ),
        "maximum_accepted_angular_increment": max(
            (item.maximum_accepted_angular_increment for item in diagnostics), default=0.0
        ),
        "minimum_event_crossing_speed": min(crossing_speeds, default=None),
        "minimum_competing_surface_margin": min(margins, default=None),
        "maximum_triggering_surface_residual": max(
            triggering_residuals, default=0.0
        ),
    }


def first_flip_evaluator_binding(
    spec: FirstFlipFieldSpec | None = None,
    *,
    force_trusted: bool = False,
    force_compiled: bool = False,
) -> EvaluatorBinding:
    fixed_spec = spec or FirstFlipFieldSpec()
    assert fixed_spec.solver is not None
    compiled_selected = (
        not force_trusted
        and first_flip_compiled_support().supported
        and first_flip_compiled_eligibility(
            fixed_spec.parameters,
            fixed_spec.solver,
            fixed_spec.observation_horizon_seconds,
            energy_drift_limit=fixed_spec.energy_drift_limit,
            event_residual_limit=fixed_spec.event_surface_residual_limit,
            angular_increment_limit=fixed_spec.maximum_accepted_angular_increment,
        ).eligible
    )
    native_selected = (
        compiled_selected and not force_compiled and first_flip_native_support()["supported"]
    )
    artifact = prepare_first_flip_native_artifact_for_workers() if native_selected else None
    return EvaluatorBinding(
        name=("native_first_flip_with_compiled_and_trusted_recovery" if native_selected else ("compiled_first_flip_with_trusted_recovery" if compiled_selected else "physical_first_flip_reference")),
        initialize_worker=initialize_first_flip_field_worker,
        initializer_arguments=(fixed_spec, not compiled_selected, force_compiled, artifact),
        evaluate_cell=evaluate_first_flip_field_cell,
        execution_routes=(
            (FIRST_FLIP_NATIVE_EVALUATOR, FIRST_FLIP_COMPILED_EVALUATOR, FIRST_FLIP_REFERENCE_EVALUATOR)
            if native_selected else (FIRST_FLIP_COMPILED_EVALUATOR, FIRST_FLIP_REFERENCE_EVALUATOR)
            if compiled_selected
            else (FIRST_FLIP_REFERENCE_EVALUATOR,)
        ),
        summarize_tile=summarize_first_flip_tile,
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


def periodic_first_flip_field_definition(
    samples_per_axis: int,
    spec: FirstFlipFieldSpec | None = None,
    *,
    force_trusted: bool = False,
    force_compiled: bool = False,
) -> FieldDefinition:
    fixed_spec = spec or FirstFlipFieldSpec()
    assert fixed_spec.solver is not None
    domain = PeriodicAngularDomain.square(samples_per_axis)
    compiled_selected = (
        not force_trusted
        and first_flip_compiled_support().supported
        and first_flip_compiled_eligibility(
            fixed_spec.parameters,
            fixed_spec.solver,
            fixed_spec.observation_horizon_seconds,
            energy_drift_limit=fixed_spec.energy_drift_limit,
            event_residual_limit=fixed_spec.event_surface_residual_limit,
            angular_increment_limit=fixed_spec.maximum_accepted_angular_increment,
        ).eligible
    )
    native_selected = compiled_selected and not force_compiled and first_flip_native_support()["supported"]
    evaluator_provenance = (
        {
            "policy": "native_first_flip_with_compiled_and_trusted_recovery",
            "route": FIRST_FLIP_NATIVE_EVALUATOR,
            "compiled_recovery_route": FIRST_FLIP_COMPILED_EVALUATOR,
            "trusted_route": FIRST_FLIP_REFERENCE_EVALUATOR,
            "native": first_flip_native_provenance(),
            "compiled": first_flip_compiled_provenance(),
            "reference_experiment": "development/chaos_content/experiments/physical_observables/020_first_flip_event_contract",
            "physical_flow": "compiled four-state Euler-Lagrange RHS",
            "event_surfaces": ["arm1-", "arm1+", "arm2-", "arm2+"],
            "terminal": True, "crossing_direction": 1,
            "angles": "continuous_lifted_absolute_link_orientations",
        }
        if native_selected else
        {
            "policy": "compiled_first_flip_with_trusted_recovery",
            "route": FIRST_FLIP_COMPILED_EVALUATOR,
            "trusted_route": FIRST_FLIP_REFERENCE_EVALUATOR,
            "compiled": first_flip_compiled_provenance(),
            "reference_experiment": "development/chaos_content/experiments/physical_observables/020_first_flip_event_contract",
            "physical_flow": "compiled four-state Euler-Lagrange RHS",
            "event_surfaces": ["arm1-", "arm1+", "arm2-", "arm2+"],
            "terminal": True,
            "crossing_direction": 1,
            "angles": "continuous_lifted_absolute_link_orientations",
        }
        if compiled_selected
        else {
            "policy": "experiment_020_reference_promotion",
            "route": FIRST_FLIP_REFERENCE_EVALUATOR,
            "reference_experiment": "development/chaos_content/experiments/physical_observables/020_first_flip_event_contract",
            "physical_flow": "EulerLagrangeDynamics.flow",
            "event_surfaces": ["arm1-", "arm1+", "arm2-", "arm2+"],
            "terminal": True,
            "crossing_direction": 1,
            "angles": "continuous_lifted_absolute_link_orientations",
        }
    )
    return FieldDefinition(
        theta1_axis=tuple(float(value) for value in domain.theta1_axis_radians),
        theta2_axis=tuple(float(value) for value in domain.theta2_axis_radians),
        coordinate_unit="radians",
        periodic=True,
        periodic_interval="[-pi, pi)",
        nominal_tile_shape=(8, 8),
        observable_provenance={
            "name": "capped_dimensionless_first_flip_time",
            "symbol": "min(tau_hat_flip, T_hat_max)",
            "physical_observable": "first completed link revolution",
            "definition": "first |theta_i(t)-theta_i(0)| = 2*pi for either absolute link angle",
            "accepted_scope": "transversal, numerically separated events; equal-link simple model",
            "censoring_contract": (
                "a completed-valid value exactly equal to the dimensionless horizon is "
                "right-censored; a smaller value is an observed event"
            ),
            "threshold_contract": (
                "for 0 < H <= T_hat_max, event-before-H is values < H on completed-valid cells"
            ),
        },
        physical_parameters=asdict(fixed_spec.parameters),
        numerical_parameters={
            "observation_horizon_seconds": fixed_spec.observation_horizon_seconds,
            "gravity_timescale_seconds": fixed_spec.gravity_timescale_seconds,
            "dimensionless_observation_horizon": fixed_spec.dimensionless_observation_horizon,
            "initial_angular_velocities_radians_per_second": [0.0, 0.0],
            "energy_drift_limit": fixed_spec.energy_drift_limit,
            "event_surface_residual_limit": fixed_spec.event_surface_residual_limit,
            "maximum_accepted_angular_increment": fixed_spec.maximum_accepted_angular_increment,
            "solver": asdict(fixed_spec.solver),
        },
        evaluator_provenance=evaluator_provenance,
        software_provenance={
            "prototype": "state_space_maps",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "h5py": h5py.__version__,
            "hdf5": h5py.version.hdf5_version,
            "platform": platform.platform(),
            "git_head": _git_head(),
        },
        route_vocabulary=(
            FIRST_FLIP_ROUTE_VOCABULARY
            if native_selected else FIRST_FLIP_ROUTE_VOCABULARY[:3]
            if compiled_selected
            else FIRST_FLIP_ROUTE_VOCABULARY[:2]
        ),
    )


def run_periodic_first_flip_field(
    output_path: Path,
    samples_per_axis: int,
    *,
    mode: str,
    spec: FirstFlipFieldSpec | None = None,
    execution: ProcessExecutionSpec | None = None,
    progress_callback: ProgressCallback | None = None,
    force_trusted: bool = False,
    force_compiled: bool = False,
) -> FieldRunSummary:
    fixed_spec = spec or FirstFlipFieldSpec()
    return run_scalar_field(
        output_path,
        periodic_first_flip_field_definition(
            samples_per_axis, fixed_spec, force_trusted=force_trusted, force_compiled=force_compiled
        ),
        first_flip_evaluator_binding(fixed_spec, force_trusted=force_trusted, force_compiled=force_compiled),
        execution=execution,
        mode=mode,
        progress_callback=progress_callback,
    )


def _decode_json(value: object) -> dict[str, object]:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(str(value))


def summarize_persisted_first_flip_field(
    dataset_path: Path,
) -> CappedFirstFlipFieldSummary:
    """Derive pilot statistics without re-integrating any trajectory."""

    snapshot = read_authoritative_field(dataset_path)
    numerical = snapshot.metadata["numerical_parameters"]
    assert isinstance(numerical, dict)
    cap = float(numerical["dimensionless_observation_horizon"])
    time_scale = float(numerical["gravity_timescale_seconds"])
    valid = snapshot.status == CellState.COMPLETED_VALID
    observed = valid & (snapshot.values < cap)
    censored = valid & (snapshot.values == cap)
    if np.any(valid & ~observed & ~censored):
        raise ValueError("A completed-valid first-flip value violates the capped contract.")
    observed_values = snapshot.values[observed]
    tile_seconds: list[float] = []
    total_rhs = 0
    rhs_minima: list[int] = []
    rhs_medians: list[float] = []
    rhs_maxima: list[int] = []
    cell_wall_minima: list[float] = []
    cell_wall_medians: list[float] = []
    cell_wall_maxima: list[float] = []
    maximum_residuals: list[float] = []
    maximum_energy_drifts: list[float] = []
    maximum_angular_increments: list[float] = []
    crossing_speeds: list[float] = []
    competing_margins: list[float] = []
    with h5py.File(dataset_path, "r") as source:
        tile_seconds = [float(value) for value in source["tiles/evaluation_seconds"][:]]
        for encoded in source["tiles/diagnostics_json"][:]:
            item = _decode_json(encoded)
            total_rhs += int(item.get("solver_function_evaluations", 0))
            rhs_minima.append(int(item["solver_function_evaluations_minimum"]))
            rhs_medians.append(float(item["solver_function_evaluations_median"]))
            rhs_maxima.append(int(item["solver_function_evaluations_maximum"]))
            cell_wall_minima.append(float(item["cell_wall_seconds_minimum"]))
            cell_wall_medians.append(float(item["cell_wall_seconds_median"]))
            cell_wall_maxima.append(float(item["cell_wall_seconds_maximum"]))
            maximum_residuals.append(
                float(item["maximum_triggering_surface_residual"])
            )
            maximum_energy_drifts.append(
                float(item["maximum_normalized_energy_drift"])
            )
            maximum_angular_increments.append(
                float(item["maximum_accepted_angular_increment"])
            )
            speed = item.get("minimum_event_crossing_speed")
            margin = item.get("minimum_competing_surface_margin")
            if speed is not None:
                crossing_speeds.append(float(speed))
            if margin is not None:
                competing_margins.append(float(margin))

    def statistic(values: np.ndarray, operation: str) -> float | None:
        if not len(values):
            return None
        return float(getattr(np, operation)(values))

    seconds = observed_values * time_scale
    median_tile = float(np.median(tile_seconds))
    return CappedFirstFlipFieldSummary(
        cell_count=int(snapshot.values.size),
        observed_count=int(np.count_nonzero(observed)),
        censored_count=int(np.count_nonzero(censored)),
        completed_invalid_count=int(
            np.count_nonzero(snapshot.status == CellState.COMPLETED_INVALID)
        ),
        execution_error_count=int(
            np.count_nonzero(snapshot.status == CellState.EXECUTION_ERROR)
        ),
        dimensionless_horizon=cap,
        observed_time_seconds_minimum=statistic(seconds, "min"),
        observed_time_seconds_median=statistic(seconds, "median"),
        observed_time_seconds_maximum=statistic(seconds, "max"),
        observed_time_dimensionless_minimum=statistic(observed_values, "min"),
        observed_time_dimensionless_median=statistic(observed_values, "median"),
        observed_time_dimensionless_maximum=statistic(observed_values, "max"),
        tile_evaluation_seconds_minimum=float(np.min(tile_seconds)),
        tile_evaluation_seconds_median=median_tile,
        tile_evaluation_seconds_maximum=float(np.max(tile_seconds)),
        tile_maximum_to_median_ratio=(
            float(np.max(tile_seconds)) / median_tile if median_tile else math.inf
        ),
        summed_rhs_evaluations=total_rhs,
        rhs_evaluations_minimum=min(rhs_minima),
        rhs_evaluations_tile_median_median=float(np.median(rhs_medians)),
        rhs_evaluations_maximum=max(rhs_maxima),
        cell_wall_seconds_minimum=min(cell_wall_minima),
        cell_wall_seconds_tile_median_median=float(np.median(cell_wall_medians)),
        cell_wall_seconds_maximum=max(cell_wall_maxima),
        maximum_triggering_surface_residual=max(maximum_residuals),
        maximum_normalized_energy_drift=max(maximum_energy_drifts),
        maximum_accepted_angular_increment=max(maximum_angular_increments),
        minimum_event_crossing_speed=min(crossing_speeds, default=None),
        minimum_competing_surface_margin=min(competing_margins, default=None),
    )


def validate_first_flip_reference_spots(
    dataset_path: Path,
    spec: FirstFlipFieldSpec | None = None,
) -> FirstFlipSpotValidation:
    """Compare nine mechanically selected cells with a stricter DOP853 run."""

    fixed_spec = spec or FirstFlipFieldSpec()
    assert fixed_spec.solver is not None
    snapshot = read_authoritative_field(dataset_path)
    if snapshot.values.shape[0] != snapshot.values.shape[1]:
        raise ValueError("The first-flip spot selector requires a square field.")
    stored_horizon = float(
        snapshot.metadata["numerical_parameters"]["observation_horizon_seconds"]
    )
    if stored_horizon != fixed_spec.observation_horizon_seconds:
        raise ValueError("Spot-validation specification does not match the field horizon.")
    samples = snapshot.values.shape[0]
    axis_indices = tuple(dict.fromkeys((0, samples // 2, samples - 1)))
    selected = tuple(
        (theta2_index, theta1_index)
        for theta2_index in axis_indices
        for theta1_index in axis_indices
    )
    strict_solver = SolverSpec(
        method=fixed_spec.solver.method,
        rtol=1.0e-11,
        atol=1.0e-13,
        max_step=fixed_spec.solver.max_step,
    )
    cap = fixed_spec.dimensionless_observation_horizon
    comparisons: list[dict[str, object]] = []
    for theta2_index, theta1_index in selected:
        theta1 = float(snapshot.theta1_axis[theta1_index])
        theta2 = float(snapshot.theta2_axis[theta2_index])
        strict = first_flip_time(
            EulerLagrangeState(theta1, theta2, 0.0, 0.0),
            parameters=fixed_spec.parameters,
            solver_spec=strict_solver,
            observation_horizon=fixed_spec.observation_horizon_seconds,
        )
        stored_status = int(snapshot.status[theta2_index, theta1_index])
        stored_value = float(snapshot.values[theta2_index, theta1_index])
        stored_outcome = "invalid"
        time_difference = 0.0
        accepted = stored_status == int(CellState.COMPLETED_VALID)
        if accepted and stored_value == cap:
            stored_outcome = "right_censored"
            accepted = strict.status is FirstFlipStatus.RIGHT_CENSORED
        elif accepted and stored_value < cap:
            stored_outcome = "event_observed"
            accepted = bool(
                strict.status is FirstFlipStatus.EVENT_OBSERVED
                and strict.attribution is EventAttribution.UNIQUE
                and strict.event_time_seconds is not None
                and strict.event_time_seconds < fixed_spec.observation_horizon_seconds
            )
            if strict.dimensionless_event_time is not None:
                time_difference = abs(
                    stored_value * fixed_spec.gravity_timescale_seconds
                    - strict.event_time_seconds
                )
                accepted = accepted and time_difference <= EVENT_TIME_CONVERGENCE_SECONDS
        else:
            accepted = False
        comparisons.append(
            {
                "theta2_index": theta2_index,
                "theta1_index": theta1_index,
                "theta2_radians": theta2,
                "theta1_radians": theta1,
                "stored_outcome": stored_outcome,
                "stored_dimensionless_time": stored_value,
                "strict_status": strict.status.value,
                "strict_event_time_seconds": strict.event_time_seconds,
                "strict_event_identity": (
                    strict.event_identities[0].label
                    if len(strict.event_identities) == 1
                    else None
                ),
                "event_time_difference_seconds": time_difference,
                "accepted": accepted,
            }
        )
    return FirstFlipSpotValidation(
        accepted=all(item["accepted"] for item in comparisons),
        selected_indices=selected,
        maximum_event_time_difference_seconds=max(
            item["event_time_difference_seconds"] for item in comparisons
        ),
        comparisons=tuple(comparisons),
    )
