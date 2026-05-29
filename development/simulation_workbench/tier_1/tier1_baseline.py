"""Phase 6 / Tier 1 simulation baseline.

Run from the repository root:

    .venv/bin/python development/simulation_workbench/tier_1/tier1_baseline.py

The script exercises the current production model classes without modifying
them. Timings for model construction include equation cache lookup/derivation,
lambdification, and numerical integration because that is how the current
constructors behave.
"""

from __future__ import annotations

import json
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
import plotly.tools as tls

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
            and (candidate / "README.md").is_file()
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


OUTPUT_PATH = Path(__file__).with_name("tier1_baseline_results.json")
SAMPLE_RATE_PER_SECOND = 200
TIME_START = 0.0
TIME_END = 5.0
REQUESTED_SAMPLE_COUNT = int((TIME_END - TIME_START) * SAMPLE_RATE_PER_SECOND)
TIME_VECTOR = [TIME_START, TIME_END, REQUESTED_SAMPLE_COUNT]
INITIAL_CONDITIONS_DEGREES = [45.0, -30.0, 0.0, 0.0]
TOLERANCE = 1e-10

@dataclass(frozen=True)
class BaselineCase:
    name: str
    model_type: str
    system_type: str
    model_class: type
    parameters: dict[Any, float]
    parameter_values: dict[str, float]
    state_variable_names: list[str]
    convention_warning: str | None = None


BASELINE_CASES = [
    BaselineCase(
        name="simple_lagrangian",
        model_type="simple",
        system_type="lagrangian",
        model_class=DoublePendulumLagrangian,
        parameters={l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81},
        parameter_values={"l1": 1.0, "l2": 1.0, "m1": 1.0, "m2": 1.0, "g": 9.81},
        state_variable_names=["theta1", "theta2", "omega1", "omega2"],
    ),
    BaselineCase(
        name="simple_hamiltonian",
        model_type="simple",
        system_type="hamiltonian",
        model_class=DoublePendulumHamiltonian,
        parameters={l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81},
        parameter_values={"l1": 1.0, "l2": 1.0, "m1": 1.0, "m2": 1.0, "g": 9.81},
        state_variable_names=["theta1", "theta2", "p_theta_1", "p_theta_2"],
        convention_warning=(
            "UI-shaped initial conditions label the last two inputs as angular "
            "velocities, but this Hamiltonian state uses canonical momenta."
        ),
    ),
    BaselineCase(
        name="compound_lagrangian",
        model_type="compound",
        system_type="lagrangian",
        model_class=DoublePendulumLagrangian,
        parameters={l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81},
        parameter_values={"l1": 1.0, "l2": 1.0, "M1": 1.0, "M2": 1.0, "g": 9.81},
        state_variable_names=["theta1", "theta2", "omega1", "omega2"],
    ),
    BaselineCase(
        name="compound_hamiltonian",
        model_type="compound",
        system_type="hamiltonian",
        model_class=DoublePendulumHamiltonian,
        parameters={l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81},
        parameter_values={"l1": 1.0, "l2": 1.0, "M1": 1.0, "M2": 1.0, "g": 9.81},
        state_variable_names=["theta1", "theta2", "p_theta_1", "p_theta_2"],
        convention_warning=(
            "UI-shaped initial conditions label the last two inputs as angular "
            "velocities, but this Hamiltonian state uses canonical momenta."
        ),
    ),
]


def timed_call(func):
    start = perf_counter()
    value = func()
    return value, perf_counter() - start


def construct_model(case: BaselineCase):
    return case.model_class(
        case.parameters,
        list(INITIAL_CONDITIONS_DEGREES),
        list(TIME_VECTOR),
        model=case.model_type,
    )


def shape_of(array) -> list[int]:
    return [int(value) for value in np.shape(array)]


def bool_value(value) -> bool:
    return bool(value)


def max_abs(array) -> float | None:
    if array is None or np.size(array) == 0:
        return None
    return float(np.max(np.abs(array)))


def plot_json_size(fig) -> int:
    return len(fig.to_json())


def trace_count(fig) -> int:
    return len(getattr(fig, "data", []) or [])


def frame_count(fig) -> int:
    return len(getattr(fig, "frames", []) or [])


def point_count(fig) -> int:
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


