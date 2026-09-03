"""Run the frozen Experiment 014 EL-only 1280-second convergence protocol."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping

import numpy as np


EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
EXPERIMENTS_ROOT = EXPERIMENT_ROOT.parent


def _load_module(name: str, relative_path: str) -> Any:
    path = EXPERIMENTS_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


experiment012 = _load_module(
    "experiment012_for_014",
    "012_initial_condition_spectrum_robustness/initial_condition_spectrum_robustness.py",
)
experiment013 = _load_module(
    "experiment013_for_014",
    "013_restart_grade_qr_continuation/restart_grade_qr_continuation.py",
)
experiment007 = experiment012.experiment007
experiment006 = experiment012.experiment006
experiment011 = experiment012.experiment011


EXPERIMENT_NAME = "unsettled_shadow_duration_convergence"
FORMULATION = "euler_lagrange"
CONDITIONS = (
    {
        "id": "ic_1",
        "label": "IC-1",
        "state_degrees": [-120.0, 0.0, 0.0, 0.0],
        "state_radians": [float(np.deg2rad(-120.0)), 0.0, 0.0, 0.0],
        "analytical_energy_joules": 0.0,
    },
    {
        "id": "ic_3",
        "label": "IC-3",
        "state_degrees": [120.0, -120.0, 0.0, 0.0],
        "state_radians": [
            float(np.deg2rad(120.0)),
            float(np.deg2rad(-120.0)),
            0.0,
            0.0,
        ],
        "analytical_energy_joules": 14.715,
    },
)
SHADOW_NAMES = ("baseline", "strict", "half_step")
TOTAL_DURATION_SECONDS = 1280.0
QR_INTERVAL_SECONDS = 0.25
CHECKPOINTS_SECONDS = (320.0, 480.0, 640.0, 800.0, 960.0, 1120.0, 1280.0)
LATE_CHECKPOINTS_SECONDS = (960.0, 1120.0, 1280.0)
DECORRELATION_DISTANCE = 1.0
INDEPENDENCE_DEADLINE_SECONDS = 960.0

MAX_CHANGE_960_TO_1120 = 0.08
MAX_CHANGE_1120_TO_1280 = 0.05
MAX_WITHIN_LATE_RANGE = 0.05
MAX_FINAL_BETWEEN_RANGE = 0.05
MAX_FINAL_BETWEEN_SAMPLE_STD = 0.025
MAX_ENSEMBLE_MEAN_CHANGE_1120_TO_1280 = 0.04
MAX_LATE_WINDOW_BETWEEN_RANGE = 0.07

NUMERICAL_LIMITS = dict(experiment012.NUMERICAL_LIMITS)


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shadow_specs() -> dict[str, tuple[Any, float]]:
    return experiment012.shadow_specs(FORMULATION)


def frozen_contract() -> dict[str, Any]:
    return {
        "experiment": EXPERIMENT_NAME,
        "research_question": (
            "For IC-1 and IC-3, does increasing the independently integrated EL "
            "averaging duration to 1280 seconds produce compatible cumulative QR "
            "spectrum estimates under the unchanged protocol?"
        ),
        "formulation": FORMULATION,
        "conditions": CONDITIONS,
        "duration_seconds": TOTAL_DURATION_SECONDS,
        "qr_interval_seconds": QR_INTERVAL_SECONDS,
        "analysis_and_restart_checkpoints_seconds": CHECKPOINTS_SECONDS,
        "late_checkpoints_seconds": LATE_CHECKPOINTS_SECONDS,
        "shadow_policies": {
            name: experiment006.policy_dict(policy)
            | {"max_step_seconds": max_step}
            for name, (policy, max_step) in shadow_specs().items()
        },
        "settling_limits": {
            "maximum_change_960_to_1120_per_second": MAX_CHANGE_960_TO_1120,
            "maximum_change_1120_to_1280_per_second": MAX_CHANGE_1120_TO_1280,
            "maximum_within_960_1120_1280_range_per_second": MAX_WITHIN_LATE_RANGE,
            "maximum_final_between_range_per_second": MAX_FINAL_BETWEEN_RANGE,
            "maximum_final_between_sample_std_per_second": MAX_FINAL_BETWEEN_SAMPLE_STD,
            "maximum_ensemble_mean_change_1120_to_1280_per_second": (
                MAX_ENSEMBLE_MEAN_CHANGE_1120_TO_1280
            ),
            "maximum_between_range_across_late_checkpoints_per_second": (
                MAX_LATE_WINDOW_BETWEEN_RANGE
            ),
        },
        "numerical_limits": NUMERICAL_LIMITS,
        "decorrelation_distance": DECORRELATION_DISTANCE,
        "independence_deadline_seconds": INDEPENDENCE_DEADLINE_SECONDS,
        "workload": {
            "physical_conditions": 2,
            "formulations": 1,
            "policies_per_condition": 3,
            "integrations": 6,
            "simulated_formulation_seconds": 7680.0,
            "qr_cycles": 30720,
            "checkpoint_spectrum_vectors": 42,
            "canonical_runs": 0,
        },
        "restart_schema": {
            "name": experiment013.SCHEMA_NAME,
            "version": experiment013.SCHEMA_VERSION,
            "checkpoint_every_declared_analysis_time": True,
        },
    }


def pre_execution_gate() -> dict[str, Any]:
    contract = frozen_contract()
    expected_states = {
        "ic_1": [-2.0943951023931953, 0.0, 0.0, 0.0],
        "ic_3": [2.0943951023931953, -2.0943951023931953, 0.0, 0.0],
    }
    specs = shadow_specs()
    checks = {
        "exactly_two_outcome_conditioned_states": [item["id"] for item in CONDITIONS]
        == ["ic_1", "ic_3"],
        "exact_states_and_zero_velocities": all(
            np.array_equal(
                np.asarray(item["state_radians"]), np.asarray(expected_states[item["id"]])
            )
            and item["state_radians"][2:] == [0.0, 0.0]
            for item in CONDITIONS
        ),
        "analytical_energies_match": all(
            math.isclose(
                float(experiment006.simple_energy(item["state_radians"])),
                item["analytical_energy_joules"],
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
            for item in CONDITIONS
        ),
        "el_only_no_canonical_path": contract["formulation"] == FORMULATION
        and contract["workload"]["canonical_runs"] == 0,
        "exact_three_policies": tuple(specs) == SHADOW_NAMES,
        "exact_policy_values": (
            experiment006.policy_dict(specs["baseline"][0])
            == {
                "name": "simple_reference",
                "method": "DOP853",
                "rtol": 1.0e-9,
                "atol": 1.0e-11,
                "role": "high-fidelity simple-model reference",
            }
            and specs["baseline"][1] == 0.0099773571
            and experiment006.policy_dict(specs["strict"][0])["rtol"] == 1.0e-11
            and experiment006.policy_dict(specs["strict"][0])["atol"] == 1.0e-13
            and specs["strict"][1] == 0.0099773571
            and specs["half_step"][1] == 0.00498867855
        ),
        "duration_and_checkpoints_exact": TOTAL_DURATION_SECONDS == 1280.0
        and CHECKPOINTS_SECONDS
        == (320.0, 480.0, 640.0, 800.0, 960.0, 1120.0, 1280.0),
        "qr_interval_exact": QR_INTERVAL_SECONDS == 0.25,
        "late_definitions_frozen": LATE_CHECKPOINTS_SECONDS
        == (960.0, 1120.0, 1280.0),
        "inherited_absolute_limits_exact": (
            MAX_CHANGE_960_TO_1120 == 0.08
            and MAX_CHANGE_1120_TO_1280 == 0.05
            and MAX_WITHIN_LATE_RANGE == 0.05
            and MAX_FINAL_BETWEEN_RANGE == 0.05
            and MAX_FINAL_BETWEEN_SAMPLE_STD == 0.025
            and MAX_ENSEMBLE_MEAN_CHANGE_1120_TO_1280 == 0.04
            and MAX_LATE_WINDOW_BETWEEN_RANGE == 0.07
        ),
        "workload_exact": contract["workload"]
        == {
            "physical_conditions": 2,
            "formulations": 1,
            "policies_per_condition": 3,
            "integrations": 6,
            "simulated_formulation_seconds": 7680.0,
            "qr_cycles": 30720,
            "checkpoint_spectrum_vectors": 42,
            "canonical_runs": 0,
        },
        "restart_schema_is_accepted_013": contract["restart_schema"]
        == {
            "name": "chaos_tangent_qr_boundary_restart",
            "version": 1,
            "checkpoint_every_declared_analysis_time": True,
        },
    }
    return {"accepted": all(checks.values()), "checks": checks, "contract": contract}


def classify_condition(
    *, numerical_valid: bool, settled: bool, independence_demonstrated: bool
) -> str:
    if not numerical_valid:
        return "numerically_invalid"
    if not settled:
        return "numerically_valid_but_still_unsettled_at_1280_seconds"
    if independence_demonstrated:
        return "numerically_valid_settled_at_1280_with_demonstrated_shadow_independence"
    return "numerically_valid_settled_at_1280_without_demonstrated_shadow_independence"


def experiment_level_verdict(categories: Mapping[str, str]) -> str:
    if any(value == "numerically_invalid" for value in categories.values()):
        return "numerical_invalidity"
    settled_categories = {
        "numerically_valid_settled_at_1280_with_demonstrated_shadow_independence",
        "numerically_valid_settled_at_1280_without_demonstrated_shadow_independence",
    }
    settled = {key: value in settled_categories for key, value in categories.items()}
    if all(settled.values()):
        return "both_conditions_settle_at_1280_seconds"
    if settled.get("ic_1"):
        return "only_ic_1_settles_at_1280_seconds"
    if settled.get("ic_3"):
        return "only_ic_3_settles_at_1280_seconds"
    return "neither_condition_settles_at_1280_seconds"


def project_level_implication(verdict: str) -> str:
    if verdict == "both_conditions_settle_at_1280_seconds":
        return (
            "Long-time spectrum estimation remains usable for the selected difficult "
            "conditions, but adequate duration may be substantially longer than 640 s."
        )
    if verdict == "numerical_invalidity":
        return (
            "The mapping contract cannot be decided because Experiment 014 exposed "
            "numerical invalidity rather than a settling result."
        )
    return (
        "Asymptotic settling at every future map pixel is not a practical or "
        "scientifically justified contract; future map work should use a clearly "
        "labelled fixed-horizon finite-time Lyapunov/stretching observable."
    )


def _segment_public_summary(run: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "accepted",
        "start_time_seconds",
        "integration_span_seconds",
        "elapsed_time_seconds",
        "qr_interval_seconds",
        "solver_policy",
        "max_step_seconds",
        "cycle_count",
        "segment_cycle_count",
        "completed_cycle_count_at_start",
        "continued_from_qr_boundary",
        "diagnostic_energy_baseline_joules",
        "final_cumulative_log_growth",
        "final_diagnostic_spectrum_per_second",
        "maximum_normalized_reference_energy_drift",
        "maximum_q_orthonormality_error",
        "maximum_scaled_reconstruction_relative_error",
        "maximum_physical_reconstruction_relative_error",
        "maximum_post_metric_orthonormality_error",
        "maximum_reset_map_error",
        "minimum_r_diagonal",
        "maximum_pre_qr_condition_number",
        "cumulative_bookkeeping_error",
        "spectrum_bookkeeping_error",
        "solver_statistics",
        "checks",
    )
    return {key: run[key] for key in keys}


def _write_segment_evidence(path: Path, run: Mapping[str, Any]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    summary_path = path / "segment_summary.json"
    reference_path = path / "reference_samples.npz"
    cycles_path = path / "cycles.csv"
    write_json(summary_path, _segment_public_summary(run))
    np.savez(
        reference_path,
        time_seconds=np.asarray(run["_reference_time"], dtype=np.float64),
        reference_state=np.asarray(run["_reference_state"], dtype=np.float64),
    )
    fields = [
        "cycle_index",
        "start_time_seconds",
        "end_time_seconds",
        "accepted",
        "segment_maximum_normalized_reference_energy_drift",
        "pre_qr_condition_number",
        "minimum_r_diagonal",
        "q_orthonormality_error",
        "scaled_reconstruction_relative_error",
        "physical_reconstruction_relative_error",
        "post_metric_orthonormality_error",
        "reset_map_error",
        *[f"cycle_log_{index}" for index in range(1, 5)],
        *[f"cumulative_log_{index}" for index in range(1, 5)],
    ]
    with cycles_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for cycle in run["cycles"]:
            row = {
                "cycle_index": cycle["cycle_index"],
                "start_time_seconds": cycle["start_time_seconds"],
                "end_time_seconds": cycle["end_time_seconds"],
                "accepted": cycle["accepted"],
                "segment_maximum_normalized_reference_energy_drift": cycle[
                    "segment_maximum_normalized_reference_energy_drift"
                ],
                "pre_qr_condition_number": cycle["pre_qr_condition_number"],
                "minimum_r_diagonal": min(cycle["r_diagonal"]),
                "q_orthonormality_error": cycle["q_orthonormality_error"],
                "scaled_reconstruction_relative_error": cycle[
                    "scaled_reconstruction_relative_error"
                ],
                "physical_reconstruction_relative_error": cycle[
                    "physical_reconstruction_relative_error"
                ],
                "post_metric_orthonormality_error": cycle[
                    "post_metric_orthonormality_error"
                ],
                "reset_map_error": cycle["reset_map_error"],
            }
            for index, value in enumerate(cycle["cycle_log_growth"], start=1):
                row[f"cycle_log_{index}"] = value
            for index, value in enumerate(cycle["cumulative_log_growth"], start=1):
                row[f"cumulative_log_{index}"] = value
            writer.writerow(row)
    write_json(
        path / "segment_manifest.json",
        {
            "files": {
                file.name: {
                    "bytes": file.stat().st_size,
                    "sha256": sha256_file(file),
                }
                for file in (summary_path, reference_path, cycles_path)
            }
        },
    )


def _verify_segment_evidence(path: Path) -> None:
    manifest_path = path / "segment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, record in manifest["files"].items():
        file = path / name
        if file.stat().st_size != record["bytes"] or sha256_file(file) != record["sha256"]:
            raise RuntimeError(f"Segment evidence integrity failed: {file}")


def _run_segment(
    condition: Mapping[str, Any],
    shadow: str,
    policy: Any,
    max_step: float,
    start_time: float,
    end_time: float,
    restart_state: Any | None,
) -> dict[str, Any]:
    run_id = f"{condition['id']}_{shadow}_{int(start_time)}_{int(end_time)}s"
    if restart_state is None:
        return experiment007.run_qr_primitive(
            experiment006.VariationalDynamics(),
            run_id=run_id,
            duration=end_time,
            qr_interval=QR_INTERVAL_SECONDS,
            policy=policy,
            max_step=max_step,
            initial_reference=np.asarray(condition["state_radians"], dtype=float),
        )
    return experiment013.resume_from_restart(
        restart_state,
        additional_duration_seconds=end_time - start_time,
        run_id=run_id,
    )


def _checkpoint_path(run_root: Path, checkpoint: float) -> Path:
    return run_root / "restart_checkpoints" / f"{int(checkpoint)}s"


def _segment_path(run_root: Path, checkpoint: float) -> Path:
    return run_root / "segments" / f"through_{int(checkpoint)}s"


def _checkpoint_complete(run_root: Path, checkpoint: float) -> bool:
    return (
        (_checkpoint_path(run_root, checkpoint) / experiment013.CHECKPOINT_MANIFEST_FILE).exists()
        and (_segment_path(run_root, checkpoint) / "segment_manifest.json").exists()
    )


def execute_shadow(
    condition: Mapping[str, Any], shadow: str, output_root: Path
) -> None:
    policy, max_step = shadow_specs()[shadow]
    run_root = output_root / condition["id"] / shadow
    restart_state = None
    previous = 0.0
    for checkpoint in CHECKPOINTS_SECONDS:
        checkpoint_path = _checkpoint_path(run_root, checkpoint)
        segment_path = _segment_path(run_root, checkpoint)
        if _checkpoint_complete(run_root, checkpoint):
            _verify_segment_evidence(segment_path)
            restart_state = experiment013.load_restart_checkpoint(
                checkpoint_path,
                expected_formulation=FORMULATION,
                expected_policy=policy,
                expected_max_step=max_step,
                expected_qr_interval=QR_INTERVAL_SECONDS,
            )
            print(
                f"SKIP {condition['label']} {shadow} checkpoint {int(checkpoint)}s",
                flush=True,
            )
            previous = checkpoint
            continue
        if previous > 0.0 and restart_state is None:
            raise RuntimeError("Missing prior restart state for a continuation segment.")
        print(
            f"START {condition['label']} {shadow} {int(previous)}→{int(checkpoint)}s",
            flush=True,
        )
        run = _run_segment(
            condition,
            shadow,
            policy,
            max_step,
            previous,
            checkpoint,
            restart_state,
        )
        if not run["accepted"]:
            raise RuntimeError(
                f"Numerically invalid segment for {condition['label']} {shadow} "
                f"through {checkpoint}s: {run['checks']}"
            )
        _write_segment_evidence(segment_path, run)
        checkpoint_state = experiment013.restart_state_from_run(
            run,
            formulation=FORMULATION,
            physical_initial_condition=condition,
            policy_name=shadow,
        )
        experiment013.save_restart_checkpoint(checkpoint_path, checkpoint_state)
        restart_state = experiment013.load_restart_checkpoint(
            checkpoint_path,
            expected_formulation=FORMULATION,
            expected_policy=policy,
            expected_max_step=max_step,
            expected_qr_interval=QR_INTERVAL_SECONDS,
        )
        if restart_state.metadata["elapsed_time_seconds"] != checkpoint:
            raise RuntimeError("Restart checkpoint elapsed time changed.")
        print(
            f"DONE  {condition['label']} {shadow} checkpoint {int(checkpoint)}s",
            flush=True,
        )
        previous = checkpoint


def _load_reference_series(run_root: Path) -> tuple[np.ndarray, np.ndarray]:
    times: list[np.ndarray] = []
    states: list[np.ndarray] = []
    for index, checkpoint in enumerate(CHECKPOINTS_SECONDS):
        path = _segment_path(run_root, checkpoint) / "reference_samples.npz"
        with np.load(path, allow_pickle=False) as values:
            segment_time = np.array(values["time_seconds"], copy=True)
            segment_state = np.array(values["reference_state"], copy=True)
        if index > 0:
            segment_time = segment_time[1:]
            segment_state = segment_state[1:]
        times.append(segment_time)
        states.append(segment_state)
    return np.concatenate(times), np.concatenate(states)


def _aggregate_numerical_validity(run_root: Path) -> dict[str, Any]:
    summaries = [
        json.loads(
            (_segment_path(run_root, checkpoint) / "segment_summary.json").read_text(
                encoding="utf-8"
            )
        )
        for checkpoint in CHECKPOINTS_SECONDS
    ]
    extrema = {
        "maximum_normalized_reference_energy_drift": max(
            item["maximum_normalized_reference_energy_drift"] for item in summaries
        ),
        "maximum_q_orthonormality_error": max(
            item["maximum_q_orthonormality_error"] for item in summaries
        ),
        "maximum_scaled_reconstruction_relative_error": max(
            item["maximum_scaled_reconstruction_relative_error"] for item in summaries
        ),
        "maximum_physical_reconstruction_relative_error": max(
            item["maximum_physical_reconstruction_relative_error"] for item in summaries
        ),
        "maximum_post_metric_orthonormality_error": max(
            item["maximum_post_metric_orthonormality_error"] for item in summaries
        ),
        "maximum_reset_map_error": max(item["maximum_reset_map_error"] for item in summaries),
        "minimum_r_diagonal": min(item["minimum_r_diagonal"] for item in summaries),
        "maximum_pre_qr_condition_number": max(
            item["maximum_pre_qr_condition_number"] for item in summaries
        ),
        "maximum_cumulative_bookkeeping_error": max(
            item["cumulative_bookkeeping_error"] for item in summaries
        ),
        "maximum_spectrum_bookkeeping_error": max(
            item["spectrum_bookkeeping_error"] for item in summaries
        ),
        "accounted_qr_cycles": sum(item["segment_cycle_count"] for item in summaries),
        "all_segments_accepted": all(item["accepted"] for item in summaries),
    }
    qr_limit = NUMERICAL_LIMITS["qr_reconstruction_orthonormality_bookkeeping"]
    checks = {
        "all_segments_accepted": extrema["all_segments_accepted"],
        "all_5120_cycles_accounted": extrema["accounted_qr_cycles"] == 5120,
        "energy_drift_within_1e-7": extrema[
            "maximum_normalized_reference_energy_drift"
        ]
        <= NUMERICAL_LIMITS["normalized_energy_drift"],
        "qr_and_bookkeeping_within_1e-12": max(
            extrema["maximum_q_orthonormality_error"],
            extrema["maximum_scaled_reconstruction_relative_error"],
            extrema["maximum_physical_reconstruction_relative_error"],
            extrema["maximum_post_metric_orthonormality_error"],
            extrema["maximum_reset_map_error"],
            extrema["maximum_cumulative_bookkeeping_error"],
            extrema["maximum_spectrum_bookkeeping_error"],
        )
        <= qr_limit,
        "minimum_r_diagonal_at_least_1e-14": extrema["minimum_r_diagonal"]
        >= NUMERICAL_LIMITS["minimum_positive_r_diagonal"],
        "pre_qr_condition_at_most_1e12": extrema[
            "maximum_pre_qr_condition_number"
        ]
        <= NUMERICAL_LIMITS["maximum_pre_qr_condition_number"],
    }
    return {"accepted": all(checks.values()), "checks": checks, "extrema": extrema}


def load_shadow_result(
    condition: Mapping[str, Any], shadow: str, output_root: Path
) -> dict[str, Any]:
    run_root = output_root / condition["id"] / shadow
    policy, max_step = shadow_specs()[shadow]
    checkpoints: dict[str, np.ndarray] = {}
    checkpoint_restart_verified: dict[str, bool] = {}
    for checkpoint in CHECKPOINTS_SECONDS:
        state = experiment013.load_restart_checkpoint(
            _checkpoint_path(run_root, checkpoint),
            expected_formulation=FORMULATION,
            expected_policy=policy,
            expected_max_step=max_step,
            expected_qr_interval=QR_INTERVAL_SECONDS,
        )
        checkpoints[f"{int(checkpoint)}s"] = (
            state.cumulative_log_growth / checkpoint
        )
        checkpoint_restart_verified[f"{int(checkpoint)}s"] = True
    time, reference = _load_reference_series(run_root)
    numerical = _aggregate_numerical_validity(run_root)
    change_960_1120 = np.abs(checkpoints["1120s"] - checkpoints["960s"])
    change_1120_1280 = np.abs(checkpoints["1280s"] - checkpoints["1120s"])
    late_values = np.asarray([checkpoints[f"{int(value)}s"] for value in LATE_CHECKPOINTS_SECONDS])
    late_range = np.ptp(late_values, axis=0)
    checks = {
        "960_to_1120_change_within_0.08_per_second": bool(
            np.all(change_960_1120 <= MAX_CHANGE_960_TO_1120)
        ),
        "1120_to_1280_change_within_0.05_per_second": bool(
            np.all(change_1120_1280 <= MAX_CHANGE_1120_TO_1280)
        ),
        "960_1120_1280_range_within_0.05_per_second": bool(
            np.all(late_range <= MAX_WITHIN_LATE_RANGE)
        ),
    }
    within = {
        "accepted": all(checks.values()),
        "checks": checks,
        "component_change_960_to_1120_per_second": change_960_1120,
        "maximum_change_960_to_1120_per_second": float(np.max(change_960_1120)),
        "component_change_1120_to_1280_per_second": change_1120_1280,
        "maximum_change_1120_to_1280_per_second": float(np.max(change_1120_1280)),
        "late_component_range_per_second": late_range,
        "maximum_late_component_range_per_second": float(np.max(late_range)),
    }
    result = {
        "shadow": shadow,
        "solver_policy": experiment006.policy_dict(policy),
        "max_step_seconds": max_step,
        "checkpoint_spectra_per_second": checkpoints,
        "restart_checkpoints_verified": checkpoint_restart_verified,
        "numerical_validity": numerical,
        "within_shadow_settling": within,
        "final_spectrum_per_second": checkpoints["1280s"],
        "_reference_time": time,
        "_reference_state": reference,
    }
    write_json(
        run_root / "run_summary.json",
        {key: value for key, value in result.items() if not key.startswith("_")},
    )
    return result


def between_shadow_analysis(runs: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    checkpoint_statistics: dict[str, Any] = {}
    means: dict[str, np.ndarray] = {}
    for checkpoint in CHECKPOINTS_SECONDS:
        key = f"{int(checkpoint)}s"
        values = np.asarray(
            [run["checkpoint_spectra_per_second"][key] for run in runs.values()]
        )
        ranges = np.ptp(values, axis=0)
        std = np.std(values, axis=0, ddof=1)
        mean = np.mean(values, axis=0)
        means[key] = mean
        checkpoint_statistics[key] = {
            "ensemble_mean_per_second": mean,
            "component_range_per_second": ranges,
            "maximum_component_range_per_second": float(np.max(ranges)),
            "sample_standard_deviation_per_second": std,
            "maximum_sample_standard_deviation_per_second": float(np.max(std)),
            "ensemble_mean_hamiltonian_diagnostics": (
                experiment007.hamiltonian_structure_diagnostics(mean)
            ),
        }
    final_values = np.asarray(
        [run["checkpoint_spectra_per_second"]["1280s"] for run in runs.values()]
    )
    final_ranges = np.ptp(final_values, axis=0)
    final_std = np.std(final_values, axis=0, ddof=1)
    mean_drift = np.abs(means["1280s"] - means["1120s"])
    late_ranges = np.asarray(
        [
            checkpoint_statistics[f"{int(value)}s"]["component_range_per_second"]
            for value in LATE_CHECKPOINTS_SECONDS
        ]
    )
    maximum_late_component_range = np.max(late_ranges, axis=0)
    per_shadow_terminal_changes = np.asarray(
        [
            np.abs(
                run["checkpoint_spectra_per_second"]["1280s"]
                - run["checkpoint_spectra_per_second"]["1120s"]
            )
            for run in runs.values()
        ]
    )
    width = np.maximum.reduce(
        [final_std, final_ranges / 2.0, np.max(per_shadow_terminal_changes, axis=0)]
    )
    checks = {
        "final_component_ranges_within_0.05_per_second": bool(
            np.all(final_ranges <= MAX_FINAL_BETWEEN_RANGE)
        ),
        "final_sample_std_within_0.025_per_second": bool(
            np.all(final_std <= MAX_FINAL_BETWEEN_SAMPLE_STD)
        ),
        "ensemble_mean_change_1120_to_1280_within_0.04_per_second": bool(
            np.all(mean_drift <= MAX_ENSEMBLE_MEAN_CHANGE_1120_TO_1280)
        ),
        "late_checkpoint_between_ranges_within_0.07_per_second": bool(
            np.all(maximum_late_component_range <= MAX_LATE_WINDOW_BETWEEN_RANGE)
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "checkpoint_statistics": checkpoint_statistics,
        "final_ensemble_mean_per_second": means["1280s"],
        "final_component_range_per_second": final_ranges,
        "final_sample_standard_deviation_per_second": final_std,
        "ensemble_mean_change_1120_to_1280_per_second": mean_drift,
        "maximum_ensemble_mean_change_1120_to_1280_per_second": float(np.max(mean_drift)),
        "maximum_late_checkpoint_component_range_per_second": (
            maximum_late_component_range
        ),
        "maximum_late_checkpoint_between_range_per_second": float(
            np.max(maximum_late_component_range)
        ),
        "final_descriptive_uncertainty_half_width_per_second": width,
        "uncertainty_definition": (
            "maximum of final sample SD, half final range, and largest absolute "
            "per-shadow 1120-to-1280 change"
        ),
        "trend_role": "descriptive only; no fitted convergence law or acceptance criterion",
    }


def reference_independence_analysis(
    runs: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    names = list(runs)
    common_time = np.asarray(runs[names[0]]["_reference_time"])
    if not all(
        np.array_equal(common_time, np.asarray(runs[name]["_reference_time"]))
        for name in names[1:]
    ):
        raise RuntimeError("Reference sample times differ across shadow policies.")
    scale = experiment011.candidate_a_scaling_matrix()
    pairs: dict[str, Any] = {}
    series: dict[str, np.ndarray] = {}
    for first, second in combinations(names, 2):
        name = f"{first}_vs_{second}"
        difference = np.asarray(runs[first]["_reference_state"]) - np.asarray(
            runs[second]["_reference_state"]
        )
        difference[:, :2] = experiment006.wrap_angle_difference(difference[:, :2])
        distance = np.linalg.norm(difference @ scale.T, axis=1)
        indices = np.flatnonzero(distance >= DECORRELATION_DISTANCE)
        crossing = float(common_time[int(indices[0])]) if len(indices) else None
        pairs[name] = {
            "first_threshold_crossing_seconds": crossing,
            "crossed_by_960_seconds": bool(
                crossing is not None and crossing <= INDEPENDENCE_DEADLINE_SECONDS
            ),
            "final_candidate_a_distance": float(distance[-1]),
            "maximum_candidate_a_distance": float(np.max(distance)),
        }
        series[name] = distance
    demonstrated = all(item["crossed_by_960_seconds"] for item in pairs.values())
    return {
        "demonstrated": demonstrated,
        "status": (
            "demonstrated_before_late_window"
            if demonstrated
            else "not_demonstrated_before_late_window"
        ),
        "distance_threshold": DECORRELATION_DISTANCE,
        "deadline_seconds": INDEPENDENCE_DEADLINE_SECONDS,
        "pairs": pairs,
        "_time": common_time,
        "_series": series,
    }


def _write_pair_distances(path: Path, independence: Mapping[str, Any]) -> None:
    series = independence["_series"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["time_seconds", *series]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, time in enumerate(independence["_time"]):
            writer.writerow(
                {"time_seconds": time}
                | {name: values[index] for name, values in series.items()}
            )


def analyze_condition(
    condition: Mapping[str, Any], output_root: Path
) -> dict[str, Any]:
    runs = {
        shadow: load_shadow_result(condition, shadow, output_root)
        for shadow in SHADOW_NAMES
    }
    between = between_shadow_analysis(runs)
    independence = reference_independence_analysis(runs)
    numerical_valid = all(run["numerical_validity"]["accepted"] for run in runs.values())
    settled = all(run["within_shadow_settling"]["accepted"] for run in runs.values()) and between[
        "accepted"
    ]
    category = classify_condition(
        numerical_valid=numerical_valid,
        settled=settled,
        independence_demonstrated=independence["demonstrated"],
    )
    public_runs = {
        name: {key: value for key, value in run.items() if not key.startswith("_")}
        for name, run in runs.items()
    }
    public_independence = {
        key: value for key, value in independence.items() if not key.startswith("_")
    }
    result = {
        "initial_condition": condition,
        "numerical_valid": numerical_valid,
        "settled": settled,
        "shadow_independence": public_independence,
        "runs": public_runs,
        "between_shadow": between,
        "outcome_category": category,
    }
    condition_root = output_root / condition["id"]
    _write_pair_distances(condition_root / "reference_pair_distances.csv", independence)
    write_json(condition_root / "condition_summary.json", result)
    return result


def write_manifest(output_root: Path) -> None:
    path = output_root / "manifest.json"
    files = sorted(item for item in output_root.rglob("*") if item.is_file() and item != path)
    write_json(
        path,
        {
            "experiment": EXPERIMENT_NAME,
            "source": str(Path(__file__).relative_to(REPOSITORY_ROOT)),
            "source_sha256": sha256_file(Path(__file__)),
            "files": [
                {
                    "path": str(item.relative_to(output_root)),
                    "bytes": item.stat().st_size,
                    "sha256": sha256_file(item),
                }
                for item in files
            ],
        },
    )


def run_experiment(output_root: Path) -> dict[str, Any]:
    gate = pre_execution_gate()
    write_json(output_root / "pre_execution_gate.json", gate)
    write_json(output_root / "frozen_contract.json", gate["contract"])
    if not gate["accepted"]:
        raise AssertionError(
            f"Experiment 014 pre-execution gate failed: "
            f"{[key for key, value in gate['checks'].items() if not value]}"
        )
    for condition in CONDITIONS:
        for shadow in SHADOW_NAMES:
            execute_shadow(condition, shadow, output_root)
    results = [analyze_condition(condition, output_root) for condition in CONDITIONS]
    categories = {
        item["initial_condition"]["id"]: item["outcome_category"] for item in results
    }
    verdict = experiment_level_verdict(categories)
    summary = {
        "experiment": EXPERIMENT_NAME,
        "status": "executed_frozen_protocol",
        "pre_execution_gate_accepted": True,
        "condition_results": results,
        "experiment_level_verdict": verdict,
        "project_level_map_implication": project_level_implication(verdict),
        "claim_boundary": (
            "Two outcome-conditioned EL-only initial conditions and three "
            "independent numerical policies through 1280 s; not infinite-time, "
            "canonical, global-map, or universal evidence."
        ),
    }
    write_json(output_root / "summary.json", summary)
    write_manifest(output_root)
    return summary


def verify_evidence(output_root: Path, summary: Mapping[str, Any]) -> None:
    if len(summary["condition_results"]) != 2:
        raise AssertionError("Experiment 014 must retain exactly two conditions.")
    for condition in CONDITIONS:
        for shadow, (policy, max_step) in shadow_specs().items():
            for checkpoint in CHECKPOINTS_SECONDS:
                state = experiment013.load_restart_checkpoint(
                    _checkpoint_path(output_root / condition["id"] / shadow, checkpoint),
                    expected_formulation=FORMULATION,
                    expected_policy=policy,
                    expected_max_step=max_step,
                    expected_qr_interval=QR_INTERVAL_SECONDS,
                )
                if state.metadata["elapsed_time_seconds"] != checkpoint:
                    raise AssertionError("Checkpoint elapsed time mismatch.")
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = output_root / item["path"]
        if path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise AssertionError(f"Evidence hash mismatch: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "development/chaos_content/experiments/outputs/014"
            / "frozen_1280s"
        ),
    )
    parser.add_argument("--gate-only", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.gate_only:
        gate = pre_execution_gate()
        print(json.dumps(_jsonable(gate), indent=2, sort_keys=True))
        return 0 if gate["accepted"] else 1
    summary = run_experiment(args.output_dir)
    if args.self_check:
        verify_evidence(args.output_dir, summary)
    print(
        json.dumps(
            {
                "experiment_level_verdict": summary["experiment_level_verdict"],
                "condition_categories": {
                    item["initial_condition"]["id"]: item["outcome_category"]
                    for item in summary["condition_results"]
                },
                "project_level_map_implication": summary[
                    "project_level_map_implication"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
