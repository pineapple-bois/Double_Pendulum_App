"""Compare a predeclared set of Stage 1 sensitivity regimes.

The adjacent README.md owns the mathematical and numerical contract. This is
a narrow extension of the fixed-pair experiment, not a reusable Chaos API.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import minimal_initial_condition_sensitivity as fixed_pair


COMPARISON_NAME = "predeclared_20_second_regime_selection"
QUESTION = (
    "Can a small, physically motivated set of simple-double-pendulum initial "
    "conditions spanning regular to strongly nonlinear motion reveal materially "
    "different finite-time sensitivity under the same perturbation and numerical "
    "policy within the existing 20-second simulation horizon?"
)

# These cases and their hypotheses were recorded in README.md before integration.
CASES: tuple[dict[str, Any], ...] = (
    {
        "name": fixed_pair.EXPERIMENT_NAME,
        "base_state_degrees": (0.0, 120.0, 0.0, 0.0),
        "declared_base_energy_joules": -14.715,
        "declared_pair_energy_difference_joules": 1.48277350947e-4,
        "classification": "retained_regular_control",
        "rationale": (
            "The prior numerically accepted fixed run remained close for 20 seconds, "
            "so it controls against treating every small perturbation as visibly sensitive."
        ),
    },
    {
        "name": "small_angle_in_phase",
        "base_state_degrees": (10.0, 10.0, 0.0, 0.0),
        "declared_base_energy_joules": -28.9828921711,
        "declared_pair_energy_difference_joules": 2.9732956687e-5,
        "classification": "low_excitation_low_complexity_hypothesis",
        "rationale": (
            "Low excitation and nearly aligned links should remain close to the "
            "small-angle, low-complexity regime."
        ),
    },
    {
        "name": "nonlinear_bounded_release",
        "base_state_degrees": (45.0, 60.0, 0.0, 0.0),
        "declared_base_energy_joules": -18.7784350469,
        "declared_pair_energy_difference_joules": 1.48278845092e-4,
        "classification": "bounded_nonlinear_swing_hypothesis",
        "rationale": (
            "A large-angle rest release introduces nonlinear coupling while total "
            "energy remains below the second-link upright potential barrier."
        ),
    },
    {
        "name": "second_link_rotation_access",
        "base_state_degrees": (0.0, 0.0, 0.0, 360.0),
        "declared_base_energy_joules": -9.69079119782,
        "declared_pair_energy_difference_joules": 1.49414880468e-9,
        "classification": "near_rotation_barrier_hypothesis",
        "rationale": (
            "Second-link kinetic energy puts total energy only 0.119 J above the "
            "theta1=0, theta2=pi potential barrier, allowing but not guaranteeing rotation."
        ),
    },
    {
        "name": "opposed_high_energy_fixture",
        "base_state_degrees": (120.0, -120.0, 120.0, -90.0),
        "declared_base_energy_joules": 21.9801254619,
        "declared_pair_energy_difference_joules": -9.85527562207e-5,
        "classification": "strongly_coupled_high_excitation_hypothesis",
        "rationale": (
            "Opposed large angles and counter-moving velocities create strong coupling; "
            "the base state also has an independent production numerical-test provenance."
        ),
    },
    {
        "name": "near_inverted_release",
        "base_state_degrees": (179.0, 179.0, 0.0, 0.0),
        "declared_base_energy_joules": 29.4255176685,
        "declared_pair_energy_difference_joules": 2.98665125698e-6,
        "classification": "near_unstable_potential_maximum_hypothesis",
        "rationale": (
            "A rest release close to the both-links-up potential maximum samples a "
            "geometrically unstable, high-potential configuration."
        ),
    },
)


def _perturbed_state(base_state_degrees: np.ndarray) -> np.ndarray:
    state = np.asarray(base_state_degrees, dtype=float).copy()
    state[1] += fixed_pair.PERTURBATION_DEGREES
    return state


def _initial_energy(initial_state_degrees: np.ndarray) -> float:
    state_radians = np.radians(np.asarray(initial_state_degrees, dtype=float))[None, :]
    return float(fixed_pair._simple_energy(state_radians)[0])


def _finite_ratio(numerator: float, denominator: float) -> float:
    return 1e300 if denominator == 0.0 else numerator / denominator


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    base_state = np.asarray(case["base_state_degrees"], dtype=float)
    perturbed_state = _perturbed_state(base_state)
    trajectories = [
        fixed_pair._integrate_trajectory(
            f"{case['name']}:base_principal",
            base_state,
            fixed_pair.SIMPLE_DEFAULT_SOLVER_POLICY,
            fixed_pair.PRINCIPAL_MAX_ENERGY_DRIFT,
        ),
        fixed_pair._integrate_trajectory(
            f"{case['name']}:perturbed_principal",
            perturbed_state,
            fixed_pair.SIMPLE_DEFAULT_SOLVER_POLICY,
            fixed_pair.PRINCIPAL_MAX_ENERGY_DRIFT,
        ),
        fixed_pair._integrate_trajectory(
            f"{case['name']}:base_reference",
            base_state,
            fixed_pair.SIMPLE_REFERENCE_SOLVER_POLICY,
            fixed_pair.REFERENCE_MAX_ENERGY_DRIFT,
        ),
        fixed_pair._integrate_trajectory(
            f"{case['name']}:perturbed_reference",
            perturbed_state,
            fixed_pair.SIMPLE_REFERENCE_SOLVER_POLICY,
            fixed_pair.REFERENCE_MAX_ENERGY_DRIFT,
        ),
    ]

    base_energy = _initial_energy(base_state)
    perturbed_energy = _initial_energy(perturbed_state)
    pre_run = {
        "base_initial_state_degrees": base_state.tolist(),
        "perturbed_initial_state_degrees": perturbed_state.tolist(),
        "base_initial_energy_joules": base_energy,
        "perturbed_initial_energy_joules": perturbed_energy,
        "signed_pair_energy_difference_joules": perturbed_energy - base_energy,
        "base_energy_over_scale": base_energy / fixed_pair._energy_scale(),
        "base_excitation_above_hanging_minimum_over_scale": (
            base_energy + fixed_pair._energy_scale()
        )
        / fixed_pair._energy_scale(),
        "classification_hypothesis": case["classification"],
        "physical_rationale": case["rationale"],
    }

    trajectory_summaries = [fixed_pair._trajectory_summary(item) for item in trajectories]
    diagnostic_inputs_available = all(
        item["time"].shape == (fixed_pair.SAMPLE_COUNT,)
        and item["state"].shape == (fixed_pair.SAMPLE_COUNT, 4)
        and item["positions"].shape == (4, fixed_pair.SAMPLE_COUNT)
        and item["energies"].shape == (fixed_pair.SAMPLE_COUNT,)
        and np.all(np.isfinite(item["time"]))
        and np.all(np.isfinite(item["state"]))
        and np.all(np.isfinite(item["positions"]))
        and np.all(np.isfinite(item["energies"]))
        for item in trajectories
    )
    if not diagnostic_inputs_available:
        return {
            "summary": {
                "case": case["name"],
                "pre_run": pre_run,
                "numerical_status": "rejected",
                "sensitivity_status": "not_evaluable",
                "reference_credibility_issue": True,
                "numerical_checks": {
                    "all_trajectories_numerically_accepted": all(
                        item["accepted"] for item in trajectories
                    ),
                    "complete_finite_diagnostic_inputs_available": False,
                },
                "sensitivity_checks": {},
                "measurements": {},
                "trajectories": trajectory_summaries,
            },
            "series": None,
        }

    base_principal, perturbed_principal, base_reference, perturbed_reference = trajectories
    times = base_principal["time"]
    time_aligned = all(np.array_equal(times, item["time"]) for item in trajectories[1:])
    times_strictly_increasing = bool(np.all(np.diff(times) > 0.0))

    tip_principal = fixed_pair._normalized_tip_distance(
        base_principal["positions"], perturbed_principal["positions"]
    )
    tip_reference = fixed_pair._normalized_tip_distance(
        base_reference["positions"], perturbed_reference["positions"]
    )
    configuration_principal = fixed_pair._normalized_configuration_distance(
        base_principal["positions"], perturbed_principal["positions"]
    )
    configuration_reference = fixed_pair._normalized_configuration_distance(
        base_reference["positions"], perturbed_reference["positions"]
    )
    angle_principal = fixed_pair._angular_configuration_distance(
        base_principal["state"], perturbed_principal["state"]
    )
    angle_reference = fixed_pair._angular_configuration_distance(
        base_reference["state"], perturbed_reference["state"]
    )
    base_numerical_error = fixed_pair._normalized_tip_distance(
        base_principal["positions"], base_reference["positions"]
    )
    perturbed_numerical_error = fixed_pair._normalized_tip_distance(
        perturbed_principal["positions"], perturbed_reference["positions"]
    )
    numerical_envelope = np.maximum(base_numerical_error, perturbed_numerical_error)
    pair_policy_disagreement = np.abs(tip_principal - tip_reference)

    diagnostics = (
        tip_principal,
        tip_reference,
        configuration_principal,
        configuration_reference,
        angle_principal,
        angle_reference,
        base_numerical_error,
        perturbed_numerical_error,
        numerical_envelope,
        pair_policy_disagreement,
    )
    diagnostics_finite = all(np.all(np.isfinite(values)) for values in diagnostics)

    declared_delta = perturbed_state - base_state
    changed_indices = np.flatnonzero(declared_delta != 0.0)
    exactly_one_component = changed_indices.tolist() == [1] and math.isclose(
        float(declared_delta[1]),
        fixed_pair.PERTURBATION_DEGREES,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    expected_initial_separation = (
        2.0
        * float(fixed_pair.PARAMETERS[fixed_pair.l2])
        * math.sin(math.radians(fixed_pair.PERTURBATION_DEGREES) / 2.0)
        / float(fixed_pair.PARAMETERS[fixed_pair.l1] + fixed_pair.PARAMETERS[fixed_pair.l2])
    )
    initial_geometry_matches = math.isclose(
        float(tip_principal[0]),
        expected_initial_separation,
        rel_tol=0.0,
        abs_tol=fixed_pair.INITIAL_SEPARATION_ABSOLUTE_TOLERANCE,
    ) and math.isclose(
        float(tip_reference[0]),
        expected_initial_separation,
        rel_tol=0.0,
        abs_tol=fixed_pair.INITIAL_SEPARATION_ABSOLUTE_TOLERANCE,
    )
    wrapped_principal = fixed_pair._wrap_to_pi(
        base_principal["state"][:, :2] - perturbed_principal["state"][:, :2]
    )
    wrapped_reference = fixed_pair._wrap_to_pi(
        base_reference["state"][:, :2] - perturbed_reference["state"][:, :2]
    )
    periodic_differences_valid = bool(
        np.all(wrapped_principal >= -math.pi)
        and np.all(wrapped_principal < math.pi)
        and np.all(wrapped_reference >= -math.pi)
        and np.all(wrapped_reference < math.pi)
    )

    principal_crossing_index = fixed_pair._first_threshold_index(tip_principal)
    reference_crossing_index = fixed_pair._first_threshold_index(tip_reference)
    principal_crossing_time = (
        float(times[principal_crossing_index]) if principal_crossing_index is not None else None
    )
    reference_crossing_time = (
        float(times[reference_crossing_index]) if reference_crossing_index is not None else None
    )
    crossing_difference = (
        abs(principal_crossing_time - reference_crossing_time)
        if principal_crossing_time is not None and reference_crossing_time is not None
        else None
    )

    ratio_at_reference_crossing: float | None = None
    numerical_error_at_reference_crossing: float | None = None
    if reference_crossing_index is not None:
        numerical_error_at_reference_crossing = float(
            numerical_envelope[reference_crossing_index]
        )
        ratio_at_reference_crossing = _finite_ratio(
            float(tip_reference[reference_crossing_index]),
            numerical_error_at_reference_crossing,
        )

    reference_max_index = int(np.argmax(tip_reference))
    principal_max_index = int(np.argmax(tip_principal))
    ratio_at_reference_max = _finite_ratio(
        float(tip_reference[reference_max_index]),
        float(numerical_envelope[reference_max_index]),
    )
    numerical_checks = {
        "all_trajectories_numerically_accepted": all(
            item["accepted"] for item in trajectories
        ),
        "complete_finite_diagnostic_inputs_available": diagnostic_inputs_available,
        "all_trajectory_times_are_aligned": time_aligned,
        "times_are_strictly_increasing": times_strictly_increasing,
        "all_diagnostics_are_finite": diagnostics_finite,
        "exactly_one_declared_component_perturbed": exactly_one_component,
        "initial_separation_matches_geometry": initial_geometry_matches,
        "periodic_angular_differences_are_valid": periodic_differences_valid,
    }
    numerical_accepted = all(numerical_checks.values())
    sensitivity_checks = {
        "principal_pair_reaches_substantial_separation": principal_crossing_index is not None,
        "reference_pair_reaches_substantial_separation": reference_crossing_index is not None,
        "crossing_times_agree_within_limit": (
            crossing_difference is not None
            and crossing_difference <= fixed_pair.MAX_CROSSING_TIME_DIFFERENCE_SECONDS
        ),
        "physical_separation_exceeds_numerical_disagreement_ratio": (
            ratio_at_reference_crossing is not None
            and ratio_at_reference_crossing >= fixed_pair.MIN_PHYSICAL_TO_NUMERICAL_RATIO
        ),
    }
    sensitivity_accepted = numerical_accepted and all(sensitivity_checks.values())
    one_policy_only_crosses = (
        (principal_crossing_index is None) != (reference_crossing_index is None)
    )
    reference_credibility_issue = bool(
        not numerical_accepted
        or one_policy_only_crosses
        or (
            principal_crossing_index is not None
            and reference_crossing_index is not None
            and not (
                sensitivity_checks["crossing_times_agree_within_limit"]
                and sensitivity_checks[
                    "physical_separation_exceeds_numerical_disagreement_ratio"
                ]
            )
        )
    )

    measurements = {
        "initial_normalized_tip_separation": float(tip_reference[0]),
        "principal_max_normalized_tip_separation": float(tip_principal[principal_max_index]),
        "principal_max_separation_time_seconds": float(times[principal_max_index]),
        "reference_max_normalized_tip_separation": float(tip_reference[reference_max_index]),
        "reference_max_separation_time_seconds": float(times[reference_max_index]),
        "principal_first_threshold_crossing_time_seconds": principal_crossing_time,
        "reference_first_threshold_crossing_time_seconds": reference_crossing_time,
        "crossing_time_difference_seconds": crossing_difference,
        "numerical_error_at_reference_crossing": numerical_error_at_reference_crossing,
        "physical_to_numerical_ratio_at_reference_crossing": ratio_at_reference_crossing,
        "physical_to_numerical_ratio_at_reference_max": ratio_at_reference_max,
        "max_base_principal_reference_disagreement": float(np.max(base_numerical_error)),
        "max_perturbed_principal_reference_disagreement": float(
            np.max(perturbed_numerical_error)
        ),
        "max_numerical_disagreement_envelope": float(np.max(numerical_envelope)),
        "max_pair_separation_policy_disagreement": float(
            np.max(pair_policy_disagreement)
        ),
        "principal_max_normalized_configuration_separation": float(
            np.max(configuration_principal)
        ),
        "reference_max_normalized_configuration_separation": float(
            np.max(configuration_reference)
        ),
        "principal_max_periodic_angular_separation_radians": float(
            np.max(angle_principal)
        ),
        "reference_max_periodic_angular_separation_radians": float(
            np.max(angle_reference)
        ),
    }
    return {
        "summary": {
            "case": case["name"],
            "pre_run": pre_run,
            "numerical_status": "accepted" if numerical_accepted else "rejected",
            "sensitivity_status": (
                "accepted"
                if sensitivity_accepted
                else "rejected" if numerical_accepted else "not_evaluable"
            ),
            "reference_credibility_issue": reference_credibility_issue,
            "numerical_checks": numerical_checks,
            "sensitivity_checks": sensitivity_checks,
            "measurements": measurements,
            "trajectories": trajectory_summaries,
        },
        "series": {
            "time": times,
            "tip_principal": tip_principal,
            "tip_reference": tip_reference,
            "configuration_principal": configuration_principal,
            "configuration_reference": configuration_reference,
            "angle_principal": angle_principal,
            "angle_reference": angle_reference,
            "base_numerical_error": base_numerical_error,
            "perturbed_numerical_error": perturbed_numerical_error,
            "numerical_envelope": numerical_envelope,
            "pair_policy_disagreement": pair_policy_disagreement,
        },
    }


def run_comparison() -> dict[str, Any]:
    case_runs = [_run_case(case) for case in CASES]
    case_summaries = [case_run["summary"] for case_run in case_runs]
    any_numerical_rejection = any(
        case["numerical_status"] != "accepted" for case in case_summaries
    )
    any_reference_credibility_issue = any(
        case["reference_credibility_issue"] for case in case_summaries
    )
    sensitive_cases = [
        case["case"] for case in case_summaries if case["sensitivity_status"] == "accepted"
    ]

    if any_numerical_rejection or any_reference_credibility_issue:
        outcome = "C"
        interpretation = (
            "Numerical credibility is problematic in at least one predeclared regime; "
            "the numerical or tighter-reference policy requires investigation before "
            "a pedagogical sensitivity conclusion."
        )
    elif sensitive_cases:
        outcome = "A"
        interpretation = (
            "At least one predeclared, physically motivated case reaches substantial "
            "separation inside 20 seconds and satisfies the tighter-reference policy."
        )
    else:
        outcome = "B"
        interpretation = (
            "The selected regimes may differ descriptively, but none satisfies the "
            "substantial-separation acceptance policy inside 20 seconds."
        )

    summary = {
        "experiment": COMPARISON_NAME,
        "question": QUESTION,
        "predeclared_case_count": len(CASES),
        "additional_case_count": len(CASES) - 1,
        "case_order": [case["name"] for case in CASES],
        "configuration": {
            "model": fixed_pair.MODEL,
            "formulation": fixed_pair.FORMULATION,
            "parameters_si": fixed_pair._parameter_dict(),
            "perturbed_component": fixed_pair.PERTURBED_COMPONENT,
            "perturbation_degrees": fixed_pair.PERTURBATION_DEGREES,
            "equal_initial_energy_required": False,
            "t_start_seconds": fixed_pair.T_START,
            "t_stop_seconds": fixed_pair.T_STOP,
            "sample_count": fixed_pair.SAMPLE_COUNT,
            "sample_interval_seconds": (
                (fixed_pair.T_STOP - fixed_pair.T_START) / (fixed_pair.SAMPLE_COUNT - 1)
            ),
            "principal_policy": fixed_pair._policy_dict(
                fixed_pair.SIMPLE_DEFAULT_SOLVER_POLICY
            ),
            "reference_policy": fixed_pair._policy_dict(
                fixed_pair.SIMPLE_REFERENCE_SOLVER_POLICY
            ),
        },
        "acceptance_policy": {
            "substantial_normalized_tip_separation": fixed_pair.SUBSTANTIAL_SEPARATION,
            "maximum_crossing_time_difference_seconds": (
                fixed_pair.MAX_CROSSING_TIME_DIFFERENCE_SECONDS
            ),
            "minimum_physical_to_numerical_ratio": (
                fixed_pair.MIN_PHYSICAL_TO_NUMERICAL_RATIO
            ),
            "principal_max_normalized_energy_drift": (
                fixed_pair.PRINCIPAL_MAX_ENERGY_DRIFT
            ),
            "reference_max_normalized_energy_drift": (
                fixed_pair.REFERENCE_MAX_ENERGY_DRIFT
            ),
            "energy_scale_joules": fixed_pair._energy_scale(),
        },
        "all_cases_numerically_accepted": not any_numerical_rejection,
        "all_cases_reference_credible_for_threshold_claim": (
            not any_reference_credibility_issue
        ),
        "sensitive_cases": sensitive_cases,
        "outcome": outcome,
        "interpretation": interpretation,
        "cases": case_summaries,
        "claim_boundary": (
            "For each named accepted pair, the result describes finite-time physical "
            "separation under the declared 20-second policies. It does not establish "
            "mathematical chaos, exponential divergence, Lyapunov behaviour, global "
            "state-space properties, or solver-independent long-time dynamics."
        ),
    }
    return {"summary": summary, "case_runs": case_runs}


SUMMARY_FIELDS = (
    "case",
    "classification_hypothesis",
    "base_initial_state_degrees",
    "perturbed_initial_state_degrees",
    "base_initial_energy_joules",
    "base_energy_over_scale",
    "base_excitation_above_hanging_minimum_over_scale",
    "signed_pair_energy_difference_joules",
    "initial_normalized_tip_separation",
    "principal_max_normalized_tip_separation",
    "reference_max_normalized_tip_separation",
    "reference_max_separation_time_seconds",
    "principal_first_threshold_crossing_time_seconds",
    "reference_first_threshold_crossing_time_seconds",
    "max_numerical_disagreement_envelope",
    "max_pair_separation_policy_disagreement",
    "physical_to_numerical_ratio_at_reference_crossing",
    "numerical_status",
    "sensitivity_status",
)


def _write_summary_csv(path: Path, case_runs: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for case_run in case_runs:
            summary = case_run["summary"]
            pre_run = summary["pre_run"]
            measurements = summary["measurements"]
            measurement_fields = {
                name: measurements.get(name)
                for name in SUMMARY_FIELDS
                if name in measurements
            }
            writer.writerow(
                {
                    "case": summary["case"],
                    "classification_hypothesis": pre_run["classification_hypothesis"],
                    "base_initial_state_degrees": json.dumps(
                        pre_run["base_initial_state_degrees"]
                    ),
                    "perturbed_initial_state_degrees": json.dumps(
                        pre_run["perturbed_initial_state_degrees"]
                    ),
                    "base_initial_energy_joules": pre_run["base_initial_energy_joules"],
                    "base_energy_over_scale": pre_run["base_energy_over_scale"],
                    "base_excitation_above_hanging_minimum_over_scale": pre_run[
                        "base_excitation_above_hanging_minimum_over_scale"
                    ],
                    "signed_pair_energy_difference_joules": pre_run[
                        "signed_pair_energy_difference_joules"
                    ],
                    **measurement_fields,
                    "numerical_status": summary["numerical_status"],
                    "sensitivity_status": summary["sensitivity_status"],
                }
            )


def _write_timeseries_csv(path: Path, case_runs: list[dict[str, Any]]) -> None:
    diagnostic_names = (
        "tip_principal",
        "tip_reference",
        "configuration_principal",
        "configuration_reference",
        "angle_principal",
        "angle_reference",
        "base_numerical_error",
        "perturbed_numerical_error",
        "numerical_envelope",
        "pair_policy_disagreement",
    )
    fieldnames = ["time_s"]
    for case_run in case_runs:
        for diagnostic in diagnostic_names:
            fieldnames.append(f"{case_run['summary']['case']}__{diagnostic}")

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        accepted_series = [run["series"] for run in case_runs if run["series"] is not None]
        if not accepted_series:
            return
        time = accepted_series[0]["time"]
        for index, time_value in enumerate(time):
            row: dict[str, Any] = {"time_s": float(time_value)}
            for case_run in case_runs:
                series = case_run["series"]
                if series is None:
                    continue
                for diagnostic in diagnostic_names:
                    row[f"{case_run['summary']['case']}__{diagnostic}"] = float(
                        series[diagnostic][index]
                    )
            writer.writerow(row)


def _write_plot(path: Path, comparison: dict[str, Any]) -> None:
    all_case_runs = comparison["case_runs"]
    case_runs = [run for run in all_case_runs if run["series"] is not None]
    if not case_runs:
        return
    plt = fixed_pair._load_pyplot()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = plt.get_cmap("tab10").colors
    floor = 1e-12

    for index, case_run in enumerate(case_runs):
        color = colors[index % len(colors)]
        series = case_run["series"]
        name = case_run["summary"]["case"]
        if case_run["summary"]["numerical_status"] != "accepted":
            name = f"{name} [rejected]"
        axes[0, 0].semilogy(
            series["time"],
            np.maximum(series["tip_reference"], floor),
            color=color,
            label=name,
        )
    axes[0, 0].axhline(
        fixed_pair.SUBSTANTIAL_SEPARATION,
        color="black",
        linestyle=":",
        label="substantial threshold",
    )
    axes[0, 0].set_title("Reference-policy physical separation")
    axes[0, 0].set_xlabel("time / s")
    axes[0, 0].set_ylabel("normalized second-bob separation")
    axes[0, 0].legend(fontsize=7)

    names = [
        run["summary"]["case"]
        + (" [rejected]" if run["summary"]["numerical_status"] != "accepted" else "")
        for run in case_runs
    ]
    reference_maxima = [
        run["summary"]["measurements"]["reference_max_normalized_tip_separation"]
        for run in case_runs
    ]
    principal_maxima = [
        run["summary"]["measurements"]["principal_max_normalized_tip_separation"]
        for run in case_runs
    ]
    positions = np.arange(len(case_runs))
    axes[0, 1].barh(positions, reference_maxima, color=colors[: len(case_runs)], alpha=0.75)
    axes[0, 1].scatter(principal_maxima, positions, color="black", marker="|", label="principal")
    axes[0, 1].axvline(fixed_pair.SUBSTANTIAL_SEPARATION, color="black", linestyle=":")
    axes[0, 1].set_yticks(positions, labels=names, fontsize=8)
    axes[0, 1].set_xscale("log")
    axes[0, 1].set_title("Maximum separation: reference bars, principal marks")
    axes[0, 1].set_xlabel("maximum normalized second-bob separation")
    axes[0, 1].legend(fontsize=8)

    control = case_runs[0]
    most_separated = max(
        case_runs,
        key=lambda run: run["summary"]["measurements"][
            "reference_max_normalized_tip_separation"
        ],
    )
    representatives = [control]
    if most_separated["summary"]["case"] != control["summary"]["case"]:
        representatives.append(most_separated)
    for index, case_run in enumerate(representatives):
        color = colors[index]
        series = case_run["series"]
        name = case_run["summary"]["case"]
        if case_run["summary"]["numerical_status"] != "accepted":
            name = f"{name} [rejected]"
        axes[1, 0].semilogy(
            series["time"],
            np.maximum(series["tip_reference"], floor),
            color=color,
            label=f"{name}: physical",
        )
        axes[1, 0].semilogy(
            series["time"],
            np.maximum(series["numerical_envelope"], floor),
            color=color,
            linestyle="--",
            label=f"{name}: numerical",
        )
    axes[1, 0].axhline(fixed_pair.SUBSTANTIAL_SEPARATION, color="black", linestyle=":")
    axes[1, 0].set_title("Representative physical effect versus policy disagreement")
    axes[1, 0].set_xlabel("time / s")
    axes[1, 0].set_ylabel("normalized second-bob distance")
    axes[1, 0].legend(fontsize=7)

    principal_drifts = []
    reference_drifts = []
    for case_run in case_runs:
        trajectories = case_run["summary"]["trajectories"]
        principal_drifts.append(max(item["max_energy_drift"] for item in trajectories[:2]))
        reference_drifts.append(max(item["max_energy_drift"] for item in trajectories[2:]))
    width = 0.36
    axes[1, 1].bar(
        positions - width / 2,
        principal_drifts,
        width,
        label="principal max of pair",
    )
    axes[1, 1].bar(
        positions + width / 2,
        reference_drifts,
        width,
        label="reference max of pair",
    )
    axes[1, 1].axhline(fixed_pair.PRINCIPAL_MAX_ENERGY_DRIFT, color="black", linestyle=":")
    axes[1, 1].axhline(fixed_pair.REFERENCE_MAX_ENERGY_DRIFT, color="gray", linestyle=":")
    axes[1, 1].set_yscale("log")
    axes[1, 1].set_xticks(positions, labels=names, rotation=30, ha="right", fontsize=7)
    axes[1, 1].set_title("Independent energy-drift acceptance")
    axes[1, 1].set_ylabel("maximum |E(t)-E(0)| / E_scale")
    axes[1, 1].legend(fontsize=8)

    for axis in axes.flat:
        axis.grid(True, alpha=0.25)
    fig.suptitle(
        "Stage 1 predeclared regime comparison — "
        f"Outcome {comparison['summary']['outcome']}"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def write_output_bundle(
    comparison: dict[str, Any], output_dir: Path, include_plots: bool
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "regime_summary.json"
    fixed_pair._json_write(summary_path, comparison["summary"])
    summary_csv_path = output_dir / "regime_comparison.csv"
    _write_summary_csv(summary_csv_path, comparison["case_runs"])
    timeseries_path = output_dir / "regime_separation_timeseries.csv"
    _write_timeseries_csv(timeseries_path, comparison["case_runs"])
    created = [summary_path, summary_csv_path, timeseries_path]

    if include_plots:
        plot_path = output_dir / "regime_comparison_diagnostics.png"
        _write_plot(plot_path, comparison)
        created.append(plot_path)

    manifest_path = output_dir / "regime_manifest.json"
    manifest = {
        "artifact": "initial_condition_sensitivity_regime_selection",
        "experiment": COMPARISON_NAME,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "outcome": comparison["summary"]["outcome"],
        "created_files": [manifest_path.name, *[path.name for path in created]],
        "reproduction_command": (
            "uv run python development/chaos_content/experiments/"
            "002_initial_condition_sensitivity/regime_selection_comparison.py "
            "--output-dir development/chaos_content/outputs/"
            "initial_condition_sensitivity/regime_selection --plots"
        ),
        "contract": (
            "development/chaos_content/experiments/"
            "002_initial_condition_sensitivity/README.md"
        ),
        "case_order": comparison["summary"]["case_order"],
        "claim_boundary": comparison["summary"]["claim_boundary"],
    }
    fixed_pair._json_write(manifest_path, manifest)
    return [manifest_path, *created]


def _assert_self_check(comparison: dict[str, Any]) -> None:
    summary = comparison["summary"]
    expected_names = [case["name"] for case in CASES]
    if summary["case_order"] != expected_names or len(expected_names) != 6:
        raise AssertionError("The predeclared case set or order changed.")
    if expected_names[0] != fixed_pair.EXPERIMENT_NAME:
        raise AssertionError("The fixed regular-control case is not preserved first.")
    if summary["additional_case_count"] != 5:
        raise AssertionError("Expected exactly five predeclared additional cases.")

    for declared, case_run in zip(CASES, comparison["case_runs"], strict=True):
        case_summary = case_run["summary"]
        pre_run = case_summary["pre_run"]
        base = np.asarray(pre_run["base_initial_state_degrees"], dtype=float)
        perturbed = np.asarray(pre_run["perturbed_initial_state_degrees"], dtype=float)
        changed = np.flatnonzero(perturbed - base)
        if changed.tolist() != [1] or not math.isclose(
            float(perturbed[1] - base[1]),
            fixed_pair.PERTURBATION_DEGREES,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise AssertionError(f"Perturbation contract changed for {declared['name']}.")
        if not math.isclose(
            pre_run["base_initial_energy_joules"],
            declared["declared_base_energy_joules"],
            rel_tol=0.0,
            abs_tol=5e-11,
        ):
            raise AssertionError(f"Predeclared base energy changed for {declared['name']}.")
        if not math.isclose(
            pre_run["signed_pair_energy_difference_joules"],
            declared["declared_pair_energy_difference_joules"],
            rel_tol=0.0,
            abs_tol=5e-11,
        ):
            raise AssertionError(f"Predeclared pair energy changed for {declared['name']}.")
        if case_summary["numerical_status"] == "accepted":
            if case_run["series"] is None:
                raise AssertionError(f"Accepted case has no series: {declared['name']}.")
            if len(case_run["series"]["time"]) != fixed_pair.SAMPLE_COUNT:
                raise AssertionError(f"Unexpected sample count for {declared['name']}.")
            if not all(case_summary["numerical_checks"].values()):
                raise AssertionError(f"Numerical checks disagree for {declared['name']}.")

    expected_outcomes = {"A", "B", "C"}
    if summary["outcome"] not in expected_outcomes:
        raise AssertionError(f"Unexpected completed-comparison outcome: {summary['outcome']}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="run all predeclared cases and assert deterministic structural checks",
    )
    parser.add_argument("--output-dir", type=Path, help="ignored sandbox output directory")
    parser.add_argument("--plots", action="store_true", help="write comparative diagnostics")
    args = parser.parse_args()
    if args.plots and args.output_dir is None:
        parser.error("--plots requires --output-dir")

    comparison = run_comparison()
    if args.self_check:
        _assert_self_check(comparison)
    if args.output_dir is not None:
        write_output_bundle(comparison, args.output_dir, include_plots=args.plots)
    console_summary = {
        "experiment": COMPARISON_NAME,
        "outcome": comparison["summary"]["outcome"],
        "interpretation": comparison["summary"]["interpretation"],
        "cases": [
            {
                "case": case["case"],
                "numerical_status": case["numerical_status"],
                "sensitivity_status": case["sensitivity_status"],
                "reference_max_normalized_tip_separation": case["measurements"].get(
                    "reference_max_normalized_tip_separation"
                ),
                "reference_first_threshold_crossing_time_seconds": case[
                    "measurements"
                ].get("reference_first_threshold_crossing_time_seconds"),
            }
            for case in comparison["summary"]["cases"]
        ],
    }
    print(json.dumps(console_summary, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
