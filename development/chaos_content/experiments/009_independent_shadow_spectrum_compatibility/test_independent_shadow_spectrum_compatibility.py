"""Focused tests for Experiment 009 long-time shadow statistics."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import independent_shadow_spectrum_compatibility as experiment


def synthetic_run(spectrum: np.ndarray, *, late_slope: float = 0.0) -> dict:
    times = np.arange(0.25, experiment.DURATION_SECONDS + 0.125, 0.25)
    spectra = np.tile(np.asarray(spectrum, dtype=float), (len(times), 1))
    late_mask = times >= experiment.LATE_WINDOW_START_SECONDS
    spectra[late_mask, 0] += late_slope * (
        times[late_mask] - experiment.LATE_WINDOW_START_SECONDS
    )
    cycles = [
        {
            "end_time_seconds": float(time_value),
            "cumulative_finite_time_spectrum_per_second": values.tolist(),
        }
        for time_value, values in zip(times, spectra)
    ]
    return {
        "cycles": cycles,
        "_finite_time_spectrum": spectra,
    }


def test_scaled_reference_distance_wraps_angles_and_scales_velocities() -> None:
    characteristic_time = experiment.experiment006.characteristic_time()
    first = np.array([[np.pi - 1.0e-6, 0.0, 0.0, 0.0]])
    second = np.array([[-np.pi + 1.0e-6, 0.0, 1.0, 0.0]])
    distance = experiment.scaled_reference_distance(first, second)

    expected = np.hypot(2.0e-6, characteristic_time)
    np.testing.assert_allclose(distance, [expected], rtol=0.0, atol=1.0e-12)


def test_reference_decorrelation_uses_distance_not_pointwise_agreement() -> None:
    time = np.array([0.0, 40.0, 80.0])
    scale = experiment.experiment006.characteristic_time()
    base = np.zeros((3, 4))
    strict = np.zeros((3, 4))
    half_step = np.zeros((3, 4))
    strict[1:, 2] = 1.2 / scale
    half_step[1:, 2] = -1.2 / scale
    runs = {
        "baseline": {"_reference_time": time, "_reference_state": base},
        "strict": {"_reference_time": time, "_reference_state": strict},
        "half_step": {"_reference_time": time, "_reference_state": half_step},
    }

    analysis = experiment.reference_decorrelation_analysis(runs)

    assert analysis["accepted"]
    assert all(
        pair["first_threshold_crossing_seconds"] == 40.0
        for pair in analysis["pairs"].values()
    )


def test_within_shadow_analysis_accepts_settled_cumulative_values() -> None:
    run = synthetic_run(np.array([0.9, 0.01, -0.01, -0.9]))
    analysis = experiment.within_shadow_analysis(run)

    assert analysis["accepted"]
    assert analysis["maximum_change_160_to_240_per_second"] == 0.0
    assert analysis["maximum_change_240_to_320_per_second"] == 0.0
    assert analysis["maximum_late_component_range_per_second"] == 0.0


def test_between_shadow_analysis_reports_range_and_sample_std() -> None:
    runs = {
        "baseline": synthetic_run(np.array([0.9, 0.01, -0.01, -0.9])),
        "strict": synthetic_run(np.array([0.91, 0.0, 0.0, -0.91])),
        "half_step": synthetic_run(np.array([0.89, 0.02, -0.02, -0.89])),
    }
    analysis = experiment.between_shadow_analysis(runs)

    assert analysis["accepted"]
    np.testing.assert_allclose(
        analysis["checkpoint_statistics"]["320s"]["component_range_per_second"],
        [0.02, 0.02, 0.02, 0.02],
        rtol=0.0,
        atol=1.0e-14,
    )


def test_compatibility_classification_is_ternary() -> None:
    within = {
        name: experiment.within_shadow_analysis(
            synthetic_run(np.array([0.9, 0.01, -0.01, -0.9]))
        )
        for name in ("baseline", "strict", "half_step")
    }
    between = experiment.between_shadow_analysis(
        {
            name: synthetic_run(np.array([0.9, 0.01, -0.01, -0.9]))
            for name in within
        }
    )

    assert experiment.classify_compatibility(
        validity_accepted=True,
        decorrelation_accepted=True,
        within=within,
        between=between,
    ) == "accepted_statistical_compatibility"

    clearly_incompatible = copy.deepcopy(between)
    clearly_incompatible["accepted"] = False
    clearly_incompatible["checkpoint_statistics"]["320s"][
        "maximum_component_range_per_second"
    ] = 0.11
    assert experiment.classify_compatibility(
        validity_accepted=True,
        decorrelation_accepted=True,
        within=within,
        between=clearly_incompatible,
    ) == "clearly_incompatible_at_320_seconds"

    assert experiment.classify_compatibility(
        validity_accepted=False,
        decorrelation_accepted=True,
        within=within,
        between=between,
    ) == "unresolved_at_320_seconds"

