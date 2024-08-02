import sympy as sp

# Declare variables & constants
t = sp.Symbol("t")
l1, l2, m1, m2, M1, M2, g = sp.symbols('l1 l2 m1 m2 M1 M2 g', real=True, positive=True)

theta1 = sp.Function('theta1')(t)
theta2 = sp.Function('theta2')(t)
theta1_dot = sp.Function('theta1_dot')(t)
theta2_dot = sp.Function('theta2_dot')(t)
omega1 = sp.diff(theta1, t)
omega2 = sp.diff(theta2, t)
p_theta_1 = sp.Function('p_theta_1')(t)
p_theta_2 = sp.Function('p_theta_2')(t)


def trans_kinetic_energy(m, dx, dy, dz):
    T = sp.Rational(1,2)*m*(dx**2 + dy**2 + dz**2)
    return T


def potential_energy(m, g, h):
    V = m*g*h
    return V


def moment_of_inertia(M, L):
    # The moment of inertia for a uniform thin rod
    I_cm = sp.Rational(1, 12) * M * L ** 2
    # Applying parallel axis theorem
    I_end = I_cm + M * (L / 2) ** 2
    return I_end


def rotational_kinetic_energy(M, L, omega):
    I = moment_of_inertia(M, L)
    T_rot = sp.Rational(1, 2) * I * omega**2
    return T_rot


def form_lagrangian(model='simple'):
    """
    The function computes the Lagrangian by determining the translational and rotational kinetic energies,
    as well as the potential energy, of two rods in a pendulum system.
    It supports 'simple' and 'compound' models

    Returns the symbolic expression for the Lagrangian of the system.
    """
    if model == 'simple':
        # coordinates of P1
        x1 = l1 * sp.sin(theta1)
        y1 = -l1 * sp.cos(theta1)

        # coordinates of P2
        x2 = x1 + l2 * sp.sin(theta2)
        y2 = y1 - l2 * sp.cos(theta2)

    elif model == 'compound':
        # Calculate positions of the center of mass
        # Rod 1
        x1 = l1 / 2 * sp.sin(theta1)
        y1 = -l1 / 2 * sp.cos(theta1)
        # Rod 2
        x2 = x1 + l2 / 2 * sp.sin(theta2)
        y2 = y1 - l2 / 2 * sp.cos(theta2)

    # Handling incorrect model types
    else:
        raise AttributeError("Invalid model type. Please choose 'simple' or 'compound'.")

    # Calculate velocities
    xdot1 = sp.diff(x1, t)
    ydot1 = sp.diff(y1, t)
    xdot2 = sp.diff(x2, t)
    ydot2 = sp.diff(y2, t)

    # Define angular velocity
    omega_1 = sp.diff(theta1, t)
    omega_2 = sp.diff(theta2, t)

    if model == 'simple':
        T1 = trans_kinetic_energy(m1, xdot1, ydot1, 0)
        V1 = potential_energy(m1, g, y1)

        T2 = trans_kinetic_energy(m2, xdot2, ydot2, 0)
        V2 = potential_energy(m2, g, y2)

        T = sp.trigsimp(T1 + T2)
        V = sp.simplify(V1 + V2)
        L = T - V

    elif model == 'compound':
        T1_trans = trans_kinetic_energy(M1, xdot1, ydot1, 0)
        V1 = potential_energy(M1, g, y1)
        T1_rot = rotational_kinetic_energy(M1, l1, omega_1)

        T2_trans = trans_kinetic_energy(M2, xdot2, ydot2, 0)
        V2 = potential_energy(M2, g, y2)
        T2_rot = rotational_kinetic_energy(M2, l2, omega_2)

        # Form the Lagrangian
        T = sp.trigsimp(T1_trans + T1_rot + T2_trans + T2_rot)
        V = sp.simplify(V1 + V2)
        L = T - V
    return L


def derive_canonical_momenta(L):
    """
    Derive the canonical momenta for the double pendulum system.

    Parameters:
        L (sympy.Expr): The Lagrangian of the system.

    Returns:
        tuple of sympy.Expr: The canonical momenta (p_theta1, p_theta2).
    """
    p_theta1 = sp.diff(L, omega1)
    p_theta2 = sp.diff(L, omega2)
    return p_theta1, p_theta2


def express_generalized_velocities(p_theta1, p_theta2):
    B = sp.Matrix([
        [(m1 + m2) * l1**2, m2 * l1 * l2 * sp.cos(theta1 - theta2)],
        [m2 * l1 * l2 * sp.cos(theta1 - theta2), m2 * l2**2]
    ])
    B_inv = B.inv()
    p = sp.Matrix([p_theta1, p_theta2])
    omega = B_inv * p
    omega1_solved = omega[0]
    omega2_solved = omega[1]
    return omega1_solved, omega2_solved


def compute_hamiltonian(omega1_solved, omega2_solved):
    T = sp.Rational(1, 2) * (p_theta_1 * omega1_solved + p_theta_2 * omega2_solved)
    V = -(m1 + m2) * g * l1 * sp.cos(theta1) - m2 * g * l2 * sp.cos(theta2)
    H = T + V
    return H


def derive_hamiltons_equations(H):
    H_theta1 = sp.diff(H, p_theta_1)
    H_theta2 = sp.diff(H, p_theta_2)
    H_p_theta1 = -sp.diff(H, theta1)
    H_p_theta2 = -sp.diff(H, theta2)
    Heq1 = sp.Eq(sp.diff(theta1, t), H_theta1)
    Heq2 = sp.Eq(sp.diff(theta2, t), H_theta2)
    Heq3 = sp.Eq(sp.diff(p_theta_1, t), H_p_theta1)
    Heq4 = sp.Eq(sp.diff(p_theta_2, t), H_p_theta2)
    return Heq1, Heq2, Heq3, Heq4


def first_order_system(Heq1, Heq2, Heq3, Heq4):
    eq1 = Heq1.rhs
    eq2 = Heq2.rhs
    eq3 = Heq3.rhs
    eq4 = Heq4.rhs
    LHS_FIRST = sp.Matrix([
        [sp.diff(theta1, t)],
        [sp.diff(theta2, t)],
        [sp.diff(p_theta_1, t)],
        [sp.diff(p_theta_2, t)]
    ])
    RHS_FIRST = sp.Matrix([
        [eq1],
        [eq2],
        [eq3],
        [eq4]
    ])
    MAT_EQ = sp.Eq(LHS_FIRST, RHS_FIRST)
    return MAT_EQ
