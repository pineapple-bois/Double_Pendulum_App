from dash import dcc, html

from app.content.simulation import (
    GRAVITY_LABEL,
    GRAVITY_OPTIONS,
    GRAVITY_PLACEHOLDER,
    INITIAL_STATE_HELP_LINES,
    INITIAL_STATE_PRESET_LABEL,
    INITIAL_STATE_PRESET_OPTIONS,
    INITIAL_STATE_PRESET_PLACEHOLDER,
    INITIAL_CONDITIONS_TITLE,
    INPUT_PLACEHOLDERS,
    LENGTHS_LABEL,
    MASSES_LABEL,
    MODEL_SYSTEM_TITLE,
    MODEL_TYPE_OPTIONS,
    PARAMETER_TITLE,
    RUN_SECTION_TITLE,
    RUN_SIMULATION_LABEL,
    RUN_VALIDATION_INITIAL,
    SIMULATION_INTERVAL_TITLE,
    SYSTEM_TYPE_OPTIONS,
    UNITY_PARAMETERS_BUTTON_LABEL,
)


INITIAL_STATE_PRESET_ID = "initial-state-preset"
INITIAL_STATE_PRESET_APPLY_STORE_ID = "initial-state-preset-apply-store"
RUN_VALIDATION_MESSAGE_ID = "simulation-run-validation-message"
TIME_MARKS = {
    value: str(value)
    for value in (10, 20, 30, 40, 50, 60)
}
SLIDER_TOOLTIP = {"always_visible": False, "placement": "bottom"}


def build_initial_state_heading():
    return html.Div(
        className="initial-state-heading-row",
        children=[
            html.H4(INITIAL_CONDITIONS_TITLE, className="inputs-title initial-state-title"),
            html.Details(
                className="initial-state-help",
                open=False,
                children=[
                    html.Summary("?", className="initial-state-help-summary", title="Initial state help"),
                    html.Div(
                        className="initial-state-help-panel",
                        children=[
                            html.P(INITIAL_STATE_HELP_LINES[0]),
                            html.P(INITIAL_STATE_HELP_LINES[1]),
                            html.P(INITIAL_STATE_HELP_LINES[2]),
                            html.P(INITIAL_STATE_HELP_LINES[3]),
                        ],
                    ),
                ],
            ),
        ],
    )


def build_initial_state_preset_control():
    return html.Div(
        className="initial-state-preset-control",
        children=[
            html.Label(INITIAL_STATE_PRESET_LABEL, className="label initial-state-preset-label"),
            dcc.Dropdown(
                id=INITIAL_STATE_PRESET_ID,
                options=list(INITIAL_STATE_PRESET_OPTIONS),
                placeholder=INITIAL_STATE_PRESET_PLACEHOLDER,
                clearable=True,
                searchable=False,
                className="dropdown initial-state-preset-dropdown",
            ),
        ],
    )


def build_model_selector():
    return html.Div(
        className="input-group model-system-group",
        children=[
            html.H4(MODEL_SYSTEM_TITLE, className="inputs-title"),
            dcc.RadioItems(
                id="model-type",
                options=list(MODEL_TYPE_OPTIONS),
                value="simple",
                inline=True,
                className="binary-choice model-system-choice",
                labelClassName="system-button",
                inputClassName="system-button-input",
            ),
            dcc.RadioItems(
                id="system-type",
                options=list(SYSTEM_TYPE_OPTIONS),
                value="lagrangian",
                inline=True,
                className="binary-choice system-type-choice",
                labelClassName="system-button",
                inputClassName="system-button-input",
            ),
            html.Label(GRAVITY_LABEL, id="g-label", className="label g-label"),
            dcc.Dropdown(
                id="param_g",
                options=list(GRAVITY_OPTIONS),
                value=9.81,
                placeholder=GRAVITY_PLACEHOLDER,
                clearable=False,
                searchable=False,
                className="dropdown gravity-dropdown",
            ),
        ],
    )


