"""Standalone Stage 1 nearby-trajectory teaching prototype.

Run from the repository root with:

    uv run python development/chaos_content/prototypes/
        initial_condition_sensitivity/app.py

This module imports accepted model code from ``src/``. Production code does
not import this prototype.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from dash import ClientsideFunction, Dash, Input, Output, State, ctx, dcc, html, no_update


PROTOTYPE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_REFERENCE_SOLVER_POLICY,
    DoublePendulumLagrangian,
)


PAYLOAD_SCHEMA = "stage1_sensitivity_prototype.v1"
PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
OUTPUT_RATE_HZ = 100
ENERGY_DRIFT_LIMIT = 1e-6
MIN_DURATION_SECONDS = 2.0
MAX_DURATION_SECONDS = 40.0
PRESETS: dict[str, dict[str, Any]] = {
    "small_angle": {
        "label": "Small angle",
        "state": [10.0, 10.0, 0.0, 0.0],
    },
    "regular_control": {
        "label": "Regular control",
        "state": [0.0, 120.0, 0.0, 0.0],
    },
    "bounded_nonlinear": {
        "label": "Nonlinear release",
        "state": [45.0, 60.0, 0.0, 0.0],
    },
    "near_inverted": {
        "label": "Near inverted",
        "state": [179.0, 179.0, 0.0, 0.0],
    },
}


def _format_number(value: float) -> str:
    if value == 0:
        return "0"
    if abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _error_payload(message: str, details: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": PAYLOAD_SCHEMA,
        "status": "failed",
        "message": message,
        "errors": details or [],
        "rendering": {"drawable": False, "autoplay_allowed": False},
    }


def _validate_state_and_duration(
    state_degrees: list[float], duration_seconds: float
) -> list[str]:
    issues: list[str] = []
    state = np.asarray(state_degrees, dtype=float)
    if state.shape != (4,) or not np.all(np.isfinite(state)):
        issues.append("All four initial-state values must be finite numbers.")
        return issues
    if np.any(np.abs(state[:2]) > 360.0):
        issues.append("Prototype angles must lie between -360° and 360°.")
    if np.any(np.abs(state[2:]) > 1000.0):
        issues.append("Prototype angular velocities must lie between -1000°/s and 1000°/s.")
    if not math.isfinite(duration_seconds) or not (
        MIN_DURATION_SECONDS <= duration_seconds <= MAX_DURATION_SECONDS
    ):
        issues.append(
            f"Duration must lie between {MIN_DURATION_SECONDS:g} and "
            f"{MAX_DURATION_SECONDS:g} seconds."
        )
    return issues


def _energy_scale() -> float:
    return float(PARAMETERS[g]) * (
        (float(PARAMETERS[m1]) + float(PARAMETERS[m2])) * float(PARAMETERS[l1])
        + float(PARAMETERS[m2]) * float(PARAMETERS[l2])
    )


def _simple_energy(state: np.ndarray) -> np.ndarray:
    theta1 = state[:, 0]
    theta2 = state[:, 1]
    omega1 = state[:, 2]
    omega2 = state[:, 3]
    length1 = float(PARAMETERS[l1])
    length2 = float(PARAMETERS[l2])
    mass1 = float(PARAMETERS[m1])
    mass2 = float(PARAMETERS[m2])
    gravity = float(PARAMETERS[g])

    kinetic = (
        0.5 * (mass1 + mass2) * length1**2 * omega1**2
        + 0.5 * mass2 * length2**2 * omega2**2
        + mass2
        * length1
        * length2
        * omega1
        * omega2
        * np.cos(theta1 - theta2)
    )
    potential = -(
        (mass1 + mass2) * gravity * length1 * np.cos(theta1)
        + mass2 * gravity * length2 * np.cos(theta2)
    )
    return np.asarray(kinetic + potential, dtype=float)


def _integrate_one(
    label: str, initial_state_degrees: list[float], duration_seconds: float
) -> dict[str, Any]:
    sample_count = int(round(duration_seconds * OUTPUT_RATE_HZ)) + 1
    requested_time = np.linspace(0.0, duration_seconds, sample_count)
    issues: list[str] = []
    try:
        model = DoublePendulumLagrangian(
            PARAMETERS,
            initial_state_degrees,
            [0.0, duration_seconds, sample_count],
            model="simple",
            solver_policy=SIMPLE_REFERENCE_SOLVER_POLICY,
        )
    except Exception as exc:  # pragma: no cover - defensive app boundary
        return {"accepted": False, "issues": [f"Integration failed: {exc}"], "label": label}

    metadata = model.solver_metadata
    state = np.asarray(model.sol, dtype=float)
    returned_time = np.asarray(model.solver_time, dtype=float)
    if metadata.success is not True:
        issues.append(f"Solver did not complete: {metadata.message}")
    if metadata.returned_time_matches_requested is not True:
        issues.append("Solver output did not match every requested playback time.")
    if returned_time.shape != requested_time.shape or not np.array_equal(
        returned_time, requested_time
    ):
        issues.append("Solver output was incomplete or time-misaligned.")
    if state.shape != (sample_count, 4):
        issues.append(f"Unexpected state shape: {state.shape}.")
    if not np.all(np.isfinite(state)):
        issues.append("Solver returned non-finite state values.")

    positions = np.empty((4, 0), dtype=float)
    energies = np.array([], dtype=float)
    max_energy_drift: float | None = None
    if not issues:
        model.precompute_positions()
        positions = np.asarray(model.precomputed_positions, dtype=float)
        if positions.shape != (4, sample_count):
            issues.append(f"Unexpected position shape: {positions.shape}.")
        elif not np.all(np.isfinite(positions)):
            issues.append("Position calculation returned non-finite values.")

    if not issues:
        energies = _simple_energy(state)
        drift = np.abs(energies - energies[0]) / _energy_scale()
        if not np.all(np.isfinite(energies)) or not np.all(np.isfinite(drift)):
            issues.append("Energy diagnostic returned non-finite values.")
        else:
            max_energy_drift = float(np.max(drift))
            if max_energy_drift > ENERGY_DRIFT_LIMIT:
                issues.append(
                    "Prototype energy check failed: "
                    f"{max_energy_drift:.3e} > {ENERGY_DRIFT_LIMIT:.1e}."
                )

    return {
        "accepted": not issues,
        "issues": issues,
        "label": label,
        "time": returned_time,
        "state": state,
        "positions": positions,
        "initial_energy_joules": float(energies[0]) if len(energies) else None,
        "max_normalized_energy_drift": max_energy_drift,
        "solver_metadata": metadata.to_dict(),
    }


def build_simulation_payload(
    original_state_degrees: list[float],
    nearby_state_degrees: list[float],
    duration_seconds: float,
    perturbation: dict[str, Any],
) -> dict[str, Any]:
    duration_seconds = float(duration_seconds)
    issues = _validate_state_and_duration(original_state_degrees, duration_seconds)
    issues.extend(_validate_state_and_duration(nearby_state_degrees, duration_seconds))
    if issues:
        return _error_payload("Please revise the prototype inputs and try again.", issues)

    original = _integrate_one("original", original_state_degrees, duration_seconds)
    nearby = _integrate_one("nearby", nearby_state_degrees, duration_seconds)
    trajectories = (original, nearby)
    if not all(item["accepted"] for item in trajectories):
        errors = [
            f"{item['label']}: {issue}"
            for item in trajectories
            for issue in item.get("issues", [])
        ]
        return _error_payload(
            "This run did not pass the prototype numerical checks and will not be animated.",
            errors,
        )

    if not np.array_equal(original["time"], nearby["time"]):
        return _error_payload(
            "The trajectories were not returned on the same playback timeline."
        )

    total_length = float(PARAMETERS[l1] + PARAMETERS[l2])
    original_positions = original["positions"]
    nearby_positions = nearby["positions"]
    separation_metres = np.hypot(
        original_positions[2] - nearby_positions[2],
        original_positions[3] - nearby_positions[3],
    )
    separation_normalized = separation_metres / total_length
    if not np.all(np.isfinite(separation_normalized)):
        return _error_payload("The separation diagnostic contained non-finite values.")

    sample_count = len(original["time"])
    return {
        "schema_version": PAYLOAD_SCHEMA,
        "status": "success",
        "message": "Both trajectories are ready for synchronized playback.",
        "rendering": {"drawable": True, "autoplay_allowed": True},
        "model": "simple point-mass double pendulum",
        "formulation": "Euler-Lagrange",
        "time_s": original["time"].tolist(),
        "sample_count": sample_count,
        "duration_seconds": duration_seconds,
        "output_rate_hz": OUTPUT_RATE_HZ,
        "parameters_si": {str(symbol): float(value) for symbol, value in PARAMETERS.items()},
        "total_length_metres": total_length,
        "original": {
            "initial_state_degrees": [float(value) for value in original_state_degrees],
            "x1": original_positions[0].tolist(),
            "y1": original_positions[1].tolist(),
            "x2": original_positions[2].tolist(),
            "y2": original_positions[3].tolist(),
            "initial_energy_joules": original["initial_energy_joules"],
            "max_normalized_energy_drift": original["max_normalized_energy_drift"],
            "solver_metadata": original["solver_metadata"],
        },
        "nearby": {
            "initial_state_degrees": [float(value) for value in nearby_state_degrees],
            "x1": nearby_positions[0].tolist(),
            "y1": nearby_positions[1].tolist(),
            "x2": nearby_positions[2].tolist(),
            "y2": nearby_positions[3].tolist(),
            "initial_energy_joules": nearby["initial_energy_joules"],
            "max_normalized_energy_drift": nearby["max_normalized_energy_drift"],
            "solver_metadata": nearby["solver_metadata"],
        },
        "separation_normalized": separation_normalized.tolist(),
        "separation_metres": separation_metres.tolist(),
        "max_normalized_separation": float(np.max(separation_normalized)),
        "max_separation_metres": float(np.max(separation_metres)),
        "perturbation": perturbation,
        "prototype_numerical_policy": {
            "name": SIMPLE_REFERENCE_SOLVER_POLICY.name,
            "method": SIMPLE_REFERENCE_SOLVER_POLICY.method,
            "rtol": SIMPLE_REFERENCE_SOLVER_POLICY.rtol,
            "atol": SIMPLE_REFERENCE_SOLVER_POLICY.atol,
            "maximum_normalized_energy_drift": ENERGY_DRIFT_LIMIT,
        },
    }


def _angle_input(component: str, label: str, value: float) -> html.Div:
    return html.Div(
        className="prototype-angle-field",
        children=[
            html.Label(label, htmlFor=f"prototype-{component}"),
            html.Div(
                className="prototype-unit-input",
                children=[
                    dcc.Input(
                        id=f"prototype-{component}",
                        type="number",
                        value=value,
                        min=-360,
                        max=360,
                        step=0.1,
                        debounce=False,
                    ),
                    html.Span("°"),
                ],
            ),
        ],
    )


def _state_disclosure(data: dict[str, Any] | None) -> html.Div:
    if not data or not data.get("valid"):
        return html.Div("Enter valid angles and a positive perturbation.")
    base = data["original_state_degrees"]
    nearby = data["nearby_state_degrees"]
    return html.Div(
        children=[
            html.Div(
                className="prototype-pair-row",
                children=[
                    html.Strong("Original"),
                    html.Span(f"θ₁ = {_format_number(base[0])}°"),
                    html.Span(f"θ₂ = {_format_number(base[1])}°"),
                ],
            ),
            html.Div(
                className="prototype-pair-row prototype-nearby-row",
                children=[
                    html.Strong("Nearby"),
                    html.Span(f"θ₁ = {_format_number(nearby[0])}°"),
                    html.Span(f"θ₂ = {_format_number(nearby[1])}°"),
                ],
            ),
        ]
    )


def build_layout() -> html.Div:
    default = PRESETS["regular_control"]["state"]
    return html.Div(
        id="prototype-root",
        children=[
            dcc.Store(id="prototype-simulation-store"),
            dcc.Store(id="prototype-render-hook"),
            dcc.Store(id="prototype-mode-hook"),
            dcc.Store(id="prototype-speed-hook"),
            dcc.Store(id="prototype-stale-hook"),
            html.Header(
                className="prototype-header",
                children=[
                    html.H1("Initial condition sensitivity"),
                    html.P(
                        "Release two nearly identical double pendulums from rest and compare their motion.",
                        className="prototype-lede",
                    ),
                ],
            ),
            html.Main(
                className="prototype-shell",
                children=[
                    html.Section(
                        className="prototype-controls",
                        children=[
                            html.Div(
                                className="prototype-angle-grid",
                                children=[
                                    _angle_input("theta1", "θ₁", default[0]),
                                    _angle_input("theta2", "θ₂", default[1]),
                                    html.Div(
                                        className="prototype-perturb-field",
                                        children=[
                                            html.Label(
                                                "Perturb θ₂ by",
                                                htmlFor="prototype-perturb-magnitude",
                                            ),
                                            html.Div(
                                                className="prototype-unit-input prototype-perturb-input",
                                                children=[
                                                    html.Span("+", className="prototype-unit-prefix"),
                                                    dcc.Input(
                                                        id="prototype-perturb-magnitude",
                                                        type="number",
                                                        value=0.001,
                                                        min=0.000001,
                                                        max=0.1,
                                                        step="any",
                                                    ),
                                                    html.Span("°"),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                id="prototype-state-disclosure",
                                className="prototype-state-disclosure",
                            ),
                            html.Div(
                                className="prototype-shortcuts",
                                children=[
                                    html.Span("Try:"),
                                    *[
                                        html.Button(
                                            item["label"],
                                            id=f"prototype-preset-{name}",
                                            className="prototype-preset-button",
                                            n_clicks=0,
                                        )
                                        for name, item in PRESETS.items()
                                    ],
                                    html.Div(
                                        className="prototype-duration-row",
                                        children=[
                                            html.Label("Duration", htmlFor="prototype-duration"),
                                            dcc.Input(
                                                id="prototype-duration",
                                                type="number",
                                                value=20,
                                                min=MIN_DURATION_SECONDS,
                                                max=MAX_DURATION_SECONDS,
                                                step=1,
                                            ),
                                            html.Span("seconds"),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Section(
                        className="prototype-experience",
                        children=[
                            html.Div(
                                className="prototype-stage-toolbar",
                                children=[
                                    dcc.RadioItems(
                                        id="prototype-comparison-mode",
                                        value="superimposed",
                                        inline=True,
                                        options=[
                                            {"label": "Superimposed", "value": "superimposed"},
                                            {"label": "Side by side", "value": "side_by_side"},
                                        ],
                                    ),
                                    html.Div(
                                        className="prototype-legend",
                                        children=[
                                            html.Span([html.I(className="legend-original"), "Original"]),
                                            html.Span([html.I(className="legend-nearby"), "Nearby"]),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                id="prototype-animation-stage",
                                className="prototype-animation-stage mode-superimposed",
                                children=[
                                    html.Div(
                                        id="prototype-overlay-panel",
                                        className="prototype-overlay-panel",
                                        children=[
                                            html.Canvas(
                                                id="prototype-overlay-canvas",
                                                className="prototype-motion-canvas",
                                            )
                                        ],
                                    ),
                                    html.Div(
                                        id="prototype-side-panel",
                                        className="prototype-side-panel",
                                        children=[
                                            html.Figure(
                                                children=[
                                                    html.Canvas(
                                                        id="prototype-original-canvas",
                                                        className="prototype-motion-canvas",
                                                    ),
                                                    html.Figcaption("Original"),
                                                ]
                                            ),
                                            html.Figure(
                                                children=[
                                                    html.Canvas(
                                                        id="prototype-nearby-canvas",
                                                        className="prototype-motion-canvas",
                                                    ),
                                                    html.Figcaption("Nearby"),
                                                ]
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        id="prototype-empty-stage",
                                        className="prototype-empty-stage is-visible",
                                        children=[
                                            html.Div("A", className="prototype-ghost-bob ghost-a"),
                                            html.Div("B", className="prototype-ghost-bob ghost-b"),
                                            html.P("Release a nearby pair to begin."),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                className="prototype-playback",
                                children=[
                                    html.Button(
                                        "Release",
                                        id="prototype-run-button",
                                        className="prototype-primary-button",
                                        n_clicks=0,
                                    ),
                                    html.Button("Pause", id="prototype-pause", n_clicks=0),
                                    html.Button("Reset", id="prototype-reset", n_clicks=0),
                                    html.Button("Replay", id="prototype-replay", n_clicks=0),
                                    html.Div(
                                        className="prototype-speed-control",
                                        children=[
                                            html.Label("Speed", htmlFor="prototype-speed"),
                                            dcc.Dropdown(
                                                id="prototype-speed",
                                                value="1",
                                                clearable=False,
                                                searchable=False,
                                                options=[
                                                    {"label": "0.5×", "value": "0.5"},
                                                    {"label": "1×", "value": "1"},
                                                    {"label": "2×", "value": "2"},
                                                    {"label": "4×", "value": "4"},
                                                ],
                                            ),
                                        ],
                                    ),
                                    dcc.Loading(
                                        type="dot",
                                        children=html.Div(
                                            "",
                                            id="prototype-run-message",
                                            className="prototype-run-message",
                                        ),
                                    ),
                                ],
                            ),
                            html.Div(
                                className="prototype-relationship",
                                children=[
                                    html.Div(
                                        className="prototype-readout-grid",
                                        children=[
                                            html.Div(
                                                [html.Span("Time"), html.Strong("0.00 s", id="prototype-time")]
                                            ),
                                            html.Div(
                                                [
                                                    html.Span("End-bob distance"),
                                                    html.Strong("—", id="prototype-current-separation"),
                                                ]
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="prototype-trace-wrap",
                                        children=[
                                            html.Div(
                                                className="prototype-trace-heading",
                                                children=[html.H2("Separation")],
                                            ),
                                            html.Canvas(
                                                id="prototype-separation-canvas",
                                                className="prototype-separation-canvas",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


app = Dash(
    __name__,
    title="Initial condition sensitivity",
    assets_folder=str(PROTOTYPE_ROOT / "assets"),
    suppress_callback_exceptions=False,
)
server = app.server
app.layout = build_layout


@app.callback(
    Output("prototype-theta1", "value"),
    Output("prototype-theta2", "value"),
    Input("prototype-preset-small_angle", "n_clicks"),
    Input("prototype-preset-regular_control", "n_clicks"),
    Input("prototype-preset-bounded_nonlinear", "n_clicks"),
    Input("prototype-preset-near_inverted", "n_clicks"),
    prevent_initial_call=True,
)
def apply_preset(*_clicks: int):
    preset_name = str(ctx.triggered_id).removeprefix("prototype-preset-")
    preset = PRESETS.get(preset_name)
    if preset is None:
        return no_update, no_update
    return tuple(preset["state"][:2])


@app.callback(
    Output("prototype-state-disclosure", "children"),
    Input("prototype-theta1", "value"),
    Input("prototype-theta2", "value"),
    Input("prototype-perturb-magnitude", "value"),
)
def construct_nearby_state(
    theta1: Any,
    theta2: Any,
    magnitude: Any,
):
    try:
        base = [float(theta1), float(theta2), 0.0, 0.0]
        magnitude_value = float(magnitude)
    except (TypeError, ValueError):
        data = {"valid": False}
        return _state_disclosure(data)
    if (
        not np.all(np.isfinite(base))
        or not math.isfinite(magnitude_value)
        or not 0.000001 <= magnitude_value <= 0.1
    ):
        data = {"valid": False}
        return _state_disclosure(data)

    nearby = list(base)
    nearby[1] += magnitude_value
    data = {
        "valid": True,
        "original_state_degrees": base,
        "nearby_state_degrees": nearby,
        "component": "theta2",
        "magnitude": magnitude_value,
        "signed_delta": magnitude_value,
    }
    return _state_disclosure(data)


@app.callback(
    Output("prototype-simulation-store", "data"),
    Output("prototype-run-message", "children"),
    Input("prototype-run-button", "n_clicks"),
    State("prototype-theta1", "value"),
    State("prototype-theta2", "value"),
    State("prototype-perturb-magnitude", "value"),
    State("prototype-duration", "value"),
    prevent_initial_call=True,
)
def run_nearby_pair(
    n_clicks: int,
    theta1: Any,
    theta2: Any,
    magnitude: Any,
    duration: Any,
):
    del n_clicks
    try:
        base = [float(theta1), float(theta2), 0.0, 0.0]
        magnitude_value = float(magnitude)
        duration_value = float(duration)
    except (TypeError, ValueError):
        payload = _error_payload("Enter valid angles, perturbation, and duration.")
        return payload, payload["message"]
    if not math.isfinite(magnitude_value) or not 0.000001 <= magnitude_value <= 0.1:
        payload = _error_payload("Enter a positive perturbation between 0.000001° and 0.1°.")
        return payload, payload["message"]

    nearby = list(base)
    nearby[1] += magnitude_value
    perturbation = {
        "valid": True,
        "component": "theta2",
        "magnitude": magnitude_value,
        "signed_delta": magnitude_value,
        "original_state_degrees": base,
        "nearby_state_degrees": nearby,
    }
    payload = build_simulation_payload(base, nearby, duration_value, perturbation)
    if payload["status"] == "success":
        message = ""
    else:
        message = payload["message"]
    return payload, message


app.clientside_callback(
    ClientsideFunction(namespace="sensitivityPrototype", function_name="applyPayload"),
    Output("prototype-render-hook", "data"),
    Input("prototype-simulation-store", "data"),
)
app.clientside_callback(
    ClientsideFunction(namespace="sensitivityPrototype", function_name="setMode"),
    Output("prototype-mode-hook", "data"),
    Input("prototype-comparison-mode", "value"),
)
app.clientside_callback(
    ClientsideFunction(namespace="sensitivityPrototype", function_name="setSpeed"),
    Output("prototype-speed-hook", "data"),
    Input("prototype-speed", "value"),
)
app.clientside_callback(
    ClientsideFunction(namespace="sensitivityPrototype", function_name="markInputsChanged"),
    Output("prototype-stale-hook", "data"),
    Input("prototype-theta1", "value"),
    Input("prototype-theta2", "value"),
    Input("prototype-perturb-magnitude", "value"),
    Input("prototype-duration", "value"),
)


def run_self_check() -> None:
    for preset_name, preset in PRESETS.items():
        original = list(preset["state"])
        nearby = list(original)
        nearby[1] += 0.001
        perturbation = {
            "valid": True,
            "component": "theta2",
            "magnitude": 0.001,
            "signed_delta": 0.001,
            "original_state_degrees": original,
            "nearby_state_degrees": nearby,
        }
        payload = build_simulation_payload(original, nearby, 20.0, perturbation)
        if payload["status"] != "success":
            raise AssertionError(f"Preset failed: {preset_name}: {payload}")
        if payload["sample_count"] != 2001:
            raise AssertionError(f"Unexpected sample count for {preset_name}.")
        if not math.isclose(
            payload["separation_normalized"][0],
            2.0 * math.sin(math.radians(0.001) / 2.0) / 2.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise AssertionError(f"Initial geometry mismatch for {preset_name}.")
        print(
            f"{preset_name}: ok; max separation="
            f"{payload['max_normalized_separation']:.6g}"
        )

    failed = build_simulation_payload(
        [math.nan, 0.0, 0.0, 0.0],
        [math.nan, 0.001, 0.0, 0.0],
        20.0,
        {"component": "theta2", "signed_delta": 0.001},
    )
    if failed["status"] != "failed" or failed["rendering"]["drawable"]:
        raise AssertionError("Invalid-state rejection contract failed.")
    json.dumps(failed, allow_nan=False)
    print("invalid-state rejection: ok")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8060)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        run_self_check()
        return 0
    app.run(debug=args.debug, host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
