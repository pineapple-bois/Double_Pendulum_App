"""Focused tests for dynamics-free first-flip consensus and rendering."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.demonstrations.first_flip_logarithmic_consensus.render_fixture import (
    DEFAULT_FIXTURE,
    load_fixture_classes,
    render_fixture,
)
from development.chaos_content.prototypes.state_space_maps.runners.render_first_flip_field import (
    build_figure,
    build_logarithmic_consensus_figure,
)
from development.chaos_content.prototypes.state_space_maps.src.generation.hdf5 import (
    CellState,
    FieldSnapshot,
    ResumeState,
)
from development.chaos_content.prototypes.state_space_maps.src.logarithmic_first_flip import (
    LOGARITHMIC_CLASS_ORDER,
    FirstFlipLogarithmicClass,
    TrustedPolicyFirstFlipOutcome,
    TrustedPolicyOutcomeStatus,
    classify_zero_velocity_consensus,
    logarithmic_class_for_event_time,
    zero_velocity_energy_inaccessible,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
CONVERGENCE_EVIDENCE = (
    Path(__file__).resolve().parents[2]
    / "investigations/first_flip_log_class_convergence/evidence"
    / "first_flip_log_class_convergence.json"
)


def _event(policy: str, time: float) -> TrustedPolicyFirstFlipOutcome:
    return TrustedPolicyFirstFlipOutcome(
        policy,
        TrustedPolicyOutcomeStatus.EVENT_OBSERVED,
        time,
    )


def _censored(policy: str) -> TrustedPolicyFirstFlipOutcome:
    return TrustedPolicyFirstFlipOutcome(
        policy,
        TrustedPolicyOutcomeStatus.RIGHT_CENSORED,
    )


@pytest.mark.parametrize(
    ("time", "expected"),
    (
        (0.001, FirstFlipLogarithmicClass.TAU_HAT_LT_1),
        (0.999, FirstFlipLogarithmicClass.TAU_HAT_LT_1),
        (1.0, FirstFlipLogarithmicClass.TAU_HAT_1_TO_10),
        (9.999, FirstFlipLogarithmicClass.TAU_HAT_1_TO_10),
        (10.0, FirstFlipLogarithmicClass.TAU_HAT_10_TO_100),
        (99.999, FirstFlipLogarithmicClass.TAU_HAT_10_TO_100),
        (100.0, FirstFlipLogarithmicClass.TAU_HAT_100_TO_1000),
        (999.999, FirstFlipLogarithmicClass.TAU_HAT_100_TO_1000),
        (1000.0, FirstFlipLogarithmicClass.TAU_HAT_1000_TO_10000),
        (9999.999, FirstFlipLogarithmicClass.TAU_HAT_1000_TO_10000),
        (10000.0, FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000),
    ),
)
def test_every_decade_and_exact_boundary(time: float, expected) -> None:
    assert logarithmic_class_for_event_time(time) is expected


def test_unanimous_class_accepts_different_times_inside_one_decade() -> None:
    result = classify_zero_velocity_consensus(
        math.pi,
        0.0,
        (_event("trusted_a", 112.0), _event("trusted_b", 873.0)),
    )
    assert result is FirstFlipLogarithmicClass.TAU_HAT_100_TO_1000


def test_unanimous_censoring_is_distinct_from_energy_inaccessible() -> None:
    outcomes = (_censored("trusted_a"), _censored("trusted_b"))
    assert classify_zero_velocity_consensus(math.pi, 0.0, outcomes) is (
        FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000
    )
    assert classify_zero_velocity_consensus(0.0, 0.0, outcomes) is (
        FirstFlipLogarithmicClass.ENERGY_INACCESSIBLE
    )


def test_policy_decade_disagreement_is_unresolved() -> None:
    result = classify_zero_velocity_consensus(
        math.pi,
        0.0,
        (_event("trusted_a", 999.0), _event("trusted_b", 1000.0)),
    )
    assert result is FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED


def test_policy_event_censor_disagreement_is_unresolved() -> None:
    result = classify_zero_velocity_consensus(
        math.pi,
        0.0,
        (_event("trusted_a", 5000.0), _censored("trusted_b")),
    )
    assert result is FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED


def test_unusable_policy_result_is_unresolved_not_censored() -> None:
    invalid = TrustedPolicyFirstFlipOutcome(
        "trusted_b", TrustedPolicyOutcomeStatus.NUMERICALLY_INVALID
    )
    result = classify_zero_velocity_consensus(
        math.pi,
        0.0,
        (_censored("trusted_a"), invalid),
    )
    assert result is FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED


def test_cap_equality_uses_strict_no_event_by_horizon_convention() -> None:
    result = classify_zero_velocity_consensus(
        math.pi,
        0.0,
        (_event("trusted_a", 10000.0), _censored("trusted_b")),
    )
    assert result is FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000


def test_energy_inaccessible_cannot_be_overwritten_or_hide_contradiction() -> None:
    assert zero_velocity_energy_inaccessible(0.0, 0.0)
    assert not zero_velocity_energy_inaccessible(0.0, math.pi)
    assert classify_zero_velocity_consensus(
        0.0,
        0.0,
        (_censored("trusted_a"), _censored("trusted_b")),
    ) is FirstFlipLogarithmicClass.ENERGY_INACCESSIBLE
    assert classify_zero_velocity_consensus(
        0.0,
        0.0,
        (_event("trusted_a", 5.0), _censored("trusted_b")),
    ) is FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED


def test_consensus_rules_reproduce_selected_convergence_evidence() -> None:
    evidence = json.loads(CONVERGENCE_EVIDENCE.read_text(encoding="utf-8"))
    cases = {item["name"]: item for item in evidence["case_definition"]["cases"]}
    policy_results: dict[str, list[dict[str, object]]] = {}
    for item in evidence["policy_results"]:
        policy_results.setdefault(item["case"], []).append(item)

    def classify(case_name: str) -> FirstFlipLogarithmicClass:
        case = cases[case_name]
        outcomes = []
        for item in policy_results[case_name]:
            if not item["numerically_valid"]:
                status = TrustedPolicyOutcomeStatus.NUMERICALLY_INVALID
            elif item["event_observed"]:
                status = TrustedPolicyOutcomeStatus.EVENT_OBSERVED
            else:
                status = TrustedPolicyOutcomeStatus.RIGHT_CENSORED
            outcomes.append(
                TrustedPolicyFirstFlipOutcome(
                    policy=item["policy"],
                    status=status,
                    dimensionless_event_time=(
                        item["dimensionless_event_time"]
                        if status is TrustedPolicyOutcomeStatus.EVENT_OBSERVED
                        else None
                    ),
                )
            )
        return classify_zero_velocity_consensus(
            case["theta1_radians"], case["theta2_radians"], outcomes
        )

    assert classify("early_arm1_positive") is (
        FirstFlipLogarithmicClass.TAU_HAT_1_TO_10
    )
    assert classify("decade_100_1000_mid300") is (
        FirstFlipLogarithmicClass.TAU_HAT_100_TO_1000
    )
    assert classify("known_h1000_disagreement") is (
        FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED
    )
    assert classify("energy_boundary_accessible_event") is (
        FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED
    )
    assert classify("h1000_survivor_quadrant_pp") is (
        FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000
    )
    assert classify("energy_boundary_inaccessible") is (
        FirstFlipLogarithmicClass.ENERGY_INACCESSIBLE
    )


def test_fixture_contains_every_class_and_renders_through_real_path(
    tmp_path: Path,
) -> None:
    theta1_axis, theta2_axis, classes = load_fixture_classes(DEFAULT_FIXTURE)
    assert set(classes.flat) == set(LOGARITHMIC_CLASS_ORDER)

    figure = build_logarithmic_consensus_figure(
        classes,
        theta1_axis=theta1_axis,
        theta2_axis=theta2_axis,
    )
    assert len(figure.axes[0].get_legend().get_texts()) == len(
        LOGARITHMIC_CLASS_ORDER
    )
    import matplotlib.pyplot as plt

    plt.close(figure)

    output = tmp_path / "fixture.png"
    summary = render_fixture(DEFAULT_FIXTURE, output)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert summary["artifact_kind"] == "non_scientific_semantic_fixture"
    assert summary["dynamics_evaluator_imported"] is False
    assert set(summary["class_counts"].values()) == {1}


def test_established_continuous_renderer_still_uses_primitive_values() -> None:
    values = np.asarray(((1.0, 10.0), (3.0, 10.0)))
    snapshot = FieldSnapshot(
        theta1_axis=np.asarray((-math.pi, 0.0)),
        theta2_axis=np.asarray((-math.pi, 0.0)),
        values=values,
        status=np.full((2, 2), CellState.COMPLETED_VALID, dtype=np.uint8),
        execution_route=np.ones((2, 2), dtype=np.uint8),
        resume_state=ResumeState((), (), (), ()),
        metadata={
            "observable_provenance": {
                "name": "capped_dimensionless_first_flip_time"
            },
            "numerical_parameters": {
                "dimensionless_observation_horizon": 10.0,
                "observation_horizon_seconds": 3.0,
            },
        },
    )
    figure = build_figure(snapshot)
    np.testing.assert_array_equal(figure.axes[0].images[0].get_array().data, values)
    assert len(figure.axes[0].images) == 2
    import matplotlib.pyplot as plt

    plt.close(figure)


def test_classification_and_renderer_imports_do_not_load_dynamics() -> None:
    modules = (
        "development.chaos_content.prototypes.state_space_maps.src.logarithmic_first_flip",
        "development.chaos_content.prototypes.state_space_maps.runners.render_first_flip_field",
        "development.chaos_content.prototypes.state_space_maps.demonstrations."
        "first_flip_logarithmic_consensus.render_fixture",
    )
    for module in modules:
        script = (
            f"import {module}; import sys; "
            "assert not any(name == "
            "'development.chaos_content.prototypes.state_space_maps.src.first_flip' "
            "or name.startswith("
            "'development.chaos_content.prototypes.state_space_maps.src.first_flip.'"
            ") or name == "
            "'development.chaos_content.prototypes.state_space_maps.src.lyapunov' "
            "or name.startswith("
            "'development.chaos_content.prototypes.state_space_maps.src.lyapunov.'"
            ") for name in sys.modules)"
        )
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPOSITORY_ROOT,
            check=True,
        )
