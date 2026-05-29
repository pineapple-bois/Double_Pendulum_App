from dash import dcc, html

from app.content.simulation import (
    GRAVITY_LABEL,
    GRAVITY_OPTIONS,
    GRAVITY_PLACEHOLDER,
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
    STOP_LABEL,
    SYSTEM_TYPE_OPTIONS,
    TIME_CAP_COPY,
    UNITY_PARAMETERS_BUTTON_LABEL,
)


RUN_VALIDATION_MESSAGE_ID = "simulation-run-validation-message"
LABELLED_ANGLE_VALUES = (-180, -90, -45, 0, 45, 90, 180)
ANGLE_MARKS = {
    value: str(value)
    for value in LABELLED_ANGLE_VALUES
}
VELOCITY_MARKS = {
    value: str(value)
    for value in (-720, -360, 0, 360, 720)
}
TIME_MARKS = {
    value: str(value)
    for value in (1, 15, 30, 45, 60)
}
SLIDER_TOOLTIP = {"always_visible": False, "placement": "bottom"}


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
            ),
            dcc.RadioItems(
                id="system-type",
                options=list(SYSTEM_TYPE_OPTIONS),
                value="lagrangian",
                inline=True,
                className="binary-choice system-type-choice",
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
            html.H4(INITIAL_CONDITIONS_TITLE, className="inputs-title"),
            html.Div(
                className="initial-state-slider-stack",
                children=[
                    html.Section(
                        className="initial-state-slider-section angle-slider-section",
                        children=[
                            html.Div(
                                className="slider-control angle-slider-control",
                                children=[
                                    html.Label("θ₁ (deg)", className="label slider-label"),
                                    dcc.Slider(
                                        id="init_cond_theta1",
                                        min=-180,
                                        max=180,
                                        step=1,
                                        value=0,
                                        marks=ANGLE_MARKS,
                                        tooltip=SLIDER_TOOLTIP,
                                        className="simulation-slider angle-slider",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="slider-control angle-slider-control",
                                children=[
                                    html.Label("θ₂ (deg)", className="label slider-label"),
                                    dcc.Slider(
                                        id="init_cond_theta2",
                                        min=-180,
                                        max=180,
                                        step=1,
                                        value=0,
                                        marks=ANGLE_MARKS,
                                        tooltip=SLIDER_TOOLTIP,
                                        className="simulation-slider angle-slider",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Section(
                        className="initial-state-slider-section velocity-slider-section",
                        children=[
                            html.Div(
                                className="slider-control velocity-slider-control",
                                children=[
                                    html.Label("ω₁ (deg/s)", className="label slider-label"),
                                    dcc.Slider(
                                        id="init_cond_omega1",
                                        min=-720,
                                        max=720,
                                        step=5,
                                        value=0,
                                        marks=VELOCITY_MARKS,
                                        tooltip=SLIDER_TOOLTIP,
                                        className="simulation-slider velocity-slider",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="slider-control velocity-slider-control",
                                children=[
                                    html.Label("ω₂ (deg/s)", className="label slider-label"),
                                    dcc.Slider(
                                        id="init_cond_omega2",
                                        min=-720,
                                        max=720,
                                        step=5,
                                        value=0,
                                        marks=VELOCITY_MARKS,
                                        tooltip=SLIDER_TOOLTIP,
                                        className="simulation-slider velocity-slider",
                                    ),
                                ],
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
            html.P(TIME_CAP_COPY, className="input-subtext time-cap-copy"),
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
                    html.Label(f"{STOP_LABEL} (s)", className="label time-vector-label slider-label"),
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
