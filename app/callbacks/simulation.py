import dash
from dash import html
from dash.dependencies import Input, Output, State
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import plotly.tools as tls
import sympy as sp
from copy import deepcopy
from time import perf_counter_ns

from app.components.figure_style import mpl_layout
from app.components.graphs import get_animation_phase_children, get_time_graph_children
from app.components.simulation_interaction import (
    CANVAS_PAYLOAD_STORE_ID,
    EMPTY_STATE_MESSAGE,
    PLAYBACK_STATE_STORE_ID,
    RESULT_STATE_STORE_ID,
    RENDERER_SYNC_SIGNAL_ID,
    RUN_SUMMARY_AREA_ID,
    SOLVER_DIAGNOSTICS_AREA_ID,
    STATUS_MESSAGE_ID,
    initial_canvas_payload,
    initial_playback_state,
)
from app.content.simulation import INFO_BUTTON_CLOSE_LABEL, INFO_BUTTON_OPEN_LABEL
from app.content.simulation import PHASE_PORTRAIT_TITLE, TIME_GRAPH_TITLE, TRACE_ANIMATION_TITLE
from app.serialization import (
    build_canvas_motion_payload,
    estimate_canvas_payload_size,
    summarise_canvas_payload,
    validate_canvas_motion_payload,
)
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian
from src.double_pendulum.validation.dash import validate_inputs


M1, M2, m1, m2, l1, l2, g = sp.symbols("M1, M2, m1, m2, l1, l2, g", positive=True, real=True)


def _flatten_dash_text(component):
    messages = []

    def collect(node):
        if node is None:
            return
        if isinstance(node, str):
            messages.append(node)
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                collect(child)
            return
        if hasattr(node, "children"):
            collect(node.children)

    collect(component)
    return " ".join(str(message) for message in messages if str(message).strip()).strip()


def _status_message_class(status):
    return f"simulation-status-message simulation-status-{status}"


def _result_state(status, payload, message, playback_state="idle"):
    return {
        "status": status,
        "run_id": payload.get("run_id", 0) if isinstance(payload, dict) else 0,
        "playback_state": playback_state,
        "message": message,
    }


def _playback_state(payload, playback_state="idle", previous_state=None):
    previous_state = previous_state or {}
    return {
        "active_run_id": payload.get("run_id", 0) if isinstance(payload, dict) else 0,
        "selected_frame": int(previous_state.get("selected_frame", 0)),
        "playback_state": playback_state,
        "axes": bool(previous_state.get("axes", True)),
        "grid": bool(previous_state.get("grid", True)),
    }


def _set_payload_size(payload):
    for _ in range(4):
        size_bytes = estimate_canvas_payload_size(payload)
        if payload.get("payload_size_bytes") == size_bytes:
            return payload
        payload["payload_size_bytes"] = size_bytes
    return payload


def mark_canvas_payload_stale(payload, message="Settings changed - rerun to update."):
    if not isinstance(payload, dict) or payload.get("status") not in ("success", "stale"):
        return initial_canvas_payload()

    stale_payload = deepcopy(payload)
    stale_payload["status"] = "stale"
    stale_payload["message"] = message
    stale_payload.setdefault("warnings", [])
    stale_payload.setdefault("rendering", {})
    stale_payload["rendering"]["drawable"] = True
    stale_payload["rendering"]["autoplay_allowed"] = False
    stale_payload["rendering"]["stale"] = True
    return _set_payload_size(stale_payload)


def _parameter_values(model_type, param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g):
    if model_type == "simple":
        weights = {m1: param_m1, m2: param_m2}
    else:
        weights = {M1: param_M1, M2: param_M2}
    return {l1: param_l1, l2: param_l2, g: param_g, **weights}


