"""Bounded feasibility benchmark for a compiled first-flip physical RHS."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable, Mapping

import numba
import numpy as np
import scipy

from ....src.first_flip import reference as reference_module
from ....src.first_flip.field_adapter import (
    ENERGY_DRIFT_LIMIT,
    EVENT_SURFACE_RESIDUAL_LIMIT,
    EVENT_TIME_CONVERGENCE_SECONDS,
    FirstFlipFieldSpec,
    adapt_first_flip_result,
)
from ....src.first_flip.reference import (
    EventIdentity,
    FirstFlipResult,
    first_flip_time,
)
from ....src.generation import accepted_process_execution_spec, read_authoritative_field
from ....src.lyapunov.reference import EulerLagrangeState
from .first_flip_compiled_rhs import (
    PROTOTYPE_IDENTITY,
    compiled_rhs,
    first_flip_time_compiled_rhs,
    warm_compiled_rhs,
)


PERFORMANCE_DIRECTORY = Path(__file__).resolve().parents[1]
PROTOTYPE_DIRECTORY = PERFORMANCE_DIRECTORY.parents[1]
DEFAULT_FIELD = (
    PROTOTYPE_DIRECTORY
    / "outputs"
    / "first_flip_field"
    / "first_flip_field_512_T5s.h5"
)
DEFAULT_FIELD_MANIFEST = DEFAULT_FIELD.with_suffix(".json")
DEFAULT_OUTPUT = (
    PERFORMANCE_DIRECTORY
    / "evidence"
    / "current"
    / "first_flip_compiled_rhs_feasibility.json"
)
EVENT_STATE_CONVERGENCE_ATOL = 5.0e-7
TIMING_QUANTILES = tuple((index + 0.5) / 16.0 for index in range(16))
SIGNED_CASES = (
    ("experiment_020_arm1_positive", (-150.0, -150.0), EventIdentity(1, 1)),
    ("experiment_020_arm1_negative", (150.0, 150.0), EventIdentity(1, -1)),
    ("experiment_020_arm2_positive", (179.0, 179.0), EventIdentity(2, 1)),
    ("experiment_020_arm2_negative", (-179.0, -179.0), EventIdentity(2, -1)),
    (
        "experiment_020_near_horizon",
        (-180.0, -13.84615384615384),
        EventIdentity(2, -1),
    ),
)


@dataclass(frozen=True)
class Case:
    name: str
    source: str
    category: str
    theta1_radians: float
    theta2_radians: float
    weighting_sample: bool
    expected_identity: EventIdentity | None = None

    def state(self) -> EulerLagrangeState:
        return EulerLagrangeState(
            self.theta1_radians,
            self.theta2_radians,
            0.0,
            0.0,
        )


class TimedRhs:
    """Approximate inclusive Python-call wall for one RHS implementation."""

    def __init__(self, function: Callable[[float, np.ndarray], np.ndarray]) -> None:
        self.function = function
        self.calls = 0
        self.seconds = 0.0

    def __call__(self, time_value: float, state: np.ndarray) -> np.ndarray:
        started = perf_counter()
        try:
            return self.function(time_value, state)
        finally:
            self.seconds += perf_counter() - started
            self.calls += 1


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], capture_output=True, check=False, text=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _case_from_index(
    name: str,
    source: str,
    category: str,
    index: tuple[int, int],
    theta1_axis: np.ndarray,
    theta2_axis: np.ndarray,
    *,
    weighting_sample: bool,
) -> Case:
    theta2_index, theta1_index = index
    return Case(
        name=name,
        source=source,
        category=category,
        theta1_radians=float(theta1_axis[theta1_index]),
        theta2_radians=float(theta2_axis[theta2_index]),
        weighting_sample=weighting_sample,
    )


def _quantile_indices(indices: np.ndarray) -> tuple[tuple[int, int], ...]:
    positions = np.asarray(
        [min(len(indices) - 1, int(quantile * len(indices))) for quantile in TIMING_QUANTILES]
    )
    return tuple(tuple(int(value) for value in indices[position]) for position in positions)


def representative_cases(field_path: Path) -> tuple[Case, ...]:
    """Select fixed contract cases and distribution-aware 512-field samples."""

    snapshot = read_authoritative_field(field_path)
    cap = float(snapshot.metadata["numerical_parameters"]["dimensionless_observation_horizon"])
    observed = np.argwhere(snapshot.values < cap)
    observed_values = snapshot.values[observed[:, 0], observed[:, 1]]
    observed = observed[np.argsort(observed_values, kind="stable")]
    censored = np.argwhere(snapshot.values == cap)

    cases = [
        Case(
            name=name,
            source="experiment_020",
            category=("near_horizon" if "near_horizon" in name else "signed_event"),
            theta1_radians=float(np.deg2rad(angles[0])),
            theta2_radians=float(np.deg2rad(angles[1])),
            weighting_sample=False,
            expected_identity=identity,
        )
        for name, angles, identity in SIGNED_CASES
    ]
    for position, index in enumerate(_quantile_indices(observed)):
        quantile = TIMING_QUANTILES[position]
        category = "early_flip" if quantile < 0.25 else (
            "near_horizon" if quantile >= 0.875 else "medium_flip"
        )
        cases.append(
            _case_from_index(
                f"field_observed_q{quantile:.4f}",
                "authoritative_512_observed_time_quantile",
                category,
                index,
                snapshot.theta1_axis,
                snapshot.theta2_axis,
                weighting_sample=True,
            )
        )
    for position, index in enumerate(_quantile_indices(censored)):
        quantile = TIMING_QUANTILES[position]
        cases.append(
            _case_from_index(
                f"field_censored_spatial_q{quantile:.4f}",
                "authoritative_512_censored_flat_index_quantile",
                "censored",
                index,
                snapshot.theta1_axis,
                snapshot.theta2_axis,
                weighting_sample=True,
            )
        )
    return tuple(cases)


def _evaluate(
    case: Case,
    spec: FirstFlipFieldSpec,
    implementation: str,
) -> tuple[FirstFlipResult, object, float]:
    started = perf_counter()
    if implementation == "trusted":
        result = first_flip_time(
            case.state(),
            parameters=spec.parameters,
            solver_spec=spec.solver,
            observation_horizon=spec.observation_horizon_seconds,
        )
    elif implementation == "compiled":
        result = first_flip_time_compiled_rhs(
            case.state(),
            parameters=spec.parameters,
            solver_spec=spec.solver,
            observation_horizon=spec.observation_horizon_seconds,
        )
    else:  # pragma: no cover - fixed benchmark labels.
        raise ValueError(implementation)
    evaluation = adapt_first_flip_result(result, spec)
    return result, evaluation, perf_counter() - started


def _maximum_event_state_difference(
    trusted: FirstFlipResult, compiled: FirstFlipResult
) -> float:
    if trusted.event_state is None and compiled.event_state is None:
        return 0.0
    if trusted.event_state is None or compiled.event_state is None:
        return float("inf")
    return float(
        np.max(np.abs(np.asarray(trusted.event_state) - np.asarray(compiled.event_state)))
    )


def _maximum_residual_difference(
    trusted: FirstFlipResult, compiled: FirstFlipResult
) -> float:
    if not trusted.event_surface_residuals and not compiled.event_surface_residuals:
        return 0.0
    if len(trusted.event_surface_residuals) != len(compiled.event_surface_residuals):
        return float("inf")
    return max(
        abs(left.residual - right.residual)
        for left, right in zip(
            trusted.event_surface_residuals,
            compiled.event_surface_residuals,
            strict=True,
        )
    )


def compare_case(
    case: Case,
    spec: FirstFlipFieldSpec,
) -> tuple[dict[str, object], FirstFlipResult, FirstFlipResult]:
    trusted, trusted_evaluation, _ = _evaluate(case, spec, "trusted")
    compiled, compiled_evaluation, _ = _evaluate(case, spec, "compiled")
    time_difference = (
        0.0
        if trusted.event_time_seconds is None and compiled.event_time_seconds is None
        else abs(float(trusted.event_time_seconds) - float(compiled.event_time_seconds))
        if trusted.event_time_seconds is not None and compiled.event_time_seconds is not None
        else float("inf")
    )
    state_difference = _maximum_event_state_difference(trusted, compiled)
    residual_difference = _maximum_residual_difference(trusted, compiled)
    maximum_compiled_residual = max(
        (
            abs(item.residual)
            for item in compiled.event_surface_residuals
            if item.identity in compiled.event_identities
        ),
        default=0.0,
    )
    energy_difference = abs(
        trusted.maximum_normalized_energy_drift
        - compiled.maximum_normalized_energy_drift
    )
    checks = {
        "outcome_and_status": (
            trusted.status is compiled.status
            and trusted.event_observed == compiled.event_observed
            and trusted.censored == compiled.censored
            and trusted.solver_success == compiled.solver_success
            and trusted.numerically_valid == compiled.numerically_valid
            and trusted.validation_issues == compiled.validation_issues
            and trusted_evaluation.status is compiled_evaluation.status
            and trusted_evaluation.diagnostics.outcome
            == compiled_evaluation.diagnostics.outcome
        ),
        "event_attribution": (
            trusted.attribution is compiled.attribution
            and trusted.event_identities == compiled.event_identities
            and trusted.winning_arm == compiled.winning_arm
            and trusted.winning_direction == compiled.winning_direction
            and trusted.raw_event_counts == compiled.raw_event_counts
            and (
                case.expected_identity is None
                or compiled.event_identities == (case.expected_identity,)
            )
        ),
        "event_time": time_difference <= EVENT_TIME_CONVERGENCE_SECONDS,
        "event_state": state_difference <= EVENT_STATE_CONVERGENCE_ATOL,
        "event_residual": (
            maximum_compiled_residual <= EVENT_SURFACE_RESIDUAL_LIMIT
            and residual_difference <= EVENT_SURFACE_RESIDUAL_LIMIT
        ),
        "energy_diagnostic": (
            trusted.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT
            and compiled.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT
            and energy_difference <= ENERGY_DRIFT_LIMIT
        ),
        "rhs_evaluation_count": trusted.rhs_evaluations == compiled.rhs_evaluations,
    }
    return (
        {
            "accepted": all(checks.values()),
            "checks": checks,
            "trusted_status": trusted.status.value,
            "compiled_status": compiled.status.value,
            "trusted_identity": (
                trusted.event_identities[0].label
                if len(trusted.event_identities) == 1
                else None
            ),
            "compiled_identity": (
                compiled.event_identities[0].label
                if len(compiled.event_identities) == 1
                else None
            ),
            "trusted_event_time_seconds": trusted.event_time_seconds,
            "compiled_event_time_seconds": compiled.event_time_seconds,
            "event_time_difference_seconds": time_difference,
            "maximum_event_state_difference": state_difference,
            "maximum_event_residual_difference": residual_difference,
            "maximum_compiled_event_residual": maximum_compiled_residual,
            "trusted_maximum_normalized_energy_drift": (
                trusted.maximum_normalized_energy_drift
            ),
            "compiled_maximum_normalized_energy_drift": (
                compiled.maximum_normalized_energy_drift
            ),
            "energy_diagnostic_difference": energy_difference,
            "trusted_rhs_evaluations": trusted.rhs_evaluations,
            "compiled_rhs_evaluations": compiled.rhs_evaluations,
        },
        trusted,
        compiled,
    )


def _timed_rhs_attribution(
    case: Case,
    spec: FirstFlipFieldSpec,
    implementation: str,
) -> dict[str, object]:
    if implementation == "trusted":
        function = reference_module._cached_dynamics(spec.parameters).flow
    else:
        function = compiled_rhs(spec.parameters)
    timer = TimedRhs(function)
    started = perf_counter()
    result = first_flip_time(
        case.state(),
        parameters=spec.parameters,
        solver_spec=spec.solver,
        observation_horizon=spec.observation_horizon_seconds,
        _rhs_override=timer,
    )
    adapt_first_flip_result(result, spec)
    outer = perf_counter() - started
    return {
        "rhs_calls": timer.calls,
        "rhs_inclusive_seconds": timer.seconds,
        "solve_ivp_seconds": result.wall_seconds,
        "evaluator_seconds": outer,
        "rhs_fraction_of_solve_ivp": timer.seconds / result.wall_seconds,
        "rhs_fraction_of_evaluator": timer.seconds / outer,
    }


def _distribution(values: list[float]) -> dict[str, float]:
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "maximum": max(values),
    }


def run_benchmark(
    field_path: Path,
    field_manifest_path: Path,
    repetitions: int,
) -> dict[str, object]:
    spec = FirstFlipFieldSpec()
    warm_compiled_rhs(spec.parameters)
    reference_module.initialize_reference_dynamics(spec.parameters)
    cases = representative_cases(field_path)
    records: list[dict[str, object]] = []
    for case_index, case in enumerate(cases):
        comparison, trusted_result, compiled_result = compare_case(case, spec)
        _evaluate(case, spec, "trusted")
        _evaluate(case, spec, "compiled")
        timings = {"trusted": [], "compiled": []}
        for repetition in range(repetitions):
            order = (
                ("trusted", "compiled")
                if (case_index + repetition) % 2 == 0
                else ("compiled", "trusted")
            )
            for implementation in order:
                _result, _evaluation, elapsed = _evaluate(
                    case, spec, implementation
                )
                timings[implementation].append(elapsed)
        trusted_median = statistics.median(timings["trusted"])
        compiled_median = statistics.median(timings["compiled"])
        records.append(
            {
                **asdict(case),
                "expected_identity": (
                    case.expected_identity.label if case.expected_identity else None
                ),
                "outcome": (
                    "observed" if trusted_result.event_observed else "censored"
                ),
                "event_time_seconds": trusted_result.event_time_seconds,
                "rhs_evaluations": trusted_result.rhs_evaluations,
                "correctness": comparison,
                "timing": {
                    "repetitions": repetitions,
                    "trusted_seconds": timings["trusted"],
                    "compiled_seconds": timings["compiled"],
                    "trusted_median_seconds": trusted_median,
                    "compiled_median_seconds": compiled_median,
                    "speedup": trusted_median / compiled_median,
                },
                "compiled_result_status": compiled_result.status.value,
            }
        )

    weighting_records = [record for record in records if record["weighting_sample"]]
    groups: dict[str, object] = {}
    for outcome in ("observed", "censored"):
        selected = [record for record in weighting_records if record["outcome"] == outcome]
        trusted = [float(record["timing"]["trusted_median_seconds"]) for record in selected]
        compiled = [float(record["timing"]["compiled_median_seconds"]) for record in selected]
        speedups = [float(record["timing"]["speedup"]) for record in selected]
        rhs_counts = [int(record["rhs_evaluations"]) for record in selected]
        groups[outcome] = {
            "cells": len(selected),
            "trusted_seconds": _distribution(trusted),
            "compiled_seconds": _distribution(compiled),
            "speedup": _distribution(speedups),
            "rhs_evaluations": _distribution([float(value) for value in rhs_counts]),
        }

    manifest = json.loads(field_manifest_path.read_text())
    observed_fraction = float(manifest["field_statistics"]["observed_fraction"])
    censored_fraction = float(manifest["field_statistics"]["censored_fraction"])
    trusted_weighted = (
        observed_fraction * groups["observed"]["trusted_seconds"]["mean"]
        + censored_fraction * groups["censored"]["trusted_seconds"]["mean"]
    )
    compiled_weighted = (
        observed_fraction * groups["observed"]["compiled_seconds"]["mean"]
        + censored_fraction * groups["censored"]["compiled_seconds"]["mean"]
    )
    attribution_cases = {
        "observed": next(
            case for case in cases if case.name == "field_observed_q0.5312"
        ),
        "censored": next(
            case for case in cases if case.name == "field_censored_spatial_q0.5312"
        ),
    }
    attribution = {
        outcome: {
            implementation: _timed_rhs_attribution(case, spec, implementation)
            for implementation in ("trusted", "compiled")
        }
        for outcome, case in attribution_cases.items()
    }
    estimated_cell_compute_speedup = trusted_weighted / compiled_weighted
    baseline_total = float(manifest["run_summary"]["total_seconds"])
    baseline_evaluation = float(manifest["run_summary"]["evaluation_seconds"])
    estimated_evaluation = baseline_evaluation / estimated_cell_compute_speedup
    estimated_total = baseline_total - baseline_evaluation + estimated_evaluation
    estimated_field_speedup = baseline_total / estimated_total
    all_correct = all(bool(record["correctness"]["accepted"]) for record in records)
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "compiled four-state RHS under unchanged first-flip solve_ivp events",
        "prototype_identity": PROTOTYPE_IDENTITY,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "numba": numba.__version__,
            "git_head": _git_output("rev-parse", "HEAD"),
            "git_status_short_before_artifact": _git_output("status", "--short"),
        },
        "contract": {
            "field_spec": asdict(spec),
            "event_time_tolerance_seconds": EVENT_TIME_CONVERGENCE_SECONDS,
            "event_state_tolerance": EVENT_STATE_CONVERGENCE_ATOL,
            "event_surface_residual_limit": EVENT_SURFACE_RESIDUAL_LIMIT,
            "energy_drift_limit": ENERGY_DRIFT_LIMIT,
            "events": ["arm1-", "arm1+", "arm2-", "arm2+"],
            "terminal": True,
            "direction": 1.0,
        },
        "selection": {
            "authoritative_field": str(field_path),
            "authoritative_field_sha256": _sha256(field_path),
            "field_manifest": str(field_manifest_path),
            "field_manifest_sha256": _sha256(field_manifest_path),
            "timing_quantiles": list(TIMING_QUANTILES),
            "case_count": len(records),
            "weighting_case_count": len(weighting_records),
        },
        "existing_512_field": {
            "cell_count": manifest["field_statistics"]["cell_count"],
            "observed_count": manifest["field_statistics"]["observed_count"],
            "observed_fraction": observed_fraction,
            "censored_count": manifest["field_statistics"]["censored_count"],
            "censored_fraction": censored_fraction,
            "execution_policy": asdict(accepted_process_execution_spec()),
        },
        "cases": records,
        "group_timings": groups,
        "rhs_attribution": attribution,
        "weighted_estimate": {
            "formula": "(p_observed * mean_observed) + (p_censored * mean_censored)",
            "trusted_weighted_seconds_per_cell": trusted_weighted,
            "compiled_weighted_seconds_per_cell": compiled_weighted,
            "estimated_cell_compute_speedup": estimated_cell_compute_speedup,
            "existing_512_total_seconds": baseline_total,
            "existing_512_evaluation_seconds": baseline_evaluation,
            "estimated_compiled_evaluation_seconds": estimated_evaluation,
            "estimated_512_total_seconds": estimated_total,
            "estimated_whole_field_speedup": estimated_field_speedup,
            "whole_field_formula": (
                "baseline_total / (baseline_total - baseline_evaluation "
                "+ baseline_evaluation / estimated_cell_compute_speedup)"
            ),
            "promotion_threshold": 1.5,
        },
        "decision": {
            "all_scientific_comparisons_accepted": all_correct,
            "estimated_speedup_at_least_1_5": estimated_field_speedup >= 1.5,
            "recommend_promotion": all_correct and estimated_field_speedup >= 1.5,
        },
        "source_sha256": {
            str(path): _sha256(path)
            for path in (
                Path(__file__),
                Path(__file__).with_name("first_flip_compiled_rhs.py"),
                Path(reference_module.__file__),
                PROTOTYPE_DIRECTORY / "src" / "first_flip" / "field_adapter.py",
            )
        },
    }


def save(payload: Mapping[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as target:
        json.dump(payload, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field", type=Path, default=DEFAULT_FIELD)
    parser.add_argument("--field-manifest", type=Path, default=DEFAULT_FIELD_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repetitions", type=int, default=9)
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    if options.output.exists():
        raise FileExistsError(f"Refusing to replace benchmark: {options.output}")
    if options.repetitions < 3:
        raise ValueError("At least three warm timing repetitions are required")
    payload = run_benchmark(
        options.field, options.field_manifest, options.repetitions
    )
    save(payload, options.output)
    print(json.dumps({
        "group_timings": payload["group_timings"],
        "weighted_estimate": payload["weighted_estimate"],
        "decision": payload["decision"],
    }, indent=2, sort_keys=True))
    return 0 if payload["decision"]["all_scientific_comparisons_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
