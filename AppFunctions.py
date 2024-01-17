from dash import html
import plotly.tools as tls
import matplotlib.pyplot as plt

# Define a maximum time allowed for the simulation (2 minutes)
MAX_TIME = 120

# Define max parameter values
MAX_LENGTH = 10      # meters
MIN_LENGTH = 0.1     # meters
MAX_MASS = 1000      # kilograms
MIN_MASS = 0.1       # kilograms
MAX_GRAVITY = 24.79  # m/s^2, g on Jupiter (2.528 * g_earth)
MIN_GRAVITY = 1.623  # m/s^2, g on the Moon (0.1654 * g_earth)

# Max initial conditions (theta_i is hardcoded to be \in [-360, 360]
MAX_ANGULAR_VELOCITY = 1000


# Error checking of parameters and initial conditions
def validate_inputs(initial_conditions_list, time_start, time_end, model_type,
                    param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g):
    error_list = []

    # Check if time values are None
    if time_start is None:
        error_list.append("Please provide a value for start time.")
        error_list.append(html.Br())
    if time_end is None:
        error_list.append("Please provide a value for end time.")
        error_list.append(html.Br())

    # Only perform further checks if both times are not None
    if time_start is not None and time_end is not None:
        if time_start >= time_end or time_end <= 0:
            error_list.append("End time must be greater than start time.")
            error_list.append(html.Br())

        if time_start < 0:
            error_list.append("Time interval must begin at zero.")
            error_list.append(html.Br())

        if time_end - time_start > MAX_TIME:
            error_list.append(f"Maximum simulation time is {MAX_TIME} seconds.")
            error_list.append(html.Br())

    # Validate parameters
    # Parameter limits
    param_limits = {
        'l1 (length of rod 1)': (MIN_LENGTH, MAX_LENGTH),
        'l2 (length of rod 2)': (MIN_LENGTH, MAX_LENGTH),
        'm1 (mass of bob 1)': (MIN_MASS, MAX_MASS),
        'm2 (mass of bob 2)': (MIN_MASS, MAX_MASS),
        'M1 (mass of rod 1)': (MIN_MASS, MAX_MASS),
        'M2 (mass of rod 2)': (MIN_MASS, MAX_MASS),
        'g (acceleration due to gravity)': (MIN_GRAVITY, MAX_GRAVITY),
    }

    # Prepare parameter validation based on model type
    param_values = {
        'l1 (length of rod 1)': param_l1,
        'l2 (length of rod 2)': param_l2,
        'g (acceleration due to gravity)': param_g,
        'm1 (mass of bob 1)' if model_type == 'simple' else 'M1 (mass of rod 1)':
            param_m1 if model_type == 'simple' else param_M1,
        'm2 (mass of bob 2)' if model_type == 'simple' else 'M2 (mass of rod 2)':
            param_m2 if model_type == 'simple' else param_M2,
    }

    # Validate parameters
    # Validate each parameter against its limits
    for param_name, param_value in param_values.items():
        if param_name in param_limits:  # Ensure the parameter name exists in the limits dictionary
            min_val, max_val = param_limits[param_name]
            if param_value is None:
                error_list.append(f"{param_name} is required.")
                error_list.append(html.Br())
            elif not isinstance(param_value, (int, float)):
                error_list.append(f"{param_name} must be a number.")
                error_list.append(html.Br())
            elif not (min_val <= param_value <= max_val):
                error_list.append(f"{param_name} must be between {min_val} and {max_val}.")
                error_list.append(html.Br())
                if param_name == 'g (acceleration due to gravity)':
                    error_list.append(
                        f"Note: Moon's gravity = {MIN_GRAVITY} m/s^2, Jupiter's gravity = {MAX_GRAVITY} m/s^2")
                    error_list.append(html.Br())

    # Validate initial conditions
    # Define a mapping from index to label
    index_to_label = {1: 'Pendulum A', 2: 'Pendulum B', 3: 'Pendulum C'}

    for i, conditions in enumerate(initial_conditions_list, start=1):
        condition_names = ['θ1', 'θ2', 'ω1', 'ω2']
        pendulum_label = index_to_label.get(i, f"{i}")
        for name, value in zip(condition_names, conditions):
            if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
                error_list.append(f"{pendulum_label}: {name} requires a numerical value.")
                error_list.append(html.Br())
            else:
                if name in ['θ1', 'θ2'] and (value < -360 or value > 360):
                    error_list.append(f"{pendulum_label}: {name} must be between -360 and 360 degrees.")
                    error_list.append(html.Br())
                elif name in ['ω1', 'ω2']:
                    if abs(value) > MAX_ANGULAR_VELOCITY:
                        if value > 0:
                            error_list.append(
                                f"{pendulum_label}: {name} must be less than {MAX_ANGULAR_VELOCITY} deg/s.")
                        else:
                            error_list.append(
                                f"{pendulum_label}: {name} must be greater than -{MAX_ANGULAR_VELOCITY} deg/s.")
                        error_list.append(html.Br())

    # Return the error message or None if there are no errors
    return html.Div(error_list) if error_list else None


# Helper function to generate animation and phase figures for a pendulum
def generate_pendulum_figures(pendulum, fig_width, fig_height):
    pendulum.precompute_positions()
    animation = pendulum.animate_pendulum(trace=True, fig_width=fig_width, fig_height=fig_height)
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
