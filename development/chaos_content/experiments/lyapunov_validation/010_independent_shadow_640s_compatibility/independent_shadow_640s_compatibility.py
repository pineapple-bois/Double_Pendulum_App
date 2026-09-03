"""Continue the Experiment 009 three-shadow QR ensemble to 640 seconds."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_009_ROOT = (
    EXPERIMENT_ROOT.parent / "009_independent_shadow_spectrum_compatibility"
)
for import_root in (REPOSITORY_ROOT, EXPERIMENT_009_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import numpy as np

import independent_shadow_spectrum_compatibility as experiment009


experiment007 = experiment009.experiment007
experiment006 = experiment009.experiment006
EXPERIMENT_NAME = "independent_shadow_640s_compatibility"
DURATION_SECONDS = 640.0
CHECKPOINTS_SECONDS = (320.0, 400.0, 480.0, 560.0, 640.0)
LATE_WINDOW_START_SECONDS = 560.0

# Experiment 009's criteria, moved to an identically sized terminal window.
MAX_CHANGE_480_TO_560 = experiment009.MAX_CHANGE_160_TO_240
MAX_CHANGE_560_TO_640 = experiment009.MAX_CHANGE_240_TO_320
MAX_WITHIN_LATE_RANGE = experiment009.MAX_WITHIN_LATE_RANGE
MAX_FINAL_BETWEEN_RANGE = experiment009.MAX_FINAL_BETWEEN_RANGE
MAX_FINAL_BETWEEN_SAMPLE_STD = experiment009.MAX_FINAL_BETWEEN_SAMPLE_STD
MAX_ENSEMBLE_MEAN_CHANGE_560_TO_640 = (
    experiment009.MAX_ENSEMBLE_MEAN_CHANGE_240_TO_320
)
MAX_LATE_WINDOW_BETWEEN_RANGE = experiment009.MAX_LATE_WINDOW_BETWEEN_RANGE
CLEAR_INCOMPATIBILITY_LIMIT = experiment009.CLEAR_INCOMPATIBILITY_LIMIT
PREFIX_REPRODUCTION_LIMIT = 1.0e-12

PRIOR_FINAL_SPECTRA = {
    "baseline": np.array(
        [
            0.9905701481654374,
            0.0101030388310209,
            -0.007600214343032423,
            -0.9952028999198385,
        ]
    ),
    "strict": np.array(
        [
            0.9503654635081029,
            0.012889031646623573,
            -0.009377965532661391,
            -0.9555308616397173,
        ]
    ),
    "half_step": np.array(
        [
            1.0055884099465415,
            0.014313055928105636,
            -0.008048789405077316,
            -1.012810347370304,
        ]
    ),
}
PRIOR_FINAL_MAXIMUM_RANGE = 0.05727948573058672
PRIOR_LATE_MAXIMUM_RANGE = 0.0966595780916194


def shadow_specs() -> dict[str, tuple[Any, float]]:
    """Return the unchanged Experiment 009 policies."""

    return experiment009.shadow_specs()


def checkpoint_spectra(run: dict[str, Any]) -> dict[str, np.ndarray]:
    return {
        f"{int(time_value)}s": experiment007.spectrum_at_time(run, time_value)
        for time_value in CHECKPOINTS_SECONDS
    }


def prefix_reproduction(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    differences = {
        name: np.abs(
            experiment007.spectrum_at_time(run, 320.0) - PRIOR_FINAL_SPECTRA[name]
        )
        for name, run in runs.items()
    }
    maximum = max(float(np.max(value)) for value in differences.values())
    return {
        "accepted": maximum <= PREFIX_REPRODUCTION_LIMIT,
        "limit_per_second": PREFIX_REPRODUCTION_LIMIT,
        "component_absolute_differences_per_second": {
            name: value.tolist() for name, value in differences.items()
        },
        "maximum_absolute_difference_per_second": maximum,
        "provenance": "committed Experiment 009 320-second final spectra",
    }


def within_shadow_analysis(run: dict[str, Any]) -> dict[str, Any]:
    checkpoints = checkpoint_spectra(run)
    change_480_to_560 = np.abs(checkpoints["560s"] - checkpoints["480s"])
    change_560_to_640 = np.abs(checkpoints["640s"] - checkpoints["560s"])
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
        "checkpoint_spectra_per_second": {
            key: value.tolist() for key, value in checkpoints.items()
        },
        "component_change_480_to_560_per_second": change_480_to_560.tolist(),
        "maximum_change_480_to_560_per_second": float(
            np.max(change_480_to_560)
        ),
        "component_change_560_to_640_per_second": change_560_to_640.tolist(),
        "maximum_change_560_to_640_per_second": float(
            np.max(change_560_to_640)
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
    mean_change = np.abs(ensemble_means["640s"] - ensemble_means["560s"])
    final = checkpoint_statistics["640s"]
    final_ranges = np.asarray(final["component_range_per_second"])
    final_stds = np.asarray(final["sample_standard_deviation_per_second"])
    per_shadow_late_changes = np.asarray(
        [
            np.abs(
                experiment007.spectrum_at_time(run, 640.0)
                - experiment007.spectrum_at_time(run, 560.0)
            )
            for run in runs.values()
        ]
    )
    uncertainty = np.maximum.reduce(
        [final_stds, final_ranges / 2.0, np.max(per_shadow_late_changes, axis=0)]
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
        "ensemble_mean_component_change_560_to_640_per_second": mean_change.tolist(),
        "maximum_ensemble_mean_change_560_to_640_per_second": float(
            np.max(mean_change)
        ),
        "late_window_component_ranges_per_second": np.max(
            late_ranges, axis=0
        ).tolist(),
        "maximum_late_window_between_range_per_second": maximum_late_range,
        "final_descriptive_uncertainty_half_width_per_second": uncertainty.tolist(),
        "uncertainty_definition": (
            "componentwise maximum of final sample standard deviation, half final "
            "range, and largest absolute per-shadow 560-to-640 change"
        ),
        "_late_times": common_end_times[late_mask],
        "_late_ranges": late_ranges,
    }


def classify_compatibility(
    *,
    validity_accepted: bool,
    decorrelation_accepted: bool,
    prefix_accepted: bool,
    within: dict[str, dict[str, Any]],
    between: dict[str, Any],
) -> str:
    if not validity_accepted or not decorrelation_accepted or not prefix_accepted:
        return "numerically_unresolved_at_640_seconds"
    if all(item["accepted"] for item in within.values()) and between["accepted"]:
        return "accepted_statistical_compatibility_at_640_seconds"

    final_range = between["checkpoint_statistics"]["640s"][
        "maximum_component_range_per_second"
    ]
    late_range = between["maximum_late_window_between_range_per_second"]
    relevant_values = [
        final_range,
        late_range,
        between["maximum_ensemble_mean_change_560_to_640_per_second"],
        *[
            item["maximum_change_480_to_560_per_second"]
            for item in within.values()
        ],
        *[
            item["maximum_change_560_to_640_per_second"]
            for item in within.values()
        ],
        *[
            item["maximum_late_component_range_per_second"]
            for item in within.values()
        ],
    ]
    final_still_fails_without_contraction = (
        final_range > MAX_FINAL_BETWEEN_RANGE
        and final_range >= PRIOR_FINAL_MAXIMUM_RANGE
    )
    late_still_fails_without_contraction = (
        late_range > MAX_LATE_WINDOW_BETWEEN_RANGE
        and late_range >= PRIOR_LATE_MAXIMUM_RANGE
    )
    if (
        max(relevant_values) > CLEAR_INCOMPATIBILITY_LIMIT
        or final_still_fails_without_contraction
        or late_still_fails_without_contraction
    ):
        return "rejected_plateau_or_material_worsening_at_640_seconds"
    if (
        final_range < PRIOR_FINAL_MAXIMUM_RANGE
        and late_range < PRIOR_LATE_MAXIMUM_RANGE
    ):
        return "unresolved_but_continuing_contraction_at_640_seconds"
    return "rejected_plateau_or_material_worsening_at_640_seconds"


def _public(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if not key.startswith("_")}


def run_investigation() -> dict[str, Any]:
    dynamics = experiment006.VariationalDynamics()
    runs = {
        name: experiment007.run_qr_primitive(
            dynamics,
            run_id=f"{name}_640s",
            duration=DURATION_SECONDS,
            qr_interval=experiment007.QR_INTERVAL_SECONDS,
            policy=policy,
            max_step=max_step,
        )
        for name, (policy, max_step) in shadow_specs().items()
    }
    decorrelation = experiment009.reference_decorrelation_analysis(runs)
    prefix = prefix_reproduction(runs)
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
        prefix_accepted=prefix["accepted"],
        within=within,
        between=between,
    )
    accepted = classification.startswith("accepted_")
    final_stats = between["checkpoint_statistics"]["640s"]
    final_mean = final_stats["ensemble_mean_per_second"]
    uncertainty = between["final_descriptive_uncertainty_half_width_per_second"]

    if accepted:
        status = "accepted_statistical_compatibility_at_640_seconds"
        strongest_claim = (
            "Three independently integrated, decorrelated Euler-Lagrange numerical "
            "shadows satisfy the predeclared within-shadow settling and between-"
            "shadow compatibility criteria at 640 seconds."
        )
        next_question = (
            "Does an independently formulated Hamiltonian/canonical tangent QR "
            "calculation reproduce this compatible Euler-Lagrange spectrum estimate?"
        )
    elif classification.startswith("unresolved_but"):
        status = "unresolved_but_continuing_contraction_at_640_seconds"
        strongest_claim = (
            "The valid three-shadow estimates continue to contract relative to "
            "Experiment 009 but do not satisfy every predeclared compatibility limit."
        )
        next_question = (
            "Should long-time convergence next be tested with a predeclared block-"
            "increment sampling design rather than another single duration extension?"
        )
    elif classification.startswith("rejected_"):
        status = "rejected_statistical_compatibility_at_640_seconds"
        strongest_claim = (
            "The valid three-shadow ensemble does not show the required continuing "
            "contraction at 640 seconds under the predeclared criteria."
        )
        next_question = (
            "What feature of the long-time QR increments causes the observed spread "
            "to plateau or worsen across independently integrated shadows?"
        )
    else:
        status = "numerically_unresolved_at_640_seconds"
        strongest_claim = (
            "A numerical validity, decorrelation, or exact-continuation check failed, "
            "so the 640-second statistical comparison is not interpretable."
        )
        next_question = "Which failed numerical guard invalidated the continuation?"

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
        "minimum_r_diagonal": min(run["minimum_r_diagonal"] for run in runs.values()),
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
            "Does extending the same three independently integrated chaotic shadows "
            "from 320 seconds to 640 seconds bring late-window fluctuation and "
            "between-shadow spread below the predeclared compatibility limits?"
        ),
        "continuation_design": {
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
                "exact one-step continuation of the three deterministic Experiment "
                "009 numerical shadows"
            ),
        },
        "criteria": {
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
            "clear_incompatibility_limit_per_second": CLEAR_INCOMPATIBILITY_LIMIT,
            "prefix_reproduction_limit_per_second": PREFIX_REPRODUCTION_LIMIT,
            "prior_320_final_maximum_range_per_second": PRIOR_FINAL_MAXIMUM_RANGE,
            "prior_240_to_320_late_maximum_range_per_second": (
                PRIOR_LATE_MAXIMUM_RANGE
            ),
            "criteria_provenance": "predeclared in README before the 640-second run",
        },
        "shadow_runs": {
            name: experiment009.public_run_summary(run)
            for name, run in runs.items()
        },
        "prefix_reproduction": prefix,
        "reference_decorrelation": _public(decorrelation),
        "within_shadow": within,
        "between_shadow": _public(between),
        "ensemble_spectrum_estimate_per_second": final_mean,
        "descriptive_uncertainty_half_width_per_second": uncertainty,
        "ensemble_mean_hamiltonian_diagnostics": (
            experiment007.hamiltonian_structure_diagnostics(
                np.asarray(final_mean, dtype=float)
            )
        ),
        "numerical_validity_checks": validity_checks,
        "numerical_validity_accepted": validity_accepted,
        "numerical_extrema": numerical_extrema,
        "strongest_claim": strongest_claim,
        "claim_boundary": (
            "The result applies only to three deterministic numerical shadows of "
            "one Euler-Lagrange initial condition under the declared 640-second "
            "Candidate-A QR protocol. It does not establish all-duration, all-shadow, "
            "norm, initial-condition, or canonical-formulation invariance and is not "
            "a general chaos classification."
        ),
        "next_question": next_question,
    }
    return {
        "summary": summary,
        "runs": runs,
        "decorrelation": decorrelation,
        "prefix": prefix,
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
                diagnostics = analysis["hamiltonian_diagnostics"][checkpoint_key]
                row: dict[str, Any] = {
                    "shadow": name,
                    "checkpoint_seconds": float(checkpoint_key.removesuffix("s")),
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


def write_cycles_json(path: Path, runs: dict[str, dict[str, Any]]) -> None:
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
    names = list(result["runs"])
    times = np.asarray(
        [cycle["end_time_seconds"] for cycle in result["runs"][names[0]]["cycles"]]
    )

    path = output_dir / "01_cumulative_shadow_spectra.png"
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True)
    for component, axis in enumerate(axes.flat):
        for name, run in result["runs"].items():
            axis.plot(times, run["_finite_time_spectrum"][:, component], label=name)
        axis.axhline(0.0, color="black", linewidth=0.7)
        axis.axvspan(LATE_WINDOW_START_SECONDS, DURATION_SECONDS, color="grey", alpha=0.1)
        axis.set_title(f"fixed QR column {component + 1}")
        axis.grid(True, alpha=0.25)
    axes[0, 0].legend(fontsize=8)
    for axis in axes[-1]:
        axis.set_xlabel("time / s")
    for axis in axes[:, 0]:
        axis.set_ylabel("cumulative value / s$^{-1}$")
    fig.suptitle("Experiment 010 cumulative QR estimates")
    save_figure(fig, path)
    paths.append(path)

    stacked = np.asarray(
        [run["_finite_time_spectrum"] for run in result["runs"].values()]
    )
    path = output_dir / "02_between_shadow_spread.png"
    fig, axis = plt.subplots(figsize=(8, 5))
    for component in range(4):
        axis.plot(times, np.ptp(stacked, axis=0)[:, component], label=f"column {component + 1}")
    axis.axhline(MAX_FINAL_BETWEEN_RANGE, color="red", linestyle="--", label="final limit")
    axis.axvspan(LATE_WINDOW_START_SECONDS, DURATION_SECONDS, color="grey", alpha=0.1)
    axis.set(xlabel="time / s", ylabel="ensemble range / s$^{-1}$", title="Between-shadow cumulative spread")
    axis.grid(True, alpha=0.25)
    axis.legend()
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "03_ensemble_mean_hamiltonian_diagnostics.png"
    checkpoint_stats = result["between"]["checkpoint_statistics"]
    means = np.asarray(
        [checkpoint_stats[f"{int(time)}s"]["ensemble_mean_per_second"] for time in CHECKPOINTS_SECONDS]
    )
    diagnostics = [experiment007.hamiltonian_structure_diagnostics(value) for value in means]
    fig, axis = plt.subplots(figsize=(8, 5))
    for field, label in (
        ("sum_per_second", "sum"),
        ("outer_pair_sum_per_second", "outer pair"),
        ("inner_pair_sum_per_second", "inner pair"),
    ):
        axis.plot(CHECKPOINTS_SECONDS, [item[field] for item in diagnostics], marker="o", label=label)
    axis.axhline(0.0, color="black", linewidth=0.7)
    axis.set(xlabel="time / s", ylabel="diagnostic / s$^{-1}$", title="Ensemble-mean Hamiltonian diagnostics")
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
    reference_path = output_dir / "reference_pair_distances.csv"
    cycles_path = output_dir / "cycles.json"
    json_write(summary_path, result["summary"])
    write_checkpoint_csv(checkpoint_path, result)
    write_cumulative_csv(cumulative_path, result["runs"])
    experiment009.write_reference_distance_csv(reference_path, result["decorrelation"])
    write_cycles_json(cycles_path, result["runs"])
    paths = [summary_path, checkpoint_path, cumulative_path, reference_path, cycles_path]
    if plots:
        paths.extend(write_plots(output_dir, result))
    manifest_path = output_dir / "manifest.json"
    manifest = {
        "experiment": EXPERIMENT_NAME,
        "output_role": "Experiment 010 exact 640-second continuation evidence",
        "claim_boundary": "three-shadow 640-second Candidate-A QR protocol only",
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
    expected_cycles = int(round(DURATION_SECONDS / experiment007.QR_INTERVAL_SECONDS))
    assert summary["numerical_validity_accepted"] == all(
        summary["numerical_validity_checks"].values()
    )
    for run in result["runs"].values():
        assert run["cycle_count"] == expected_cycles
        np.testing.assert_allclose(
            np.cumsum(run["_cycle_logs"], axis=0),
            run["_cumulative_logs"],
            rtol=0.0,
            atol=experiment007.BOOKKEEPING_ERROR_LIMIT,
        )
        assert np.all(np.isfinite(run["_finite_time_spectrum"]))
    recomputed = classify_compatibility(
        validity_accepted=summary["numerical_validity_accepted"],
        decorrelation_accepted=result["decorrelation"]["accepted"],
        prefix_accepted=result["prefix"]["accepted"],
        within=result["within"],
        between=result["between"],
    )
    assert recomputed == summary["classification"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "development/chaos_content/outputs/independent_shadow_640s_compatibility/baseline"
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
                "ensemble_spectrum_estimate_per_second": summary[
                    "ensemble_spectrum_estimate_per_second"
                ],
                "output_dir": str(args.output_dir),
                "files_written": len(paths),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
