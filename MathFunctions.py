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


def euler_lagrange_system(L, q1, q2, model='simple'):
    """
    Computes the Euler-Lagrange equations for a double pendulum system with two generalized coordinates.

    Parameters
    ----------
    q1 : sympy.Function
        The first generalized coordinate as a function of time.
    q2 : sympy.Function
        The second generalized coordinate as a function of time.
    model : str, optional
        The model type of the pendulum system, either 'simple' or 'compound'.

    Returns
    -------
    tuple of sympy.Eq
        A tuple containing two sympy.Eq objects representing the simplified Euler-Lagrange equations
        for the two generalized coordinates.

    Raises
    ------
    ValueError
        If an invalid model type is provided.
    """
    # Derivatives of the generalized coordinates
    q1_dot = sp.diff(q1, t)
    q2_dot = sp.diff(q2, t)

    # Euler-Lagrange equations for q1
    partial_L_partial_q1 = sp.diff(L, q1)
    partial_L_partial_q1_dot = sp.diff(L, q1_dot)
    EL_q1 = sp.diff(partial_L_partial_q1_dot, t) - partial_L_partial_q1

    # Euler-Lagrange equations for q2
    partial_L_partial_q2 = sp.diff(L, q2)
    partial_L_partial_q2_dot = sp.diff(L, q2_dot)
    EL_q2 = sp.diff(partial_L_partial_q2_dot, t) - partial_L_partial_q2

    # Apply specific simplification factors based on the model
    if model == 'simple':
        EL_q1 = EL_q1 / l1
        EL_q2 = EL_q2 / (l2*m2)

    elif model == 'compound':
        EL_q1 = EL_q1 * (12 / l1)
        EL_q2 = EL_q2 * (12 / (M2 * l2))

    else:
        pass # attribute error

    # Simplify the equations
    EL_q1_simplified = sp.simplify(EL_q1)
    EL_q2_simplified = sp.simplify(EL_q2)

    eqn1 = sp.Eq(EL_q1_simplified, 0)
    eqn2 = sp.Eq(EL_q2_simplified, 0)

    return eqn1, eqn2


def isolate_terms(equation):
    """
    Returns the second derivative terms isolated from the given equation.

    Parameters:
        equation (sympy.Eq): The equation from which to isolate the second derivative terms.

    Returns:
        list: A list containing the isolated second derivative terms.
    """
    # Define derivative terms
    theta1ddot = sp.diff(theta1, t, 2)
    theta2ddot = sp.diff(theta2, t, 2)

    terms = []

    try:
        th1 = sp.Eq(theta1ddot, sp.solve(equation, theta1ddot)[0])
        rhs_eq = th1.rhs
        alpha1 = sp.together(rhs_eq).as_numer_denom()[1]
        eq_new = sp.Eq(th1.lhs * alpha1, th1.rhs * alpha1)
        theta1_second = eq_new.lhs
        terms.append(theta1_second)
    except IndexError:
        pass

    try:
        th2 = sp.Eq(theta2ddot, sp.solve(equation, theta2ddot)[0])
        rhs_eq = th2.rhs
        alpha2 = sp.together(rhs_eq).as_numer_denom()[1]
        eq_new = sp.Eq(th2.lhs * alpha2, th2.rhs * alpha2)
        theta2_second = eq_new.lhs
        terms.append(theta2_second)
    except IndexError:
        pass

    return terms


