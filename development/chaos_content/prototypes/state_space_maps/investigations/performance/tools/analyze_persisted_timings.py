"""Read persisted field timing evidence without invoking field dynamics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import h5py
import numpy as np


def _text(value: object) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _quantiles(values: np.ndarray) -> dict[str, float]:
    levels = (0, 50, 90, 95, 99, 100)
    measured = np.percentile(values, levels)
    return {
        f"p{level:02d}": float(value)
        for level, value in zip(levels, measured, strict=True)
    }


def _tile_group(
    tile_wall_seconds: np.ndarray,
    summed_evaluator_seconds: np.ndarray,
    mask: np.ndarray,
) -> dict[str, float | int] | None:
    if not np.any(mask):
        return None
    return {
        "tile_count": int(np.count_nonzero(mask)),
        "tile_wall_seconds_total": float(np.sum(tile_wall_seconds[mask])),
        "tile_wall_seconds_mean": float(np.mean(tile_wall_seconds[mask])),
        "tile_wall_seconds_p50": float(np.median(tile_wall_seconds[mask])),
        "summed_evaluator_seconds_total": float(
            np.sum(summed_evaluator_seconds[mask])
        ),
        "summed_evaluator_seconds_mean_per_tile": float(
            np.mean(summed_evaluator_seconds[mask])
        ),
    }


def analyze_field(path: Path) -> dict[str, object]:
    """Return measurements and direct derivations from one persisted HDF5 field."""

    with h5py.File(path, "r") as source:
        definition = json.loads(_text(source.attrs["definition_json"]))
        route_vocabulary = {
            int(code): label
            for code, label in definition["execution_route_vocabulary"].items()
        }
        status_vocabulary = {
            int(code): label
            for code, label in definition["status_vocabulary"].items()
        }
        field_routes = np.asarray(source["field/execution_route"], dtype=np.uint8)
        field_status = np.asarray(source["field/status"], dtype=np.uint8)
        tile_wall_seconds = np.asarray(
            source["tiles/evaluation_seconds"], dtype=float
        )
        diagnostics = tuple(
            json.loads(_text(value))
            for value in source["tiles/diagnostics_json"][:]
        )
        summed_evaluator_seconds = np.asarray(
            [item["summed_evaluator_seconds"] for item in diagnostics],
            dtype=float,
        )
        solver_function_evaluations = np.asarray(
            [item["solver_function_evaluations"] for item in diagnostics],
            dtype=np.int64,
        )
        fallback_route = definition["evaluator_provenance"]["fallback_route"]
        fallback_cells_per_tile = np.asarray(
            [item["route_counts"].get(fallback_route, 0) for item in diagnostics],
            dtype=np.int64,
        )
        first_provenance = json.loads(
            _text(source["tiles/provenance_json"][0])
        )
        process_policy = first_provenance["execution_policy"]
        process_width = int(process_policy["process_width"])
        shape = tuple(int(value) for value in source["field/values"].shape)
        cell_count = int(np.prod(shape))
        tile_wall_total = float(np.sum(tile_wall_seconds))
        evaluator_total = float(np.sum(summed_evaluator_seconds))
        fast_only = fallback_cells_per_tile == 0
        has_fallback = ~fast_only

        association: dict[str, float | int | None] = {
            "fallback_cell_count": int(np.sum(fallback_cells_per_tile)),
            "fallback_fraction": float(
                np.sum(fallback_cells_per_tile) / cell_count
            ),
            "fallback_containing_tile_count": int(np.count_nonzero(has_fallback)),
            "maximum_fallback_cells_per_tile": int(
                np.max(fallback_cells_per_tile)
            ),
            "fallback_count_tile_wall_correlation": None,
            "fallback_count_summed_evaluator_correlation": None,
            "fallback_associated_tile_wall_excess_vs_fast_only_mean_seconds": None,
            "fallback_associated_summed_evaluator_excess_vs_fast_only_mean_seconds": None,
        }
        if np.std(fallback_cells_per_tile) > 0.0:
            association["fallback_count_tile_wall_correlation"] = float(
                np.corrcoef(fallback_cells_per_tile, tile_wall_seconds)[0, 1]
            )
            association["fallback_count_summed_evaluator_correlation"] = float(
                np.corrcoef(
                    fallback_cells_per_tile,
                    summed_evaluator_seconds,
                )[0, 1]
            )
        if np.any(fast_only) and np.any(has_fallback):
            association[
                "fallback_associated_tile_wall_excess_vs_fast_only_mean_seconds"
            ] = float(
                np.sum(tile_wall_seconds[has_fallback])
                - np.count_nonzero(has_fallback) * np.mean(tile_wall_seconds[fast_only])
            )
            association[
                "fallback_associated_summed_evaluator_excess_vs_fast_only_mean_seconds"
            ] = float(
                np.sum(summed_evaluator_seconds[has_fallback])
                - np.count_nonzero(has_fallback)
                * np.mean(summed_evaluator_seconds[fast_only])
            )

        return {
            "artifact": {
                "path": str(path),
                "bytes": path.stat().st_size,
                "shape_theta2_theta1": list(shape),
                "cell_count": cell_count,
                "work_unit_count": len(tile_wall_seconds),
            },
            "execution_policy_from_tile_provenance": process_policy,
            "status_counts": {
                label: int(np.count_nonzero(field_status == code))
                for code, label in status_vocabulary.items()
            },
            "route_counts": {
                label: int(np.count_nonzero(field_routes == code))
                for code, label in route_vocabulary.items()
            },
            "persisted_timing": {
                "tile_evaluation_wall_seconds_total": tile_wall_total,
                "tile_evaluation_throughput_cells_per_second": (
                    cell_count / tile_wall_total
                ),
                "tile_evaluation_wall_seconds_quantiles": _quantiles(
                    tile_wall_seconds
                ),
                "summed_cell_evaluator_seconds": evaluator_total,
                "mean_cell_evaluator_seconds": evaluator_total / cell_count,
                "evaluator_occupancy_proxy": (
                    evaluator_total / (process_width * tile_wall_total)
                ),
                "solver_function_evaluations_total": int(
                    np.sum(solver_function_evaluations)
                ),
                "solver_function_evaluations_per_cell": float(
                    np.sum(solver_function_evaluations) / cell_count
                ),
            },
            "tile_groups": {
                "fast_only": _tile_group(
                    tile_wall_seconds,
                    summed_evaluator_seconds,
                    fast_only,
                ),
                "fallback_containing": _tile_group(
                    tile_wall_seconds,
                    summed_evaluator_seconds,
                    has_fallback,
                ),
            },
            "fallback_association_not_causal_attribution": association,
            "tile_attempt_counts": {
                str(int(attempt)): int(count)
                for attempt, count in zip(
                    *np.unique(source["tiles/attempt"][:], return_counts=True),
                    strict=True,
                )
            },
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fields",
        type=Path,
        nargs="+",
        help="Completed authoritative HDF5 fields to inspect read-only.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    analyses = [analyze_field(path) for path in arguments.fields]
    print(json.dumps(analyses, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
