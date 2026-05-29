"""Workbench-only output composition helpers for Tier 2 preview."""

from __future__ import annotations

import os
import sys
import tempfile
import warnings
from dataclasses import dataclass
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
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objs as go
import plotly.tools as tls

from tier2_metrics import figure_metrics, timed_call

warnings.filterwarnings(
    "ignore",
    message="I found a path object that I don't think is part of a bar chart. Ignoring.",
    category=UserWarning,
    module="plotly.matplotlylib.renderer",
)


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (
            (candidate / "AGENTS.md").is_file()
            and (candidate / "TIER4_README.md").is_file()
            and (candidate / "src" / "double_pendulum").is_dir()
        ):
            return candidate
    raise RuntimeError(f"Could not find repository root from {start}")


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.components.figure_style import mpl_layout
from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian


SAMPLES_PER_SECOND_OPTIONS = [80, 120, 200]
DURATION_OPTIONS = [2.0, 3.0, 5.0]
BASELINE_MATRIX = [
    ("simple", "lagrangian"),
    ("simple", "hamiltonian"),
    ("compound", "lagrangian"),
    ("compound", "hamiltonian"),
]

PRESETS = {
    "zero velocities": {
        "label": "Zero velocities",
        "initial_conditions_degrees": [45.0, -30.0, 0.0, 0.0],
        "note": "Tier 1 baseline-style request.",
    },
    "nonzero velocities": {
        "label": "Nonzero velocities",
        "initial_conditions_degrees": [45.0, -30.0, 10.0, -5.0],
        "note": "Exercises Tier 1D Hamiltonian velocity-to-momentum conversion.",
    },
    "small angles": {
        "label": "Small angles",
        "initial_conditions_degrees": [10.0, -8.0, 2.0, -1.0],
        "note": "Conservative short-duration inspection request.",
    },
}


@dataclass(frozen=True)
class PreviewRequest:
    model_type: str
    system_type: str
    preset_name: str
    duration_seconds: float
    samples_per_second: int

    @property
    def initial_conditions_degrees(self) -> list[float]:
        return list(PRESETS[self.preset_name]["initial_conditions_degrees"])

    @property
    def sample_count(self) -> int:
        return int(self.duration_seconds * self.samples_per_second)

    @property
    def time_vector(self) -> list[float | int]:
        return [0.0, self.duration_seconds, self.sample_count]


def parameters_for_model(model_type: str) -> tuple[dict[Any, float], dict[str, float]]:
    if model_type == "simple":
        parameters = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
        parameter_values = {"l1": 1.0, "l2": 1.0, "m1": 1.0, "m2": 1.0, "g": 9.81}
    elif model_type == "compound":
        parameters = {l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81}
        parameter_values = {"l1": 1.0, "l2": 1.0, "M1": 1.0, "M2": 1.0, "g": 9.81}
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    return parameters, parameter_values


def model_class_for_system(system_type: str):
    if system_type == "lagrangian":
        return DoublePendulumLagrangian
    if system_type == "hamiltonian":
        return DoublePendulumHamiltonian
    raise ValueError(f"Unsupported system type: {system_type}")


def build_model(request: PreviewRequest):
    parameters, _ = parameters_for_model(request.model_type)
    model_class = model_class_for_system(request.system_type)
    return model_class(
        parameters,
        request.initial_conditions_degrees,
        request.time_vector,
        model=request.model_type,
    )


def build_time_figure(model):
    matplotlib_time_fig = model.time_graph()
    try:
        fig = tls.mpl_to_plotly(matplotlib_time_fig)
        fig.update_layout(
            title="Angular displacement time series",
            autosize=True,
            margin=dict(l=24, r=20, t=48, b=28),
        )
        fig.update_layout(mpl_layout)
        return fig
    finally:
        plt.close(matplotlib_time_fig)


def build_projection_figure(model):
    matplotlib_projection_fig = model.phase_path()
    try:
        fig = tls.mpl_to_plotly(matplotlib_projection_fig)
        fig.update_layout(
            title="Theta-theta state projection",
            autosize=True,
            margin=dict(l=24, r=20, t=48, b=28),
            width=600,
            height=520,
        )
        fig.update_layout(mpl_layout)
        return fig
    finally:
        plt.close(matplotlib_projection_fig)


def build_animation_figure(model):
    model.precompute_positions()
    fig = model.animate_pendulum(trace=True, fig_width=620, fig_height=520, static=True)
    fig.update_layout(title="Physical motion preview", margin=dict(l=20, r=20, t=48, b=24))
    return fig


def solver_metadata_dict(model) -> dict[str, Any]:
    metadata = getattr(model, "solver_metadata", None)
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()
    return dict(metadata)


def build_diagnostics(model, request: PreviewRequest) -> dict[str, Any]:
    solver_metadata = solver_metadata_dict(model)
    return {
        "solver_metadata_available": bool(solver_metadata),
        "solver_success": solver_metadata.get("success"),
        "solver_status": solver_metadata.get("status"),
        "solver_message": solver_metadata.get("message"),
        "nfev": solver_metadata.get("nfev"),
        "njev": solver_metadata.get("njev"),
        "nlu": solver_metadata.get("nlu"),
        "requested_time_count": solver_metadata.get("requested_time_count", request.sample_count),
        "returned_time_count": solver_metadata.get("returned_time_count"),
        "returned_time_matches_requested": solver_metadata.get("returned_time_matches_requested"),
        "solution_shape": list(np.shape(model.sol)),
        "time_shape": list(np.shape(model.time)),
        "state_values_finite": bool(np.all(np.isfinite(model.sol))),
        "time_values_finite": bool(np.all(np.isfinite(model.time))),
        "time_monotonic_increasing": bool(np.all(np.diff(model.time) > 0)),
        "first_state_matches_internal_initial_conditions": bool(
            np.allclose(model.sol[0], model.initial_conditions, rtol=0, atol=1e-10)
        ),
    }


