import sympy as sp

from MathFunctions import (
    compute_hamiltonian,
    form_lagrangian,
    g,
    l1,
    l2,
    m1,
    m2,
    p_theta_1,
    p_theta_2,
    t,
    theta1,
    theta2,
)


def test_simple_lagrangian_matches_reference_kinetic_minus_potential_form():
    # Cross-checked against development/math_reference/DerivationLagrangian.ipynb.
    # This is intentionally a symbolic smoke test, not a full derivation audit;
    # compound-model fidelity remains a documented gap for later phases.
    theta1_dot = sp.diff(theta1, t)
    theta2_dot = sp.diff(theta2, t)
    expected_kinetic = sp.Rational(1, 2) * (
        (m1 + m2) * l1**2 * theta1_dot**2
        + m2 * l2**2 * theta2_dot**2
        + 2 * m2 * l1 * l2 * sp.cos(theta1 - theta2) * theta1_dot * theta2_dot
    )
    expected_potential = -((m1 + m2) * g * l1 * sp.cos(theta1) + m2 * g * l2 * sp.cos(theta2))
    expected_lagrangian = expected_kinetic - expected_potential

    assert sp.simplify(form_lagrangian("simple") - expected_lagrangian) == 0


def test_simple_hamiltonian_uses_expected_mass_matrix_and_potential_energy():
    # Cross-checked against development/math_reference/DevelopmentHamiltonian.ipynb
    # and development/math_reference/MathFunctions.py. Energy conservation and
    # trajectory regression remain known Phase 2 gaps. The Hamiltonian runtime
    # state/input convention also needs a later audit because the equations use
    # canonical momenta while the current UI is velocity-oriented.
    delta = theta1 - theta2
    denominator = l1**2 * l2**2 * m2 * (m1 + m2 * sp.sin(delta) ** 2)
    expected_kinetic = (
        m2 * l2**2 * p_theta_1**2
        - 2 * m2 * l1 * l2 * sp.cos(delta) * p_theta_1 * p_theta_2
        + (m1 + m2) * l1**2 * p_theta_2**2
    ) / (2 * denominator)
    expected_potential = -((m1 + m2) * g * l1 * sp.cos(theta1) + m2 * g * l2 * sp.cos(theta2))
    expected_hamiltonian = expected_kinetic + expected_potential

    assert sp.simplify(compute_hamiltonian("simple") - expected_hamiltonian) == 0
