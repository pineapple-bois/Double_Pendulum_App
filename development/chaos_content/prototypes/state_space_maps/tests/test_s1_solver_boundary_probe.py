from __future__ import annotations

from development.chaos_content.prototypes.state_space_maps.investigations.performance.s1_history.probe_s1_solver_boundary import (
    CELL_CASES,
    OBSERVATION_HORIZONS,
    summarize_wall_records,
)


def test_probe_configuration_is_bounded_and_includes_required_horizons() -> None:
    assert OBSERVATION_HORIZONS == (5.0, 20.0)
    assert len(CELL_CASES) == 4
    assert {case.t5_route_stratum for case in CELL_CASES} == {
        "compiled_dop853",
        "compiled_rhs_solve_ivp_fallback",
    }


def test_wall_summary_separates_horizon_and_observed_route() -> None:
    def record(
        duration: float,
        route: str,
        case: str,
        wall: float,
        integration: float,
        compiled_calls: int,
        fallback_calls: int,
        rhs_calls: int,
    ) -> dict[str, object]:
        return {
            "duration_seconds": duration,
            "route": route,
            "case": {"name": case},
            "wall_seconds": wall,
            "returned_solver_function_evaluations": rhs_calls,
            "integration_calls": {
                "all_calls_seconds": integration,
                "outside_calls_seconds": wall - integration,
                "compiled_dop853_segment_calls": compiled_calls,
                "solve_ivp_segment_calls": fallback_calls,
            },
        }

    summary = summarize_wall_records(
        (
            record(5.0, "fast", "a", 0.01, 0.008, 20, 0, 6000),
            record(5.0, "fast", "b", 0.02, 0.014, 20, 0, 7000),
            record(20.0, "fallback", "a", 0.20, 0.18, 81, 80, 30000),
        )
    )

    assert set(summary) == {"T=5|fast", "T=20|fallback"}
    assert summary["T=5|fast"]["measurements"] == 2
    assert summary["T=5|fast"]["distinct_cases"] == 2
    assert summary["T=5|fast"]["compiled_dop853_segment_calls_mean"] == 20
    assert summary["T=20|fallback"]["solve_ivp_segment_calls_mean"] == 80
