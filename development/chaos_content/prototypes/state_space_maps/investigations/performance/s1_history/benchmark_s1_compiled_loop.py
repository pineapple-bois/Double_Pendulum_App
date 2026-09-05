"""Bounded same-process, alternating-order warm comparison; never runs a field."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
from statistics import median
import subprocess
from time import perf_counter

import numba
import numpy as np
import scipy

from ....src.lyapunov.s1 import (
    S1_BUILD_FLAGS as BUILD_FLAGS,
    S1_NATIVE_DIRECTORY as NATIVE_DIRECTORY,
    evaluate_renormalized_tangent_s1 as evaluate_compiled_loop,
    run_renormalized_tangent_s1 as run_compiled_loop,
)
from ....src.lyapunov import s1 as promoted_s1_module
from ....src.lyapunov.compiled_dop853 import (
    evaluate_renormalized_tangent_compiled_dop853 as trusted_evaluate,
    run_renormalized_tangent_compiled_dop853 as trusted_run,
)
from ....src.lyapunov.compiled_equivalence import compare_results
from ....src.lyapunov.reference import EulerLagrangeState, RenormalizedTangentSpec

DIRECTORY = Path(__file__).resolve().parent
EVIDENCE_DIRECTORY = DIRECTORY.parent / "evidence" / "s1"
# First two are the exact S1 profile cells. The five additions span the
# successful persisted-fast representatives in route_stratified_16_cells.json.
# Selection is fixed here, independent of prototype accuracy or speed.
CELLS = (
    ("fast_equilibrium", -np.pi, -np.pi),
    ("fast_interior", -0.5645049299419158, -0.4417864669110645),
    ("fast_145_57", -2.791845033951867, -2.2518837966161214),
    ("fast_294_27", -2.9759227284981438, -1.337631247036279),
    ("fast_583_606", 0.5767767762450009, 0.43565054375952217),
    ("fast_729_957", 2.7304858024364416, 1.3314953238847362),
    ("fast_1023_1023", 3.135456730438251, 3.135456730438251),
)
REJECTED_AT_T20 = ("fast_878_958", 2.736621725587984, 2.2457478734645786)


def cell_spec(cell, horizon):
    return RenormalizedTangentSpec(
        initial_state=EulerLagrangeState(cell[1], cell[2], 0.0, 0.0), duration=horizon)


def numerical_comparison(reference, candidate):
    comparison = compare_results(reference, candidate)
    for field in ("stretch_factor", "cumulative_log_stretch", "cumulative_finite_time_rate"):
        comparison[field+"_maximum_absolute_error"] = float(np.max(np.abs(
            getattr(reference, field)-getattr(candidate, field))))
    comparison["cycle_times_identical"] = bool(np.array_equal(
        reference.cycle_end_time, candidate.cycle_end_time))
    comparison["reference_diagnostics"] = asdict(reference.diagnostics)
    comparison["prototype_diagnostics"] = asdict(candidate.diagnostics)
    comparison["nfev_identical"] = (reference.diagnostics.solver_function_evaluations
                                     == candidate.diagnostics.solver_function_evaluations)
    comparison["accepted"] = bool(comparison["accepted"] and
        reference.diagnostics.numerically_valid and candidate.diagnostics.numerically_valid
        and comparison["cycle_times_identical"] and comparison["nfev_identical"])
    return comparison


def run_benchmark(repetitions=11):
    if repetitions < 3:
        raise ValueError("Use at least three paired warm repetitions.")
    rows = []
    # Warm both complete evaluators, all selected cells and both horizons before
    # any timing. Numerical comparisons are independent untimed calls.
    for horizon in (5.0, 20.0):
        for cell in CELLS:
            spec = cell_spec(cell, horizon)
            reference, candidate = trusted_run(spec), run_compiled_loop(spec)
            trusted_evaluate(spec)
            evaluate_compiled_loop(spec)
            rows.append(dict(name=cell[0], horizon=horizon, spec=asdict(spec),
                comparison=numerical_comparison(reference,candidate),
                trusted_seconds=[], prototype_seconds=[]))
    for repetition in range(repetitions):
        # Reverse cell order as well, avoiding a persistent order advantage.
        for row in (rows if repetition % 2 == 0 else rows[::-1]):
            cell = next(cell for cell in CELLS if cell[0] == row["name"])
            spec = cell_spec(cell, row["horizon"])
            calls = [("trusted_seconds", trusted_evaluate),
                     ("prototype_seconds", evaluate_compiled_loop)]
            if repetition % 2:
                calls.reverse()
            for key, evaluator in calls:
                started = perf_counter()
                result = evaluator(spec)
                elapsed = perf_counter()-started
                if result.value is None or not result.diagnostics.numerically_valid:
                    raise RuntimeError(f"Timed evaluation failed: {row['name']}: {result}")
                row[key].append(elapsed)
    for row in rows:
        row["trusted_median_seconds"] = median(row["trusted_seconds"])
        row["prototype_median_seconds"] = median(row["prototype_seconds"])
        row["speedup"] = row["trusted_median_seconds"]/row["prototype_median_seconds"]
    aggregates = {}
    for horizon in (5.0,20.0):
        group = [row for row in rows if row["horizon"] == horizon]
        aggregates[str(horizon)] = dict(
            median_per_cell_speedup=median(row["speedup"] for row in group),
            median_trusted_seconds=median(row["trusted_median_seconds"] for row in group),
            median_prototype_seconds=median(row["prototype_median_seconds"] for row in group))
    rejected = []
    for horizon in (5.0,20.0):
        spec = cell_spec(REJECTED_AT_T20,horizon)
        outputs = {}
        for name, evaluator in (("trusted",trusted_evaluate),("prototype",evaluate_compiled_loop)):
            result = evaluator(spec)
            outputs[name] = dict(status=result.status.value, error=result.error_message)
        rejected.append(dict(name=REJECTED_AT_T20[0], horizon=horizon, outcomes=outputs))
    numerical_pass = all(row["comparison"]["accepted"] for row in rows)
    performance_pass = all(v["median_per_cell_speedup"] >= 1.5 for v in aggregates.values())
    source_files = [Path(__file__), Path(promoted_s1_module.__file__),
                    *sorted(NATIVE_DIRECTORY.iterdir())]
    return dict(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        environment=dict(python=platform.python_version(), platform=platform.platform(),
            numpy=np.__version__, scipy=scipy.__version__, numba=numba.__version__,
            compiler=subprocess.check_output(["clang","--version"],text=True).strip(),
            build_flags=BUILD_FLAGS,
            git_head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()),
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in source_files if p.is_file()},
        protocol=dict(repetitions=repetitions, timing="perf_counter around full evaluator adapter",
            order="paired alternating evaluator order; alternating cell order",
            warmup="both complete evaluators, every cell and horizon, before all timing",
            compilation="excluded; C build once per process in temporary directory",
            aggregate="median of per-cell ratios of median warm evaluator times"),
        cells=rows, aggregates=aggregates, excluded_common_cohort=rejected,
        numerical_pass=numerical_pass, performance_pass=performance_pass,
        recommendation="GO" if numerical_pass and performance_pass else "NO-GO")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=EVIDENCE_DIRECTORY / "s1_compiled_loop_benchmark.json",
    )
    parser.add_argument("--repetitions",type=int,default=11)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new --output path to preserve evidence.")
    results=run_benchmark(args.repetitions)
    args.output.write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:results[k] for k in (
        "aggregates","numerical_pass","performance_pass","recommendation")},indent=2))


if __name__ == "__main__":
    main()
