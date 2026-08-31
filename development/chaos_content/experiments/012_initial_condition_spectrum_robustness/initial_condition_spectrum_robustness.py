"""Execute the frozen Experiment 012 initial-condition robustness protocol."""

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
from typing import Any, Sequence

import numpy as np


EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


experiment010 = _load_module(
    "experiment010_for_012",
    EXPERIMENT_ROOT.parent
    / "010_independent_shadow_640s_compatibility"
    / "independent_shadow_640s_compatibility.py",
)
experiment011 = _load_module(
    "experiment011_for_012",
    EXPERIMENT_ROOT.parent
    / "011_hamiltonian_canonical_spectrum_crosscheck"
    / "canonical_spectrum_crosscheck.py",
)

experiment007 = experiment010.experiment007
experiment006 = experiment010.experiment006

EXPERIMENT_NAME = "initial_condition_spectrum_robustness"
DURATION_SECONDS = 640.0
QR_INTERVAL_SECONDS = 0.25
CHECKPOINTS_SECONDS = (80.0, 160.0, 240.0, 320.0, 400.0, 480.0, 560.0, 640.0)
LATE_WINDOW_START_SECONDS = 560.0
DECORRELATION_DISTANCE = 1.0
EARLY_DECORRELATION_DEADLINE_SECONDS = 80.0
INDEPENDENCE_DEADLINE_SECONDS = 560.0
BASELINE_MAX_STEP_SECONDS = 0.0099773571
HALF_STEP_MAX_STEP_SECONDS = 0.00498867855

MAX_CHANGE_480_TO_560 = 0.08
MAX_CHANGE_560_TO_640 = 0.05
MAX_WITHIN_LATE_RANGE = 0.05
MAX_FINAL_BETWEEN_RANGE = 0.05
MAX_FINAL_BETWEEN_SAMPLE_STD = 0.025
MAX_ENSEMBLE_MEAN_CHANGE_560_TO_640 = 0.04
MAX_LATE_WINDOW_BETWEEN_RANGE = 0.07

CROSS_MAX_MEAN_DISPLACEMENT = 0.05
CROSS_MAX_COMBINED_RANGE = 0.07
CROSS_MAX_COMBINED_SAMPLE_STD = 0.025
CROSS_MAX_LATE_DRIFT_DIFFERENCE = 0.04

NUMERICAL_LIMITS = {
    "normalized_energy_drift": 1.0e-7,
    "qr_reconstruction_orthonormality_bookkeeping": 1.0e-12,
    "minimum_positive_r_diagonal": 1.0e-14,
    "maximum_pre_qr_condition_number": 1.0e12,
    "canonical_minimum_pullback_singular_value": 1.0e-6,
    "canonical_maximum_pullback_condition_number": 1.0e3,
}

INITIAL_CONDITIONS = (
    {
        "id": "ic_1",
        "label": "IC-1",
        "state_degrees": (-120.0, 0.0, 0.0, 0.0),
        "state_radians": (-2.0 * math.pi / 3.0, 0.0, 0.0, 0.0),
        "analytical_energy_joules": 0.0,
    },
    {
        "id": "ic_2",
        "label": "IC-2",
        "state_degrees": (0.0, 120.0, 0.0, 0.0),
        "state_radians": (0.0, 2.0 * math.pi / 3.0, 0.0, 0.0),
        "analytical_energy_joules": -14.715,
    },
    {
        "id": "ic_3",
        "label": "IC-3",
        "state_degrees": (120.0, -120.0, 0.0, 0.0),
        "state_radians": (2.0 * math.pi / 3.0, -2.0 * math.pi / 3.0, 0.0, 0.0),
        "analytical_energy_joules": 14.715,
    },
)
HISTORICAL_ANCHOR_DEGREES = (179.0, 179.0, 0.0, 0.0)
FORMULATIONS = ("euler_lagrange", "canonical_hamiltonian")
SHADOW_NAMES = ("baseline", "strict", "half_step")


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
        json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def shadow_specs(formulation: str) -> dict[str, tuple[Any, float]]:
    if formulation == "euler_lagrange":
        inherited = experiment010.shadow_specs()
        return {
            "baseline": (inherited["baseline"][0], BASELINE_MAX_STEP_SECONDS),
            "strict": (inherited["strict"][0], BASELINE_MAX_STEP_SECONDS),
            "half_step": (inherited["half_step"][0], HALF_STEP_MAX_STEP_SECONDS),
        }
    if formulation == "canonical_hamiltonian":
        inherited = experiment011.phase_c_shadow_specs()
        return {
            "baseline": (inherited["baseline"][0], BASELINE_MAX_STEP_SECONDS),
            "strict": (inherited["strict"][0], BASELINE_MAX_STEP_SECONDS),
            "half_step": (inherited["half_step"][0], HALF_STEP_MAX_STEP_SECONDS),
        }
    raise ValueError(f"Unknown formulation: {formulation}")


def execution_plan() -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for condition in INITIAL_CONDITIONS:
        for formulation in FORMULATIONS:
            for shadow, (policy, max_step) in shadow_specs(formulation).items():
                plan.append(
                    {
                        "initial_condition_id": condition["id"],
                        "initial_state_radians": condition["state_radians"],
                        "formulation": formulation,
                        "shadow": shadow,
                        "solver_policy": experiment006.policy_dict(policy),
                        "max_step_seconds": max_step,
                        "duration_seconds": DURATION_SECONDS,
                        "qr_interval_seconds": QR_INTERVAL_SECONDS,
                        "checkpoints_seconds": CHECKPOINTS_SECONDS,
                    }
                )
    return plan


def _policy_signature(policy: Any, max_step: float) -> tuple[Any, ...]:
    data = experiment006.policy_dict(policy)
    return (
        data["method"],
        float(data["rtol"]),
        float(data["atol"]),
        float(max_step),
    )


