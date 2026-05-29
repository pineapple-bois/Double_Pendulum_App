"""Run a workbench-only Tier 2 Simulation Workspace preview.

From the repository root:

    python development/simulation_workbench/tier_2/workspace_preview_app.py
"""

from __future__ import annotations

from typing import Any

from dash import Dash, Input, Output, State, callback_context, dcc, html
import plotly.graph_objs as go

from output_composition import (
    DURATION_OPTIONS,
    PRESETS,
    SAMPLES_PER_SECOND_OPTIONS,
    assemble_workspace_payload,
    empty_state_payload,
    failure_state_payload,
)


APP_PORT = 8062

PAGE_STYLE = {
    "fontFamily": "Arial, sans-serif",
    "background": "#f7f8fb",
    "color": "#1d2433",
    "minHeight": "100vh",
    "padding": "24px",
}
SHELL_STYLE = {"maxWidth": "1240px", "margin": "0 auto"}
PANEL_STYLE = {
    "background": "white",
    "border": "1px solid #d9dee8",
    "borderRadius": "8px",
    "padding": "16px",
    "boxShadow": "0 1px 2px rgba(16, 24, 40, 0.04)",
}
GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(320px, 1fr))",
    "gap": "16px",
    "alignItems": "start",
}
CONTROL_STYLE = {
    **PANEL_STYLE,
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
    "gap": "14px",
    "alignItems": "end",
    "marginBottom": "16px",
}
BUTTON_STYLE = {
    "border": "1px solid #26364f",
    "background": "#26364f",
    "color": "white",
    "borderRadius": "6px",
    "padding": "9px 12px",
    "cursor": "pointer",
}
SECONDARY_BUTTON_STYLE = {
    **BUTTON_STYLE,
    "background": "white",
    "color": "#26364f",
}
LABEL_STYLE = {"fontWeight": "700", "fontSize": "13px", "marginBottom": "6px"}
MUTED_STYLE = {"color": "#596579", "fontSize": "13px", "lineHeight": "1.45"}
WARNING_STYLE = {
    "background": "#fff8e6",
    "border": "1px solid #f0d28a",
    "borderRadius": "6px",
    "padding": "10px 12px",
    "fontSize": "13px",
}


def label(text: str) -> html.Div:
    return html.Div(text, style=LABEL_STYLE)


def panel(title: str, children, extra_style: dict[str, Any] | None = None) -> html.Div:
    style = dict(PANEL_STYLE)
    if extra_style:
        style.update(extra_style)
    return html.Div(
        [html.H3(title, style={"marginTop": 0, "fontSize": "18px"}), children],
        style=style,
    )


def key_value_rows(data: dict[str, Any]) -> html.Table:
    rows = []
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            display_value = repr(value)
        else:
            display_value = str(value)
        rows.append(
            html.Tr(
                [
                    html.Th(key.replace("_", " "), style={"textAlign": "left", "padding": "4px 10px 4px 0"}),
                    html.Td(display_value, style={"padding": "4px 0", "wordBreak": "break-word"}),
                ]
            )
        )
    return html.Table(rows, style={"width": "100%", "fontSize": "13px", "borderCollapse": "collapse"})


def warning_list(warnings: list[str]) -> html.Div:
    return html.Div(
        [html.Div(warning, style=WARNING_STYLE) for warning in warnings],
        style={"display": "grid", "gap": "8px"},
    )


def metric_rows(metrics: dict[str, Any]) -> html.Div:
    figure_rows = []
    for name, values in metrics.get("figures", {}).items():
        figure_rows.append(
            html.Tr(
                [
                    html.Td(name.replace("_", " ")),
                    html.Td(f"{values['build_time_seconds']:.4f}s"),
                    html.Td(values["trace_count"]),
                    html.Td(values["frame_count"]),
                    html.Td(values["point_count"]),
                    html.Td(values["plotly_json_size_bytes"]),
                ]
            )
        )
    table = html.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Figure"),
                        html.Th("Build"),
                        html.Th("Traces"),
                        html.Th("Frames"),
                        html.Th("Points"),
                        html.Th("JSON bytes"),
                    ]
                )
            ),
            html.Tbody(figure_rows),
        ],
        style={"width": "100%", "fontSize": "13px", "borderCollapse": "collapse"},
    )
    return html.Div(
        [
            key_value_rows(
                {
                    "model_build_time_seconds": f"{metrics['model_build_time_seconds']:.4f}",
                    "composition_total_time_seconds": f"{metrics['composition_total_time_seconds']:.4f}",
                    "output_panel_count": metrics["output_panel_count"],
                    "warning_count": metrics["warning_count"],
                    "solver_metadata_available": metrics["solver_metadata_available"],
                }
            ),
            html.H4("Figure metrics", style={"marginBottom": "8px"}),
            table,
        ]
    )


def empty_view() -> html.Div:
    payload = empty_state_payload()
    return html.Div(
        [
            panel(
                payload["title"],
                html.Div(
                    [
                        html.P(
                            "Run a conservative preview request to populate the planned workspace regions.",
                            style=MUTED_STYLE,
                        ),
                        html.Ul([html.Li(region) for region in payload["regions"]]),
                        warning_list(payload["warnings"]),
                    ]
                ),
            )
        ]
    )


