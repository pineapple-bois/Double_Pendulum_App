import dash
from dash import no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import plotly.tools as tls
import sympy as sp

from app.components.figure_style import mpl_layout
from app.content.home import INFO_BUTTON_CLOSE_LABEL, INFO_BUTTON_OPEN_LABEL
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian
from src.double_pendulum.validation.dash import validate_inputs


M1, M2, m1, m2, l1, l2, g = sp.symbols("M1, M2, m1, m2, l1, l2, g", positive=True, real=True)


def register_simulation_callbacks(app):
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
                return {"display": "block"}, INFO_BUTTON_CLOSE_LABEL, info_n_clicks
            else:
                return {"display": "none"}, INFO_BUTTON_OPEN_LABEL, info_n_clicks
        elif button_id == "close-info-button":
            return {"display": "none"}, INFO_BUTTON_OPEN_LABEL, current_info_n_clicks + 1

        return current_style, INFO_BUTTON_OPEN_LABEL, info_n_clicks

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

    @app.callback(
        [Output('param_m1', 'style'),
         Output('param_m2', 'style'),
         Output('param_M1', 'style'),
         Output('param_M2', 'style')],
        [Input('model-type', 'value')]
    )
    def adjust_parameters_visibility(model_type):
        if model_type == 'simple':
            # Hide M1 and M2 for the simple model
            return ({'display': 'block'}, {'display': 'block'},
                    {'display': 'none'}, {'display': 'none'})
        elif model_type == 'compound':
            # Show M1 and M2 for the compound model
            return ({'display': 'none'}, {'display': 'none'},
                    {'display': 'block'}, {'display': 'block'})

    @app.callback(
        [
            Output('time-graph', 'figure', allow_duplicate=True),
            Output('phase-graph', 'figure', allow_duplicate=True),
            Output('pendulum-animation', 'figure', allow_duplicate=True),
            Output('animation-phase-container', 'style', allow_duplicate=True),
            Output('time-graph-container', 'style', allow_duplicate=True),
            Output('time-graph-section', 'style', allow_duplicate=True),
            Output('error-message', 'children', allow_duplicate=True)
        ],
        [
            Input('init_cond_theta1', 'value'),
            Input('init_cond_theta2', 'value'),
            Input('init_cond_omega1', 'value'),
            Input('init_cond_omega2', 'value'),
            Input('time_start', 'value'),
            Input('time_end', 'value'),
            Input('param_l1', 'value'),
            Input('param_l2', 'value'),
            Input('param_m1', 'value'),
            Input('param_m2', 'value'),
            Input('param_M1', 'value'),
            Input('param_M2', 'value'),
            Input('param_g', 'value'),
            Input('model-type', 'value'),
            Input('system-type', 'value')
        ],
        [State('error-message', 'children')],
        prevent_initial_call=True
    )
    def clear_graphs_on_input_change(init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2,
                                     time_start, time_end, param_l1, param_l2, param_m1, param_m2, param_M1,
                                     param_M2, param_g, model_type, system_type, current_error_message):

        # Step 1: Validate inputs
        initial_conditions = [init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2]
        new_error_message = validate_inputs([initial_conditions],
                                            time_start, time_end, model_type, param_l1, param_l2, param_m1, param_m2,
                                            param_M1, param_M2, param_g)

        # If the error message hasn't changed, prevent updating to avoid flickering
        if new_error_message == current_error_message:
            raise PreventUpdate

        # Step 2: If there's an error, return empty graphs and hide graph containers
        if new_error_message:
            empty_figure = go.Figure()
            return (
                empty_figure, empty_figure, empty_figure,
                {'display': 'none'}, {'display': 'none'}, {'display': 'none'},
                new_error_message
            )

        # Step 3: If no error, update graphs and show graph containers
        # (Your logic to generate the figures goes here. For now, returning empty for example)
        time_figure = go.Figure()  # Replace with actual figure generation logic
        phase_figure = go.Figure()  # Replace with actual figure generation logic
        animation_figure = go.Figure()  # Replace with actual figure generation logic

        return (
            time_figure, phase_figure, animation_figure,
            {'display': 'none'}, {'display': 'none'}, {'display': 'none'},
            new_error_message  # Should be an empty string or None if no error
        )

    @app.callback(
        [Output('time-graph', 'figure'),
         Output('phase-graph', 'figure'),
         Output('pendulum-animation', 'figure'),
         Output('animation-phase-container', 'style'),
         Output('time-graph-container', 'style'),
         Output('time-graph-section', 'style'),
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
                        {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, error_message)

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
                    {'display': 'flex'}, {'display': 'block'}, {'display': 'flex'}, '')

        # If the button hasn't been clicked yet, return empty figures and keep everything hidden
        return (go.Figure(), go.Figure(), go.Figure(),
                {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, '')
