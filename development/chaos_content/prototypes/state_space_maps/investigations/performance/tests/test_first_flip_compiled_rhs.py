"""Focused checks for the investigation-only compiled first-flip RHS."""

from __future__ import annotations

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.benchmark_first_flip_compiled_rhs import (
    SIGNED_CASES,
    compare_case,
    Case,
)
from development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.first_flip_compiled_rhs import (
    compiled_rhs,
    first_flip_time_compiled_rhs,
    warm_compiled_rhs,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.field_adapter import (
    FirstFlipFieldSpec,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.reference import (
    FirstFlipStatus,
    _cached_dynamics,
    first_flip_time,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    EulerLagrangeState,
    PendulumParameters,
)


def test_compiled_kernel_matches_trusted_physical_flow() -> None:
    parameters = PendulumParameters()
    trusted = _cached_dynamics(parameters).flow
    candidate = compiled_rhs(parameters)
    warm_compiled_rhs(parameters)
    for state in (
        np.zeros(4),
        np.array((-2.6, -2.2, 0.0, 0.0)),
        np.array((3.7, -4.2, 2.4, -3.1)),
    ):
        assert candidate(0.37, state) == pytest.approx(
            trusted(0.37, state), rel=0.0, abs=2.0e-14
        )


@pytest.mark.parametrize(("name", "angles", "identity"), SIGNED_CASES)
def test_experiment_020_cases_preserve_complete_event_contract(
    name: str,
    angles: tuple[float, float],
    identity,
) -> None:
    case = Case(
        name=name,
        source="experiment_020",
        category="contract",
        theta1_radians=float(np.deg2rad(angles[0])),
        theta2_radians=float(np.deg2rad(angles[1])),
        weighting_sample=False,
        expected_identity=identity,
    )
    comparison, _trusted, _compiled = compare_case(case, FirstFlipFieldSpec())
    assert comparison["accepted"]
    assert all(comparison["checks"].values())


def test_compiled_rhs_preserves_censoring_and_default_route_is_untouched() -> None:
    state = EulerLagrangeState(0.0, 0.0, 0.0, 0.0)
    trusted = first_flip_time(state)
    compiled = first_flip_time_compiled_rhs(state)

    assert trusted.status is FirstFlipStatus.RIGHT_CENSORED
    assert compiled.status is trusted.status
    assert compiled.event_time_seconds is None
    assert compiled.event_state is None
    assert compiled.rhs_evaluations == trusted.rhs_evaluations
