"""Bounded persisted-field A/B for promoted S1 versus the pre-S1 hybrid."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import tempfile
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Mapping

import h5py
import numba
import numpy as np
import scipy

from ....src.generation import (
    EvaluatorBinding,
    ProcessExecutionSpec,
    accepted_process_execution_spec,
    read_authoritative_field,
    run_scalar_field,
)
from ....src.lyapunov.compiled_equivalence import RATE_ABSOLUTE_TOLERANCE
from ....src.lyapunov.field_adapter import (
    LYAPUNOV_ROUTE_VOCABULARY,
    lyapunov_evaluator_binding,
    periodic_lyapunov_field_definition,
    specification_for_cell,
    summarize_lyapunov_tile,
)
from ....src.lyapunov.hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_ERROR_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
    evaluate_renormalized_tangent_hybrid,
)
from ....src.lyapunov.reference import RenormalizedTangentSpec
from ....src.lyapunov.s1 import (
    S1_EVALUATOR,
    s1_build_provenance,
    s1_build_support,
    s1_specification_eligibility,
)
from ....src.state_space_fields import EvaluationStatus


PERFORMANCE_DIRECTORY = Path(__file__).resolve().parents[1]
PROTOTYPE_DIRECTORY = PERFORMANCE_DIRECTORY.parents[1]
DEFAULT_OUTPUT = (
    PERFORMANCE_DIRECTORY / "evidence" / "current" / "s1_field_level_benchmark_64.json"
)
TRUSTED_ROUTE_VOCABULARY = LYAPUNOV_ROUTE_VOCABULARY[:-1]
_TRUSTED_SPEC: RenormalizedTangentSpec | None = None


def initialize_trusted_field_worker(base_spec: RenormalizedTangentSpec) -> None:
    """Warm exactly the retained pre-S1 operational hybrid."""

    global _TRUSTED_SPEC
    _TRUSTED_SPEC = base_spec
    warm = evaluate_renormalized_tangent_hybrid(base_spec)
    if warm.status is not EvaluationStatus.COMPLETED_VALID:
        raise RuntimeError("Trusted Lyapunov worker warm-up was not valid.")


def evaluate_trusted_field_cell(task):
    """Evaluate one field cell through the unchanged pre-S1 hybrid."""

    if _TRUSTED_SPEC is None:
        raise RuntimeError("Trusted Lyapunov field worker was not initialized.")
    return evaluate_renormalized_tangent_hybrid(
        specification_for_cell(task, _TRUSTED_SPEC)
    )


def trusted_evaluator_binding(
    spec: RenormalizedTangentSpec,
) -> EvaluatorBinding:
    return EvaluatorBinding(
        name="forced_pre_s1_targeted_hybrid_lyapunov",
        initialize_worker=initialize_trusted_field_worker,
        initializer_arguments=(spec,),
        evaluate_cell=evaluate_trusted_field_cell,
        execution_routes=tuple(
            label for code, label in TRUSTED_ROUTE_VOCABULARY if code
        ),
        summarize_tile=summarize_lyapunov_tile,
    )


def trusted_field_definition(samples: int, spec: RenormalizedTangentSpec):
    promoted = periodic_lyapunov_field_definition(samples, spec)
    return replace(
        promoted,
        evaluator_provenance={
            "policy": "forced_pre_s1_targeted_hybrid",
            "normal_route": HYBRID_FAST_EVALUATOR,
            "fallback_route": HYBRID_FALLBACK_EVALUATOR,
            "bounded_error_route": HYBRID_FAST_ERROR_EVALUATOR,
            "scientific_oracles": [
                "numpy_sympy_solve_ivp",
                "numba_rhs_jvp_solve_ivp",
            ],
        },
        route_vocabulary=TRUSTED_ROUTE_VOCABULARY,
    )


def _decode(value: object) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tile_totals(path: Path) -> dict[str, object]:
    attempted: Counter[str] = Counter()
    recoveries: Counter[str] = Counter()
    rhs_evaluations = 0
    with h5py.File(path, "r") as source:
        metadata = json.loads(_decode(source.attrs["definition_json"]))
        for encoded in source["tiles/diagnostics_json"]:
            diagnostics = json.loads(_decode(encoded))
            rhs_evaluations += int(diagnostics["solver_function_evaluations"])
            attempted.update(diagnostics.get("attempted_evaluator_counts", {}))
            recoveries.update(diagnostics.get("recovery_reason_counts", {}))
    return {
        "retained_result_rhs_evaluations": rhs_evaluations,
        "attempted_evaluator_counts": dict(sorted(attempted.items())),
        "recovery_reason_counts": dict(sorted(recoveries.items())),
        "evaluator_provenance": metadata["evaluator_provenance"],
    }


def _summary_record(summary, outer_wall_seconds: float) -> dict[str, object]:
    return {
        "outer_create_wall_seconds": outer_wall_seconds,
        "outer_create_cells_per_second": summary.evaluated_cells
        / outer_wall_seconds,
        "runner_total_seconds": summary.total_seconds,
        "runner_cells_per_second": summary.cells_per_second,
        "setup_seconds": summary.setup_seconds,
        "evaluation_seconds": summary.evaluation_seconds,
        "persistence_seconds": summary.persistence_seconds,
        "shutdown_seconds": summary.shutdown_seconds,
        "pool_count": summary.pool_count,
        "recycling_events": summary.recycling_events,
        "all_workers_stopped": summary.all_workers_stopped,
        "maximum_worker_peak_rss_bytes": summary.maximum_worker_peak_rss_bytes,
        "coordinator_peak_rss_bytes": summary.coordinator_peak_rss_bytes,
        "artifact_bytes": summary.artifact_bytes,
        "route_counts": summary.validation.route_counts,
        "status_counts": summary.validation.status_counts,
        "validation_accepted": summary.validation.accepted,
    }


def _route_labels(snapshot) -> dict[int, str]:
    return {
        int(code): label
        for code, label in snapshot.metadata[
            "execution_route_vocabulary"
        ].items()
    }


def _route_mask(snapshot, label: str) -> np.ndarray:
    vocabulary = _route_labels(snapshot)
    code = next(code for code, candidate in vocabulary.items() if candidate == label)
    return snapshot.execution_route == code


def _compare_fields(promoted, trusted) -> dict[str, object]:
    axes_identical = bool(
        np.array_equal(promoted.theta1_axis, trusted.theta1_axis)
        and np.array_equal(promoted.theta2_axis, trusted.theta2_axis)
    )
    statuses_identical = bool(np.array_equal(promoted.status, trusted.status))
    values_exact = bool(
        np.array_equal(promoted.values, trusted.values, equal_nan=True)
    )
    finite = np.isfinite(promoted.values) & np.isfinite(trusted.values)
    differences = np.abs(promoted.values[finite] - trusted.values[finite])
    maximum_difference = float(np.max(differences)) if differences.size else 0.0
    promoted_fallback = _route_mask(promoted, HYBRID_FALLBACK_EVALUATOR)
    trusted_fallback = _route_mask(trusted, HYBRID_FALLBACK_EVALUATOR)
    promoted_s1 = _route_mask(promoted, S1_EVALUATOR)
    trusted_fast = _route_mask(trusted, HYBRID_FAST_EVALUATOR)
    return {
        "axes_identical": axes_identical,
        "statuses_identical": statuses_identical,
        "values_bitwise_identical_including_nan": values_exact,
        "maximum_absolute_value_difference_per_second": maximum_difference,
        "existing_rate_absolute_tolerance_per_second": RATE_ABSOLUTE_TOLERANCE,
        "cells_exceeding_tolerance": int(
            np.count_nonzero(differences > RATE_ABSOLUTE_TOLERANCE)
        ),
        "fallback_masks_identical": bool(
            np.array_equal(promoted_fallback, trusted_fallback)
        ),
        "promoted_s1_mask_matches_trusted_fast_mask": bool(
            np.array_equal(promoted_s1, trusted_fast)
        ),
        "accepted": bool(
            axes_identical
            and statuses_identical
            and maximum_difference <= RATE_ABSOLUTE_TOLERANCE
            and np.array_equal(promoted_fallback, trusted_fallback)
            and np.array_equal(promoted_s1, trusted_fast)
        ),
    }


def _git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def run_benchmark(
    samples_per_axis: int,
    duration: float,
    work_directory: Path,
) -> dict[str, object]:
    spec = RenormalizedTangentSpec(duration=duration)
    eligibility = s1_specification_eligibility(spec)
    support = s1_build_support()
    if not eligibility.eligible:
        raise RuntimeError(f"Benchmark specification is not S1 eligible: {eligibility}")
    if not support.supported:
        raise RuntimeError(f"This is not a validated S1 build: {support.reason}")

    execution = accepted_process_execution_spec()
    promoted_definition = periodic_lyapunov_field_definition(samples_per_axis, spec)
    trusted_definition = trusted_field_definition(samples_per_axis, spec)
    if (
        promoted_definition.theta1_axis != trusted_definition.theta1_axis
        or promoted_definition.theta2_axis != trusted_definition.theta2_axis
        or promoted_definition.physical_parameters
        != trusted_definition.physical_parameters
        or promoted_definition.numerical_parameters
        != trusted_definition.numerical_parameters
    ):
        raise AssertionError("A/B definitions do not share the same grid and spec.")

    promoted_path = work_directory / "promoted_s1.h5"
    trusted_path = work_directory / "trusted_pre_s1.h5"
    promoted_started = perf_counter()
    promoted_summary = run_scalar_field(
        promoted_path,
        promoted_definition,
        lyapunov_evaluator_binding(spec),
        execution=execution,
        mode="create",
    )
    promoted_outer = perf_counter() - promoted_started

    trusted_started = perf_counter()
    trusted_summary = run_scalar_field(
        trusted_path,
        trusted_definition,
        trusted_evaluator_binding(spec),
        execution=execution,
        mode="create",
    )
    trusted_outer = perf_counter() - trusted_started

    promoted_snapshot = read_authoritative_field(promoted_path)
    trusted_snapshot = read_authoritative_field(trusted_path)
    comparison = _compare_fields(promoted_snapshot, trusted_snapshot)
    if not comparison["accepted"]:
        raise RuntimeError(f"Persisted field comparison failed: {comparison}")

    sources = (
        Path(__file__),
        PROTOTYPE_DIRECTORY / "src" / "lyapunov" / "operational.py",
        PROTOTYPE_DIRECTORY / "src" / "lyapunov" / "s1.py",
        PROTOTYPE_DIRECTORY / "src" / "lyapunov" / "hybrid.py",
        PROTOTYPE_DIRECTORY / "src" / "generation" / "runner.py",
    )
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "bounded operational S1 versus forced pre-S1 field A/B",
        "order": ["promoted_s1", "trusted_pre_s1"],
        "workload": {
            "samples_per_axis": samples_per_axis,
            "field_shape_theta2_theta1": list(promoted_definition.field_shape),
            "cell_count": samples_per_axis**2,
            "duration_seconds": duration,
            "tile_shape_theta2_theta1": list(
                promoted_definition.nominal_tile_shape
            ),
            "physical_parameters": dict(promoted_definition.physical_parameters),
            "numerical_parameters": dict(promoted_definition.numerical_parameters),
            "multiprocessing_policy": asdict(execution),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "numba": numba.__version__,
            "git_head": _git_output("rev-parse", "HEAD"),
            "git_status_short_before_artifact": _git_output("status", "--short"),
            "s1_build": s1_build_provenance(),
        },
        "promoted_s1": {
            **_summary_record(promoted_summary, promoted_outer),
            **_tile_totals(promoted_path),
            "hdf5_sha256": _sha256(promoted_path),
        },
        "trusted_pre_s1": {
            **_summary_record(trusted_summary, trusted_outer),
            **_tile_totals(trusted_path),
            "hdf5_sha256": _sha256(trusted_path),
        },
        "speedup": {
            "outer_create_wall": trusted_outer / promoted_outer,
            "runner_total": trusted_summary.total_seconds
            / promoted_summary.total_seconds,
            "tile_evaluation": trusted_summary.evaluation_seconds
            / promoted_summary.evaluation_seconds,
        },
        "persisted_comparison": comparison,
        "source_sha256": {str(path): _sha256(path) for path in sources},
    }


def save(payload: Mapping[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as target:
        json.dump(payload, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-axis", type=int, default=64)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--work-directory",
        type=Path,
        help="Optional empty directory in which to retain both HDF5 fields.",
    )
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    if options.samples_per_axis <= 0:
        raise ValueError("samples-per-axis must be positive")
    if options.output.exists():
        raise FileExistsError(f"Refusing to replace benchmark: {options.output}")
    if options.work_directory is None:
        with tempfile.TemporaryDirectory(prefix="s1-field-ab-") as directory:
            payload = run_benchmark(
                options.samples_per_axis,
                options.duration,
                Path(directory),
            )
    else:
        options.work_directory.mkdir(parents=True, exist_ok=False)
        payload = run_benchmark(
            options.samples_per_axis,
            options.duration,
            options.work_directory,
        )
    save(payload, options.output)
    print(json.dumps({
        "output": str(options.output),
        "speedup": payload["speedup"],
        "persisted_comparison": payload["persisted_comparison"],
        "promoted_routes": payload["promoted_s1"]["route_counts"],
        "trusted_routes": payload["trusted_pre_s1"]["route_counts"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
