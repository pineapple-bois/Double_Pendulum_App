"""Tier 3E Canvas payload stress checks.

Run from the repository root:

    python development/simulation_workbench/tier_3/tier_3e_renderer_decision/canvas_stress_runner.py

The script writes compact metrics only. It does not save payload arrays,
screenshots, HTML, or full Plotly/Canvas artifacts.
"""

from __future__ import annotations

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
RESULTS_PATH = TIER_DIR / "tier3e_results.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian


STRESS_CASES = [
    {
        "case_id": "simple_lagrangian_baseline_5s",
        "model_type": "simple",
        "system_type": "lagrangian",
        "initial_conditions_degrees": [45.0, -30.0, 0.0, 0.0],
        "duration_seconds": 5.0,
        "sample_count": 1000,
    },
    {
        "case_id": "simple_hamiltonian_nonzero_5s",
        "model_type": "simple",
        "system_type": "hamiltonian",
        "initial_conditions_degrees": [45.0, -30.0, 10.0, -5.0],
        "duration_seconds": 5.0,
        "sample_count": 1000,
    },
    {
        "case_id": "compound_lagrangian_large_angles_10s",
        "model_type": "compound",
        "system_type": "lagrangian",
        "initial_conditions_degrees": [120.0, -100.0, 0.0, 0.0],
        "duration_seconds": 10.0,
        "sample_count": 2000,
    },
    {
        "case_id": "compound_hamiltonian_large_velocity_10s",
        "model_type": "compound",
        "system_type": "hamiltonian",
        "initial_conditions_degrees": [150.0, -130.0, 20.0, -15.0],
        "duration_seconds": 10.0,
        "sample_count": 2000,
    },
    {
        "case_id": "simple_lagrangian_long_20s",
        "model_type": "simple",
        "system_type": "lagrangian",
        "initial_conditions_degrees": [120.0, -100.0, 10.0, -5.0],
        "duration_seconds": 20.0,
        "sample_count": 4000,
    },
    {
        "case_id": "compound_hamiltonian_long_20s",
        "model_type": "compound",
        "system_type": "hamiltonian",
        "initial_conditions_degrees": [120.0, -100.0, 10.0, -5.0],
        "duration_seconds": 20.0,
        "sample_count": 4000,
    },
]


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


def payload_size_estimate(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, separators=(",", ":")))


