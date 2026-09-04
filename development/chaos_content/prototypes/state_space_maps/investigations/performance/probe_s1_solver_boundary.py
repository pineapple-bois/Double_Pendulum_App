"""Bounded warm-process profile of the current Lyapunov solver boundary."""

from __future__ import annotations

import argparse
import cProfile
import json
import math
import platform
import pstats
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Sequence
from unittest.mock import patch

import numba
import numpy as np
import scipy


PROBE_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROBE_DIRECTORY / "s1_solver_boundary_profile.json"
OBSERVATION_HORIZONS = (5.0, 20.0)
DEFAULT_REPETITIONS = 5


@dataclass(frozen=True)
class CellCase:
    name: str
    theta1_radians: float
    theta2_radians: float
    t5_route_stratum: str


# Deterministic T=5 route representatives from route_stratified_16_cells.json.
CELL_CASES = (
    CellCase("fast_equilibrium", -math.pi, -math.pi, "compiled_dop853"),
    CellCase(
        "fast_interior",
        -0.5645049299419158,
        -0.4417864669110645,
        "compiled_dop853",
    ),
    CellCase(
        "fallback_near_boundary",
        -3.067961575771282,
        -math.pi,
        "compiled_rhs_solve_ivp_fallback",
    ),
    CellCase(
        "fallback_interior",
        -2.8532042654672924,
        -0.7547185476397353,
        "compiled_rhs_solve_ivp_fallback",
    ),
)


def _specification(case: CellCase, duration: float) -> object:
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
        EulerLagrangeState,
        RenormalizedTangentSpec,
    )

    return RenormalizedTangentSpec(
        initial_state=EulerLagrangeState(
            case.theta1_radians,
            case.theta2_radians,
            0.0,
            0.0,
        ),
        duration=duration,
    )


def _outcome_record(outcome: object) -> dict[str, object]:
    diagnostics = outcome.diagnostics
    return {
        "route": outcome.evaluator,
        "status": outcome.status.value,
        "value_per_second": outcome.value,
        "reported_elapsed_seconds": outcome.elapsed_seconds,
        "returned_segment_count": (
            None if diagnostics is None else diagnostics.segment_count
        ),
        "returned_solver_function_evaluations": (
            None
            if diagnostics is None
            else diagnostics.solver_function_evaluations
        ),
    }


def measure_wall(case: CellCase, duration: float) -> dict[str, object]:
    """Measure existing integration call boundaries with two lightweight timers."""

    from development.chaos_content.prototypes.state_space_maps.src.lyapunov import (
        compiled_dop853 as compiled_dop853_module,
        hybrid as hybrid_module,
        reference as reference_module,
    )

    ode_integrate_seconds: list[float] = []
    solve_ivp_seconds: list[float] = []
    original_ode_integrate = compiled_dop853_module.ode.integrate
    original_solve_ivp = reference_module.solve_ivp
    specification = _specification(case, duration)

    def timed_ode_integrate(integrator: object, *args: object, **kwargs: object) -> object:
        started = perf_counter()
        try:
            return original_ode_integrate(integrator, *args, **kwargs)
        finally:
            ode_integrate_seconds.append(perf_counter() - started)

    def timed_solve_ivp(*args: object, **kwargs: object) -> object:
        started = perf_counter()
        try:
            return original_solve_ivp(*args, **kwargs)
        finally:
            solve_ivp_seconds.append(perf_counter() - started)

    with (
        patch.object(
            compiled_dop853_module.ode,
            "integrate",
            timed_ode_integrate,
        ),
        patch.object(reference_module, "solve_ivp", timed_solve_ivp),
    ):
        started = perf_counter()
        outcome = hybrid_module.evaluate_renormalized_tangent_hybrid(specification)
        total_seconds = perf_counter() - started
    integration_seconds = sum(ode_integrate_seconds) + sum(solve_ivp_seconds)
    return {
        "case": asdict(case),
        "duration_seconds": duration,
        **_outcome_record(outcome),
        "wall_seconds": total_seconds,
        "integration_calls": {
            "compiled_dop853_segment_calls": len(ode_integrate_seconds),
            "compiled_dop853_seconds": sum(ode_integrate_seconds),
            "solve_ivp_segment_calls": len(solve_ivp_seconds),
            "solve_ivp_seconds": sum(solve_ivp_seconds),
            "all_calls_seconds": integration_seconds,
            "outside_calls_seconds": max(0.0, total_seconds - integration_seconds),
        },
    }


