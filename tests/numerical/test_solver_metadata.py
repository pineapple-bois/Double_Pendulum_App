import numpy as np
import pytest
from scipy.integrate import odeint

from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian


SIMPLE_PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
COMPOUND_PARAMETERS = {l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81}
INITIAL_CONDITIONS_DEGREES = [10.0, 20.0, 0.0, 0.0]
TIME_VECTOR = [0.0, 0.05, 4]


@pytest.mark.parametrize(
    ("model_class", "model_type", "parameters"),
    [
        (DoublePendulumLagrangian, "simple", SIMPLE_PARAMETERS),
        (DoublePendulumHamiltonian, "simple", SIMPLE_PARAMETERS),
        (DoublePendulumLagrangian, "compound", COMPOUND_PARAMETERS),
        (DoublePendulumHamiltonian, "compound", COMPOUND_PARAMETERS),
    ],
)
def test_solve_ivp_metadata_is_captured_without_changing_solution_behavior(
    model_class,
    model_type,
    parameters,
):
    pendulum = model_class(parameters, INITIAL_CONDITIONS_DEGREES, TIME_VECTOR, model=model_type)
    metadata = pendulum.solver_metadata

    assert pendulum.sol.shape == (TIME_VECTOR[2], 4)
    assert pendulum.time.shape == (TIME_VECTOR[2],)
    assert pendulum.solver_time.shape == pendulum.time.shape
    np.testing.assert_allclose(pendulum.solver_time, pendulum.time, rtol=0, atol=0)
    np.testing.assert_allclose(
        pendulum.sol[0],
        pendulum.initial_conditions,
        rtol=0,
        atol=1e-12,
    )

    assert metadata.integrator == "solve_ivp"
    assert metadata.success is True
    assert metadata.status == 0
    assert isinstance(metadata.message, str)
    assert metadata.message
    assert isinstance(metadata.nfev, int)
    assert metadata.nfev > 0
    assert metadata.requested_time_count == TIME_VECTOR[2]
    assert metadata.returned_time_count == TIME_VECTOR[2]
    assert metadata.requested_time_start == TIME_VECTOR[0]
    assert metadata.requested_time_end == TIME_VECTOR[1]
    assert metadata.returned_time_start == TIME_VECTOR[0]
    assert metadata.returned_time_end == TIME_VECTOR[1]
    assert metadata.returned_time_matches_requested is True
    assert metadata.solution_shape == pendulum.sol.shape
    assert metadata.solver_kwargs == {}

    metadata_dict = metadata.to_dict()
    assert metadata_dict["solution_shape"] == list(pendulum.sol.shape)
    assert metadata_dict["returned_time_matches_requested"] is True


def test_odeint_path_exposes_partial_metadata_without_solver_status_claims():
    pendulum = DoublePendulumLagrangian(
        SIMPLE_PARAMETERS,
        INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="simple",
        integrator=odeint,
    )
    metadata = pendulum.solver_metadata

    assert pendulum.sol.shape == (TIME_VECTOR[2], 4)
    assert pendulum.time.shape == (TIME_VECTOR[2],)
    assert metadata.integrator == "odeint"
    assert metadata.success is None
    assert metadata.status is None
    assert metadata.message is None
    assert metadata.nfev is None
    assert metadata.njev is None
    assert metadata.nlu is None
    assert metadata.requested_time_count == TIME_VECTOR[2]
    assert metadata.returned_time_count == TIME_VECTOR[2]
    assert metadata.returned_time_matches_requested is True
    assert metadata.solution_shape == pendulum.sol.shape
