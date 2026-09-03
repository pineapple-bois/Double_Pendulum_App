"""Test long-time cumulative QR compatibility across numerical reference shadows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
from itertools import combinations
from pathlib import Path
from typing import Any

RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_007_ROOT = EXPERIMENT_ROOT.parent / "007_full_matrix_qr_tangent_dynamics"
for import_root in (REPOSITORY_ROOT, EXPERIMENT_007_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import numpy as np

import full_matrix_qr_tangent_dynamics as experiment007


experiment006 = experiment007.experiment006
EXPERIMENT_NAME = "independent_shadow_spectrum_compatibility"
DURATION_SECONDS = 320.0
CHECKPOINTS_SECONDS = (80.0, 160.0, 240.0, 320.0)
LATE_WINDOW_START_SECONDS = 240.0
DECORRELATION_DISTANCE = 1.0
DECORRELATION_DEADLINE_SECONDS = 80.0

MAX_CHANGE_160_TO_240 = 0.08
MAX_CHANGE_240_TO_320 = 0.05
MAX_WITHIN_LATE_RANGE = 0.05
MAX_FINAL_BETWEEN_RANGE = 0.05
MAX_FINAL_BETWEEN_SAMPLE_STD = 0.025
MAX_ENSEMBLE_MEAN_CHANGE_240_TO_320 = 0.04
MAX_LATE_WINDOW_BETWEEN_RANGE = 0.07
CLEAR_INCOMPATIBILITY_LIMIT = 0.10


def shadow_specs() -> dict[str, tuple[Any, float]]:
    return {
        "baseline": (
            experiment007.SOLVER_POLICY,
            experiment007.MAX_STEP_SECONDS,
        ),
        "strict": (
            experiment007.STRICTER_POLICY,
            experiment007.MAX_STEP_SECONDS,
        ),
        "half_step": (
            experiment007.SOLVER_POLICY,
            experiment007.HALF_MAX_STEP_SECONDS,
        ),
    }


def public_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in run.items()
        if not key.startswith("_") and key != "cycles"
    }


def scaled_reference_distance(
    first_state: np.ndarray, second_state: np.ndarray
) -> np.ndarray:
    difference = experiment006.wrapped_el_difference(first_state, second_state)
    scaled = np.asarray(difference, dtype=float) @ experiment007.scaling_matrix().T
    if scaled.ndim == 1:
        return np.asarray(float(np.linalg.norm(scaled)))
    return np.linalg.norm(scaled, axis=1)


def reference_decorrelation_analysis(
    runs: dict[str, dict[str, Any]],
    *,
    threshold: float = DECORRELATION_DISTANCE,
    deadline: float = DECORRELATION_DEADLINE_SECONDS,
) -> dict[str, Any]:
    names = list(runs)
    common_time = np.asarray(runs[names[0]]["_reference_time"], dtype=float)
    times_aligned = all(
        np.array_equal(common_time, np.asarray(runs[name]["_reference_time"]))
        for name in names[1:]
    )
    pairs: dict[str, Any] = {}
    distance_series: dict[str, np.ndarray] = {}
    for first_name, second_name in combinations(names, 2):
        pair_name = f"{first_name}_vs_{second_name}"
        distances = scaled_reference_distance(
            runs[first_name]["_reference_state"],
            runs[second_name]["_reference_state"],
        )
        distance_series[pair_name] = distances
        crossing_indices = np.flatnonzero(distances >= threshold)
        first_crossing = (
            float(common_time[int(crossing_indices[0])])
            if len(crossing_indices)
            else None
        )
        post_deadline = distances[common_time >= deadline - 1.0e-13]
        pairs[pair_name] = {
            "first_threshold_crossing_seconds": first_crossing,
            "crossed_by_deadline": bool(
                first_crossing is not None and first_crossing <= deadline
            ),
            "final_candidate_a_distance": float(distances[-1]),
            "median_candidate_a_distance_after_deadline": float(
                np.median(post_deadline)
            ),
            "maximum_candidate_a_distance": float(np.max(distances)),
        }
    checks = {
        "reference_sample_times_identical": times_aligned,
        "all_pairs_decorrelated_by_80_seconds": all(
            pair["crossed_by_deadline"] for pair in pairs.values()
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "distance_threshold": threshold,
        "deadline_seconds": deadline,
        "pairs": pairs,
        "_time": common_time,
        "_distance_series": distance_series,
    }


def checkpoint_spectra(run: dict[str, Any]) -> dict[str, np.ndarray]:
    return {
        f"{int(time_value)}s": experiment007.spectrum_at_time(run, time_value)
        for time_value in CHECKPOINTS_SECONDS
    }


def within_shadow_analysis(run: dict[str, Any]) -> dict[str, Any]:
    checkpoints = checkpoint_spectra(run)
    change_160_to_240 = np.abs(checkpoints["240s"] - checkpoints["160s"])
    change_240_to_320 = np.abs(checkpoints["320s"] - checkpoints["240s"])
    late_spectra = np.asarray(
        [
            cycle["cumulative_finite_time_spectrum_per_second"]
            for cycle in run["cycles"]
            if cycle["end_time_seconds"] >= LATE_WINDOW_START_SECONDS - 1.0e-13
        ],
        dtype=float,
    )
    late_ranges = np.ptp(late_spectra, axis=0)
    checks = {
        "160_to_240_change_within_0.08_per_second": bool(
            np.max(change_160_to_240) <= MAX_CHANGE_160_TO_240
        ),
        "240_to_320_change_within_0.05_per_second": bool(
            np.max(change_240_to_320) <= MAX_CHANGE_240_TO_320
        ),
        "late_component_ranges_within_0.05_per_second": bool(
            np.all(late_ranges <= MAX_WITHIN_LATE_RANGE)
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "checkpoint_spectra_per_second": {
            key: value.tolist() for key, value in checkpoints.items()
        },
        "component_change_160_to_240_per_second": change_160_to_240.tolist(),
        "maximum_change_160_to_240_per_second": float(
            np.max(change_160_to_240)
        ),
        "component_change_240_to_320_per_second": change_240_to_320.tolist(),
        "maximum_change_240_to_320_per_second": float(
            np.max(change_240_to_320)
        ),
        "late_component_ranges_per_second": late_ranges.tolist(),
        "maximum_late_component_range_per_second": float(np.max(late_ranges)),
        "hamiltonian_diagnostics": {
            key: experiment007.hamiltonian_structure_diagnostics(value)
            for key, value in checkpoints.items()
        },
    }


def between_shadow_analysis(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    checkpoint_statistics: dict[str, Any] = {}
    ensemble_means: dict[str, np.ndarray] = {}
    for time_value in CHECKPOINTS_SECONDS:
        key = f"{int(time_value)}s"
        values = np.asarray(
            [experiment007.spectrum_at_time(run, time_value) for run in runs.values()]
        )
        mean = np.mean(values, axis=0)
        sample_std = np.std(values, axis=0, ddof=1)
        component_range = np.ptp(values, axis=0)
        ensemble_means[key] = mean
        checkpoint_statistics[key] = {
            "ensemble_mean_per_second": mean.tolist(),
            "sample_standard_deviation_per_second": sample_std.tolist(),
            "component_range_per_second": component_range.tolist(),
            "maximum_component_range_per_second": float(np.max(component_range)),
            "maximum_sample_standard_deviation_per_second": float(
                np.max(sample_std)
            ),
            "ensemble_mean_hamiltonian_diagnostics": (
                experiment007.hamiltonian_structure_diagnostics(mean)
            ),
        }

    common_end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in next(iter(runs.values()))["cycles"]]
    )
    late_mask = common_end_times >= LATE_WINDOW_START_SECONDS - 1.0e-13
    late_values = np.asarray(
        [run["_finite_time_spectrum"][late_mask] for run in runs.values()]
    )
    late_ranges = np.ptp(late_values, axis=0)
    maximum_late_range = float(np.max(late_ranges))
    mean_change = np.abs(ensemble_means["320s"] - ensemble_means["240s"])
    final_ranges = np.asarray(
        checkpoint_statistics["320s"]["component_range_per_second"]
    )
    final_stds = np.asarray(
        checkpoint_statistics["320s"]["sample_standard_deviation_per_second"]
    )
    checks = {
        "final_component_ranges_within_0.05_per_second": bool(
            np.all(final_ranges <= MAX_FINAL_BETWEEN_RANGE)
        ),
        "final_sample_standard_deviations_within_0.025_per_second": bool(
            np.all(final_stds <= MAX_FINAL_BETWEEN_SAMPLE_STD)
        ),
        "ensemble_mean_change_240_to_320_within_0.04_per_second": bool(
            np.max(mean_change) <= MAX_ENSEMBLE_MEAN_CHANGE_240_TO_320
        ),
        "late_window_between_range_within_0.07_per_second": bool(
            maximum_late_range <= MAX_LATE_WINDOW_BETWEEN_RANGE
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "checkpoint_statistics": checkpoint_statistics,
        "ensemble_mean_component_change_240_to_320_per_second": mean_change.tolist(),
        "maximum_ensemble_mean_change_240_to_320_per_second": float(
            np.max(mean_change)
        ),
        "late_window_component_ranges_per_second": np.max(
            late_ranges, axis=0
        ).tolist(),
        "maximum_late_window_between_range_per_second": maximum_late_range,
        "_late_times": common_end_times[late_mask],
        "_late_ranges": late_ranges,
    }


def classify_compatibility(
    *,
    validity_accepted: bool,
    decorrelation_accepted: bool,
    within: dict[str, dict[str, Any]],
    between: dict[str, Any],
) -> str:
    if not validity_accepted or not decorrelation_accepted:
        return "unresolved_at_320_seconds"
    if all(item["accepted"] for item in within.values()) and between["accepted"]:
        return "accepted_statistical_compatibility"
    clear_incompatibility = (
        any(
            item["maximum_change_240_to_320_per_second"]
            > CLEAR_INCOMPATIBILITY_LIMIT
            for item in within.values()
        )
        or between["checkpoint_statistics"]["320s"][
            "maximum_component_range_per_second"
        ]
        > CLEAR_INCOMPATIBILITY_LIMIT
        or between["maximum_late_window_between_range_per_second"]
        > CLEAR_INCOMPATIBILITY_LIMIT
    )
    if clear_incompatibility:
        return "clearly_incompatible_at_320_seconds"
    return "unresolved_at_320_seconds"


def _public_between(between: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in between.items() if not key.startswith("_")}


def _public_decorrelation(decorrelation: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in decorrelation.items()
        if not key.startswith("_")
    }


def run_investigation() -> dict[str, Any]:
    dynamics = experiment006.VariationalDynamics()
    runs = {
        name: experiment007.run_qr_primitive(
            dynamics,
            run_id=f"{name}_320s",
            duration=DURATION_SECONDS,
            qr_interval=experiment007.QR_INTERVAL_SECONDS,
            policy=policy,
            max_step=max_step,
        )
        for name, (policy, max_step) in shadow_specs().items()
    }
    decorrelation = reference_decorrelation_analysis(runs)
    within = {name: within_shadow_analysis(run) for name, run in runs.items()}
    between = between_shadow_analysis(runs)
    validity_checks = {
        f"{name}_numerically_valid": run["accepted"]
        for name, run in runs.items()
    }
    validity_accepted = all(validity_checks.values())
    classification = classify_compatibility(
        validity_accepted=validity_accepted,
        decorrelation_accepted=decorrelation["accepted"],
        within=within,
        between=between,
    )
    if classification == "accepted_statistical_compatibility":
        status = "accepted_statistical_compatibility_at_320_seconds"
        accepted = True
        strongest_claim = (
            "Three independently integrated and decorrelated Euler-Lagrange "
            "numerical shadows produce cumulative four-component QR estimates "
            "that satisfy the predeclared within-shadow settling and between-shadow "
            "compatibility criteria through 320 seconds."
        )
        next_question = (
            "Does an independently formulated Hamiltonian/canonical tangent QR "
            "calculation reproduce the compatible Euler-Lagrange long-time spectrum?"
        )
    elif classification == "clearly_incompatible_at_320_seconds":
        status = "rejected_statistical_compatibility_at_320_seconds"
        accepted = False
        strongest_claim = (
            "The declared decorrelated numerical-shadow ensemble remains clearly "
            "incompatible at 320 seconds despite valid QR integrations."
        )
        next_question = (
            "Does one predeclared longer-duration extension reduce the identified "
            "within-shadow drift or between-shadow spread?"
        )
    else:
        status = "unresolved_statistical_compatibility_at_320_seconds"
        accepted = False
        strongest_claim = (
            "The three-shadow cumulative estimates become substantially more "
            "compatible from 80 to 320 seconds and pass every checkpoint-drift "
            "criterion, but residual late-window fluctuation and between-shadow "
            "spread remain marginally above the predeclared acceptance limits."
        )
        next_question = (
            "Does one predeclared extension of the same three-shadow ensemble to "
            "640 seconds reduce outer-exponent late-window drift and between-shadow "
            "spread below the compatibility limits?"
        )

    numerical_extrema = {
        "maximum_reference_energy_drift": max(
            run["maximum_normalized_reference_energy_drift"] for run in runs.values()
        ),
        "maximum_q_orthonormality_error": max(
            run["maximum_q_orthonormality_error"] for run in runs.values()
        ),
        "maximum_physical_reconstruction_relative_error": max(
            run["maximum_physical_reconstruction_relative_error"]
            for run in runs.values()
        ),
        "minimum_r_diagonal": min(
            run["minimum_r_diagonal"] for run in runs.values()
        ),
        "maximum_pre_qr_condition_number": max(
            run["maximum_pre_qr_condition_number"] for run in runs.values()
        ),
    }
    summary = {
        "experiment": EXPERIMENT_NAME,
        "status": status,
        "classification": classification,
        "accepted": accepted,
        "question": (
            "After independently integrated Euler-Lagrange reference trajectories "
            "decorrelate, do their cumulative QR spectrum estimates approach "
            "statistically compatible long-time values?"
        ),
        "ensemble_design": {
            "shadow_count": len(runs),
            "shadow_names": list(runs),
            "duration_seconds": DURATION_SECONDS,
            "checkpoints_seconds": list(CHECKPOINTS_SECONDS),
            "late_window_seconds": [LATE_WINDOW_START_SECONDS, DURATION_SECONDS],
            "qr_interval_seconds": experiment007.QR_INTERVAL_SECONDS,
            "common_physical_initial_state_degrees": (
                experiment006.BASE_STATE_DEGREES.tolist()
            ),
            "shadow_policies": {
                name: {
                    "solver_policy": experiment006.policy_dict(policy),
                    "max_step_seconds": max_step,
                }
                for name, (policy, max_step) in shadow_specs().items()
            },
            "interpretation": (
                "three deterministic numerical shadows, not random seeds or a "
                "formal invariant-measure sample"
            ),
        },
        "criteria": {
            "decorrelation_distance": DECORRELATION_DISTANCE,
            "decorrelation_deadline_seconds": DECORRELATION_DEADLINE_SECONDS,
            "maximum_change_160_to_240_per_second": MAX_CHANGE_160_TO_240,
            "maximum_change_240_to_320_per_second": MAX_CHANGE_240_TO_320,
            "maximum_within_late_range_per_second": MAX_WITHIN_LATE_RANGE,
            "maximum_final_between_range_per_second": MAX_FINAL_BETWEEN_RANGE,
            "maximum_final_between_sample_std_per_second": (
                MAX_FINAL_BETWEEN_SAMPLE_STD
            ),
            "maximum_ensemble_mean_change_240_to_320_per_second": (
                MAX_ENSEMBLE_MEAN_CHANGE_240_TO_320
            ),
            "maximum_late_window_between_range_per_second": (
                MAX_LATE_WINDOW_BETWEEN_RANGE
            ),
            "clear_incompatibility_limit_per_second": CLEAR_INCOMPATIBILITY_LIMIT,
            "criteria_provenance": "predeclared in README before long-time runs",
        },
        "shadow_runs": {
            name: public_run_summary(run) for name, run in runs.items()
        },
        "reference_decorrelation": _public_decorrelation(decorrelation),
        "within_shadow": within,
        "between_shadow": _public_between(between),
        "numerical_validity_checks": validity_checks,
        "numerical_validity_accepted": validity_accepted,
        "numerical_extrema": numerical_extrema,
        "strongest_claim": strongest_claim,
        "claim_boundary": (
            "The result applies only to three deterministic numerical shadows of "
            "one Euler-Lagrange initial condition under the declared 320-second "
            "Candidate-A QR protocol. It does not establish all-duration, all-shadow, "
            "norm, initial-condition, or canonical-formulation invariance, and it is "
            "not a chaos classification."
        ),
        "next_question": next_question,
    }
    return {
        "summary": summary,
        "runs": runs,
        "decorrelation": decorrelation,
        "within": within,
        "between": between,
    }


def json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_checkpoint_csv(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "shadow",
        "checkpoint_seconds",
        *[f"lambda_{index}_per_s" for index in range(1, 5)],
        "sum_per_s",
        "outer_pair_sum_per_s",
        "inner_pair_sum_per_s",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name, analysis in result["within"].items():
            for checkpoint_key, values in analysis[
                "checkpoint_spectra_per_second"
            ].items():
                checkpoint = float(checkpoint_key.removesuffix("s"))
                diagnostics = analysis["hamiltonian_diagnostics"][checkpoint_key]
                row: dict[str, Any] = {
                    "shadow": name,
                    "checkpoint_seconds": checkpoint,
                    "sum_per_s": diagnostics["sum_per_second"],
                    "outer_pair_sum_per_s": diagnostics[
                        "outer_pair_sum_per_second"
                    ],
                    "inner_pair_sum_per_s": diagnostics[
                        "inner_pair_sum_per_second"
                    ],
                }
                for index, value in enumerate(values, start=1):
                    row[f"lambda_{index}_per_s"] = value
                writer.writerow(row)


def write_cumulative_csv(path: Path, runs: dict[str, dict[str, Any]]) -> None:
    fields = [
        "shadow",
        "time_seconds",
        *[f"lambda_{index}_per_s" for index in range(1, 5)],
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name, run in runs.items():
            for cycle in run["cycles"]:
                row: dict[str, Any] = {
                    "shadow": name,
                    "time_seconds": cycle["end_time_seconds"],
                }
                for index, value in enumerate(
                    cycle["cumulative_finite_time_spectrum_per_second"], start=1
                ):
                    row[f"lambda_{index}_per_s"] = value
                writer.writerow(row)


def write_reference_distance_csv(path: Path, decorrelation: dict[str, Any]) -> None:
    pair_names = list(decorrelation["_distance_series"])
    fields = ["time_seconds", *pair_names]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, time_value in enumerate(decorrelation["_time"]):
            row = {"time_seconds": time_value}
            row.update(
                {
                    name: decorrelation["_distance_series"][name][index]
                    for name in pair_names
                }
            )
            writer.writerow(row)


def write_cycle_json(path: Path, runs: dict[str, dict[str, Any]]) -> None:
    fields = (
        "cycle_index",
        "start_time_seconds",
        "end_time_seconds",
        "accepted",
        "cycle_log_growth",
        "cumulative_log_growth",
        "cumulative_finite_time_spectrum_per_second",
        "q_orthonormality_error",
        "physical_reconstruction_relative_error",
        "post_metric_orthonormality_error",
        "pre_qr_condition_number",
        "segment_maximum_normalized_reference_energy_drift",
        "solver_status",
    )
    json_write(
        path,
        {
            "experiment": EXPERIMENT_NAME,
            "shadows": {
                name: [
                    {field: cycle[field] for field in fields}
                    for cycle in run["cycles"]
                ]
                for name, run in runs.items()
            },
        },
    )


def load_pyplot():
    import matplotlib.pyplot as plt

    return plt


def save_figure(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    load_pyplot().close(fig)


def write_plots(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    plt = load_pyplot()
    paths: list[Path] = []
    run_names = list(result["runs"])
    time_values = np.asarray(
        [cycle["end_time_seconds"] for cycle in result["runs"][run_names[0]]["cycles"]]
    )

    path = output_dir / "01_cumulative_shadow_spectra.png"
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True)
    for component, axis in enumerate(axes.flat):
        for name, run in result["runs"].items():
            axis.plot(
                time_values,
                run["_finite_time_spectrum"][:, component],
                label=name.replace("_", " "),
            )
        axis.axhline(0.0, color="black", linewidth=0.7)
        axis.axvspan(
            LATE_WINDOW_START_SECONDS,
            DURATION_SECONDS,
            color="grey",
            alpha=0.1,
        )
        axis.set_title(f"fixed QR column {component + 1}")
        axis.grid(True, alpha=0.25)
    for axis in axes[-1]:
        axis.set_xlabel("time / s")
    for axis in axes[:, 0]:
        axis.set_ylabel("cumulative value / s$^{-1}$")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Independent numerical-shadow cumulative QR estimates")
    save_figure(fig, path)
    paths.append(path)

    stacked = np.asarray(
        [run["_finite_time_spectrum"] for run in result["runs"].values()]
    )
    component_ranges = np.ptp(stacked, axis=0)
    path = output_dir / "02_between_shadow_spread.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for component in range(4):
        axis.plot(
            time_values,
            component_ranges[:, component],
            label=f"column {component + 1}",
        )
    axis.axhline(MAX_FINAL_BETWEEN_RANGE, color="red", linestyle="--", label="final limit")
    axis.axvspan(
        LATE_WINDOW_START_SECONDS,
        DURATION_SECONDS,
        color="grey",
        alpha=0.1,
    )
    axis.set(
        xlabel="time / s",
        ylabel="ensemble range / s$^{-1}$",
        title="Between-shadow cumulative spread",
    )
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "03_reference_shadow_decorrelation.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for name, distances in result["decorrelation"]["_distance_series"].items():
        axis.semilogy(
            result["decorrelation"]["_time"],
            np.maximum(distances, 1.0e-16),
            label=name.replace("_", " "),
        )
    axis.axhline(DECORRELATION_DISTANCE, color="red", linestyle="--", label="threshold")
    axis.axvline(DECORRELATION_DEADLINE_SECONDS, color="black", linestyle=":")
    axis.set(
        xlabel="time / s",
        ylabel="wrapped Candidate-A distance",
        title="Independent reference-shadow decorrelation",
    )
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(fontsize=8)
    save_figure(fig, path)
    paths.append(path)

    checkpoint_stats = result["between"]["checkpoint_statistics"]
    checkpoint_times = np.asarray(CHECKPOINTS_SECONDS)
    mean_spectra = np.asarray(
        [
            checkpoint_stats[f"{int(time_value)}s"]["ensemble_mean_per_second"]
            for time_value in checkpoint_times
        ]
    )
    structure = [
        experiment007.hamiltonian_structure_diagnostics(value)
        for value in mean_spectra
    ]
    path = output_dir / "04_ensemble_mean_hamiltonian_diagnostics.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for field, label in (
        ("sum_per_second", "sum"),
        ("outer_pair_sum_per_second", "outer pair"),
        ("inner_pair_sum_per_second", "inner pair"),
    ):
        axis.plot(
            checkpoint_times,
            [item[field] for item in structure],
            marker="o",
            label=label,
        )
    axis.axhline(0.0, color="black", linewidth=0.7)
    axis.set(
        xlabel="time / s",
        ylabel="diagnostic / s$^{-1}$",
        title="Ensemble-mean Hamiltonian diagnostics (supporting only)",
    )
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)
    return paths


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_output_bundle(
    result: dict[str, Any], output_dir: Path, *, plots: bool = True
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    checkpoint_path = output_dir / "checkpoint_spectra.csv"
    cumulative_path = output_dir / "cumulative_timeseries.csv"
    reference_distance_path = output_dir / "reference_pair_distances.csv"
    cycles_path = output_dir / "cycles.json"
    json_write(summary_path, result["summary"])
    write_checkpoint_csv(checkpoint_path, result)
    write_cumulative_csv(cumulative_path, result["runs"])
    write_reference_distance_csv(reference_distance_path, result["decorrelation"])
    write_cycle_json(cycles_path, result["runs"])
    paths = [
        summary_path,
        checkpoint_path,
        cumulative_path,
        reference_distance_path,
        cycles_path,
    ]
    if plots:
        paths.extend(write_plots(output_dir, result))
    manifest_path = output_dir / "manifest.json"
    manifest = {
        "experiment": EXPERIMENT_NAME,
        "output_role": "Experiment 009 independent-shadow compatibility evidence",
        "claim_boundary": "three-shadow 320-second protocol only",
        "source": str(Path(__file__).relative_to(REPOSITORY_ROOT)),
        "files": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in paths
        ],
    }
    json_write(manifest_path, manifest)
    paths.append(manifest_path)
    return paths


def assert_self_check(result: dict[str, Any]) -> None:
    summary = result["summary"]
    assert summary["numerical_validity_accepted"] == all(
        summary["numerical_validity_checks"].values()
    )
    expected_cycles = int(
        round(DURATION_SECONDS / experiment007.QR_INTERVAL_SECONDS)
    )
    for run in result["runs"].values():
        assert run["cycle_count"] == expected_cycles
        recomputed = np.cumsum(run["_cycle_logs"], axis=0)
        np.testing.assert_allclose(
            recomputed,
            run["_cumulative_logs"],
            rtol=0.0,
            atol=experiment007.BOOKKEEPING_ERROR_LIMIT,
        )
        assert np.all(np.isfinite(run["_finite_time_spectrum"]))
    recomputed_classification = classify_compatibility(
        validity_accepted=summary["numerical_validity_accepted"],
        decorrelation_accepted=result["decorrelation"]["accepted"],
        within=result["within"],
        between=result["between"],
    )
    assert recomputed_classification == summary["classification"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "development/chaos_content/outputs/independent_shadow_spectrum_compatibility/baseline"
        ),
    )
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_investigation()
    if args.self_check:
        assert_self_check(result)
    paths = write_output_bundle(result, args.output_dir, plots=not args.no_plots)
    summary = result["summary"]
    print(
        json.dumps(
            {
                "status": summary["status"],
                "classification": summary["classification"],
                "accepted": summary["accepted"],
                "final_shadow_spectra_per_second": {
                    name: run["final_diagnostic_spectrum_per_second"]
                    for name, run in summary["shadow_runs"].items()
                },
                "output_dir": str(args.output_dir),
                "files_written": len(paths),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