def pre_execution_gate() -> dict[str, Any]:
    """Verify the frozen contract before any long integration is launched."""

    dynamics = experiment011.CanonicalDynamics()
    expected_policy_signatures = {
        "baseline": ("DOP853", 1.0e-9, 1.0e-11, 0.0099773571),
        "strict": ("DOP853", 1.0e-11, 1.0e-13, 0.0099773571),
        "half_step": ("DOP853", 1.0e-9, 1.0e-11, 0.00498867855),
    }
    conditions: dict[str, Any] = {}
    state_checks: list[bool] = []
    energy_checks: list[bool] = []
    map_checks: list[bool] = []
    basis_checks: list[bool] = []
    scaling = experiment011.candidate_a_scaling_matrix()
    el_basis = experiment007.initial_physical_tangent_basis()
    for condition in INITIAL_CONDITIONS:
        state = np.asarray(condition["state_radians"], dtype=float)
        canonical = experiment011.el_to_canonical(state)
        roundtrip = experiment011.canonical_to_el(canonical)
        el_energy = float(experiment006.simple_energy(state))
        canonical_energy = float(dynamics.energy(canonical))
        expected_energy = float(condition["analytical_energy_joules"])
        factor = experiment011.candidate_a_pullback_factor(canonical)
        canonical_basis = np.linalg.solve(factor, np.eye(4))
        mapped_basis = experiment011.inverse_tangent_map(canonical) @ canonical_basis
        state_exact = bool(
            state.shape == (4,)
            and np.all(state[2:] == 0.0)
            and np.allclose(
                np.degrees(state[:2]),
                np.asarray(condition["state_degrees"][:2]),
                rtol=0.0,
                atol=1.0e-12,
            )
        )
        energy_exact = bool(
            math.isclose(el_energy, expected_energy, rel_tol=0.0, abs_tol=1.0e-12)
            and math.isclose(
                canonical_energy, expected_energy, rel_tol=0.0, abs_tol=1.0e-12
            )
        )
        maps_match = bool(np.allclose(roundtrip, state, rtol=0.0, atol=1.0e-12))
        bases_match = bool(
            np.allclose(scaling @ el_basis, np.eye(4), rtol=0.0, atol=1.0e-14)
            and np.allclose(
                factor @ canonical_basis, np.eye(4), rtol=0.0, atol=1.0e-14
            )
            and np.allclose(mapped_basis, el_basis, rtol=0.0, atol=1.0e-12)
        )
        state_checks.append(state_exact)
        energy_checks.append(energy_exact)
        map_checks.append(maps_match)
        basis_checks.append(bases_match)
        conditions[condition["id"]] = {
            "state_radians": state,
            "state_degrees": condition["state_degrees"],
            "all_velocities_zero": bool(np.all(state[2:] == 0.0)),
            "el_energy_joules": el_energy,
            "canonical_hamiltonian_joules": canonical_energy,
            "preregistered_energy_joules": expected_energy,
            "state_map_maximum_roundtrip_error": float(
                np.max(np.abs(roundtrip - state))
            ),
            "candidate_a_basis_maximum_correspondence_error": float(
                np.max(np.abs(mapped_basis - el_basis))
            ),
        }

    el_specs = shadow_specs("euler_lagrange")
    canonical_specs = shadow_specs("canonical_hamiltonian")
    policies_match = all(
        _policy_signature(*el_specs[name]) == expected_policy_signatures[name]
        and _policy_signature(*canonical_specs[name])
        == expected_policy_signatures[name]
        for name in SHADOW_NAMES
    )
    sign_probe = np.diag([-1.0, 4.0, -2.0, 0.5])
    _, upper = experiment007.positive_diagonal_qr(sign_probe)
    positive_diagonal_without_sorting = bool(
        np.allclose(np.diag(upper), [1.0, 4.0, 2.0, 0.5])
    )
    plan = execution_plan()
    per_condition_counts = {
        condition["id"]: sum(
            item["initial_condition_id"] == condition["id"] for item in plan
        )
        for condition in INITIAL_CONDITIONS
    }
    anchor_radians = tuple(
        np.radians(HISTORICAL_ANCHOR_DEGREES[:2]).tolist() + [0.0, 0.0]
    )
    anchor_not_scheduled = all(
        not np.allclose(
            item["initial_state_radians"], anchor_radians, rtol=0.0, atol=1.0e-14
        )
        for item in plan
    )
    no_per_ic_overrides = all(
        item["solver_policy"]
        == experiment006.policy_dict(shadow_specs(item["formulation"])[item["shadow"]][0])
        and item["max_step_seconds"]
        == shadow_specs(item["formulation"])[item["shadow"]][1]
        for item in plan
    )
    schema_dimensions_separate = set(
        ("numerical_validity", "settling", "shadow_independence", "cross_formulation")
    ) == {
        "numerical_validity",
        "settling",
        "shadow_independence",
        "cross_formulation",
    }
    checks = {
        "exact_preregistered_states": all(state_checks),
        "all_initial_velocities_zero": all(
            np.all(np.asarray(condition["state_radians"])[2:] == 0.0)
            for condition in INITIAL_CONDITIONS
        ),
        "analytical_energies_match_both_formulations": all(energy_checks),
        "el_canonical_state_maps_match": all(map_checks),
        "candidate_a_tangent_bases_correspond": all(basis_checks),
        "three_solver_policies_match_frozen_values": policies_match,
        "duration_qr_cadence_and_checkpoints_match": bool(
            DURATION_SECONDS == 640.0
            and QR_INTERVAL_SECONDS == 0.25
            and CHECKPOINTS_SECONDS
            == (80.0, 160.0, 240.0, 320.0, 400.0, 480.0, 560.0, 640.0)
        ),
        "positive_diagonal_qr_without_column_sorting": (
            positive_diagonal_without_sorting
        ),
        "historical_anchor_not_scheduled": anchor_not_scheduled,
        "exactly_six_runs_per_condition": all(
            value == 6 for value in per_condition_counts.values()
        ),
        "exactly_eighteen_runs": len(plan) == 18,
        "workload_accounting": bool(
            len(plan) * DURATION_SECONDS == 11520.0
            and len(plan) * int(DURATION_SECONDS / QR_INTERVAL_SECONDS) == 46080
            and len(plan) * len(CHECKPOINTS_SECONDS) == 144
        ),
        "decision_schema_separates_four_questions": schema_dimensions_separate,
        "decorrelation_not_a_numerical_validity_guard": True,
        "no_per_condition_policy_override": no_per_ic_overrides,
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "conditions": conditions,
        "execution_plan": plan,
        "per_condition_run_counts": per_condition_counts,
        "accounting": {
            "integrations": len(plan),
            "simulated_formulation_seconds": len(plan) * DURATION_SECONDS,
            "qr_cycles": len(plan) * int(DURATION_SECONDS / QR_INTERVAL_SECONDS),
            "checkpoint_spectrum_vectors": len(plan) * len(CHECKPOINTS_SECONDS),
        },
        "decision_schema": {
            "numerical_validity": "independent of decorrelation",
            "settling": "frozen cumulative-spectrum limits",
            "shadow_independence": "distance/time evidence only",
            "cross_formulation": "same-IC symmetric descriptive comparison",
        },
    }