def build_payload_for_measurement(model, case: dict[str, Any], parameter_values: dict[str, float]) -> dict[str, Any]:
    x1, y1, x2, y2 = model.precomputed_positions
    theta1_deg = np.rad2deg(model.sol[:, 0])
    theta2_deg = np.rad2deg(model.sol[:, 1])
    angular_state = {
        "theta1_deg": [float(value) for value in theta1_deg],
        "theta2_deg": [float(value) for value in theta2_deg],
    }
    if case["system_type"] == "lagrangian":
        angular_state["omega1_deg_per_second"] = [float(value) for value in np.rad2deg(model.sol[:, 2])]
        angular_state["omega2_deg_per_second"] = [float(value) for value in np.rad2deg(model.sol[:, 3])]
    else:
        angular_state["omega1_deg_per_second"] = None
        angular_state["omega2_deg_per_second"] = None
        angular_state["hamiltonian_note"] = (
            "Hamiltonian state slots 3 and 4 are canonical momenta; angular velocities "
            "should not be serialized from those slots without a dedicated velocity reconstruction."
        )

    return {
        "schema_version": "tier3e.canvas_motion_payload.v1",
        "status": "success",
        "run_id": 1,
        "model_type": case["model_type"],
        "system_type": case["system_type"],
        "request_label": case["case_id"],
        "time": [float(value) for value in model.time],
        "angular_state": angular_state,
        "positions": {
            "x1": [float(value) for value in x1],
            "y1": [float(value) for value in y1],
            "x2": [float(value) for value in x2],
            "y2": [float(value) for value in y2],
        },
        "sample_count": int(case["sample_count"]),
        "duration_seconds": float(case["duration_seconds"]),
        "user_initial_conditions": {
            "names": list(getattr(model, "user_initial_condition_names", [])),
            "degrees": [float(value) for value in getattr(model, "user_initial_conditions_degrees", [])],
        },
        "internal_initial_state_summary": {
            "state_convention": getattr(model, "solver_state_convention", None),
            "first_state_row": [float(value) for value in model.sol[0]],
        },
        "state_units": {
            "theta1": "degrees in payload",
            "theta2": "degrees in payload",
            "omega1": "degrees/second for Lagrangian only; null for Hamiltonian until audited",
            "omega2": "degrees/second for Lagrangian only; null for Hamiltonian until audited",
        },
        "position_units": "model length units",
        "solver_metadata": solver_metadata_summary(model),
        "parameters": parameter_values,
        "warnings": [
            "Canvas payload is not an energy diagnostic.",
            "Theta-theta projection is not a full phase portrait.",
            "JavaScript must render only; Python owns simulation mathematics.",
        ],
        "bounds": drawing_bounds(x1, y1, x2, y2),
    }


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    parameters, parameter_values = parameters_for_model(case["model_type"])
    model_class = model_class_for_system(case["system_type"])

    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "model_type": case["model_type"],
        "system_type": case["system_type"],
        "initial_conditions_degrees": case["initial_conditions_degrees"],
        "duration_seconds": case["duration_seconds"],
        "sample_count": case["sample_count"],
        "status": "unknown",
    }

    try:
        model, construction_seconds = timed_call(
            lambda: model_class(
                parameters,
                list(case["initial_conditions_degrees"]),
                [0.0, case["duration_seconds"], case["sample_count"]],
                model=case["model_type"],
            )
        )
        _, position_precompute_seconds = timed_call(model.precompute_positions)
        payload, payload_preparation_seconds = timed_call(
            lambda: build_payload_for_measurement(model, case, parameter_values)
        )
        payload_bytes = payload_size_estimate(payload)
        metadata = payload["solver_metadata"]

        result.update(
            {
                "status": "success",
                "model_construction_seconds": construction_seconds,
                "position_precompute_seconds": position_precompute_seconds,
                "payload_preparation_seconds": payload_preparation_seconds,
                "payload_size_bytes": payload_bytes,
                "approx_bytes_per_sample": payload_bytes / max(1, case["sample_count"]),
                "warning_count": len(payload["warnings"]),
                "solver_success": metadata.get("success"),
                "solver_status": metadata.get("status"),
                "solver_message": metadata.get("message"),
                "solver_nfev": metadata.get("nfev"),
                "returned_time_matches_requested": metadata.get("returned_time_matches_requested"),
                "state_shape": list(model.sol.shape),
                "position_shape": list(model.precomputed_positions.shape),
                "state_values_finite": bool(np.all(np.isfinite(model.sol))),
                "position_values_finite": bool(np.all(np.isfinite(model.precomputed_positions))),
                "time_monotonic": bool(np.all(np.diff(model.time) > 0)),
                "time_end_matches": bool(np.isclose(float(model.time[-1]), float(case["duration_seconds"]))),
                "internal_state_convention": getattr(model, "solver_state_convention", None),
                "payload_arrays_saved": False,
            }
        )
    except Exception as exc:  # noqa: BLE001 - stress runner should record failures.
        result.update(
            {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "payload_arrays_saved": False,
            }
        )
    return result


def run_stress_checks() -> dict[str, Any]:
    cases = [run_case(case) for case in STRESS_CASES]
    successful = [case for case in cases if case["status"] == "success"]
    failed = [case for case in cases if case["status"] != "success"]
    max_payload = max((case.get("payload_size_bytes", 0) for case in successful), default=0)
    max_samples = max((case.get("sample_count", 0) for case in successful), default=0)
    return {
        "tier": "Phase 6 / Tier 3E",
        "purpose": "Compact Canvas payload stress metrics; arrays omitted",
        "case_count": len(cases),
        "success_count": len(successful),
        "failure_count": len(failed),
        "max_payload_size_bytes": max_payload,
        "max_sample_count": max_samples,
        "stress_dimensions": [
            "larger initial angles",
            "nonzero angular velocities",
            "5s, 10s, and 20s durations",
            "simple and compound models",
            "Lagrangian and Hamiltonian systems",
        ],
        "manual_browser_checks": "not rerun in Tier 3E; Tier 3C.2 and Tier 3D browser checks remain the current lifecycle evidence",
        "cases": cases,
    }


def main() -> int:
    summary = run_stress_checks()
    RESULTS_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Wrote compact Tier 3E stress results: {RESULTS_PATH}")
    for case in summary["cases"]:
        if case["status"] == "success":
            print(
                f"- {case['case_id']}: samples={case['sample_count']} "
                f"payload={case['payload_size_bytes']} bytes "
                f"model={case['model_construction_seconds']:.4f}s "
                f"finite={case['state_values_finite'] and case['position_values_finite']}"
            )
        else:
            print(f"- {case['case_id']}: FAILED {case.get('error_type')}: {case.get('error_message')}")
    return 0 if summary["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
