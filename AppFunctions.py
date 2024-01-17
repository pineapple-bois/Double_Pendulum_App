from dash import html
import plotly.tools as tls
import matplotlib.pyplot as plt

# Define a maximum time allowed for the simulation (2 minutes)
MAX_TIME = 120


# Error checking of parameters and initial conditions
def validate_inputs(initial_conditions_list, time_start, time_end,
                    param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g):
    error_list = []
    # Check if time and parameter inputs are None
    time_and_param_inputs = [time_start, time_end, param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g]
    if any(param is None for param in time_and_param_inputs):
        error_list.append("Please fill in all required fields.")
        error_list.append(html.Br())

    # Time vector
    times = {
        'start time': time_start,
        'end time': time_end,
    }
    for time_name, time_value in times.items():
        if time_value is None:
            error_list.append(f"Please provide a value for {time_name}")
            error_list.append(html.Br())

    if time_start >= time_end or time_end <= 0:
        error_list.append("End time must be greater than start time.")
        error_list.append(html.Br())

    if time_start < 0:
        error_list.append("Time interval must begin at zero")
        error_list.append(html.Br())

    if time_end - time_start > MAX_TIME:
        error_list.append(f"Maximum simulation time is {MAX_TIME} seconds.\n")
        error_list.append(html.Br())

    # Parameters
    param_values = {
        'l1 (length of rod 1)': param_l1,
        'l2 (length of rod 2)': param_l2,
        'm1 (mass of bob 1)': param_m1,
        'm2 (mass of bob 2)': param_m2,
        'M1 (mass of rod 1)': param_M1,
        'M2 (mass of rod 2)': param_M2,
        'g (acceleration due to gravity)': param_g,
    }
    for param_name, param_value in param_values.items():
        if param_value is None or not isinstance(param_value, (int, float)):
            error_list.append(f"Please provide a numerical value for {param_name}")
            error_list.append(html.Br())

    for param_name, param_value in param_values.items():
        if param_value is not None and param_value <= 0:
            error_list.append(f"Parameter: {param_name} must be greater than zero.")
            error_list.append(html.Br())

    # Validate each pendulum's initial conditions
    for i, conditions in enumerate(initial_conditions_list, start=1):
        condition_names = ['θ1', 'θ2', 'ω1', 'ω2']
        for name, value in zip(condition_names, conditions):
            if value is None:
                error_list.append(f"Pendulum {i}: {name} requires a numerical value.")
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


