"""Test trusted-policy convergence of long-horizon first-flip log classes.

The physical primitive remains the first completed net revolution of either
lifted absolute link angle.  This investigation compares classifications
derived from independent solve_ivp runs; it does not alter production dispatch,
native eligibility, dynamics, event surfaces, or numerical gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import os
import platform
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..first_flip_horizon.first_flip_horizon_and_energy_accessibility import (
    ENERGY_DRIFT_LIMIT,
    EVENT_SURFACE_RESIDUAL_LIMIT,
    EVENT_TIME_CONVERGENCE_SECONDS,
    MAXIMUM_ACCEPTED_ANGULAR_INCREMENT,
    either_flip_energy_barrier,
    zero_velocity_energy,
)
from ...src.first_flip.compiled import first_flip_compiled_eligibility
from ...src.first_flip.reference import (
    EventAttribution,
    FirstFlipStatus,
    default_solver_spec,
    first_flip_time,
    gravity_timescale,
)
from ...src.lyapunov.reference import (
    EulerLagrangeState,
    PendulumParameters,
    SolverSpec,
)


HERE = Path(__file__).resolve().parent
DEFAULT_CASES = HERE / "selected_cases.json"
DEFAULT_EVIDENCE = HERE / "evidence" / "first_flip_log_class_convergence.json"
DEFAULT_RENDER = HERE / "evidence" / "first_flip_log_class_convergence.png"
HORIZON_HAT = 10_000.0
POLICY_ORDER = ("baseline", "strict", "strict_half_step")
CLASS_ORDER = (
    "tau_hat_lt_1",
    "tau_hat_1_to_10",
    "tau_hat_10_to_100",
    "tau_hat_100_to_1000",
    "tau_hat_1000_to_10000",
    "no_flip_observed_by_10000",
    "energy_inaccessible",
    "numerically_invalid",
)
CLASS_BOUNDARIES = (1.0, 10.0, 100.0, 1000.0, 10_000.0)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trusted_policies(
    parameters: PendulumParameters = PendulumParameters(),
) -> dict[str, SolverSpec]:
    """Return the three predeclared trusted DOP853 refinement policies."""

    baseline = default_solver_spec(parameters)
    assert baseline.max_step is not None
    return {
        "baseline": baseline,
        "strict": SolverSpec(
            method="DOP853",
            rtol=1.0e-11,
            atol=1.0e-13,
            max_step=baseline.max_step,
        ),
        "strict_half_step": SolverSpec(
            method="DOP853",
            rtol=1.0e-11,
            atol=1.0e-13,
            max_step=baseline.max_step / 2.0,
        ),
    }


def logarithmic_class(
    dimensionless_event_time: float | None,
    *,
    censored: bool,
    energy_inaccessible: bool,
    numerically_valid: bool = True,
) -> str:
    """Classify one trusted outcome without replacing its primitive event time."""

    if not numerically_valid:
        return "numerically_invalid"
    if energy_inaccessible:
        return "energy_inaccessible"
    if censored:
        return "no_flip_observed_by_10000"
    if dimensionless_event_time is None or not math.isfinite(dimensionless_event_time):
        return "numerically_invalid"
    if dimensionless_event_time < 1.0:
        return "tau_hat_lt_1"
    if dimensionless_event_time < 10.0:
        return "tau_hat_1_to_10"
    if dimensionless_event_time < 100.0:
        return "tau_hat_10_to_100"
    if dimensionless_event_time < 1000.0:
        return "tau_hat_100_to_1000"
    if dimensionless_event_time < 10_000.0:
        return "tau_hat_1000_to_10000"
    return "no_flip_observed_by_10000"


def _event_residual(result) -> float | None:
    if not result.event_identities:
        return None
    return max(
        abs(item.residual)
        for item in result.event_surface_residuals
        if item.identity in result.event_identities
    )


def _evaluate_task(task: tuple[dict[str, object], str, SolverSpec, float]) -> dict[str, object]:
    case, policy_name, solver, horizon_seconds = task
    parameters = PendulumParameters()
    state = EulerLagrangeState(
        float(case["theta1_radians"]),
        float(case["theta2_radians"]),
        0.0,
        0.0,
    )
    started = perf_counter()
    result = first_flip_time(
        state,
        parameters=parameters,
        solver_spec=solver,
        observation_horizon=horizon_seconds,
    )
    outer_wall = perf_counter() - started
    inaccessible = bool(case["energy_inaccessible"])
    residual = _event_residual(result)
    issues = list(result.validation_issues)
    if result.maximum_normalized_energy_drift > ENERGY_DRIFT_LIMIT:
        issues.append("energy_drift_limit_exceeded")
    if result.maximum_accepted_angular_increment >= MAXIMUM_ACCEPTED_ANGULAR_INCREMENT:
        issues.append("accepted_angular_increment_limit_exceeded")
    if result.status is FirstFlipStatus.EVENT_OBSERVED:
        if result.attribution is not EventAttribution.UNIQUE:
            issues.append("unsupported_nonunique_event_attribution")
        if residual is None or residual > EVENT_SURFACE_RESIDUAL_LIMIT:
            issues.append("event_surface_residual_limit_exceeded")
        if any(value == 0.0 for value in result.triggering_angular_velocities):
            issues.append("nontransversal_event")
        if result.dimensionless_event_time is None or not (
            result.dimensionless_event_time < HORIZON_HAT
        ):
            issues.append("event_not_strictly_before_cap")
    if inaccessible and result.status is FirstFlipStatus.EVENT_OBSERVED:
        issues.append("event_in_rigorous_energy_inaccessible_region")
    numerically_valid = (
        result.status in (FirstFlipStatus.EVENT_OBSERVED, FirstFlipStatus.RIGHT_CENSORED)
        and not issues
    )
    event_identity = (
        result.event_identities[0].label
        if len(result.event_identities) == 1
        else None
    )
    return {
        "case": str(case["name"]),
        "policy": policy_name,
        "status": result.status.value,
        "event_observed": result.status is FirstFlipStatus.EVENT_OBSERVED,
        "censored": result.status is FirstFlipStatus.RIGHT_CENSORED,
        "event_time_seconds": result.event_time_seconds,
        "dimensionless_event_time": result.dimensionless_event_time,
        "logarithmic_class": logarithmic_class(
            result.dimensionless_event_time,
            censored=result.status is FirstFlipStatus.RIGHT_CENSORED,
            energy_inaccessible=inaccessible,
            numerically_valid=numerically_valid,
        ),
        "event_identity": event_identity,
        "first_flipping_arm": result.winning_arm,
        "event_direction": result.winning_direction,
        "event_surface_residual": residual,
        "triggering_angular_velocity": (
            result.triggering_angular_velocities[0]
            if len(result.triggering_angular_velocities) == 1
            else None
        ),
        "minimum_competing_surface_margin": result.minimum_competing_surface_margin,
        "maximum_normalized_energy_drift": result.maximum_normalized_energy_drift,
        "maximum_absolute_energy_error_joules": result.maximum_absolute_energy_error_joules,
        "maximum_accepted_angular_increment": result.maximum_accepted_angular_increment,
        "integration_endpoint_seconds": result.integration_endpoint_seconds,
        "rhs_evaluations": result.rhs_evaluations,
        "accepted_point_count": result.accepted_point_count,
        "solver_success": result.solver_success,
        "solver_message": result.solver_message,
        "solver_method": result.solver_method,
        "solver_rtol": result.solver_rtol,
        "solver_atol": result.solver_atol,
        "effective_max_step_seconds": result.effective_max_step_seconds,
        "evaluation_wall_seconds": result.wall_seconds,
        "worker_outer_wall_seconds": outer_wall,
        "numerically_valid": numerically_valid,
        "validity_issues": sorted(set(issues)),
    }


def _class_at_horizon(
    record: Mapping[str, object],
    horizon_hat: float,
    inaccessible: bool,
) -> str:
    if not bool(record["numerically_valid"]):
        return "numerically_invalid"
    if inaccessible:
        return "energy_inaccessible"
    time_hat = record["dimensionless_event_time"]
    if time_hat is None or not float(time_hat) < horizon_hat:
        return f"no_flip_observed_by_{horizon_hat:g}"
    return logarithmic_class(
        float(time_hat),
        censored=False,
        energy_inaccessible=False,
    )


def _earliest_class_disagreement(classes: Sequence[str]) -> str | None:
    if len(set(classes)) <= 1:
        return None
    event_ranks = [CLASS_ORDER.index(value) for value in classes if value in CLASS_ORDER[:5]]
    if len(event_ranks) != len(classes):
        return "H=10000 outcome boundary or invalid result"
    boundary_index = min(event_ranks)
    return f"H={CLASS_BOUNDARIES[boundary_index]:g} logarithmic boundary"


def analyze_case(
    case: Mapping[str, object],
    records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    ordered = sorted(records, key=lambda item: POLICY_ORDER.index(str(item["policy"])))
    valid = all(bool(item["numerically_valid"]) for item in ordered)
    outcomes = [bool(item["event_observed"]) for item in ordered]
    classes = [str(item["logarithmic_class"]) for item in ordered]
    all_observed = valid and all(outcomes)
    horizon_stable = valid and len(set(outcomes)) == 1
    decade_stable = valid and len(set(classes)) == 1
    times = [float(item["event_time_seconds"]) for item in ordered if item["event_time_seconds"] is not None]
    time_range = max(times) - min(times) if len(times) == len(ordered) else None
    exact_stable = bool(
        all_observed
        and decade_stable
        and time_range is not None
        and time_range <= EVENT_TIME_CONVERGENCE_SECONDS
    )
    arms = [item["first_flipping_arm"] for item in ordered]
    directions = [item["event_direction"] for item in ordered]
    arm_stable = all_observed and len(set(arms)) == 1
    sign_stable = all_observed and len(set(directions)) == 1
    levels: list[str] = []
    if horizon_stable:
        levels.append("HORIZON_OUTCOME_STABLE")
    if decade_stable:
        levels.append("DECADE_STABLE")
    if exact_stable:
        levels.append("EXACT_TIME_STABLE")
    unresolved = not decade_stable
    if unresolved:
        levels.append("NUMERICALLY_UNRESOLVED")
    strongest = (
        "EXACT_TIME_STABLE"
        if exact_stable
        else "DECADE_STABLE"
        if decade_stable
        else "HORIZON_OUTCOME_STABLE"
        if horizon_stable
        else "NUMERICALLY_UNRESOLVED"
    )
    horizon_views = {}
    for horizon_hat in (1000.0, 10_000.0):
        horizon_classes = [
            _class_at_horizon(item, horizon_hat, bool(case["energy_inaccessible"]))
            for item in ordered
        ]
        horizon_outcomes = [
            bool(
                item["dimensionless_event_time"] is not None
                and float(item["dimensionless_event_time"]) < horizon_hat
            )
            for item in ordered
        ]
        horizon_views[f"H{horizon_hat:g}"] = {
            "classes": horizon_classes,
            "logarithmic_class_stable": valid and len(set(horizon_classes)) == 1,
            "flip_no_flip_stable": valid and len(set(horizon_outcomes)) == 1,
        }
    return {
        "name": case["name"],
        "group": case["group"],
        "energy_inaccessible": case["energy_inaccessible"],
        "policy_classes": {
            str(item["policy"]): item["logarithmic_class"] for item in ordered
        },
        "policy_event_times_hat": {
            str(item["policy"]): item["dimensionless_event_time"] for item in ordered
        },
        "policy_event_identities": {
            str(item["policy"]): item["event_identity"] for item in ordered
        },
        "all_policies_numerically_valid": valid,
        "exact_time_applicable": all_observed,
        "exact_time_range_seconds": time_range,
        "exact_time_stable": exact_stable,
        "decade_stable": decade_stable,
        "horizon_outcome_stable": horizon_stable,
        "arm_agreement": arm_stable if all_observed else None,
        "signed_surface_agreement": sign_stable if all_observed else None,
        "numerically_unresolved_for_log_representation": unresolved,
        "earliest_disagreement": _earliest_class_disagreement(classes),
        "levels_satisfied": levels,
        "strongest_state": strongest,
        "horizon_views": horizon_views,
    }


def _aggregate(
    cases: Sequence[Mapping[str, object]],
    analyses: Sequence[Mapping[str, object]],
    records: Sequence[Mapping[str, object]],
    outer_wall_seconds: float,
) -> dict[str, object]:
    case_count = len(cases)
    exact_applicable = [item for item in analyses if item["exact_time_applicable"]]
    all_observed = [
        item
        for item in analyses
        if all(value is not None for value in item["policy_event_times_hat"].values())
    ]
    arm_applicable = [item for item in analyses if item["arm_agreement"] is not None]
    by_policy = {}
    for policy in POLICY_ORDER:
        selected = [item for item in records if item["policy"] == policy]
        by_policy[policy] = {
            "case_count": len(selected),
            "event_count": sum(bool(item["event_observed"]) for item in selected),
            "censored_count": sum(bool(item["censored"]) for item in selected),
            "numerically_invalid_count": sum(
                not bool(item["numerically_valid"]) for item in selected
            ),
            "summed_evaluation_wall_seconds": sum(
                float(item["evaluation_wall_seconds"]) for item in selected
            ),
            "summed_rhs_evaluations": sum(int(item["rhs_evaluations"]) for item in selected),
            "maximum_energy_drift": max(
                float(item["maximum_normalized_energy_drift"]) for item in selected
            ),
            "maximum_event_residual": max(
                (
                    float(item["event_surface_residual"])
                    for item in selected
                    if item["event_surface_residual"] is not None
                ),
                default=0.0,
            ),
            "maximum_accepted_angular_increment": max(
                float(item["maximum_accepted_angular_increment"]) for item in selected
            ),
        }
    horizon_summaries = {}
    for label in ("H1000", "H10000"):
        class_stable = [
            item for item in analyses if item["horizon_views"][label]["logarithmic_class_stable"]
        ]
        outcome_stable = [
            item for item in analyses if item["horizon_views"][label]["flip_no_flip_stable"]
        ]
        horizon_summaries[label] = {
            "logarithmic_class_stable_count": len(class_stable),
            "logarithmic_class_stable_fraction": len(class_stable) / case_count,
            "flip_no_flip_stable_count": len(outcome_stable),
            "flip_no_flip_stable_fraction": len(outcome_stable) / case_count,
            "unresolved_cases": [
                item["name"]
                for item in analyses
                if not item["horizon_views"][label]["logarithmic_class_stable"]
            ],
        }
    return {
        "case_count": case_count,
        "all_policy_results_numerically_valid_count": sum(
            bool(item["all_policies_numerically_valid"]) for item in analyses
        ),
        "exact_time_stable_count": sum(bool(item["exact_time_stable"]) for item in analyses),
        "exact_time_stable_fraction_of_all_cases": sum(
            bool(item["exact_time_stable"]) for item in analyses
        )
        / case_count,
        "exact_time_stable_fraction_of_applicable_observed_cases": (
            sum(bool(item["exact_time_stable"]) for item in exact_applicable)
            / len(exact_applicable)
            if exact_applicable
            else 0.0
        ),
        "exact_time_applicable_observed_case_count": len(exact_applicable),
        "all_policies_observed_case_count": len(all_observed),
        "decade_stable_count": sum(bool(item["decade_stable"]) for item in analyses),
        "decade_stable_fraction": sum(bool(item["decade_stable"]) for item in analyses)
        / case_count,
        "horizon_outcome_stable_count": sum(
            bool(item["horizon_outcome_stable"]) for item in analyses
        ),
        "horizon_outcome_stable_fraction": sum(
            bool(item["horizon_outcome_stable"]) for item in analyses
        )
        / case_count,
        "arm_agreement_count": sum(item["arm_agreement"] is True for item in arm_applicable),
        "arm_agreement_fraction_of_applicable": (
            sum(item["arm_agreement"] is True for item in arm_applicable)
            / len(arm_applicable)
            if arm_applicable
            else 0.0
        ),
        "signed_surface_agreement_count": sum(
            item["signed_surface_agreement"] is True for item in arm_applicable
        ),
        "signed_surface_agreement_fraction_of_applicable": (
            sum(item["signed_surface_agreement"] is True for item in arm_applicable)
            / len(arm_applicable)
            if arm_applicable
            else 0.0
        ),
        "numerically_unresolved_count": sum(
            bool(item["numerically_unresolved_for_log_representation"])
            for item in analyses
        ),
        "numerically_unresolved_cases": [
            item["name"]
            for item in analyses
            if item["numerically_unresolved_for_log_representation"]
        ],
        "earliest_disagreement": next(
            (
                item["earliest_disagreement"]
                for item in analyses
                if item["earliest_disagreement"] is not None
            ),
            None,
        ),
        "horizon_summaries": horizon_summaries,
        "policy_summaries": by_policy,
        "outer_wall_seconds": outer_wall_seconds,
    }


def _render(
    path: Path,
    cases: Sequence[Mapping[str, object]],
    records: Sequence[Mapping[str, object]],
    analyses: Sequence[Mapping[str, object]],
) -> None:
    lookup = {(str(item["case"]), str(item["policy"])): item for item in records}
    values = np.empty((len(cases), len(POLICY_ORDER)), dtype=int)
    for row, case in enumerate(cases):
        for column, policy in enumerate(POLICY_ORDER):
            values[row, column] = CLASS_ORDER.index(
                str(lookup[(str(case["name"]), policy)]["logarithmic_class"])
            )
    colours = (
        "#f7fbff",
        "#fdd49e",
        "#fc8d59",
        "#ef6548",
        "#b30000",
        "#bdbdbd",
        "#25324b",
        "#7b3294",
    )
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    figure_height = max(8.0, 0.34 * len(cases) + 2.4)
    figure, axis = plt.subplots(figsize=(10.5, figure_height), constrained_layout=True)
    axis.imshow(
        values,
        cmap=ListedColormap(colours),
        vmin=-0.5,
        vmax=len(CLASS_ORDER) - 0.5,
        interpolation="nearest",
        aspect="auto",
    )
    axis.set_xticks(range(len(POLICY_ORDER)), POLICY_ORDER)
    labels = []
    for case, analysis in zip(cases, analyses, strict=True):
        marker = "  ⚠" if analysis["numerically_unresolved_for_log_representation"] else ""
        labels.append(f"{case['name']}{marker}")
    axis.set_yticks(range(len(cases)), labels, fontsize=8)
    axis.set_title("Trusted-policy first-flip logarithmic classes at $\\widehat H=10^4$")
    axis.set_xlabel("independent solve_ivp policy")
    axis.set_ylabel("deterministically selected initial condition")
    legend_labels = (
        r"$\widehat\tau<1$",
        r"$1\leq\widehat\tau<10$",
        r"$10\leq\widehat\tau<100$",
        r"$100\leq\widehat\tau<1000$",
        r"$1000\leq\widehat\tau<10000$",
        r"no flip by $10^4$",
        "energy-inaccessible",
        "numerically invalid",
    )
    axis.legend(
        handles=[Patch(color=colour, label=label) for colour, label in zip(colours, legend_labels, strict=True)],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.06),
        ncol=3,
        fontsize=8,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _load_cases(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    definition = json.loads(path.read_text(encoding="utf-8"))
    source = (path.parent / definition["source"]["artifact"]).resolve()
    if _sha256(source) != definition["source"]["sha256"]:
        raise ValueError("selected-case source artifact checksum changed")
    parameters = PendulumParameters()
    barrier = either_flip_energy_barrier(parameters)
    cases = []
    names: set[str] = set()
    for raw in definition["cases"]:
        case = dict(raw)
        if case["name"] in names:
            raise ValueError("selected case names must be unique")
        names.add(str(case["name"]))
        energy = float(
            zero_velocity_energy(
                float(case["theta1_radians"]),
                float(case["theta2_radians"]),
                parameters,
            )
        )
        case["initial_energy_joules"] = energy
        case["energy_barrier_joules"] = barrier
        case["energy_inaccessible"] = energy < barrier
        cases.append(case)
    if not 10 <= len(cases) <= 64:
        raise ValueError("bounded case set must contain between 10 and 64 cases")
    return definition, cases


def run_investigation(
    case_path: Path = DEFAULT_CASES,
    evidence_path: Path = DEFAULT_EVIDENCE,
    render_path: Path = DEFAULT_RENDER,
    workers: int = 4,
) -> dict[str, object]:
    if workers <= 0 or workers > 4:
        raise ValueError("this bounded investigation accepts one to four workers")
    definition, cases = _load_cases(case_path)
    parameters = PendulumParameters()
    time_scale = gravity_timescale(parameters)
    horizon_seconds = HORIZON_HAT * time_scale
    policies = trusted_policies(parameters)
    for solver in policies.values():
        if not first_flip_compiled_eligibility(
            parameters, solver, horizon_seconds
        ).eligible:
            continue
        raise RuntimeError("production eligibility unexpectedly accepted this experiment")

    cost_priority = {
        "energy_inaccessible_control": 0,
        "long_lived_region": 1,
        "energy_boundary": 2,
        "known_disagreement": 3,
        "decade_boundary": 4,
        "decade_interior": 5,
        "early_control": 6,
    }
    policy_priority = {"strict_half_step": 0, "strict": 1, "baseline": 2}
    tasks = [
        (case, policy, policies[policy], horizon_seconds)
        for case in cases
        for policy in POLICY_ORDER
    ]
    tasks.sort(
        key=lambda item: (
            cost_priority.get(str(item[0]["group"]), 99),
            policy_priority[item[1]],
            str(item[0]["name"]),
        )
    )
    started = perf_counter()
    records: list[dict[str, object]] = []
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        futures = {executor.submit(_evaluate_task, task): task for task in tasks}
        for completed_count, future in enumerate(as_completed(futures), start=1):
            record = future.result()
            records.append(record)
            print(
                json.dumps(
                    {
                        "completed": completed_count,
                        "total": len(tasks),
                        "case": record["case"],
                        "policy": record["policy"],
                        "class": record["logarithmic_class"],
                        "tau_hat": record["dimensionless_event_time"],
                        "valid": record["numerically_valid"],
                        "wall_seconds": record["evaluation_wall_seconds"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    outer_wall = perf_counter() - started
    records.sort(
        key=lambda item: (
            next(index for index, case in enumerate(cases) if case["name"] == item["case"]),
            POLICY_ORDER.index(str(item["policy"])),
        )
    )
    analyses = [
        analyze_case(
            case,
            [record for record in records if record["case"] == case["name"]],
        )
        for case in cases
    ]
    aggregate = _aggregate(cases, analyses, records, outer_wall)
    _render(render_path, cases, records, analyses)
    payload: dict[str, object] = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "investigation": "first_flip_log_class_convergence",
        "question": "trusted-policy convergence of first-flip logarithmic class",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "workers": workers,
            "start_method": "spawn",
        },
        "physical_contract": {
            "model": "simple equal-link point-mass double pendulum",
            "parameters": asdict(parameters),
            "initial_angular_velocities_radians_per_second": [0.0, 0.0],
            "event": "first |theta_i(t)-theta_i(0)| = 2*pi on lifted absolute angles",
            "gravity_timescale_seconds": time_scale,
            "dimensionless_horizon": HORIZON_HAT,
            "physical_horizon_seconds": horizon_seconds,
            "strict_cap_semantics": True,
            "energy_inaccessible_rule": "E0 < -g for this simple unit model",
        },
        "classification_contract": {
            "primitive_remains": "first-flip time with event identity and finite-horizon censoring",
            "derived_representation": "first-flip logarithmic class",
            "classes": list(CLASS_ORDER[:-1]),
            "invalid_class_is_not_scientific_data": "numerically_invalid",
            "hierarchy": {
                "EXACT_TIME_STABLE": f"all trusted policies observe an event in the same logarithmic class and max physical time spread <= {EVENT_TIME_CONVERGENCE_SECONDS:g} s",
                "DECADE_STABLE": "all trusted policies return the same separate energy/censor/event-decade class",
                "HORIZON_OUTCOME_STABLE": "all trusted policies agree on flip versus no flip by the horizon",
                "NUMERICALLY_UNRESOLVED": "a numerical gate fails or trusted policies disagree on logarithmic class or horizon outcome",
                "implication": "EXACT_TIME_STABLE implies DECADE_STABLE implies HORIZON_OUTCOME_STABLE; unresolved may coexist with outcome stability when decades disagree",
            },
        },
        "numerical_policies": {
            name: {
                **asdict(policy),
                "physical_rhs": "independent symbolic EulerLagrangeDynamics.flow",
                "event_implementation": "scipy.solve_ivp terminal root",
            }
            for name, policy in policies.items()
        },
        "scientific_gates": {
            "exact_event_time_spread_seconds": EVENT_TIME_CONVERGENCE_SECONDS,
            "maximum_normalized_energy_drift": ENERGY_DRIFT_LIMIT,
            "maximum_event_surface_residual": EVENT_SURFACE_RESIDUAL_LIMIT,
            "maximum_accepted_angular_increment_strict": MAXIMUM_ACCEPTED_ANGULAR_INCREMENT,
        },
        "production_contract": {
            "production_dispatch_changed": False,
            "native_eligibility_changed": False,
            "all_investigation_policies_rejected_by_production_T5_allowlist": True,
        },
        "case_definition": {
            "path": case_path.name,
            "sha256": _sha256(case_path),
            "source": definition["source"],
            "selection_contract": definition["selection_contract"],
            "cases": cases,
        },
        "policy_results": records,
        "case_analysis": analyses,
        "aggregate": aggregate,
        "artifacts": {
            "render_path": str(render_path.relative_to(HERE)),
            "render_sha256": _sha256(render_path),
        },
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--render", type=Path, default=DEFAULT_RENDER)
    parser.add_argument("--workers", type=int, default=4)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    payload = run_investigation(
        case_path=arguments.cases,
        evidence_path=arguments.evidence,
        render_path=arguments.render,
        workers=arguments.workers,
    )
    print(json.dumps(payload["aggregate"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
