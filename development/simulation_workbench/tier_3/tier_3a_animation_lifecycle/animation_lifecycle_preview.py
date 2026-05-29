"""Tier 3A Plotly animation lifecycle preview.

Run from the repository root:

    python development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py

Optional compact metrics only:

    python development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py --metrics-only
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


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian


APP_PORT = 8063
OUTPUT_PATH = Path(__file__).with_name("tier3a_results.json")

PRESETS = {
    "zero_tail": {
        "label": "Zero velocities",
        "initial_conditions": [45.0, -30.0, 0.0, 0.0],
    },
    "nonzero_tail": {
        "label": "Nonzero velocities",
        "initial_conditions": [45.0, -30.0, 10.0, -5.0],
    },
    "small_angle": {
        "label": "Small angle",
        "initial_conditions": [10.0, -8.0, 2.0, -1.0],
    },
}

PAGE_STYLE = {
    "fontFamily": "Arial, sans-serif",
    "background": "#f6f7fb",
    "color": "#1d2433",
    "minHeight": "100vh",
    "padding": "24px",
}
SHELL_STYLE = {"maxWidth": "1180px", "margin": "0 auto"}
PANEL_STYLE = {
    "background": "white",
    "border": "1px solid #d9dee8",
    "borderRadius": "8px",
    "padding": "16px",
    "boxShadow": "0 1px 2px rgba(16, 24, 40, 0.04)",
}
GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))",
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


def parameters_for_model(model_type: str) -> dict[Any, float]:
    if model_type == "simple":
        return {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
    if model_type == "compound":
        return {l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81}
    raise ValueError(f"Unsupported model type: {model_type}")


def model_class_for_system(system_type: str):
    if system_type == "lagrangian":
        return DoublePendulumLagrangian
    if system_type == "hamiltonian":
        return DoublePendulumHamiltonian
    raise ValueError(f"Unsupported system type: {system_type}")


def timed_call(func):
    start = perf_counter()
    value = func()
    return value, perf_counter() - start


def figure_point_count(fig) -> int:
    total = 0
    for trace in getattr(fig, "data", []) or []:
        x_values = getattr(trace, "x", None)
        if x_values is not None:
            total += len(x_values)
    for frame in getattr(fig, "frames", []) or []:
        for trace in getattr(frame, "data", []) or []:
            x_values = getattr(trace, "x", None)
            if x_values is not None:
                total += len(x_values)
    return int(total)


def figure_metrics(fig, build_time_seconds: float) -> dict[str, Any]:
    return {
        "build_time_seconds": build_time_seconds,
        "trace_count": len(getattr(fig, "data", []) or []),
        "frame_count": len(getattr(fig, "frames", []) or []),
        "point_count": figure_point_count(fig),
        "plotly_json_size_bytes": len(fig.to_json()),
    }


def build_animation_payload(
    model_type: str,
    system_type: str,
    preset_name: str,
    duration_seconds: float = 4.0,
    samples_per_second: int = 160,
    run_id: int = 1,
    identity_strategy: str = "fixed_graph",
):
    sample_count = int(duration_seconds * samples_per_second)
    model = model_class_for_system(system_type)(
        parameters_for_model(model_type),
        list(PRESETS[preset_name]["initial_conditions"]),
        [0.0, duration_seconds, sample_count],
        model=model_type,
    )
    model.precompute_positions()
    fig, build_time = timed_call(
        lambda: model.animate_pendulum(trace=True, fig_width=620, fig_height=520, static=False)
    )
    fig.update_layout(
        title=f"Run {run_id}: {model_type} {system_type} ({PRESETS[preset_name]['label']})",
        margin=dict(l=20, r=20, t=48, b=24),
    )
    if identity_strategy == "unique_uirevision":
        fig.update_layout(uirevision=f"run-{run_id}")
    elif identity_strategy == "fixed_uirevision":
        fig.update_layout(uirevision="tier3a-fixed")

    metrics = figure_metrics(fig, build_time)
    run_context = {
        "run_id": run_id,
        "model_type": model_type,
        "system_type": system_type,
        "preset": preset_name,
        "duration_seconds": duration_seconds,
        "sample_count": sample_count,
        "samples_per_second": samples_per_second,
        "identity_strategy": identity_strategy,
        "graph_identity": "unique per run" if identity_strategy == "unique_graph" else "fixed graph id",
        "solver_success": getattr(model.solver_metadata, "success", None),
        "solver_state_convention": getattr(model, "solver_state_convention", None),
    }
    return fig, metrics, run_context


def clear_figure(run_id: int) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=f"Run {run_id}: cleared",
        annotations=[
            {
                "text": "Cleared. Any old animation should stop immediately.",
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
            }
        ],
        xaxis={"visible": False},
        yaxis={"visible": False},
        height=520,
    )
    return fig


def failure_figure(run_id: int) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=f"Run {run_id}: simulated failure",
        annotations=[
            {
                "text": "Failure preview. Old successful animation must not continue.",
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
            }
        ],
        xaxis={"visible": False},
        yaxis={"visible": False},
        height=520,
    )
    return fig


def status_panel(run_context: dict[str, Any], metrics: dict[str, Any], action: str) -> html.Div:
    rows = {**run_context, **{f"animation_{key}": value for key, value in metrics.items()}, "last_action": action}
    return html.Table(
        [
            html.Tr(
                [
                    html.Th(key.replace("_", " "), style={"textAlign": "left", "padding": "4px 10px 4px 0"}),
                    html.Td(str(value), style={"padding": "4px 0"}),
                ]
            )
            for key, value in rows.items()
        ],
        style={"fontSize": "13px", "borderCollapse": "collapse", "width": "100%"},
    )


def graph_component(fig, run_id: int, identity_strategy: str):
    graph_id = f"tier3a-animation-{run_id}" if identity_strategy == "unique_graph" else "tier3a-animation"
    return dcc.Graph(
        id=graph_id,
        figure=fig,
        config={"displayModeBar": False},
        style={"height": "560px"},
    )


def manual_test_card() -> html.Div:
    steps = [
        "Click Run Animation, then press Play inside the Plotly figure.",
        "While it is playing, click Run Animation again with the same request.",
        "Repeat while switching model, system, and preset.",
        "Repeat while using Clear Output and Simulated Failure.",
        "Try identity strategies: fixed graph, unique uirevision, unique graph.",
        "Record whether old motion keeps playing after the run context changes.",
    ]
    return html.Div(
        [
            html.H3("Manual lifecycle script", style={"marginTop": 0}),
            html.Ol([html.Li(step) for step in steps]),
            html.Div(
                "This preview does not claim automated browser reproduction. It exposes the smallest lifecycle surface to inspect the known bug.",
                style=WARNING_STYLE,
            ),
        ],
        style=PANEL_STYLE,
    )


def app_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H1("Tier 3A Animation Lifecycle Preview", style={"marginBottom": "6px"}),
                    html.P(
                        "Workbench-only Plotly stale-playback investigation. Production /simulation is untouched.",
                        style={"color": "#596579"},
                    ),
                    dcc.Store(id="tier3a-run-counter", data=0),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Model type"),
                                    dcc.RadioItems(
                                        id="tier3a-model-type",
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
                                        id="tier3a-system-type",
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
                                        id="tier3a-preset",
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
                                    html.Label("Identity strategy"),
                                    dcc.Dropdown(
                                        id="tier3a-identity-strategy",
                                        options=[
                                            {"label": "Fixed graph id", "value": "fixed_graph"},
                                            {"label": "Unique uirevision", "value": "unique_uirevision"},
                                            {"label": "Fixed uirevision", "value": "fixed_uirevision"},
                                            {"label": "Unique graph per run", "value": "unique_graph"},
                                        ],
                                        value="fixed_graph",
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Button("Run Animation", id="tier3a-run", style=BUTTON_STYLE),
                                    html.Button("Clear Output", id="tier3a-clear", style=SECONDARY_BUTTON_STYLE),
                                    html.Button(
                                        "Simulated Failure",
                                        id="tier3a-failure",
                                        style=SECONDARY_BUTTON_STYLE,
                                    ),
                                ],
                                style={"display": "flex", "gap": "8px", "alignItems": "end"},
                            ),
                        ],
                        style={**PANEL_STYLE, **GRID_STYLE, "marginBottom": "14px"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                id="tier3a-animation-shell",
                                children=graph_component(clear_figure(0), 0, "fixed_graph"),
                                style=PANEL_STYLE,
                            ),
                            html.Div(
                                [
                                    html.Div(id="tier3a-status", children="No run yet."),
                                    html.Br(),
                                    manual_test_card(),
                                ],
                                style={"display": "grid", "gap": "14px"},
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "minmax(420px, 2fr) minmax(320px, 1fr)",
                            "gap": "14px",
                            "alignItems": "start",
                        },
                    ),
                ],
                style=SHELL_STYLE,
            )
        ],
        style=PAGE_STYLE,
    )


app = Dash(__name__)
app.title = "Tier 3A Animation Lifecycle Preview"
app.layout = app_layout


@app.callback(
    Output("tier3a-animation-shell", "children"),
    Output("tier3a-status", "children"),
    Output("tier3a-run-counter", "data"),
    Input("tier3a-run", "n_clicks"),
    Input("tier3a-clear", "n_clicks"),
    Input("tier3a-failure", "n_clicks"),
    State("tier3a-model-type", "value"),
    State("tier3a-system-type", "value"),
    State("tier3a-preset", "value"),
    State("tier3a-identity-strategy", "value"),
    State("tier3a-run-counter", "data"),
    prevent_initial_call=True,
)
def update_animation(run_clicks, clear_clicks, failure_clicks, model_type, system_type, preset, strategy, run_counter):
    del run_clicks, clear_clicks, failure_clicks
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    run_id = int(run_counter or 0) + 1

    if triggered_id == "tier3a-clear":
        fig = clear_figure(run_id)
        context = {"run_id": run_id, "identity_strategy": strategy, "graph_identity": "clear figure"}
        metrics = figure_metrics(fig, 0.0)
        return graph_component(fig, run_id, strategy), status_panel(context, metrics, "clear"), run_id

    if triggered_id == "tier3a-failure":
        fig = failure_figure(run_id)
        context = {"run_id": run_id, "identity_strategy": strategy, "graph_identity": "failure figure"}
        metrics = figure_metrics(fig, 0.0)
        return graph_component(fig, run_id, strategy), status_panel(context, metrics, "failure"), run_id

    fig, metrics, context = build_animation_payload(
        model_type=model_type,
        system_type=system_type,
        preset_name=preset,
        run_id=run_id,
        identity_strategy=strategy,
    )
    return graph_component(fig, run_id, strategy), status_panel(context, metrics, "run"), run_id


def write_metrics_only() -> None:
    cases = []
    for model_type, system_type in [
        ("simple", "lagrangian"),
        ("simple", "hamiltonian"),
        ("compound", "lagrangian"),
        ("compound", "hamiltonian"),
    ]:
        _, metrics, context = build_animation_payload(
            model_type=model_type,
            system_type=system_type,
            preset_name="nonzero_tail",
            run_id=len(cases) + 1,
            identity_strategy="fixed_graph",
        )
        cases.append({"context": context, "metrics": metrics})

    summary = {
        "tier": "Phase 6 / Tier 3A",
        "purpose": "Compact animation lifecycle preview metrics",
        "manual_reproduction_status": "not automated; use preview app manual script",
        "manual_runs_tested": 0,
        "stale_playback_observed": None,
        "clear_reset_appeared_to_stop_playback": None,
        "failure_state_appeared_to_stop_playback": None,
        "cases": cases,
    }
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Wrote compact Tier 3A metrics: {OUTPUT_PATH}")
    for case in cases:
        context = case["context"]
        metrics = case["metrics"]
        print(
            f"- {context['model_type']} {context['system_type']}: "
            f"frames={metrics['frame_count']} json={metrics['plotly_json_size_bytes']} bytes"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-only", action="store_true")
    args = parser.parse_args()
    if args.metrics_only:
        write_metrics_only()
        return 0

    print(f"Starting Tier 3A preview at http://127.0.0.1:{APP_PORT}/")
    app.run(debug=False, port=APP_PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
