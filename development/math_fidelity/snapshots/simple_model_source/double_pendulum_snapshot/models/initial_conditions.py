import numpy as np

from ..math.functions import M1, M2, l1, l2, m1, m2


USER_INITIAL_CONDITION_NAMES = ["theta1", "theta2", "omega1", "omega2"]
LAGRANGIAN_STATE_VARIABLE_NAMES = ["theta1", "theta2", "omega1", "omega2"]
HAMILTONIAN_STATE_VARIABLE_NAMES = ["theta1", "theta2", "p_theta_1", "p_theta_2"]

LAGRANGIAN_SOLVER_STATE_CONVENTION = "angles_and_angular_velocities"
HAMILTONIAN_SOLVER_STATE_CONVENTION = "angles_and_canonical_momenta"


def user_initial_conditions_to_radians(initial_conditions):
    return np.deg2rad(np.asarray(initial_conditions, dtype=float))


def angular_velocities_to_canonical_momenta(parameters, initial_conditions_radians, model):
    theta_1, theta_2, omega_1, omega_2 = initial_conditions_radians
    delta_cos = np.cos(theta_1 - theta_2)

    if model == "simple":
        length_1 = float(parameters[l1])
        length_2 = float(parameters[l2])
        mass_1 = float(parameters[m1])
        mass_2 = float(parameters[m2])
        inertia_11 = (mass_1 + mass_2) * length_1**2
        inertia_12 = mass_2 * length_1 * length_2 * delta_cos
        inertia_22 = mass_2 * length_2**2
    elif model == "compound":
        length_1 = float(parameters[l1])
        length_2 = float(parameters[l2])
        mass_1 = float(parameters[M1])
        mass_2 = float(parameters[M2])
        inertia_11 = (7.0 / 12.0) * mass_1 * length_1**2 + 0.25 * mass_2 * length_1**2
        inertia_12 = 0.25 * mass_2 * length_1 * length_2 * delta_cos
        inertia_22 = (7.0 / 12.0) * mass_2 * length_2**2
    else:
        raise AttributeError("Invalid model type. Please choose 'simple' or 'compound'.")

    return np.array(
        [
            inertia_11 * omega_1 + inertia_12 * omega_2,
            inertia_12 * omega_1 + inertia_22 * omega_2,
        ]
    )


def hamiltonian_solver_initial_conditions(parameters, initial_conditions_radians, model):
    canonical_momenta = angular_velocities_to_canonical_momenta(
        parameters,
        initial_conditions_radians,
        model,
    )
    return np.array(
        [
            initial_conditions_radians[0],
            initial_conditions_radians[1],
            canonical_momenta[0],
            canonical_momenta[1],
        ]
    )
