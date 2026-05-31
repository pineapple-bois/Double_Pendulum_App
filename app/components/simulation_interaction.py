from dash import dcc, html

from app.serialization import build_canvas_motion_payload


CANVAS_PAYLOAD_STORE_ID = "canvas-motion-payload-store"
RESULT_STATE_STORE_ID = "simulation-result-state-store"
PLAYBACK_STATE_STORE_ID = "simulation-playback-state-store"

INTERACTION_SHELL_ID = "simulation-interaction-shell"
CANVAS_WORKSPACE_ID = "canvas-inspection-workspace"
CANVAS_MOTION_PLACEHOLDER_ID = "canvas-motion-placeholder"
CANVAS_TIME_SERIES_PLACEHOLDER_ID = "canvas-time-series-placeholder"
CANVAS_PROJECTION_PLACEHOLDER_ID = "canvas-projection-placeholder"
CANVAS_MOTION_VIEW_ID = "canvas-motion-view"
CANVAS_TIME_SERIES_VIEW_ID = "canvas-time-series-view"
CANVAS_PROJECTION_VIEW_ID = "canvas-projection-view"
SELECTED_STATE_READOUT_ID = "selected-state-readout"
STATUS_MESSAGE_ID = "simulation-status-message"
RUN_SUMMARY_AREA_ID = "run-summary-area"
SOLVER_DIAGNOSTICS_AREA_ID = "solver-diagnostics-area"
PLAY_BUTTON_ID = "simulation-play-button"
PAUSE_BUTTON_ID = "simulation-pause-button"
RESET_BUTTON_ID = "simulation-reset-button"
SCRUBBER_ID = "simulation-scrubber"
DISPLAY_OPTIONS_ID = "simulation-display-options"
FRAME_INDICATOR_ID = "simulation-frame-indicator"
RENDERER_SYNC_SIGNAL_ID = "simulation-renderer-sync-signal"
DIAGNOSTICS_TOGGLE_ID = "simulation-diagnostics-toggle"
DIAGNOSTICS_CONTENT_ID = "simulation-diagnostics-content"

EMPTY_STATE_MESSAGE = (
    "No simulation run yet. Run a validated setup to prepare motion playback, "
    "run summary, and solver diagnostics."
)


def initial_canvas_payload():
    return build_canvas_motion_payload(
        None,
        run_id=0,
        status="empty",
        message=EMPTY_STATE_MESSAGE,
    )


def initial_result_state():
    return {
        "status": "empty",
        "run_id": 0,
        "playback_state": "idle",
        "message": EMPTY_STATE_MESSAGE,
    }


def initial_playback_state():
    return {
        "active_run_id": 0,
        "selected_frame": 0,
        "playback_state": "idle",
        "axes": True,
        "grid": True,
    }


def build_simulation_state_stores():
    return [
        dcc.Store(
            id=CANVAS_PAYLOAD_STORE_ID,
            storage_type="memory",
            data=initial_canvas_payload(),
        ),
        dcc.Store(
            id=RESULT_STATE_STORE_ID,
            storage_type="memory",
            data=initial_result_state(),
        ),
        dcc.Store(
            id=PLAYBACK_STATE_STORE_ID,
            storage_type="memory",
            data=initial_playback_state(),
        ),
    ]


def _canvas_panel(title, element_id, canvas_id, label, panel_class):
    return html.Div(
        className=f"simulation-panel canvas-placeholder-panel {panel_class}",
        children=[
            html.H4(title, className="simulation-panel-title"),
            html.Div(
                id=element_id,
                className="canvas-placeholder canvas-renderer-panel",
                children=[
                    html.Canvas(
                        id=canvas_id,
                        className="simulation-canvas-view",
                        role="img",
                        **{"aria-label": label},
                    ),
                ],
            ),
        ],
    )


def build_canvas_workspace_placeholder():
    return html.Section(
        id=CANVAS_WORKSPACE_ID,
        className="simulation-panel canvas-inspection-workspace",
        children=[
            html.Div(
                className="simulation-output-header-row",
                children=[
                    build_playback_shell(),
                ],
            ),
            html.Div(
                className="canvas-workspace-grid",
                children=[
                    _canvas_panel(
                        "Motion",
                        CANVAS_MOTION_PLACEHOLDER_ID,
                        CANVAS_MOTION_VIEW_ID,
                        "Double pendulum motion view",
                        "canvas-panel-motion",
                    ),
                    _canvas_panel(
                        "Angular State Projection",
                        CANVAS_PROJECTION_PLACEHOLDER_ID,
                        CANVAS_PROJECTION_VIEW_ID,
                        "Theta-theta angular state projection view",
                        "canvas-panel-projection",
                    ),
                    build_scrubber_shell(),
                    _canvas_panel(
                        "Angular Displacement",
                        CANVAS_TIME_SERIES_PLACEHOLDER_ID,
                        CANVAS_TIME_SERIES_VIEW_ID,
                        "Angular displacement time-series view",
                        "canvas-panel-time",
                    ),
                ],
            ),
        ],
    )


