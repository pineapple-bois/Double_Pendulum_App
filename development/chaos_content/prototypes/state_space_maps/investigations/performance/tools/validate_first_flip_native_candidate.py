"""Reproduce the 37-case production native first-flip promotion validation."""

from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ....src.first_flip.field_adapter import FirstFlipFieldSpec, adapt_first_flip_result
from ....src.first_flip.native_artifacts import FIRST_FLIP_NATIVE_EVALUATOR
from ....src.first_flip.native_runtime import first_flip_native_provenance, run_native_first_flip
from ....src.first_flip.reference import first_flip_time
from ....src.lyapunov.reference import EulerLagrangeState
from ....src.state_space_fields import EvaluationStatus

PERFORMANCE = Path(__file__).resolve().parents[1]
DEFAULT_CASES = PERFORMANCE / "evidence/current/first_flip_compiled_rhs_feasibility.json"
DEFAULT_OUTPUT = PERFORMANCE / "evidence/current/first_flip_native_dop853_promotion_candidate.json"


def _difference(left, right) -> float:
    if left is None and right is None:
        return 0.0
    if left is None or right is None:
        return float("inf")
    return abs(float(left) - float(right))


def validate(case_path: Path) -> dict[str, object]:
    cases = json.loads(case_path.read_text())["cases"]
    if len(cases) != 37:
        raise ValueError("the saved validation set must contain exactly 37 cases")
    spec = FirstFlipFieldSpec()
    records = []
    maxima = {"event_time_difference_seconds": 0.0, "event_state_component_difference": 0.0, "triggering_residual": 0.0, "normalized_energy_drift": 0.0, "normalized_energy_drift_difference": 0.0, "accepted_angular_increment": 0.0, "solver_step_seconds": 0.0, "censored_endpoint_difference_seconds": 0.0}
    for case in cases:
        state = EulerLagrangeState(float(case["theta1_radians"]), float(case["theta2_radians"]), 0.0, 0.0)
        trusted = first_flip_time(state, spec.parameters, spec.solver, 5.0)
        execution = run_native_first_flip(state, spec.parameters, spec.solver, 5.0)
        native = execution.result
        trusted_adapter = adapt_first_flip_result(trusted, spec)
        native_adapter = adapt_first_flip_result(native, spec, evaluator=FIRST_FLIP_NATIVE_EVALUATOR, implementation_provenance=first_flip_native_provenance())
        time_difference = _difference(native.event_time_seconds, trusted.event_time_seconds)
        state_difference = 0.0 if native.event_state is None and trusted.event_state is None else float(np.max(np.abs(np.asarray(native.event_state) - np.asarray(trusted.event_state))))
        triggering_residual = max((abs(item.residual) for item in native.event_surface_residuals if item.identity in native.event_identities), default=0.0)
        endpoint_difference = abs(native.integration_endpoint_seconds - 5.0) if native.censored else 0.0
        checks = {
            "completed_valid": trusted_adapter.status is EvaluationStatus.COMPLETED_VALID and native_adapter.status is EvaluationStatus.COMPLETED_VALID,
            "classification": native.status is trusted.status and native.event_observed == trusted.event_observed and native.censored == trusted.censored,
            "attribution": native.event_identities == trusted.event_identities and native.winning_arm == trusted.winning_arm and native.winning_direction == trusted.winning_direction,
            "event_counts": native.raw_event_counts == trusted.raw_event_counts,
            "event_time": time_difference <= 5e-8,
            "event_state": state_difference <= 5e-7,
            "triggering_residual": triggering_residual <= 1e-10,
            "energy": native.maximum_normalized_energy_drift <= 5e-9,
            "angular_increment": native.maximum_accepted_angular_increment < 0.5,
            "censored_endpoint": endpoint_difference <= 2e-14,
            "max_step": execution.maximum_solver_step_seconds <= float(spec.solver.max_step) + 2e-14,
        }
        if not all(checks.values()):
            raise AssertionError(f"production native validation failed for {case['name']}: {checks}")
        values = {
            "event_time_difference_seconds": time_difference,
            "event_state_component_difference": state_difference,
            "triggering_residual": triggering_residual,
            "normalized_energy_drift": native.maximum_normalized_energy_drift,
            "normalized_energy_drift_difference": abs(native.maximum_normalized_energy_drift - trusted.maximum_normalized_energy_drift),
            "accepted_angular_increment": native.maximum_accepted_angular_increment,
            "solver_step_seconds": execution.maximum_solver_step_seconds,
            "censored_endpoint_difference_seconds": endpoint_difference,
        }
        for key, value in values.items():
            maxima[key] = max(maxima[key], value)
        records.append({"name": case["name"], "outcome": native.status.value, "checks": checks, **values})
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "case_source": str(case_path.relative_to(PERFORMANCE)),
        "case_count": len(cases), "passed_count": len(records), "all_passed": True,
        "maxima": maxima, "native_provenance": first_flip_native_provenance(), "cases": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = validate(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"all_passed": payload["all_passed"], "case_count": payload["case_count"], "maxima": payload["maxima"]}, indent=2))


if __name__ == "__main__":
    main()
