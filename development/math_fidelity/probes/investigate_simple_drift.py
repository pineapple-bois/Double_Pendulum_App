#!/usr/bin/env python3
"""Investigate simple-model Lagrangian/Hamiltonian drift.

Run from the repository root:

    .venv/bin/python development/math_fidelity/probes/investigate_simple_drift.py

The probe imports the diagnostic source snapshot under
development/math_fidelity/snapshots/simple_model_source rather than the live
production package. Outputs are written to development/math_fidelity/logs and
development/math_fidelity/reports.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
LAB_ROOT = REPO_ROOT / "development" / "math_fidelity"
LOG_DIR = LAB_ROOT / "logs"
TIMESERIES_DIR = LOG_DIR / "timeseries"
REPORT_DIR = LAB_ROOT / "reports"
SNAPSHOT_SOURCE = LAB_ROOT / "snapshots" / "simple_model_source"

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/double_pendulum_math_fidelity_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/double_pendulum_math_fidelity_cache")
sys.path.insert(0, str(SNAPSHOT_SOURCE))

from double_pendulum_snapshot.math.functions import g, l1, l2, m1, m2  # noqa: E402
from double_pendulum_snapshot.models import (  # noqa: E402
    DoublePendulumHamiltonian,
    DoublePendulumLagrangian,
)


THETA_DIVERGENCE_THRESHOLDS_RAD = (1e-3, 1e-2, 1e-1)


@dataclass(frozen=True)
class ProbeCase:
    name: str
    description: str
    initial_conditions_deg: tuple[float, float, float, float]
    parameters: dict[Any, float]
    duration_s: float
    sample_count: int


@dataclass(frozen=True)
class SolverConfig:
    name: str
    method: str | None
    rtol: float | None
    atol: float | None

    def kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if self.method is not None:
            kwargs["method"] = self.method
        if self.rtol is not None:
            kwargs["rtol"] = self.rtol
        if self.atol is not None:
            kwargs["atol"] = self.atol
        return kwargs


def simple_energy(parameters: dict[Any, float], state: np.ndarray, *, state_kind: str) -> np.ndarray:
    """Return simple point-mass total energy for Lagrangian or Hamiltonian state."""

    theta_1 = state[:, 0]
    theta_2 = state[:, 1]
    if state_kind == "lagrangian":
        omega_1 = state[:, 2]
        omega_2 = state[:, 3]
    elif state_kind == "hamiltonian":
        omega_1, omega_2 = reconstruct_simple_omega(parameters, state)
    else:
        raise ValueError(f"unsupported state kind: {state_kind}")

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


def reconstruct_simple_omega(parameters: dict[Any, float], hamiltonian_state: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reconstruct omega from simple Hamiltonian canonical momenta."""

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


def first_divergence_time(time: np.ndarray, theta_abs_diff_by_sample: np.ndarray, threshold: float) -> float | None:
    matches = np.flatnonzero(theta_abs_diff_by_sample >= threshold)
    if len(matches) == 0:
        return None
    return float(time[int(matches[0])])


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


