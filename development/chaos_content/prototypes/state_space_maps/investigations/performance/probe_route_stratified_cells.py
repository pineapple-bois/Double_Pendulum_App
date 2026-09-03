"""Time 8 fast and 8 fallback cells selected from a persisted field."""

from __future__ import annotations

import argparse
import json
import math
import platform
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Any, Callable, Sequence
from unittest.mock import patch

import h5py
import numpy as np


PROBE_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROBE_DIRECTORY / "route_stratified_16_cells.json"
SAMPLES_PER_STRATUM = 8


def _text(value: object) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


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


def _row_major_rank_positions(population: int) -> tuple[int, ...]:
    if population < SAMPLES_PER_STRATUM:
        raise ValueError(
            f"Each route needs at least {SAMPLES_PER_STRATUM} persisted cells."
        )
    denominator = SAMPLES_PER_STRATUM - 1
    return tuple(
        sample * (population - 1) // denominator
        for sample in range(SAMPLES_PER_STRATUM)
    )


def select_cells(field_path: Path) -> tuple[dict[str, object], ...]:
    """Select evenly ranked cells from each persisted route before timing."""

    with h5py.File(field_path, "r") as source:
        definition = json.loads(_text(source.attrs["definition_json"]))
        route_vocabulary = {
            int(code): label
            for code, label in definition["execution_route_vocabulary"].items()
        }
        route_codes = {label: code for code, label in route_vocabulary.items()}
        fast_route = definition["evaluator_provenance"]["normal_route"]
        fallback_route = definition["evaluator_provenance"]["fallback_route"]
        routes = np.asarray(source["field/execution_route"], dtype=np.uint8)
        theta1 = np.asarray(source["axes/theta1"], dtype=float)
        theta2 = np.asarray(source["axes/theta2"], dtype=float)
        values = np.asarray(source["field/values"], dtype=float)
        statuses = np.asarray(source["field/status"], dtype=np.uint8)
        status_vocabulary = {
            int(code): label
            for code, label in definition["status_vocabulary"].items()
        }

        selected_by_route: dict[str, list[dict[str, object]]] = {}
        for route in (fast_route, fallback_route):
            indices = np.argwhere(routes == route_codes[route])
            positions = _row_major_rank_positions(len(indices))
            selected_by_route[route] = []
            for stratum_rank, position in enumerate(positions):
                theta2_index, theta1_index = (
                    int(value) for value in indices[position]
                )
                selected_by_route[route].append(
                    {
                        "stratum": (
                            "persisted_fast"
                            if route == fast_route
                            else "persisted_fallback"
                        ),
                        "stratum_rank": stratum_rank,
                        "population_rank": position,
                        "population_size": len(indices),
                        "linear_index": theta2_index * routes.shape[1] + theta1_index,
                        "theta2_index": theta2_index,
                        "theta1_index": theta1_index,
                        "theta2_radians": float(theta2[theta2_index]),
                        "theta1_radians": float(theta1[theta1_index]),
                        "persisted_route": route,
                        "persisted_status": status_vocabulary[
                            int(statuses[theta2_index, theta1_index])
                        ],
                        "persisted_value_per_second": float(
                            values[theta2_index, theta1_index]
                        ),
                    }
                )

    interleaved: list[dict[str, object]] = []
    for rank in range(SAMPLES_PER_STRATUM):
        interleaved.append(selected_by_route[fast_route][rank])
        interleaved.append(selected_by_route[fallback_route][rank])
    return tuple(interleaved)


def _outcome_summary(outcome: object | None) -> dict[str, object] | None:
    if outcome is None:
        return None
    return {
        "status": outcome.status.value,
        "evaluator": outcome.evaluator,
        "reported_elapsed_seconds": outcome.elapsed_seconds,
        "error_type": outcome.error_type,
        "error_message": outcome.error_message,
    }