def build_run_summary(model, request: PreviewRequest, parameter_values: dict[str, float]) -> dict[str, Any]:
    return {
        "model_type": request.model_type,
        "system_type": request.system_type,
        "parameters": parameter_values,
        "user_initial_condition_names": list(getattr(model, "user_initial_condition_names", [])),
        "user_initial_conditions_degrees": [
            float(value) for value in getattr(model, "user_initial_conditions_degrees", [])
        ],
        "user_initial_conditions_radians": [
            float(value) for value in getattr(model, "user_initial_conditions_radians", [])
        ],
        "solver_state_variable_names": list(getattr(model, "solver_state_variable_names", [])),
        "solver_state_convention": getattr(model, "solver_state_convention", None),
        "initial_condition_conversion": getattr(model, "initial_condition_conversion", None),
        "initial_canonical_momenta": [
            float(value) for value in getattr(model, "initial_canonical_momenta", [])
        ],
        "time_interval": {"start": 0.0, "end": request.duration_seconds},
        "sample_count": request.sample_count,
        "samples_per_second": request.samples_per_second,
        "solver_method": solver_metadata_dict(model).get("integrator"),
        "preset": PRESETS[request.preset_name]["label"],
        "preset_note": PRESETS[request.preset_name]["note"],
    }


def build_warnings(request: PreviewRequest, diagnostics: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    warnings_list = [
        "Energy diagnostics are not accepted in Tier 2; no energy drift claim is made.",
        "This preview is not scientific validation of full physical correctness, chaos, or long-duration behavior.",
        "The theta-theta view is a reduced state projection, not a validated full phase portrait.",
    ]
    if request.system_type == "hamiltonian":
        warnings_list.append(
            "Hamiltonian runs convert UI angular velocities to canonical momenta before solving."
        )
    if diagnostics.get("solver_success") is not True:
        warnings_list.append("Solver success was not confirmed for this preview run.")
    if summary.get("sample_count", 0) > 800:
        warnings_list.append("Higher sample counts increase animation payload size and callback cost.")
    return warnings_list


def assemble_workspace_payload(
    model_type: str,
    system_type: str,
    preset_name: str,
    duration_seconds: float,
    samples_per_second: int,
) -> dict[str, Any]:
    request = PreviewRequest(
        model_type=model_type,
        system_type=system_type,
        preset_name=preset_name,
        duration_seconds=float(duration_seconds),
        samples_per_second=int(samples_per_second),
    )
    parameters, parameter_values = parameters_for_model(request.model_type)

    composition_start = perf_counter()
    model, model_build_time = timed_call(lambda: build_model(request))
    summary = build_run_summary(model, request, parameter_values)
    diagnostics = build_diagnostics(model, request)

    animation_fig, animation_time = timed_call(lambda: build_animation_figure(model))
    time_fig, time_time = timed_call(lambda: build_time_figure(model))
    projection_fig, projection_time = timed_call(lambda: build_projection_figure(model))

    warnings_list = build_warnings(request, diagnostics, summary)
    figures = {
        "animation": animation_fig,
        "time_series": time_fig,
        "state_projection": projection_fig,
    }
    figure_metric_data = {
        "animation": figure_metrics(animation_fig, animation_time),
        "time_series": figure_metrics(time_fig, time_time),
        "state_projection": figure_metrics(projection_fig, projection_time),
    }
    metrics = {
        "model_build_time_seconds": model_build_time,
        "composition_total_time_seconds": perf_counter() - composition_start,
        "figures": figure_metric_data,
        "output_panel_count": 5,
        "warning_count": len(warnings_list),
        "solver_metadata_available": diagnostics["solver_metadata_available"],
    }

    return {
        "status": "success",
        "summary": summary,
        "diagnostics": diagnostics,
        "warnings": warnings_list,
        "figures": figures,
        "metrics": metrics,
    }


def empty_state_payload() -> dict[str, Any]:
    return {
        "status": "empty",
        "title": "No preview run yet",
        "regions": [
            "Run summary",
            "Numerical diagnostics",
            "Physical motion preview",
            "Angular displacement time series",
            "Theta-theta state projection",
        ],
        "warnings": [
            "Energy, chaos, and long-duration claims are intentionally absent from this preview.",
            "The projection region is planned as a reduced state view, not a full phase portrait.",
        ],
    }


def failure_state_payload() -> dict[str, Any]:
    return {
        "status": "failure_preview",
        "title": "Preview failure state",
        "message": "This is a simulated Tier 2 failure/invalid state, not a forced solver failure.",
        "details": [
            "Keep the previous successful figures hidden or clearly stale.",
            "Show the validation or solver message near the run controls.",
            "Preserve requested model, system, and preset values for debugging.",
            "Do not render attractive plots when solver success is unknown.",
        ],
        "warnings": [
            "Failure presentation is a candidate composition, not production behavior.",
            "The production app still needs a deliberate failure-state implementation plan.",
        ],
    }
