import dash
from dash import html, dcc, no_update, Dash
from dash.dependencies import Input, Output, State, ClientsideFunction
from dash.exceptions import PreventUpdate
from flask import Flask, redirect, request
import plotly.tools as tls
import plotly.graph_objs as go
import plotly.io as pio
import matplotlib.pyplot as plt
import sympy as sp
import os
from layouts.layout_main import get_main_layout
from layouts.layout_chaos import get_chaos_layout
from layouts.layout_matplotlib import mpl_layout
from AppFunctions import validate_inputs, generate_pendulum_figures, set_display_styles
from DoublePendulum import DoublePendulum

# Sympy variables for parameters
M1, M2, m1, m2, l1, l2, g = sp.symbols("M1, M2, m1, m2, l1, l2, g", positive=True, real=True)


server = Flask(__name__)
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,  # May not be warned about genuine mistakes like typos in component IDs
    external_scripts=[
        # ... (other scripts if any)
        'https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.0/es5/tex-mml-chtml.js'
    ],
    server=server
)


# Comment out to launch locally (development)
#@server.before_request
#def before_request():
    #if not request.is_secure:
        #url = request.url.replace('http://', 'https://', 1)
        #return redirect(url, code=301)


# App set up
app.title = 'Double Pendulum: Lagrangian formulation - pineapple-bois'
app.index_string = open('assets/custom-header.html', 'r').read()
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),  # Tracks the url
    html.Div(id='page-content', children=get_main_layout())  # Set initial content
])


# Clientside callback for resetting the page
app.clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='reset'
    ),
    # This output is dummy, as we don't really update anything on the server
    Output('reset-button', 'n_clicks'),
    Input('reset-button', 'n_clicks')
)


# Navigate to page layout based on url
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    # If the URL path is '/chaos', show the chaos page layout
    if pathname == '/chaos':
        return get_chaos_layout()
    # If the URL path is the root or home, show the main page layout
    elif pathname == '/' or pathname == '/home':
        return get_main_layout()
    # Add more pages as required
    else:
        return get_main_layout()  # or return a 404 not found page layout in future?


# Callback for the unity parameters
@app.callback(
    [Output('param_l1', 'value'),
     Output('param_l2', 'value'),
     Output('param_m1', 'value'),
     Output('param_m2', 'value'),
     Output('param_M1', 'value'),
     Output('param_M2', 'value'),
     Output('param_g', 'value')],
    [Input('unity-parameters', 'n_clicks')],
)
def set_unity_parameters(n_clicks):
    if n_clicks > 0:
        # Return unity values for the parameters, except g which is set to 9.81
        return 1, 1, 1, 1, 1, 1, 9.81
    return dash.no_update  # Prevents updating before button click


# Adjust parameters to model selection
@app.callback(
    [Output('param_m1', 'style'),
     Output('param_m2', 'style'),
     Output('param_M1', 'style'),
     Output('param_M2', 'style'),
     Output('parameters-label', 'children')],
    [Input('model-type', 'value')]
)
def adjust_parameters_visibility(model_type):
    if model_type == 'simple':
        # Hide M1 and M2 for the simple model
        return ({'display': 'block'}, {'display': 'block'}, {'display': 'none'}, {'display': 'none'},
                'Parameters (l1, l2, m1, m2, g): m, kg, m/s')
    elif model_type == 'compound':
        # Show M1 and M2 for the compound model
        return ({'display': 'none'}, {'display': 'none'}, {'display': 'block'}, {'display': 'block'},
                'Parameters (l1, l2, M1, M2, g): m, kg, m/s')


# If Chaos, (if multi pendulums selected), display initial condition inputs
@app.callback(
    [Output('input-column-one', 'style'),
     Output('input-column-two', 'style'),
     Output('input-column-three', 'style'),
     Output('run-simulation-button', 'style')],
    [Input('side-by-sides', 'value')]
)
def toggle_columns(selection):
    if selection == 'two_pendulums':
        return {'display': 'block'}, {'display': 'block'}, {'display': 'none'}, {'display': 'block'}
    elif selection == 'three_pendulums':
        return {'display': 'block'}, {'display': 'block'}, {'display': 'block'}, {'display': 'block'}
    else:
        # Hide everything if no selection is made
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}


