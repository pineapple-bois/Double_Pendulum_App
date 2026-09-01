"""Regression coverage for the promoted Experiment 015 segment boundary."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


STRAND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
for path in (STRAND_ROOT, REPOSITORY_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fortran_dop853 as fortran_module
from compiled import compiled_rhs, run_renormalized_tangent_compiled
from compiled_equivalence import (
    CYCLE_LOG_ABSOLUTE_TOLERANCE,
    ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
    FINAL_REFERENCE_DISTANCE_TOLERANCE,
    FINAL_TANGENT_DISTANCE_TOLERANCE,
    RATE_ABSOLUTE_TOLERANCE,
    VALIDATION_ANGLE_PAIRS_DEGREES,
    compare_results,
    validation_spec,
)
from evaluation import evaluate_renormalized_tangent_reference
from fortran_dop853 import (
    COMPILED_FORTRAN_EVALUATOR,
    _integrate_fortran_dop853_segment,
    evaluate_renormalized_tangent_compiled_fortran,
    run_renormalized_tangent_compiled_fortran,
)
from reference import (
    EulerLagrangeDynamics,
    RenormalizedTangentSpec,
    _run_renormalized_tangent_with_rhs,
    _solve_segment,
    run_renormalized_tangent,
)
from development.chaos_content.prototypes.state_space_fields import EvaluationStatus


@pytest.fixture(scope="module")
def promoted_comparisons():
    results = []
    for angle_pair in VALIDATION_ANGLE_PAIRS_DEGREES:
        spec = validation_spec(*angle_pair)
        oracle = run_renormalized_tangent_compiled(spec)
        promoted = run_renormalized_tangent_compiled_fortran(spec)
        results.append(
            (angle_pair, oracle, promoted, compare_results(oracle, promoted))
        )
    return results


def test_five_case_experiment_015_equivalence_is_preserved(
    promoted_comparisons,
) -> None:
    for angle_pair, oracle, promoted, comparison in promoted_comparisons:
        assert comparison["accepted"], angle_pair
        assert comparison["absolute_rate_error_per_second"] <= (
            RATE_ABSOLUTE_TOLERANCE
        )
        assert comparison["maximum_cycle_log_absolute_error"] <= (
            CYCLE_LOG_ABSOLUTE_TOLERANCE
        )
        assert comparison["final_reference_candidate_a_distance"] <= (
            FINAL_REFERENCE_DISTANCE_TOLERANCE
        )
        assert comparison["final_tangent_candidate_a_distance"] <= (
            FINAL_TANGENT_DISTANCE_TOLERANCE
        )
        assert comparison["energy_diagnostic_absolute_error"] <= (
            ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
        )
        assert promoted.spec == oracle.spec
        assert promoted.diagnostics.numerically_valid == (
            oracle.diagnostics.numerically_valid
        )
        assert promoted.diagnostics.validity_issues == (
            oracle.diagnostics.validity_issues
        )
        assert (
            promoted.diagnostics.maximum_normalized_reference_energy_drift
            <= promoted.spec.energy_drift_limit
        )


def test_promoted_cycle_bookkeeping_remains_the_shared_contract(
    promoted_comparisons,
) -> None:
    for _angle_pair, oracle, promoted, _comparison in promoted_comparisons:
        np.testing.assert_array_equal(promoted.cycle_end_time, oracle.cycle_end_time)
        assert len(promoted.cycle_end_time) == promoted.diagnostics.segment_count == 20
        assert np.all(np.isfinite(promoted.stretch_factor))
        assert np.all(promoted.stretch_factor > 0.0)
        np.testing.assert_allclose(
            promoted.log_stretch_increment,
            np.log(promoted.stretch_factor),
            rtol=0.0,
            atol=2.0e-15,
        )
        np.testing.assert_allclose(
            promoted.cumulative_log_stretch,
            np.cumsum(promoted.log_stretch_increment),
            rtol=0.0,
            atol=2.0e-15,
        )
        assert promoted.finite_time_stretching_rate == pytest.approx(
            promoted.cumulative_log_stretch[-1] / promoted.spec.duration,
            rel=0.0,
            abs=2.0e-15,
        )
        assert (
            promoted.diagnostics.maximum_post_renormalization_norm_error
            <= promoted.spec.renormalization_norm_tolerance
        )


def test_promoted_segment_observes_valid_accepted_steps() -> None:
    spec = validation_spec(179.0, 179.0)
    promoted = run_renormalized_tangent_compiled_fortran(spec)
    initial = np.concatenate(
        (spec.initial_state.as_array(), np.asarray(spec.initial_tangent, dtype=float))
    )
    requested = np.linspace(0.0, spec.renormalization_interval, 26)
    segment = _integrate_fortran_dop853_segment(
        compiled_rhs(spec.parameters),
        initial,
        requested,
        spec.solver,
        promoted.diagnostics.max_step_seconds,
    )

    assert segment.return_code == 1
    assert segment.warning_messages == ()
    assert segment.function_evaluations > 0
    assert len(segment.time) > 2
    assert segment.time[0] == pytest.approx(0.0, rel=0.0, abs=1.0e-13)
    assert segment.time[-1] == pytest.approx(
        spec.renormalization_interval, rel=0.0, abs=1.0e-13
    )
    assert np.all(np.diff(segment.time) > 0.0)
    assert np.max(np.diff(segment.time)) <= (
        promoted.diagnostics.max_step_seconds
        + fortran_module._MAX_STEP_FLOATING_POINT_ALLOWANCE
    )
    assert segment.state.shape == (len(segment.time), 8)
    assert np.all(np.isfinite(segment.state))


def test_explicit_oracle_segment_solver_reproduces_existing_paths() -> None:
    spec = RenormalizedTangentSpec(duration=0.25)

    compiled_default = run_renormalized_tangent_compiled(spec)
    compiled_explicit = _run_renormalized_tangent_with_rhs(
        spec,
        compiled_rhs(spec.parameters),
        segment_solver=_solve_segment,
    )
    assert compiled_explicit.finite_time_stretching_rate == (
        compiled_default.finite_time_stretching_rate
    )
    np.testing.assert_array_equal(
        compiled_explicit.final_reference_state,
        compiled_default.final_reference_state,
    )
    np.testing.assert_array_equal(
        compiled_explicit.final_unit_tangent,
        compiled_default.final_unit_tangent,
    )
    assert compiled_explicit.diagnostics == compiled_default.diagnostics

    reference_default = run_renormalized_tangent(spec)
    dynamics = EulerLagrangeDynamics(spec.parameters)
    reference_explicit = _run_renormalized_tangent_with_rhs(
        spec,
        dynamics.reference_and_tangent_rhs,
        segment_solver=_solve_segment,
    )
    assert reference_explicit.finite_time_stretching_rate == (
        reference_default.finite_time_stretching_rate
    )
    np.testing.assert_array_equal(
        reference_explicit.final_reference_state,
        reference_default.final_reference_state,
    )
    np.testing.assert_array_equal(
        reference_explicit.final_unit_tangent,
        reference_default.final_unit_tangent,
    )
    assert reference_explicit.diagnostics == reference_default.diagnostics


def test_promoted_evaluator_preserves_valid_and_invalid_outcome_semantics() -> None:
    valid_spec = RenormalizedTangentSpec(duration=0.25)
    oracle_valid = evaluate_renormalized_tangent_reference(valid_spec)
    promoted_valid = evaluate_renormalized_tangent_compiled_fortran(valid_spec)
    assert oracle_valid.status is promoted_valid.status is EvaluationStatus.COMPLETED_VALID
    assert promoted_valid.evaluator == COMPILED_FORTRAN_EVALUATOR
    assert promoted_valid.value == pytest.approx(
        oracle_valid.value, rel=0.0, abs=RATE_ABSOLUTE_TOLERANCE
    )

    invalid_spec = RenormalizedTangentSpec(
        duration=0.25,
        energy_drift_limit=1.0e-20,
    )
    oracle_invalid = evaluate_renormalized_tangent_reference(invalid_spec)
    promoted_invalid = evaluate_renormalized_tangent_compiled_fortran(invalid_spec)
    assert (
        oracle_invalid.status
        is promoted_invalid.status
        is EvaluationStatus.COMPLETED_INVALID
    )
    assert promoted_invalid.validity_issues == oracle_invalid.validity_issues


def test_promoted_evaluator_bounds_runtime_errors_only(monkeypatch) -> None:
    def numerical_error(*_args, **_kwargs):
        raise RuntimeError("Fortran integration failed")

    monkeypatch.setattr(
        fortran_module,
        "_solve_fortran_dop853_segment",
        numerical_error,
    )
    outcome = evaluate_renormalized_tangent_compiled_fortran(
        RenormalizedTangentSpec(duration=0.25)
    )
    assert outcome.status is EvaluationStatus.EXECUTION_ERROR
    assert outcome.error_type == "RuntimeError"
    assert outcome.error_message == "Fortran integration failed"

    def programming_error(*_args, **_kwargs):
        raise ValueError("programming defect")

    monkeypatch.setattr(
        fortran_module,
        "_solve_fortran_dop853_segment",
        programming_error,
    )
    with pytest.raises(ValueError, match="programming defect"):
        evaluate_renormalized_tangent_compiled_fortran(
            RenormalizedTangentSpec(duration=0.25)
        )


def test_low_level_numerical_failure_is_translated(monkeypatch) -> None:
    class FailedIntegrator:
        def set_integrator(self, *_args, **_kwargs):
            return self

        def set_solout(self, _callback):
            return self

        def set_initial_value(self, initial, start):
            self.initial = np.asarray(initial)
            self.t = start
            return self

        def integrate(self, _end):
            return self.initial

        def successful(self):
            return False

        def get_return_code(self):
            return -2

    monkeypatch.setattr(fortran_module, "ode", lambda _rhs: FailedIntegrator())
    spec = RenormalizedTangentSpec(duration=0.25)
    with pytest.raises(RuntimeError, match="return code -2"):
        _integrate_fortran_dop853_segment(
            compiled_rhs(spec.parameters),
            np.ones(8),
            np.asarray((0.0, 0.25)),
            spec.solver,
            0.01,
        )


def test_low_level_specification_errors_propagate() -> None:
    spec = RenormalizedTangentSpec(duration=0.25)
    with pytest.raises(ValueError, match="only DOP853"):
        _integrate_fortran_dop853_segment(
            compiled_rhs(spec.parameters),
            np.ones(8),
            np.asarray((0.0, 0.25)),
            fortran_module.SolverSpec(method="RK45"),
            0.01,
        )