def run_pair(case: ProbeCase, config: SolverConfig) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    time_vector = [0.0, case.duration_s, case.sample_count]
    kwargs = config.kwargs()

    lagrangian_start = perf_counter()
    lagrangian = DoublePendulumLagrangian(
        case.parameters,
        list(case.initial_conditions_deg),
        time_vector,
        model="simple",
        **kwargs,
    )
    lagrangian_runtime_s = perf_counter() - lagrangian_start

    hamiltonian_start = perf_counter()
    hamiltonian = DoublePendulumHamiltonian(
        case.parameters,
        list(case.initial_conditions_deg),
        time_vector,
        model="simple",
        **kwargs,
    )
    hamiltonian_runtime_s = perf_counter() - hamiltonian_start

    lag_state = np.asarray(lagrangian.sol, dtype=float)
    ham_state = np.asarray(hamiltonian.sol, dtype=float)
    time = np.asarray(lagrangian.solver_time, dtype=float)

    common_count = min(len(lag_state), len(ham_state), len(time))
    lag_state = lag_state[:common_count]
    ham_state = ham_state[:common_count]
    time = time[:common_count]

    theta_diff = lag_state[:, :2] - ham_state[:, :2]
    theta_abs_diff_by_sample = np.max(np.abs(theta_diff), axis=1)
    final_theta_diff = theta_diff[-1].tolist()

    lag_positions = calculate_positions(case.parameters, lag_state)
    ham_positions = calculate_positions(case.parameters, ham_state)
    position_abs_diff_by_sample = np.max(np.abs(lag_positions - ham_positions), axis=1)
    second_bob_position_diff = np.sqrt(
        (lag_positions[:, 2] - ham_positions[:, 2]) ** 2
        + (lag_positions[:, 3] - ham_positions[:, 3]) ** 2
    )

    lag_energy = simple_energy(case.parameters, lag_state, state_kind="lagrangian")
    ham_energy = simple_energy(case.parameters, ham_state, state_kind="hamiltonian")
    lag_energy_delta = lag_energy - lag_energy[0]
    ham_energy_delta = ham_energy - ham_energy[0]

    divergence_times = {
        str(threshold): first_divergence_time(time, theta_abs_diff_by_sample, threshold)
        for threshold in THETA_DIVERGENCE_THRESHOLDS_RAD
    }

    lag_metadata = solver_metadata_dict(lagrangian)
    ham_metadata = solver_metadata_dict(hamiltonian)

    result = {
        "case_name": case.name,
        "case_description": case.description,
        "solver_config": config.name,
        "method": config.method or "solve_ivp_default",
        "rtol": config.rtol,
        "atol": config.atol,
        "duration_s": case.duration_s,
        "sample_count_requested": case.sample_count,
        "sample_count_compared": common_count,
        "initial_conditions_user_units": list(case.initial_conditions_deg),
        "parameters": parameter_record(case.parameters),
        "lagrangian_solver_success": lag_metadata.get("success"),
        "lagrangian_solver_status": lag_metadata.get("status"),
        "lagrangian_solver_message": lag_metadata.get("message"),
        "lagrangian_nfev": lag_metadata.get("nfev"),
        "lagrangian_runtime_s": lagrangian_runtime_s,
        "hamiltonian_solver_success": ham_metadata.get("success"),
        "hamiltonian_solver_status": ham_metadata.get("status"),
        "hamiltonian_solver_message": ham_metadata.get("message"),
        "hamiltonian_nfev": ham_metadata.get("nfev"),
        "hamiltonian_runtime_s": hamiltonian_runtime_s,
        "max_abs_theta_diff_rad": float(np.max(theta_abs_diff_by_sample)),
        "max_abs_theta_diff_deg": float(np.rad2deg(np.max(theta_abs_diff_by_sample))),
        "final_theta_diff_rad": final_theta_diff,
        "final_theta_diff_deg": np.rad2deg(final_theta_diff).tolist(),
        "max_bob_position_abs_diff": float(np.max(position_abs_diff_by_sample)),
        "divergence_time_s_by_theta_threshold_rad": divergence_times,
        "lagrangian_max_abs_energy_drift": float(np.max(np.abs(lag_energy_delta))),
        "hamiltonian_max_abs_energy_drift": float(np.max(np.abs(ham_energy_delta))),
        "lagrangian_final_energy_drift": float(lag_energy_delta[-1]),
        "hamiltonian_final_energy_drift": float(ham_energy_delta[-1]),
    }

    mapping = mapping_check(case, hamiltonian)
    mapping.update(
        {
            "case_name": case.name,
            "solver_config": config.name,
            "method": config.method or "solve_ivp_default",
            "rtol": config.rtol,
            "atol": config.atol,
        }
    )
    timeseries = timeseries_records(
        case=case,
        config=config,
        time=time,
        lag_state=lag_state,
        ham_state=ham_state,
        theta_diff=theta_diff,
        theta_abs_diff_by_sample=theta_abs_diff_by_sample,
        lag_positions=lag_positions,
        ham_positions=ham_positions,
        position_abs_diff_by_sample=position_abs_diff_by_sample,
        second_bob_position_diff=second_bob_position_diff,
        lag_energy=lag_energy,
        ham_energy=ham_energy,
        lag_energy_delta=lag_energy_delta,
        ham_energy_delta=ham_energy_delta,
    )
    return result, mapping, timeseries