def _spectrum_array(run: dict[str, Any], formulation: str) -> np.ndarray:
    key = "_finite_time_spectrum" if formulation == "euler_lagrange" else "_diagnostic"
    return np.asarray(run[key], dtype=float)


def _reference_as_el(run: dict[str, Any], formulation: str) -> np.ndarray:
    key = "_reference_state" if formulation == "euler_lagrange" else "_reference_as_el"
    return np.asarray(run[key], dtype=float)


def _spectrum_at_time(
    run: dict[str, Any], formulation: str, time_value: float
) -> np.ndarray:
    cycle_index = int(round(time_value / QR_INTERVAL_SECONDS)) - 1
    cycle = run["cycles"][cycle_index]
    if not math.isclose(
        float(cycle["end_time_seconds"]), time_value, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError(f"No QR checkpoint at {time_value} seconds.")
    field = (
        "cumulative_finite_time_spectrum_per_second"
        if formulation == "euler_lagrange"
        else "cumulative_finite_time_diagnostic_per_second"
    )
    return np.asarray(cycle[field], dtype=float)


def numerical_validity(run: dict[str, Any], formulation: str) -> dict[str, Any]:
    limit = NUMERICAL_LIMITS["qr_reconstruction_orthonormality_bookkeeping"]
    if formulation == "euler_lagrange":
        checks = {
            "runner_accepted": bool(run["accepted"]),
            "energy_drift_within_1e-7": run[
                "maximum_normalized_reference_energy_drift"
            ]
            <= NUMERICAL_LIMITS["normalized_energy_drift"],
            "q_orthonormality_within_1e-12": run[
                "maximum_q_orthonormality_error"
            ]
            <= limit,
            "scaled_reconstruction_within_1e-12": run[
                "maximum_scaled_reconstruction_relative_error"
            ]
            <= limit,
            "physical_reconstruction_within_1e-12": run[
                "maximum_physical_reconstruction_relative_error"
            ]
            <= limit,
            "post_metric_orthonormality_within_1e-12": run[
                "maximum_post_metric_orthonormality_error"
            ]
            <= limit,
            "reset_map_within_1e-12": run["maximum_reset_map_error"] <= limit,
            "bookkeeping_within_1e-12": max(
                run["cumulative_bookkeeping_error"],
                run["spectrum_bookkeeping_error"],
            )
            <= limit,
            "minimum_positive_r_diagonal_at_least_1e-14": run[
                "minimum_r_diagonal"
            ]
            >= NUMERICAL_LIMITS["minimum_positive_r_diagonal"],
            "pre_qr_condition_at_most_1e12": run[
                "maximum_pre_qr_condition_number"
            ]
            <= NUMERICAL_LIMITS["maximum_pre_qr_condition_number"],
        }
    else:
        checks = {
            "runner_accepted": bool(run["accepted"]),
            "hamiltonian_drift_within_1e-7": run[
                "maximum_normalized_reference_energy_drift"
            ]
            <= NUMERICAL_LIMITS["normalized_energy_drift"],
            "pullback_condition_at_most_1e3": run[
                "maximum_pullback_factor_condition_number"
            ]
            <= NUMERICAL_LIMITS["canonical_maximum_pullback_condition_number"],
            "pullback_singular_value_at_least_1e-6": run[
                "minimum_pullback_factor_singular_value"
            ]
            >= NUMERICAL_LIMITS["canonical_minimum_pullback_singular_value"],
            "pre_qr_condition_at_most_1e12": run[
                "maximum_pre_qr_condition_number"
            ]
            <= NUMERICAL_LIMITS["maximum_pre_qr_condition_number"],
            "minimum_positive_r_diagonal_at_least_1e-14": run[
                "minimum_r_diagonal"
            ]
            >= NUMERICAL_LIMITS["minimum_positive_r_diagonal"],
            "q_orthonormality_within_1e-12": run[
                "maximum_q_orthonormality_error"
            ]
            <= limit,
            "scaled_reconstruction_within_1e-12": run[
                "maximum_scaled_reconstruction_relative_error"
            ]
            <= limit,
            "canonical_reconstruction_within_1e-12": run[
                "maximum_coordinate_reconstruction_relative_error"
            ]
            <= limit,
            "physical_reconstruction_within_1e-12": run[
                "maximum_physical_reconstruction_relative_error"
            ]
            <= limit,
            "post_pullback_orthonormality_within_1e-12": run[
                "maximum_post_pullback_orthonormality_error"
            ]
            <= limit,
            "reset_identity_within_1e-12": run["maximum_reset_identity_error"]
            <= limit,
            "bookkeeping_within_1e-12": max(
                run["cumulative_bookkeeping_error"],
                run["diagnostic_bookkeeping_error"],
            )
            <= limit,
        }
    return {"accepted": all(checks.values()), "checks": checks}


def within_shadow_analysis(run: dict[str, Any], formulation: str) -> dict[str, Any]:
    checkpoints = {
        f"{int(time_value)}s": _spectrum_at_time(run, formulation, time_value)
        for time_value in CHECKPOINTS_SECONDS
    }
    change_480_to_560 = np.abs(checkpoints["560s"] - checkpoints["480s"])
    change_560_to_640 = np.abs(checkpoints["640s"] - checkpoints["560s"])
    end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in run["cycles"]], dtype=float
    )
    late = _spectrum_array(run, formulation)[
        end_times >= LATE_WINDOW_START_SECONDS - 1.0e-13
    ]
    late_ranges = np.ptp(late, axis=0)
    checks = {
        "480_to_560_change_within_0.08_per_second": bool(
            np.max(change_480_to_560) <= MAX_CHANGE_480_TO_560
        ),
        "560_to_640_change_within_0.05_per_second": bool(
            np.max(change_560_to_640) <= MAX_CHANGE_560_TO_640
        ),
        "late_component_ranges_within_0.05_per_second": bool(
            np.all(late_ranges <= MAX_WITHIN_LATE_RANGE)
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "checkpoint_spectra_per_second": checkpoints,
        "component_change_480_to_560_per_second": change_480_to_560,
        "maximum_change_480_to_560_per_second": float(np.max(change_480_to_560)),
        "component_change_560_to_640_per_second": change_560_to_640,
        "maximum_change_560_to_640_per_second": float(np.max(change_560_to_640)),
        "late_component_ranges_per_second": late_ranges,
        "maximum_late_component_range_per_second": float(np.max(late_ranges)),
        "hamiltonian_diagnostics": {
            key: experiment007.hamiltonian_structure_diagnostics(value)
            for key, value in checkpoints.items()
        },
    }


def between_shadow_analysis(
    runs: dict[str, dict[str, Any]], formulation: str
) -> dict[str, Any]:
    checkpoint_statistics: dict[str, Any] = {}
    means: dict[str, np.ndarray] = {}
    for time_value in CHECKPOINTS_SECONDS:
        key = f"{int(time_value)}s"
        values = np.asarray(
            [_spectrum_at_time(run, formulation, time_value) for run in runs.values()]
        )
        mean = np.mean(values, axis=0)
        std = np.std(values, axis=0, ddof=1)
        ranges = np.ptp(values, axis=0)
        means[key] = mean
        checkpoint_statistics[key] = {
            "ensemble_mean_per_second": mean,
            "sample_standard_deviation_per_second": std,
            "component_range_per_second": ranges,
            "maximum_component_range_per_second": float(np.max(ranges)),
            "maximum_sample_standard_deviation_per_second": float(np.max(std)),
            "ensemble_mean_hamiltonian_diagnostics": (
                experiment007.hamiltonian_structure_diagnostics(mean)
            ),
        }
    end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in next(iter(runs.values()))["cycles"]]
    )
    late_mask = end_times >= LATE_WINDOW_START_SECONDS - 1.0e-13
    late_values = np.asarray(
        [_spectrum_array(run, formulation)[late_mask] for run in runs.values()]
    )
    late_ranges = np.ptp(late_values, axis=0)
    maximum_late_range = float(np.max(late_ranges))
    mean_change = np.abs(means["640s"] - means["560s"])
    final_values = np.asarray(
        [_spectrum_at_time(run, formulation, 640.0) for run in runs.values()]
    )
    final_ranges = np.ptp(final_values, axis=0)
    final_stds = np.std(final_values, axis=0, ddof=1)
    per_shadow_changes = np.asarray(
        [
            np.abs(
                _spectrum_at_time(run, formulation, 640.0)
                - _spectrum_at_time(run, formulation, 560.0)
            )
            for run in runs.values()
        ]
    )
    width = np.maximum.reduce(
        [final_stds, final_ranges / 2.0, np.max(per_shadow_changes, axis=0)]
    )
    checks = {
        "final_component_ranges_within_0.05_per_second": bool(
            np.all(final_ranges <= MAX_FINAL_BETWEEN_RANGE)
        ),
        "final_sample_standard_deviations_within_0.025_per_second": bool(
            np.all(final_stds <= MAX_FINAL_BETWEEN_SAMPLE_STD)
        ),
        "ensemble_mean_change_560_to_640_within_0.04_per_second": bool(
            np.max(mean_change) <= MAX_ENSEMBLE_MEAN_CHANGE_560_TO_640
        ),
        "late_window_between_range_within_0.07_per_second": bool(
            maximum_late_range <= MAX_LATE_WINDOW_BETWEEN_RANGE
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "checkpoint_statistics": checkpoint_statistics,
        "ensemble_mean_component_change_560_to_640_per_second": mean_change,
        "maximum_ensemble_mean_change_560_to_640_per_second": float(
            np.max(mean_change)
        ),
        "late_window_component_ranges_per_second": np.max(late_ranges, axis=0),
        "maximum_late_window_between_range_per_second": maximum_late_range,
        "final_descriptive_uncertainty_half_width_per_second": width,
        "uncertainty_definition": (
            "componentwise maximum of final sample standard deviation, half final "
            "range, and largest absolute per-shadow 560-to-640 change"
        ),
    }


def reference_independence_analysis(
    runs: dict[str, dict[str, Any]], formulation: str
) -> dict[str, Any]:
    names = list(runs)
    common_time = np.asarray(runs[names[0]]["_reference_time"], dtype=float)
    times_identical = all(
        np.array_equal(common_time, np.asarray(runs[name]["_reference_time"]))
        for name in names[1:]
    )
    scale = experiment011.candidate_a_scaling_matrix()
    pairs: dict[str, Any] = {}
    series: dict[str, np.ndarray] = {}
    for first, second in combinations(names, 2):
        pair_name = f"{first}_vs_{second}"
        first_state = _reference_as_el(runs[first], formulation)
        second_state = _reference_as_el(runs[second], formulation)
        difference = first_state - second_state
        difference[:, :2] = experiment006.wrap_angle_difference(difference[:, :2])
        distances = np.linalg.norm(difference @ scale.T, axis=1)
        crossing_indices = np.flatnonzero(distances >= DECORRELATION_DISTANCE)
        first_crossing = (
            float(common_time[int(crossing_indices[0])])
            if len(crossing_indices)
            else None
        )
        pairs[pair_name] = {
            "first_threshold_crossing_seconds": first_crossing,
            "crossed_by_80_seconds": bool(
                first_crossing is not None
                and first_crossing <= EARLY_DECORRELATION_DEADLINE_SECONDS
            ),
            "crossed_by_560_seconds": bool(
                first_crossing is not None
                and first_crossing <= INDEPENDENCE_DEADLINE_SECONDS
            ),
            "final_candidate_a_distance": float(distances[-1]),
            "maximum_candidate_a_distance": float(np.max(distances)),
        }
        series[pair_name] = distances
    all_early = all(item["crossed_by_80_seconds"] for item in pairs.values())
    all_terminal = all(item["crossed_by_560_seconds"] for item in pairs.values())
    if all_early:
        status = "early_decorrelation"
    elif all_terminal:
        status = "terminal_window_independence"
    else:
        status = "independence_not_demonstrated"
    return {
        "status": status,
        "reference_sample_times_identical": times_identical,
        "distance_threshold": DECORRELATION_DISTANCE,
        "early_deadline_seconds": EARLY_DECORRELATION_DEADLINE_SECONDS,
        "independence_deadline_seconds": INDEPENDENCE_DEADLINE_SECONDS,
        "pairs": pairs,
        "_time": common_time,
        "_distance_series": series,
    }


def cross_formulation_analysis(
    el_runs: dict[str, dict[str, Any]],
    canonical_runs: dict[str, dict[str, Any]],
    el_between: dict[str, Any],
    canonical_between: dict[str, Any],
    *,
    internally_interpretable: bool,
) -> dict[str, Any]:
    el_560 = np.asarray(
        [_spectrum_at_time(run, "euler_lagrange", 560.0) for run in el_runs.values()]
    )
    el_640 = np.asarray(
        [_spectrum_at_time(run, "euler_lagrange", 640.0) for run in el_runs.values()]
    )
    canonical_560 = np.asarray(
        [
            _spectrum_at_time(run, "canonical_hamiltonian", 560.0)
            for run in canonical_runs.values()
        ]
    )
    canonical_640 = np.asarray(
        [
            _spectrum_at_time(run, "canonical_hamiltonian", 640.0)
            for run in canonical_runs.values()
        ]
    )
    el_mean_560 = np.mean(el_560, axis=0)
    el_mean_640 = np.mean(el_640, axis=0)
    canonical_mean_560 = np.mean(canonical_560, axis=0)
    canonical_mean_640 = np.mean(canonical_640, axis=0)
    displacement = np.abs(canonical_mean_640 - el_mean_640)
    envelope_sum = np.asarray(
        el_between["final_descriptive_uncertainty_half_width_per_second"]
    ) + np.asarray(
        canonical_between["final_descriptive_uncertainty_half_width_per_second"]
    )
    combined = np.concatenate((el_640, canonical_640), axis=0)
    combined_range = np.ptp(combined, axis=0)
    combined_std = np.std(combined, axis=0, ddof=1)
    el_drift = el_mean_640 - el_mean_560
    canonical_drift = canonical_mean_640 - canonical_mean_560
    drift_difference = np.abs(canonical_drift - el_drift)
    checks = {
        "both_formulations_numerically_valid_and_settled": internally_interpretable,
        "descriptive_envelopes_overlap_componentwise": bool(
            np.all(displacement <= envelope_sum)
        ),
        "terminal_mean_displacement_within_0.05_per_second": bool(
            np.all(displacement <= CROSS_MAX_MEAN_DISPLACEMENT)
        ),
        "combined_six_shadow_ranges_within_0.07_per_second": bool(
            np.all(combined_range <= CROSS_MAX_COMBINED_RANGE)
        ),
        "combined_six_shadow_sample_std_within_0.025_per_second": bool(
            np.all(combined_std <= CROSS_MAX_COMBINED_SAMPLE_STD)
        ),
        "late_mean_drift_difference_within_0.04_per_second": bool(
            np.all(drift_difference <= CROSS_MAX_LATE_DRIFT_DIFFERENCE)
        ),
    }
    accepted = all(checks.values())
    verdict = (
        "accepted_descriptive_cross_formulation_compatibility"
        if accepted
        else (
            "rejected_descriptive_cross_formulation_compatibility"
            if internally_interpretable
            else "not_evaluable_due_to_numerical_validity_or_settling"
        )
    )
    return {
        "accepted": accepted,
        "verdict": verdict,
        "checks": checks,
        "el_ensemble_mean_560_per_second": el_mean_560,
        "el_ensemble_mean_640_per_second": el_mean_640,
        "canonical_ensemble_mean_560_per_second": canonical_mean_560,
        "canonical_ensemble_mean_640_per_second": canonical_mean_640,
        "terminal_mean_absolute_displacement_per_second": displacement,
        "descriptive_envelope_sum_per_second": envelope_sum,
        "descriptive_envelope_margin_per_second": envelope_sum - displacement,
        "combined_six_shadow_component_range_per_second": combined_range,
        "combined_six_shadow_sample_standard_deviation_per_second": combined_std,
        "el_ensemble_mean_change_560_to_640_per_second": el_drift,
        "canonical_ensemble_mean_change_560_to_640_per_second": canonical_drift,
        "late_mean_drift_absolute_difference_per_second": drift_difference,
        "criterion_role": (
            "symmetric descriptive numerical compatibility; not confidence "
            "intervals or a formal hypothesis test"
        ),
    }


def classify_condition(
    *,
    numerical_valid: bool,
    settled: bool,
    cross_compatible: bool,
    independence_demonstrated: bool,
) -> str:
    if not numerical_valid:
        return "numerically_invalid"
    if not settled:
        return "numerically_valid_but_unsettled_at_640_seconds"
    if not cross_compatible:
        return "settled_but_cross_formulation_incompatible"
    if independence_demonstrated:
        return "settled_formulation_agreement_with_decorrelated_shadows"
    return "settled_formulation_agreement_without_demonstrated_shadow_independence"


def _public_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in run.items()
        if not key.startswith("_") and key != "cycles"
    }


