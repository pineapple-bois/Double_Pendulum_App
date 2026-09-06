"""Focused checks for the investigation-only native first-flip prototype."""

from __future__ import annotations

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.first_flip_native_dop853 import (
    prototype_source_identity,
    run_native_first_flip,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.reference import (
    EventIdentity,
    FirstFlipStatus,
    first_flip_time,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    EulerLagrangeState,
)


@pytest.mark.parametrize(
    ("angles", "expected"),
    (
        ((-150.0, -150.0), EventIdentity(1, 1)),
        ((150.0, 150.0), EventIdentity(1, -1)),
        ((179.0, 179.0), EventIdentity(2, 1)),
        ((-179.0, -179.0), EventIdentity(2, -1)),
    ),
)
def test_native_loop_preserves_all_signed_terminal_events(
    angles: tuple[float, float], expected: EventIdentity
) -> None:
    state = EulerLagrangeState.from_degrees(*angles, 0.0, 0.0)
    trusted = first_flip_time(state)
    native = run_native_first_flip(state)
    assert native.result.status is FirstFlipStatus.EVENT_OBSERVED
    assert native.result.event_identities == trusted.event_identities == (expected,)
    assert native.result.raw_event_counts == trusted.raw_event_counts
    assert native.terminal_candidate_count == 1
    assert native.root_iterations > 0
    assert native.result.event_time_seconds is not None
    assert trusted.event_time_seconds is not None
    assert abs(native.result.event_time_seconds - trusted.event_time_seconds) <= 5.0e-8
    assert np.max(
        np.abs(np.asarray(native.result.event_state) - np.asarray(trusted.event_state))
    ) <= 5.0e-7


def test_native_loop_preserves_censoring_and_near_horizon_dense_root() -> None:
    censored = run_native_first_flip(
        EulerLagrangeState.from_degrees(0.0, 0.0, 0.0, 0.0)
    )
    assert censored.result.status is FirstFlipStatus.RIGHT_CENSORED
    assert censored.result.integration_endpoint_seconds == 5.0
    assert censored.result.raw_event_counts == (0, 0, 0, 0)

    state = EulerLagrangeState.from_degrees(-180.0, -13.84615384615384, 0.0, 0.0)
    trusted = first_flip_time(state)
    native = run_native_first_flip(state)
    assert native.result.status is FirstFlipStatus.EVENT_OBSERVED
    assert native.result.event_time_seconds is not None
    assert trusted.event_time_seconds is not None
    assert abs(native.result.event_time_seconds - trusted.event_time_seconds) <= 5.0e-8
    assert max(
        abs(item.residual)
        for item in native.result.event_surface_residuals
        if item.identity in native.result.event_identities
    ) <= 1.0e-10
    assert native.result.maximum_normalized_energy_drift <= 5.0e-9
    assert native.result.maximum_accepted_angular_increment < 0.5


def test_native_loop_reuses_unchanged_licensed_s1_sources() -> None:
    identity = prototype_source_identity()
    assert identity["vendored_source_sha256"] == identity["expected_s1_source_sha256"]
    assert identity["dense_counter_correction"] == "nfcn += 3; -> *nfcn += 3;"
