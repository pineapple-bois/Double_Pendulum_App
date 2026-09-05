"""Check the validation harness rejects deliberate scientific regressions."""
from dataclasses import replace

import pytest

from development.chaos_content.prototypes.state_space_maps.investigations.performance.s1_history.validate_s1_promotion import (
    HORIZONS, compare, trusted_run, validation_cases,
)


@pytest.fixture(scope="module")
def result():
    return trusted_run(replace(validation_cases()[0]["spec"],duration=1.0))


@pytest.mark.parametrize("field", (
    "cumulative_finite_time_rate", "cumulative_log_stretch", "log_stretch_increment",
    "final_reference_state", "final_unit_tangent",
))
def test_comparison_rejects_perturbed_scientific_quantities(result,field):
    changed=getattr(result,field).copy()
    changed[-1]+=1e-3
    assert not compare(result,replace(result,**{field:changed}))["accepted"]


@pytest.mark.parametrize("field,value", (
    ("solver_function_evaluations",-1), ("segment_count",-1),
    ("maximum_normalized_reference_energy_drift",1e-5),
    ("maximum_post_renormalization_norm_error",1e-5),
    ("numerically_valid",False),
))
def test_comparison_rejects_diagnostic_or_status_regressions(result,field,value):
    candidate=replace(result,diagnostics=replace(result.diagnostics,**{field:value}))
    assert not compare(result,candidate)["accepted"]


def test_fixed_set_constructs_at_every_required_horizon():
    cases=validation_cases()
    assert len(cases)==104
    assert HORIZONS==(1.,2.,5.,10.,20.)
    for case in cases:
        for horizon in HORIZONS:
            replace(case["spec"],duration=horizon)


def test_identical_result_is_accepted(result):
    assert compare(result,result)["accepted"]
