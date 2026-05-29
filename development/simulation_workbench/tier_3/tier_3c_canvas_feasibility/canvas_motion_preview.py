"""Tier 3C Canvas motion feasibility preview.

Run from the repository root:

    python development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/canvas_motion_preview.py

Optional compact metrics only:

    python development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/canvas_motion_preview.py --metrics-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "double_pendulum_app_matplotlib_cache"),
)
os.environ.setdefault(
    "XDG_CACHE_HOME",
    str(Path(tempfile.gettempdir()) / "double_pendulum_app_cache"),
)

import matplotlib

matplotlib.use("Agg")
import numpy as np
from dash import Dash, Input, Output, State, callback_context, dcc, html
import plotly.graph_objs as go


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (
            (candidate / "AGENTS.md").is_file()
            and (candidate / "README.md").is_file()
            and (candidate / "src" / "double_pendulum").is_dir()
        ):
            return candidate
    raise RuntimeError(f"Could not find repository root from {start}")


TIER_DIR = Path(__file__).resolve().parent
REPO_ROOT = find_repo_root(TIER_DIR)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian


APP_PORT = 8065
OUTPUT_PATH = TIER_DIR / "tier3c_results.json"

PRESETS = {
    "nonzero_tail": {
        "label": "Nonzero velocities",
        "initial_conditions": [45.0, -30.0, 10.0, -5.0],
    },
    "small_angle": {
        "label": "Small angle",
        "initial_conditions": [10.0, -8.0, 2.0, -1.0],
    },
}

DURATION_OPTIONS = {
    "short_640": {"label": "4s / 640 samples", "duration_seconds": 4.0, "sample_count": 640},
    "moderate_1200": {"label": "6s / 1200 samples", "duration_seconds": 6.0, "sample_count": 1200},
    "larger_2000": {"label": "8s / 2000 samples", "duration_seconds": 8.0, "sample_count": 2000},
}

METRIC_CASES = [
    ("simple", "lagrangian", "nonzero_tail", "short_640"),
    ("compound", "hamiltonian", "nonzero_tail", "moderate_1200"),
    ("simple", "lagrangian", "small_angle", "larger_2000"),
]

PAGE_STYLE = {
    "fontFamily": "Arial, sans-serif",
    "background": "#f6f7fb",
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
    "gridTemplateColumns": "repeat(auto-fit, minmax(230px, 1fr))",
    "gap": "14px",
}
BUTTON_STYLE = {
    "border": "1px solid #26364f",
    "background": "#26364f",
    "color": "white",
    "borderRadius": "6px",
    "padding": "9px 12px",
    "cursor": "pointer",
}
SECONDARY_BUTTON_STYLE = {**BUTTON_STYLE, "background": "white", "color": "#26364f"}
WARNING_STYLE = {
    "background": "#fff8e6",
    "border": "1px solid #f0d28a",
    "borderRadius": "6px",
    "padding": "10px",
}


def timed_call(func):
    start = perf_counter()
    value = func()
    return value, perf_counter() - start


def parameters_for_model(model_type: str) -> tuple[dict[Any, float], dict[str, float]]:
    if model_type == "simple":
        parameters = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
        return parameters, {"l1": 1.0, "l2": 1.0, "m1": 1.0, "m2": 1.0, "g": 9.81}
    if model_type == "compound":
        parameters = {l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81}
        return parameters, {"l1": 1.0, "l2": 1.0, "M1": 1.0, "M2": 1.0, "g": 9.81}
    raise ValueError(f"Unsupported model type: {model_type}")


def model_class_for_system(system_type: str):
    if system_type == "lagrangian":
        return DoublePendulumLagrangian
    if system_type == "hamiltonian":
        return DoublePendulumHamiltonian
    raise ValueError(f"Unsupported system type: {system_type}")


def solver_metadata_summary(model) -> dict[str, Any]:
    metadata = getattr(model, "solver_metadata", None)
    if metadata is None:
        return {}
    data = metadata.to_dict() if hasattr(metadata, "to_dict") else dict(metadata)
    keep = [
        "integrator",
        "success",
        "status",
        "message",
        "nfev",
        "njev",
        "nlu",
        "requested_time_count",
        "returned_time_count",
        "returned_time_matches_requested",
        "solution_shape",
    ]
    return {key: data.get(key) for key in keep}


def drawing_bounds(x1, y1, x2, y2) -> dict[str, float]:
    max_extent = float(max(np.max(np.abs(x1)), np.max(np.abs(y1)), np.max(np.abs(x2)), np.max(np.abs(y2))))
    padding = max(0.1, 0.1 * max_extent)
    return {
        "min_x": -max_extent - padding,
        "max_x": max_extent + padding,
        "min_y": -max_extent - padding,
        "max_y": max_extent + padding,
    }


def build_motion_payload(
    model_type: str,
    system_type: str,
    preset_name: str,
    duration_key: str,
    run_id: int,
):
    duration = DURATION_OPTIONS[duration_key]
    preset = PRESETS[preset_name]
    parameters, parameter_values = parameters_for_model(model_type)
    model_class = model_class_for_system(system_type)

    def construct_model():
        return model_class(
            parameters,
            list(preset["initial_conditions"]),
            [0.0, duration["duration_seconds"], duration["sample_count"]],
            model=model_type,
        )

    model, model_seconds = timed_call(construct_model)
    _, position_seconds = timed_call(model.precompute_positions)
    x1, y1, x2, y2 = model.precomputed_positions
    theta1_deg = np.rad2deg(model.sol[:, 0])
    theta2_deg = np.rad2deg(model.sol[:, 1])

    def assemble_payload():
        payload = {
            "schema_version": "tier3c.motion_payload.v1",
            "kind": "success",
            "run_id": run_id,
            "model_type": model_type,
            "system_type": system_type,
            "preset_name": preset_name,
            "request_label": f"{model_type} {system_type} / {preset['label']} / {duration['label']}",
            "duration_seconds": float(duration["duration_seconds"]),
            "sample_count": int(duration["sample_count"]),
            "time": [float(value) for value in model.time],
            "positions": {
                "x1": [float(value) for value in x1],
                "y1": [float(value) for value in y1],
                "x2": [float(value) for value in x2],
                "y2": [float(value) for value in y2],
            },
            "angular_state": {
                "theta1_deg": [float(value) for value in theta1_deg],
                "theta2_deg": [float(value) for value in theta2_deg],
                "label": "theta1/theta2 angular displacement in degrees; not a full phase portrait",
            },
            "user_initial_conditions": {
                "names": list(getattr(model, "user_initial_condition_names", [])),
                "degrees": [float(value) for value in getattr(model, "user_initial_conditions_degrees", [])],
            },
            "solver_state_convention": getattr(model, "solver_state_convention", None),
            "solver_metadata": solver_metadata_summary(model),
            "parameters": parameter_values,
            "warnings": [
                "Canvas draws Python-computed positions only; it does not validate energy or chaos behavior.",
                "This is a workbench renderer spike, not a production renderer decision.",
                "Theta-theta output is an angular state projection, not a full phase portrait.",
            ],
            "bounds": drawing_bounds(x1, y1, x2, y2),
        }
        payload["payload_byte_estimate"] = len(json.dumps(payload, separators=(",", ":")))
        return payload

    payload, payload_seconds = timed_call(assemble_payload)
    metrics = {
        "python_model_construction_seconds": model_seconds,
        "position_precompute_seconds": position_seconds,
        "payload_preparation_seconds": payload_seconds,
        "payload_byte_estimate": payload["payload_byte_estimate"],
        "sample_count": payload["sample_count"],
        "duration_seconds": payload["duration_seconds"],
        "approx_bytes_per_sample": payload["payload_byte_estimate"] / max(1, payload["sample_count"]),
        "solver_success": payload["solver_metadata"].get("success"),
        "state_values_finite": bool(np.all(np.isfinite(model.sol))),
        "position_values_finite": bool(np.all(np.isfinite(model.precomputed_positions))),
    }
    return payload, metrics


def state_payload(kind: str, run_id: int) -> dict[str, Any]:
    return {
        "schema_version": "tier3c.motion_payload.v1",
        "kind": kind,
        "run_id": run_id,
        "time": [],
        "positions": {"x1": [], "y1": [], "x2": [], "y2": []},
        "angular_state": {"theta1_deg": [], "theta2_deg": []},
        "sample_count": 0,
        "duration_seconds": 0,
        "warnings": [f"{kind} state intentionally contains no drawable motion data."],
        "bounds": {"min_x": -1, "max_x": 1, "min_y": -1, "max_y": 1},
        "payload_byte_estimate": 0,
    }


def compact_metrics(payload: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": payload["run_id"],
        "kind": payload["kind"],
        "model_type": payload.get("model_type"),
        "system_type": payload.get("system_type"),
        "preset_name": payload.get("preset_name"),
        "sample_count": payload.get("sample_count"),
        "duration_seconds": payload.get("duration_seconds"),
        "payload_byte_estimate": metrics.get("payload_byte_estimate", payload.get("payload_byte_estimate")),
        "approx_bytes_per_sample": metrics.get("approx_bytes_per_sample"),
        "python_model_construction_seconds": metrics.get("python_model_construction_seconds"),
        "position_precompute_seconds": metrics.get("position_precompute_seconds"),
        "payload_preparation_seconds": metrics.get("payload_preparation_seconds"),
        "solver_success": metrics.get("solver_success"),
        "position_values_finite": metrics.get("position_values_finite"),
    }


def metrics_table(metrics: dict[str, Any]) -> html.Table:
    return html.Table(
        [
            html.Tr(
                [
                    html.Th(key.replace("_", " "), style={"textAlign": "left", "padding": "4px 10px 4px 0"}),
                    html.Td(str(value), style={"padding": "4px 0"}),
                ]
            )
            for key, value in metrics.items()
        ],
        style={"fontSize": "13px", "borderCollapse": "collapse", "width": "100%"},
    )


def empty_inspection_figure(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        height=320,
        margin=dict(l=48, r=20, t=48, b=44),
        annotations=[
            {
                "text": message,
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
            }
        ],
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def boundary_card() -> html.Div:
    return html.Div(
        [
            html.H3("Boundary", style={"marginTop": 0}),
            html.P("Python model run -> position arrays and metadata -> Dash store payload -> JavaScript Canvas manager -> draw selected frame or playback loop."),
            html.Ul(
                [
                    html.Li("Python owns model construction, integration, position arrays, metadata, and warnings."),
                    html.Li("Dash transports a run-scoped payload; it does not stream every frame through callbacks."),
                    html.Li("JavaScript draws already-computed positions and handles play, pause, reset, scrub, and stale-run cancellation."),
                    html.Li("There is no JavaScript physics."),
                ]
            ),
        ],
        style=PANEL_STYLE,
    )


def app_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H1("Tier 3C Canvas Motion Preview", style={"marginBottom": "6px"}),
                    html.P(
                        "Workbench-only Canvas renderer spike. Python computes the simulation; JavaScript only draws and controls playback.",
                        style={"color": "#596579"},
                    ),
                    dcc.Store(id="tier3c-run-counter", data=0),
                    dcc.Store(id="tier3c-motion-payload", data=state_payload("clear", 0)),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Model type"),
                                    dcc.RadioItems(
                                        id="tier3c-model-type",
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
                                    html.Label("System type"),
                                    dcc.RadioItems(
                                        id="tier3c-system-type",
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
                                    html.Label("Preset"),
                                    dcc.Dropdown(
                                        id="tier3c-preset",
                                        options=[
                                            {"label": value["label"], "value": key}
                                            for key, value in PRESETS.items()
                                        ],
                                        value="nonzero_tail",
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("Duration / samples"),
                                    dcc.Dropdown(
                                        id="tier3c-duration",
                                        options=[
                                            {"label": value["label"], "value": key}
                                            for key, value in DURATION_OPTIONS.items()
                                        ],
                                        value="short_640",
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Button("Run", id="tier3c-run", style=BUTTON_STYLE),
                                    html.Button("Clear", id="tier3c-clear", style=SECONDARY_BUTTON_STYLE),
                                    html.Button("Simulated Failure", id="tier3c-failure", style=SECONDARY_BUTTON_STYLE),
                                ],
                                style={"display": "flex", "gap": "8px", "alignItems": "end"},
                            ),
                        ],
                        style={**PANEL_STYLE, **GRID_STYLE, "marginBottom": "14px"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Canvas(
                                        id="tier3c-canvas",
                                        style={
                                            "width": "100%",
                                            "height": "540px",
                                            "border": "1px solid #d9dee8",
                                            "borderRadius": "8px",
                                            "background": "white",
                                        },
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Label("Canvas reference frame"),
                                                    dcc.Checklist(
                                                        id="tier3c-canvas-options",
                                                        options=[
                                                            {"label": "Axes", "value": "axes"},
                                                            {"label": "Grid", "value": "grid"},
                                                            {"label": "Origin marker", "value": "origin"},
                                                        ],
                                                        value=["axes", "grid", "origin"],
                                                        inline=True,
                                                    ),
                                                ],
                                                style={"marginBottom": "10px"},
                                            ),
                                            html.Button("Play", id="tier3c-play", style=BUTTON_STYLE),
                                            html.Button("Pause", id="tier3c-pause", style=SECONDARY_BUTTON_STYLE),
                                            html.Button("Reset Playback", id="tier3c-reset-playback", style=SECONDARY_BUTTON_STYLE),
                                        ],
                                        style={"display": "flex", "gap": "8px", "marginTop": "10px"},
                                    ),
                                    html.Div(
                                        [
                                            html.Label("Scrub frame"),
                                            dcc.Slider(
                                                id="tier3c-scrubber",
                                                min=0,
                                                max=0,
                                                step=1,
                                                value=0,
                                                marks=None,
                                                disabled=True,
                                                tooltip={"placement": "bottom", "always_visible": False},
                                            ),
                                        ],
                                        style={"marginTop": "16px"},
                                    ),
                                ],
                                style=PANEL_STYLE,
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H3("Canvas status", style={"marginTop": 0}),
                                            html.Pre(
                                                id="tier3c-canvas-status",
                                                children="No payload yet.",
                                                style={"whiteSpace": "pre-wrap", "fontSize": "13px"},
                                            ),
                                        ],
                                        style=PANEL_STYLE,
                                    ),
                                    html.Div(
                                        [
                                            html.H3("Payload metrics", style={"marginTop": 0}),
                                            html.Div(id="tier3c-metrics", children="No run yet."),
                                        ],
                                        style=PANEL_STYLE,
                                    ),
                                    boundary_card(),
                                    html.Div(
                                        "Manual stale-state checks: play, then run a new request; play, then clear; play, then failure; scrub while playing; reset after scrub.",
                                        style=WARNING_STYLE,
                                    ),
                                ],
                                style={"display": "grid", "gap": "14px"},
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "minmax(460px, 2fr) minmax(330px, 1fr)",
                            "gap": "14px",
                            "alignItems": "start",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H3("Selected-time readout", style={"marginTop": 0}),
                                    html.Pre(
                                        id="tier3c-selected-readout",
                                        children="No selected state.",
                                        style={"whiteSpace": "pre-wrap", "fontSize": "13px"},
                                    ),
                                ],
                                style=PANEL_STYLE,
                            ),
                            html.Div(
                                [
                                    dcc.Graph(
                                        id="tier3c-time-series",
                                        figure=empty_inspection_figure(
                                            "Angular displacement time series",
                                            "Run a successful simulation to inspect angular state.",
                                        ),
                                        config={"displaylogo": False},
                                    )
                                ],
                                style=PANEL_STYLE,
                            ),
                            html.Div(
                                [
                                    dcc.Graph(
                                        id="tier3c-projection",
                                        figure=empty_inspection_figure(
                                            "Theta-theta angular state projection",
                                            "Run a successful simulation to inspect the projection.",
                                        ),
                                        config={"displaylogo": False},
                                    )
                                ],
                                style=PANEL_STYLE,
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(auto-fit, minmax(330px, 1fr))",
                            "gap": "14px",
                            "marginTop": "14px",
                        },
                    ),
                ],
                style=SHELL_STYLE,
            )
        ],
        style=PAGE_STYLE,
    )


app = Dash(__name__, assets_folder=str(TIER_DIR / "assets"))
app.title = "Tier 3C Canvas Motion Preview"
app.layout = app_layout


@app.callback(
    Output("tier3c-motion-payload", "data"),
    Output("tier3c-metrics", "children"),
    Output("tier3c-run-counter", "data"),
    Output("tier3c-scrubber", "max"),
    Output("tier3c-scrubber", "value"),
    Output("tier3c-scrubber", "disabled"),
    Input("tier3c-run", "n_clicks"),
    Input("tier3c-clear", "n_clicks"),
    Input("tier3c-failure", "n_clicks"),
    State("tier3c-model-type", "value"),
    State("tier3c-system-type", "value"),
    State("tier3c-preset", "value"),
    State("tier3c-duration", "value"),
    State("tier3c-run-counter", "data"),
    prevent_initial_call=True,
)
def update_payload(
    run_clicks,
    clear_clicks,
    failure_clicks,
    model_type,
    system_type,
    preset_name,
    duration_key,
    run_counter,
):
    del run_clicks, clear_clicks, failure_clicks
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    run_id = int(run_counter or 0) + 1

    if triggered_id == "tier3c-clear":
        payload = state_payload("clear", run_id)
        metrics = {"run_id": run_id, "kind": "clear", "payload_byte_estimate": len(json.dumps(payload))}
        return payload, metrics_table(metrics), run_id, 0, 0, True

    if triggered_id == "tier3c-failure":
        payload = state_payload("failure", run_id)
        metrics = {"run_id": run_id, "kind": "failure", "payload_byte_estimate": len(json.dumps(payload))}
        return payload, metrics_table(metrics), run_id, 0, 0, True

    payload, metrics = build_motion_payload(model_type, system_type, preset_name, duration_key, run_id)
    compact = compact_metrics(payload, metrics)
    return payload, metrics_table(compact), run_id, payload["sample_count"] - 1, 0, False


app.clientside_callback(
    """
    function(payload, playClicks, pauseClicks, resetClicks, scrubValue, displayOptions) {
        return window.dash_clientside.tier3c_canvas.handleCanvasEvent(
            payload, playClicks, pauseClicks, resetClicks, scrubValue, displayOptions
        );
    }
    """,
    Output("tier3c-canvas-status", "children"),
    Input("tier3c-motion-payload", "data"),
    Input("tier3c-play", "n_clicks"),
    Input("tier3c-pause", "n_clicks"),
    Input("tier3c-reset-playback", "n_clicks"),
    Input("tier3c-scrubber", "value"),
    Input("tier3c-canvas-options", "value"),
    prevent_initial_call=True,
)


app.clientside_callback(
    """
    function(payload, scrubValue) {
        return window.dash_clientside.tier3c_canvas.inspectionFigures(payload, scrubValue);
    }
    """,
    Output("tier3c-time-series", "figure"),
    Output("tier3c-projection", "figure"),
    Output("tier3c-selected-readout", "children"),
    Input("tier3c-motion-payload", "data"),
    Input("tier3c-scrubber", "value"),
)


def collect_metrics() -> dict[str, Any]:
    cases = []
    for run_id, (model_type, system_type, preset_name, duration_key) in enumerate(METRIC_CASES, start=1):
        payload, metrics = build_motion_payload(model_type, system_type, preset_name, duration_key, run_id)
        cases.append(compact_metrics(payload, metrics))

    tier3b_path = TIER_DIR.parent / "tier_3b_plotly_strategies" / "tier3b_results.json"
    tier3b_reference = None
    if tier3b_path.is_file():
        tier3b_data = json.loads(tier3b_path.read_text())
        tier3b_reference = {
            "path": str(tier3b_path.relative_to(REPO_ROOT)),
            "summary": "Tier 3B showed reduced frames are not preferred; static scrubber suggests selected-time inspection is valuable.",
            "case_count": len(tier3b_data.get("cases", [])),
        }

    return {
        "tier": "Phase 6 / Tier 3C",
        "purpose": "Compact Canvas motion and synced-inspection payload metrics; arrays omitted",
        "payload_policy": "full selected sample set plus theta1/theta2 inspection samples are serialized to the Dash store; no frame-count reduction",
        "sync_policy": "scrub updates Canvas, time-series marker, theta-theta projection marker, and selected-state readout; playback marker sync is deferred",
        "manual_observation_status": "browser smoke verified axes/grid toggle, scrub sync, play, pause, reset, new-run cancellation, clear, and simulated failure",
        "tier3b_reference": tier3b_reference,
        "cases": cases,
    }


def write_metrics_only() -> None:
    summary = collect_metrics()
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Wrote compact Tier 3C metrics: {OUTPUT_PATH}")
    for case in summary["cases"]:
        print(
            f"- {case['model_type']} {case['system_type']} "
            f"samples={case['sample_count']} payload={case['payload_byte_estimate']} bytes "
            f"precompute={case['position_precompute_seconds']:.4f}s"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-only", action="store_true")
    args = parser.parse_args()
    if args.metrics_only:
        write_metrics_only()
        return 0

    print(f"Starting Tier 3C preview at http://127.0.0.1:{APP_PORT}/")
    app.run(debug=False, port=APP_PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
