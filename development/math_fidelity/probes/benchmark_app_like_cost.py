#!/usr/bin/env python3
"""Benchmark app-like simple-model simulation costs using the source snapshot.

Run from the repository root:

    .venv/bin/python development/math_fidelity/probes/benchmark_app_like_cost.py

The benchmark imports from development/math_fidelity/snapshots/simple_model_source
rather than live production source. It prepares a diagnostic Canvas-like payload
but does not import or exercise production Canvas payload code.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
LAB_ROOT = REPO_ROOT / "development" / "math_fidelity"
LOG_DIR = LAB_ROOT / "logs"
SNAPSHOT_SOURCE = LAB_ROOT / "snapshots" / "simple_model_source"

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/double_pendulum_math_fidelity_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/double_pendulum_math_fidelity_cache")
sys.path.insert(0, str(SNAPSHOT_SOURCE))

from double_pendulum_snapshot.math.functions import g, l1, l2, m1, m2  # noqa: E402
from double_pendulum_snapshot.models import (  # noqa: E402
    DoublePendulumHamiltonian,
    DoublePendulumLagrangian,
)


SAMPLE_RATE_HZ = 200


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    description: str
    initial_conditions_deg: tuple[float, float, float, float]
    parameters: dict[Any, float]


@dataclass(frozen=True)
class SolverConfig:
    name: str
    method: str | None
    rtol: float | None
    atol: float | None
    notes: str

    def kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if self.method is not None:
            kwargs["method"] = self.method
        if self.rtol is not None:
            kwargs["rtol"] = self.rtol
        if self.atol is not None:
            kwargs["atol"] = self.atol
        return kwargs


def cases() -> list[BenchmarkCase]:
    unity = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
    spirograph_parameters = {l1: 1.0, l2: 1.5, m1: 3.0, m2: 1.0, g: 9.81}
    return [
        BenchmarkCase(
            name="low_energy_small_angles",
            description="Small angles released from rest; comparatively benign.",
            initial_conditions_deg=(5.0, 7.0, 0.0, 0.0),
            parameters=unity,
        ),
        BenchmarkCase(
            name="screenshot_like_simple_start",
            description="Screenshot-like simple case [0, 60, 0, 0].",
            initial_conditions_deg=(0.0, 60.0, 0.0, 0.0),
            parameters=unity,
        ),
        BenchmarkCase(
            name="nonzero_velocity_spirograph",
            description="Nonzero angular-velocity case using non-unity lengths and masses.",
            initial_conditions_deg=(90.0, 0.0, 572.95, -458.37),
            parameters=spirograph_parameters,
        ),
        BenchmarkCase(
            name="higher_energy_wide_swing",
            description="Large separated angles plus nonzero velocities; more sensitive.",
            initial_conditions_deg=(120.0, -120.0, 120.0, -90.0),
            parameters=unity,
        ),
    ]


def solver_configs() -> list[SolverConfig]:
    return [
        SolverConfig("solve_ivp_default", None, None, None, "Negative baseline-risk policy."),
        SolverConfig("rk45_strict", "RK45", 1e-8, 1e-10, "Strict RK45 candidate."),
        SolverConfig("dop853_moderate", "DOP853", 1e-6, 1e-8, "Moderate DOP853 candidate."),
        SolverConfig("dop853_strict", "DOP853", 1e-9, 1e-11, "Strict DOP853 candidate."),
    ]


def repeat_count_for_duration(duration_s: int) -> int:
    if duration_s >= 30:
        return 2
    return 3


def sample_count(duration_s: int) -> int:
    return int(duration_s * SAMPLE_RATE_HZ)


def solver_metadata_dict(pendulum: Any) -> dict[str, Any]:
    metadata = getattr(pendulum, "solver_metadata", None)
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()
    return dict(metadata)


def parameter_record(parameters: dict[Any, float]) -> dict[str, float]:
    return {str(symbol): float(value) for symbol, value in parameters.items()}


def json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def reconstruct_simple_omega(parameters: dict[Any, float], hamiltonian_state: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    theta_1 = hamiltonian_state[:, 0]
    theta_2 = hamiltonian_state[:, 1]
    p_1 = hamiltonian_state[:, 2]
    p_2 = hamiltonian_state[:, 3]

    length_1 = float(parameters[l1])
    length_2 = float(parameters[l2])
    mass_1 = float(parameters[m1])
    mass_2 = float(parameters[m2])
    delta = theta_1 - theta_2
    b11 = (mass_1 + mass_2) * length_1**2
    b12 = mass_2 * length_1 * length_2 * np.cos(delta)
    b22 = mass_2 * length_2**2
    determinant = b11 * b22 - b12**2

    omega_1 = (b22 * p_1 - b12 * p_2) / determinant
    omega_2 = (-b12 * p_1 + b11 * p_2) / determinant
    return omega_1, omega_2


def simple_energy(parameters: dict[Any, float], state: np.ndarray, *, formulation: str) -> np.ndarray:
    theta_1 = state[:, 0]
    theta_2 = state[:, 1]
    if formulation == "lagrangian":
        omega_1 = state[:, 2]
        omega_2 = state[:, 3]
    elif formulation == "hamiltonian":
        omega_1, omega_2 = reconstruct_simple_omega(parameters, state)
    else:
        raise ValueError(f"unsupported formulation: {formulation}")

    length_1 = float(parameters[l1])
    length_2 = float(parameters[l2])
    mass_1 = float(parameters[m1])
    mass_2 = float(parameters[m2])
    gravity = float(parameters[g])
    delta = theta_1 - theta_2

    kinetic = (
        0.5 * (mass_1 + mass_2) * length_1**2 * omega_1**2
        + 0.5 * mass_2 * length_2**2 * omega_2**2
        + mass_2 * length_1 * length_2 * omega_1 * omega_2 * np.cos(delta)
    )
    potential = (
        -(mass_1 + mass_2) * gravity * length_1 * np.cos(theta_1)
        - mass_2 * gravity * length_2 * np.cos(theta_2)
    )
    return kinetic + potential


def calculate_positions(parameters: dict[Any, float], state: np.ndarray) -> np.ndarray:
    theta_1 = state[:, 0]
    theta_2 = state[:, 1]
    length_1 = float(parameters[l1])
    length_2 = float(parameters[l2])
    x_1 = length_1 * np.sin(theta_1)
    y_1 = -length_1 * np.cos(theta_1)
    x_2 = x_1 + length_2 * np.sin(theta_2)
    y_2 = y_1 - length_2 * np.cos(theta_2)
    return np.column_stack([x_1, y_1, x_2, y_2])


def instantiate_model(
    *,
    formulation: str,
    case: BenchmarkCase,
    duration_s: int,
    config: SolverConfig,
) -> Any:
    time_vector = [0.0, float(duration_s), sample_count(duration_s)]
    model_class = DoublePendulumLagrangian if formulation == "lagrangian" else DoublePendulumHamiltonian
    return model_class(
        case.parameters,
        list(case.initial_conditions_deg),
        time_vector,
        model="simple",
        **config.kwargs(),
    )


def build_diagnostic_payload(
    *,
    case: BenchmarkCase,
    formulation: str,
    config: SolverConfig,
    duration_s: int,
    time_values: np.ndarray,
    state: np.ndarray,
    positions: np.ndarray,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    theta_1 = state[:, 0]
    theta_2 = state[:, 1]
    frames = [
        {
            "t": float(time_values[index]),
            "theta1": float(theta_1[index]),
            "theta2": float(theta_2[index]),
            "x1": float(positions[index, 0]),
            "y1": float(positions[index, 1]),
            "x2": float(positions[index, 2]),
            "y2": float(positions[index, 3]),
        }
        for index in range(len(state))
    ]
    return {
        "diagnostic_schema": "phase8_app_like_simple_payload_v1",
        "case_name": case.name,
        "formulation": formulation,
        "solver_config": config.name,
        "duration_s": duration_s,
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "requested_sample_count": sample_count(duration_s),
        "returned_sample_count": len(frames),
        "initial_conditions_user_units": list(case.initial_conditions_deg),
        "parameters": parameter_record(case.parameters),
        "solver": {
            "success": metadata.get("success"),
            "status": metadata.get("status"),
            "message": metadata.get("message"),
            "nfev": metadata.get("nfev"),
        },
        "frames": frames,
    }


def run_once(
    *,
    formulation: str,
    case: BenchmarkCase,
    duration_s: int,
    config: SolverConfig,
) -> dict[str, Any]:
    model_start = perf_counter()
    pendulum = instantiate_model(
        formulation=formulation,
        case=case,
        duration_s=duration_s,
        config=config,
    )
    model_construction_and_solve_time_s = perf_counter() - model_start

    state = np.asarray(pendulum.sol, dtype=float)
    time_values = np.asarray(pendulum.solver_time, dtype=float)
    metadata = solver_metadata_dict(pendulum)
    common_count = min(len(state), len(time_values))
    state = state[:common_count]
    time_values = time_values[:common_count]

    position_start = perf_counter()
    positions = calculate_positions(case.parameters, state)
    position_reconstruction_time_s = perf_counter() - position_start

    if state.size:
        energy = simple_energy(case.parameters, state, formulation=formulation)
        energy_delta = energy - energy[0]
        final_energy_drift = float(energy_delta[-1])
        final_abs_energy_drift = float(abs(energy_delta[-1]))
        max_abs_energy_drift = float(np.max(np.abs(energy_delta)))
    else:
        final_energy_drift = float("nan")
        final_abs_energy_drift = float("nan")
        max_abs_energy_drift = float("nan")

    payload_start = perf_counter()
    payload = build_diagnostic_payload(
        case=case,
        formulation=formulation,
        config=config,
        duration_s=duration_s,
        time_values=time_values,
        state=state,
        positions=positions,
        metadata=metadata,
    )
    payload_preparation_time_s = perf_counter() - payload_start

    json_start = perf_counter()
    payload_json = json.dumps(payload, separators=(",", ":"), allow_nan=True)
    json_serialization_time_s = perf_counter() - json_start

    return {
        "model_construction_and_solve_time_s": model_construction_and_solve_time_s,
        "position_reconstruction_time_s": position_reconstruction_time_s,
        "payload_preparation_time_s": payload_preparation_time_s,
        "json_serialization_time_s": json_serialization_time_s,
        "total_runtime_s": (
            model_construction_and_solve_time_s
            + position_reconstruction_time_s
            + payload_preparation_time_s
            + json_serialization_time_s
        ),
        "json_payload_bytes": len(payload_json.encode("utf-8")),
        "payload_row_count": len(payload["frames"]),
        "nfev": metadata.get("nfev"),
        "success": metadata.get("success"),
        "status": metadata.get("status"),
        "message": metadata.get("message"),
        "returned_time_matches_requested": metadata.get("returned_time_matches_requested"),
        "final_energy_drift": final_energy_drift,
        "final_abs_energy_drift": final_abs_energy_drift,
        "max_abs_energy_drift": max_abs_energy_drift,
    }


def summarize_repeats(
    *,
    formulation: str,
    case: BenchmarkCase,
    duration_s: int,
    config: SolverConfig,
    repeats: list[dict[str, Any]],
) -> dict[str, Any]:
    def values(key: str) -> list[float]:
        return [float(row[key]) for row in repeats]

    nfev_values = [int(row["nfev"]) for row in repeats if row["nfev"] is not None]
    success_values = [row["success"] for row in repeats]
    statuses = sorted({str(row["status"]) for row in repeats})
    messages = sorted({str(row["message"]) for row in repeats})
    notes = [config.notes]
    notes.append("Class design combines construction, lambdify, and solve timing.")
    if duration_s >= 30:
        notes.append("Repeat count reduced for longer app-like runs.")

    return {
        "case_name": case.name,
        "case_description": case.description,
        "formulation": formulation,
        "solver_config": config.name,
        "solver_method": config.method or "solve_ivp_default",
        "rtol": config.rtol,
        "atol": config.atol,
        "duration_s": duration_s,
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "requested_sample_count": sample_count(duration_s),
        "repeat_count": len(repeats),
        "median_payload_row_count": median(values("payload_row_count")),
        "median_json_payload_bytes": median(values("json_payload_bytes")),
        "min_total_runtime_s": min(values("total_runtime_s")),
        "median_total_runtime_s": median(values("total_runtime_s")),
        "max_total_runtime_s": max(values("total_runtime_s")),
        "median_model_construction_and_solve_time_s": median(values("model_construction_and_solve_time_s")),
        "median_position_reconstruction_time_s": median(values("position_reconstruction_time_s")),
        "median_payload_preparation_time_s": median(values("payload_preparation_time_s")),
        "median_json_serialization_time_s": median(values("json_serialization_time_s")),
        "median_nfev": median(nfev_values) if nfev_values else None,
        "solver_success_all": all(value is True for value in success_values),
        "solver_statuses": statuses,
        "solver_messages": messages,
        "median_final_abs_energy_drift": median(values("final_abs_energy_drift")),
        "median_max_abs_energy_drift": median(values("max_abs_energy_drift")),
        "last_final_energy_drift": repeats[-1]["final_energy_drift"],
        "initial_conditions_user_units": list(case.initial_conditions_deg),
        "parameters": parameter_record(case.parameters),
        "notes": " ".join(notes),
    }


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    key: json_text(value) if isinstance(value, (dict, list, tuple)) else value
                    for key, value in record.items()
                }
            )


def write_json(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def warm_solver_caches() -> None:
    warm_case = cases()[0]
    warm_config = SolverConfig("warmup", "RK45", 1e-6, 1e-8, "Cache warmup.")
    for formulation in ("lagrangian", "hamiltonian"):
        instantiate_model(
            formulation=formulation,
            case=warm_case,
            duration_s=1,
            config=warm_config,
        )


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    warm_solver_caches()

    records: list[dict[str, Any]] = []
    durations = [10, 30, 60]
    formulations = ["lagrangian", "hamiltonian"]

    for case in cases():
        for duration_s in durations:
            repeat_count = repeat_count_for_duration(duration_s)
            for formulation in formulations:
                for config in solver_configs():
                    repeats = [
                        run_once(
                            formulation=formulation,
                            case=case,
                            duration_s=duration_s,
                            config=config,
                        )
                        for _ in range(repeat_count)
                    ]
                    records.append(
                        summarize_repeats(
                            formulation=formulation,
                            case=case,
                            duration_s=duration_s,
                            config=config,
                            repeats=repeats,
                        )
                    )

    write_csv(LOG_DIR / "app_like_cost_benchmark.csv", records)
    write_json(LOG_DIR / "app_like_cost_benchmark.json", records)
    print(f"Wrote {len(records)} app-like benchmark rows to {LOG_DIR / 'app_like_cost_benchmark.csv'}")
    print(f"Wrote JSON app-like benchmark log to {LOG_DIR / 'app_like_cost_benchmark.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
