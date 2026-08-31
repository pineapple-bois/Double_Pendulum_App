"""Focused contract and bookkeeping tests for Experiment 012."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import initial_condition_spectrum_robustness as experiment


def synthetic_run(spectrum: np.ndarray, formulation: str) -> dict:
    times = np.arange(
        experiment.QR_INTERVAL_SECONDS,
        experiment.DURATION_SECONDS + experiment.QR_INTERVAL_SECONDS / 2.0,
        experiment.QR_INTERVAL_SECONDS,
    )
    values = np.tile(np.asarray(spectrum, dtype=float), (len(times), 1))
    field = (
        "cumulative_finite_time_spectrum_per_second"
        if formulation == "euler_lagrange"
        else "cumulative_finite_time_diagnostic_per_second"
    )
    cycles = [
        {"end_time_seconds": float(time), field: value}
        for time, value in zip(times, values)
    ]
    reference_time = np.arange(0.0, experiment.DURATION_SECONDS + 0.005, 0.01)
    reference = np.zeros((len(reference_time), 4))
    run = {
        "cycles": cycles,
        "_reference_time": reference_time,
        "_reference_state": reference,
        "_reference_as_el": reference,
    }
    run[
        "_finite_time_spectrum"
        if formulation == "euler_lagrange"
        else "_diagnostic"
    ] = values
    return run


def test_pre_execution_gate_matches_frozen_contract() -> None:
    gate = experiment.pre_execution_gate()

    assert gate["accepted"]
    assert all(gate["checks"].values())
    assert gate["accounting"] == {
        "integrations": 18,
        "simulated_formulation_seconds": 11520.0,
        "qr_cycles": 46080,
        "checkpoint_spectrum_vectors": 144,
    }
    assert gate["per_condition_run_counts"] == {
        "ic_1": 6,
        "ic_2": 6,
        "ic_3": 6,
    }


def test_preregistered_states_and_energies_are_exact() -> None:
    gate = experiment.pre_execution_gate()
    expected = {
        "ic_1": ((-120.0, 0.0, 0.0, 0.0), 0.0),
        "ic_2": ((0.0, 120.0, 0.0, 0.0), -14.715),
        "ic_3": ((120.0, -120.0, 0.0, 0.0), 14.715),
    }

    for name, (state, energy) in expected.items():
        assert tuple(gate["conditions"][name]["state_degrees"]) == state
        assert gate["conditions"][name]["all_velocities_zero"]
        assert np.isclose(
            gate["conditions"][name]["el_energy_joules"], energy, atol=1.0e-12
        )
        assert np.isclose(
            gate["conditions"][name]["canonical_hamiltonian_joules"],
            energy,
            atol=1.0e-12,
        )


def test_shared_qr_runners_preserve_defaults_and_accept_explicit_state() -> None:
    state = np.asarray(experiment.INITIAL_CONDITIONS[0]["state_radians"])
    el_default = experiment.experiment007.run_qr_primitive(
        experiment.experiment006.VariationalDynamics(),
        run_id="test_el_default",
        duration=0.25,
    )
    el_explicit = experiment.experiment007.run_qr_primitive(
        experiment.experiment006.VariationalDynamics(),
        run_id="test_el_explicit",
        duration=0.25,
        initial_reference=state,
    )
    np.testing.assert_allclose(
        el_default["initial_reference"],
        experiment.experiment006.BASE_STATE_RADIANS,
        rtol=0.0,
        atol=0.0,
    )
    np.testing.assert_allclose(el_explicit["initial_reference"], state)

    policy, max_step = experiment.shadow_specs("canonical_hamiltonian")["baseline"]
    canonical_default = experiment.experiment011.run_canonical_qr_primitive(
        experiment.experiment011.CanonicalDynamics(),
        run_id="test_canonical_default",
        duration=0.25,
        policy=policy,
        max_step=max_step,
    )
    canonical_explicit = experiment.experiment011.run_canonical_qr_primitive(
        experiment.experiment011.CanonicalDynamics(),
        run_id="test_canonical_explicit",
        duration=0.25,
        policy=policy,
        max_step=max_step,
        initial_el_state=state,
    )
    np.testing.assert_allclose(
        canonical_default["initial_el_reference"],
        experiment.experiment011.INITIAL_EL_STATE,
        rtol=0.0,
        atol=0.0,
    )
    np.testing.assert_allclose(canonical_explicit["initial_el_reference"], state)


def test_non_decorrelation_does_not_invalidate_settled_result() -> None:
    spectra = {
        "baseline": np.array([0.1, 0.0, 0.0, -0.1]),
        "strict": np.array([0.1, 0.0, 0.0, -0.1]),
        "half_step": np.array([0.1, 0.0, 0.0, -0.1]),
    }
    runs = {
        name: synthetic_run(value, "euler_lagrange")
        for name, value in spectra.items()
    }
    between = experiment.between_shadow_analysis(runs, "euler_lagrange")
    independence = experiment.reference_independence_analysis(
        runs, "euler_lagrange"
    )

    assert between["accepted"]
    assert independence["status"] == "independence_not_demonstrated"
    assert experiment.classify_condition(
        numerical_valid=True,
        settled=True,
        cross_compatible=True,
        independence_demonstrated=False,
    ) == "settled_formulation_agreement_without_demonstrated_shadow_independence"


def test_cross_formulation_rule_is_symmetric_and_same_ic_only() -> None:
    values = {
        "baseline": np.array([0.2, 0.01, -0.01, -0.2]),
        "strict": np.array([0.19, 0.0, 0.0, -0.19]),
        "half_step": np.array([0.21, 0.02, -0.02, -0.21]),
    }
    el_runs = {
        name: synthetic_run(value, "euler_lagrange")
        for name, value in values.items()
    }
    canonical_runs = {
        name: synthetic_run(value, "canonical_hamiltonian")
        for name, value in values.items()
    }
    el_between = experiment.between_shadow_analysis(el_runs, "euler_lagrange")
    canonical_between = experiment.between_shadow_analysis(
        canonical_runs, "canonical_hamiltonian"
    )
    comparison = experiment.cross_formulation_analysis(
        el_runs,
        canonical_runs,
        el_between,
        canonical_between,
        internally_interpretable=True,
    )

    assert comparison["accepted"]
    np.testing.assert_allclose(
        comparison["terminal_mean_absolute_displacement_per_second"], 0.0
    )


def test_experiment_level_verdict_does_not_average_away_failures() -> None:
    accepted = {
        "numerical_validity_accepted": True,
        "settling_accepted": True,
        "cross_formulation_accepted": True,
        "shadow_independence_demonstrated_in_both_formulations": True,
    }
    unsettled = accepted | {"settling_accepted": False}

    assert experiment.experiment_level_verdict([accepted] * 3) == (
        "accepted_independent_shadow_formulation_robustness_across_selected_set"
    )
    assert experiment.experiment_level_verdict([accepted, accepted, unsettled]) == (
        "full_selected_set_unresolved_at_640_seconds"
    )
