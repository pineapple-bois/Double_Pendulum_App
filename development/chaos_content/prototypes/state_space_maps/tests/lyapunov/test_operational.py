"""Guard, recovery, and provenance tests for operational S1 selection."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from development.chaos_content.prototypes.state_space_maps.src.lyapunov import operational as operational_module
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
    evaluate_renormalized_tangent_hybrid,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.operational import (
    S1_RECOVERY_BORDERLINE_DIAGNOSTIC,
    S1_RECOVERY_EXECUTION_ERROR,
    S1_RECOVERY_NUMERICAL_REJECTION,
    evaluate_renormalized_tangent_operational,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    EulerLagrangeState,
    RenormalizedTangentDiagnostics,
    RenormalizedTangentSpec,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.s1 import (
    S1_EVALUATOR,
    s1_build_support,
)
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)


def _diagnostics(
    *,
    energy: float = 1.0e-10,
    norm: float = 1.0e-16,
    valid: bool = True,
) -> RenormalizedTangentDiagnostics:
    issues = () if valid else ("reference energy drift exceeded its declared limit",)
    return RenormalizedTangentDiagnostics(
        maximum_normalized_reference_energy_drift=energy,
        maximum_post_renormalization_norm_error=norm,
        max_step_seconds=0.009977357137720327,
        segment_count=20,
        solver_function_evaluations=100,
        numerically_valid=valid,
        validity_issues=issues,
    )


def _valid(evaluator: str = HYBRID_FAST_EVALUATOR) -> ScalarEvaluation:
    return ScalarEvaluation(
        status=EvaluationStatus.COMPLETED_VALID,
        value=1.25,
        diagnostics=_diagnostics(),
        elapsed_seconds=0.01,
        evaluator=evaluator,
    )


def test_eligible_s1_success_has_distinct_route_status_and_provenance() -> None:
    if not s1_build_support().supported:
        pytest.skip("S1 operational success runs only on the validated build")
    result = evaluate_renormalized_tangent_operational(RenormalizedTangentSpec())

    assert result.status is EvaluationStatus.COMPLETED_VALID
    assert result.evaluator == S1_EVALUATOR
    assert result.attempted_evaluators == ()
    assert result.recovery_reason is None
    assert result.implementation_provenance["implementation"] == S1_EVALUATOR
    assert result.implementation_provenance["supported"] is True


def test_ineligible_specification_routes_directly_to_existing_hybrid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = replace(RenormalizedTangentSpec(), sampling_interval=0.02)
    expected = evaluate_renormalized_tangent_hybrid(spec)
    monkeypatch.setattr(
        operational_module,
        "evaluate_renormalized_tangent_s1",
        lambda _spec: pytest.fail("ineligible specifications must not attempt S1"),
    )
    result = evaluate_renormalized_tangent_operational(spec)

    assert result.evaluator == expected.evaluator
    assert result.status is expected.status
    assert result.value == expected.value
    assert result.diagnostics == expected.diagnostics
    assert result.attempted_evaluators == ()


def test_unsupported_native_build_routes_directly_to_existing_hybrid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _valid()
    monkeypatch.setattr(
        operational_module,
        "s1_build_support",
        lambda: SimpleNamespace(supported=False, reason="unsupported fixture"),
    )
    monkeypatch.setattr(
        operational_module,
        "evaluate_renormalized_tangent_s1",
        lambda _spec: pytest.fail("unsupported builds must not attempt S1"),
    )
    monkeypatch.setattr(
        operational_module,
        "evaluate_renormalized_tangent_hybrid",
        lambda _spec: expected,
    )

    assert evaluate_renormalized_tangent_operational(
        RenormalizedTangentSpec()
    ) is expected


def test_s1_numerical_rejection_recovers_through_authoritative_hybrid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = ScalarEvaluation(
        status=EvaluationStatus.COMPLETED_INVALID,
        value=0.5,
        diagnostics=_diagnostics(energy=2.0e-7, valid=False),
        elapsed_seconds=0.01,
        evaluator=S1_EVALUATOR,
        validity_issues=("reference energy drift exceeded its declared limit",),
        implementation_provenance={"implementation": S1_EVALUATOR},
    )
    recovered = _valid()
    monkeypatch.setattr(
        operational_module, "s1_build_support", lambda: SimpleNamespace(supported=True)
    )
    monkeypatch.setattr(
        operational_module, "evaluate_renormalized_tangent_s1", lambda _spec: candidate
    )
    monkeypatch.setattr(
        operational_module, "evaluate_renormalized_tangent_hybrid", lambda _spec: recovered
    )

    result = evaluate_renormalized_tangent_operational(RenormalizedTangentSpec())
    assert result.evaluator == HYBRID_FAST_EVALUATOR
    assert result.status is EvaluationStatus.COMPLETED_VALID
    assert result.attempted_evaluators == (S1_EVALUATOR,)
    assert result.recovery_reason == S1_RECOVERY_NUMERICAL_REJECTION
    assert result.implementation_provenance == {}
    assert result.attempt_provenance[S1_EVALUATOR]["implementation"] == S1_EVALUATOR


def test_borderline_diagnostic_is_replayed_through_trusted_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = replace(
        _valid(S1_EVALUATOR),
        diagnostics=_diagnostics(energy=9.5e-8),
        implementation_provenance={"implementation": S1_EVALUATOR},
    )
    recovered = _valid()
    monkeypatch.setattr(
        operational_module, "s1_build_support", lambda: SimpleNamespace(supported=True)
    )
    monkeypatch.setattr(
        operational_module, "evaluate_renormalized_tangent_s1", lambda _spec: candidate
    )
    monkeypatch.setattr(
        operational_module, "evaluate_renormalized_tangent_hybrid", lambda _spec: recovered
    )

    result = evaluate_renormalized_tangent_operational(RenormalizedTangentSpec())
    assert result.evaluator == HYBRID_FAST_EVALUATOR
    assert result.recovery_reason == S1_RECOVERY_BORDERLINE_DIAGNOSTIC
    assert result.attempted_evaluators == (S1_EVALUATOR,)


def test_native_execution_or_build_failure_recovers_without_string_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = ScalarEvaluation(
        status=EvaluationStatus.EXECUTION_ERROR,
        value=None,
        diagnostics=None,
        elapsed_seconds=0.01,
        evaluator=S1_EVALUATOR,
        error_type="S1NativeUnavailableError",
        error_message="arbitrary message that is not inspected",
        implementation_provenance={"implementation": S1_EVALUATOR},
    )
    recovered = _valid(HYBRID_FALLBACK_EVALUATOR)
    monkeypatch.setattr(
        operational_module, "s1_build_support", lambda: SimpleNamespace(supported=True)
    )
    monkeypatch.setattr(
        operational_module, "evaluate_renormalized_tangent_s1", lambda _spec: candidate
    )
    monkeypatch.setattr(
        operational_module, "evaluate_renormalized_tangent_hybrid", lambda _spec: recovered
    )

    result = evaluate_renormalized_tangent_operational(RenormalizedTangentSpec())
    assert result.evaluator == HYBRID_FALLBACK_EVALUATOR
    assert result.recovery_reason == S1_RECOVERY_EXECUTION_ERROR
    assert result.attempted_evaluators == (S1_EVALUATOR,)
    assert result.attempt_provenance[S1_EVALUATOR]["implementation"] == S1_EVALUATOR


def test_endpoint_cap_rejection_delegates_fallback_decision_to_hybrid() -> None:
    if not s1_build_support().supported:
        pytest.skip("S1 endpoint recovery runs only on the validated build")
    spec = RenormalizedTangentSpec(
        initial_state=EulerLagrangeState.from_degrees(
            177.75,
            170.25,
            0.0,
            0.0,
        )
    )
    result = evaluate_renormalized_tangent_operational(spec)

    assert result.evaluator == HYBRID_FALLBACK_EVALUATOR
    assert result.status is EvaluationStatus.COMPLETED_VALID
    assert result.attempted_evaluators == (S1_EVALUATOR,)
    assert result.recovery_reason == S1_RECOVERY_EXECUTION_ERROR


def test_programming_errors_propagate_without_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        operational_module, "s1_build_support", lambda: SimpleNamespace(supported=True)
    )
    monkeypatch.setattr(
        operational_module,
        "evaluate_renormalized_tangent_s1",
        lambda _spec: (_ for _ in ()).throw(ValueError("controlled programming error")),
    )
    monkeypatch.setattr(
        operational_module,
        "evaluate_renormalized_tangent_hybrid",
        lambda _spec: pytest.fail("programming errors must not recover"),
    )

    with pytest.raises(ValueError, match="controlled programming error"):
        evaluate_renormalized_tangent_operational(RenormalizedTangentSpec())


def test_nonfinite_specification_error_precedes_route_selection() -> None:
    spec = replace(
        RenormalizedTangentSpec(),
        initial_state=EulerLagrangeState(float("nan"), 0.0, 0.0, 0.0),
    )
    with pytest.raises(ValueError, match="finite"):
        evaluate_renormalized_tangent_operational(spec)
