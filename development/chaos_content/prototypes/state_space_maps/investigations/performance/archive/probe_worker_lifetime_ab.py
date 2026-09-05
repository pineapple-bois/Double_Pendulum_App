"""Compare accepted 1024-cell recycling with one 2048-cell pool lifetime."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Sequence

from development.chaos_content.prototypes.state_space_maps.src.generation.runner import (
    _close_pool,
    _evaluate_bound_cell,
    _open_pool,
    accepted_process_execution_spec,
)

from .probe_worker_lifetime import (
    _all_correct,
    _correctness_record,
    _current_rss_bytes,
    _expected_by_linear_index,
    _jsonable,
    _load_fast_cells,
    _rss_summary,
    _sha256,
    _task,
)


PROBE_DIRECTORY = Path(__file__).resolve().parent
EVIDENCE_DIRECTORY = PROBE_DIRECTORY.parent / "evidence"
DEFAULT_SELECTION_EVIDENCE = EVIDENCE_DIRECTORY / "s1" / "route_stratified_16_cells.json"
DEFAULT_OUTPUT = EVIDENCE_DIRECTORY / "lifecycle" / "worker_lifetime_ab_2048_cells.json"
POLICY_A = "accepted_recycle_at_1024"
POLICY_B = "candidate_single_2048_lifetime"
PREREGISTERED_ORDER = (
    (1, (POLICY_A, POLICY_B)),
    (2, (POLICY_B, POLICY_A)),
    (3, (POLICY_A, POLICY_B)),
)
CELLS_PER_REPETITION = 2048
BOUNDARY_CELLS = 1024
TILE_BATCH_CELLS = 64
EXPECTED_FAST_CELLS = 8


def _task_stream_digest(tasks: Sequence[object]) -> str:
    payload = [
        (
            task.linear_index,
            task.theta2_index,
            task.theta1_index,
            task.theta2_coordinate,
            task.theta1_coordinate,
        )
        for task in tasks
    ]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _rss_or_raise(process_ids: Sequence[int]) -> dict[str, object]:
    rss = _current_rss_bytes(process_ids)
    if rss["errors_by_pid"]:
        raise RuntimeError(f"Current RSS unavailable: {rss['errors_by_pid']}")
    return rss


def _evaluate_segment(
    executor: object,
    tasks: Sequence[object],
    expected: dict[int, dict[str, object]],
    execution: object,
) -> dict[str, object]:
    if len(tasks) != BOUNDARY_CELLS:
        raise ValueError("Each comparable segment must contain exactly 1024 cells.")

    evaluation_seconds = 0.0
    evaluator_seconds = 0.0
    completed_by_pid: Counter[int] = Counter()
    routes: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    worker_peak: dict[int, int] = {}
    correctness_checks = 0
    correctness_failures = 0
    mismatch_examples: list[dict[str, object]] = []
    observed_tasks: list[object] = []

    for start in range(0, len(tasks), TILE_BATCH_CELLS):
        batch = tasks[start : start + TILE_BATCH_CELLS]
        started = perf_counter()
        outcomes = tuple(
            executor.map(
                _evaluate_bound_cell,
                batch,
                chunksize=execution.chunksize,
            )
        )
        evaluation_seconds += perf_counter() - started
        if len(outcomes) != len(batch):
            raise RuntimeError("Worker pool returned an incomplete 64-cell batch.")
        if tuple(outcome.task for outcome in outcomes) != tuple(batch):
            raise RuntimeError("Worker pool changed the ordered scientific task stream.")

        for outcome in outcomes:
            observed_tasks.append(outcome.task)
            evaluation = outcome.evaluation
            completed_by_pid[outcome.worker_pid] += 1
            routes[evaluation.evaluator] += 1
            statuses[evaluation.status.value] += 1
            evaluator_seconds += evaluation.elapsed_seconds
            worker_peak[outcome.worker_pid] = max(
                worker_peak.get(outcome.worker_pid, 0),
                outcome.worker_peak_rss_bytes,
            )
            check = _correctness_record(outcome, expected)
            correctness_checks += 1
            if not _all_correct(check):
                correctness_failures += 1
                if len(mismatch_examples) < 10:
                    mismatch_examples.append(check)
        del outcomes

    return {
        "completed_cells": len(tasks),
        "tile_batches": len(tasks) // TILE_BATCH_CELLS,
        "evaluation_seconds": evaluation_seconds,
        "cells_per_evaluation_second": len(tasks) / evaluation_seconds,
        "summed_evaluator_seconds": evaluator_seconds,
        "evaluator_occupancy_proxy": (
            evaluator_seconds / (execution.process_width * evaluation_seconds)
        ),
        "completed_by_pid": {
            str(process_id): count
            for process_id, count in sorted(completed_by_pid.items())
        },
        "worker_peak_rss_bytes_by_pid": {
            str(process_id): value
            for process_id, value in sorted(worker_peak.items())
        },
        "route_counts": dict(sorted(routes.items())),
        "status_counts": dict(sorted(statuses.items())),
        "correctness_checks": correctness_checks,
        "correctness_failures": correctness_failures,
        "mismatch_examples": mismatch_examples,
        "observed_task_stream_sha256": _task_stream_digest(observed_tasks),
        "expected_task_stream_sha256": _task_stream_digest(tasks),
    }


def _run_pool(
    segments: Sequence[tuple[int, Sequence[object]]],
    expected: dict[int, dict[str, object]],
    binding: object,
    execution: object,
) -> dict[str, object]:
    executor = None
    identities = ()
    closed = False
    shutdown_seconds = None
    all_workers_stopped = False
    segment_records: list[dict[str, object]] = []
    try:
        executor, identities, setup_seconds = _open_pool(binding, execution)
        process_ids = tuple(identity.process_id for identity in identities)
        ready_raw = _rss_or_raise(process_ids)
        ready_by_pid = {
            str(key): int(value)
            for key, value in ready_raw["rss_bytes_by_pid"].items()
        }
        ready = _rss_summary(ready_raw, ready_by_pid)

        for segment_number, segment_tasks in segments:
            record = _evaluate_segment(
                executor,
                segment_tasks,
                expected,
                execution,
            )
            gc.collect()
            record["segment_number"] = segment_number
            record["pool_completed_cells"] = sum(
                int(item["completed_cells"]) for item in segment_records
            ) + int(record["completed_cells"])
            record["rss_after_segment"] = _rss_summary(
                _rss_or_raise(process_ids),
                ready_by_pid,
            )
            segment_records.append(record)

        shutdown_seconds, all_workers_stopped = _close_pool(executor, identities)
        closed = True
    finally:
        if executor is not None and not closed:
            shutdown_seconds, all_workers_stopped = _close_pool(executor, identities)
            closed = True

    completed_by_pid: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    peak_by_pid: dict[str, int] = {}
    for segment in segment_records:
        completed_by_pid.update(segment["completed_by_pid"])
        route_counts.update(segment["route_counts"])
        status_counts.update(segment["status_counts"])
        for process_id, value in segment["worker_peak_rss_bytes_by_pid"].items():
            peak_by_pid[process_id] = max(peak_by_pid.get(process_id, 0), value)

    evaluation_seconds = sum(
        float(segment["evaluation_seconds"]) for segment in segment_records
    )
    return {
        "setup_seconds": setup_seconds,
        "worker_identities": [_jsonable(identity) for identity in identities],
        "ready_rss": ready,
        "segments": segment_records,
        "evaluation_seconds": evaluation_seconds,
        "completed_cells": sum(
            int(segment["completed_cells"]) for segment in segment_records
        ),
        "completed_by_pid": dict(sorted(completed_by_pid.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "maximum_observed_worker_peak_rss_bytes": max(peak_by_pid.values()),
        "correctness_checks": sum(
            int(segment["correctness_checks"]) for segment in segment_records
        ),
        "correctness_failures": sum(
            int(segment["correctness_failures"]) for segment in segment_records
        ),
        "shutdown_seconds": shutdown_seconds,
        "all_workers_stopped": all_workers_stopped,
        "active_wall_seconds": setup_seconds + evaluation_seconds + shutdown_seconds,
    }


def _run_policy(
    policy: str,
    task_stream: Sequence[object],
    expected: dict[int, dict[str, object]],
    binding: object,
    execution: object,
) -> dict[str, object]:
    first = task_stream[:BOUNDARY_CELLS]
    second = task_stream[BOUNDARY_CELLS:]
    outer_started = perf_counter()
    if policy == POLICY_A:
        pools = [
            _run_pool(((1, first),), expected, binding, execution),
            _run_pool(((2, second),), expected, binding, execution),
        ]
    elif policy == POLICY_B:
        pools = [
            _run_pool(((1, first), (2, second)), expected, binding, execution)
        ]
    else:
        raise ValueError(f"Unknown policy: {policy}")
    outer_wall_seconds = perf_counter() - outer_started

    setup_seconds = sum(float(pool["setup_seconds"]) for pool in pools)
    evaluation_seconds = sum(float(pool["evaluation_seconds"]) for pool in pools)
    shutdown_seconds = sum(float(pool["shutdown_seconds"]) for pool in pools)
    active_wall_seconds = setup_seconds + evaluation_seconds + shutdown_seconds
    routes: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    for pool in pools:
        routes.update(pool["route_counts"])
        statuses.update(pool["status_counts"])

    terminal = pools[-1]["segments"][-1]["rss_after_segment"]
    endpoint_rss = [
        segment["rss_after_segment"]
        for pool in pools
        for segment in pool["segments"]
    ]
    return {
        "policy": policy,
        "pool_lifetimes": len(pools),
        "worker_process_lifetimes": sum(len(pool["worker_identities"]) for pool in pools),
        "completed_cells": sum(int(pool["completed_cells"]) for pool in pools),
        "tile_batches": sum(
            int(segment["tile_batches"])
            for pool in pools
            for segment in pool["segments"]
        ),
        "setup_seconds": setup_seconds,
        "evaluation_seconds": evaluation_seconds,
        "shutdown_seconds": shutdown_seconds,
        "lifecycle_seconds": setup_seconds + shutdown_seconds,
        "active_wall_seconds": active_wall_seconds,
        "outer_wall_seconds_including_observation": outer_wall_seconds,
        "observation_overhead_seconds": outer_wall_seconds - active_wall_seconds,
        "cells_per_evaluation_second": CELLS_PER_REPETITION / evaluation_seconds,
        "cells_per_active_wall_second": CELLS_PER_REPETITION / active_wall_seconds,
        "route_counts": dict(sorted(routes.items())),
        "status_counts": dict(sorted(statuses.items())),
        "correctness_checks": sum(int(pool["correctness_checks"]) for pool in pools),
        "correctness_failures": sum(
            int(pool["correctness_failures"]) for pool in pools
        ),
        "all_workers_stopped": all(bool(pool["all_workers_stopped"]) for pool in pools),
        "terminal_endpoint_median_rss_bytes": terminal["median_rss_bytes"],
        "maximum_endpoint_worker_rss_bytes": max(
            int(endpoint["maximum_rss_bytes"]) for endpoint in endpoint_rss
        ),
        "maximum_observed_worker_peak_rss_bytes": max(
            int(pool["maximum_observed_worker_peak_rss_bytes"]) for pool in pools
        ),
        "pools": pools,
    }


def _summary(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "median": median(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def _build_comparison(runs: Sequence[dict[str, object]]) -> dict[str, object]:
    by_repetition: dict[int, dict[str, dict[str, object]]] = {}
    for run in runs:
        by_repetition.setdefault(int(run["repetition"]), {})[
            str(run["policy"])
        ] = run

    pairs: list[dict[str, object]] = []
    for repetition in sorted(by_repetition):
        accepted = by_repetition[repetition][POLICY_A]
        candidate = by_repetition[repetition][POLICY_B]
        active_saving = (
            float(accepted["active_wall_seconds"])
            - float(candidate["active_wall_seconds"])
        )
        lifecycle_saving = (
            float(accepted["lifecycle_seconds"])
            - float(candidate["lifecycle_seconds"])
        )
        evaluation_difference = (
            float(accepted["evaluation_seconds"])
            - float(candidate["evaluation_seconds"])
        )
        pairs.append(
            {
                "repetition": repetition,
                "accepted_active_wall_seconds": accepted["active_wall_seconds"],
                "candidate_active_wall_seconds": candidate["active_wall_seconds"],
                "candidate_active_wall_saving_seconds": active_saving,
                "candidate_active_wall_saving_fraction_of_accepted": (
                    active_saving / float(accepted["active_wall_seconds"])
                ),
                "accepted_lifecycle_seconds": accepted["lifecycle_seconds"],
                "candidate_lifecycle_seconds": candidate["lifecycle_seconds"],
                "candidate_lifecycle_saving_seconds": lifecycle_saving,
                "accepted_evaluation_seconds": accepted["evaluation_seconds"],
                "candidate_evaluation_seconds": candidate["evaluation_seconds"],
                "accepted_minus_candidate_evaluation_seconds": evaluation_difference,
                "candidate_terminal_additional_rss_bytes": (
                    float(candidate["terminal_endpoint_median_rss_bytes"])
                    - float(accepted["terminal_endpoint_median_rss_bytes"])
                ),
                "candidate_additional_maximum_endpoint_rss_bytes": (
                    int(candidate["maximum_endpoint_worker_rss_bytes"])
                    - int(accepted["maximum_endpoint_worker_rss_bytes"])
                ),
            }
        )

    return {
        "paired_repetitions": pairs,
        "candidate_active_wall_saving_seconds": _summary(
            [float(pair["candidate_active_wall_saving_seconds"]) for pair in pairs]
        ),
        "candidate_active_wall_saving_fraction_of_accepted": _summary(
            [
                float(pair["candidate_active_wall_saving_fraction_of_accepted"])
                for pair in pairs
            ]
        ),
        "candidate_lifecycle_saving_seconds": _summary(
            [float(pair["candidate_lifecycle_saving_seconds"]) for pair in pairs]
        ),
        "accepted_minus_candidate_evaluation_seconds": _summary(
            [
                float(pair["accepted_minus_candidate_evaluation_seconds"])
                for pair in pairs
            ]
        ),
        "candidate_terminal_additional_rss_bytes": _summary(
            [float(pair["candidate_terminal_additional_rss_bytes"]) for pair in pairs]
        ),
        "candidate_additional_maximum_endpoint_rss_bytes": _summary(
            [
                float(pair["candidate_additional_maximum_endpoint_rss_bytes"])
                for pair in pairs
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection-evidence",
        type=Path,
        default=DEFAULT_SELECTION_EVIDENCE,
        help="Existing route-probe JSON supplying eight accepted fast cells.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Investigation-local JSON result path.",
    )
    parser.add_argument(
        "--design-only",
        action="store_true",
        help="Print the fixed ordering and task-stream digest without evaluation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    selected = _load_fast_cells(arguments.selection_evidence)
    if len(selected) != EXPECTED_FAST_CELLS:
        raise ValueError("The A/B probe requires exactly eight fast-route cells.")
    base_tasks = tuple(_task(record) for record in selected)
    task_stream = tuple(
        base_tasks[index % len(base_tasks)] for index in range(CELLS_PER_REPETITION)
    )
    task_stream_sha256 = _task_stream_digest(task_stream)
    design = {
        "question": "accepted 1024-cell recycling versus one 2048-cell lifetime",
        "preregistered_order": [
            {"repetition": repetition, "order": list(order)}
            for repetition, order in PREREGISTERED_ORDER
        ],
        "task_stream": (
            "eight mechanically selected persisted-fast cells repeated cyclically "
            "256 times, split into thirty-two ordered 64-cell batches"
        ),
        "task_stream_sha256": task_stream_sha256,
        "cells_per_policy_repetition": CELLS_PER_REPETITION,
        "tile_batch_cells": TILE_BATCH_CELLS,
        "boundary_cells_pool_total": BOUNDARY_CELLS,
        "policy_a": (
            "two pools: 1024 returned outcomes, shutdown, fresh pool, 1024 outcomes"
        ),
        "policy_b": "one pool: 2048 returned outcomes without midpoint recycling",
        "repetitions_per_policy": 3,
        "measured_scientific_cell_evaluations": 12_288,
        "initializer_warmup_evaluations": {
            POLICY_A: 24,
            POLICY_B: 12,
            "total": 36,
        },
        "selection_evidence_path": str(arguments.selection_evidence),
        "selection_evidence_sha256": _sha256(arguments.selection_evidence),
        "promoted_runner_invoked": False,
        "field_or_persistence_involved": False,
    }
    print(json.dumps(design, indent=2, sort_keys=True), flush=True)
    if arguments.design_only:
        return 0
    if arguments.output.exists():
        raise FileExistsError(f"Refusing to replace probe evidence: {arguments.output}")

    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
        lyapunov_evaluator_binding,
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
        RenormalizedTangentSpec,
    )

    execution = accepted_process_execution_spec()
    binding = lyapunov_evaluator_binding(RenormalizedTangentSpec())
    expected = _expected_by_linear_index(selected)
    runs: list[dict[str, object]] = []
    sequence_number = 0
    for repetition, order in PREREGISTERED_ORDER:
        for order_position, policy in enumerate(order, start=1):
            sequence_number += 1
            run = _run_policy(policy, task_stream, expected, binding, execution)
            run["repetition"] = repetition
            run["order_position_within_repetition"] = order_position
            run["execution_sequence_number"] = sequence_number
            run["expected_full_task_stream_sha256"] = task_stream_sha256
            runs.append(run)

    payload = {
        "probe": "worker_lifetime_ab_1024_vs_2048",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "design": design,
        "runs": runs,
        "comparison": _build_comparison(runs),
        "validation": {
            "run_count": len(runs),
            "policy_counts": dict(Counter(str(run["policy"]) for run in runs)),
            "measured_scientific_cell_evaluations": sum(
                int(run["completed_cells"]) for run in runs
            ),
            "correctness_checks": sum(int(run["correctness_checks"]) for run in runs),
            "correctness_failures": sum(
                int(run["correctness_failures"]) for run in runs
            ),
            "all_workers_stopped": all(
                bool(run["all_workers_stopped"]) for run in runs
            ),
            "all_task_streams_preserved": all(
                segment["observed_task_stream_sha256"]
                == segment["expected_task_stream_sha256"]
                for run in runs
                for pool in run["pools"]
                for segment in pool["segments"]
            ),
            "all_routes_fast": all(
                run["route_counts"] == {"compiled_dop853": CELLS_PER_REPETITION}
                for run in runs
            ),
            "all_statuses_valid": all(
                run["status_counts"] == {"completed_valid": CELLS_PER_REPETITION}
                for run in runs
            ),
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
    accepted = payload["validation"]
    return 0 if all(
        (
            accepted["run_count"] == 6,
            accepted["measured_scientific_cell_evaluations"] == 12_288,
            accepted["correctness_failures"] == 0,
            accepted["all_workers_stopped"],
            accepted["all_task_streams_preserved"],
            accepted["all_routes_fast"],
            accepted["all_statuses_valid"],
        )
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
