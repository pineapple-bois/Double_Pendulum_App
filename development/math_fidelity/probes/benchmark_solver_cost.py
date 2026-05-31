#!/usr/bin/env python3
"""Benchmark simple-model solver costs using the diagnostic source snapshot.

Run from the repository root:

    .venv/bin/python development/math_fidelity/probes/benchmark_solver_cost.py

The benchmark imports from development/math_fidelity/snapshots/simple_model_source
rather than the live production package. Outputs are written to
development/math_fidelity/logs.
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
APP_RELEVANT_DURATION_S = 60


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
        SolverConfig("solve_ivp_default", None, None, None, "Current default solve_ivp behavior."),
        SolverConfig("rk45_moderate", "RK45", 1e-6, 1e-8, "Moderate RK45 tolerance candidate."),
        SolverConfig("rk45_strict", "RK45", 1e-8, 1e-10, "Strict RK45 tolerance candidate."),
        SolverConfig("dop853_moderate", "DOP853", 1e-6, 1e-8, "Moderate DOP853 tolerance candidate."),
        SolverConfig("dop853_strict", "DOP853", 1e-9, 1e-11, "Strict DOP853 tolerance candidate."),
    ]


def repeat_count_for_duration(duration_s: int) -> int:
    if duration_s >= 60:
        return 2
    if duration_s >= 30:
        return 2
    return 3


def sample_count(duration_s: int) -> int:
    return int(duration_s * SAMPLE_RATE_HZ)


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


def run_once(
    *,
    formulation: str,
    case: BenchmarkCase,
    duration_s: int,
    config: SolverConfig,
) -> dict[str, Any]:
    start = perf_counter()
    pendulum = instantiate_model(
        formulation=formulation,
        case=case,
        duration_s=duration_s,
        config=config,
    )
    runtime_s = perf_counter() - start
    state = np.asarray(pendulum.sol, dtype=float)
    metadata = solver_metadata_dict(pendulum)

    if state.size:
        energy = simple_energy(case.parameters, state, formulation=formulation)
        energy_delta = energy - energy[0]
        final_energy_drift = float(energy_delta[-1])
        final_abs_energy_drift = float(abs(energy_delta[-1]))
        max_abs_energy_drift = float(np.max(np.abs(energy_delta)))
    else:
        final_energy_drift = np.nan
        final_abs_energy_drift = np.nan
        max_abs_energy_drift = np.nan

    return {
        "runtime_s": runtime_s,
        "nfev": metadata.get("nfev"),
        "success": metadata.get("success"),
        "status": metadata.get("status"),
        "message": metadata.get("message"),
        "returned_time_count": metadata.get("returned_time_count"),
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
    runtimes = [float(row["runtime_s"]) for row in repeats]
    nfev_values = [int(row["nfev"]) for row in repeats if row["nfev"] is not None]
    max_energy_drifts = [float(row["max_abs_energy_drift"]) for row in repeats]
    final_abs_energy_drifts = [float(row["final_abs_energy_drift"]) for row in repeats]
    sample_count_value = sample_count(duration_s)
    success_values = [row["success"] for row in repeats]
    statuses = sorted({str(row["status"]) for row in repeats})
    messages = sorted({str(row["message"]) for row in repeats})
    notes = [config.notes]
    if duration_s >= 30:
        notes.append("Repeat count reduced for longer app-relevance runs.")
    notes.append("Accuracy reference not computed in this cost benchmark; use drift logs for L/H agreement.")

    return {
        "case_name": case.name,
        "case_description": case.description,
        "formulation": formulation,
        "solver_config": config.name,
        "solver_method": config.method or "solve_ivp_default",
        "rtol": config.rtol,
        "atol": config.atol,
        "duration_s": duration_s,
        "sample_count": sample_count_value,
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "repeat_count": len(repeats),
        "min_runtime_s": min(runtimes),
        "median_runtime_s": median(runtimes),
        "max_runtime_s": max(runtimes),
        "min_nfev": min(nfev_values) if nfev_values else None,
        "median_nfev": median(nfev_values) if nfev_values else None,
        "max_nfev": max(nfev_values) if nfev_values else None,
        "solver_success_all": all(value is True for value in success_values),
        "solver_statuses": statuses,
        "solver_messages": messages,
        "median_final_abs_energy_drift": median(final_abs_energy_drifts),
        "median_max_abs_energy_drift": median(max_energy_drifts),
        "last_final_energy_drift": repeats[-1]["final_energy_drift"],
        "max_angular_drift_vs_reference_rad": None,
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
    durations = [5, 10, 30, 60]
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

    write_csv(LOG_DIR / "solver_cost_benchmark.csv", records)
    write_json(LOG_DIR / "solver_cost_benchmark.json", records)
    print(f"Wrote {len(records)} benchmark rows to {LOG_DIR / 'solver_cost_benchmark.csv'}")
    print(f"Wrote JSON benchmark log to {LOG_DIR / 'solver_cost_benchmark.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