def build_playback_shell():
    return html.Div(
        className=(
            "playback-shell canvas-playback-panel simulation-playback-strip "
            "simulation-playback-header"
        ),
        children=[
            html.Div(
                className="playback-panel-copy",
                children=[
                    html.H3("Run and inspect the simulation", className="simulation-panel-heading playback-panel-heading"),
                    html.P(
                        "Choose the system configuration, then run the solver to prepare playback, "
                        "state projection, and time-series plots.",
                        className="playback-panel-text",
                    ),
                    html.P(
                        "Use playback, guide toggles, and the time slider to inspect the computed "
                        "trajectory across the linked visualisations.",
                        className="playback-panel-text",
                    ),
                ],
            ),
            html.Div(
                className="playback-controls-row playback-panel-controls-row",
                children=[
                    html.Div(
                        className="playback-control-row playback-header-controls",
                        children=[
                            html.Div(
                                className="playback-controls playback-button-group",
                                children=[
                                    html.Button("Play", id=PLAY_BUTTON_ID, className="button", disabled=True),
                                    html.Button("Pause", id=PAUSE_BUTTON_ID, className="button", disabled=True),
                                    html.Button("Reset", id=RESET_BUTTON_ID, className="button", disabled=True),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="playback-options-row playback-header-display",
                        children=[
                            dcc.Checklist(
                                id=DISPLAY_OPTIONS_ID,
                                options=[
                                    {"label": "Axes", "value": "axes", "disabled": True},
                                    {"label": "Grid", "value": "grid", "disabled": True},
                                ],
                                value=["axes", "grid"],
                                inline=True,
                                className="display-options-toggle",
                            ),
                        ],
                    ),
                    html.Div(
                        id=FRAME_INDICATOR_ID,
                        className="simulation-frame-indicator",
                        children="t = --",
                    ),
                ],
            ),
        ],
    )


def build_scrubber_shell():
    return html.Div(
        className="scrubber-row canvas-time-selector",
        children=[
            dcc.Input(
                id=SCRUBBER_ID,
                type="range",
                min=0,
                max=0,
                value=0,
                step=1,
                disabled=True,
                className="simulation-scrubber",
            ),
        ],
    )


def build_status_shell():
    return html.Div(
        id=STATUS_MESSAGE_ID,
        className="simulation-status-message simulation-status-empty",
        children=EMPTY_STATE_MESSAGE,
    )


def build_summary_diagnostics_shell(visible=True):
    diagnostics_content = html.Div(
        id=DIAGNOSTICS_CONTENT_ID,
        className="simulation-summary-diagnostics simulation-detail-diagnostics",
        children=[
            html.Section(
                className="simulation-panel selected-state-diagnostics-area",
                children=[
                    html.H3("Selected State", className="simulation-panel-heading"),
                    html.Div(
                        id=SELECTED_STATE_READOUT_ID,
                        className="selected-state-readout",
                        children="Selected frame: 0",
                    ),
                ],
            ),
            html.Section(
                id=RUN_SUMMARY_AREA_ID,
                className="simulation-panel run-summary-area",
                children=[
                    html.H3("Run Summary", className="simulation-panel-heading"),
                    html.P("Awaiting a simulation run."),
                ],
            ),
            html.Section(
                id=SOLVER_DIAGNOSTICS_AREA_ID,
                className="simulation-panel solver-diagnostics-area",
                children=[
                    html.H3("Solver Diagnostics", className="simulation-panel-heading"),
                    html.P("Solver has not run yet."),
                ],
            ),
        ],
    )

    if not visible:
        return html.Div(
            id=DIAGNOSTICS_TOGGLE_ID,
            className="simulation-diagnostics-toggle simulation-hidden-runtime-targets",
            children=diagnostics_content,
        )

    return html.Details(
        id=DIAGNOSTICS_TOGGLE_ID,
        className="simulation-diagnostics-toggle",
        open=False,
        children=[
            html.Summary("Show diagnostics", className="simulation-diagnostics-summary"),
            diagnostics_content,
        ],
    )


def build_simulation_interaction_shell():
    return html.Div(
        id=INTERACTION_SHELL_ID,
        className="simulation-interaction-shell",
        children=[
            *build_simulation_state_stores(),
            html.Div(id=RENDERER_SYNC_SIGNAL_ID, className="simulation-renderer-sync-signal"),
            build_canvas_workspace_placeholder(),
        ],
    )