def simplify_system(eq1, eq2, model='simple'):
    """
    Simplifies the system of equations based on the specified model.

    Parameters:
    eq1, eq2 : sympy.Eq
        The Euler-Lagrange equations of the system.
    model : str, optional
        The model type of the pendulum system: 'simple'(Default) or 'compound'

    Returns:
    tuple of sympy.Eq
        The simplified equations for the system.
    """
    if model == 'simple':
        second_derivatives_1 = isolate_terms(eq1)
        lhs_1 = sum(second_derivatives_1)
        rhs_1 = sp.simplify(eq1.lhs - lhs_1)
        eqn1_lhs = sp.simplify(lhs_1 / (l1 * (m1 + m2)))
        eqn1_rhs = sp.simplify(rhs_1 / (l1 * (m1 + m2)))
        eqn1 = sp.Eq(eqn1_lhs, eqn1_rhs)

        second_derivatives_2 = isolate_terms(eq2)
        lhs_2 = sum(second_derivatives_2)
        rhs_2 = sp.simplify(eq2.lhs - lhs_2)
        eqn2_lhs = sp.simplify(lhs_2 / l2)
        eqn2_rhs = sp.simplify(rhs_2 / l2)
        eqn2 = sp.Eq(eqn2_lhs, eqn2_rhs)

        return eqn1, eqn2

    elif model == 'compound':
        second_derivatives_1 = isolate_terms(eq1)
        lhs_1 = sum(second_derivatives_1)
        rhs_1 = sp.simplify(eq1.lhs - lhs_1)
        eqn1 = sp.Eq(lhs_1, rhs_1)

        second_derivatives_2 = isolate_terms(eq2)
        lhs_2 = sum(second_derivatives_2)
        rhs_2 = sp.simplify(eq2.lhs - lhs_2)
        eqn2 = sp.Eq(lhs_2, rhs_2)

        # Simplify eqn1
        eqn1_lhs = sp.simplify(eqn1.lhs / (l1 * (7 * M1 + 3 * M2)))
        eqn1_rhs = sp.simplify(eqn1.rhs / (l1 * (7 * M1 + 3 * M2)))
        eqn1 = sp.Eq(eqn1_lhs, eqn1_rhs)

        # Simplify eqn2
        eqn2_lhs = sp.simplify(eqn2.lhs / (7 * l2))
        eqn2_rhs = sp.simplify(eqn2.rhs / (7 * l2))
        eqn2 = sp.Eq(eqn2_lhs, eqn2_rhs)

        return eqn1, eqn2


def extract_coefficient(equation, derivative_term):
    """
    Extracts the coefficient, including the denominator, of the specified derivative term from the left-hand side of the equation.

    Parameters:
        equation (sympy.Expr): The equation to extract the coefficient from.
        derivative_term (sympy.Expr): The derivative term to extract the coefficient of.

    Returns:
        coeff (sympy.Expr): The coefficient, including the denominator, of the derivative term in the equation.
    """
    lhs_parts = sp.fraction(equation.lhs)
    lhs_coeff_term = lhs_parts[0]
    lhs_denominator_term = lhs_parts[1]
    coeff = lhs_coeff_term.coeff(derivative_term) / lhs_denominator_term

    return coeff


def create_matrix_equation(theta1dd_coeff, theta2dd_coeff, rhs_1, rhs_2):
    """
    This function constructs a matrix A based on symbolic functions alpha1 and alpha2, which represent
    coefficients related to the system's inertia, and solves the equation A*[theta1'', theta2''] = -[f1, f2]
    for the angular accelerations.

    Parameters:
    theta1dd_coeff : symbolic expression
        The coefficient for theta1's second derivative, as derived from the system's dynamics.
    theta2dd_coeff : symbolic expression
        The coefficient for theta2's second derivative, as derived from the system's dynamics.
    rhs_1 : symbolic expression
        The function representing the external force or torque acting on theta1.
    rhs_2 : symbolic expression
        The function representing the external force or torque acting on theta2.

    Returns:
    sympy.Eq
        The symbolic equation representing the system, with the specified coefficients and forces/torques substituted in.
    """
    # Define the symbolic functions for alpha1 and alpha2
    alpha1 = sp.Function('alpha1')(theta1, theta2)
    alpha2 = sp.Function('alpha2')(theta1, theta2)

    # Define the symbolic functions for f1 and f2
    function1 = sp.Function('f1')(theta1, theta2, sp.diff(theta1, t), sp.diff(theta2, t))
    function2 = sp.Function('f2')(theta1, theta2, sp.diff(theta1, t), sp.diff(theta2, t))

    # Left-hand side of the equation
    LHS = sp.Matrix([[sp.diff(theta1, t, 2)], [sp.diff(theta2, t, 2)]])

    # A matrix with symbolic functions alpha1 and alpha2
    A = sp.Matrix([[1, alpha1], [alpha2, 1]])

    # Right-hand side of the equation before substitution
    RHS = sp.Matrix([[function1], [function2]])

    # Invert matrix A and simplify the product with RHS
    NewRHS = sp.simplify(A.inv() * RHS)

    # Create the equation
    EQS = sp.Eq(LHS, -1*NewRHS)

    # Substitute the derived expressions into the equation
    EQS_subst = EQS.subs({
        alpha1: theta1dd_coeff,
        alpha2: theta2dd_coeff,
        function1: rhs_1,
        function2: rhs_2
    })

    RHS_1 = sp.simplify(EQS_subst.rhs[0])
    RHS_2 = sp.simplify(EQS_subst.rhs[1])

    return RHS_1, RHS_2


