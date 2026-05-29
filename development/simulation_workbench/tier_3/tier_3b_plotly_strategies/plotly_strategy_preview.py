"""Tier 3B Plotly motion strategy preview.

Run from the repository root:

    python development/simulation_workbench/tier_3/tier_3b_plotly_strategies/plotly_strategy_preview.py

Optional compact metrics only:

    python development/simulation_workbench/tier_3/tier_3b_plotly_strategies/plotly_strategy_preview.py --metrics-only
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


APP_PORT = 8064
OUTPUT_PATH = Path(__file__).with_name("tier3b_results.json")

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

CASES = {
    "short_simple_lagrangian": {
        "label": "Short simple Lagrangian",
        "model_type": "simple",
        "system_type": "lagrangian",
        "preset": "nonzero_tail",
        "duration_seconds": 4.0,
        "sample_count": 640,
    },
    "moderate_compound_hamiltonian": {
        "label": "Moderate compound Hamiltonian",
        "model_type": "compound",
        "system_type": "hamiltonian",
        "preset": "nonzero_tail",
        "duration_seconds": 6.0,
        "sample_count": 1200,
    },
    "larger_simple_lagrangian": {
        "label": "Larger simple Lagrangian",
        "model_type": "simple",
        "system_type": "lagrangian",
        "preset": "small_angle",
        "duration_seconds": 8.0,
        "sample_count": 2000,
    },
}

STRATEGIES = {
    "current_frames": {
        "label": "Current Plotly frames",
        "description": "Existing animate_pendulum output with frame step 10.",
    },
    "reduced_frames": {
        "label": "Reduced Plotly frames",
        "description": "Workbench-only Plotly frames using a coarser frame step.",
    },
    "static_scrubber": {
        "label": "Plotly static scrubber",
        "description": "No frames; Plotly slider updates the pendulum trace.",
    },
    "selected_frame_server": {
        "label": "Server-selected frame",
        "description": "No Plotly frames; Dash selects a single static frame.",
    },
}

PAGE_STYLE = {
    "fontFamily": "Arial, sans-serif",
    "background": "#f6f7fb",
    "color": "#1d2433",
    "minHeight": "100vh",
    "padding": "24px",
}
SHELL_STYLE = {"maxWidth": "1220px", "margin": "0 auto"}
PANEL_STYLE = {
    "background": "white",
    "border": "1px solid #d9dee8",
    "borderRadius": "8px",
    "padding": "16px",
    "boxShadow": "0 1px 2px rgba(16, 24, 40, 0.04)",
}
GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(250px, 1fr))",
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


def build_model_for_case(case: dict[str, Any]):
    model_type = case["model_type"]
    system_type = case["system_type"]
    preset = PRESETS[case["preset"]]
    time_vector = [0.0, case["duration_seconds"], case["sample_count"]]
    model_class = model_class_for_system(system_type)

    def construct():
        model = model_class(
            parameters_for_model(model_type),
            list(preset["initial_conditions"]),
            time_vector,
            model=model_type,
        )
        model.precompute_positions()
        return model

    return timed_call(construct)


def empty_figure(title: str, body: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[
            {
                "text": body,
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
        margin=dict(l=20, r=20, t=48, b=24),
    )
    return fig


def base_motion_figure(model, title: str) -> go.Figure:
    x1, y1, x2, y2 = model.precomputed_positions
    max_extent = max(
        abs(x1).max(),
        abs(y1).max(),
        abs(x2).max(),
        abs(y2).max(),
    )
    padding = 0.1 * max_extent
    axis_range = [-max_extent - padding, max_extent + padding]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[0, x1[0], x2[0]],
            y=[0, y1[0], y2[0]],
            mode="lines+markers",
            name="Pendulum",
            line=dict(width=2, color="#4410AD"),
            marker=dict(size=10, color="#4410AD"),
        )
    )
    fig.add_trace(
        go.Scatter(x=x1, y=y1, mode="lines", name="Path P1", line=dict(width=1, color="#F4762F"))
    )
    fig.add_trace(
        go.Scatter(x=x2, y=y2, mode="lines", name="Path P2", line=dict(width=1, color="#4EC5AE"))
    )
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            range=axis_range,
            autorange=False,
            zeroline=False,
            showgrid=True,
            gridcolor="rgba(0, 0, 0, 0.1)",
        ),
        yaxis=dict(
            range=axis_range,
            autorange=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1,
            showgrid=True,
            gridcolor="rgba(0, 0, 0, 0.1)",
        ),
        autosize=False,
        width=640,
        height=520,
        margin=dict(l=20, r=20, t=48, b=24),
        showlegend=False,
    )
    return fig


def add_play_button(fig: go.Figure, frame_duration_ms: int = 33) -> None:
    fig.update_layout(
        updatemenus=[
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": frame_duration_ms, "redraw": True},
                                "fromcurrent": True,
                                "mode": "immediate",
                            },
                        ],
                    }
                ],
                "direction": "left",
                "pad": {"r": 10, "t": 10},
                "showactive": False,
                "x": 0.05,
                "y": 0.95,
                "xanchor": "left",
                "yanchor": "top",
            }
        ]
    )


def build_current_frames(model, title: str) -> go.Figure:
    fig = model.animate_pendulum(trace=True, fig_width=640, fig_height=520, static=False)
    fig.update_layout(title=title, margin=dict(l=20, r=20, t=48, b=24), showlegend=False)
    return fig


def build_reduced_frames(model, title: str, frame_step: int = 25) -> go.Figure:
    x1, y1, x2, y2 = model.precomputed_positions
    fig = base_motion_figure(model, title)
    fig.frames = [
        go.Frame(
            data=[
                go.Scatter(
                    x=[0, x1[index], x2[index]],
                    y=[0, y1[index], y2[index]],
                    mode="lines+markers",
                    line=dict(width=2, color="#4410AD"),
                    marker=dict(size=10, color="#4410AD"),
                )
            ],
            name=str(index),
        )
        for index in range(0, len(x1), frame_step)
    ]
    add_play_button(fig)
    return fig


def build_static_scrubber(model, title: str, slider_step: int = 20) -> go.Figure:
    x1, y1, x2, y2 = model.precomputed_positions
    fig = base_motion_figure(model, title)
    steps = []
    for index in range(0, len(x1), slider_step):
        steps.append(
            {
                "label": str(index),
                "method": "restyle",
                "args": [
                    {
                        "x": [[0, x1[index], x2[index]]],
                        "y": [[0, y1[index], y2[index]]],
                    },
                    [0],
                ],
            }
        )
    fig.update_layout(
        sliders=[
            {
                "active": 0,
                "steps": steps,
                "currentvalue": {"prefix": "sample "},
                "pad": {"t": 38},
            }
        ]
    )
    return fig


def build_selected_frame(model, title: str, selected_index: int = 0) -> go.Figure:
    x1, y1, x2, y2 = model.precomputed_positions
    selected_index = max(0, min(int(selected_index), len(x1) - 1))
    fig = base_motion_figure(model, f"{title} - sample {selected_index}")
    fig.data[0].x = [0, x1[selected_index], x2[selected_index]]
    fig.data[0].y = [0, y1[selected_index], y2[selected_index]]
    return fig


def figure_point_count(fig: go.Figure) -> int:
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


def slider_step_count(fig: go.Figure) -> int:
    sliders = getattr(fig.layout, "sliders", None)
    if not sliders:
        return 0
    return int(sum(len(slider.steps or []) for slider in sliders))


def figure_metrics(fig: go.Figure, build_time_seconds: float) -> dict[str, Any]:
    return {
        "build_time_seconds": build_time_seconds,
        "trace_count": len(getattr(fig, "data", []) or []),
        "frame_count": len(getattr(fig, "frames", []) or []),
        "slider_step_count": slider_step_count(fig),
        "point_count": figure_point_count(fig),
        "plotly_json_size_bytes": len(fig.to_json()),
    }


def build_strategy_figure(model, strategy: str, title: str, selected_index: int = 0):
    if strategy == "current_frames":
        return timed_call(lambda: build_current_frames(model, title))
    if strategy == "reduced_frames":
        return timed_call(lambda: build_reduced_frames(model, title))
    if strategy == "static_scrubber":
        return timed_call(lambda: build_static_scrubber(model, title))
    if strategy == "selected_frame_server":
        return timed_call(lambda: build_selected_frame(model, title, selected_index))
    raise ValueError(f"Unsupported strategy: {strategy}")


def strategy_payload(case_id: str, strategy: str, run_id: int, selected_index: int = 0):
    case = CASES[case_id]
    model, model_time = build_model_for_case(case)
    title = f"Run {run_id}: {case['label']} - {STRATEGIES[strategy]['label']}"
    fig, figure_time = build_strategy_figure(model, strategy, title, selected_index)
    metrics = figure_metrics(fig, figure_time)
    metrics["model_construction_seconds"] = model_time
    metrics["total_python_seconds"] = model_time + figure_time
    context = {
        "run_id": run_id,
        "case_id": case_id,
        "case_label": case["label"],
        "strategy": strategy,
        "strategy_label": STRATEGIES[strategy]["label"],
        "model_type": case["model_type"],
        "system_type": case["system_type"],
        "preset": case["preset"],
        "duration_seconds": case["duration_seconds"],
        "sample_count": case["sample_count"],
        "selected_index": selected_index if strategy == "selected_frame_server" else None,
        "graph_identity": "unique graph per run",
        "solver_success": getattr(model.solver_metadata, "success", None),
        "solver_state_convention": getattr(model, "solver_state_convention", None),
    }
    return fig, metrics, context


def graph_component(fig: go.Figure, run_id: int, strategy: str) -> dcc.Graph:
    return dcc.Graph(
        id=f"tier3b-motion-{strategy}-{run_id}",
        figure=fig,
        config={"displayModeBar": False},
        style={"height": "560px"},
    )


def status_panel(context: dict[str, Any], metrics: dict[str, Any], action: str) -> html.Table:
    rows = {**context, **{f"metric_{key}": value for key, value in metrics.items()}, "last_action": action}
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


def slider_control(case_id: str, strategy: str, selected_index: int = 0):
    if strategy != "selected_frame_server":
        return html.Div(
            [
                html.Div(
                    "Only the server-selected frame strategy uses the Dash frame slider.",
                    style={"color": "#596579", "fontSize": "13px"},
                ),
                dcc.Slider(id="tier3b-selected-index", min=0, max=1, step=1, value=0, disabled=True),
            ]
        )
    case = CASES[case_id]
    step = max(1, case["sample_count"] // 100)
    return html.Div(
        [
            html.Label("Selected sample"),
            dcc.Slider(
                id="tier3b-selected-index",
                min=0,
                max=case["sample_count"] - 1,
                step=step,
                value=selected_index,
                marks=None,
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ]
    )


def guidance_card() -> html.Div:
    return html.Div(
        [
            html.H3("Manual comparison script", style={"marginTop": 0}),
            html.Ol(
                [
                    html.Li("Run each strategy for the same case and compare payload metrics."),
                    html.Li("For frame strategies, press Plotly Play and observe responsiveness."),
                    html.Li("Use Clear Output during playback and confirm old motion stops."),
                    html.Li("For selected-frame mode, scrub the Dash slider and observe latency."),
                    html.Li("Compare short, moderate, and larger sample-count cases."),
                ]
            ),
            html.Div(
                "Tier 3B inherits the Tier 3A fix: graph identity is unique per run. This preview compares Plotly motion strategies, not new model behavior.",
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
                    html.H1("Tier 3B Plotly Strategy Preview", style={"marginBottom": "6px"}),
                    html.P(
                        "Workbench-only comparison of Plotly motion rendering strategies. Production /simulation is untouched.",
                        style={"color": "#596579"},
                    ),
                    dcc.Store(id="tier3b-run-counter", data=0),
                    dcc.Store(id="tier3b-active-request", data=None),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Case"),
                                    dcc.Dropdown(
                                        id="tier3b-case",
                                        options=[
                                            {"label": case["label"], "value": key}
                                            for key, case in CASES.items()
                                        ],
                                        value="short_simple_lagrangian",
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("Strategy"),
                                    dcc.Dropdown(
                                        id="tier3b-strategy",
                                        options=[
                                            {"label": value["label"], "value": key}
                                            for key, value in STRATEGIES.items()
                                        ],
                                        value="current_frames",
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Button("Run Strategy", id="tier3b-run", style=BUTTON_STYLE),
                                    html.Button("Clear Output", id="tier3b-clear", style=SECONDARY_BUTTON_STYLE),
                                    html.Button("Simulated Failure", id="tier3b-failure", style=SECONDARY_BUTTON_STYLE),
                                ],
                                style={"display": "flex", "gap": "8px", "alignItems": "end"},
                            ),
                        ],
                        style={**PANEL_STYLE, **GRID_STYLE, "marginBottom": "14px"},
                    ),
                    html.Div(id="tier3b-slider-shell", children=slider_control("short_simple_lagrangian", "current_frames")),
                    html.Div(
                        [
                            html.Div(
                                id="tier3b-motion-shell",
                                children=graph_component(
                                    empty_figure("No strategy run", "Run a strategy to inspect Plotly payload and interaction."),
                                    0,
                                    "empty",
                                ),
                                style=PANEL_STYLE,
                            ),
                            html.Div(
                                [
                                    html.Div(id="tier3b-status", children="No run yet."),
                                    html.Br(),
                                    guidance_card(),
                                ],
                                style={"display": "grid", "gap": "14px"},
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "minmax(420px, 2fr) minmax(320px, 1fr)",
                            "gap": "14px",
                            "alignItems": "start",
                            "marginTop": "14px",
                        },
                    ),
                ],
                style=SHELL_STYLE,
            )
        ],
        style=PAGE_STYLE,
    )


app = Dash(__name__)
app.title = "Tier 3B Plotly Strategy Preview"
app.layout = app_layout


@app.callback(
    Output("tier3b-motion-shell", "children"),
    Output("tier3b-status", "children"),
    Output("tier3b-run-counter", "data"),
    Output("tier3b-active-request", "data"),
    Output("tier3b-slider-shell", "children"),
    Input("tier3b-run", "n_clicks"),
    Input("tier3b-clear", "n_clicks"),
    Input("tier3b-failure", "n_clicks"),
    Input("tier3b-selected-index", "value"),
    State("tier3b-case", "value"),
    State("tier3b-strategy", "value"),
    State("tier3b-run-counter", "data"),
    State("tier3b-active-request", "data"),
    prevent_initial_call=True,
)
def update_preview(
    run_clicks,
    clear_clicks,
    failure_clicks,
    selected_index,
    case_id,
    strategy,
    run_counter,
    active_request,
):
    del run_clicks, clear_clicks, failure_clicks
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]
    run_id = int(run_counter or 0)

    if triggered_id == "tier3b-selected-index":
        if not active_request or active_request.get("strategy") != "selected_frame_server":
            return (
                graph_component(empty_figure("No selected-frame run", "Run selected-frame mode before scrubbing."), run_id, "empty"),
                "No selected-frame run to scrub.",
                run_id,
                active_request,
                slider_control(case_id, strategy),
            )
        case_id = active_request["case_id"]
        strategy = active_request["strategy"]
        run_id = active_request["run_id"]
        fig, metrics, context = strategy_payload(case_id, strategy, run_id, selected_index or 0)
        return (
            graph_component(fig, run_id, strategy),
            status_panel(context, metrics, "scrub selected frame"),
            run_id,
            active_request,
            slider_control(case_id, strategy, selected_index or 0),
        )

    run_id += 1

    if triggered_id == "tier3b-clear":
        fig = empty_figure(f"Run {run_id}: cleared", "Cleared. Old Plotly playback should stop.")
        context = {"run_id": run_id, "graph_identity": "unique graph per run", "strategy": "clear"}
        metrics = figure_metrics(fig, 0.0)
        return (
            graph_component(fig, run_id, "clear"),
            status_panel(context, metrics, "clear"),
            run_id,
            None,
            slider_control(case_id, strategy),
        )

    if triggered_id == "tier3b-failure":
        fig = empty_figure(f"Run {run_id}: simulated failure", "Failure preview. Old animation must not continue.")
        context = {"run_id": run_id, "graph_identity": "unique graph per run", "strategy": "failure"}
        metrics = figure_metrics(fig, 0.0)
        return (
            graph_component(fig, run_id, "failure"),
            status_panel(context, metrics, "failure"),
            run_id,
            None,
            slider_control(case_id, strategy),
        )

    fig, metrics, context = strategy_payload(case_id, strategy, run_id, selected_index or 0)
    active_request = {"case_id": case_id, "strategy": strategy, "run_id": run_id}
    return (
        graph_component(fig, run_id, strategy),
        status_panel(context, metrics, "run strategy"),
        run_id,
        active_request,
        slider_control(case_id, strategy, selected_index or 0),
    )


def collect_metrics() -> dict[str, Any]:
    cases = []
    for case_id in CASES:
        case = CASES[case_id]
        model, model_time = build_model_for_case(case)
        strategy_results = []
        for strategy in STRATEGIES:
            title = f"{case['label']} - {STRATEGIES[strategy]['label']}"
            fig, figure_time = build_strategy_figure(model, strategy, title)
            metrics = figure_metrics(fig, figure_time)
            metrics["model_construction_seconds"] = model_time
            metrics["total_python_seconds_if_model_reused"] = model_time + figure_time
            strategy_results.append(
                {
                    "strategy": strategy,
                    "strategy_label": STRATEGIES[strategy]["label"],
                    "metrics": metrics,
                }
            )
        cases.append(
            {
                "case_id": case_id,
                "case": case,
                "solver_success": getattr(model.solver_metadata, "success", None),
                "solver_state_convention": getattr(model, "solver_state_convention", None),
                "strategies": strategy_results,
            }
        )

    return {
        "tier": "Phase 6 / Tier 3B",
        "purpose": "Compact Plotly motion strategy metrics",
        "graph_identity_policy": "unique graph per run inherited from Tier 3A",
        "manual_observation_status": "metrics generated; browser responsiveness remains manual",
        "strategies": STRATEGIES,
        "cases": cases,
    }


def write_metrics_only() -> None:
    summary = collect_metrics()
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Wrote compact Tier 3B metrics: {OUTPUT_PATH}")
    for case_result in summary["cases"]:
        print(f"- {case_result['case_id']}")
        for strategy_result in case_result["strategies"]:
            metrics = strategy_result["metrics"]
            print(
                f"  {strategy_result['strategy']}: "
                f"frames={metrics['frame_count']} "
                f"slider_steps={metrics['slider_step_count']} "
                f"json={metrics['plotly_json_size_bytes']} bytes "
                f"figure={metrics['build_time_seconds']:.4f}s"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics-only", action="store_true")
    args = parser.parse_args()
    if args.metrics_only:
        write_metrics_only()
        return 0

    print(f"Starting Tier 3B preview at http://127.0.0.1:{APP_PORT}/")
    app.run(debug=False, port=APP_PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