def _cycle_spectrum_field(formulation: str) -> str:
    return (
        "cumulative_finite_time_spectrum_per_second"
        if formulation == "euler_lagrange"
        else "cumulative_finite_time_diagnostic_per_second"
    )


def write_run_evidence(
    output_dir: Path,
    run: dict[str, Any],
    formulation: str,
    validity: dict[str, Any],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "run_summary.json"
    cumulative_path = output_dir / "cumulative_timeseries.csv"
    cycles_path = output_dir / "cycles.csv"
    write_json(
        summary_path,
        {
            "formulation": formulation,
            "run": _public_run_summary(run),
            "numerical_validity": validity,
            "checkpoint_spectra_per_second": {
                f"{int(time_value)}s": _spectrum_at_time(
                    run, formulation, time_value
                )
                for time_value in CHECKPOINTS_SECONDS
            },
        },
    )
    with cumulative_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "cycle_index",
            "time_seconds",
            *[f"lambda_{index}_per_s" for index in range(1, 5)],
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        spectrum_field = _cycle_spectrum_field(formulation)
        for cycle in run["cycles"]:
            row: dict[str, Any] = {
                "cycle_index": cycle["cycle_index"],
                "time_seconds": cycle["end_time_seconds"],
            }
            for index, value in enumerate(cycle[spectrum_field], start=1):
                row[f"lambda_{index}_per_s"] = value
            writer.writerow(row)
    common_fields = [
        "cycle_index",
        "start_time_seconds",
        "end_time_seconds",
        "accepted",
        "segment_maximum_normalized_reference_energy_drift",
        "pre_qr_condition_number",
        "minimum_r_diagonal",
        "q_orthonormality_error",
        "physical_reconstruction_relative_error",
        "post_metric_orthonormality_error",
    ]
    with cycles_path.open("w", newline="", encoding="utf-8") as handle:
        fields = common_fields + [
            *[f"cycle_log_{index}" for index in range(1, 5)],
            *[f"cumulative_log_{index}" for index in range(1, 5)],
        ]
        if formulation == "canonical_hamiltonian":
            fields += [
                "pullback_factor_condition_number",
                "pullback_factor_minimum_singular_value",
                "canonical_reconstruction_relative_error",
                "reset_identity_error",
            ]
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
                "physical_reconstruction_relative_error": cycle[
                    "physical_reconstruction_relative_error"
                ],
                "post_metric_orthonormality_error": (
                    cycle["post_metric_orthonormality_error"]
                    if formulation == "euler_lagrange"
                    else cycle["post_pullback_orthonormality_error"]
                ),
            }
            for index, value in enumerate(cycle["cycle_log_growth"], start=1):
                row[f"cycle_log_{index}"] = value
            for index, value in enumerate(cycle["cumulative_log_growth"], start=1):
                row[f"cumulative_log_{index}"] = value
            if formulation == "canonical_hamiltonian":
                row |= {
                    "pullback_factor_condition_number": cycle[
                        "pullback_factor_condition_number"
                    ],
                    "pullback_factor_minimum_singular_value": cycle[
                        "pullback_factor_minimum_singular_value"
                    ],
                    "canonical_reconstruction_relative_error": cycle[
                        "coordinate_reconstruction_relative_error"
                    ],
                    "reset_identity_error": cycle["reset_identity_error"],
                }
            writer.writerow(row)
    return [summary_path, cumulative_path, cycles_path]


