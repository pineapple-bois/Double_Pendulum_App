import numpy as np
import pytest

from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian


SIMPLE_PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
COMPOUND_PARAMETERS = {l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81}
INITIAL_CONDITIONS_DEGREES = [10.0, 20.0, 0.0, 0.0]
TIME_VECTOR = [0.0, 0.05, 4]

# Current behavior note: the Hamiltonian class state is
# [theta1, theta2, p_theta_1, p_theta_2], but the app passes the same
# UI-shaped degree values used by the Lagrangian angular-velocity state.
# These tests preserve that contract without asserting it is physically final.


@pytest.mark.parametrize(
    ("model_class", "model_type", "parameters"),
    [
        (DoublePendulumLagrangian, "simple", SIMPLE_PARAMETERS),
        (DoublePendulumHamiltonian, "simple", SIMPLE_PARAMETERS),
        (DoublePendulumLagrangian, "compound", COMPOUND_PARAMETERS),
        (DoublePendulumHamiltonian, "compound", COMPOUND_PARAMETERS),
    ],
)
def test_model_simulations_return_expected_shape_and_finite_values(
    model_class,
    model_type,
    parameters,
):
    pendulum = model_class(parameters, INITIAL_CONDITIONS_DEGREES, TIME_VECTOR, model=model_type)

    assert pendulum.sol.shape == (TIME_VECTOR[2], 4)
    assert pendulum.time.shape == (TIME_VECTOR[2],)
    assert np.all(np.isfinite(pendulum.sol))


@pytest.mark.parametrize(
    ("model_class", "model_type", "parameters"),
    [
        (DoublePendulumLagrangian, "simple", SIMPLE_PARAMETERS),
        (DoublePendulumHamiltonian, "simple", SIMPLE_PARAMETERS),
    ],
)
def test_first_solution_row_matches_initial_conditions_in_radians(
    model_class,
    model_type,
    parameters,
):
    pendulum = model_class(parameters, INITIAL_CONDITIONS_DEGREES, TIME_VECTOR, model=model_type)

    np.testing.assert_allclose(
        pendulum.sol[0],
        np.deg2rad(INITIAL_CONDITIONS_DEGREES),
        rtol=0,
        atol=1e-12,
    )


@pytest.mark.parametrize(
    ("model_class", "model_type", "parameters"),
    [
        (DoublePendulumLagrangian, "simple", SIMPLE_PARAMETERS),
        (DoublePendulumHamiltonian, "simple", SIMPLE_PARAMETERS),
    ],
)
def test_precomputed_positions_have_expected_dimensions_and_finite_values(
    model_class,
    model_type,
    parameters,
):
    pendulum = model_class(parameters, INITIAL_CONDITIONS_DEGREES, TIME_VECTOR, model=model_type)
    pendulum.precompute_positions()

    assert pendulum.precomputed_positions.shape == (4, TIME_VECTOR[2])
    assert np.all(np.isfinite(pendulum.precomputed_positions))


def test_static_vertical_initial_condition_positions_are_consistent():
    pendulum = DoublePendulumLagrangian(
        SIMPLE_PARAMETERS,
        [0.0, 0.0, 0.0, 0.0],
        TIME_VECTOR,
        model="simple",
    )

    x_1, y_1, x_2, y_2 = pendulum._calculate_positions()

    np.testing.assert_allclose(x_1[0], 0.0, atol=1e-12)
    np.testing.assert_allclose(y_1[0], -SIMPLE_PARAMETERS[l1], atol=1e-12)
    np.testing.assert_allclose(x_2[0], 0.0, atol=1e-12)
    np.testing.assert_allclose(y_2[0], -(SIMPLE_PARAMETERS[l1] + SIMPLE_PARAMETERS[l2]), atol=1e-12)
