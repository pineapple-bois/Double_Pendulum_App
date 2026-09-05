"""Production-facing regression coverage for the promoted S1 implementation."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_dop853 import (
    run_renormalized_tangent_compiled_dop853,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_equivalence import (
    compare_results,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    EulerLagrangeState,
    PendulumParameters,
    RenormalizedTangentSpec,
    SolverSpec,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.s1 import (
    S1_SOURCE_SHA256,
    _source_hashes,
    run_renormalized_tangent_s1,
    s1_build_support,
    s1_specification_eligibility,
)


def test_promoted_native_sources_and_license_match_validated_digests() -> None:
    assert _source_hashes() == dict(S1_SOURCE_SHA256)


@pytest.mark.parametrize(
    "theta1,theta2,duration",
    (
        (-np.pi, -np.pi, 5.0),
        (-0.5645049299419158, -0.4417864669110645, 20.0),
    ),
)
def test_promoted_s1_retains_trusted_scientific_record(
    theta1: float,
    theta2: float,
    duration: float,
) -> None:
    if not s1_build_support().supported:
        pytest.skip("S1 native equivalence runs only on the validated build")
    spec = RenormalizedTangentSpec(
        initial_state=EulerLagrangeState(theta1, theta2, 0.0, 0.0),
        duration=duration,
    )
    trusted = run_renormalized_tangent_compiled_dop853(spec)
    promoted = run_renormalized_tangent_s1(spec)
    comparison = compare_results(trusted, promoted)

    assert comparison["accepted"], comparison
    np.testing.assert_array_equal(promoted.cycle_end_time, trusted.cycle_end_time)
    assert (
        promoted.diagnostics.solver_function_evaluations
        == trusted.diagnostics.solver_function_evaluations
    )
    assert promoted.diagnostics.segment_count == trusted.diagnostics.segment_count


@pytest.mark.parametrize(
    "spec",
    (
        replace(
            RenormalizedTangentSpec(),
            initial_state=EulerLagrangeState(np.pi, 0.0, 0.0, 0.0),
        ),
        replace(
            RenormalizedTangentSpec(),
            initial_state=EulerLagrangeState(0.0, 0.0, 0.1, 0.0),
        ),
        replace(
            RenormalizedTangentSpec(),
            parameters=PendulumParameters(length1=1.1),
        ),
        replace(RenormalizedTangentSpec(), initial_tangent=(0.0, 1.0, 0.0, 0.0)),
        replace(RenormalizedTangentSpec(), duration=0.25),
        replace(RenormalizedTangentSpec(), renormalization_interval=0.5),
        replace(RenormalizedTangentSpec(), sampling_interval=0.02),
        replace(RenormalizedTangentSpec(), energy_drift_limit=2.0e-7),
        replace(
            RenormalizedTangentSpec(),
            renormalization_norm_tolerance=2.0e-12,
        ),
        replace(RenormalizedTangentSpec(), characteristic_length=1.1),
        replace(
            RenormalizedTangentSpec(),
            solver=SolverSpec(max_step=0.005),
        ),
    ),
)
def test_s1_allowlist_does_not_expand_beyond_standard_field_policy(
    spec: RenormalizedTangentSpec,
) -> None:
    eligibility = s1_specification_eligibility(spec)
    assert not eligibility.eligible
    assert eligibility.reasons


def test_periodic_lift_is_not_canonicalised_into_s1_eligibility() -> None:
    lifted = replace(
        RenormalizedTangentSpec(),
        initial_state=EulerLagrangeState(2.0 * np.pi, 0.0, 0.0, 0.0),
    )
    assert not s1_specification_eligibility(lifted).eligible


def test_nonfinite_state_remains_a_specification_error() -> None:
    spec = replace(
        RenormalizedTangentSpec(),
        initial_state=EulerLagrangeState(np.nan, 0.0, 0.0, 0.0),
    )
    with pytest.raises(ValueError, match="finite"):
        s1_specification_eligibility(spec)
