from dash import dcc, html

from app.components.simulation_interaction import build_status_shell, build_summary_diagnostics_shell
from app.content.simulation import (
    GRAVITY_OPTIONS,
    GRAVITY_PLACEHOLDER,
    INITIAL_STATE_HELP_LINES,
    INITIAL_STATE_PRESET_OPTIONS,
    INITIAL_CONDITIONS_TITLE,
    INPUT_PLACEHOLDERS,
    LENGTHS_LABEL,
    MASSES_LABEL,
    MODEL_TYPE_OPTIONS,
    PARAMETER_TITLE,
    RUN_SIMULATION_LABEL,
    RUN_VALIDATION_INITIAL,
    SIMULATION_INTERVAL_TITLE,
    SYSTEM_TYPE_OPTIONS,
    UNITY_PARAMETERS_BUTTON_LABEL,
)


INITIAL_STATE_PRESET_ID = "initial-state-preset"
INITIAL_STATE_PRESET_APPLY_STORE_ID = "initial-state-preset-apply-store"
INTEGRATOR_POLICY_ID = "integrator-policy"
INTEGRATOR_POLICY_DEFAULT = "simple_default"
INTEGRATOR_POLICY_OPTIONS = (
    {"label": "DOP853 moderate - default candidate", "value": "simple_default"},
    {"label": "DOP853 strict - high fidelity", "value": "simple_reference"},
    {"label": "SciPy default - baseline/risky", "value": "solve_ivp_default_baseline"},
)
RUN_VALIDATION_MESSAGE_ID = "simulation-run-validation-message"
TIME_MARKS = {
    value: str(value)
    for value in (10, 20, 30, 40, 50, 60)
}
SLIDER_TOOLTIP = {"always_visible": False, "placement": "bottom"}
PARAMETER_INPUT_IDS = ("param_l1", "param_l2", "param_m1", "param_m2", "param_M1", "param_M2")
PARAMETER_INPUT_PLACEHOLDER_KEYS = {
    "param_l1": "l1",
    "param_l2": "l2",
    "param_m1": "m1",
    "param_m2": "m2",
    "param_M1": "M1",
    "param_M2": "M2",
}


def parameter_stepper_id(parameter_id, direction):
    return f"{parameter_id}-{direction}"


def parameter_control_id(parameter_id):
    return f"{parameter_id}-control"


def build_parameter_stepper(parameter_id, visible=True):
    style = None if visible else {"display": "none"}
    placeholder_key = PARAMETER_INPUT_PLACEHOLDER_KEYS[parameter_id]
    return html.Div(
        id=parameter_control_id(parameter_id),
        className="parameter-stepper",
        style=style,
        children=[
            html.Button(
                "-",
                id=parameter_stepper_id(parameter_id, "decrement"),
                n_clicks=0,
                className="parameter-stepper-button parameter-stepper-decrement",
                type="button",
                title=f"Decrease {INPUT_PLACEHOLDERS[placeholder_key]}",
            ),
            dcc.Input(
                id=parameter_id,
                type="text",
                inputMode="numeric",
                placeholder=INPUT_PLACEHOLDERS[placeholder_key],
                min=1,
                max=10,
                readOnly=True,
                step=1,
                className="input parameters-input parameter-stepper-input",
            ),
            html.Button(
                "+",
                id=parameter_stepper_id(parameter_id, "increment"),
                n_clicks=0,
                className="parameter-stepper-button parameter-stepper-increment",
                type="button",
                title=f"Increase {INPUT_PLACEHOLDERS[placeholder_key]}",
            ),
        ],
    )


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
        className="initial-state-preset-hidden",
        children=[
            dcc.Dropdown(
                id=INITIAL_STATE_PRESET_ID,
                options=list(INITIAL_STATE_PRESET_OPTIONS),
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
            dcc.Dropdown(
                id="param_g",
                options=list(GRAVITY_OPTIONS),
                value=9.81,
                placeholder=GRAVITY_PLACEHOLDER,
                clearable=False,
                searchable=False,
                className="dropdown gravity-dropdown quiet-gravity-dropdown",
            ),
            html.Div(
                className="integrator-policy-hidden",
                children=dcc.Dropdown(
                    id=INTEGRATOR_POLICY_ID,
                    options=list(INTEGRATOR_POLICY_OPTIONS),
                    value=INTEGRATOR_POLICY_DEFAULT,
                    clearable=False,
                    searchable=False,
                    className="dropdown integrator-policy-dropdown",
                ),
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
                            build_parameter_stepper("param_l1"),
                            build_parameter_stepper("param_l2"),
                        ],
                    ),
                    html.Div(
                        className="input-columns parameter-column",
                        children=[
                            html.Label(MASSES_LABEL, id="masses-label", className="label masses-label"),
                            build_parameter_stepper("param_m1"),
                            build_parameter_stepper("param_m2"),
                            build_parameter_stepper("param_M1", visible=False),
                            build_parameter_stepper("param_M2", visible=False),
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
        className="input-group run-group simulation-run-dock simulation-run-action",
        children=[
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
            html.Div(
                className="simulation-hidden-runtime-targets",
                children=[
                    build_status_shell(),
                    build_summary_diagnostics_shell(visible=False),
                ],
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
                    html.Div(
                        className="simulation-config-column simulation-config-system-column",
                        children=[
                            build_model_selector(),
                            build_physical_parameters_controls(),
                        ],
                    ),
                    html.Div(
                        className="simulation-config-column simulation-config-state-column",
                        children=[
                            build_initial_conditions_controls(),
                            build_time_controls(),
                        ],
                    ),
                    build_run_controls(),
                ],
            )
        ],
    )
