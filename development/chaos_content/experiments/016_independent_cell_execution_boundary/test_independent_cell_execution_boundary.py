"""Focused correctness tests for Experiment 016's execution harness."""

from __future__ import annotations

import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest


EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import independent_cell_execution_boundary as experiment

from development.chaos_content.prototypes.lyapunov_exponents.reference import (
    RenormalizedTangentSpec,
)


@pytest.fixture(scope="module")
def short_spec() -> RenormalizedTangentSpec:
    return replace(RenormalizedTangentSpec(), duration=0.25)


def test_mechanical_axes_and_row_major_index_contract() -> None:
    assert experiment.angle_axis_degrees(9) == pytest.approx(
        tuple(169.0 + 2.5 * index for index in range(9))
    )
    tasks = experiment.grid_tasks(9)

    assert len(tasks) == 81
    assert tasks[0] == experiment.CellTask(0, 0, 0, 169.0, 169.0)
    assert tasks[8] == experiment.CellTask(8, 0, 8, 169.0, 189.0)
    assert tasks[9] == experiment.CellTask(9, 1, 0, 171.5, 169.0)
    assert tasks[40] == experiment.CellTask(40, 4, 4, 179.0, 179.0)
    assert tasks[-1] == experiment.CellTask(80, 8, 8, 189.0, 189.0)


def test_state_substitution_changes_only_declared_angles(
    short_spec: RenormalizedTangentSpec,
) -> None:
    task = experiment.CellTask(0, 0, 0, 173.0, 181.0)
    actual = experiment.specification_for_task(task, short_spec)

    assert actual.initial_state.theta1 == pytest.approx(
        experiment.math.radians(181.0)
    )
    assert actual.initial_state.theta2 == pytest.approx(
        experiment.math.radians(173.0)
    )
    assert actual.initial_state.omega1 == short_spec.initial_state.omega1
    assert actual.initial_state.omega2 == short_spec.initial_state.omega2
    assert replace(actual, initial_state=short_spec.initial_state) == short_spec


def test_dispatch_amortisation_is_mechanical() -> None:
    assert experiment.amortized_chunksize(81, 1) == 11
    assert experiment.amortized_chunksize(289, 2) == 19
    assert experiment.amortized_chunksize(625, 4) == 20
    with pytest.raises(ValueError, match="positive"):
        experiment.amortized_chunksize(0, 1)


def test_thread_and_spawn_process_execution_preserve_cell_results(
    short_spec: RenormalizedTangentSpec,
) -> None:
    tasks = experiment.grid_tasks(2)
    baseline = experiment.run_sequential(tasks, short_spec)

    with ThreadPoolExecutor(max_workers=2) as executor:
        threaded = experiment.run_thread_pool(executor, tasks, short_spec)
    thread_comparison = experiment.compare_outcomes(baseline, threaded)
    assert thread_comparison["accepted"]
    assert thread_comparison["exact_value_matches"] == 4
    assert thread_comparison["exact_diagnostic_matches"] == 4

    with ProcessPoolExecutor(
        max_workers=2,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=experiment._initialize_process_worker,
        initargs=(short_spec,),
    ) as executor:
        identities = experiment._wait_for_process_workers(executor, 2)
        processed = experiment.run_process_pool(executor, tasks, chunksize=1)
    process_comparison = experiment.compare_outcomes(baseline, processed)
    assert len({identity.process_id for identity in identities}) == 2
    assert process_comparison["accepted"]
    assert process_comparison["exact_value_matches"] == 4
    assert process_comparison["exact_diagnostic_matches"] == 4


def test_missing_and_duplicate_cells_are_rejected(
    short_spec: RenormalizedTangentSpec,
) -> None:
    baseline = experiment.run_sequential(experiment.grid_tasks(2), short_spec)

    missing = experiment.compare_outcomes(baseline, baseline[:-1])
    duplicated = experiment.compare_outcomes(baseline, baseline + (baseline[0],))

    assert not missing["accepted"]
    assert missing["missing_linear_indices"] == [3]
    assert not duplicated["accepted"]
    assert duplicated["duplicate_candidate_count"] == 1


def test_failure_semantics_remain_distinct(
    short_spec: RenormalizedTangentSpec,
) -> None:
    checks = experiment.evaluate_failure_semantics(base_spec=short_spec)["sequential"]

    assert checks == {
        "completed_invalid_preserved": True,
        "execution_error_preserved": True,
        "programming_error_propagated": True,
        "accepted": True,
    }


def _timing_distribution(wall: float) -> dict[str, object]:
    return {
        "wall_seconds_median": wall,
        "wall_seconds_q1": wall * 0.99,
        "wall_seconds_q3": wall * 1.01,
        "cells_per_second_median": 100.0 / wall,
        "all_equivalence_checks_passed": True,
    }


def test_decision_requires_sustained_spread_separated_improvement() -> None:
    timing_groups = {
        experiment._timing_group_key("sequential", 17, 1, "direct"): (
            _timing_distribution(2.0)
        ),
        experiment._timing_group_key("sequential", 25, 1, "direct"): (
            _timing_distribution(4.0)
        ),
        experiment._timing_group_key("process_spawn", 17, 2, "amortized"): (
            _timing_distribution(1.2)
        ),
        experiment._timing_group_key("process_spawn", 25, 2, "amortized"): (
            _timing_distribution(2.3)
        ),
        experiment._timing_group_key("process_spawn", 17, 2, "per_cell"): (
            _timing_distribution(1.21)
        ),
        experiment._timing_group_key("process_spawn", 25, 2, "per_cell"): (
            _timing_distribution(2.31)
        ),
    }
    accepted_probe = {"accepted": True}
    decision = experiment.decide_execution_policy(
        timing_groups,
        thread_results={},
        process_results={
            "2": {"failure_message": None, "workers_stopped": True}
        },
        sequential_failure_probe=accepted_probe,
        process_failure_probe=accepted_probe,
    )

    assert decision["outcome"] == "execution_policy_accepted"
    assert decision["accepted_policy"] == {
        "strategy": "process_spawn",
        "width": 2,
        "dispatch_policy": "per_cell",
        "observed_chunksize_on_25x25": 1,
    }


def test_decision_can_retain_sequential_execution() -> None:
    timing_groups = {
        experiment._timing_group_key("sequential", samples, 1, "direct"): (
            _timing_distribution(wall)
        )
        for samples, wall in ((17, 2.0), (25, 4.0))
    }
    decision = experiment.decide_execution_policy(
        timing_groups,
        thread_results={},
        process_results={},
        sequential_failure_probe={"accepted": True},
        process_failure_probe=None,
    )

    assert decision["outcome"] == "no_concurrency_policy_promoted"
    assert decision["accepted_policy"] == "sequential"
