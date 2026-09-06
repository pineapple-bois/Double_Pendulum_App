from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from development.chaos_content.prototypes.state_space_maps.investigations.first_flip_horizon.first_flip_horizon_and_energy_accessibility import (
    STATUS_CENSORED,
    STATUS_ERROR,
    STATUS_INVALID,
    STATUS_OBSERVED,
    either_flip_energy_barrier,
    energy_inaccessible_mask,
    potential_coefficients,
    production_policy_rejects_horizon,
    winding_energy_barriers,
    zero_velocity_energy,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.reference import (
    default_solver_spec,
    gravity_timescale,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    PendulumParameters,
    simple_energy,
)


HERE = Path(__file__).resolve().parents[1]
EVIDENCE = HERE / "evidence" / "first_flip_horizon_128.json"
ARRAYS = HERE / "evidence" / "first_flip_horizon_128.npz"
TAIL = HERE / "evidence" / "first_flip_H1000_tail_validation.json"


def test_equal_unit_energy_barriers_follow_the_coupled_potential() -> None:
    parameters = PendulumParameters()
    coefficient1, coefficient2 = potential_coefficients(parameters)
    assert coefficient1 == 2.0 * parameters.gravity
    assert coefficient2 == parameters.gravity
    assert winding_energy_barriers(parameters) == (
        parameters.gravity,
        -parameters.gravity,
    )
    assert either_flip_energy_barrier(parameters) == -parameters.gravity


def test_zero_velocity_formula_matches_model_energy_and_keeps_equality_accessible() -> None:
    parameters = PendulumParameters()
    theta1 = np.asarray((0.0, 0.0, math.pi, 1.1))
    theta2 = np.asarray((0.0, math.pi, 0.0, -0.7))
    states = np.column_stack((theta1, theta2, np.zeros(4), np.zeros(4)))
    assert np.allclose(
        zero_velocity_energy(theta1, theta2, parameters),
        simple_energy(states, parameters),
        rtol=0.0,
        atol=2.0e-15,
    )
    mask = energy_inaccessible_mask(theta1, theta2, parameters)
    assert mask.tolist() == [True, False, False, True]
    assert zero_velocity_energy(0.0, math.pi, parameters) == either_flip_energy_barrier(
        parameters
    )


def test_investigation_does_not_broaden_production_horizon_eligibility() -> None:
    parameters = PendulumParameters()
    time_scale = gravity_timescale(parameters)
    assert not production_policy_rejects_horizon(5.0)
    assert production_policy_rejects_horizon(100.0 * time_scale)
    assert default_solver_spec(parameters).max_step == time_scale / 32.0


def test_saved_field_is_monotone_and_energy_inaccessible_cells_never_flip() -> None:
    source = np.load(ARRAYS)
    inaccessible = source["energy_inaccessible"]
    horizons = source["horizons_hat"]
    assert np.allclose(
        horizons,
        [1.0, 10.0, 5.0 / math.sqrt(1.0 / 9.81), 100.0],
        rtol=0.0,
        atol=1.0e-14,
    )
    previous_observed = np.zeros(inaccessible.shape, dtype=bool)
    previous_times = np.full(inaccessible.shape, np.nan)
    for index in range(len(horizons)):
        status = source[f"h{index}_status"]
        observed = status == STATUS_OBSERVED
        assert not np.any(observed & inaccessible)
        assert not np.any((status == STATUS_INVALID) | (status == STATUS_ERROR))
        assert np.all(observed | (status == STATUS_CENSORED))
        assert np.all(observed | ~previous_observed)
        current_times = source[f"h{index}_event_time_seconds"]
        shared = observed & previous_observed
        assert np.allclose(
            current_times[shared], previous_times[shared], rtol=0.0, atol=1.0e-11
        )
        previous_observed = observed
        previous_times = current_times


def test_saved_summary_and_binary_arrays_are_consistent() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    source = np.load(ARRAYS)
    cell_count = int(evidence["grid"]["cell_count"])
    assert evidence["artifacts"]["arrays_sha256"] == hashlib.sha256(
        ARRAYS.read_bytes()
    ).hexdigest()
    assert evidence["energy_accessibility"]["energy_inaccessible_count"] == int(
        np.count_nonzero(source["energy_inaccessible"])
    )
    for index, summary in enumerate(evidence["horizons"]):
        status = source[f"h{index}_status"]
        outcomes = summary["outcomes"]
        assert outcomes["observed_count"] == int(np.count_nonzero(status == STATUS_OBSERVED))
        assert outcomes["censored_count"] == int(np.count_nonzero(status == STATUS_CENSORED))
        assert sum(
            summary["candidate_logarithmic_bins"][name]["count"]
            for name in summary["candidate_logarithmic_bins"]
        ) == outcomes["observed_count"]
        assert (
            outcomes["observed_count"]
            + outcomes["censored_count"]
            + outcomes["invalid_count"]
            + outcomes["error_count"]
            == cell_count
        )
        assert summary["diagnostics"]["fallback_count"] == 0
        assert summary["timings"]["all_workers_stopped"] is True
    assert evidence["native_vs_trusted_preflight"]["accepted"] is True
    assert evidence["native_vs_trusted_representative"]["accepted"] is True


def test_extra_decade_is_rejected_by_tail_equivalence_gate() -> None:
    evidence = json.loads(TAIL.read_text(encoding="utf-8"))
    source_arrays = (HERE / evidence["source_arrays"]).resolve()
    assert evidence["source_arrays_sha256"] == hashlib.sha256(
        source_arrays.read_bytes()
    ).hexdigest()
    assert evidence["accepted"] is False
    cases = {item["name"]: item for item in evidence["cases"]}
    assert cases["H100_latest_observed"]["accepted"] is True
    rejected = cases["H1000_latest_observed"]
    assert rejected["accepted"] is False
    assert rejected["checks"]["event_time"] is False
    assert rejected["checks"]["event_state"] is False
    assert rejected["checks"]["unique_attribution"] is False
