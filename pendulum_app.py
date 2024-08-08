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
from layouts.layout_math import get_lagrangian_layout, get_hamiltonian_layout
from layouts.layout_chaos import get_chaos_layout
from layouts.layout_404 import get_404_layout
from layouts.layout_matplotlib import mpl_layout
from AppFunctions import validate_inputs, generate_pendulum_figures, set_display_styles
from DoublePendulumLagrangian import DoublePendulumLagrangian
from DoublePendulumHamiltonian import DoublePendulumHamiltonian

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
# @server.before_request
# def before_request():
#     if not request.is_secure:
#         url = request.url.replace('http://', 'https://', 1)
#         return redirect(url, code=301)


# App set up
app.title = 'Double Pendulum Simulation - pineapple-bois'
app.index_string = open('assets/custom-header.html', 'r').read()
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),  # Tracks the url
    html.Div(id='page-content', children=get_main_layout())  # Set initial content
])


# Navigate to page layout based on url
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/chaos':
        return get_chaos_layout()
    elif pathname == '/lagrangian':
        return get_lagrangian_layout()
    elif pathname == '/hamiltonian':
        return get_hamiltonian_layout()
    # Add more pages as required
    else:
        return get_404_layout() if pathname != '/' else get_main_layout()


@app.callback(
    [Output("info-popup", "style"),
     Output("info-button", "children"),
     Output("info-button", "n_clicks")],
    [Input("info-button", "n_clicks"),
     Input("close-info-button", "n_clicks")],
    [State("info-popup", "style"),
     State("info-button", "n_clicks")]
)
def toggle_info(info_n_clicks, close_n_clicks, current_style, current_info_n_clicks):
    ctx = dash.callback_context

    if not ctx.triggered:
        button_id = 'No clicks yet'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == "info-button":
        if info_n_clicks % 2 == 1:
            return {"display": "block"}, "Close Information", info_n_clicks
        else:
            return {"display": "none"}, "What do I even choose?", info_n_clicks
    elif button_id == "close-info-button":
        return {"display": "none"}, "What do I even choose?", current_info_n_clicks + 1

    return current_style, "What do I even choose?", info_n_clicks


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
                'Parameters (l1, l2, m1, m2, g)')
    elif model_type == 'compound':
        # Show M1 and M2 for the compound model
        return ({'display': 'none'}, {'display': 'none'}, {'display': 'block'}, {'display': 'block'},
                'Parameters (l1, l2, M1, M2, g)')


# Callback to update the graphs - main page
@app.callback(
    [Output('time-graph', 'figure'),
     Output('phase-graph', 'figure'),
     Output('pendulum-animation', 'figure'),
     Output('animation-phase-container', 'style'),
     Output('time-graph-container', 'style'),
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
     State('model-type', 'value'),
     State('system-type', 'value')]
)
def update_graphs(n_clicks, init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2,
                  time_start, time_end,
                  param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g,
                  model_type, system_type):
    if n_clicks > 0:
        initial_conditions = [init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2]
        # Validate inputs
        error_message = validate_inputs([initial_conditions],
                                        time_start, time_end, model_type, param_l1, param_l2, param_m1, param_m2,
                                        param_M1, param_M2, param_g)
        if error_message:
            # If there are errors, return immediately
            return (no_update, no_update, no_update,
                    {'display': 'none'}, {'display': 'none'}, error_message)

        time_steps = int((time_end - time_start) * 200)
        time_vector = [time_start, time_end, time_steps]

        # Conditional parameter assignment based on model type
        if model_type == 'simple':
            weights = {m1: param_m1, m2: param_m2}
        else:
            weights = {M1: param_M1, M2: param_M2}

        # Combine all parameters
        parameters = {l1: param_l1, l2: param_l2, g: param_g, **weights}

        # Create an instance of DoublePendulum
        if system_type == 'lagrangian':
            pendulum = DoublePendulumLagrangian(parameters, initial_conditions, time_vector, model=model_type)
        else:
            pendulum = DoublePendulumHamiltonian(parameters, initial_conditions, time_vector, model=model_type)

        # Convert the Matplotlib graphs to Plotly graphs
        matplotlib_time_fig = pendulum.time_graph()
        # Set the layout to be responsive
        time_fig = tls.mpl_to_plotly(matplotlib_time_fig)
        time_fig.update_layout(
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        plt.close(matplotlib_time_fig)

        matplotlib_phase_fig = pendulum.phase_path()
        # Set the layout with a fixed aspect ratio for the phase-path graph
        phase_fig = tls.mpl_to_plotly(matplotlib_phase_fig)
        phase_fig.update_layout(
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=20),
            width=600,
            height=600
        )
        plt.close(matplotlib_phase_fig)

        # Apply the layout to graphs
        time_fig.update_layout(mpl_layout)
        phase_fig.update_layout(mpl_layout)

        # Generate the animation figure
        pendulum.precompute_positions()  # Make sure positions are precomputed
        animation_fig = pendulum.animate_pendulum(trace=True, fig_width=600, fig_height=600, static=True)

        return (time_fig, phase_fig, animation_fig,  # graph figures
                {'display': 'flex'}, {'display': 'block'}, '')

    # If the button hasn't been clicked yet, return empty figures and keep everything hidden
    return (go.Figure(), go.Figure(), go.Figure(),
            {'display': 'none'}, {'display': 'none'}, '')


if __name__ == '__main__':
    app.run_server(debug=True)
