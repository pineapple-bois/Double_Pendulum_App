import pytest

from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_DEFAULT_SOLVER_POLICY,
    SIMPLE_REFERENCE_SOLVER_POLICY,
    SOLVE_IVP_DEFAULT_BASELINE_POLICY,
    DoublePendulumHamiltonian,
    DoublePendulumLagrangian,
)


SIMPLE_PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
INITIAL_CONDITIONS_DEGREES = [0.0, 60.0, 0.0, 0.0]
TIME_VECTOR = [0.0, 0.2, 40]


def test_simple_default_policy_maps_to_moderate_dop853_kwargs():
    assert SIMPLE_DEFAULT_SOLVER_POLICY.name == "simple_default"
    assert SIMPLE_DEFAULT_SOLVER_POLICY.method == "DOP853"
    assert SIMPLE_DEFAULT_SOLVER_POLICY.rtol == 1e-6
    assert SIMPLE_DEFAULT_SOLVER_POLICY.atol == 1e-8
    assert SIMPLE_DEFAULT_SOLVER_POLICY.solve_ivp_kwargs() == {
        "method": "DOP853",
        "rtol": 1e-6,
        "atol": 1e-8,
    }


def test_simple_reference_policy_maps_to_strict_dop853_kwargs():
    assert SIMPLE_REFERENCE_SOLVER_POLICY.name == "simple_reference"
    assert SIMPLE_REFERENCE_SOLVER_POLICY.method == "DOP853"
    assert SIMPLE_REFERENCE_SOLVER_POLICY.rtol == 1e-9
    assert SIMPLE_REFERENCE_SOLVER_POLICY.atol == 1e-11
    assert SIMPLE_REFERENCE_SOLVER_POLICY.solve_ivp_kwargs() == {
        "method": "DOP853",
        "rtol": 1e-9,
        "atol": 1e-11,
    }


def test_solve_ivp_default_baseline_policy_is_explicit_negative_reference():
    assert SOLVE_IVP_DEFAULT_BASELINE_POLICY.name == "solve_ivp_default_baseline"
    assert SOLVE_IVP_DEFAULT_BASELINE_POLICY.method is None
    assert SOLVE_IVP_DEFAULT_BASELINE_POLICY.rtol is None
    assert SOLVE_IVP_DEFAULT_BASELINE_POLICY.atol is None
    assert SOLVE_IVP_DEFAULT_BASELINE_POLICY.solve_ivp_kwargs() == {}
    assert "baseline" in SOLVE_IVP_DEFAULT_BASELINE_POLICY.role
    assert "not the app-facing default" in SOLVE_IVP_DEFAULT_BASELINE_POLICY.role


@pytest.mark.parametrize("model_class", [DoublePendulumLagrangian, DoublePendulumHamiltonian])
def test_simple_policy_can_be_passed_to_model_construction(model_class):
    pendulum = model_class(
        SIMPLE_PARAMETERS,
        INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="simple",
        solver_policy=SIMPLE_DEFAULT_SOLVER_POLICY,
    )

    metadata = pendulum.solver_metadata
    assert pendulum.sol.shape == (TIME_VECTOR[2], 4)
    assert metadata.policy_name == "simple_default"
    assert metadata.method == "DOP853"
    assert metadata.rtol == 1e-6
    assert metadata.atol == 1e-8
    assert metadata.success is True
