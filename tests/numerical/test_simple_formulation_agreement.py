import numpy as np
import pytest

from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_DEFAULT_SOLVER_POLICY,
    SIMPLE_REFERENCE_SOLVER_POLICY,
    DoublePendulumHamiltonian,
    DoublePendulumLagrangian,
)


CASES = (
    (
        "low_energy_small_angles",
        [5.0, 7.0, 0.0, 0.0],
        {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81},
        [0.0, 1.0, 200],
    ),
    (
        "screenshot_like_simple_start",
        [0.0, 60.0, 0.0, 0.0],
        {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81},
        [0.0, 1.0, 200],
    ),
    (
        "short_nonzero_velocity_spirograph",
        [90.0, 0.0, 572.95, -458.37],
        {l1: 1.0, l2: 1.5, m1: 3.0, m2: 1.0, g: 9.81},
        [0.0, 0.4, 120],
    ),
    (
        "higher_energy_wide_swing",
        [120.0, -120.0, 120.0, -90.0],
        {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81},
        [0.0, 0.8, 160],
    ),
)


def _position_state(pendulum):
    pendulum.precompute_positions()
    return pendulum.precomputed_positions.T


@pytest.mark.parametrize(("case_name", "initial_conditions", "parameters", "time_vector"), CASES)
def test_simple_lagrangian_and_hamiltonian_agree_under_default_policy(
    case_name,
    initial_conditions,
    parameters,
    time_vector,
):
    lagrangian = DoublePendulumLagrangian(
        parameters,
        initial_conditions,
        time_vector,
        model="simple",
        solver_policy=SIMPLE_DEFAULT_SOLVER_POLICY,
    )
    hamiltonian = DoublePendulumHamiltonian(
        parameters,
        initial_conditions,
        time_vector,
        model="simple",
        solver_policy=SIMPLE_DEFAULT_SOLVER_POLICY,
    )

    theta_diff = np.max(np.abs(lagrangian.sol[:, :2] - hamiltonian.sol[:, :2]))
    position_diff = np.max(np.abs(_position_state(lagrangian) - _position_state(hamiltonian)))

    assert theta_diff < 5e-5, case_name
    assert position_diff < 5e-5, case_name


@pytest.mark.parametrize(("case_name", "initial_conditions", "parameters", "time_vector"), CASES[:2])
def test_simple_reference_policy_is_tighter_diagnostic_fixture(
    case_name,
    initial_conditions,
    parameters,
    time_vector,
):
    lagrangian = DoublePendulumLagrangian(
        parameters,
        initial_conditions,
        time_vector,
        model="simple",
        solver_policy=SIMPLE_REFERENCE_SOLVER_POLICY,
    )
    hamiltonian = DoublePendulumHamiltonian(
        parameters,
        initial_conditions,
        time_vector,
        model="simple",
        solver_policy=SIMPLE_REFERENCE_SOLVER_POLICY,
    )

    theta_diff = np.max(np.abs(lagrangian.sol[:, :2] - hamiltonian.sol[:, :2]))
    position_diff = np.max(np.abs(_position_state(lagrangian) - _position_state(hamiltonian)))

    assert theta_diff < 1e-7, case_name
    assert position_diff < 1e-7, case_name
