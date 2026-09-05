"""Measure accepted pool lifecycle costs without generating a field."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from statistics import mean, median
from typing import Sequence

from development.chaos_content.prototypes.state_space_maps.src.generation.runner import (
    EvaluatorBinding,
    ScalarCellTask,
    _close_pool,
    _open_pool,
    accepted_process_execution_spec,
)


def _unused_cell_evaluator(_task: ScalarCellTask) -> object:
    raise RuntimeError("The lifecycle probe must not evaluate field cells.")


def _measure_binding(
    label: str,
    binding: EvaluatorBinding,
    repeats: int,
) -> dict[str, object]:
    execution = accepted_process_execution_spec()
    records: list[dict[str, object]] = []
    for repeat in range(1, repeats + 1):
        executor = None
        closed = False
        try:
            executor, identities, setup_seconds = _open_pool(binding, execution)
            shutdown_seconds, all_workers_stopped = _close_pool(
                executor,
                identities,
            )
            closed = True
        finally:
            if executor is not None and not closed:
                _close_pool(executor, identities)
        warmup_seconds = [identity.warmup_seconds for identity in identities]
        records.append(
            {
                "repeat": repeat,
                "setup_seconds": setup_seconds,
                "shutdown_seconds": shutdown_seconds,
                "worker_warmup_seconds": warmup_seconds,
                "maximum_worker_warmup_seconds": max(warmup_seconds),
                "mean_worker_warmup_seconds": mean(warmup_seconds),
                "all_workers_stopped": all_workers_stopped,
            }
        )
    return {
        "label": label,
        "repeats": records,
        "setup_seconds_mean": mean(
            float(record["setup_seconds"]) for record in records
        ),
        "setup_seconds_median": median(
            float(record["setup_seconds"]) for record in records
        ),
        "shutdown_seconds_mean": mean(
            float(record["shutdown_seconds"]) for record in records
        ),
        "maximum_worker_warmup_seconds_mean": mean(
            float(record["maximum_worker_warmup_seconds"])
            for record in records
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Pool lifetimes to measure for each binding (default: 3).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.repeats <= 0:
        raise ValueError("--repeats must be positive.")

    neutral = EvaluatorBinding(
        name="lifecycle_probe_without_numerical_warmup",
        evaluate_cell=_unused_cell_evaluator,
        execution_routes=("unused_probe_route",),
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
        lyapunov_evaluator_binding,
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
        RenormalizedTangentSpec,
    )

    execution = accepted_process_execution_spec()
    results = {
        "scope": (
            "pool startup, accepted worker initialization/warm-up, identity "
            "handshake, and shutdown only; no field cells or artifacts"
        ),
        "execution_policy": asdict(execution),
        "measurements": [
            _measure_binding("neutral_spawn_handshake", neutral, arguments.repeats),
            _measure_binding(
                "accepted_lyapunov_worker_warmup",
                lyapunov_evaluator_binding(RenormalizedTangentSpec()),
                arguments.repeats,
            ),
        ],
    }
    print(json.dumps(results, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