def build_physical_parameters_controls():
    return html.Div(
        className="input-group parameters-group",
        children=[
            html.H4(PARAMETER_TITLE, className="inputs-title"),
            html.Button(
                UNITY_PARAMETERS_BUTTON_LABEL,
                id="unity-parameters",
                n_clicks=0,
                className="button unity-parameters-button",
            ),
            html.Div(
                className="split-inputs parameter-split",
                children=[
                    html.Div(
                        className="input-columns parameter-column",
                        children=[
                            html.Label(LENGTHS_LABEL, id="lengths-label", className="label lengths-label"),
                            dcc.Input(
                                id="param_l1",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["l1"],
                                min=0.1,
                                max=10,
                                step=0.1,
                                className="input parameters-input",
                            ),
                            dcc.Input(
                                id="param_l2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["l2"],
                                min=0.1,
                                max=10,
                                step=0.1,
                                className="input parameters-input",
                            ),
                        ],
                    ),
                    html.Div(
                        className="input-columns parameter-column",
                        children=[
                            html.Label(MASSES_LABEL, id="masses-label", className="label masses-label"),
                            dcc.Input(
                                id="param_m1",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["m1"],
                                min=0.1,
                                max=1000,
                                step=0.1,
                                className="input parameters-input",
                            ),
                            dcc.Input(
                                id="param_m2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["m2"],
                                min=0.1,
                                max=1000,
                                step=0.1,
                                className="input parameters-input",
                            ),
                            dcc.Input(
                                id="param_M1",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["M1"],
                                min=0.1,
                                max=1000,
                                step=0.1,
                                className="input parameters-input",
                                style={"display": "none"},
                            ),
                            dcc.Input(
                                id="param_M2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["M2"],
                                min=0.1,
                                max=1000,
                                step=0.1,
                                className="input parameters-input",
                                style={"display": "none"},
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def build_initial_conditions_controls():
    return html.Div(
        className="input-group initial-conditions-group",
        children=[
            build_initial_state_heading(),
            build_initial_state_preset_control(),
            html.Div(
                className="split-inputs initial-state-input-grid",
                children=[
                    html.Div(
                        className="input-columns initial-state-input-column angle-input-column",
                        children=[
                            html.Label("θ₁ (deg)", className="label initial-state-input-label"),
                            dcc.Input(
                                id="init_cond_theta1",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["theta1"],
                                value=0,
                                min=-180,
                                max=180,
                                step=1,
                                className="input initial-state-input angle-input",
                            ),
                            html.Label("θ₂ (deg)", className="label initial-state-input-label"),
                            dcc.Input(
                                id="init_cond_theta2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["theta2"],
                                value=0,
                                min=-180,
                                max=180,
                                step=1,
                                className="input initial-state-input angle-input",
                            ),
                        ],
                    ),
                    html.Div(
                        className="input-columns initial-state-input-column velocity-input-column",
                        children=[
                            html.Label("ω₁ (deg/s)", className="label initial-state-input-label"),
                            dcc.Input(
                                id="init_cond_omega1",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["omega1"],
                                value=0,
                                min=-1000,
                                max=1000,
                                step=1,
                                className="input initial-state-input velocity-input",
                            ),
                            html.Label("ω₂ (deg/s)", className="label initial-state-input-label"),
                            dcc.Input(
                                id="init_cond_omega2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["omega2"],
                                value=0,
                                min=-1000,
                                max=1000,
                                step=1,
                                className="input initial-state-input velocity-input",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def build_time_controls():
    return html.Div(
        className="input-group time-group",
        children=[
            html.H4(SIMULATION_INTERVAL_TITLE, className="inputs-title time-title"),
            html.Div(
                className="time-start-hidden",
                children=dcc.Input(
                    id="time_start",
                    type="number",
                    value=0,
                    min=0,
                    max=0,
                    className="input time-vector-input",
                    style={"display": "none"},
                ),
            ),
            html.Div(
                className="slider-control time-slider-control",
                children=[
                    dcc.Slider(
                        id="time_end",
                        min=1,
                        max=60,
                        step=1,
                        value=20,
                        marks=TIME_MARKS,
                        tooltip=SLIDER_TOOLTIP,
                        className="simulation-slider time-slider",
                    ),
                ],
            ),
        ],
    )


def build_run_controls():
    return html.Div(
        className="input-group run-group simulation-run-action",
        children=[
            html.H4(RUN_SECTION_TITLE, className="inputs-title run-title"),
            html.Div(
                id=RUN_VALIDATION_MESSAGE_ID,
                className="simulation-run-validation-message simulation-run-validation-ready",
                children=[
                    html.Strong("Ready: "),
                    html.Span(RUN_VALIDATION_INITIAL),
                ],
            ),
            html.Button(
                RUN_SIMULATION_LABEL,
                id="submit-val",
                n_clicks=0,
                className="button run-simulation-button simulation-sidebar-run-button",
            ),
        ],
    )


def build_simulation_controls():
    return html.Div(
        className="side-bar",
        children=[
            dcc.Store(id=INITIAL_STATE_PRESET_APPLY_STORE_ID, storage_type="memory"),
            html.Div(
                className="inputs",
                children=[
                    build_model_selector(),
                    build_physical_parameters_controls(),
                    build_initial_conditions_controls(),
                    build_time_controls(),
                    build_run_controls(),
                ],
            )
        ],
    )
