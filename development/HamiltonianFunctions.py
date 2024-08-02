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


def derive_canonical_momenta(L, theta1, theta2, t):
    """
    Derive the canonical momenta for the double pendulum system.

    Parameters:
        L (sympy.Expr): The Lagrangian of the system.
        theta1 (sympy.Function): The first generalized coordinate as a function of time.
        theta2 (sympy.Function): The second generalized coordinate as a function of time.
        t (sympy.Symbol): The time variable.

    Returns:
        tuple of sympy.Expr: The canonical momenta (p_theta1, p_theta2).
    """
    # Define the generalised velocities
    omega1 = sp.diff(theta1, t)
    omega2 = sp.diff(theta2, t)

    # Compute the canonical momenta
    p_theta1 = sp.diff(L, omega1)
    p_theta2 = sp.diff(L, omega2)

    return p_theta1, p_theta2


def compute_generalized_velocities(theta1, theta2, l1, l2, m1, m2):
    """
    Compute the generalized velocities in terms of the canonical momenta.

    Parameters:
        theta1 (sympy.Function): The first generalized coordinate as a function of time.
        theta2 (sympy.Function): The second generalized coordinate as a function of time.
        l1, l2 (sympy.Symbol): Lengths of the pendulum arms.
        m1, m2 (sympy.Symbol): Masses of the pendulum bobs.

    Returns:
        tuple of sympy.Expr: The generalized velocities (omega1_solved, omega2_solved).
    """
    # Define the coefficient matrix B
    B = sp.Matrix([
        [(m1 + m2) * l1**2, m2 * l1 * l2 * sp.cos(theta1 - theta2)],
        [m2 * l1 * l2 * sp.cos(theta1 - theta2), m2 * l2**2]
    ])

    # Invert the matrix B
    B_inv = B.inv()

    # Define canonical momenta as a matrix
    p = sp.Matrix([p_theta_1, p_theta_2])

    # Solve for the generalized velocities
    omega = B_inv * p

    omega1_solved = omega[0]
    omega2_solved = omega[1]

    # Simplify omega_sol's with substitution for trigonometric identity
    omega1_sol = sp.simplify(omega1_solved.subs(sp.cos(theta1 - theta2) ** 2, 1 - sp.sin(theta1 - theta2) ** 2))
    omega2_sol_simplified = sp.simplify(omega2_solved.subs(sp.cos(theta1 - theta2) ** 2, 1 - sp.sin(theta1 - theta2) ** 2))

    # Explicitly substitute m2 - m2*cos^2(theta1 - theta2) with m2*sin^2(theta1 - theta2)
    omega2_sol_targeted = omega2_sol_simplified.subs(m2 - m2 * sp.cos(theta1 - theta2) ** 2,
                                                     m2 * sp.sin(theta1 - theta2) ** 2)
    omega2_sol = sp.simplify(omega2_sol_targeted)

    return omega1_sol, omega2_sol, B


def compute_hamiltonian(B, theta1, theta2, l1, l2, m1, m2, g):
    """
    Compute the Hamiltonian for the double pendulum system.

    Parameters:
        B (sympy.Matrix): The coefficient matrix B.
        theta1 (sympy.Function): The first generalized coordinate as a function of time.
        theta2 (sympy.Function): The second generalized coordinate as a function of time.
        l1, l2 (sympy.Symbol): Lengths of the pendulum arms.
        m1, m2 (sympy.Symbol): Masses of the pendulum bobs.
        g (sympy.Symbol): Gravitational acceleration.

    Returns:
        sympy.Expr: The Hamiltonian.
    """
    # Invert the matrix B
    B_inv = B.inv()

    # Define canonical momenta as a matrix
    p = sp.Matrix([p_theta_1, p_theta_2])

    # Compute the kinetic energy T in terms of canonical momenta
    T = sp.Rational(1, 2) * p.T * B_inv * p

    # Simplify T, apply trig identity
    T_target = T[0].subs(sp.cos(theta1 - theta2) ** 2, 1 - sp.sin(theta1 - theta2) ** 2)
    T_simp = sp.simplify(T_target)

    # Define the potential energy V
    V = -(m1 + m2) * g * l1 * sp.cos(theta1) - m2 * g * l2 * sp.cos(theta2)

    # Form the Hamiltonian
    H = T_simp + V

    return H


