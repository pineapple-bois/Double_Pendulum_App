"""Regression gates for the Experiment 020 reference promotion."""

from __future__ import annotations

import importlib

import pytest

from development.chaos_content.prototypes.state_space_maps.src.first_flip.reference import (
    EventIdentity,
    FirstFlipStatus,
    first_flip_time,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    EulerLagrangeState,
)


CASES = (
    ((-150.0, -150.0), EventIdentity(1, +1)),
    ((150.0, 150.0), EventIdentity(1, -1)),
    ((179.0, 179.0), EventIdentity(2, +1)),
    ((-179.0, -179.0), EventIdentity(2, -1)),
)


@pytest.mark.parametrize(("angles", "expected_identity"), CASES)
def test_promoted_reference_agrees_with_accepted_experiment(
    angles: tuple[float, float],
    expected_identity: EventIdentity,
) -> None:
    experiment = importlib.import_module(
        "development.chaos_content.experiments.physical_observables."
        "020_first_flip_event_contract.first_flip_event_contract"
    )
    state = EulerLagrangeState.from_degrees(*angles, 0.0, 0.0)
    promoted = first_flip_time(state)
    accepted = experiment.first_flip_time(state)

    assert promoted.status is FirstFlipStatus.EVENT_OBSERVED
    assert promoted.event_identities == (expected_identity,)
    assert promoted.event_time_seconds == pytest.approx(
        accepted.event_time_seconds, rel=0.0, abs=2.0e-13
    )
    assert promoted.dimensionless_event_time == pytest.approx(
        accepted.dimensionless_event_time, rel=0.0, abs=1.0e-12
    )
    assert promoted.event_state == pytest.approx(
        accepted.event_state, rel=0.0, abs=2.0e-12
    )
    assert promoted.rhs_evaluations == accepted.rhs_evaluations


def test_promoted_reference_preserves_right_censoring() -> None:
    result = first_flip_time((0.0, 0.0, 0.0, 0.0), observation_horizon=1.0)

    assert result.status is FirstFlipStatus.RIGHT_CENSORED
    assert result.censored
    assert not result.event_observed
    assert result.event_time_seconds is None
    assert result.dimensionless_event_time is None
    assert result.integration_endpoint_seconds == pytest.approx(1.0)
