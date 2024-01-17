import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint, solve_ivp
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from MathFunctions import *

omega1 = sp.Function('omega1')(t)
omega2 = sp.Function('omega2')(t)


def add_equations(model='simple'):
    # Form Lagrangian
    L = form_lagrangian(model=model)

    # Form EL equations
    eq1, eq2 = euler_lagrange_system(L, theta1, theta2, model=model)

    # Simplify equations
    eqn1, eqn2 = simplify_system(eq1, eq2, model=model)

    # Extract coefficients
    alpha1 = extract_coefficient(eqn1, sp.diff(theta2, t, 2))
    alpha2 = extract_coefficient(eqn2, sp.diff(theta1, t, 2))
    function_1 = eqn1.rhs
    function_2 = eqn2.rhs

    # Form matrix equations
    RHS_1, RHS_2 = create_matrix_equation(alpha1, alpha2, function_1, function_2)

    # Define equations
    MAT_EQ, eqn1, eqn2, eqn3, eqn4 = first_order_system(RHS_1, RHS_2)

    return MAT_EQ, eqn1, eqn2, eqn3, eqn4


class DoublePendulum:
    """
    A class representing a double pendulum system, used for simulating and analyzing its dynamics.

    This class models the complex motion of a double pendulum, where two pendulums are attached end to end.
    It uses symbolic and numerical methods to solve the equations of motion and provides functionalities
    for visualizing the time evolution and phase paths of the system.

        Attributes:
            initial_conditions (numpy.ndarray): The initial conditions of the system.
                Format: [theta1, theta2, omega1, omega2].
            time (numpy.ndarray): Discrete time points at which the system's state is evaluated.
            parameters (dict): Parameters of the pendulum system such as lengths and masses of the rods/bobs
            model (str): The model type used for the pendulum ('simple' or 'compound').

        Methods:
            _compute_and_cache_equations: Computes and caches the symbolic equations for the specified pendulum model.
            _system: Defines the system of differential equations for the ODE solver.
            _solve_ode: Solves the system's differential equations using a specified numerical integrator.
            _calculate_positions: Calculates the (x, y) positions of both pendulum bobs at each time step.
            time_graph: Plots the angular displacement of the pendulums versus time.
            phase_path: Plots the phase path (theta1 vs. theta2) of the double pendulum.
            precompute_positions: Precomputes and stores the positions of both pendulum bobs for each time step.
    """
    # Class variable for caching
    _cache = {}

    # Declare variables & constants
    t = sp.Symbol("t")
    l1, l2, m1, m2, M1, M2, g = sp.symbols('l1 l2 m1 m2 M1 M2 g', real=True, positive=True)

    # Declare functions
    theta1 = sp.Function('theta1')(t)
    theta2 = sp.Function('theta2')(t)
    omega1 = sp.Function('omega1')(t)
    omega2 = sp.Function('omega2')(t)

    @classmethod
    def _compute_and_cache_equations(cls, model):
        if model not in cls._cache:
            cls._cache[model] = add_equations(model)
        return cls._cache[model]

    def __init__(self, parameters, initial_conditions, time_vector,
                 model='simple', integrator=solve_ivp, **integrator_args):
        self.initial_conditions = np.deg2rad(initial_conditions)
        self.time = np.linspace(time_vector[0], time_vector[1], time_vector[2])
        self.parameters = parameters
        self.model = model

        # Get equations for the specified model
        MAT_EQ, eqn1, eqn2, eqn3, eqn4 = self._compute_and_cache_equations(model)

        # Symbolic equation
        self.matrix = MAT_EQ

        # Substitute parameters into the equations
        eq1_subst = eqn1.subs(parameters)
        eq2_subst = eqn2.subs(parameters)
        eq3_subst = eqn3.subs(parameters)
        eq4_subst = eqn4.subs(parameters)

        # Lambdify the equations after substitution
        self.eqn1_func = sp.lambdify((theta1, theta2, omega1, omega2, t), eq1_subst, 'numpy')
        self.eqn2_func = sp.lambdify((theta1, theta2, omega1, omega2, t), eq2_subst, 'numpy')
        self.eqn3_func = sp.lambdify((theta1, theta2, omega1, omega2, t), eq3_subst, 'numpy')
        self.eqn4_func = sp.lambdify((theta1, theta2, omega1, omega2, t), eq4_subst, 'numpy')

        self.sol = self._solve_ode(integrator, **integrator_args)

    def _system(self, y, t):
        th1, th2, w1, w2 = y
        system = [
            self.eqn1_func(th1, th2, w1, w2, t),
            self.eqn2_func(th1, th2, w1, w2, t),
            self.eqn3_func(th1, th2, w1, w2, t),
            self.eqn4_func(th1, th2, w1, w2, t)
        ]
        return system

    def _solve_ode(self, integrator, **integrator_args):
        """
        Solve the system of ODEs using the specified integrator.

        Parameters:
        - integrator: The integrator function to use. Default is scipy's odeint.
        - system: The system function defining the ODEs.
        - **integrator_args: Additional arguments specific to the chosen integrator.
        """
        if integrator == odeint:
            sol = odeint(self._system, self.initial_conditions, self.time, **integrator_args)
        elif integrator == solve_ivp:
            t_span = (self.time[0], self.time[-1])
            sol = solve_ivp(lambda t, y: self._system(y, t), t_span, self.initial_conditions,
                            t_eval=self.time, **integrator_args)
            sol = sol.y.T  # Transpose
        else:
            raise ValueError("Unsupported integrator")
        return sol

    def _calculate_positions(self):
        # Unpack solution for theta1 and theta2
        theta_1, theta_2 = self.sol[:, 0], self.sol[:, 1]

        # Evaluate lengths of the pendulum arms using the provided parameter values
        l_1 = float(self.parameters[l1])
        l_2 = float(self.parameters[l2])

        # Calculate the (x, y) positions of the first pendulum bob
        x_1 = l_1 * np.sin(theta_1)
        y_1 = -l_1 * np.cos(theta_1)

        # Calculate the (x, y) positions of the second pendulum bob
        x_2 = x_1 + l_2 * np.sin(theta_2)
        y_2 = y_1 - l_2 * np.cos(theta_2)

        return x_1, y_1, x_2, y_2

    def time_graph(self):
        plt.style.use('default')  # Reset to the default style
        fig, ax = plt.subplots()
        # Plot settings to match the animation's appearance
        ax.plot(self.time, np.rad2deg(self.sol[:, 0]), color='darkorange', label="θ1", linewidth=2)
        ax.plot(self.time, np.rad2deg(self.sol[:, 1]), color='green', label="θ2", linewidth=2)

        # Set the labels, title, and grid
        ax.set_xlabel('Time / seconds')
        ax.set_ylabel('Angular displacement / degrees')
        ax.set_title('Time Graph', fontname='Courier New', fontsize=16)

        ax.grid(True, color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
        plt.legend(loc='best')
        return fig

    def phase_path(self):
        plt.style.use('default')  # Reset to the default style
        fig, ax = plt.subplots()

        # Plot settings to match the animation's appearance
        ax.plot(np.rad2deg(self.sol[:, 0]), np.rad2deg(self.sol[:, 1]), color='navy', label="Phase Path",
                linewidth=2)

        # Set the labels, title, and grid
        ax.set_xlabel('θ1 / degrees')
        ax.set_ylabel('θ2 / degrees')
        ax.set_title('Phase Path', fontname='Courier New', fontsize=16)

        ax.grid(True, color='gray', linestyle='-', linewidth=0.5, alpha=0.7)
        plt.legend(loc='best')
        return fig

    def precompute_positions(self):
        """
        Precomputes and stores the positions of both pendulum bobs for each time step.

        This method calculates the (x, y) positions of the first and second pendulum bobs at each time step,
        using the provided initial conditions and system parameters. The positions are stored in a NumPy array
        as an instance attribute, which can be used for plotting and animation purposes, reducing the
        computational load at rendering time.
        """
        self.precomputed_positions = np.array(self._calculate_positions())

    def animate_pendulum(self, fig_width=700, fig_height=700, trace=False, appearance='light'):
        """
        Generates an animation for the double pendulum using precomputed positions.

        Parameters:
            trace (bool): If True, show the trace of the pendulum.
            appearance (str): 'dark' for dark mode (default), 'light' for light mode.

        Raises:
            AttributeError: If `precompute_positions` has not been called before animation.

        Returns:
            A Plotly figure object containing the animation.
        """
        # Check if precomputed_positions has been calculated
        if not hasattr(self, 'precomputed_positions') or self.precomputed_positions is None:
            raise AttributeError("Precomputed positions must be calculated before animating. "
                                 "Please call 'precompute_positions' method first.")

        x_1, y_1, x_2, y_2 = self.precomputed_positions

        # Check appearance and set colors
        if appearance == 'dark':
            pendulum_color = 'rgba(255, 255, 255, 0.9)'  # White with slight transparency for visibility
            trace_color_theta1 = 'rgba(255, 165, 0, 0.6)'  # Soft orange with transparency for trace of P1
            trace_color_theta2 = 'rgba(0, 255, 0, 0.6)'  # Soft green with transparency for trace of P2
            background_color = 'rgb(17, 17, 17)'  # Very dark (almost black) for the plot background
            text_color = 'rgba(255, 255, 255, 0.9)'  # White text color for better visibility in dark mode
            grid_color = 'rgba(255, 255, 255, 0.3)'  # Light grey for grid lines

        elif appearance == 'light':
            pendulum_color = 'navy'  # Dark blue for better visibility against light background
            trace_color_theta1 = 'darkorange'  # Dark orange for a vivid contrast for trace of P1
            trace_color_theta2 = 'green'  # Dark green for trace of P2
            background_color = 'rgb(255, 255, 255)'  # White for the plot background
            text_color = 'rgb(0, 0, 0)'  # Black text color for better visibility in light mode
            grid_color = 'rgba(0, 0, 0, 0.1)'  # Light black (gray) for grid lines, with transparency for subtlety

        else:
            print("Invalid appearance setting. Please choose 'dark' or 'light'.")
            return None  # Exit the function if invalid appearance

        # Create figure with initial trace
        fig = go.Figure(
            data=[go.Scatter(
                x=[0, x_1[0], x_2[0]],
                y=[0, y_1[0], y_2[0]],
                mode='lines+markers',
                name='Pendulum',
                line=dict(width=2, color=pendulum_color),
                marker=dict(size=10, color=pendulum_color)
            )]
        )

        # If trace is True, add path traces
        if trace:
            path_1 = go.Scatter(
                x=x_1, y=y_1,
                mode='lines',
                name='Path of P1',
                line=dict(width=1, color=trace_color_theta1),
            )
            path_2 = go.Scatter(
                x=x_2, y=y_2,
                mode='lines',
                name='Path of P2',
                line=dict(width=1, color=trace_color_theta2),
            )
            fig.add_trace(path_1)
            fig.add_trace(path_2)

        # Calculate the max extent based on the precomputed positions
        max_extent = max(
            np.max(np.abs(x_1)),
            np.max(np.abs(y_1)),
            np.max(np.abs(x_2)),
            np.max(np.abs(y_2))
        )

        # Add padding to the max extent
        padding = 0.1 * max_extent  # 10% padding
        axis_range_with_padding = [-max_extent - padding, max_extent + padding]

        # Add frames to the animation
        step = 10
        frames = [go.Frame(data=[go.Scatter(x=[0, x_1[k], x_2[k]], y=[0, y_1[k], y_2[k]],
                                            mode='lines+markers',
                                            line=dict(width=2))])
                  for k in range(0, len(x_1), step)]  # Use a step to reduce the number of frames
        fig.frames = frames

        # Update figure layout to create a square plot with padded axis range
        fig.update_layout(
            plot_bgcolor=background_color,
            paper_bgcolor=background_color,
            xaxis=dict(
                showgrid=True, gridwidth=1, gridcolor=grid_color,
                range=axis_range_with_padding,
                autorange=False,
                zeroline=False,
                tickcolor=text_color,
                tickfont=dict(size=12, color=text_color),
            ),
            yaxis=dict(
                showgrid=True, gridwidth=1, gridcolor=grid_color,
                range=axis_range_with_padding,
                autorange=False,
                zeroline=False,
                scaleanchor='x',
                scaleratio=1,
                tickcolor=text_color,
                tickfont=dict(size=12, color=text_color),
            ),
            autosize=False,
            width=fig_width,
            height=fig_height,

            updatemenus=[{
                'type': 'buttons',
                'buttons': [
                    dict(
                        label="Play",
                        method="animate",
                        args=[None, {"frame": {"duration": 33, "redraw": True}, "fromcurrent": True,
                                     "mode": "immediate",
                                     'label': 'Play',
                                     'font': {'size': 14, 'color': 'black'},
                                     'bgcolor': 'lightblue'
                        }],
                    )
                ],
                'direction': "left",
                'pad': {"r": 10, "t": 10},  # Adjust padding if needed
                'showactive': False,
                'type': 'buttons',
                'x': 0.05,  # Position for x
                'y': 0.95,  # Position for y,(the top of the figure)
                'xanchor': "left",
                'yanchor': "top"
            }],
        margin=dict(l=20, r=20, t=20, b=20),
        )

        return fig