def failure_view(payload: dict[str, Any]) -> html.Div:
    return html.Div(
        [
            panel(
                payload["title"],
                html.Div(
                    [
                        html.P(payload["message"], style=MUTED_STYLE),
                        html.Ul([html.Li(item) for item in payload["details"]]),
                        warning_list(payload["warnings"]),
                    ]
                ),
            )
        ]
    )


def success_view(payload: dict[str, Any]) -> html.Div:
    figures = payload["figures"]
    return html.Div(
        [
            html.Div(
                [
                    panel("Run Summary", key_value_rows(payload["summary"])),
                    panel("Numerical Diagnostics", key_value_rows(payload["diagnostics"])),
                    panel("Warnings And Limits", warning_list(payload["warnings"])),
                    panel("Rendering Metrics", metric_rows(payload["metrics"])),
                ],
                style=GRID_STYLE,
            ),
            html.Div(
                [
                    panel("Physical Motion", dcc.Graph(figure=figures["animation"], config={"displayModeBar": False})),
                    panel(
                        "Angular Displacement Time Series",
                        dcc.Graph(figure=figures["time_series"], config={"displayModeBar": False}),
                    ),
                    panel(
                        "Theta-Theta State Projection",
                        dcc.Graph(figure=figures["state_projection"], config={"displayModeBar": False}),
                    ),
                ],
                style={**GRID_STYLE, "marginTop": "16px"},
            ),
        ]
    )


def app_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H1("Tier 2 Simulation Workspace Preview", style={"marginBottom": "6px"}),
                    html.P(
                        "Workbench-only preview. Uses real model outputs, compact metrics, and explicit warnings.",
                        style=MUTED_STYLE,
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    label("Model type"),
                                    dcc.RadioItems(
                                        id="tier2-model-type",
                                        options=[
                                            {"label": "Simple", "value": "simple"},
                                            {"label": "Compound", "value": "compound"},
                                        ],
                                        value="simple",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    label("System type"),
                                    dcc.RadioItems(
                                        id="tier2-system-type",
                                        options=[
                                            {"label": "Lagrangian", "value": "lagrangian"},
                                            {"label": "Hamiltonian", "value": "hamiltonian"},
                                        ],
                                        value="lagrangian",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    label("Preset"),
                                    dcc.Dropdown(
                                        id="tier2-preset",
                                        options=[
                                            {"label": preset["label"], "value": name}
                                            for name, preset in PRESETS.items()
                                        ],
                                        value="nonzero velocities",
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    label("Duration"),
                                    dcc.Dropdown(
                                        id="tier2-duration",
                                        options=[
                                            {"label": f"{duration:.0f} seconds", "value": duration}
                                            for duration in DURATION_OPTIONS
                                        ],
                                        value=3.0,
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    label("Samples"),
                                    dcc.Dropdown(
                                        id="tier2-samples-per-second",
                                        options=[
                                            {"label": f"{samples}/second", "value": samples}
                                            for samples in SAMPLES_PER_SECOND_OPTIONS
                                        ],
                                        value=120,
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    dcc.Checklist(
                                        id="tier2-failure-preview",
                                        options=[
                                            {
                                                "label": "Preview invalid/failure state",
                                                "value": "failure",
                                            }
                                        ],
                                        value=[],
                                    ),
                                    html.Div(
                                        [
                                            html.Button("Run Preview", id="tier2-run", style=BUTTON_STYLE),
                                            html.Button("Clear", id="tier2-clear", style=SECONDARY_BUTTON_STYLE),
                                        ],
                                        style={"display": "flex", "gap": "8px", "marginTop": "8px"},
                                    ),
                                ]
                            ),
                        ],
                        style=CONTROL_STYLE,
                    ),
                    html.Div(id="tier2-workspace", children=empty_view()),
                ],
                style=SHELL_STYLE,
            )
        ],
        style=PAGE_STYLE,
    )


app = Dash(__name__)
app.title = "Tier 2 Simulation Workspace Preview"
app.layout = app_layout


@app.callback(
    Output("tier2-workspace", "children"),
    Input("tier2-run", "n_clicks"),
    Input("tier2-clear", "n_clicks"),
    State("tier2-model-type", "value"),
    State("tier2-system-type", "value"),
    State("tier2-preset", "value"),
    State("tier2-duration", "value"),
    State("tier2-samples-per-second", "value"),
    State("tier2-failure-preview", "value"),
    prevent_initial_call=True,
)
def update_workspace(
    run_clicks,
    clear_clicks,
    model_type,
    system_type,
    preset,
    duration,
    samples_per_second,
    failure_preview,
):
    del run_clicks, clear_clicks
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    if triggered_id == "tier2-clear":
        return empty_view()
    if "failure" in (failure_preview or []):
        return failure_view(failure_state_payload())
    try:
        payload = assemble_workspace_payload(
            model_type=model_type,
            system_type=system_type,
            preset_name=preset,
            duration_seconds=duration,
            samples_per_second=samples_per_second,
        )
        return success_view(payload)
    except Exception as exc:  # noqa: BLE001 - preview should show controlled failure state.
        payload = failure_state_payload()
        payload["message"] = f"Preview composition failed: {type(exc).__name__}: {exc}"
        return failure_view(payload)


if __name__ == "__main__":
    print(f"Starting Tier 2 preview at http://127.0.0.1:{APP_PORT}/")
    app.run(debug=False, port=APP_PORT)
