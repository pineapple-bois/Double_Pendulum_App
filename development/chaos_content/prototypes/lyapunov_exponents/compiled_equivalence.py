"""Bounded reference-versus-Numba equivalence and timing assessment."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from time import perf_counter

import numpy as np

if __package__:
    from .compiled import (
        compiled_reference_and_tangent_rhs,
        run_renormalized_tangent_compiled,
    )
    from .reference import (
        CandidateAMetric,
        EulerLagrangeState,
        RenormalizedTangentResult,
        RenormalizedTangentSpec,
        run_renormalized_tangent,
    )
else:
    from compiled import (
        compiled_reference_and_tangent_rhs,
        run_renormalized_tangent_compiled,
    )
    from reference import (
        CandidateAMetric,
        EulerLagrangeState,
        RenormalizedTangentResult,
        RenormalizedTangentSpec,
        run_renormalized_tangent,
    )


PROTOTYPE_ROOT = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = PROTOTYPE_ROOT / "outputs"
DEFAULT_DATA_PATH = OUTPUT_DIRECTORY / "reference_vs_compiled_equivalence.json"

# Declared before compiled results were inspected. These are absolute
# tolerances because a finite-time rate may legitimately be near zero.
RATE_ABSOLUTE_TOLERANCE = 1.0e-8
CYCLE_LOG_ABSOLUTE_TOLERANCE = 5.0e-8
FINAL_REFERENCE_DISTANCE_TOLERANCE = 1.0e-7
FINAL_TANGENT_DISTANCE_TOLERANCE = 1.0e-7
ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE = 1.0e-8

# Center plus four corners of the mechanically selected reference rectangle.
VALIDATION_ANGLE_PAIRS_DEGREES = (
    (179.0, 179.0),
    (169.0, 169.0),
    (169.0, 189.0),
    (189.0, 169.0),
    (189.0, 189.0),
)
BENCHMARK_ANGLE_PAIRS_DEGREES = VALIDATION_ANGLE_PAIRS_DEGREES[:3]


def validation_spec(
    theta1_degrees: float,
    theta2_degrees: float,
) -> RenormalizedTangentSpec:
    """Return one fixed-policy validation specification."""

    return RenormalizedTangentSpec(
        initial_state=EulerLagrangeState.from_degrees(
            theta1_degrees,
            theta2_degrees,
            0.0,
            0.0,
        )
    )


def compare_results(
    reference: RenormalizedTangentResult,
    compiled: RenormalizedTangentResult,
) -> dict[str, object]:
    """Compare one compiled result with its authoritative reference result."""

    metric = CandidateAMetric(
        reference.spec.characteristic_length,
        reference.spec.parameters.gravity,
    )
    reference_state_distance = float(
        metric.distance(
            reference.final_reference_state,
            compiled.final_reference_state,
        )
    )
    tangent_distance = float(
        metric.tangent_norm(
            compiled.final_unit_tangent - reference.final_unit_tangent
        )
    )
    rate_error = abs(
        compiled.finite_time_stretching_rate
        - reference.finite_time_stretching_rate
    )
    cycle_log_error = float(
        np.max(
            np.abs(
                compiled.log_stretch_increment
                - reference.log_stretch_increment
            )
        )
    )
    energy_diagnostic_error = abs(
        compiled.diagnostics.maximum_normalized_reference_energy_drift
        - reference.diagnostics.maximum_normalized_reference_energy_drift
    )
    status_matches = (
        compiled.diagnostics.numerically_valid
        == reference.diagnostics.numerically_valid
        and compiled.diagnostics.validity_issues
        == reference.diagnostics.validity_issues
    )
    accepted = (
        rate_error <= RATE_ABSOLUTE_TOLERANCE
        and cycle_log_error <= CYCLE_LOG_ABSOLUTE_TOLERANCE
        and reference_state_distance <= FINAL_REFERENCE_DISTANCE_TOLERANCE
        and tangent_distance <= FINAL_TANGENT_DISTANCE_TOLERANCE
        and energy_diagnostic_error <= ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
        and status_matches
    )
    return {
        "accepted": accepted,
        "reference_rate_per_second": reference.finite_time_stretching_rate,
        "compiled_rate_per_second": compiled.finite_time_stretching_rate,
        "absolute_rate_error_per_second": rate_error,
        "maximum_cycle_log_absolute_error": cycle_log_error,
        "final_reference_candidate_a_distance": reference_state_distance,
        "final_tangent_candidate_a_distance": tangent_distance,
        "energy_diagnostic_absolute_error": energy_diagnostic_error,
        "reference_numerically_valid": reference.diagnostics.numerically_valid,
        "compiled_numerically_valid": compiled.diagnostics.numerically_valid,
        "reference_solver_function_evaluations": (
            reference.diagnostics.solver_function_evaluations
        ),
        "compiled_solver_function_evaluations": (
            compiled.diagnostics.solver_function_evaluations
        ),
    }


def run_assessment(benchmark_repeats: int = 2) -> dict[str, object]:
    """Run bounded equivalence checks and separate cold/warmed timings."""

    if benchmark_repeats <= 0:
        raise ValueError("benchmark_repeats must be positive.")

    center_spec = validation_spec(*VALIDATION_ANGLE_PAIRS_DEGREES[0])
    first_call_triggered_compilation = not bool(
        compiled_reference_and_tangent_rhs.signatures
    )
    cold_started = perf_counter()
    cold_compiled = run_renormalized_tangent_compiled(center_spec)
    cold_seconds = perf_counter() - cold_started

    comparisons = []
    for index, angle_pair in enumerate(VALIDATION_ANGLE_PAIRS_DEGREES):
        spec = validation_spec(*angle_pair)
        reference = run_renormalized_tangent(spec)
        compiled = (
            cold_compiled
            if index == 0
            else run_renormalized_tangent_compiled(spec)
        )
        comparisons.append(
            {
                "theta1_degrees": angle_pair[0],
                "theta2_degrees": angle_pair[1],
                **compare_results(reference, compiled),
            }
        )

    reference_timings = []
    compiled_timings = []
    for _ in range(benchmark_repeats):
        for angle_pair in BENCHMARK_ANGLE_PAIRS_DEGREES:
            spec = validation_spec(*angle_pair)
            started = perf_counter()
            run_renormalized_tangent(spec)
            reference_timings.append(perf_counter() - started)

            started = perf_counter()
            run_renormalized_tangent_compiled(spec)
            compiled_timings.append(perf_counter() - started)

    reference_median = median(reference_timings)
    compiled_median = median(compiled_timings)
    return {
        "observable": (
            "one-vector Candidate-A fixed-horizon finite-time stretching rate"
        ),
        "asymptotic_convergence_claimed": False,
        "compiled_boundary": "Numba augmented RHS with shared SciPy DOP853 driver",
        "validation_angle_pairs_degrees": [
            list(pair) for pair in VALIDATION_ANGLE_PAIRS_DEGREES
        ],
        "fixed_policy": {
            "duration_seconds": center_spec.duration,
            "renormalization_interval_seconds": (
                center_spec.renormalization_interval
            ),
            "initial_tangent": list(center_spec.initial_tangent),
            "initial_angular_velocities_radians_per_second": [0.0, 0.0],
            "solver_method": center_spec.solver.method,
            "solver_rtol": center_spec.solver.rtol,
            "solver_atol": center_spec.solver.atol,
        },
        "predeclared_absolute_tolerances": {
            "rate_per_second": RATE_ABSOLUTE_TOLERANCE,
            "cycle_log": CYCLE_LOG_ABSOLUTE_TOLERANCE,
            "final_reference_candidate_a_distance": (
                FINAL_REFERENCE_DISTANCE_TOLERANCE
            ),
            "final_tangent_candidate_a_distance": (
                FINAL_TANGENT_DISTANCE_TOLERANCE
            ),
            "energy_diagnostic": ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
        },
        "all_validation_cases_accepted": all(
            comparison["accepted"] for comparison in comparisons
        ),
        "comparisons": comparisons,
        "timing": {
            "first_call_triggered_compilation": first_call_triggered_compilation,
            "cold_first_compiled_evaluation_seconds": cold_seconds,
            "benchmark_angle_pairs_degrees": [
                list(pair) for pair in BENCHMARK_ANGLE_PAIRS_DEGREES
            ],
            "benchmark_repeats": benchmark_repeats,
            "warmed_evaluations_per_path": len(reference_timings),
            "warmed_reference_median_seconds_per_evaluation": reference_median,
            "warmed_compiled_median_seconds_per_evaluation": compiled_median,
            "warmed_speedup": reference_median / compiled_median,
            "estimated_compilation_and_first_call_overhead_seconds": max(
                0.0,
                cold_seconds - compiled_median,
            ),
            "reference_seconds": reference_timings,
            "compiled_seconds": compiled_timings,
        },
    }


def save_assessment(
    assessment: dict[str, object],
    path: Path = DEFAULT_DATA_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        json.dump(assessment, output, indent=2, allow_nan=False)
        output.write("\n")
    return path


def main() -> int:
    assessment = run_assessment()
    save_assessment(assessment)
    return 0 if assessment["all_validation_cases_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