def build_time_plotly_figure(model):
    matplotlib_time_fig = model.time_graph()
    try:
        time_fig = tls.mpl_to_plotly(matplotlib_time_fig)
        time_fig.update_layout(
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        time_fig.update_layout(mpl_layout)
        return time_fig
    finally:
        plt.close(matplotlib_time_fig)


def build_phase_plotly_figure(model):
    matplotlib_phase_fig = model.phase_path()
    try:
        phase_fig = tls.mpl_to_plotly(matplotlib_phase_fig)
        phase_fig.update_layout(
            autosize=True,
            margin=dict(l=20, r=20, t=20, b=20),
            width=600,
            height=600,
        )
        phase_fig.update_layout(mpl_layout)
        return phase_fig
    finally:
        plt.close(matplotlib_phase_fig)


def rendering_metrics(name: str, fig) -> dict[str, Any]:
    return {
        f"{name}_trace_count": trace_count(fig),
        f"{name}_frame_count": frame_count(fig),
        f"{name}_point_count": point_count(fig),
        f"{name}_json_size_bytes": plot_json_size(fig),
    }


def solver_metadata_summary(model) -> dict[str, Any] | None:
    metadata = getattr(model, "solver_metadata", None)
    if metadata is None:
        return None
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()
    return dict(metadata)


def run_case(case: BaselineCase) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": case.name,
        "model_type": case.model_type,
        "system_type": case.system_type,
        "model_class": f"{case.model_class.__module__}.{case.model_class.__name__}",
        "parameters": case.parameter_values,
        "initial_conditions_degrees": list(INITIAL_CONDITIONS_DEGREES),
        "time_interval": {"start": TIME_START, "end": TIME_END},
        "sample_rate_rule": f"{SAMPLE_RATE_PER_SECOND} samples per second",
        "requested_sample_count": REQUESTED_SAMPLE_COUNT,
        "state_variable_names": case.state_variable_names,
        "tolerance": TOLERANCE,
        "warnings": [],
        "failures": [],
    }
    if case.convention_warning:
        result["warnings"].append(case.convention_warning)

    try:
        model, first_duration = timed_call(lambda: construct_model(case))
        repeat_model, repeat_duration = timed_call(lambda: construct_model(case))
    except Exception as exc:  # noqa: BLE001 - baseline evidence should capture failures.
        result.update(
            {
                "construction_completed": False,
                "failure_type": type(exc).__name__,
                "failure_message": str(exc),
            }
        )
        result["failures"].append(f"{type(exc).__name__}: {exc}")
        return result

    state_diff = model.sol - repeat_model.sol
    initial_condition_delta = model.sol[0] - model.initial_conditions
    solver_metadata = solver_metadata_summary(model)

    result.update(
        {
            "construction_completed": True,
            "timing_seconds": {
                "first_construction_integration": first_duration,
                "repeat_construction_integration": repeat_duration,
            },
            "time_shape": shape_of(model.time),
            "state_shape": shape_of(model.sol),
            "expected_time_shape": [REQUESTED_SAMPLE_COUNT],
            "expected_state_shape": [REQUESTED_SAMPLE_COUNT, 4],
            "time_values_finite": bool_value(np.all(np.isfinite(model.time))),
            "state_values_finite": bool_value(np.all(np.isfinite(model.sol))),
            "time_monotonic_increasing": bool_value(np.all(np.diff(model.time) > 0)),
            "first_time_matches_start": bool_value(np.isclose(model.time[0], TIME_START, atol=TOLERANCE, rtol=0)),
            "last_time_matches_end": bool_value(np.isclose(model.time[-1], TIME_END, atol=TOLERANCE, rtol=0)),
            "first_state_matches_internal_initial_conditions": bool_value(
                np.allclose(model.sol[0], model.initial_conditions, atol=TOLERANCE, rtol=0)
            ),
            "max_initial_condition_abs_difference": max_abs(initial_condition_delta),
            "repeat_run_deterministic": bool_value(np.allclose(model.sol, repeat_model.sol, atol=TOLERANCE, rtol=0)),
            "max_abs_repeat_run_difference": max_abs(state_diff),
            "max_abs_state_value": max_abs(model.sol),
            "internal_initial_conditions": [float(value) for value in model.initial_conditions],
            "time_start_actual": float(model.time[0]),
            "time_end_actual": float(model.time[-1]),
            "solver_metadata_available": solver_metadata is not None,
            "solver_metadata": solver_metadata,
            "solver_time_shape": shape_of(getattr(model, "solver_time", [])),
            "solver_time_matches_requested": bool_value(
                np.allclose(getattr(model, "solver_time", []), model.time, rtol=0, atol=0)
            ),
            "metadata_solution_shape_matches_sol": bool_value(
                solver_metadata is not None and solver_metadata.get("solution_shape") == shape_of(model.sol)
            ),
        }
    )

    try:
        _, position_duration = timed_call(model.precompute_positions)
        result["timing_seconds"]["position_precompute"] = position_duration
        result.update(
            {
                "position_shape": shape_of(model.precomputed_positions),
                "expected_position_shape": [4, REQUESTED_SAMPLE_COUNT],
                "position_values_finite": bool_value(np.all(np.isfinite(model.precomputed_positions))),
                "max_abs_position_value": max_abs(model.precomputed_positions),
            }
        )
    except Exception as exc:  # noqa: BLE001
        result["failures"].append(f"position precompute {type(exc).__name__}: {exc}")
        result["position_precompute_completed"] = False

    try:
        time_fig, time_graph_duration = timed_call(lambda: build_time_plotly_figure(model))
        result["timing_seconds"]["time_graph_build"] = time_graph_duration
        result.update(rendering_metrics("time_graph", time_fig))
    except Exception as exc:  # noqa: BLE001
        result["failures"].append(f"time graph {type(exc).__name__}: {exc}")

    try:
        phase_fig, phase_graph_duration = timed_call(lambda: build_phase_plotly_figure(model))
        result["timing_seconds"]["phase_projection_build"] = phase_graph_duration
        result.update(rendering_metrics("phase_projection", phase_fig))
    except Exception as exc:  # noqa: BLE001
        result["failures"].append(f"phase projection {type(exc).__name__}: {exc}")

    try:
        animation_fig, animation_duration = timed_call(
            lambda: model.animate_pendulum(trace=True, fig_width=600, fig_height=600, static=True)
        )
        result["timing_seconds"]["animation_build"] = animation_duration
        result.update(rendering_metrics("animation", animation_fig))
    except Exception as exc:  # noqa: BLE001
        result["failures"].append(f"animation {type(exc).__name__}: {exc}")

    return result