def measure_cell(
    selected: dict[str, object],
    base_spec: object,
) -> dict[str, object]:
    """Time one actual hybrid call at its existing internal call boundaries."""

    from development.chaos_content.prototypes.state_space_maps.src.generation import (
        ScalarCellTask,
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov import (
        hybrid as hybrid_module,
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
        specification_for_cell,
    )

    task = ScalarCellTask(
        linear_index=int(selected["linear_index"]),
        theta2_index=int(selected["theta2_index"]),
        theta1_index=int(selected["theta1_index"]),
        theta2_coordinate=float(selected["theta2_radians"]),
        theta1_coordinate=float(selected["theta1_radians"]),
    )
    specification = specification_for_cell(task, base_spec)
    phase_seconds: dict[str, float] = {}
    phase_outcomes: dict[str, object] = {}

    original_fast = hybrid_module.evaluate_renormalized_tangent_compiled_dop853
    original_verification = hybrid_module._verify_endpoint_max_step_incompatibility
    original_fallback = hybrid_module.evaluate_renormalized_tangent_compiled

    def timed(
        name: str,
        function: Callable[..., object],
    ) -> Callable[..., object]:
        def measure(*args: object, **kwargs: object) -> object:
            started = perf_counter()
            try:
                result = function(*args, **kwargs)
            finally:
                phase_seconds[name] = perf_counter() - started
            phase_outcomes[name] = result
            return result

        return measure

    started = perf_counter()
    with (
        patch.object(
            hybrid_module,
            "evaluate_renormalized_tangent_compiled_dop853",
            timed("compiled_fast_attempt", original_fast),
        ),
        patch.object(
            hybrid_module,
            "_verify_endpoint_max_step_incompatibility",
            timed("fallback_verification_replay", original_verification),
        ),
        patch.object(
            hybrid_module,
            "evaluate_renormalized_tangent_compiled",
            timed("solve_ivp_fallback", original_fallback),
        ),
    ):
        observed = hybrid_module.evaluate_renormalized_tangent_hybrid(specification)
    hybrid_outer_seconds = perf_counter() - started

    fast_outcome = phase_outcomes.get("compiled_fast_attempt")
    fallback_outcome = phase_outcomes.get("solve_ivp_fallback")
    verification = phase_outcomes.get("fallback_verification_replay")
    phase_total = sum(phase_seconds.values())
    persisted_value = float(selected["persisted_value_per_second"])
    observed_value = observed.value
    result = {
        **selected,
        "observed_route": observed.evaluator,
        "observed_status": observed.status.value,
        "observed_value_per_second": observed_value,
        "absolute_value_difference_per_second": (
            None
            if observed_value is None
            else abs(observed_value - persisted_value)
        ),
        "route_agrees": observed.evaluator == selected["persisted_route"],
        "status_agrees": observed.status.value == selected["persisted_status"],
        "timing": {
            "hybrid_outer_seconds": hybrid_outer_seconds,
            "hybrid_reported_seconds": observed.elapsed_seconds,
            "compiled_fast_attempt_seconds": phase_seconds.get(
                "compiled_fast_attempt"
            ),
            "fallback_verification_replay_seconds": phase_seconds.get(
                "fallback_verification_replay"
            ),
            "solve_ivp_fallback_seconds": phase_seconds.get(
                "solve_ivp_fallback"
            ),
            "phase_wrapper_remainder_seconds": max(
                0.0,
                hybrid_outer_seconds - phase_total,
            ),
        },
        "fast_attempt": _outcome_summary(fast_outcome),
        "fallback_execution": _outcome_summary(fallback_outcome),
        "fallback_verification": _jsonable(verification),
        "final_diagnostics": _jsonable(observed.diagnostics),
    }
    return result


def _group_summary(records: Sequence[dict[str, object]]) -> dict[str, object]:
    total = [float(record["timing"]["hybrid_outer_seconds"]) for record in records]

    def phase(name: str) -> list[float]:
        return [
            float(value)
            for record in records
            if (value := record["timing"][name]) is not None
        ]

    return {
        "cell_count": len(records),
        "route_agreement_count": sum(bool(record["route_agrees"]) for record in records),
        "status_agreement_count": sum(
            bool(record["status_agrees"]) for record in records
        ),
        "hybrid_outer_seconds": {
            "mean": mean(total),
            "median": median(total),
            "minimum": min(total),
            "maximum": max(total),
            "standard_deviation_population": math.sqrt(
                mean((value - mean(total)) ** 2 for value in total)
            ),
        },
        "phase_seconds_mean_when_present": {
            name: (mean(values) if (values := phase(name)) else None)
            for name in (
                "compiled_fast_attempt_seconds",
                "fallback_verification_replay_seconds",
                "solve_ivp_fallback_seconds",
                "phase_wrapper_remainder_seconds",
            )
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "field",
        type=Path,
        help="Completed authoritative 1024 HDF5 field to inspect read-only.",
    )
    parser.add_argument(
        "--selection-only",
        action="store_true",
        help="Print the deterministic 8+8 selection without evaluating cells.",
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
    selected = select_cells(arguments.field)
    selection_record = {
        "rule": (
            "Within each persisted route stratum, sort cells in row-major "
            "(theta2_index, theta1_index) order and select population ranks "
            "floor(k * (M - 1) / 7) for k = 0,...,7; evaluate by interleaving "
            "fast and fallback strata at each k."
        ),
        "uses_persisted_timing_for_selection": False,
        "selected_cells": selected,
    }
    print(json.dumps(_jsonable(selection_record), indent=2), flush=True)
    if arguments.selection_only:
        return 0
    if arguments.output.exists():
        raise FileExistsError(f"Refusing to replace probe evidence: {arguments.output}")

    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
        specification_for_cell,
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
        evaluate_renormalized_tangent_hybrid,
    )
    from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
        RenormalizedTangentSpec,
    )

    base_spec = RenormalizedTangentSpec()
    warmup_started = perf_counter()
    warmup = evaluate_renormalized_tangent_hybrid(base_spec)
    warmup_seconds = perf_counter() - warmup_started
    if not warmup.numerically_valid:
        raise RuntimeError("The separate accepted evaluator warm-up was invalid.")

    records = [measure_cell(cell, base_spec) for cell in selected]
    fast_records = [
        record for record in records if record["stratum"] == "persisted_fast"
    ]
    fallback_records = [
        record for record in records if record["stratum"] == "persisted_fallback"
    ]
    if len(fast_records) != 8 or len(fallback_records) != 8:
        raise AssertionError("The probe must measure exactly 8 cells per route.")

    payload = {
        "probe": "route_stratified_16_cells",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "field_path": str(arguments.field),
        "selection": selection_record,
        "warmup": {
            "separate_from_measured_cells": True,
            "cell_count": 1,
            "route": warmup.evaluator,
            "elapsed_seconds": warmup_seconds,
            "specification": _jsonable(base_spec),
        },
        "method": {
            "scientific_cells_measured": 16,
            "execution": "sequential single-process after one separate warm-up",
            "hybrid_entry_point": "evaluate_renormalized_tangent_hybrid",
            "timed_existing_boundaries": [
                "evaluate_renormalized_tangent_compiled_dop853",
                "_verify_endpoint_max_step_incompatibility",
                "evaluate_renormalized_tangent_compiled",
            ],
            "promoted_source_modified": False,
        },
        "cells": records,
        "groups": {
            "persisted_fast": _group_summary(fast_records),
            "persisted_fallback": _group_summary(fallback_records),
        },
        "all_routes_agree": all(bool(record["route_agrees"]) for record in records),
        "all_statuses_agree": all(
            bool(record["status_agrees"]) for record in records
        ),
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(f"Probe evidence written: {arguments.output}", flush=True)
    return 0 if payload["all_routes_agree"] and payload["all_statuses_agree"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