def _profile_stat(
    stats: pstats.Stats,
    *,
    function: str | None = None,
    function_contains: str | None = None,
    path_contains: str | None = None,
) -> dict[str, float | int]:
    primitive_calls = 0
    total_calls = 0
    self_seconds = 0.0
    cumulative_seconds = 0.0
    for (filename, _line, function_name), values in stats.stats.items():
        if function is not None and function_name != function:
            continue
        if function_contains is not None and function_contains not in function_name:
            continue
        if path_contains is not None and path_contains not in filename:
            continue
        calls, calls_total, own, cumulative, _callers = values
        primitive_calls += calls
        total_calls += calls_total
        self_seconds += own
        cumulative_seconds += cumulative
    return {
        "primitive_calls": primitive_calls,
        "total_calls": total_calls,
        "self_seconds": self_seconds,
        "cumulative_seconds": cumulative_seconds,
    }


def measure_profile(case: CellCase, duration: float) -> dict[str, object]:
    """Run one additional cell under cProfile for call counts and attribution."""

    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
        evaluate_renormalized_tangent_hybrid,
    )

    specification = _specification(case, duration)
    profiler = cProfile.Profile()
    started = perf_counter()
    profiler.enable()
    outcome = evaluate_renormalized_tangent_hybrid(specification)
    profiler.disable()
    profile_wall_seconds = perf_counter() - started
    stats = pstats.Stats(profiler)
    metrics = {
        "renormalization_driver": _profile_stat(
            stats,
            function="_run_renormalized_tangent_with_rhs",
            path_contains="/lyapunov/reference.py",
        ),
        "compiled_rhs_binding": _profile_stat(
            stats,
            function="evaluate",
            path_contains="/lyapunov/compiled.py",
        ),
        "fast_rhs_counter_callback": _profile_stat(
            stats,
            function="counted_rhs",
            path_contains="/lyapunov/compiled_dop853.py",
        ),
        "accepted_step_observer": _profile_stat(
            stats,
            function="observe",
            path_contains="/lyapunov/compiled_dop853.py",
        ),
        "scipy_solout_bridge": _profile_stat(
            stats,
            function="_solout",
            path_contains="scipy/integrate/_ode.py",
        ),
        "native_dopri853_driver": _profile_stat(
            stats,
            function_contains="scipy.integrate._dop.dopri853",
        ),
        "solve_ivp": _profile_stat(
            stats,
            function="solve_ivp",
            path_contains="scipy/integrate/_ivp/ivp.py",
        ),
        "solve_ivp_rk_step": _profile_stat(
            stats,
            function="rk_step",
            path_contains="scipy/integrate/_ivp/rk.py",
        ),
    }
    return {
        "case": asdict(case),
        "duration_seconds": duration,
        **_outcome_record(outcome),
        "profile_wall_seconds": profile_wall_seconds,
        "metrics": metrics,
    }


def summarize_wall_records(
    records: Sequence[dict[str, object]],
) -> dict[str, object]:
    """Summarize repetitions by observed horizon and route."""

    groups: dict[tuple[float, str], list[dict[str, object]]] = {}
    for record in records:
        key = (float(record["duration_seconds"]), str(record["route"]))
        groups.setdefault(key, []).append(record)

    summaries: dict[str, object] = {}
    for (duration, route), group in sorted(groups.items()):
        wall = [float(record["wall_seconds"]) for record in group]
        integration = [
            float(record["integration_calls"]["all_calls_seconds"])
            for record in group
        ]
        outside = [
            float(record["integration_calls"]["outside_calls_seconds"])
            for record in group
        ]
        summaries[f"T={duration:g}|{route}"] = {
            "measurements": len(group),
            "distinct_cases": len(
                {str(record["case"]["name"]) for record in group}
            ),
            "wall_seconds_mean": mean(wall),
            "wall_seconds_median": median(wall),
            "wall_seconds_minimum": min(wall),
            "wall_seconds_maximum": max(wall),
            "integration_call_seconds_mean": mean(integration),
            "outside_integration_call_seconds_mean": mean(outside),
            "integration_call_wall_fraction": sum(integration) / sum(wall),
            "compiled_dop853_segment_calls_mean": mean(
                float(record["integration_calls"]["compiled_dop853_segment_calls"])
                for record in group
            ),
            "solve_ivp_segment_calls_mean": mean(
                float(record["integration_calls"]["solve_ivp_segment_calls"])
                for record in group
            ),
            "returned_rhs_evaluations_mean": mean(
                float(record["returned_solver_function_evaluations"])
                for record in group
            ),
        }
    return summaries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Investigation-local JSON result path.",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=DEFAULT_REPETITIONS,
        help="Unprofiled wall-time repetitions per case and horizon.",
    )
    return parser