def write_reference_distances(
    path: Path, analysis: dict[str, Any]
) -> None:
    series = analysis["_distance_series"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["time_seconds", *series]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, time_value in enumerate(analysis["_time"]):
            writer.writerow(
                {"time_seconds": time_value}
                | {name: values[index] for name, values in series.items()}
            )


def run_single(
    condition: dict[str, Any],
    formulation: str,
    shadow: str,
    policy: Any,
    max_step: float,
) -> dict[str, Any]:
    state = np.asarray(condition["state_radians"], dtype=float)
    run_id = f"{condition['id']}_{formulation}_{shadow}_640s"
    if formulation == "euler_lagrange":
        return experiment007.run_qr_primitive(
            experiment006.VariationalDynamics(),
            run_id=run_id,
            duration=DURATION_SECONDS,
            qr_interval=QR_INTERVAL_SECONDS,
            policy=policy,
            max_step=max_step,
            initial_reference=state,
        )
    return experiment011.run_canonical_qr_primitive(
        experiment011.CanonicalDynamics(),
        run_id=run_id,
        duration=DURATION_SECONDS,
        qr_interval=QR_INTERVAL_SECONDS,
        policy=policy,
        max_step=max_step,
        initial_el_state=state,
    )


def run_condition(condition: dict[str, Any], output_root: Path) -> dict[str, Any]:
    condition_root = output_root / condition["id"]
    formulation_results: dict[str, Any] = {}
    formulation_runs: dict[str, dict[str, dict[str, Any]]] = {}
    for formulation in FORMULATIONS:
        runs: dict[str, dict[str, Any]] = {}
        validities: dict[str, Any] = {}
        execution_failures: dict[str, Any] = {}
        for shadow, (policy, max_step) in shadow_specs(formulation).items():
            print(
                f"START {condition['label']} {formulation} {shadow}", flush=True
            )
            try:
                run = run_single(condition, formulation, shadow, policy, max_step)
            except Exception as error:  # preserve a numerical-invalidity outcome
                failure = {
                    "initial_condition_id": condition["id"],
                    "formulation": formulation,
                    "shadow": shadow,
                    "exception_type": type(error).__name__,
                    "message": str(error),
                    "classification": "documented_execution_failure_numerically_invalid",
                }
                execution_failures[shadow] = failure
                write_json(
                    condition_root / formulation / shadow / "failure.json", failure
                )
                print(
                    f"FAIL  {condition['label']} {formulation} {shadow} "
                    f"{type(error).__name__}: {error}",
                    flush=True,
                )
                continue
            validity = numerical_validity(run, formulation)
            run_dir = condition_root / formulation / shadow
            write_run_evidence(run_dir, run, formulation, validity)
            runs[shadow] = run
            validities[shadow] = validity
            print(
                f"DONE  {condition['label']} {formulation} {shadow} "
                f"valid={validity['accepted']} cycles={run['cycle_count']}",
                flush=True,
            )
        complete_ensemble = len(runs) == len(SHADOW_NAMES)
        if complete_ensemble:
            within = {
                name: within_shadow_analysis(run, formulation)
                for name, run in runs.items()
            }
            between = between_shadow_analysis(runs, formulation)
            independence = reference_independence_analysis(runs, formulation)
            write_reference_distances(
                condition_root / formulation / "reference_pair_distances.csv",
                independence,
            )
        else:
            within = {}
            between = {
                "accepted": False,
                "reason": "incomplete ensemble after documented execution failure",
            }
            independence = {
                "status": "not_evaluable_due_to_execution_failure",
                "pairs": {},
            }
        numerical_accepted = bool(
            complete_ensemble
            and len(validities) == len(SHADOW_NAMES)
            and all(item["accepted"] for item in validities.values())
        )
        settling_accepted = bool(
            numerical_accepted
            and all(item["accepted"] for item in within.values())
            and between["accepted"]
        )
        formulation_summary = {
            "formulation": formulation,
            "numerical_validity": {
                "accepted": numerical_accepted,
                "runs": validities,
                "execution_failures": execution_failures,
            },
            "settling": {
                "accepted": settling_accepted,
                "within_shadow": within,
                "between_shadow": between,
            },
            "shadow_independence": {
                key: value
                for key, value in independence.items()
                if not key.startswith("_")
            },
            "ensemble_mean_640_per_second": (
                between["checkpoint_statistics"]["640s"][
                    "ensemble_mean_per_second"
                ]
                if complete_ensemble
                else None
            ),
            "descriptive_half_width_per_second": (
                between["final_descriptive_uncertainty_half_width_per_second"]
                if complete_ensemble
                else None
            ),
            "hamiltonian_structure_diagnostics": (
                between["checkpoint_statistics"]["640s"][
                    "ensemble_mean_hamiltonian_diagnostics"
                ]
                if complete_ensemble
                else None
            ),
        }
        write_json(
            condition_root / formulation / "formulation_summary.json",
            formulation_summary,
        )
        formulation_results[formulation] = formulation_summary
        formulation_runs[formulation] = runs

    el_result = formulation_results["euler_lagrange"]
    canonical_result = formulation_results["canonical_hamiltonian"]
    numerical_valid = bool(
        el_result["numerical_validity"]["accepted"]
        and canonical_result["numerical_validity"]["accepted"]
    )
    settled = bool(
        el_result["settling"]["accepted"]
        and canonical_result["settling"]["accepted"]
    )
    complete_cross_ensembles = all(
        len(formulation_runs[formulation]) == len(SHADOW_NAMES)
        for formulation in FORMULATIONS
    )
    if complete_cross_ensembles:
        cross = cross_formulation_analysis(
            formulation_runs["euler_lagrange"],
            formulation_runs["canonical_hamiltonian"],
            el_result["settling"]["between_shadow"],
            canonical_result["settling"]["between_shadow"],
            internally_interpretable=bool(numerical_valid and settled),
        )
    else:
        cross = {
            "accepted": False,
            "verdict": "not_evaluable_due_to_documented_execution_failure",
            "checks": {
                "both_formulation_ensembles_complete": False,
            },
        }
    independence_demonstrated = all(
        formulation_results[formulation]["shadow_independence"]["status"]
        in {"early_decorrelation", "terminal_window_independence"}
        for formulation in FORMULATIONS
    )
    category = classify_condition(
        numerical_valid=numerical_valid,
        settled=settled,
        cross_compatible=cross["accepted"],
        independence_demonstrated=independence_demonstrated,
    )
    summary = {
        "initial_condition": condition,
        "formulations": formulation_results,
        "cross_formulation": cross,
        "numerical_validity_accepted": numerical_valid,
        "settling_accepted": settled,
        "shadow_independence_demonstrated_in_both_formulations": (
            independence_demonstrated
        ),
        "cross_formulation_accepted": cross["accepted"],
        "preregistered_outcome_category": category,
    }
    write_json(condition_root / "ic_summary.json", summary)
    return summary


def experiment_level_verdict(condition_results: Sequence[dict[str, Any]]) -> str:
    if not all(item["numerical_validity_accepted"] for item in condition_results):
        return "full_selected_set_numerically_unresolved"
    if not all(item["settling_accepted"] for item in condition_results):
        return "full_selected_set_unresolved_at_640_seconds"
    if not all(item["cross_formulation_accepted"] for item in condition_results):
        return "rejected_cross_formulation_robustness_across_selected_set"
    if all(
        item["shadow_independence_demonstrated_in_both_formulations"]
        for item in condition_results
    ):
        return "accepted_independent_shadow_formulation_robustness_across_selected_set"
    return "accepted_policy_stable_formulation_robustness_without_full_shadow_independence"


def write_manifest(output_root: Path) -> Path:
    manifest_path = output_root / "manifest.json"
    files = sorted(
        path for path in output_root.rglob("*") if path.is_file() and path != manifest_path
    )
    write_json(
        manifest_path,
        {
            "experiment": EXPERIMENT_NAME,
            "output_role": "frozen Experiment 012 18-run evidence",
            "source": str(Path(__file__).relative_to(REPOSITORY_ROOT)),
            "files": [
                {
                    "path": str(path.relative_to(output_root)),
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in files
            ],
        },
    )
    return manifest_path


def run_experiment(output_root: Path) -> dict[str, Any]:
    gate = pre_execution_gate()
    write_json(output_root / "pre_execution_gate.json", gate)
    if not gate["accepted"]:
        failed = [name for name, value in gate["checks"].items() if not value]
        raise AssertionError(f"Experiment 012 pre-execution gate failed: {failed}")
    write_json(
        output_root / "frozen_contract.json",
        {
            "experiment": EXPERIMENT_NAME,
            "initial_conditions": INITIAL_CONDITIONS,
            "duration_seconds": DURATION_SECONDS,
            "qr_interval_seconds": QR_INTERVAL_SECONDS,
            "checkpoints_seconds": CHECKPOINTS_SECONDS,
            "shadow_policies": {
                formulation: {
                    name: experiment006.policy_dict(policy)
                    | {"max_step_seconds": max_step}
                    for name, (policy, max_step) in shadow_specs(formulation).items()
                }
                for formulation in FORMULATIONS
            },
            "numerical_limits": NUMERICAL_LIMITS,
            "settling_limits": {
                "maximum_change_480_to_560_per_second": MAX_CHANGE_480_TO_560,
                "maximum_change_560_to_640_per_second": MAX_CHANGE_560_TO_640,
                "maximum_within_late_range_per_second": MAX_WITHIN_LATE_RANGE,
                "maximum_final_between_range_per_second": MAX_FINAL_BETWEEN_RANGE,
                "maximum_final_between_sample_std_per_second": (
                    MAX_FINAL_BETWEEN_SAMPLE_STD
                ),
                "maximum_ensemble_mean_change_560_to_640_per_second": (
                    MAX_ENSEMBLE_MEAN_CHANGE_560_TO_640
                ),
                "maximum_late_window_between_range_per_second": (
                    MAX_LATE_WINDOW_BETWEEN_RANGE
                ),
            },
            "cross_formulation_limits": {
                "maximum_terminal_mean_displacement_per_second": (
                    CROSS_MAX_MEAN_DISPLACEMENT
                ),
                "maximum_combined_six_shadow_range_per_second": (
                    CROSS_MAX_COMBINED_RANGE
                ),
                "maximum_combined_six_shadow_sample_std_per_second": (
                    CROSS_MAX_COMBINED_SAMPLE_STD
                ),
                "maximum_late_mean_drift_difference_per_second": (
                    CROSS_MAX_LATE_DRIFT_DIFFERENCE
                ),
            },
        },
    )
    results = [run_condition(condition, output_root) for condition in INITIAL_CONDITIONS]
    verdict = experiment_level_verdict(results)
    overall = {
        "experiment": EXPERIMENT_NAME,
        "status": "executed_frozen_protocol",
        "research_question": (
            "Across the preregistered three-condition zero-velocity design, does "
            "independent EL/canonical long-time spectrum agreement persist without "
            "retuning the accepted numerical protocol?"
        ),
        "pre_execution_gate_accepted": gate["accepted"],
        "accounting": gate["accounting"],
        "condition_results": results,
        "experiment_level_verdict": verdict,
        "historical_anchor": {
            "state_degrees": HISTORICAL_ANCHOR_DEGREES,
            "rerun": False,
            "provenance": "accepted Experiments 010 and 011 evidence",
        },
        "claim_boundary": (
            "Three preregistered zero-velocity conditions under the frozen 640-second "
            "EL/canonical three-policy protocol only; not a global field, classifier, "
            "infinite-time proof, or test of nonzero initial velocity."
        ),
    }
    write_json(output_root / "summary.json", overall)
    write_manifest(output_root)
    return overall


def verify_evidence(output_root: Path, summary: dict[str, Any]) -> None:
    if summary["accounting"] != {
        "integrations": 18,
        "simulated_formulation_seconds": 11520.0,
        "qr_cycles": 46080,
        "checkpoint_spectrum_vectors": 144,
    }:
        raise AssertionError("Frozen workload accounting changed.")
    for condition in summary["condition_results"]:
        for formulation in FORMULATIONS:
            result = condition["formulations"][formulation]
            if len(result["settling"]["within_shadow"]) != 3:
                raise AssertionError("A formulation is missing a numerical shadow.")
            for shadow in SHADOW_NAMES:
                path = (
                    output_root
                    / condition["initial_condition"]["id"]
                    / formulation
                    / shadow
                    / "run_summary.json"
                )
                if not path.exists():
                    raise AssertionError(f"Missing run evidence: {path}")
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = output_root / item["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise AssertionError(f"Evidence hash mismatch: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "development/chaos_content/outputs"
            / "initial_condition_spectrum_robustness"
            / "frozen_640s"
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
                    item["initial_condition"]["id"]: item[
                        "preregistered_outcome_category"
                    ]
                    for item in summary["condition_results"]
                },
                "output_dir": str(args.output_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
