"""Focused tests for Experiment 015's integration-boundary evidence."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import compiled_integration_boundary as experiment


@pytest.fixture(scope="module")
def equivalence_assessments():
    experiment._warm_numba_kernel()
    return experiment.assess_equivalence()


def test_validation_set_and_gates_are_the_existing_mechanical_contract() -> None:
    assert experiment.VALIDATION_ANGLE_PAIRS_DEGREES == (
        (179.0, 179.0),
        (169.0, 169.0),
        (169.0, 189.0),
        (189.0, 169.0),
        (189.0, 189.0),
    )
    assert experiment.RATE_ABSOLUTE_TOLERANCE == 1.0e-8
    assert experiment.CYCLE_LOG_ABSOLUTE_TOLERANCE == 5.0e-8
    assert experiment.FINAL_REFERENCE_DISTANCE_TOLERANCE == 1.0e-7
    assert experiment.FINAL_TANGENT_DISTANCE_TOLERANCE == 1.0e-7
    assert experiment.ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE == 1.0e-8
    assert experiment.MATERIAL_SPEEDUP_GATE == 2.0


def test_explicit_oracle_segment_seam_preserves_existing_compiled_result() -> None:
    spec = experiment.validation_spec(179.0, 179.0)
    default = experiment.run_renormalized_tangent_compiled(spec)
    injected = experiment._run_with_segment_solver(spec, experiment._solve_segment)

    assert injected.finite_time_stretching_rate == default.finite_time_stretching_rate
    np.testing.assert_array_equal(
        injected.log_stretch_increment,
        default.log_stretch_increment,
    )
    np.testing.assert_array_equal(
        injected.final_reference_state,
        default.final_reference_state,
    )
    np.testing.assert_array_equal(
        injected.final_unit_tangent,
        default.final_unit_tangent,
    )
    assert injected.diagnostics == default.diagnostics


def test_fortran_candidate_segment_mechanics() -> None:
    spec = experiment.validation_spec(179.0, 179.0)
    candidate = experiment.run_fortran_candidate(spec)
    mechanics = experiment._mechanics_assessment(candidate)

    assert mechanics["all_checks_passed"]
    assert mechanics["cycle_count"] == 20
    assert mechanics["cycle_times_match_exactly"]
    assert mechanics["positive_finite_stretch_factors"]
    assert mechanics["accepted_times_strictly_monotonic"]
    assert mechanics["accepted_steps_observed"]
    assert mechanics["all_segment_endpoints_reached"]
    assert mechanics["all_accepted_states_finite"]
    assert mechanics["return_codes_successful"]
    assert mechanics["max_step_enforced"]
    assert mechanics["accepted_step_count"] > 0
    assert mechanics["maximum_post_reset_candidate_a_norm_error"] <= 1.0e-12


def test_candidate_meets_all_five_equivalence_and_energy_gates(
    equivalence_assessments,
) -> None:
    assert len(equivalence_assessments) == 5
    for comparison in equivalence_assessments:
        assert comparison["accepted"], (
            comparison["theta1_degrees"],
            comparison["theta2_degrees"],
        )
        assert comparison["absolute_rate_error_per_second"] <= 1.0e-8
        assert comparison["maximum_cycle_log_absolute_error"] <= 5.0e-8
        assert comparison["final_reference_candidate_a_distance"] <= 1.0e-7
        assert comparison["final_tangent_candidate_a_distance"] <= 1.0e-7
        assert comparison["energy_diagnostic_absolute_error"] <= 1.0e-8
        assert comparison["both_energy_diagnostics_below_limit"]
        assert comparison["reference_numerically_valid"] == (
            comparison["compiled_numerically_valid"]
        )
        assert comparison["mechanics"]["all_checks_passed"]


def test_energy_sampling_distinction_is_explicit_and_bounded(
    equivalence_assessments,
) -> None:
    for comparison in equivalence_assessments:
        assert comparison["oracle_energy_sampling"] == (
            "uniform 0.01 s diagnostic grid"
        )
        assert comparison["candidate_energy_sampling"] == (
            "accepted Fortran DOP853 steps"
        )
        assert comparison["candidate_maximum_accepted_step_gap_seconds"] <= (
            comparison["mechanics"]["declared_max_step_seconds"]
            + experiment.MAX_STEP_FLOATING_POINT_ALLOWANCE
        )


def test_endpoint_only_control_is_explicitly_sparse_diagnostic_sampling() -> None:
    spec = experiment.validation_spec(179.0, 179.0)
    requested = np.linspace(0.0, spec.renormalization_interval, 26)
    initial = np.concatenate(
        (spec.initial_state.as_array(), np.asarray(spec.initial_tangent, dtype=float))
    )
    state, function_evaluations = experiment.solve_ivp_endpoint_only_segment(
        experiment.compiled_rhs(spec.parameters),
        initial,
        requested,
        spec.solver,
        min(
            np.sqrt(spec.characteristic_length / spec.parameters.gravity) / 32.0,
            spec.renormalization_interval / 25.0,
        ),
    )

    assert state.shape == (2, 8)
    assert function_evaluations > 0


def test_numerical_solver_failure_becomes_bounded_runtime_error(monkeypatch) -> None:
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

    monkeypatch.setattr(experiment, "ode", lambda _rhs: FailedIntegrator())
    spec = experiment.validation_spec(179.0, 179.0)
    solver = experiment.FortranDop853SegmentSolver()
    with pytest.raises(RuntimeError, match="return code -2"):
        solver(
            experiment.compiled_rhs(spec.parameters),
            np.ones(8),
            np.asarray((0.0, 0.25)),
            spec.solver,
            0.01,
        )


def test_programming_and_specification_errors_are_not_masked(monkeypatch) -> None:
    class ProgrammingErrorIntegrator:
        def set_integrator(self, *_args, **_kwargs):
            return self

        def set_solout(self, _callback):
            return self

        def set_initial_value(self, _initial, _start):
            return self

        def integrate(self, _end):
            raise ValueError("programming defect")

    monkeypatch.setattr(
        experiment,
        "ode",
        lambda _rhs: ProgrammingErrorIntegrator(),
    )
    spec = experiment.validation_spec(179.0, 179.0)
    solver = experiment.FortranDop853SegmentSolver()
    with pytest.raises(ValueError, match="programming defect"):
        solver(
            experiment.compiled_rhs(spec.parameters),
            np.ones(8),
            np.asarray((0.0, 0.25)),
            spec.solver,
            0.01,
        )

    with pytest.raises(ValueError, match="only the declared DOP853"):
        solver(
            experiment.compiled_rhs(spec.parameters),
            np.ones(8),
            np.asarray((0.0, 0.25)),
            experiment.SolverSpec(method="RK45"),
            0.01,
        )