def all_core_checks_passed(case_result: dict[str, Any]) -> bool:
    if not case_result.get("construction_completed"):
        return False
    return all(
        case_result.get(key) is True
        for key in [
            "time_values_finite",
            "state_values_finite",
            "time_monotonic_increasing",
            "first_time_matches_start",
            "last_time_matches_end",
            "first_state_matches_internal_initial_conditions",
            "repeat_run_deterministic",
            "position_values_finite",
            "solver_metadata_available",
            "solver_time_matches_requested",
            "metadata_solution_shape_matches_sol",
        ]
    )


def main() -> int:
    cases = [run_case(case) for case in BASELINE_CASES]
    summary = {
        "tier": "Phase 6 / Tier 1",
        "purpose": "Numerical evidence baseline for current simulation model behavior",
        "measurement_notes": [
            "Model construction timings include equation cache lookup/derivation, lambdification, and integration.",
            "Tier 1b model classes retain compact solve_ivp metadata; raw full OdeResult objects are not saved.",
            "Hamiltonian cases preserve current behavior but are not a physical validation of UI velocity inputs as momenta.",
            "JSON sizes are approximate Plotly payload-size proxies; full plot JSON is not saved separately.",
        ],
        "baseline_request": {
            "gravity": 9.81,
            "lengths": {"l1": 1.0, "l2": 1.0},
            "masses": 1.0,
            "initial_conditions_degrees": list(INITIAL_CONDITIONS_DEGREES),
            "time_interval": {"start": TIME_START, "end": TIME_END},
            "sample_rate_rule": f"{SAMPLE_RATE_PER_SECOND} samples per second",
            "requested_sample_count": REQUESTED_SAMPLE_COUNT,
            "tolerance": TOLERANCE,
        },
        "cases": cases,
    }
    summary["all_cases_completed"] = all(case.get("construction_completed") for case in cases)
    summary["all_core_checks_passed"] = all(all_core_checks_passed(case) for case in cases)

    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print("Phase 6 / Tier 1 baseline")
    print(f"Wrote compact JSON summary: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    for case in cases:
        status = "PASS" if all_core_checks_passed(case) else "CHECK"
        failures = "; ".join(case.get("failures", [])) or "none"
        warnings = "; ".join(case.get("warnings", [])) or "none"
        timing = case.get("timing_seconds", {})
        first_duration = timing.get("first_construction_integration")
        repeat_duration = timing.get("repeat_construction_integration")
        frame_total = case.get("animation_frame_count", "n/a")
        animation_json = case.get("animation_json_size_bytes", "n/a")
        solver_metadata = case.get("solver_metadata") or {}
        solver_success = solver_metadata.get("success", "n/a")
        solver_nfev = solver_metadata.get("nfev", "n/a")
        print(
            f"- {case['name']}: {status}; "
            f"first={first_duration:.4f}s repeat={repeat_duration:.4f}s "
            f"solver_success={solver_success} nfev={solver_nfev} "
            f"frames={frame_total} animation_json={animation_json} bytes; "
            f"warnings={warnings}; failures={failures}"
        )
    print(f"All core checks passed: {summary['all_core_checks_passed']}")
    return 0 if summary["all_core_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