# Callback to toggle the mathematics section and button appearance
@app.callback(
    [Output('mathematics-section', 'style'),
     Output('show-maths', 'children'),
     Output('show-maths', 'className')],
    [Input('show-maths', 'n_clicks')],
    [State('show-maths', 'className')]
)
def toggle_math_section(n_clicks, current_class):
    if n_clicks and n_clicks % 2 == 1:
        # If odd number of clicks, show the math section and change button to "Hide Mathematics"
        return {'display': 'flex', 'margin-top': '20px'}, 'Hide Mathematics', 'button-hide'
    else:
        # If even number of clicks, hide the math section and change button to "Show Mathematics"
        return {'display': 'none'}, 'Show Mathematics', 'button-show'


# Callback to update the graphs - main page
@app.callback(
    [Output('time-graph', 'figure'),
     Output('phase-graph', 'figure'),
     Output('pendulum-animation', 'figure'),
     Output('animation-phase-container', 'style'),
     Output('time-graph-container', 'style'),
     Output('math-button-container', 'style'),
     Output('error-message', 'children')],
    [Input('submit-val', 'n_clicks')],
    [State('init_cond_theta1', 'value'),
     State('init_cond_theta2', 'value'),
     State('init_cond_omega1', 'value'),
     State('init_cond_omega2', 'value'),
     State('time_start', 'value'),
     State('time_end', 'value'),
     State('param_l1', 'value'),
     State('param_l2', 'value'),
     State('param_m1', 'value'),
     State('param_m2', 'value'),
     State('param_M1', 'value'),
     State('param_M2', 'value'),
     State('param_g', 'value'),
     State('model-type', 'value')]
)
def update_graphs(n_clicks, init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2,
                  time_start, time_end,
                  param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g,
                  model_type):
    if n_clicks > 0:
        initial_conditions = [init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2]
        time_steps = int((time_end - time_start) * 200)
        time_vector = [time_start, time_end, time_steps]
        parameters = {l1: param_l1, l2: param_l2,
                     m1: param_m1, m2: param_m2,
                     M1: param_M1, M2: param_M2,
                     g: param_g}

        # Validate inputs
        error_message = validate_inputs([initial_conditions],
                                        time_start, time_end, model_type, param_l1, param_l2, param_m1, param_m2,
                                        param_M1, param_M2, param_g)
        if error_message:
            # If there are errors, return immediately
            return (no_update, no_update, no_update,
                    {'display': 'none'}, {'display': 'none'}, {'display': 'none'},
                    error_message)  # TODO: How do we clear the message whilst loading??

        # Create an instance of DoublePendulum
        pendulum = DoublePendulum(parameters, initial_conditions, time_vector, model=model_type)

        # Convert the Matplotlib graphs to Plotly graphs
        matplotlib_time_fig = pendulum.time_graph()
        # Set the layout to be responsive
        time_fig = tls.mpl_to_plotly(matplotlib_time_fig)
        time_fig.update_layout(
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=20),
            width=1400,  # Set the ideal width
            height=700  # Set the ideal height to maintain a 1:1 aspect ratio
        )
        plt.close(matplotlib_time_fig)

        matplotlib_phase_fig = pendulum.phase_path()
        # Set the layout with a fixed aspect ratio for the phase-path graph
        phase_fig = tls.mpl_to_plotly(matplotlib_phase_fig)
        phase_fig.update_layout(
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=20),
            width=700,  # Set the ideal width
            height=700  # Set the ideal height to maintain a 1:1 aspect ratio
        )
        plt.close(matplotlib_phase_fig)

        # Apply the layout to graphs
        time_fig.update_layout(mpl_layout)
        phase_fig.update_layout(mpl_layout)

        # Generate the animation figure
        pendulum.precompute_positions()  # Make sure positions are precomputed
        animation_fig = pendulum.animate_pendulum(trace=True, fig_width=700, fig_height=700)

        return (time_fig, phase_fig, animation_fig,  # graph figures
                {'display': 'grid'}, {'display': 'block'}, {'display': 'block'},
                '')

    # If the button hasn't been clicked yet, return empty figures and keep everything hidden
    return (go.Figure(), go.Figure(), go.Figure(),
            {'display': 'none'}, {'display': 'none'}, {'display': 'none'},
            '')