def compute_hamiltons_equations(H, theta1, theta2):
    """
    Compute Hamilton's equations of motion for the double pendulum system.

    Parameters:
        H (sympy.Expr): The Hamiltonian of the system.
        theta1 (sympy.Function): The first generalized coordinate as a function of time.
        theta2 (sympy.Function): The second generalized coordinate as a function of time.

    Returns:
        tuple of sympy.Eq: The Hamilton's equations (Heq1, Heq2, Heq3, Heq4).
    """
    # Partially differentiate H with respect to p_theta_1 and p_theta_2 (The symbolic conjugate momenta)
    H_theta1 = sp.diff(H, p_theta_1)
    H_theta1 = sp.simplify(H_theta1)

    H_theta2 = sp.diff(H, p_theta_2)
    H_theta2 = sp.simplify(H_theta2)

    H_p_theta1 = -sp.diff(H, theta1)
    H_p_theta1 = sp.simplify(H_p_theta1)

    H_p_theta2 = -sp.diff(H, theta2)
    H_p_theta2 = sp.simplify(H_p_theta2)

    # Declare all as SymPy equations
    Heq1 = sp.Eq(omega1, H_theta1)
    Heq2 = sp.Eq(omega2, H_theta2)
    Heq3 = sp.Eq(sp.diff(p_theta_1, t), H_p_theta1)
    Heq4 = sp.Eq(sp.diff(p_theta_2, t), H_p_theta2)

    return Heq1, Heq2, Heq3, Heq4


def hamiltonian_first_order_system(p_theta1, p_theta2, Heq1, Heq2, Heq3, Heq4):
    """
    Convert a second-order Hamiltonian system to a first-order system in matrix form.

    Parameters:
        Heq1 (sympy.Expr): The partial derivative of H with respect to p_theta1.
        Heq2 (sympy.Expr): The partial derivative of H with respect to p_theta2.
        Heq3 (sympy.Expr): The negative partial derivative of H with respect to theta1.
        Heq4 (sympy.Expr): The negative partial derivative of H with respect to theta2.

    Returns:
        tuple:
            - sympy.Eq representing the matrix equation of the first-order system,
            - sympy.Expr for the derivative of theta1 with respect to time after substitution,
            - sympy.Expr for the derivative of theta2 with respect to time after substitution,
            - sympy.Expr for the derivative of omega1 with respect to time after substitution,
            - sympy.Expr for the derivative of omega2 with respect to time after substitution.
    """
    # Substitute the canonical momenta
    subs_dict = {p_theta_1: p_theta1, p_theta_2: p_theta2}

    # Cast as first order system
    eq1 = Heq1.rhs.subs(subs_dict)
    eq2 = Heq2.rhs.subs(subs_dict)
    eq3 = Heq3.rhs.subs(subs_dict)
    eq4 = Heq4.rhs.subs(subs_dict)

    # Simplify
    eqn1 = sp.simplify(eq1)
    eqn2 = sp.simplify(eq2)
    eqn3 = sp.simplify(eq3)
    eqn4 = sp.simplify(eq4)

    # Assemble the system into matrix form
    LHS_FIRST = sp.Matrix([[Heq1.lhs], [Heq2.lhs], [Heq3.lhs], [Heq4.lhs]])
    RHS_FIRST = sp.Matrix([[eqn1], [eqn2], [eqn3], [eqn4]])

    # Create the matrix equation
    MAT_EQ = sp.Eq(LHS_FIRST, RHS_FIRST)

    return MAT_EQ, eqn1, eqn2, eqn3, eqn4