def first_order_system(RHS_1, RHS_2):
    """
    Convert a second-order differential equation system to a first-order system in matrix form.

    This function takes the expressions for the right-hand side (RHS) of two second-order
    differential equations and constructs a first-order system by introducing new functions
    omega1 and omega2, which represent the first derivatives of the original functions
    theta1 and theta2, respectively.

    Parameters:
    RHS_1 : sympy.Expr
        The right-hand side expression of the differential equation for d^2(theta1)/dt^2.
    RHS_2 : sympy.Expr
        The right-hand side expression of the differential equation for d^2(theta2)/dt^2.

    Returns:
    tuple:
        - sympy.Eq representing the matrix equation of the first-order system,
        - sympy.Expr for the derivative of theta1 with respect to time after substitution,
        - sympy.Expr for the derivative of theta2 with respect to time after substitution,
        - sympy.Expr for the derivative of omega1 with respect to time after substitution,
        - sympy.Expr for the derivative of omega2 with respect to time after substitution.

    The matrix equation (MAT_EQ) equates a column matrix of the left-hand sides of the equations
    to a column matrix of the right-hand sides, facilitating the representation and manipulation
    of the system of equations.

    The function returns this matrix equation along with the isolated expressions for the first
    derivatives of theta1 and theta2 (eqn1, eqn2), and the expressions for the second derivatives
    of omega1 and omega2 (eqn3, eqn4), which correspond to the second derivatives of theta1 and
    theta2, respectively.
    """
    # Define new functions for the first derivatives of theta1 and theta2
    omega1 = sp.Function('omega1')(t)
    omega2 = sp.Function('omega2')(t)

    # Cast as first order system
    eq1 = sp.Eq(omega1, sp.diff(theta1, t))
    eq2 = sp.Eq(omega2, sp.diff(theta2, t))
    eq3 = sp.Eq(sp.diff(omega1, t), RHS_1)
    eq4 = sp.Eq(sp.diff(omega2, t), RHS_2)

    # Assemble the system into matrix form
    LHS_FIRST = sp.Matrix([[eq1.lhs], [eq2.lhs], [eq3.lhs], [eq4.lhs]])
    RHS_FIRST = sp.Matrix([[eq1.rhs], [eq2.rhs], [eq3.rhs], [eq4.rhs]])

    # Create the matrix equation
    MAT_EQ = sp.Eq(LHS_FIRST, RHS_FIRST)

    # Substitute omega for derivative of theta
    derivative_subs = {sp.Derivative(theta1, t): omega1, sp.Derivative(theta2, t): omega2}

    # Isolate rhs of equations
    eqn1 = eq1.rhs.subs(derivative_subs)
    eqn2 = eq2.rhs.subs(derivative_subs)
    eqn3 = eq3.rhs.subs(derivative_subs)
    eqn4 = eq4.rhs.subs(derivative_subs)

    return MAT_EQ, eqn1, eqn2, eqn3, eqn4
