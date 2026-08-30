"""Focused tests for the Experiment 010 continuation statistics."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np

EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import independent_shadow_640s_compatibility as experiment


def synthetic_run(
    spectrum: np.ndarray,
    *,
    late_slope: float = 0.0,
) -> dict:
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
    return {"cycles": cycles, "_finite_time_spectrum": spectra}


def accepted_components() -> tuple[dict[str, dict], dict]:
    spectra = {
        "baseline": np.array([0.91, 0.01, -0.01, -0.91]),
        "strict": np.array([0.90, 0.00, 0.00, -0.90]),
        "half_step": np.array([0.89, 0.02, -0.02, -0.89]),
    }
    runs = {name: synthetic_run(value) for name, value in spectra.items()}
    within = {
        name: experiment.within_shadow_analysis(run)
        for name, run in runs.items()
    }
    return within, experiment.between_shadow_analysis(runs)


def test_continuation_design_matches_experiment009() -> None:
    assert experiment.shadow_specs() == experiment.experiment009.shadow_specs()
    assert experiment.experiment007.QR_INTERVAL_SECONDS == 0.25
    assert experiment.CHECKPOINTS_SECONDS == (320.0, 400.0, 480.0, 560.0, 640.0)


def test_prefix_reproduction_uses_committed_320_second_values() -> None:
    runs = {
        name: synthetic_run(value)
        for name, value in experiment.PRIOR_FINAL_SPECTRA.items()
    }
    analysis = experiment.prefix_reproduction(runs)

    assert analysis["accepted"]
    assert analysis["maximum_absolute_difference_per_second"] == 0.0


def test_within_shadow_analysis_uses_terminal_eighty_second_window() -> None:
    run = synthetic_run(np.array([0.9, 0.01, -0.01, -0.9]))
    analysis = experiment.within_shadow_analysis(run)

    assert analysis["accepted"]
    assert analysis["maximum_change_480_to_560_per_second"] == 0.0
    assert analysis["maximum_change_560_to_640_per_second"] == 0.0
    assert analysis["maximum_late_component_range_per_second"] == 0.0


def test_between_shadow_analysis_reports_uncertainty_envelope() -> None:
    runs = {
        "baseline": synthetic_run(np.array([0.91, 0.01, -0.01, -0.91])),
        "strict": synthetic_run(np.array([0.90, 0.00, 0.00, -0.90])),
        "half_step": synthetic_run(np.array([0.89, 0.02, -0.02, -0.89])),
    }
    analysis = experiment.between_shadow_analysis(runs)

    assert analysis["accepted"]
    np.testing.assert_allclose(
        analysis["checkpoint_statistics"]["640s"][
            "component_range_per_second"
        ],
        [0.02, 0.02, 0.02, 0.02],
        rtol=0.0,
        atol=1.0e-14,
    )
    np.testing.assert_allclose(
        analysis["final_descriptive_uncertainty_half_width_per_second"],
        [0.01, 0.01, 0.01, 0.01],
        rtol=0.0,
        atol=1.0e-14,
    )


def test_classification_covers_predeclared_outcomes() -> None:
    within, between = accepted_components()
    assert experiment.classify_compatibility(
        validity_accepted=True,
        decorrelation_accepted=True,
        prefix_accepted=True,
        within=within,
        between=between,
    ) == "accepted_statistical_compatibility_at_640_seconds"

    unresolved = copy.deepcopy(between)
    unresolved["accepted"] = False
    unresolved["checkpoint_statistics"]["640s"][
        "maximum_component_range_per_second"
    ] = 0.055
    unresolved["maximum_late_window_between_range_per_second"] = 0.08
    assert experiment.classify_compatibility(
        validity_accepted=True,
        decorrelation_accepted=True,
        prefix_accepted=True,
        within=within,
        between=unresolved,
    ) == "unresolved_but_continuing_contraction_at_640_seconds"

    rejected = copy.deepcopy(unresolved)
    rejected["maximum_late_window_between_range_per_second"] = 0.097
    assert experiment.classify_compatibility(
        validity_accepted=True,
        decorrelation_accepted=True,
        prefix_accepted=True,
        within=within,
        between=rejected,
    ) == "rejected_plateau_or_material_worsening_at_640_seconds"

    assert experiment.classify_compatibility(
        validity_accepted=True,
        decorrelation_accepted=True,
        prefix_accepted=False,
        within=within,
        between=between,
    ) == "numerically_unresolved_at_640_seconds"