def _empty_plotly_outputs(instance_id, error_message=None):
    empty_figure = go.Figure()
    return {
        "animation_phase_children": get_animation_phase_children(
            TRACE_ANIMATION_TITLE,
            PHASE_PORTRAIT_TITLE,
            animation_figure=empty_figure,
            phase_figure=empty_figure,
            instance_id=instance_id,
        ),
        "time_graph_children": get_time_graph_children(
            TIME_GRAPH_TITLE,
            figure=empty_figure,
            instance_id=instance_id,
        ),
        "animation_phase_style": {"display": "none"},
        "time_graph_container_style": {"display": "none"},
        "time_graph_section_style": {"display": "none"},
        "error_message": error_message,
    }


def _render_run_summary(payload):
    status = payload.get("status", "empty")
    if status == "empty":
        return [
            html.H3("Run Summary", className="simulation-panel-heading"),
            html.P("Awaiting a simulation run."),
        ]

    summary = summarise_canvas_payload(payload)
    children = [
        html.H3("Run Summary", className="simulation-panel-heading"),
        html.Ul(
            [
                html.Li(f"State: {summary['status']}"),
                html.Li(f"Run ID: {summary['run_id']}"),
                html.Li(f"Model: {summary['model_type'] or 'not set'}"),
                html.Li(f"System: {summary['system_type'] or 'not set'}"),
                html.Li(f"Samples: {summary['sample_count']}"),
                html.Li(f"Duration: {summary['duration_s']} s"),
                html.Li(f"Payload size: {summary['payload_size_bytes']} bytes"),
            ]
        ),
    ]
    if status in ("failed", "cleared"):
        children.append(html.P("No drawable payload is active."))
    elif status == "stale":
        children.append(html.P("Stored output is stale and must be rerun before current playback."))
    return children


def _render_solver_diagnostics(payload, validation_problems=None):
    validation_problems = list(validation_problems or [])
    status = payload.get("status", "empty")
    solver = summarise_canvas_payload(payload)["solver"]
    children = [html.H3("Solver Diagnostics", className="simulation-panel-heading")]

    if status in ("empty", "cleared"):
        children.append(html.P("Solver has not run for the current state."))
        return children

    if not solver.get("integrator"):
        children.append(html.P("Solver was not run for this state."))
    else:
        children.append(
            html.Ul(
                [
                    html.Li(f"Integrator: {solver.get('integrator')}"),
                    html.Li(f"Solver success: {solver.get('success')}"),
                    html.Li(f"Solver status: {solver.get('status')}"),
                    html.Li(f"Requested samples: {solver.get('requested_time_count')}"),
                    html.Li(f"Returned samples: {solver.get('returned_time_count')}"),
                    html.Li(f"Returned samples match request: {solver.get('returned_time_matches_requested')}"),
                ]
            )
        )

    if validation_problems:
        children.append(html.P("Payload validation problems:"))
        children.append(html.Ul([html.Li(problem) for problem in validation_problems]))
    elif status in ("success", "stale"):
        children.append(html.P("Payload validation passed."))

    return children


def _status_children(status, message):
    label = status.capitalize()
    return html.Div(
        [
            html.Strong(f"{label}: "),
            html.Span(message),
        ]
    )


def _state_outputs(payload, status, message, playback_state="idle", previous_playback_state=None, validation_problems=None):
    return {
        "canvas_payload": payload,
        "result_state": _result_state(status, payload, message, playback_state=playback_state),
        "playback_state": _playback_state(payload, playback_state=playback_state, previous_state=previous_playback_state),
        "status_children": _status_children(status, message),
        "status_className": _status_message_class(status),
        "run_summary_children": _render_run_summary(payload),
        "solver_diagnostics_children": _render_solver_diagnostics(payload, validation_problems=validation_problems),
    }


def _callback_outputs(result):
    return (
        result["animation_phase_children"],
        result["time_graph_children"],
        result["animation_phase_style"],
        result["time_graph_container_style"],
        result["time_graph_section_style"],
        result["error_message"],
        result["canvas_payload"],
        result["result_state"],
        result["playback_state"],
        result["status_children"],
        result["status_className"],
        result["run_summary_children"],
        result["solver_diagnostics_children"],
    )