def timeseries_records(
    *,
    case: ProbeCase,
    config: SolverConfig,
    time: np.ndarray,
    lag_state: np.ndarray,
    ham_state: np.ndarray,
    theta_diff: np.ndarray,
    theta_abs_diff_by_sample: np.ndarray,
    lag_positions: np.ndarray,
    ham_positions: np.ndarray,
    position_abs_diff_by_sample: np.ndarray,
    second_bob_position_diff: np.ndarray,
    lag_energy: np.ndarray,
    ham_energy: np.ndarray,
    lag_energy_delta: np.ndarray,
    ham_energy_delta: np.ndarray,
) -> list[dict[str, Any]]:
    lag_energy_denominator = max(abs(float(lag_energy[0])), 1e-12)
    ham_energy_denominator = max(abs(float(ham_energy[0])), 1e-12)
    rows: list[dict[str, Any]] = []
    for index, t_value in enumerate(time):
        rows.append(
            {
                "case_name": case.name,
                "solver_config": config.name,
                "solver_method": config.method or "solve_ivp_default",
                "rtol": config.rtol,
                "atol": config.atol,
                "t": float(t_value),
                "lagrangian_theta1_rad": float(lag_state[index, 0]),
                "lagrangian_theta2_rad": float(lag_state[index, 1]),
                "hamiltonian_theta1_rad": float(ham_state[index, 0]),
                "hamiltonian_theta2_rad": float(ham_state[index, 1]),
                "abs_theta1_diff_rad": float(abs(theta_diff[index, 0])),
                "abs_theta2_diff_rad": float(abs(theta_diff[index, 1])),
                "max_abs_theta_diff_rad": float(theta_abs_diff_by_sample[index]),
                "lagrangian_x2": float(lag_positions[index, 2]),
                "lagrangian_y2": float(lag_positions[index, 3]),
                "hamiltonian_x2": float(ham_positions[index, 2]),
                "hamiltonian_y2": float(ham_positions[index, 3]),
                "abs_x2_diff": float(abs(lag_positions[index, 2] - ham_positions[index, 2])),
                "abs_y2_diff": float(abs(lag_positions[index, 3] - ham_positions[index, 3])),
                "second_bob_position_diff": float(second_bob_position_diff[index]),
                "max_bob_position_abs_diff": float(position_abs_diff_by_sample[index]),
                "lagrangian_energy": float(lag_energy[index]),
                "lagrangian_energy_abs_drift": float(abs(lag_energy_delta[index])),
                "lagrangian_energy_signed_drift": float(lag_energy_delta[index]),
                "lagrangian_energy_relative_drift": float(lag_energy_delta[index] / lag_energy_denominator),
                "hamiltonian_energy": float(ham_energy[index]),
                "hamiltonian_energy_abs_drift": float(abs(ham_energy_delta[index])),
                "hamiltonian_energy_signed_drift": float(ham_energy_delta[index]),
                "hamiltonian_energy_relative_drift": float(ham_energy_delta[index] / ham_energy_denominator),
            }
        )
    return rows


def mapping_check(case: ProbeCase, hamiltonian: Any) -> dict[str, Any]:
    initial_state = np.asarray(hamiltonian.initial_conditions, dtype=float)
    reconstructed = np.asarray(
        reconstruct_simple_omega(case.parameters, initial_state.reshape(1, 4))
    ).reshape(2)
    expected = np.deg2rad(np.asarray(case.initial_conditions_deg[2:], dtype=float))
    return {
        "user_state_degrees": list(case.initial_conditions_deg),
        "converted_hamiltonian_state": initial_state.tolist(),
        "reconstructed_omega_rad_per_s": reconstructed.tolist(),
        "expected_omega_rad_per_s": expected.tolist(),
        "max_abs_reconstructed_omega_error": float(np.max(np.abs(reconstructed - expected))),
    }


