from dash import dcc, html

from app.content.simulation import (
    ANGLES_LABEL,
    CLOSE_INFO_BUTTON_LABEL,
    GRAVITY_LABEL,
    GRAVITY_OPTIONS,
    GRAVITY_PLACEHOLDER,
    INFO_BUTTON_OPEN_LABEL,
    INFORMATION_TEXT,
    INITIAL_CONDITIONS_TITLE,
    INPUT_PLACEHOLDERS,
    LENGTHS_LABEL,
    MASSES_LABEL,
    MODEL_SYSTEM_TITLE,
    MODEL_TYPE_LABEL,
    MODEL_TYPE_OPTIONS,
    PARAMETER_TITLE,
    SIMULATION_INTERVAL_TITLE,
    START_LABEL,
    STOP_LABEL,
    SYSTEM_TYPE_LABEL,
    SYSTEM_TYPE_OPTIONS,
    UNITY_PARAMETERS_BUTTON_LABEL,
    UNITY_PARAMETERS_MARKDOWN,
    VELOCITIES_LABEL,
)


def build_info_popup():
    return html.Div(
        id="info-popup",
        children=[
            html.Button(
                CLOSE_INFO_BUTTON_LABEL,
                id="close-info-button",
                n_clicks=0,
                className="close-info-button",
            ),
            dcc.Markdown(INFORMATION_TEXT, mathjax=True, className="information-content"),
        ],
        className="information-container",
        style={"display": "none"},
    )


def build_model_selector():
    return html.Div(
        className="input-group model-system-group",
        children=[
            html.H4(MODEL_SYSTEM_TITLE, className="inputs-title"),
            html.Button(
                INFO_BUTTON_OPEN_LABEL,
                id="info-button",
                n_clicks=0,
                className="button get-info-button",
            ),
            html.Label(MODEL_TYPE_LABEL, className="label model-type-label"),
            dcc.Dropdown(
                id="model-type",
                options=list(MODEL_TYPE_OPTIONS),
                value="simple",
                clearable=False,
                className="dropdown model-system-dropdown",
            ),
            html.Label(SYSTEM_TYPE_LABEL, className="label system-type-label"),
            dcc.Dropdown(
                id="system-type",
                options=list(SYSTEM_TYPE_OPTIONS),
                value="lagrangian",
                clearable=False,
                className="dropdown system-type-dropdown",
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
            dcc.Markdown(
                UNITY_PARAMETERS_MARKDOWN,
                mathjax=True,
                className="input-subtext parameter-text",
            ),
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
                                className="input parameters-input",
                            ),
                            dcc.Input(
                                id="param_l2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["l2"],
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
                                className="input parameters-input",
                            ),
                            dcc.Input(
                                id="param_m2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["m2"],
                                className="input parameters-input",
                            ),
                            dcc.Input(
                                id="param_M1",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["M1"],
                                className="input parameters-input",
                                style={"display": "none"},
                            ),
                            dcc.Input(
                                id="param_M2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["M2"],
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
                className="split-inputs init-cond-split",
                children=[
                    html.Div(
                        className="input-columns init-cond-column",
                        children=[
                            html.Label(ANGLES_LABEL, className="label initial-conditions-label"),
                            dcc.Input(
                                id="init_cond_theta1",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["theta1"],
                                className="input initial-conditions-input_top",
                            ),
                            dcc.Input(
                                id="init_cond_theta2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["theta2"],
                                className="input initial-conditions-input-top",
                            ),
                        ],
                    ),
                    html.Div(
                        className="input-columns init-cond-column",
                        children=[
                            html.Label(VELOCITIES_LABEL, className="label initial-conditions-label"),
                            dcc.Input(
                                id="init_cond_omega1",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["omega1"],
                                className="input initial-conditions-input-bottom",
                            ),
                            dcc.Input(
                                id="init_cond_omega2",
                                type="number",
                                placeholder=INPUT_PLACEHOLDERS["omega2"],
                                className="input initial-conditions-input-bottom",
                            ),
                        ],
                    ),
                ],
            ),
            *build_time_controls(),
        ],
    )


def build_time_controls():
    return (
        html.H4(SIMULATION_INTERVAL_TITLE, className="inputs-title time-title"),
        html.Div(
            className="split-inputs time-vector-split",
            children=[
                html.Div(
                    className="input-columns time-vector-column",
                    children=[
                        html.Label(START_LABEL, className="label time-vector-label"),
                        dcc.Input(
                            id="time_start",
                            type="number",
                            placeholder=INPUT_PLACEHOLDERS["time_start"],
                            value=0,
                            className="input time-vector-input",
                        ),
                    ],
                ),
                html.Div(
                    className="input-columns time-vector-column",
                    children=[
                        html.Label(STOP_LABEL, className="label time-vector-label"),
                        dcc.Input(
                            id="time_end",
                            type="number",
                            placeholder=INPUT_PLACEHOLDERS["time_end"],
                            value=20,
                            className="input time-vector-input",
                        ),
                    ],
                ),
            ],
        ),
    )


def build_simulation_controls():
    return html.Div(
        className="side-bar",
        children=[
            html.Div(
                className="inputs",
                children=[
                    build_info_popup(),
                    build_model_selector(),
                    build_physical_parameters_controls(),
                    build_initial_conditions_controls(),
                ],
            )
        ],
    )
