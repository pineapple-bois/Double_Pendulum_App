"""Focused experimental checks; production evaluator remains the authority."""
from dataclasses import replace

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.investigations.performance.benchmark_s1_compiled_loop import (
    CELLS, REJECTED_AT_T20, cell_spec, numerical_comparison,
)
from development.chaos_content.prototypes.state_space_maps.investigations.performance.s1_compiled_loop import (
    evaluate_compiled_loop, run_compiled_loop,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_dop853 import (
    run_renormalized_tangent_compiled_dop853 as trusted_run,
    evaluate_renormalized_tangent_compiled_dop853 as trusted_evaluate,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_equivalence import compare_results
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    PendulumParameters, SolverSpec,
)


@pytest.mark.parametrize("cell", CELLS, ids=[cell[0] for cell in CELLS])
@pytest.mark.parametrize("horizon", (5.0,20.0))
def test_existing_scientific_gates_and_solver_work(cell,horizon):
    spec=cell_spec(cell,horizon)
    reference,candidate=trusted_run(spec),run_compiled_loop(spec)
    comparison=numerical_comparison(reference,candidate)
    assert comparison["accepted"], comparison
    assert candidate.diagnostics.segment_count == round(horizon/0.25)
    assert candidate.diagnostics.max_step_seconds == reference.diagnostics.max_step_seconds
    assert (candidate.diagnostics.maximum_post_renormalization_norm_error
            <= spec.renormalization_norm_tolerance)
    np.testing.assert_allclose(candidate.stretch_factor, np.exp(candidate.log_stretch_increment),
                               rtol=1e-15,atol=0)
    np.testing.assert_allclose(candidate.cumulative_log_stretch,
                               np.cumsum(candidate.log_stretch_increment),rtol=0,atol=0)
    np.testing.assert_allclose(candidate.cumulative_finite_time_rate,
        candidate.cumulative_log_stretch/candidate.cycle_end_time,rtol=0,atol=0)


@pytest.mark.parametrize("cell,horizon", (
    (REJECTED_AT_T20,20.0),
    (("profile_fallback",-3.067961575771282,-np.pi),5.0),
))
def test_same_max_step_gate_without_fallback(cell,horizon):
    spec=cell_spec(cell,horizon)
    for runner in (trusted_run,run_compiled_loop):
        with pytest.raises(RuntimeError,match="exceeded the declared max_step"):
            runner(spec)
    reference,candidate=trusted_evaluate(spec),evaluate_compiled_loop(spec)
    assert reference.status == candidate.status
    assert reference.value is candidate.value is None


@pytest.mark.parametrize("field,limit", (
    ("energy_drift_limit",1e-18),
    ("renormalization_norm_tolerance",1e-20),
))
def test_diagnostic_gates_remain_enforced(field,limit):
    spec=replace(cell_spec(CELLS[2],5.0),**{field:limit})
    reference,candidate=trusted_run(spec),run_compiled_loop(spec)
    assert not candidate.diagnostics.numerically_valid
    assert candidate.diagnostics.validity_issues == reference.diagnostics.validity_issues
    assert compare_results(reference,candidate)["accepted"]
    assert trusted_evaluate(spec).status == evaluate_compiled_loop(spec).status


def test_nondefault_parameters_tangent_and_solver_policy():
    spec=replace(cell_spec(CELLS[1],1.0),
        parameters=PendulumParameters(1.3,0.7,1.2,0.9,9.4),
        characteristic_length=1.7,initial_tangent=(0.2,-0.3,0.4,0.1),
        solver=SolverSpec(rtol=2e-10,atol=3e-12,max_step=0.005),
        renormalization_interval=0.5,sampling_interval=0.02)
    comparison=numerical_comparison(trusted_run(spec),run_compiled_loop(spec))
    assert comparison["accepted"],comparison


def test_accepted_step_observation_policy_matches_operational_path():
    # The operational fast runner uses requested endpoints, with energy checked
    # at every accepted step. Changing interior sampling does not change it.
    spec=cell_spec(CELLS[1],5.0)
    changed=replace(spec,sampling_interval=0.037)
    for runner in (trusted_run,run_compiled_loop):
        first,second=runner(spec),runner(changed)
        np.testing.assert_array_equal(first.log_stretch_increment,second.log_stretch_increment)
        assert first.diagnostics == second.diagnostics


def test_other_solver_is_rejected():
    spec=replace(cell_spec(CELLS[1],5.0),solver=SolverSpec(method="RK45"))
    with pytest.raises(ValueError,match="DOP853"):
        run_compiled_loop(spec)
