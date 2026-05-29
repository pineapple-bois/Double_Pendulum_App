import numpy as np
import pytest

from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import (
    DoublePendulumHamiltonian,
    DoublePendulumLagrangian,
    HAMILTONIAN_SOLVER_STATE_CONVENTION,
    HAMILTONIAN_STATE_VARIABLE_NAMES,
    LAGRANGIAN_SOLVER_STATE_CONVENTION,
    LAGRANGIAN_STATE_VARIABLE_NAMES,
    USER_INITIAL_CONDITION_NAMES,
)


SIMPLE_PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
COMPOUND_PARAMETERS = {l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81}
NONZERO_INITIAL_CONDITIONS_DEGREES = [45.0, -30.0, 10.0, -5.0]
ZERO_VELOCITY_INITIAL_CONDITIONS_DEGREES = [45.0, -30.0, 0.0, 0.0]
TIME_VECTOR = [0.0, 0.05, 4]


def expected_simple_momenta(initial_conditions_degrees):
    theta_1, theta_2, omega_1, omega_2 = np.deg2rad(initial_conditions_degrees)
    return np.array(
        [
            (SIMPLE_PARAMETERS[m1] + SIMPLE_PARAMETERS[m2]) * SIMPLE_PARAMETERS[l1] ** 2 * omega_1
            + SIMPLE_PARAMETERS[m2]
            * SIMPLE_PARAMETERS[l1]
            * SIMPLE_PARAMETERS[l2]
            * np.cos(theta_1 - theta_2)
            * omega_2,
            SIMPLE_PARAMETERS[m2]
            * SIMPLE_PARAMETERS[l1]
            * SIMPLE_PARAMETERS[l2]
            * np.cos(theta_1 - theta_2)
            * omega_1
            + SIMPLE_PARAMETERS[m2] * SIMPLE_PARAMETERS[l2] ** 2 * omega_2,
        ]
    )


def expected_compound_momenta(initial_conditions_degrees):
    theta_1, theta_2, omega_1, omega_2 = np.deg2rad(initial_conditions_degrees)
    inertia_11 = (
        (7.0 / 12.0) * COMPOUND_PARAMETERS[M1] * COMPOUND_PARAMETERS[l1] ** 2
        + 0.25 * COMPOUND_PARAMETERS[M2] * COMPOUND_PARAMETERS[l1] ** 2
    )
    inertia_12 = (
        0.25
        * COMPOUND_PARAMETERS[M2]
        * COMPOUND_PARAMETERS[l1]
        * COMPOUND_PARAMETERS[l2]
        * np.cos(theta_1 - theta_2)
    )
    inertia_22 = (7.0 / 12.0) * COMPOUND_PARAMETERS[M2] * COMPOUND_PARAMETERS[l2] ** 2
    return np.array(
        [
            inertia_11 * omega_1 + inertia_12 * omega_2,
            inertia_12 * omega_1 + inertia_22 * omega_2,
        ]
    )


def test_lagrangian_preserves_user_facing_angular_velocity_state():
    pendulum = DoublePendulumLagrangian(
        SIMPLE_PARAMETERS,
        NONZERO_INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="simple",
    )

    expected_radians = np.deg2rad(NONZERO_INITIAL_CONDITIONS_DEGREES)
    np.testing.assert_allclose(pendulum.initial_conditions, expected_radians, rtol=0, atol=1e-12)
    np.testing.assert_allclose(pendulum.sol[0], expected_radians, rtol=0, atol=1e-12)
    np.testing.assert_allclose(
        pendulum.user_initial_conditions_degrees,
        NONZERO_INITIAL_CONDITIONS_DEGREES,
        rtol=0,
        atol=0,
    )
    assert pendulum.user_initial_condition_names == USER_INITIAL_CONDITION_NAMES
    assert pendulum.solver_state_variable_names == LAGRANGIAN_STATE_VARIABLE_NAMES
    assert pendulum.solver_state_convention == LAGRANGIAN_SOLVER_STATE_CONVENTION


def test_simple_hamiltonian_converts_nonzero_angular_velocities_to_momenta():
    pendulum = DoublePendulumHamiltonian(
        SIMPLE_PARAMETERS,
        NONZERO_INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="simple",
    )

    expected_angles = np.deg2rad(NONZERO_INITIAL_CONDITIONS_DEGREES[:2])
    expected_momenta = expected_simple_momenta(NONZERO_INITIAL_CONDITIONS_DEGREES)
    direct_velocity_tail = np.deg2rad(NONZERO_INITIAL_CONDITIONS_DEGREES[2:])

    np.testing.assert_allclose(pendulum.initial_conditions[:2], expected_angles, rtol=0, atol=1e-12)
    np.testing.assert_allclose(pendulum.initial_conditions[2:], expected_momenta, rtol=0, atol=1e-12)
    np.testing.assert_allclose(pendulum.sol[0], pendulum.initial_conditions, rtol=0, atol=1e-12)
    assert not np.allclose(pendulum.initial_conditions[2:], direct_velocity_tail, rtol=0, atol=1e-12)
    assert pendulum.user_initial_condition_names == USER_INITIAL_CONDITION_NAMES
    assert pendulum.solver_state_variable_names == HAMILTONIAN_STATE_VARIABLE_NAMES
    assert pendulum.solver_state_convention == HAMILTONIAN_SOLVER_STATE_CONVENTION
    assert pendulum.initial_condition_conversion == "angular_velocities_to_canonical_momenta"


def test_compound_hamiltonian_converts_nonzero_angular_velocities_to_momenta():
    pendulum = DoublePendulumHamiltonian(
        COMPOUND_PARAMETERS,
        NONZERO_INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="compound",
    )

    expected_angles = np.deg2rad(NONZERO_INITIAL_CONDITIONS_DEGREES[:2])
    expected_momenta = expected_compound_momenta(NONZERO_INITIAL_CONDITIONS_DEGREES)
    direct_velocity_tail = np.deg2rad(NONZERO_INITIAL_CONDITIONS_DEGREES[2:])

    np.testing.assert_allclose(pendulum.initial_conditions[:2], expected_angles, rtol=0, atol=1e-12)
    np.testing.assert_allclose(pendulum.initial_conditions[2:], expected_momenta, rtol=0, atol=1e-12)
    np.testing.assert_allclose(pendulum.sol[0], pendulum.initial_conditions, rtol=0, atol=1e-12)
    assert not np.allclose(pendulum.initial_conditions[2:], direct_velocity_tail, rtol=0, atol=1e-12)
    assert pendulum.user_initial_condition_names == USER_INITIAL_CONDITION_NAMES
    assert pendulum.solver_state_variable_names == HAMILTONIAN_STATE_VARIABLE_NAMES
    assert pendulum.solver_state_convention == HAMILTONIAN_SOLVER_STATE_CONVENTION


@pytest.mark.parametrize(
    ("model_type", "parameters"),
    [
        ("simple", SIMPLE_PARAMETERS),
        ("compound", COMPOUND_PARAMETERS),
    ],
)
def test_hamiltonian_zero_angular_velocities_map_to_zero_momenta(model_type, parameters):
    pendulum = DoublePendulumHamiltonian(
        parameters,
        ZERO_VELOCITY_INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model=model_type,
    )

    np.testing.assert_allclose(pendulum.initial_conditions[2:], [0.0, 0.0], rtol=0, atol=1e-12)
    np.testing.assert_allclose(pendulum.sol[0], pendulum.initial_conditions, rtol=0, atol=1e-12)
