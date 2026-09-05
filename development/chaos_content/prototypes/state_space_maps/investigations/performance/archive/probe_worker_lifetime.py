"""Measure current accepted workers across one bounded extended pool lifetime."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import resource
import subprocess
from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Sequence

import numpy as np

from development.chaos_content.prototypes.state_space_maps.src.generation.runner import (
    ScalarCellTask,
    _close_pool,
    _evaluate_bound_cell,
    _open_pool,
    accepted_process_execution_spec,
)


PROBE_DIRECTORY = Path(__file__).resolve().parent
EVIDENCE_DIRECTORY = PROBE_DIRECTORY.parent / "evidence"
DEFAULT_SELECTION_EVIDENCE = EVIDENCE_DIRECTORY / "s1" / "route_stratified_16_cells.json"
DEFAULT_OUTPUT = EVIDENCE_DIRECTORY / "lifecycle" / "worker_lifetime_4096_cells.json"
CHECKPOINTS = (256, 512, 1024, 2048, 4096)
EXPECTED_FAST_CELLS = 8


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _current_rss_bytes(process_ids: Sequence[int]) -> dict[str, object]:
    values: dict[str, int] = {}
    errors: dict[str, str] = {}
    for process_id in process_ids:
        try:
            completed = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(process_id)],
                check=True,
                capture_output=True,
                text=True,
            )
            values[str(process_id)] = int(completed.stdout.strip()) * 1024
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            errors[str(process_id)] = f"{type(error).__name__}: {error}"
    return {"rss_bytes_by_pid": values, "errors_by_pid": errors}


def _coordinator_memory() -> dict[str, int]:
    current = _current_rss_bytes((os.getpid(),))
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if platform.system() != "Darwin":
        peak *= 1024
    return {
        "current_rss_bytes": int(
            current["rss_bytes_by_pid"].get(str(os.getpid()), -1)
        ),
        "peak_rss_bytes": peak,
    }


def _load_fast_cells(path: Path) -> tuple[dict[str, object], ...]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    records = [
        record
        for record in evidence["cells"]
        if record["stratum"] == "persisted_fast"
    ]
    if len(records) != EXPECTED_FAST_CELLS:
        raise ValueError(
            f"Expected {EXPECTED_FAST_CELLS} fast-route cells, found {len(records)}."
        )
    if not all(record["route_agrees"] and record["status_agrees"] for record in records):
        raise ValueError("Selection evidence contains a route or status disagreement.")
    return tuple(records)


def _task(record: dict[str, object]) -> ScalarCellTask:
    return ScalarCellTask(
        linear_index=int(record["linear_index"]),
        theta2_index=int(record["theta2_index"]),
        theta1_index=int(record["theta1_index"]),
        theta2_coordinate=float(record["theta2_radians"]),
        theta1_coordinate=float(record["theta1_radians"]),
    )


def _diagnostic_signature(value: object) -> object:
    return _jsonable(value)


def _expected_by_linear_index(
    records: Sequence[dict[str, object]],
) -> dict[int, dict[str, object]]:
    return {
        int(record["linear_index"]): {
            "status": record["observed_status"],
            "route": record["observed_route"],
            "value": record["observed_value_per_second"],
            "diagnostics": record["final_diagnostics"],
            "validity_issues": [],
            "error_type": None,
            "error_message": None,
        }
        for record in records
    }


def _correctness_record(
    outcome: object,
    expected: dict[int, dict[str, object]],
) -> dict[str, object]:
    reference = expected[outcome.task.linear_index]
    evaluation = outcome.evaluation
    value_difference = (
        None
        if evaluation.value is None or reference["value"] is None
        else abs(float(evaluation.value) - float(reference["value"]))
    )
    return {
        "linear_index": outcome.task.linear_index,
        "worker_pid": outcome.worker_pid,
        "status_agrees": evaluation.status.value == reference["status"],
        "route_agrees": evaluation.evaluator == reference["route"],
        "value_agrees_exactly": evaluation.value == reference["value"],
        "absolute_value_difference": value_difference,
        "diagnostics_agree_exactly": (
            _diagnostic_signature(evaluation.diagnostics)
            == reference["diagnostics"]
        ),
        "issues_agree_exactly": list(evaluation.validity_issues)
        == reference["validity_issues"],
        "error_agrees_exactly": (
            evaluation.error_type == reference["error_type"]
            and evaluation.error_message == reference["error_message"]
        ),
    }


def _all_correct(record: dict[str, object]) -> bool:
    return all(
        bool(record[key])
        for key in (
            "status_agrees",
            "route_agrees",
            "value_agrees_exactly",
            "diagnostics_agree_exactly",
            "issues_agree_exactly",
            "error_agrees_exactly",
        )
    )


def _rss_summary(
    snapshot: dict[str, object],
    ready: dict[str, int],
) -> dict[str, object]:
    current = {
        str(key): int(value)
        for key, value in snapshot["rss_bytes_by_pid"].items()
    }
    deltas = {
        process_id: value - ready[process_id]
        for process_id, value in current.items()
        if process_id in ready
    }
    values = list(current.values())
    return {
        "rss_bytes_by_pid": current,
        "errors_by_pid": snapshot["errors_by_pid"],
        "delta_from_ready_bytes_by_pid": deltas,
        "minimum_rss_bytes": min(values) if values else None,
        "median_rss_bytes": median(values) if values else None,
        "maximum_rss_bytes": max(values) if values else None,
        "median_delta_from_ready_bytes": median(deltas.values()) if deltas else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection-evidence",
        type=Path,
        default=DEFAULT_SELECTION_EVIDENCE,
        help="Existing 8+8 route-probe JSON used to obtain eight accepted fast cells.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Investigation-local JSON result path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.output.exists():
        raise FileExistsError(f"Refusing to replace probe evidence: {arguments.output}")

    selected = _load_fast_cells(arguments.selection_evidence)
    tasks = tuple(_task(record) for record in selected)
    expected = _expected_by_linear_index(selected)

    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
        lyapunov_evaluator_binding,
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
        RenormalizedTangentSpec,
    )

    execution = accepted_process_execution_spec()
    binding = lyapunov_evaluator_binding(RenormalizedTangentSpec())
    executor = None
    closed = False
    setup_seconds = None
    shutdown_seconds = None
    all_workers_stopped = False
    identities = ()
    checkpoints: list[dict[str, object]] = []
    mismatch_examples: list[dict[str, object]] = []
    cumulative_counts: Counter[int] = Counter()
    cumulative_peak: dict[int, int] = {}
    total_evaluator_seconds = 0.0
    correctness_checks = 0
    correctness_failures = 0

    try:
        executor, identities, setup_seconds = _open_pool(binding, execution)
        process_ids = tuple(identity.process_id for identity in identities)
        ready_raw = _current_rss_bytes(process_ids)
        if ready_raw["errors_by_pid"]:
            raise RuntimeError(f"Current RSS unavailable: {ready_raw['errors_by_pid']}")
        ready_by_pid = {
            str(key): int(value)
            for key, value in ready_raw["rss_bytes_by_pid"].items()
        }
        checkpoints.append(
            {
                "completed_cells_pool_total": 0,
                "window_cells": 0,
                "window_seconds": None,
                "window_cells_per_second": None,
                "window_mean_evaluator_seconds": None,
                "window_evaluator_occupancy_proxy": None,
                "cumulative_completed_by_pid": {
                    str(process_id): 0 for process_id in process_ids
                },
                "rss": _rss_summary(ready_raw, ready_by_pid),
                "coordinator_memory": _coordinator_memory(),
            }
        )

        completed = 0
        for target in CHECKPOINTS:
            window_cells = target - completed
            repeated_tasks = tuple(
                tasks[index % len(tasks)] for index in range(window_cells)
            )
            started = perf_counter()
            outcomes = tuple(
                executor.map(
                    _evaluate_bound_cell,
                    repeated_tasks,
                    chunksize=execution.chunksize,
                )
            )
            window_seconds = perf_counter() - started
            if len(outcomes) != window_cells:
                raise RuntimeError("Worker pool returned an incomplete checkpoint.")

            window_counts: Counter[int] = Counter()
            window_evaluator_seconds = 0.0
            window_peak: dict[int, int] = {}
            for outcome in outcomes:
                window_counts[outcome.worker_pid] += 1
                cumulative_counts[outcome.worker_pid] += 1
                window_peak[outcome.worker_pid] = max(
                    window_peak.get(outcome.worker_pid, 0),
                    outcome.worker_peak_rss_bytes,
                )
                cumulative_peak[outcome.worker_pid] = max(
                    cumulative_peak.get(outcome.worker_pid, 0),
                    outcome.worker_peak_rss_bytes,
                )
                window_evaluator_seconds += outcome.evaluation.elapsed_seconds
                total_evaluator_seconds += outcome.evaluation.elapsed_seconds
                check = _correctness_record(outcome, expected)
                correctness_checks += 1
                if not _all_correct(check):
                    correctness_failures += 1
                    if len(mismatch_examples) < 10:
                        mismatch_examples.append(check)

            completed = target
            del outcomes
            gc.collect()
            rss = _current_rss_bytes(process_ids)
            checkpoint = {
                "completed_cells_pool_total": completed,
                "window_cells": window_cells,
                "window_seconds": window_seconds,
                "window_cells_per_second": window_cells / window_seconds,
                "window_mean_evaluator_seconds": (
                    window_evaluator_seconds / window_cells
                ),
                "window_evaluator_occupancy_proxy": (
                    window_evaluator_seconds
                    / (execution.process_width * window_seconds)
                ),
                "window_completed_by_pid": {
                    str(process_id): window_counts[process_id]
                    for process_id in process_ids
                },
                "cumulative_completed_by_pid": {
                    str(process_id): cumulative_counts[process_id]
                    for process_id in process_ids
                },
                "window_peak_rss_bytes_by_pid": {
                    str(process_id): window_peak.get(process_id)
                    for process_id in process_ids
                },
                "cumulative_peak_rss_bytes_by_pid": {
                    str(process_id): cumulative_peak.get(process_id)
                    for process_id in process_ids
                },
                "rss": _rss_summary(rss, ready_by_pid),
                "coordinator_memory": _coordinator_memory(),
            }
            checkpoints.append(checkpoint)
            print(
                f"{completed:4d} cells | "
                f"{checkpoint['window_cells_per_second']:.1f} cells/s | "
                f"median worker RSS {checkpoint['rss']['median_rss_bytes'] / 2**20:.1f} MiB",
                flush=True,
            )
    finally:
        if executor is not None and not closed:
            shutdown_seconds, all_workers_stopped = _close_pool(executor, identities)
            closed = True

    final_rss = checkpoints[-1]["rss"]
    first_work_rss = checkpoints[1]["rss"]
    payload = {
        "probe": "accepted_worker_lifetime",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "scope": (
            "one initialized accepted four-worker pool; no field, persistence, "
            "generation, or resume"
        ),
        "selection_evidence": {
            "path": str(arguments.selection_evidence),
            "sha256": _sha256(arguments.selection_evidence),
            "rule": (
                "cycle the eight mechanically selected, persisted-fast cells from "
                "the completed route-stratified probe"
            ),
            "selected_cells": [
                {
                    "linear_index": int(record["linear_index"]),
                    "theta2_index": int(record["theta2_index"]),
                    "theta1_index": int(record["theta1_index"]),
                    "theta2_radians": float(record["theta2_radians"]),
                    "theta1_radians": float(record["theta1_radians"]),
                    "route": record["observed_route"],
                    "status": record["observed_status"],
                    "value_per_second": record["observed_value_per_second"],
                }
                for record in selected
            ],
        },
        "design": {
            "checkpoints_pool_completed_cells": list(CHECKPOINTS),
            "checkpoint_rationale": (
                "retain Experiment 017 checkpoints through 2048 pool-wide cells "
                "and add one predeclared doubling to 4096 to distinguish continued "
                "growth from an early plateau in the promoted hybrid worker"
            ),
            "task_stream": (
                "non-rectangular repetition of eight accepted fast-route scientific cells"
            ),
            "process_width": execution.process_width,
            "chunksize": execution.chunksize,
            "start_method": execution.start_method,
            "production_recycling_limit_not_applied": True,
            "operational_field_cell_fraction": CHECKPOINTS[-1] / (1024 * 1024),
            "warmup_scientific_evaluations": execution.process_width,
            "measured_scientific_evaluations": CHECKPOINTS[-1],
            "total_scientific_evaluations": (
                execution.process_width + CHECKPOINTS[-1]
            ),
        },
        "measurement": {
            "rss_method": "ps -o rss= -p PID (KiB converted to bytes)",
            "peak_rss_method": (
                "worker-reported resource.getrusage(RUSAGE_SELF).ru_maxrss, "
                "platform-normalized by promoted worker wrapper"
            ),
            "setup_seconds_including_worker_warmup_and_handshake": setup_seconds,
            "worker_identities": [_jsonable(identity) for identity in identities],
            "checkpoints": checkpoints,
            "total_evaluator_seconds": total_evaluator_seconds,
            "shutdown_seconds": shutdown_seconds,
            "all_workers_stopped": all_workers_stopped,
        },
        "correctness": {
            "checks": correctness_checks,
            "failures": correctness_failures,
            "all_routes_statuses_values_diagnostics_stable": (
                correctness_failures == 0
            ),
            "mismatch_examples": mismatch_examples,
        },
        "derived": {
            "ready_median_rss_bytes": checkpoints[0]["rss"]["median_rss_bytes"],
            "after_first_checkpoint_median_rss_bytes": first_work_rss[
                "median_rss_bytes"
            ],
            "final_median_rss_bytes": final_rss["median_rss_bytes"],
            "ready_to_final_median_growth_bytes": final_rss[
                "median_delta_from_ready_bytes"
            ],
            "first_checkpoint_to_final_median_growth_bytes": (
                final_rss["median_rss_bytes"]
                - first_work_rss["median_rss_bytes"]
            ),
            "cumulative_completed_cells_by_pid": {
                str(identity.process_id): cumulative_counts[identity.process_id]
                for identity in identities
            },
        },
        "promoted_implementation_modified": False,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(f"Probe evidence written: {arguments.output}", flush=True)
    return 0 if all_workers_stopped and correctness_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