def _failed_result(
    *,
    run_id,
    model_type,
    system_type,
    message,
    errors=None,
    error_message=None,
    solver_metadata=None,
    instance_id=None,
    previous_playback_state=None,
):
    payload = build_canvas_motion_payload(
        None,
        run_id=run_id,
        status="failed",
        model_type=model_type,
        system_type=system_type,
        message=message,
        errors=errors or [],
        solver_metadata=solver_metadata,
    )
    result = _empty_plotly_outputs(instance_id or f"failed-{run_id}-{perf_counter_ns()}", error_message=error_message)
    result.update(
        _state_outputs(
            payload,
            "failed",
            message,
            playback_state="cancelled",
            previous_playback_state=previous_playback_state,
        )
    )
    return result


def build_input_change_result(
    init_cond_theta1,
    init_cond_theta2,
    init_cond_omega1,
    init_cond_omega2,
    time_start,
    time_end,
    param_l1,
    param_l2,
    param_m1,
    param_m2,
    param_M1,
    param_M2,
    param_g,
    model_type,
    system_type,
    current_payload,
    current_playback_state=None,
):
    initial_conditions = [init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2]
    new_error_message = validate_inputs([initial_conditions],
                                        time_start, time_end, model_type, param_l1, param_l2, param_m1, param_m2,
                                        param_M1, param_M2, param_g)
    instance_id = f"stale-{perf_counter_ns()}"

    if new_error_message:
        message = "Validation failed. Correct the highlighted inputs before rerunning."
        return _failed_result(
            run_id=(current_payload or {}).get("run_id", 0),
            model_type=model_type,
            system_type=system_type,
            message=message,
            errors=[_flatten_dash_text(new_error_message) or "Validation failed."],
            error_message=new_error_message,
            instance_id=instance_id,
            previous_playback_state=current_playback_state,
        )

    if isinstance(current_payload, dict) and current_payload.get("status") in ("success", "stale"):
        message = "Settings changed - rerun to update."
        payload = mark_canvas_payload_stale(current_payload, message=message)
        status = "stale"
        playback_state = "cancelled"
    else:
        message = EMPTY_STATE_MESSAGE
        payload = initial_canvas_payload()
        status = "empty"
        playback_state = "idle"

    result = _empty_plotly_outputs(instance_id, error_message=None)
    result.update(
        _state_outputs(
            payload,
            status,
            message,
            playback_state=playback_state,
            previous_playback_state=current_playback_state,
        )
    )
    return result


