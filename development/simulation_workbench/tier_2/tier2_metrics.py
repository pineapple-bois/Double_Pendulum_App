"""Compact metrics helpers for the Tier 2 Simulation Workbench preview."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable


def timed_call(func: Callable[[], Any]) -> tuple[Any, float]:
    start = perf_counter()
    value = func()
    return value, perf_counter() - start


def trace_count(fig) -> int:
    return len(getattr(fig, "data", []) or [])


def frame_count(fig) -> int:
    return len(getattr(fig, "frames", []) or [])


def point_count(fig) -> int:
    total = 0
    for trace in getattr(fig, "data", []) or []:
        x_values = getattr(trace, "x", None)
        if x_values is not None:
            total += len(x_values)
    for frame in getattr(fig, "frames", []) or []:
        for trace in getattr(frame, "data", []) or []:
            x_values = getattr(trace, "x", None)
            if x_values is not None:
                total += len(x_values)
    return int(total)


def plotly_json_size(fig) -> int:
    return len(fig.to_json())


def figure_metrics(fig, build_time_seconds: float) -> dict[str, Any]:
    return {
        "build_time_seconds": build_time_seconds,
        "trace_count": trace_count(fig),
        "frame_count": frame_count(fig),
        "point_count": point_count(fig),
        "plotly_json_size_bytes": plotly_json_size(fig),
    }


def write_compact_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main() -> int:
    from output_composition import BASELINE_MATRIX, assemble_workspace_payload

    results = []
    for model_type, system_type in BASELINE_MATRIX:
        payload = assemble_workspace_payload(
            model_type=model_type,
            system_type=system_type,
            preset_name="nonzero velocities",
            duration_seconds=3.0,
            samples_per_second=120,
        )
        results.append(
            {
                "model_type": model_type,
                "system_type": system_type,
                "status": payload["status"],
                "metrics": payload["metrics"],
                "diagnostics": payload["diagnostics"],
                "warnings": payload["warnings"],
            }
        )

    summary = {
        "tier": "Phase 6 / Tier 2",
        "purpose": "Compact preview metrics for candidate output composition",
        "case_count": len(results),
        "cases": results,
    }
    output_path = Path(__file__).with_name("tier2_preview_results.json")
    write_compact_json(output_path, summary)

    print("Phase 6 / Tier 2 metrics")
    print(f"Wrote compact JSON summary: {output_path}")
    for case in results:
        metrics = case["metrics"]
        print(
            f"- {case['model_type']} {case['system_type']}: "
            f"status={case['status']} panels={metrics['output_panel_count']} "
            f"warnings={metrics['warning_count']} "
            f"animation_json={metrics['figures']['animation']['plotly_json_size_bytes']} bytes"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
