"""Validate and benchmark the investigation-only native first-flip loop."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import permutations
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

import numba
import numpy as np
import scipy

from ....src.first_flip.compiled import first_flip_time_compiled
from ....src.first_flip.field_adapter import (
    ENERGY_DRIFT_LIMIT,
    EVENT_SURFACE_RESIDUAL_LIMIT,
    EVENT_TIME_CONVERGENCE_SECONDS,
    FirstFlipFieldSpec,
    adapt_first_flip_result,
)
from ....src.first_flip.reference import FirstFlipResult, first_flip_time
from ....src.lyapunov.reference import EulerLagrangeState
from .first_flip_native_dop853 import (
    PROTOTYPE_IDENTITY,
    NativeFirstFlipExecution,
    native_runtime,
    prototype_source_identity,
    run_native_first_flip,
)


PERFORMANCE_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_CASE_EVIDENCE = (
    PERFORMANCE_DIRECTORY
    / "evidence/current/first_flip_compiled_rhs_feasibility.json"
)
DEFAULT_PROMOTION_EVIDENCE = (
    PERFORMANCE_DIRECTORY
    / "evidence/current/first_flip_compiled_promotion_64.json"
)
DEFAULT_PROFILE_EVIDENCE = (
    PERFORMANCE_DIRECTORY
    / "evidence/current/first_flip_post_promotion_profile.json"
)
DEFAULT_OUTPUT = (
    PERFORMANCE_DIRECTORY
    / "evidence/current/first_flip_native_dop853_prototype.json"
)
EVENT_STATE_GATE = 5.0e-7
ENERGY_DIFFERENCE_GATE = 5.0e-9
ANGULAR_INCREMENT_GATE = 0.5
BOUNDARY_ACCELERATION_GATE = 2.565
WHOLE_FIELD_SPEEDUP_GATE = 1.5


@dataclass(frozen=True)
class Case:
    name: str
    source: str
    outcome: str
    theta1_radians: float
    theta2_radians: float
    weighting_sample: bool

    def state(self) -> EulerLagrangeState:
        return EulerLagrangeState(
            self.theta1_radians,
            self.theta2_radians,
            0.0,
            0.0,
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], capture_output=True, check=False, text=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _load_cases(path: Path) -> tuple[Case, ...]:
    payload = json.loads(path.read_text())
    cases = tuple(
        Case(
            name=str(record["name"]),
            source=str(record["source"]),
            outcome=str(record["outcome"]),
            theta1_radians=float(record["theta1_radians"]),
            theta2_radians=float(record["theta2_radians"]),
            weighting_sample=bool(record["weighting_sample"]),
        )
        for record in payload["cases"]
    )
    required = {
        "experiment_020_arm1_positive",
        "experiment_020_arm1_negative",
        "experiment_020_arm2_positive",
        "experiment_020_arm2_negative",
        "experiment_020_near_horizon",
    }
    if len(cases) != 37 or not required.issubset({case.name for case in cases}):
        raise ValueError("saved feasibility evidence does not contain the 37-case set")
    return cases


def _event_state_difference(left: FirstFlipResult, right: FirstFlipResult) -> float:
    if left.event_state is None and right.event_state is None:
        return 0.0
    if left.event_state is None or right.event_state is None:
        return float("inf")
    return float(
        np.max(np.abs(np.asarray(left.event_state) - np.asarray(right.event_state)))
    )


def _event_time_difference(left: FirstFlipResult, right: FirstFlipResult) -> float:
    if left.event_time_seconds is None and right.event_time_seconds is None:
        return 0.0
    if left.event_time_seconds is None or right.event_time_seconds is None:
        return float("inf")
    return abs(left.event_time_seconds - right.event_time_seconds)


def _residual_difference(left: FirstFlipResult, right: FirstFlipResult) -> float:
    if not left.event_surface_residuals and not right.event_surface_residuals:
        return 0.0
    if len(left.event_surface_residuals) != len(right.event_surface_residuals):
        return float("inf")
    return max(
        abs(a.residual - b.residual)
        for a, b in zip(
            left.event_surface_residuals,
            right.event_surface_residuals,
            strict=True,
        )
    )


def _triggering_residual(result: FirstFlipResult) -> float:
    return max(
        (
            abs(item.residual)
            for item in result.event_surface_residuals
            if item.identity in result.event_identities
        ),
        default=0.0,
    )


def validate_case(case: Case, spec: FirstFlipFieldSpec) -> dict[str, Any]:
    trusted = first_flip_time(
        case.state(), spec.parameters, spec.solver, spec.observation_horizon_seconds
    )
    compiled = first_flip_time_compiled(
        case.state(), spec.parameters, spec.solver, spec.observation_horizon_seconds
    )
    native_execution = run_native_first_flip(
        case.state(), spec.parameters, spec.solver, spec.observation_horizon_seconds
    )
    native = native_execution.result
    trusted_adapter = adapt_first_flip_result(trusted, spec)
    compiled_adapter = adapt_first_flip_result(compiled, spec)
    native_adapter = adapt_first_flip_result(
        native, spec, evaluator=PROTOTYPE_IDENTITY
    )
    time_difference = _event_time_difference(trusted, native)
    state_difference = _event_state_difference(trusted, native)
    residual_difference = _residual_difference(trusted, native)
    energy_difference = abs(
        trusted.maximum_normalized_energy_drift
        - native.maximum_normalized_energy_drift
    )
    checks = {
        "classification": (
            trusted.status is compiled.status is native.status
            and trusted.event_observed == compiled.event_observed == native.event_observed
            and trusted.censored == compiled.censored == native.censored
            and trusted.solver_success and compiled.solver_success and native.solver_success
            and trusted.numerically_valid
            and compiled.numerically_valid
            and native.numerically_valid
        ),
        "attribution": (
            trusted.attribution is compiled.attribution is native.attribution
            and trusted.event_identities
            == compiled.event_identities
            == native.event_identities
            and trusted.winning_arm == compiled.winning_arm == native.winning_arm
            and trusted.winning_direction
            == compiled.winning_direction
            == native.winning_direction
        ),
        "event_counts": (
            trusted.raw_event_counts
            == compiled.raw_event_counts
            == native.raw_event_counts
            and native_execution.terminal_candidate_count
            == (1 if native.event_observed else 0)
        ),
        "event_time": time_difference <= EVENT_TIME_CONVERGENCE_SECONDS,
        "event_state": state_difference <= EVENT_STATE_GATE,
        "triggering_event_residual": (
            _triggering_residual(native) <= EVENT_SURFACE_RESIDUAL_LIMIT
        ),
        "energy": (
            trusted.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT
            and compiled.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT
            and native.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT
            and energy_difference <= ENERGY_DIFFERENCE_GATE
        ),
        "angular_increment": (
            trusted.maximum_accepted_angular_increment < ANGULAR_INCREMENT_GATE
            and compiled.maximum_accepted_angular_increment < ANGULAR_INCREMENT_GATE
            and native.maximum_accepted_angular_increment < ANGULAR_INCREMENT_GATE
        ),
        "adapter_completed_valid": (
            trusted_adapter.status.value == "completed_valid"
            and compiled_adapter.status.value == "completed_valid"
            and native_adapter.status.value == "completed_valid"
        ),
        "censored_endpoint": (
            native.event_observed
            or native.integration_endpoint_seconds
            == spec.observation_horizon_seconds
        ),
    }
    return {
        **asdict(case),
        "accepted": all(checks.values()),
        "checks": checks,
        "trusted_status": trusted.status.value,
        "native_status": native.status.value,
        "trusted_identity": (
            trusted.event_identities[0].label
            if len(trusted.event_identities) == 1
            else None
        ),
        "native_identity": (
            native.event_identities[0].label
            if len(native.event_identities) == 1
            else None
        ),
        "event_time_difference_seconds": time_difference,
        "event_state_maximum_component_difference": state_difference,
        "triggering_residual": _triggering_residual(native),
        "surface_residual_maximum_difference": residual_difference,
        "trusted_maximum_normalized_energy_drift": (
            trusted.maximum_normalized_energy_drift
        ),
        "native_maximum_normalized_energy_drift": (
            native.maximum_normalized_energy_drift
        ),
        "energy_diagnostic_difference": energy_difference,
        "trusted_maximum_accepted_angular_increment": (
            trusted.maximum_accepted_angular_increment
        ),
        "native_maximum_accepted_angular_increment": (
            native.maximum_accepted_angular_increment
        ),
        "trusted_rhs_evaluations": trusted.rhs_evaluations,
        "compiled_rhs_evaluations": compiled.rhs_evaluations,
        "native_rhs_evaluations": native.rhs_evaluations,
        "native_accepted_steps": native_execution.accepted_steps,
        "native_rejected_steps": native_execution.rejected_steps,
        "native_maximum_solver_step_seconds": (
            native_execution.maximum_solver_step_seconds
        ),
        "native_terminal_candidate_count": native_execution.terminal_candidate_count,
        "native_root_iterations": native_execution.root_iterations,
    }


def _evaluate(
    case: Case,
    spec: FirstFlipFieldSpec,
    implementation: str,
) -> tuple[float, float, FirstFlipResult]:
    started = perf_counter()
    if implementation == "trusted":
        result = first_flip_time(
            case.state(), spec.parameters, spec.solver, spec.observation_horizon_seconds
        )
        native_wall = 0.0
    elif implementation == "compiled":
        result = first_flip_time_compiled(
            case.state(), spec.parameters, spec.solver, spec.observation_horizon_seconds
        )
        native_wall = 0.0
    elif implementation == "native":
        execution = run_native_first_flip(
            case.state(), spec.parameters, spec.solver, spec.observation_horizon_seconds
        )
        result = execution.result
        native_wall = execution.native_loop_wall_seconds
    else:
        raise ValueError(implementation)
    adapt_first_flip_result(result, spec, evaluator=implementation)
    return perf_counter() - started, native_wall, result


def _distribution(values: list[float]) -> dict[str, float]:
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "maximum": max(values),
    }


def benchmark_cases(
    cases: tuple[Case, ...], spec: FirstFlipFieldSpec, repetitions: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    timing_cases = tuple(case for case in cases if case.weighting_sample)
    implementations = ("trusted", "compiled", "native")
    orders = tuple(permutations(implementations))
    records: list[dict[str, Any]] = []
    for case_index, case in enumerate(timing_cases):
        for implementation in implementations:
            _evaluate(case, spec, implementation)
        elapsed = {name: [] for name in implementations}
        native_loop: list[float] = []
        rhs_evaluations = {name: 0 for name in implementations}
        for repetition in range(repetitions):
            for implementation in orders[(case_index + repetition) % len(orders)]:
                wall, loop_wall, result = _evaluate(case, spec, implementation)
                elapsed[implementation].append(wall)
                rhs_evaluations[implementation] = result.rhs_evaluations
                if implementation == "native":
                    native_loop.append(loop_wall)
        medians = {
            name: statistics.median(values) for name, values in elapsed.items()
        }
        records.append(
            {
                **asdict(case),
                "repetitions": repetitions,
                "evaluator_seconds": elapsed,
                "evaluator_median_seconds": medians,
                "native_loop_seconds": native_loop,
                "native_loop_median_seconds": statistics.median(native_loop),
                "speedup_native_over_trusted": medians["trusted"] / medians["native"],
                "speedup_native_over_compiled": medians["compiled"] / medians["native"],
                "rhs_evaluations": rhs_evaluations,
            }
        )

    groups: dict[str, Any] = {}
    for outcome in ("observed", "censored"):
        selected = [record for record in records if record["outcome"] == outcome]
        groups[outcome] = {
            "case_count": len(selected),
            "evaluator_seconds": {
                implementation: _distribution(
                    [
                        float(record["evaluator_median_seconds"][implementation])
                        for record in selected
                    ]
                )
                for implementation in implementations
            },
            "native_loop_seconds": _distribution(
                [float(record["native_loop_median_seconds"]) for record in selected]
            ),
            "speedup_native_over_trusted": _distribution(
                [float(record["speedup_native_over_trusted"]) for record in selected]
            ),
            "speedup_native_over_compiled": _distribution(
                [float(record["speedup_native_over_compiled"]) for record in selected]
            ),
            "rhs_evaluations": {
                implementation: _distribution(
                    [float(record["rhs_evaluations"][implementation]) for record in selected]
                )
                for implementation in implementations
            },
        }
    return records, groups


def run_benchmark(
    case_evidence_path: Path,
    promotion_evidence_path: Path,
    profile_evidence_path: Path,
    repetitions: int,
) -> dict[str, Any]:
    spec = FirstFlipFieldSpec()
    cases = _load_cases(case_evidence_path)
    cold_started = perf_counter()
    native_runtime()
    cold_initialization = perf_counter() - cold_started

    scientific_records = [validate_case(case, spec) for case in cases]
    all_scientific = all(record["accepted"] for record in scientific_records)
    timing_records: list[dict[str, Any]] = []
    groups: dict[str, Any] = {}
    if all_scientific:
        timing_records, groups = benchmark_cases(cases, spec, repetitions)

    promotion = json.loads(promotion_evidence_path.read_text())
    profile = json.loads(profile_evidence_path.read_text())
    observed_fraction = 1742.0 / 4096.0
    censored_fraction = 2354.0 / 4096.0
    weighted: dict[str, float] = {}
    boundary_acceleration = 0.0
    projected: dict[str, float] = {}
    if all_scientific:
        for implementation in ("trusted", "compiled", "native"):
            weighted[implementation] = (
                observed_fraction
                * groups["observed"]["evaluator_seconds"][implementation]["mean"]
                + censored_fraction
                * groups["censored"]["evaluator_seconds"][implementation]["mean"]
            )
        weighted["native_loop"] = (
            observed_fraction * groups["observed"]["native_loop_seconds"]["mean"]
            + censored_fraction * groups["censored"]["native_loop_seconds"]["mean"]
        )
        prior_boundary = float(
            profile["weighted_profile"]["boundary_outside_rhs_seconds"]
        )
        boundary_acceleration = prior_boundary / weighted["native_loop"]
        baseline_total = statistics.median(
            float(pair["compiled"]["outer_wall_seconds"])
            for pair in promotion["pairs"]
        )
        baseline_evaluation = statistics.median(
            float(pair["compiled"]["runner"]["evaluation_seconds"])
            for pair in promotion["pairs"]
        )
        fixed_evaluation = float(
            profile["operational_ceiling"][
                "fixed_operational_evaluation_residual_seconds"
            ]
        )
        process_width = int(promotion["workload"]["execution"]["process_width"])
        cell_count = int(promotion["workload"]["samples_per_axis"]) ** 2
        projected_cell_compute = weighted["native"] * cell_count / process_width
        projected_evaluation = fixed_evaluation + projected_cell_compute
        projected_total = baseline_total - baseline_evaluation + projected_evaluation
        projected = {
            "baseline_64_total_seconds": baseline_total,
            "baseline_64_evaluation_seconds": baseline_evaluation,
            "fixed_evaluation_residual_seconds": fixed_evaluation,
            "projected_native_cell_compute_seconds": projected_cell_compute,
            "projected_native_evaluation_seconds": projected_evaluation,
            "projected_native_total_seconds": projected_total,
            "projected_additional_whole_field_speedup": baseline_total / projected_total,
        }

    performance_pass = bool(
        all_scientific
        and boundary_acceleration >= BOUNDARY_ACCELERATION_GATE
        and projected["projected_additional_whole_field_speedup"]
        >= WHOLE_FIELD_SPEEDUP_GATE
    )
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "investigation-only native DOP853 first-flip prototype",
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
        "inputs": {
            "case_evidence": str(case_evidence_path),
            "case_evidence_sha256": _sha256(case_evidence_path),
            "promotion_evidence": str(promotion_evidence_path),
            "promotion_evidence_sha256": _sha256(promotion_evidence_path),
            "profile_evidence": str(profile_evidence_path),
            "profile_evidence_sha256": _sha256(profile_evidence_path),
            "case_count": len(cases),
            "timing_case_count": sum(case.weighting_sample for case in cases),
            "repetitions": repetitions,
            "observed_fraction": observed_fraction,
            "censored_fraction": censored_fraction,
        },
        "contract": {
            "field_spec": asdict(spec),
            "event_time_gate_seconds": EVENT_TIME_CONVERGENCE_SECONDS,
            "event_state_gate": EVENT_STATE_GATE,
            "event_residual_gate": EVENT_SURFACE_RESIDUAL_LIMIT,
            "energy_gate": ENERGY_DRIFT_LIMIT,
            "energy_difference_gate": ENERGY_DIFFERENCE_GATE,
            "angular_increment_strict_upper_bound": ANGULAR_INCREMENT_GATE,
        },
        "source_identity": prototype_source_identity(),
        "cold_initialization_seconds": cold_initialization,
        "scientific_validation": {
            "accepted": all_scientific,
            "cases": scientific_records,
            "maximum_event_time_difference_seconds": max(
                float(record["event_time_difference_seconds"])
                for record in scientific_records
            ),
            "maximum_event_state_component_difference": max(
                float(record["event_state_maximum_component_difference"])
                for record in scientific_records
            ),
            "maximum_triggering_residual": max(
                float(record["triggering_residual"])
                for record in scientific_records
            ),
            "maximum_surface_residual_difference": max(
                float(record["surface_residual_maximum_difference"])
                for record in scientific_records
            ),
            "maximum_native_normalized_energy_drift": max(
                float(record["native_maximum_normalized_energy_drift"])
                for record in scientific_records
            ),
            "maximum_energy_diagnostic_difference": max(
                float(record["energy_diagnostic_difference"])
                for record in scientific_records
            ),
            "maximum_native_accepted_angular_increment": max(
                float(record["native_maximum_accepted_angular_increment"])
                for record in scientific_records
            ),
            "maximum_native_solver_step_seconds": max(
                float(record["native_maximum_solver_step_seconds"])
                for record in scientific_records
            ),
        },
        "timings": {
            "performed": all_scientific,
            "cases": timing_records,
            "groups": groups,
            "weighted_evaluator_seconds": weighted,
            "native_boundary_acceleration_conservative": boundary_acceleration,
            "boundary_acceleration_gate": BOUNDARY_ACCELERATION_GATE,
        },
        "whole_field_projection": projected,
        "decision": {
            "scientific_gate_passed": all_scientific,
            "boundary_gate_passed": boundary_acceleration
            >= BOUNDARY_ACCELERATION_GATE,
            "whole_field_gate_passed": bool(
                projected
                and projected["projected_additional_whole_field_speedup"]
                >= WHOLE_FIELD_SPEEDUP_GATE
            ),
            "promotion_recommended": performance_pass,
            "decision": (
                "PROMOTE NATIVE FIRST-FLIP DOP853 NEXT"
                if performance_pass
                else "KEEP COMPILED-RHS SOLVE_IVP ROUTE"
            ),
        },
        "source_sha256": {str(Path(__file__)): _sha256(Path(__file__))},
    }


def save(payload: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as target:
        json.dump(payload, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-evidence", type=Path, default=DEFAULT_CASE_EVIDENCE)
    parser.add_argument(
        "--promotion-evidence", type=Path, default=DEFAULT_PROMOTION_EVIDENCE
    )
    parser.add_argument("--profile-evidence", type=Path, default=DEFAULT_PROFILE_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repetitions", type=int, default=7)
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    if options.repetitions < 3:
        raise ValueError("At least three repetitions are required")
    if options.output.exists():
        raise FileExistsError(f"Refusing to overwrite evidence: {options.output}")
    payload = run_benchmark(
        options.case_evidence,
        options.promotion_evidence,
        options.profile_evidence,
        options.repetitions,
    )
    save(payload, options.output)
    print(
        json.dumps(
            {
                "scientific_validation": {
                    key: value
                    for key, value in payload["scientific_validation"].items()
                    if key != "cases"
                },
                "groups": payload["timings"]["groups"],
                "weighted": payload["timings"]["weighted_evaluator_seconds"],
                "boundary_acceleration": payload["timings"][
                    "native_boundary_acceleration_conservative"
                ],
                "whole_field_projection": payload["whole_field_projection"],
                "decision": payload["decision"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["scientific_validation"]["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
