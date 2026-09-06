"""Operational promotion gates for the compiled first-flip RHS."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.src.first_flip import field_adapter
from development.chaos_content.prototypes.state_space_maps.src.first_flip.compiled import (
    FIRST_FLIP_COMPILED_EVALUATOR,
    FirstFlipCompiledUnavailableError,
    first_flip_time_compiled,
    initialize_compiled_rhs,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.field_adapter import (
    FIRST_FLIP_REFERENCE_EVALUATOR,
    ENERGY_DRIFT_LIMIT,
    EVENT_SURFACE_RESIDUAL_LIMIT,
    EVENT_TIME_CONVERGENCE_SECONDS,
    MAXIMUM_ACCEPTED_ANGULAR_INCREMENT,
    FirstFlipFieldSpec,
    adapt_first_flip_result,
    first_flip_evaluator_binding,
    initialize_first_flip_field_worker,
    periodic_first_flip_field_definition,
    run_periodic_first_flip_field,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.reference import first_flip_time
from development.chaos_content.prototypes.state_space_maps.src.generation import (
    IntegrityError,
    ScalarCellTask,
    read_authoritative_field,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import EulerLagrangeState
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import EvaluationStatus


EVIDENCE = Path(__file__).resolve().parents[2] / "investigations/performance/evidence/current/first_flip_compiled_rhs_feasibility.json"


def _task(theta1: float, theta2: float) -> ScalarCellTask:
    return ScalarCellTask(0, 0, 0, theta2, theta1)


def test_supported_compiled_and_ineligible_trusted_dispatch() -> None:
    compiled = first_flip_evaluator_binding(FirstFlipFieldSpec(), force_compiled=True)
    trusted = first_flip_evaluator_binding(
        FirstFlipFieldSpec(observation_horizon_seconds=2.0)
    )
    assert compiled.execution_routes[0] == FIRST_FLIP_COMPILED_EVALUATOR
    assert trusted.execution_routes == (FIRST_FLIP_REFERENCE_EVALUATOR,)
    assert periodic_first_flip_field_definition(4, force_compiled=True).evaluator_provenance["route"] == FIRST_FLIP_COMPILED_EVALUATOR
    assert periodic_first_flip_field_definition(
        4, FirstFlipFieldSpec(observation_horizon_seconds=2.0)
    ).evaluator_provenance["route"] == FIRST_FLIP_REFERENCE_EVALUATOR


def test_unsupported_build_selects_trusted_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        field_adapter,
        "first_flip_compiled_support",
        lambda: SimpleNamespace(supported=False, reason="unsupported fixture"),
    )
    binding = first_flip_evaluator_binding(FirstFlipFieldSpec(), force_compiled=True)
    assert binding.execution_routes == (FIRST_FLIP_REFERENCE_EVALUATOR,)
    assert periodic_first_flip_field_definition(4, force_compiled=True).evaluator_provenance["route"] == FIRST_FLIP_REFERENCE_EVALUATOR


def test_compiled_initialization_is_cached() -> None:
    initialize_compiled_rhs.cache_clear()
    parameters = FirstFlipFieldSpec().parameters
    cold = initialize_compiled_rhs(parameters)
    warm = initialize_compiled_rhs(parameters)
    assert cold is warm
    assert np.all(np.isfinite(warm(0.0, np.zeros(4))))


def test_initialization_unavailability_recovers_to_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(_parameters):
        raise FirstFlipCompiledUnavailableError("controlled unavailable")

    monkeypatch.setattr(field_adapter, "initialize_compiled_rhs", unavailable)
    spec = FirstFlipFieldSpec()
    initialize_first_flip_field_worker(spec, force_compiled=True)
    result = field_adapter.evaluate_first_flip_field_cell(
        _task(float(np.deg2rad(-150.0)), float(np.deg2rad(-150.0)))
    )
    assert result.status is EvaluationStatus.COMPLETED_VALID
    assert result.evaluator == FIRST_FLIP_REFERENCE_EVALUATOR
    assert result.attempted_evaluators == (FIRST_FLIP_COMPILED_EVALUATOR,)
    assert result.recovery_reason == "compiled_first_flip_initialization_unavailable"


def test_compiled_numerical_rejection_replays_trusted_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = FirstFlipFieldSpec()
    state = EulerLagrangeState.from_degrees(-150.0, -150.0, 0.0, 0.0)
    rejected = replace(
        first_flip_time(state), maximum_normalized_energy_drift=1.0
    )
    initialize_first_flip_field_worker(spec, force_compiled=True)
    monkeypatch.setattr(
        field_adapter, "first_flip_time_compiled", lambda *args, **kwargs: rejected
    )
    result = field_adapter.evaluate_first_flip_field_cell(
        _task(state.theta1, state.theta2)
    )
    assert result.status is EvaluationStatus.COMPLETED_VALID
    assert result.evaluator == FIRST_FLIP_REFERENCE_EVALUATOR
    assert result.recovery_reason == "compiled_first_flip_numerical_rejection"
    assert result.attempted_evaluators == (FIRST_FLIP_COMPILED_EVALUATOR,)


def test_unexpected_compiled_programming_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = FirstFlipFieldSpec()
    initialize_first_flip_field_worker(spec, force_compiled=True)
    monkeypatch.setattr(
        field_adapter,
        "first_flip_time_compiled",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("programming error")),
    )
    with pytest.raises(RuntimeError, match="programming error"):
        field_adapter.evaluate_first_flip_field_cell(_task(0.0, 0.0))


def test_saved_37_cases_pass_production_compiled_gates() -> None:
    payload = json.loads(EVIDENCE.read_text())
    spec = FirstFlipFieldSpec()
    for case in payload["cases"]:
        state = EulerLagrangeState(
            case["theta1_radians"], case["theta2_radians"], 0.0, 0.0
        )
        trusted = first_flip_time(
            state, spec.parameters, spec.solver, spec.observation_horizon_seconds
        )
        compiled = first_flip_time_compiled(
            state, spec.parameters, spec.solver, spec.observation_horizon_seconds
        )
        trusted_adapter = adapt_first_flip_result(trusted, spec)
        compiled_adapter = adapt_first_flip_result(
            compiled, spec, evaluator=FIRST_FLIP_COMPILED_EVALUATOR
        )
        assert trusted_adapter.status is EvaluationStatus.COMPLETED_VALID
        assert compiled_adapter.status is EvaluationStatus.COMPLETED_VALID
        assert compiled.status is trusted.status
        assert compiled.event_identities == trusted.event_identities
        assert compiled.raw_event_counts == trusted.raw_event_counts
        assert compiled.winning_arm == trusted.winning_arm
        assert compiled.winning_direction == trusted.winning_direction
        assert compiled.rhs_evaluations == trusted.rhs_evaluations
        assert compiled.maximum_accepted_angular_increment < MAXIMUM_ACCEPTED_ANGULAR_INCREMENT
        assert trusted.maximum_accepted_angular_increment < MAXIMUM_ACCEPTED_ANGULAR_INCREMENT
        assert compiled.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT
        assert trusted.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT
        assert abs(compiled.maximum_normalized_energy_drift - trusted.maximum_normalized_energy_drift) <= ENERGY_DRIFT_LIMIT
        if trusted.event_time_seconds is not None:
            assert compiled.event_time_seconds is not None
            assert abs(compiled.event_time_seconds - trusted.event_time_seconds) <= EVENT_TIME_CONVERGENCE_SECONDS
            assert np.max(np.abs(np.asarray(compiled.event_state) - np.asarray(trusted.event_state))) <= 5.0e-7
            trusted_residuals = {item.identity: item.residual for item in trusted.event_surface_residuals}
            for item in compiled.event_surface_residuals:
                if item.identity in compiled.event_identities:
                    assert abs(item.residual) <= EVENT_SURFACE_RESIDUAL_LIMIT
                    assert abs(item.residual - trusted_residuals[item.identity]) <= EVENT_SURFACE_RESIDUAL_LIMIT


def test_spawn_persistence_resume_and_cross_definition_rejection(tmp_path: Path) -> None:
    compiled_path = tmp_path / "compiled.h5"
    trusted_path = tmp_path / "trusted.h5"
    spec = FirstFlipFieldSpec()
    created = run_periodic_first_flip_field(compiled_path, 2, mode="create", spec=spec, force_compiled=True)
    resumed = run_periodic_first_flip_field(compiled_path, 2, mode="resume", spec=spec, force_compiled=True)
    snapshot = read_authoritative_field(compiled_path)
    assert created.all_workers_stopped
    assert resumed.evaluated_cells == 0
    assert set(np.unique(snapshot.execution_route)) == {2}
    assert snapshot.metadata["evaluator_provenance"]["compiled"]["kernel_source_sha256"]
    with pytest.raises(IntegrityError):
        run_periodic_first_flip_field(
            compiled_path, 2, mode="resume", spec=spec, force_trusted=True
        )
    run_periodic_first_flip_field(
        trusted_path, 2, mode="create", spec=spec, force_trusted=True
    )
    with pytest.raises(IntegrityError):
        run_periodic_first_flip_field(trusted_path, 2, mode="resume", spec=spec, force_compiled=True)