def build_simulation_run_result(
    n_clicks,
    init_cond_theta1,
    init_cond_theta2,
    init_cond_omega1,
    init_cond_omega2,
    time_start,
    time_end,
    param_l1,
    param_l2,
    param_m1,
    param_m2,
    param_M1,
    param_M2,
    param_g,
    model_type,
    system_type,
    current_playback_state=None,
):
    run_id = int(n_clicks or 0)
    if run_id <= 0:
        payload = initial_canvas_payload()
        result = _empty_plotly_outputs(None, error_message="")
        result.update(
            _state_outputs(
                payload,
                "empty",
                EMPTY_STATE_MESSAGE,
                playback_state="idle",
                previous_playback_state=initial_playback_state(),
            )
        )
        return result

    initial_conditions = [init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2]
    error_message = validate_inputs([initial_conditions],
                                    time_start, time_end, model_type, param_l1, param_l2, param_m1, param_m2,
                                    param_M1, param_M2, param_g)
    if error_message:
        message = "Validation failed. Correct the highlighted inputs before rerunning."
        return _failed_result(
            run_id=run_id,
            model_type=model_type,
            system_type=system_type,
            message=message,
            errors=[_flatten_dash_text(error_message) or "Validation failed."],
            error_message=error_message,
            instance_id=f"error-{run_id}-{perf_counter_ns()}",
            previous_playback_state=current_playback_state,
        )

    time_steps = int((time_end - time_start) * 200)
    time_vector = [time_start, time_end, time_steps]
    parameters = _parameter_values(model_type, param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g)

    try:
        if system_type == "lagrangian":
            pendulum = DoublePendulumLagrangian(parameters, initial_conditions, time_vector, model=model_type)
        else:
            pendulum = DoublePendulumHamiltonian(parameters, initial_conditions, time_vector, model=model_type)
    except Exception as exc:
        return _failed_result(
            run_id=run_id,
            model_type=model_type,
            system_type=system_type,
            message="Solver setup failed before a drawable payload could be created.",
            errors=[str(exc)],
            previous_playback_state=current_playback_state,
        )

    solver_metadata = getattr(pendulum, "solver_metadata", None)
    solver_metadata_dict = solver_metadata.to_dict() if hasattr(solver_metadata, "to_dict") else None
    if solver_metadata is not None and solver_metadata.success is False:
        return _failed_result(
            run_id=run_id,
            model_type=model_type,
            system_type=system_type,
            message="Solver failed before a drawable payload could be accepted.",
            errors=[solver_metadata.message or "Solver reported failure."],
            solver_metadata=solver_metadata_dict,
            previous_playback_state=current_playback_state,
        )

    try:
        pendulum.precompute_positions()
        payload = build_canvas_motion_payload(
            pendulum,
            run_id=run_id,
            status="success",
            model_type=model_type,
            system_type=system_type,
            request_label=f"{model_type} {system_type} run {run_id}",
        )
        payload_problems = validate_canvas_motion_payload(payload)
    except Exception as exc:
        return _failed_result(
            run_id=run_id,
            model_type=model_type,
            system_type=system_type,
            message="Output payload generation failed.",
            errors=[str(exc)],
            solver_metadata=solver_metadata_dict,
            previous_playback_state=current_playback_state,
        )

    if payload_problems:
        return _failed_result(
            run_id=run_id,
            model_type=model_type,
            system_type=system_type,
            message="Output payload validation failed.",
            errors=payload_problems,
            solver_metadata=solver_metadata_dict,
            previous_playback_state=current_playback_state,
        )

    try:
        matplotlib_time_fig = pendulum.time_graph()
        time_fig = tls.mpl_to_plotly(matplotlib_time_fig)
        time_fig.update_layout(
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        plt.close(matplotlib_time_fig)

        matplotlib_phase_fig = pendulum.phase_path()
        phase_fig = tls.mpl_to_plotly(matplotlib_phase_fig)
        phase_fig.update_layout(
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=20),
            width=600,
            height=600,
        )
        plt.close(matplotlib_phase_fig)

        time_fig.update_layout(mpl_layout)
        phase_fig.update_layout(mpl_layout)

        animation_fig = pendulum.animate_pendulum(trace=True, fig_width=600, fig_height=600, static=True)
    except Exception as exc:
        return _failed_result(
            run_id=run_id,
            model_type=model_type,
            system_type=system_type,
            message="Plotly fallback generation failed.",
            errors=[str(exc)],
            solver_metadata=solver_metadata_dict,
            previous_playback_state=current_playback_state,
        )

    instance_id = f"run-{run_id}"
    result = {
        "animation_phase_children": get_animation_phase_children(
            TRACE_ANIMATION_TITLE,
            PHASE_PORTRAIT_TITLE,
            animation_figure=animation_fig,
            phase_figure=phase_fig,
            instance_id=instance_id,
        ),
        "time_graph_children": get_time_graph_children(
            TIME_GRAPH_TITLE,
            figure=time_fig,
            instance_id=instance_id,
        ),
        "animation_phase_style": {"display": "flex"},
        "time_graph_container_style": {"display": "block"},
        "time_graph_section_style": {"display": "flex"},
        "error_message": "",
    }
    result.update(
        _state_outputs(
            payload,
            "success",
            "Run completed. Canvas workspace is ready.",
            playback_state="idle",
            previous_playback_state={"selected_frame": 0, "axes": True, "grid": True},
        )
    )
    return result


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
            Output('animation-phase-container', 'children', allow_duplicate=True),
            Output('time-graph-container', 'children', allow_duplicate=True),
            Output('animation-phase-container', 'style', allow_duplicate=True),
            Output('time-graph-container', 'style', allow_duplicate=True),
            Output('time-graph-section', 'style', allow_duplicate=True),
            Output('error-message', 'children', allow_duplicate=True),
            Output(CANVAS_PAYLOAD_STORE_ID, 'data', allow_duplicate=True),
            Output(RESULT_STATE_STORE_ID, 'data', allow_duplicate=True),
            Output(PLAYBACK_STATE_STORE_ID, 'data', allow_duplicate=True),
            Output(STATUS_MESSAGE_ID, 'children', allow_duplicate=True),
            Output(STATUS_MESSAGE_ID, 'className', allow_duplicate=True),
            Output(RUN_SUMMARY_AREA_ID, 'children', allow_duplicate=True),
            Output(SOLVER_DIAGNOSTICS_AREA_ID, 'children', allow_duplicate=True),
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
        [
            State('error-message', 'children'),
            State(CANVAS_PAYLOAD_STORE_ID, 'data'),
            State(PLAYBACK_STATE_STORE_ID, 'data'),
        ],
        prevent_initial_call=True
    )
    def clear_graphs_on_input_change(init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2,
                                     time_start, time_end, param_l1, param_l2, param_m1, param_m2, param_M1,
                                     param_M2, param_g, model_type, system_type, current_error_message,
                                     current_payload, current_playback_state):
        result = build_input_change_result(
            init_cond_theta1,
            init_cond_theta2,
            init_cond_omega1,
            init_cond_omega2,
            time_start,
            time_end,
            param_l1,
            param_l2,
            param_m1,
            param_m2,
            param_M1,
            param_M2,
            param_g,
            model_type,
            system_type,
            current_payload,
            current_playback_state=current_playback_state,
        )
        return _callback_outputs(result)

    @app.callback(
        [Output('animation-phase-container', 'children'),
         Output('time-graph-container', 'children'),
         Output('animation-phase-container', 'style'),
         Output('time-graph-container', 'style'),
         Output('time-graph-section', 'style'),
         Output('error-message', 'children'),
         Output(CANVAS_PAYLOAD_STORE_ID, 'data'),
         Output(RESULT_STATE_STORE_ID, 'data'),
         Output(PLAYBACK_STATE_STORE_ID, 'data'),
         Output(STATUS_MESSAGE_ID, 'children'),
         Output(STATUS_MESSAGE_ID, 'className'),
         Output(RUN_SUMMARY_AREA_ID, 'children'),
         Output(SOLVER_DIAGNOSTICS_AREA_ID, 'children')],
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
         State('system-type', 'value'),
         State(PLAYBACK_STATE_STORE_ID, 'data')]
    )
    def update_graphs(n_clicks, init_cond_theta1, init_cond_theta2, init_cond_omega1, init_cond_omega2,
                      time_start, time_end,
                      param_l1, param_l2, param_m1, param_m2, param_M1, param_M2, param_g,
                      model_type, system_type, current_playback_state):
        result = build_simulation_run_result(
            n_clicks,
            init_cond_theta1,
            init_cond_theta2,
            init_cond_omega1,
            init_cond_omega2,
            time_start,
            time_end,
            param_l1,
            param_l2,
            param_m1,
            param_m2,
            param_M1,
            param_M2,
            param_g,
            model_type,
            system_type,
            current_playback_state=current_playback_state,
        )
        return _callback_outputs(result)

    app.clientside_callback(
        """
        function(payload, resultState, playbackState) {
            if (
                window.DoublePendulumCanvasRenderer &&
                typeof window.DoublePendulumCanvasRenderer.applyState === 'function'
            ) {
                window.DoublePendulumCanvasRenderer.applyState(payload, resultState, playbackState);
            }
            return '';
        }
        """,
        Output(RENDERER_SYNC_SIGNAL_ID, "children"),
        Input(CANVAS_PAYLOAD_STORE_ID, "data"),
        Input(RESULT_STATE_STORE_ID, "data"),
        Input(PLAYBACK_STATE_STORE_ID, "data"),
    )
