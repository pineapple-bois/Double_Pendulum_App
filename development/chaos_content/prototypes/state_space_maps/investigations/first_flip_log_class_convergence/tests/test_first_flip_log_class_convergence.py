from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from development.chaos_content.prototypes.state_space_maps.investigations.first_flip_log_class_convergence.first_flip_log_class_convergence import (
    HORIZON_HAT,
    POLICY_ORDER,
    _load_cases,
    analyze_case,
    logarithmic_class,
    trusted_policies,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.compiled import (
    first_flip_compiled_eligibility,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.reference import (
    gravity_timescale,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    PendulumParameters,
)


HERE = Path(__file__).resolve().parents[1]
CASES = HERE / "selected_cases.json"
EVIDENCE = HERE / "evidence" / "first_flip_log_class_convergence.json"


def _evidence() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_logarithmic_classes_use_half_open_decades_and_separate_energy() -> None:
    expected = (
        (0.999, "tau_hat_lt_1"),
        (1.0, "tau_hat_1_to_10"),
        (10.0, "tau_hat_10_to_100"),
        (100.0, "tau_hat_100_to_1000"),
        (1000.0, "tau_hat_1000_to_10000"),
        (10000.0, "no_flip_observed_by_10000"),
    )
    for value, label in expected:
        assert logarithmic_class(
            value, censored=False, energy_inaccessible=False
        ) == label
    assert logarithmic_class(
        None, censored=True, energy_inaccessible=False
    ) == "no_flip_observed_by_10000"
    assert logarithmic_class(
        None, censored=True, energy_inaccessible=True
    ) == "energy_inaccessible"


def test_case_definition_is_bounded_and_source_checksummed() -> None:
    definition, cases = _load_cases(CASES)
    source = (CASES.parent / definition["source"]["artifact"]).resolve()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == definition["source"][
        "sha256"
    ]
    assert len(cases) == 26
    assert len({case["name"] for case in cases}) == len(cases)
    groups = {case["group"] for case in cases}
    assert {
        "early_control",
        "decade_boundary",
        "decade_interior",
        "known_disagreement",
        "long_lived_region",
        "energy_boundary",
        "energy_inaccessible_control",
    } <= groups
    inaccessible = [case for case in cases if case["energy_inaccessible"]]
    assert len(inaccessible) == 4
    assert all(
        case["initial_energy_joules"] < case["energy_barrier_joules"]
        for case in inaccessible
    )


def test_long_horizon_policies_remain_outside_production_native_allowlist() -> None:
    parameters = PendulumParameters()
    horizon_seconds = HORIZON_HAT * gravity_timescale(parameters)
    policies = trusted_policies(parameters)
    assert tuple(policies) == POLICY_ORDER
    assert policies["strict"].rtol < policies["baseline"].rtol
    assert policies["strict"].atol < policies["baseline"].atol
    assert policies["strict_half_step"].max_step == policies["strict"].max_step / 2.0
    assert all(
        not first_flip_compiled_eligibility(
            parameters, policy, horizon_seconds
        ).eligible
        for policy in policies.values()
    )


def test_saved_evidence_is_complete_gate_valid_and_checksum_consistent() -> None:
    evidence = _evidence()
    cases = evidence["case_definition"]["cases"]
    results = evidence["policy_results"]
    analyses = evidence["case_analysis"]
    assert evidence["physical_contract"]["dimensionless_horizon"] == HORIZON_HAT
    assert len(cases) == 26
    assert len(results) == len(cases) * len(POLICY_ORDER)
    assert len(analyses) == len(cases)
    assert all(result["numerically_valid"] for result in results)
    assert all(not result["validity_issues"] for result in results)
    assert {
        (result["case"], result["policy"]) for result in results
    } == {
        (case["name"], policy) for case in cases for policy in POLICY_ORDER
    }
    render = HERE / evidence["artifacts"]["render_path"]
    assert hashlib.sha256(render.read_bytes()).hexdigest() == evidence["artifacts"][
        "render_sha256"
    ]
    assert evidence["case_definition"]["sha256"] == hashlib.sha256(
        CASES.read_bytes()
    ).hexdigest()


def test_saved_convergence_counts_and_unresolved_cases_recompute() -> None:
    evidence = _evidence()
    analyses = evidence["case_analysis"]
    aggregate = evidence["aggregate"]
    results = evidence["policy_results"]
    assert analyses == [
        analyze_case(
            case,
            [result for result in results if result["case"] == case["name"]],
        )
        for case in evidence["case_definition"]["cases"]
    ]
    assert aggregate["exact_time_stable_count"] == sum(
        item["exact_time_stable"] for item in analyses
    ) == 8
    assert aggregate["decade_stable_count"] == sum(
        item["decade_stable"] for item in analyses
    ) == 22
    assert aggregate["horizon_outcome_stable_count"] == sum(
        item["horizon_outcome_stable"] for item in analyses
    ) == 24
    assert aggregate["arm_agreement_count"] == 16
    assert aggregate["signed_surface_agreement_count"] == 13
    assert all(
        not item["exact_time_stable"] or item["decade_stable"]
        for item in analyses
    )
    assert all(
        not item["decade_stable"] or item["horizon_outcome_stable"]
        for item in analyses
    )
    assert aggregate["horizon_summaries"]["H1000"][
        "logarithmic_class_stable_count"
    ] == 24
    assert aggregate["horizon_summaries"]["H10000"][
        "logarithmic_class_stable_count"
    ] == 22
    assert aggregate["numerically_unresolved_cases"] == [
        "known_h1000_disagreement",
        "known_h1000_disagreement_reflected",
        "energy_boundary_accessible_event",
        "energy_boundary_accessible_survivor",
    ]


def test_reflection_pairs_and_energy_controls_have_expected_evidence() -> None:
    evidence = _evidence()
    results = {
        (result["case"], result["policy"]): result
        for result in evidence["policy_results"]
    }
    for policy in POLICY_ORDER:
        positive = results[("known_h1000_disagreement", policy)]
        negative = results[("known_h1000_disagreement_reflected", policy)]
        assert math.isclose(
            positive["dimensionless_event_time"],
            negative["dimensionless_event_time"],
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        assert positive["first_flipping_arm"] == negative["first_flipping_arm"]
        assert positive["event_direction"] == -negative["event_direction"]
    for name in (
        "energy_boundary_inaccessible",
        "energy_boundary_inaccessible_reflected",
        "energy_inaccessible_equilibrium",
        "energy_inaccessible_oscillation",
    ):
        for policy in POLICY_ORDER:
            result = results[(name, policy)]
            assert result["logarithmic_class"] == "energy_inaccessible"
            assert result["censored"] is True
            assert result["event_observed"] is False