def write_json(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {
                key: json_text(value) if isinstance(value, (dict, list, tuple)) else value
                for key, value in record.items()
            }
            writer.writerow(row)


def write_timeseries_logs(timeseries_records_by_run: dict[str, list[dict[str, Any]]]) -> None:
    TIMESERIES_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    for run_name, rows in timeseries_records_by_run.items():
        all_rows.extend(rows)
        write_csv(TIMESERIES_DIR / f"{run_name}.csv", rows)
    write_csv(TIMESERIES_DIR / "simple_drift_timeseries_long.csv", all_rows)


def markdown_summary(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Simple Drift Probe Summary",
        "",
        "Generated by `development/math_fidelity/probes/investigate_simple_drift.py`.",
        "",
        "| Case | Solver | Max theta diff (rad) | Max position diff | Lag energy drift | Ham energy drift | nfev L/H |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for record in records:
        lines.append(
            "| {case} | {solver} | {theta:.6g} | {pos:.6g} | {elag:.6g} | {eham:.6g} | {nfev_l}/{nfev_h} |".format(
                case=record["case_name"],
                solver=record["solver_config"],
                theta=record["max_abs_theta_diff_rad"],
                pos=record["max_bob_position_abs_diff"],
                elag=record["lagrangian_max_abs_energy_drift"],
                eham=record["hamiltonian_max_abs_energy_drift"],
                nfev_l=record["lagrangian_nfev"],
                nfev_h=record["hamiltonian_nfev"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def cases() -> list[ProbeCase]:
    unity = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
    spirograph_parameters = {l1: 1.0, l2: 1.5, m1: 3.0, m2: 1.0, g: 9.81}
    return [
        ProbeCase(
            name="low_energy_small_angles",
            description="Small angles released from rest; expected to be comparatively benign.",
            initial_conditions_deg=(5.0, 7.0, 0.0, 0.0),
            parameters=unity,
            duration_s=4.0,
            sample_count=800,
        ),
        ProbeCase(
            name="screenshot_like_simple_start",
            description="App preset-style simple case mentioned in historical discrepancy notes.",
            initial_conditions_deg=(0.0, 60.0, 0.0, 0.0),
            parameters=unity,
            duration_s=4.0,
            sample_count=800,
        ),
        ProbeCase(
            name="nonzero_velocity_spirograph",
            description="Historical nonzero angular-velocity example using non-unity lengths/masses.",
            initial_conditions_deg=(90.0, 0.0, 572.95, -458.37),
            parameters=spirograph_parameters,
            duration_s=1.0,
            sample_count=400,
        ),
        ProbeCase(
            name="higher_energy_wide_swing",
            description="Large separated angles plus nonzero velocities; more sensitive short run.",
            initial_conditions_deg=(120.0, -120.0, 120.0, -90.0),
            parameters=unity,
            duration_s=2.0,
            sample_count=600,
        ),
    ]


def solver_configs() -> list[SolverConfig]:
    return [
        SolverConfig("solve_ivp_default", None, None, None),
        SolverConfig("rk45_strict", "RK45", 1e-8, 1e-10),
        SolverConfig("dop853_moderate", "DOP853", 1e-6, 1e-8),
        SolverConfig("dop853_strict", "DOP853", 1e-9, 1e-11),
        SolverConfig("dop853_reference", "DOP853", 1e-11, 1e-13),
    ]


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    TIMESERIES_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    run_records: list[dict[str, Any]] = []
    mapping_records: list[dict[str, Any]] = []
    timeseries_records_by_run: dict[str, list[dict[str, Any]]] = {}
    for case in cases():
        for config in solver_configs():
            result, mapping, timeseries = run_pair(case, config)
            run_records.append(result)
            mapping_records.append(mapping)
            timeseries_records_by_run[f"{case.name}__{config.name}"] = timeseries

    write_json(LOG_DIR / "simple_drift_results.json", run_records)
    write_csv(LOG_DIR / "simple_drift_results.csv", run_records)
    write_json(LOG_DIR / "simple_drift_mapping_checks.json", mapping_records)
    write_csv(LOG_DIR / "simple_drift_mapping_checks.csv", mapping_records)
    write_timeseries_logs(timeseries_records_by_run)
    (REPORT_DIR / "simple_drift_summary.md").write_text(
        markdown_summary(run_records),
        encoding="utf-8",
    )

    print(f"Wrote {len(run_records)} run records to {LOG_DIR / 'simple_drift_results.csv'}")
    print(f"Wrote {len(mapping_records)} mapping checks to {LOG_DIR / 'simple_drift_mapping_checks.csv'}")
    print(f"Wrote {len(timeseries_records_by_run)} per-run time-series CSVs to {TIMESERIES_DIR}")
    print(f"Wrote combined time-series CSV to {TIMESERIES_DIR / 'simple_drift_timeseries_long.csv'}")
    print(f"Wrote summary table to {REPORT_DIR / 'simple_drift_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