# Chaos section
# Callback to produce side-by-side animations - chaos page
@app.callback(
    [Output('pendulum-a-animation', 'figure'),
     Output('pendulum-b-animation', 'figure'),
     Output('pendulum-c-animation', 'figure'),
     Output('pendulum-a-phase', 'figure'),
     Output('pendulum-b-phase', 'figure'),      # FIGURES - 6 objects
     Output('pendulum-c-phase', 'figure'),
     Output('pendulum-a-animation', 'style'),
     Output('pendulum-b-animation', 'style'),
     Output('pendulum-c-animation', 'style'),
     Output('pendulum-a-phase', 'style'),
     Output('pendulum-b-phase', 'style'),       # STYLES - 7 objects
     Output('pendulum-c-phase', 'style'),
     Output('pendulum-c-div', 'style'),
     Output('toggle-animation-container', 'style'),
     Output('animation-container', 'style'),
     Output('math-button-container-chaos', 'style'),
     Output('error-message-chaos', 'children')],
    [Input('submit-val', 'n_clicks'),
     Input('side-by-sides', 'value')],
    [State('pend_one_theta1', 'value'),
     State('pend_one_theta2', 'value'),
     State('pend_one_omega1', 'value'),
     State('pend_one_omega2', 'value'),
     State('pend_two_theta1', 'value'),
     State('pend_two_theta2', 'value'),
     State('pend_two_omega1', 'value'),
     State('pend_two_omega2', 'value'),
     State('pend_three_theta1', 'value'),
     State('pend_three_theta2', 'value'),
     State('pend_three_omega1', 'value'),
     State('pend_three_omega2', 'value'),
     State('time_start', 'value'),
     State('time_end', 'value'),
     State('param_l1', 'value'),
     State('param_l2', 'value'),
     State('param_m1', 'value'),
     State('param_m2', 'value'),
     State('param_M1', 'value'),
     State('param_M2', 'value'),
     State('param_g', 'value'),
     State('model-type', 'value')]
)
def multi_animation(n_clicks, pendulum_count, pend_one_theta1, pend_one_theta2, pend_one_omega1, pend_one_omega2,
                    pend_two_theta1, pend_two_theta2, pend_two_omega1, pend_two_omega2,
                    pend_three_theta1, pend_three_theta2, pend_three_omega1, pend_three_omega2,
                    time_start, time_end,
                    param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g,
                    model_type):
    if n_clicks > 0:
        # Set initial conditions
        initial_conditions_a = [pend_one_theta1, pend_one_theta2, pend_one_omega1, pend_one_omega2]
        initial_conditions_b = [pend_two_theta1, pend_two_theta2, pend_two_omega1, pend_two_omega2]
        initial_conditions_c = [pend_three_theta1, pend_three_theta2, pend_three_omega1, pend_three_omega2]

        time_steps = int((time_end - time_start) * 200)
        time_vector = [time_start, time_end, time_steps]
        parameters = {l1: param_l1, l2: param_l2,
                      m1: param_m1, m2: param_m2,
                      M1: param_M1, M2: param_M2,
                      g: param_g}

        if pendulum_count == 'two_pendulums':
            condition_list = initial_conditions_a, initial_conditions_b
        else:
            condition_list = initial_conditions_a, initial_conditions_b, initial_conditions_c

        # Validate inputs
        error_message = validate_inputs(condition_list,
                                        time_start, time_end, model_type, param_l1, param_l2, param_m1, param_m2,
                                        param_M1, param_M2, param_g)
        if error_message:
            # If there are errors, return immediately with default or empty values
            empty_figure = go.Figure()
            default_style = {'display': 'none'}
            return (empty_figure, empty_figure, empty_figure,     # animation figures
                    empty_figure, empty_figure, empty_figure,     # phase figures
                    default_style, default_style, default_style,  # animation styles
                    default_style, default_style, default_style,  # phase styles
                    default_style,                                # pendulum C div
                    default_style, default_style, default_style,  # misc styles
                    error_message)

        # Create DoublePendulum instances
        pendulums = [DoublePendulum(parameters, conditions, time_vector, model=model_type)
                     for conditions in condition_list]

        # Set the animation figure size
        fig_width, fig_height = 500, 500

        # Create figures
        animations, phase_figs = zip(
            *[generate_pendulum_figures(pendulum, fig_width, fig_height) for pendulum in pendulums])

        # Apply layout to phase figures
        for phase_fig in phase_figs:
            phase_fig.update_layout(mpl_layout)

        # Determine display styles
        styles = set_display_styles(pendulum_count)

        # Prepare output based on pendulum count
        if pendulum_count == 'two_pendulums':
            return (animations[0], animations[1], go.Figure(),  # Animation figures
                    phase_figs[0], phase_figs[1], go.Figure(),  # Phase figures
                    *styles,                                    # Animation styles
                    *styles,                                    # Phase styles
                    {'display': 'none'},                        # pendulum C div
                    {'display': 'block'}, {'display': 'grid'}, {'display': 'block'}, '')  # Other styles and message

        elif pendulum_count == 'three_pendulums':
            return (*animations,          # Animation figures
                    *phase_figs,          # Phase figures
                    *styles,              # Animation styles
                    *styles,              # Phase styles
                    {'display': 'none'},  # pendulum C div
                    {'display': 'block'}, {'display': 'grid'}, {'display': 'block'}, '')  # Other styles and message
        else:
            empty_figure = go.Figure()
            default_style = {'display': 'none'}
            return (empty_figure, empty_figure, empty_figure,
                    empty_figure, empty_figure, empty_figure,
                    default_style, default_style, default_style,
                    default_style, default_style, default_style,
                    {'display': 'none'},  # pendulum C div
                    {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, '')

    # Default return for no button clicks
    return (go.Figure(), go.Figure(), go.Figure(),
            go.Figure(), go.Figure(), go.Figure(),
            {'display': 'none'}, {'display': 'none'}, {'display': 'none'},
            {'display': 'none'}, {'display': 'none'}, {'display': 'none'},
            {'display': 'none'},  # pendulum C div
            {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, '')


# Callback to play all animations from 'multi_animation'
@app.callback(
    [Output('global-toggle-button', 'children'),  # Update the button text
     Output('global-toggle-button', 'className'),        # Update the button's className
     Output('global-animation-toggle', 'children')],     # Toggle animation state
    [Input('global-toggle-button', 'n_clicks')],
    [State('global-animation-toggle', 'children')]
)
def toggle_global_animation(n_clicks, toggle_state):
    if n_clicks is None:
        # Prevents the callback from firing before the section has loaded
        raise PreventUpdate

    if n_clicks == 0:
        # Since n_clicks is 0, the page has just loaded. We ensure the initial state is 'Play'.
        return 'Play All', 'button-show', 'Play'

    # Only toggle the state if the button has been clicked at least once
    if n_clicks > 0:
        if toggle_state == 'Play':
            # Change the button to show "Pause All" and change className to 'button-hide'
            # Also update the toggle_state to 'Pause All'
            return 'Pause All', 'button-hide', 'Pause'
        else:
            # Change the button to show "Play All" and change className to 'button-show'
            # Also update the toggle_state to 'Play All'
            return 'Play All', 'button-show', 'Play'


if __name__ == '__main__':
    app.run_server(debug=True)

