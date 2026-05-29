"""Tier 3D interaction contract preview.

Run from the repository root:

    python development/simulation_workbench/tier_3/tier_3d_interaction_contract/interaction_contract_preview.py

This workbench app simulates interaction state transitions. It does not run the
double-pendulum model and does not promote any renderer into production.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dash import Dash, Input, Output, State, callback_context, dcc, html


APP_PORT = 8066
TIER_DIR = Path(__file__).resolve().parent
RESULTS_PATH = TIER_DIR / "tier3d_results.json"

MODEL_OPTIONS = ["simple", "compound"]
SYSTEM_OPTIONS = ["lagrangian", "hamiltonian"]
PRESETS = {
    "nonzero_tail": "Nonzero velocities",
    "small_angle": "Small angle",
    "wide_swing": "Wide swing",
}
SAMPLE_COUNT = 640
DURATION_SECONDS = 4.0

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


def controls_signature(model_type: str, system_type: str, preset_name: str) -> str:
    return json.dumps(
        {
            "model_type": model_type,
            "system_type": system_type,
            "preset_name": preset_name,
        },
        sort_keys=True,
    )


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": "tier3d.interaction_state.v1",
        "simulation_state": "empty",
        "playback_state": "idle",
        "run_id": 0,
        "payload_run_id": None,
        "selected_frame": 0,
        "selected_time": 0.0,
        "sample_count": 0,
        "duration_seconds": 0.0,
        "controls_signature": None,
        "payload_signature": None,
        "output_status": "empty",
        "message": "No simulation has been run in this preview session.",
        "python_called": False,
        "js_local": False,
        "last_event": "initial page load",
        "warnings": [],
    }


def frame_time(frame: int, sample_count: int, duration_seconds: float) -> float:
    if sample_count <= 1:
        return 0.0
    return duration_seconds * max(0, min(frame, sample_count - 1)) / (sample_count - 1)


def successful_run_state(
    prior: dict[str, Any],
    model_type: str,
    system_type: str,
    preset_name: str,
) -> dict[str, Any]:
    next_run_id = int(prior.get("run_id") or 0) + 1
    signature = controls_signature(model_type, system_type, preset_name)
    return {
        **prior,
        "simulation_state": "success",
        "playback_state": "idle",
        "run_id": next_run_id,
        "payload_run_id": next_run_id,
        "selected_frame": 0,
        "selected_time": 0.0,
        "sample_count": SAMPLE_COUNT,
        "duration_seconds": DURATION_SECONDS,
        "controls_signature": signature,
        "payload_signature": signature,
        "output_status": "active",
        "message": (
            f"Run {next_run_id} completed. Previous playback was cancelled and "
            "the selected frame reset to zero."
        ),
        "python_called": True,
        "js_local": False,
        "last_event": "Run clicked",
        "warnings": [
            "Preview uses simulated state transitions only; it does not run the solver.",
            "Canvas-native synced inspection remains a production candidate, not a final renderer decision.",
        ],
    }


def failure_state(prior: dict[str, Any], failure_kind: str) -> dict[str, Any]:
    next_run_id = int(prior.get("run_id") or 0) + 1
    return {
        **prior,
        "simulation_state": "failed",
        "playback_state": "cancelled",
        "run_id": next_run_id,
        "payload_run_id": None,
        "selected_frame": 0,
        "selected_time": 0.0,
        "sample_count": 0,
        "duration_seconds": 0.0,
        "output_status": "failed",
        "message": f"Run {next_run_id} entered failed state: {failure_kind}. Playback cancelled.",
        "python_called": failure_kind != "validation failure",
        "js_local": False,
        "last_event": failure_kind,
        "warnings": [
            "Failed states must not leave a previous successful animation playing.",
            "A production implementation should show the concrete validation, solver, or rendering error.",
        ],
    }


def state_table(state: dict[str, Any]) -> html.Table:
    keys = [
        "simulation_state",
        "playback_state",
        "run_id",
        "payload_run_id",
        "selected_frame",
        "selected_time",
        "sample_count",
        "output_status",
        "last_event",
        "python_called",
        "js_local",
        "message",
    ]
    return html.Table(
        [
            html.Tr(
                [
                    html.Th(key.replace("_", " "), style={"textAlign": "left", "padding": "5px 12px 5px 0"}),
                    html.Td(str(state.get(key)), style={"padding": "5px 0"}),
                ]
            )
            for key in keys
        ],
        style={"fontSize": "14px", "borderCollapse": "collapse", "width": "100%"},
    )


def state_badge(text: str, color: str) -> html.Span:
    return html.Span(
        text,
        style={
            "display": "inline-block",
            "background": color,
            "color": "white",
            "borderRadius": "999px",
            "padding": "5px 10px",
            "fontSize": "12px",
            "fontWeight": "700",
            "marginRight": "8px",
        },
    )


def output_preview(state: dict[str, Any]) -> html.Div:
    simulation_state = state.get("simulation_state")
    playback_state = state.get("playback_state")
    output_status = state.get("output_status")
    color = {
        "empty": "#596579",
        "active": "#146c43",
        "stale": "#9a6700",
        "failed": "#b42318",
        "cleared": "#596579",
    }.get(output_status, "#596579")

    return html.Div(
        [
            html.Div(
                [
                    state_badge(f"simulation: {simulation_state}", color),
                    state_badge(f"playback: {playback_state}", "#26364f"),
                    state_badge(f"output: {output_status}", color),
                ],
                style={"marginBottom": "12px"},
            ),
            html.Div(
                state.get("message", ""),
                style={
                    "border": f"1px solid {color}",
                    "borderRadius": "8px",
                    "padding": "16px",
                    "background": "#fff",
                    "minHeight": "100px",
                },
            ),
            html.P(
                "Contract: stale, failed, cleared, or superseded output may not keep animating as if current.",
                style={"color": "#596579", "marginBottom": 0},
            ),
        ],
        style=PANEL_STYLE,
    )


def warnings_list(state: dict[str, Any]) -> html.Div:
    warnings = state.get("warnings") or []
    if not warnings:
        return html.Div("No warnings for this state.")
    return html.Ul([html.Li(item) for item in warnings], style={"marginBottom": 0})


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H1("Tier 3D Interaction Contract Preview", style={"marginBottom": "6px"}),
                    html.P(
                        "Workbench-only state machine preview. It demonstrates lifecycle rules without running the solver or promoting a renderer.",
                        style={"color": "#596579"},
                    ),
                    dcc.Store(id="tier3d-state", data=initial_state()),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Model type"),
                                    dcc.RadioItems(
                                        id="tier3d-model-type",
                                        options=[{"label": value.title(), "value": value} for value in MODEL_OPTIONS],
                                        value="simple",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("System type"),
                                    dcc.RadioItems(
                                        id="tier3d-system-type",
                                        options=[{"label": value.title(), "value": value} for value in SYSTEM_OPTIONS],
                                        value="lagrangian",
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("Preset"),
                                    dcc.Dropdown(
                                        id="tier3d-preset",
                                        options=[{"label": label, "value": key} for key, label in PRESETS.items()],
                                        value="nonzero_tail",
                                        clearable=False,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Button("Run", id="tier3d-run", style=BUTTON_STYLE),
                                    html.Button("Clear", id="tier3d-clear", style=SECONDARY_BUTTON_STYLE),
                                ],
                                style={"display": "flex", "gap": "8px", "alignItems": "end"},
                            ),
                        ],
                        style={**PANEL_STYLE, **GRID_STYLE, "marginBottom": "14px"},
                    ),
                    html.Div(
                        [
                            html.Button("Validation Failure", id="tier3d-validation-failure", style=SECONDARY_BUTTON_STYLE),
                            html.Button("Solver Failure", id="tier3d-solver-failure", style=SECONDARY_BUTTON_STYLE),
                            html.Button("Output Failure", id="tier3d-output-failure", style=SECONDARY_BUTTON_STYLE),
                        ],
                        style={**PANEL_STYLE, "display": "flex", "gap": "8px", "marginBottom": "14px"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H3("Playback controls", style={"marginTop": 0}),
                                    html.Div(
                                        [
                                            html.Button("Play", id="tier3d-play", style=BUTTON_STYLE),
                                            html.Button("Pause", id="tier3d-pause", style=SECONDARY_BUTTON_STYLE),
                                            html.Button("Reset Playback", id="tier3d-reset", style=SECONDARY_BUTTON_STYLE),
                                        ],
                                        style={"display": "flex", "gap": "8px", "marginBottom": "18px"},
                                    ),
                                    html.Label("Scrub selected frame"),
                                    dcc.Slider(
                                        id="tier3d-scrub",
                                        min=0,
                                        max=SAMPLE_COUNT - 1,
                                        step=1,
                                        value=0,
                                        marks=None,
                                        tooltip={"placement": "bottom", "always_visible": False},
                                    ),
                                    html.Div(
                                        "Scrubbing pauses playback and drives the shared selected-frame state.",
                                        style=WARNING_STYLE,
                                    ),
                                ],
                                style=PANEL_STYLE,
                            ),
                            html.Div(id="tier3d-output-preview"),
                        ],
                        style={"display": "grid", "gridTemplateColumns": "minmax(340px, 1fr) minmax(340px, 1fr)", "gap": "14px"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H3("Current contract state", style={"marginTop": 0}),
                                    html.Div(id="tier3d-state-table"),
                                ],
                                style=PANEL_STYLE,
                            ),
                            html.Div(
                                [
                                    html.H3("Warnings", style={"marginTop": 0}),
                                    html.Div(id="tier3d-warnings"),
                                ],
                                style=PANEL_STYLE,
                            ),
                        ],
                        style={"display": "grid", "gridTemplateColumns": "minmax(340px, 1fr) minmax(340px, 1fr)", "gap": "14px", "marginTop": "14px"},
                    ),
                ],
                style=SHELL_STYLE,
            )
        ],
        style=PAGE_STYLE,
    )


app = Dash(__name__)
app.title = "Tier 3D Interaction Contract Preview"
app.layout = layout


@app.callback(
    Output("tier3d-state", "data"),
    Output("tier3d-scrub", "value"),
    Input("tier3d-run", "n_clicks"),
    Input("tier3d-clear", "n_clicks"),
    Input("tier3d-validation-failure", "n_clicks"),
    Input("tier3d-solver-failure", "n_clicks"),
    Input("tier3d-output-failure", "n_clicks"),
    Input("tier3d-play", "n_clicks"),
    Input("tier3d-pause", "n_clicks"),
    Input("tier3d-reset", "n_clicks"),
    Input("tier3d-scrub", "value"),
    Input("tier3d-model-type", "value"),
    Input("tier3d-system-type", "value"),
    Input("tier3d-preset", "value"),
    State("tier3d-state", "data"),
)
def transition_state(
    run_clicks,
    clear_clicks,
    validation_failure_clicks,
    solver_failure_clicks,
    output_failure_clicks,
    play_clicks,
    pause_clicks,
    reset_clicks,
    scrub_value,
    model_type,
    system_type,
    preset_name,
    current_state,
):
    del (
        run_clicks,
        clear_clicks,
        validation_failure_clicks,
        solver_failure_clicks,
        output_failure_clicks,
        play_clicks,
        pause_clicks,
        reset_clicks,
    )
    state = dict(current_state or initial_state())
    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""
    current_signature = controls_signature(model_type, system_type, preset_name)

    if triggered_id == "tier3d-run":
        return successful_run_state(state, model_type, system_type, preset_name), 0

    if triggered_id == "tier3d-clear":
        cleared = {
            **state,
            "simulation_state": "cleared",
            "playback_state": "cancelled",
            "payload_run_id": None,
            "selected_frame": 0,
            "selected_time": 0.0,
            "sample_count": 0,
            "duration_seconds": 0.0,
            "output_status": "cleared",
            "message": "Output intentionally cleared. Playback cancelled and no active payload remains.",
            "python_called": False,
            "js_local": True,
            "last_event": "Clear clicked",
            "warnings": ["Cleared output should not be confused with a failed solve."],
        }
        return cleared, 0

    if triggered_id == "tier3d-validation-failure":
        return failure_state(state, "validation failure"), 0

    if triggered_id == "tier3d-solver-failure":
        return failure_state(state, "solver failure"), 0

    if triggered_id == "tier3d-output-failure":
        return failure_state(state, "output generation failure"), 0

    if triggered_id in {"tier3d-model-type", "tier3d-system-type", "tier3d-preset"}:
        if state.get("simulation_state") == "success" and state.get("payload_signature") != current_signature:
            stale = {
                **state,
                "simulation_state": "stale",
                "playback_state": "cancelled",
                "controls_signature": current_signature,
                "output_status": "stale",
                "message": "Settings changed since the last successful run. Existing output remains inspectable but is no longer current; rerun to update.",
                "python_called": False,
                "js_local": True,
                "last_event": "Input changed after success",
                "warnings": [
                    "Stale output must be visually distinguishable from current output.",
                    "Animation is stopped so stale motion cannot masquerade as current settings.",
                ],
            }
            return stale, int(state.get("selected_frame") or 0)
        return {**state, "controls_signature": current_signature}, int(state.get("selected_frame") or 0)

    if triggered_id == "tier3d-play":
        if state.get("simulation_state") == "success" and state.get("output_status") == "active":
            next_state = {
                **state,
                "playback_state": "playing",
                "message": "Playback started for the active run.",
                "python_called": False,
                "js_local": True,
                "last_event": "Play clicked",
            }
            return next_state, int(state.get("selected_frame") or 0)
        blocked = {
            **state,
            "playback_state": "cancelled" if state.get("simulation_state") in {"failed", "cleared", "stale"} else state.get("playback_state"),
            "message": "Play is blocked unless there is an active successful payload.",
            "python_called": False,
            "js_local": True,
            "last_event": "Play clicked",
        }
        return blocked, int(state.get("selected_frame") or 0)

    if triggered_id == "tier3d-pause":
        paused = {
            **state,
            "playback_state": "paused" if state.get("sample_count", 0) else "idle",
            "message": "Playback paused; selected frame is preserved.",
            "python_called": False,
            "js_local": True,
            "last_event": "Pause clicked",
        }
        return paused, int(state.get("selected_frame") or 0)

    if triggered_id == "tier3d-reset":
        reset = {
            **state,
            "playback_state": "idle" if state.get("simulation_state") == "success" else "cancelled",
            "selected_frame": 0,
            "selected_time": 0.0,
            "message": "Selected frame reset to zero.",
            "python_called": False,
            "js_local": True,
            "last_event": "Reset playback clicked",
        }
        return reset, 0

    if triggered_id == "tier3d-scrub":
        frame = int(scrub_value or 0)
        if state.get("sample_count", 0) > 0 and state.get("simulation_state") in {"success", "stale"}:
            scrubbed = {
                **state,
                "playback_state": "scrubbing",
                "selected_frame": frame,
                "selected_time": frame_time(frame, int(state.get("sample_count") or 0), float(state.get("duration_seconds") or 0.0)),
                "message": "Scrub selected frame. Playback is paused by scrub interaction.",
                "python_called": False,
                "js_local": True,
                "last_event": "Scrub",
            }
            return scrubbed, frame
        blocked_scrub = {
            **state,
            "message": "Scrub has no effect without an inspectable successful or stale payload.",
            "python_called": False,
            "js_local": True,
            "last_event": "Scrub",
        }
        return blocked_scrub, 0

    return state, int(state.get("selected_frame") or 0)


@app.callback(
    Output("tier3d-state-table", "children"),
    Output("tier3d-output-preview", "children"),
    Output("tier3d-warnings", "children"),
    Input("tier3d-state", "data"),
)
def render_state(state):
    state = state or initial_state()
    return state_table(state), output_preview(state), warnings_list(state)


def write_results() -> None:
    summary = {
        "tier": "Phase 6 / Tier 3D",
        "purpose": "Compact interaction-contract preview summary; no solver arrays or renderer artifacts.",
        "preview_port": APP_PORT,
        "simulation_states": ["empty", "running", "success", "stale", "failed", "cleared"],
        "playback_states": ["idle", "playing", "paused", "scrubbing", "ended", "cancelled"],
        "accepted_rules": [
            "No visual state may continue animating after its simulation result has been superseded.",
            "Input changes after success mark output stale and cancel playback.",
            "Clear and failure states cancel playback and remove active payload.",
            "Selected frame is shared across motion, time-series cursor, projection marker, and readout.",
        ],
        "preview_scope": "State transition demonstration only; no production code and no numerical solve.",
    }
    RESULTS_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Wrote compact Tier 3D results: {RESULTS_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-only", action="store_true")
    args = parser.parse_args()
    if args.results_only:
        write_results()
        return 0

    print(f"Starting Tier 3D interaction preview at http://127.0.0.1:{APP_PORT}/")
    app.run(debug=False, port=APP_PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
