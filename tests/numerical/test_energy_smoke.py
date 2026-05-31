import numpy as np
import pytest

from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_DEFAULT_SOLVER_POLICY,
    SIMPLE_REFERENCE_SOLVER_POLICY,
    DoublePendulumHamiltonian,
    DoublePendulumLagrangian,
)


SIMPLE_PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
INITIAL_CONDITIONS_DEGREES = [0.0, 60.0, 0.0, 0.0]
TIME_VECTOR = [0.0, 1.0, 200]


def _omega_from_simple_hamiltonian_state(parameters, state):
    theta_1 = state[:, 0]
    theta_2 = state[:, 1]
    p_1 = state[:, 2]
    p_2 = state[:, 3]
    length_1 = float(parameters[l1])
    length_2 = float(parameters[l2])
    mass_1 = float(parameters[m1])
    mass_2 = float(parameters[m2])

    omega = np.empty((state.shape[0], 2), dtype=float)
    for index, delta_cos in enumerate(np.cos(theta_1 - theta_2)):
        mass_matrix = np.array(
            [
                [(mass_1 + mass_2) * length_1**2, mass_2 * length_1 * length_2 * delta_cos],
                [mass_2 * length_1 * length_2 * delta_cos, mass_2 * length_2**2],
            ],
            dtype=float,
        )
        omega[index] = np.linalg.solve(mass_matrix, [p_1[index], p_2[index]])
    return omega


def _simple_energy(parameters, state, formulation):
    theta_1 = state[:, 0]
    theta_2 = state[:, 1]
    if formulation == "lagrangian":
        omega = state[:, 2:4]
    else:
        omega = _omega_from_simple_hamiltonian_state(parameters, state)

    omega_1 = omega[:, 0]
    omega_2 = omega[:, 1]
    length_1 = float(parameters[l1])
    length_2 = float(parameters[l2])
    mass_1 = float(parameters[m1])
    mass_2 = float(parameters[m2])
    gravity = float(parameters[g])

    kinetic = (
        0.5 * (mass_1 + mass_2) * length_1**2 * omega_1**2
        + 0.5 * mass_2 * length_2**2 * omega_2**2
        + mass_2 * length_1 * length_2 * omega_1 * omega_2 * np.cos(theta_1 - theta_2)
    )
    potential = -((mass_1 + mass_2) * gravity * length_1 * np.cos(theta_1) + mass_2 * gravity * length_2 * np.cos(theta_2))
    return kinetic + potential


def _max_energy_drift(pendulum, formulation):
    energy = _simple_energy(pendulum.parameters, pendulum.sol, formulation)
    return float(np.max(np.abs(energy - energy[0])))


@pytest.mark.parametrize(
    ("model_class", "formulation"),
    [
        (DoublePendulumLagrangian, "lagrangian"),
        (DoublePendulumHamiltonian, "hamiltonian"),
    ],
)
def test_simple_default_policy_energy_drift_stays_within_smoke_threshold(model_class, formulation):
    pendulum = model_class(
        SIMPLE_PARAMETERS,
        INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="simple",
        solver_policy=SIMPLE_DEFAULT_SOLVER_POLICY,
    )

    assert _max_energy_drift(pendulum, formulation) < 1e-3


@pytest.mark.parametrize(
    ("model_class", "formulation"),
    [
        (DoublePendulumLagrangian, "lagrangian"),
        (DoublePendulumHamiltonian, "hamiltonian"),
    ],
)
def test_reference_policy_energy_drift_is_no_worse_than_default(model_class, formulation):
    default = model_class(
        SIMPLE_PARAMETERS,
        INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="simple",
        solver_policy=SIMPLE_DEFAULT_SOLVER_POLICY,
    )
    reference = model_class(
        SIMPLE_PARAMETERS,
        INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="simple",
        solver_policy=SIMPLE_REFERENCE_SOLVER_POLICY,
    )

    assert _max_energy_drift(reference, formulation) <= _max_energy_drift(default, formulation) * 1.05 + 1e-10


def test_hamiltonian_energy_reconstructs_omega_instead_of_treating_momenta_as_velocity():
    pendulum = DoublePendulumHamiltonian(
        SIMPLE_PARAMETERS,
        [45.0, -30.0, 10.0, -5.0],
        [0.0, 0.2, 40],
        model="simple",
        solver_policy=SIMPLE_DEFAULT_SOLVER_POLICY,
    )

    reconstructed = _omega_from_simple_hamiltonian_state(SIMPLE_PARAMETERS, pendulum.sol[:1])[0]
    direct_momentum_tail = pendulum.sol[0, 2:4]

    np.testing.assert_allclose(reconstructed, np.deg2rad([10.0, -5.0]), rtol=0, atol=1e-12)
    assert not np.allclose(reconstructed, direct_momentum_tail, rtol=0, atol=1e-12)
