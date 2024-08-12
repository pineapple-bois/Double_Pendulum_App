from dash import html
import plotly.tools as tls
import matplotlib.pyplot as plt

# Constants
MAX_TIME = 120
MAX_LENGTH = 10      # meters
MIN_LENGTH = 0.1     # meters
MAX_MASS = 1000      # kilograms
MIN_MASS = 0.1       # kilograms
MAX_GRAVITY = 23.15  # m/s^2, g on Jupiter
MIN_GRAVITY = 0.696  # m/s^2, g on Pluto
MAX_ANGULAR_VELOCITY = 1000


# Error checking of parameters and initial conditions
def validate_inputs(initial_conditions_list, time_start, time_end, model_type,
                    param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g):
    error_list = []

    # Time validation
    time_errors = []
    if time_start is None:
        time_errors.append("Please provide a value for start time.")
    if time_end is None:
        time_errors.append("Please provide a value for end time.")

    if time_start is not None and time_end is not None:
        if time_start >= time_end or time_end <= 0:
            time_errors.append("End time must be greater than start time.")
        if time_start < 0:
            time_errors.append("Time interval must begin at zero.")
        if time_end - time_start > MAX_TIME:
            time_errors.append(f"Maximum simulation time is {MAX_TIME} seconds.")

    if time_errors:
        error_list.append("Time values:")
        error_list.append(html.Br())
        error_list.extend([html.Div(error) for error in time_errors])
        error_list.append(html.Br())
        error_list.append(html.Br())

    # Parameter validation
    param_errors = []
    param_limits = {
        'l1 (length of rod 1)': (MIN_LENGTH, MAX_LENGTH),
        'l2 (length of rod 2)': (MIN_LENGTH, MAX_LENGTH),
        'm1 (mass of bob 1)': (MIN_MASS, MAX_MASS),
        'm2 (mass of bob 2)': (MIN_MASS, MAX_MASS),
        'M1 (mass of rod 1)': (MIN_MASS, MAX_MASS),
        'M2 (mass of rod 2)': (MIN_MASS, MAX_MASS),
        'g (acceleration due to gravity)': (MIN_GRAVITY, MAX_GRAVITY),
    }

    param_values = {
        'l1 (length of rod 1)': param_l1,
        'l2 (length of rod 2)': param_l2,
        'g (acceleration due to gravity)': param_g,
        'm1 (mass of bob 1)' if model_type == 'simple' else 'M1 (mass of rod 1)':
            param_m1 if model_type == 'simple' else param_M1,
        'm2 (mass of bob 2)' if model_type == 'simple' else 'M2 (mass of rod 2)':
            param_m2 if model_type == 'simple' else param_M2,
    }

    for param_name, param_value in param_values.items():
        if param_name in param_limits:
            min_val, max_val = param_limits[param_name]
            if param_value is None:
                param_errors.append(f"{param_name} requires a numerical value.")
            elif not isinstance(param_value, (int, float)):
                param_errors.append(f"{param_name} must be a number.")
            elif not (min_val <= param_value <= max_val):
                param_errors.append(f"{param_name} must be between {min_val} and {max_val}.")
                if param_name == 'g (acceleration due to gravity)':
                    param_errors.append(
                        f"Note: Pluto's gravity = {MIN_GRAVITY} m/s^2, Jupiter's gravity = {MAX_GRAVITY} m/s^2")

    if param_errors:
        error_list.append("Parameter values:")
        error_list.append(html.Br())
        error_list.extend([html.Div(error) for error in param_errors])
        error_list.append(html.Br())
        error_list.append(html.Br())

    # Initial condition validation for each pendulum
    init_cond_errors = []
    condition_names = ['θ1', 'θ2', 'ω1', 'ω2']
    multiple_initial_conditions = len(initial_conditions_list) > 1

    for i, conditions in enumerate(initial_conditions_list, start=1):
        pendulum_label = f"Pendulum {i}: " if multiple_initial_conditions else ""
        for name, value in zip(condition_names, conditions):
            if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
                init_cond_errors.append(f"{pendulum_label}{name} requires a numerical value.")
            else:
                if name in ['θ1', 'θ2'] and (value < -180 or value > 180):
                    init_cond_errors.append(f"{pendulum_label}{name} must be between -180 and 180 degrees.")
                elif name in ['ω1', 'ω2']:
                    if abs(value) > MAX_ANGULAR_VELOCITY:
                        init_cond_errors.append(
                            f"{pendulum_label}{name} must be within ±{MAX_ANGULAR_VELOCITY} deg/s.")

    if init_cond_errors:
        error_list.append("Initial conditions:")
        error_list.append(html.Br())
        error_list.extend([html.Div(error) for error in init_cond_errors])
        error_list.append(html.Br())

    # Return the error message or None if there are no errors
    return html.Div(error_list) if error_list else None


# Helper function to generate animation and phase figures for a pendulum
def generate_pendulum_figures(pendulum, fig_width, fig_height):
    pendulum.precompute_positions()
    animation = pendulum.animate_pendulum(trace=True, fig_width=fig_width, fig_height=fig_height, static=True)
    matplotlib_phase_fig = pendulum.phase_path()
    phase_fig = tls.mpl_to_plotly(matplotlib_phase_fig)
    phase_fig.update_layout(
        autosize=True,
        margin=dict(l=20, r=20, t=20, b=20),
        width=fig_width,
        height=fig_height
    )
    plt.close(matplotlib_phase_fig)
    return animation, phase_fig


# Helper function to set display styles
def set_display_styles(pendulum_count):
    if pendulum_count == 'two_pendulums':
        return [{'display': 'block'}, {'display': 'block'}, {'display': 'none'}]
    elif pendulum_count == 'three_pendulums':
        return [{'display': 'block'}, {'display': 'block'}, {'display': 'block'}]
    else:
        return [{'display': 'none'}, {'display': 'none'}, {'display': 'none'}]