def _git_head() -> str:
    repository_root = Path(__file__).resolve().parents[5]
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.repetitions <= 0:
        raise ValueError("repetitions must be positive.")
    if arguments.output.exists():
        raise FileExistsError(f"Refusing to replace probe evidence: {arguments.output}")

    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
        evaluate_renormalized_tangent_hybrid,
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
        _resolved_interval_max_step,
    )

    warmup_started = perf_counter()
    warmup_records = []
    for duration in OBSERVATION_HORIZONS:
        for case in CELL_CASES:
            warmup = evaluate_renormalized_tangent_hybrid(
                _specification(case, duration)
            )
            warmup_records.append(
                {
                    "case": case.name,
                    "duration_seconds": duration,
                    "route": warmup.evaluator,
                    "status": warmup.status.value,
                }
            )
    warmup_seconds = perf_counter() - warmup_started
    if not all(item["status"] == "completed_valid" for item in warmup_records):
        raise RuntimeError("An excluded process warm-up was not numerically valid.")
    warmup_specification = _specification(
        CELL_CASES[0], OBSERVATION_HORIZONS[0]
    )

    wall_records = [
        measure_wall(case, duration)
        for duration in OBSERVATION_HORIZONS
        for _repeat in range(arguments.repetitions)
        for case in CELL_CASES
    ]
    profile_records = [
        measure_profile(case, duration)
        for duration in OBSERVATION_HORIZONS
        for case in CELL_CASES
    ]
    all_valid = all(record["status"] == "completed_valid" for record in wall_records)
    all_valid = all_valid and all(
        record["status"] == "completed_valid" for record in profile_records
    )
    payload = {
        "probe": "s1_solver_boundary",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "numba": numba.__version__,
        "platform": platform.platform(),
        "git_head": _git_head(),
        "configuration": {
            "observation_horizons_seconds": list(OBSERVATION_HORIZONS),
            "renormalization_interval_seconds": 0.25,
            "sampling_interval_seconds": warmup_specification.sampling_interval,
            "initial_tangent": list(warmup_specification.initial_tangent),
            "physical_parameters": asdict(warmup_specification.parameters),
            "solver": asdict(warmup_specification.solver),
            "resolved_max_step_seconds": _resolved_interval_max_step(
                warmup_specification.solver,
                warmup_specification.characteristic_length,
                warmup_specification.parameters.gravity,
                warmup_specification.renormalization_interval,
            ),
            "energy_drift_limit": warmup_specification.energy_drift_limit,
            "renormalization_norm_tolerance": (
                warmup_specification.renormalization_norm_tolerance
            ),
            "wall_repetitions_per_case_and_horizon": arguments.repetitions,
            "cell_cases": [asdict(case) for case in CELL_CASES],
            "sequential_single_process": True,
            "production_configuration_changed": False,
        },
        "warmup": {
            "excluded_from_measurements": True,
            "seconds": warmup_seconds,
            "cell_horizon_evaluations": warmup_records,
        },
        "measurement_notes": {
            "wall_timers": (
                "perf_counter around the hybrid cell plus exact ode.integrate and "
                "solve_ivp calls; integration-call time includes RHS and observer callbacks"
            ),
            "profile": (
                "one separate cProfile run per case/horizon; profile timings are "
                "reported separately from unprofiled wall measurements"
            ),
            "rhs_count": (
                "returned_solver_function_evaluations covers only the returned route; "
                "compiled_rhs_binding profile calls cover discarded fast attempts and replays too"
            ),
        },
        "wall_records": wall_records,
        "wall_summary_by_horizon_and_route": summarize_wall_records(wall_records),
        "profile_records": profile_records,
        "all_measurements_completed_valid": all_valid,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["wall_summary_by_horizon_and_route"], indent=2))
    print(f"Probe evidence written: {arguments.output}")
    return 0 if all_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
