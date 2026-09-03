from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).with_name("unsettled_shadow_duration_convergence.py")
SPEC = importlib.util.spec_from_file_location(
    "unsettled_shadow_duration_convergence", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
experiment = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = experiment
SPEC.loader.exec_module(experiment)


def test_pre_execution_gate_freezes_exact_workload() -> None:
    gate = experiment.pre_execution_gate()
    assert gate["accepted"]
    assert all(gate["checks"].values())
    assert [item["id"] for item in experiment.CONDITIONS] == ["ic_1", "ic_3"]
    assert all(item["state_radians"][2:] == [0.0, 0.0] for item in experiment.CONDITIONS)
    assert experiment.SHADOW_NAMES == ("baseline", "strict", "half_step")
    assert experiment.CHECKPOINTS_SECONDS == (
        320.0,
        480.0,
        640.0,
        800.0,
        960.0,
        1120.0,
        1280.0,
    )
    assert gate["contract"]["workload"] == {
        "physical_conditions": 2,
        "formulations": 1,
        "policies_per_condition": 3,
        "integrations": 6,
        "simulated_formulation_seconds": 7680.0,
        "qr_cycles": 30720,
        "checkpoint_spectrum_vectors": 42,
        "canonical_runs": 0,
    }


def test_frozen_limits_and_classification_are_not_averaged_across_conditions() -> None:
    assert experiment.MAX_CHANGE_960_TO_1120 == 0.08
    assert experiment.MAX_CHANGE_1120_TO_1280 == 0.05
    assert experiment.MAX_WITHIN_LATE_RANGE == 0.05
    assert experiment.MAX_FINAL_BETWEEN_RANGE == 0.05
    assert experiment.MAX_FINAL_BETWEEN_SAMPLE_STD == 0.025
    assert experiment.MAX_ENSEMBLE_MEAN_CHANGE_1120_TO_1280 == 0.04
    assert experiment.MAX_LATE_WINDOW_BETWEEN_RANGE == 0.07

    settled = experiment.classify_condition(
        numerical_valid=True, settled=True, independence_demonstrated=True
    )
    unsettled = experiment.classify_condition(
        numerical_valid=True, settled=False, independence_demonstrated=True
    )
    invalid = experiment.classify_condition(
        numerical_valid=False, settled=False, independence_demonstrated=False
    )
    assert experiment.experiment_level_verdict(
        {"ic_1": settled, "ic_3": unsettled}
    ) == "only_ic_1_settles_at_1280_seconds"
    assert experiment.experiment_level_verdict(
        {"ic_1": unsettled, "ic_3": unsettled}
    ) == "neither_condition_settles_at_1280_seconds"
    assert experiment.experiment_level_verdict(
        {"ic_1": settled, "ic_3": invalid}
    ) == "numerical_invalidity"


def test_between_shadow_analysis_applies_frozen_absolute_limits() -> None:
    runs = {}
    for index, name in enumerate(experiment.SHADOW_NAMES):
        checkpoints = {
            f"{int(time)}s": np.array([1.0, 0.01, -0.01, -1.0])
            + index * np.array([0.005, 0.001, -0.001, -0.005])
            for time in experiment.CHECKPOINTS_SECONDS
        }
        runs[name] = {"checkpoint_spectra_per_second": checkpoints}
    result = experiment.between_shadow_analysis(runs)
    assert result["accepted"]
    assert all(result["checks"].values())
    assert np.max(result["final_component_range_per_second"]) <= 0.05


def test_continued_cumulative_logs_replay_runner_addition_order() -> None:
    initial = np.array([620.0, 7.0, -5.0, -622.0], dtype=np.float64)
    cycle_logs = np.tile(
        np.array([0.11, 0.003, -0.002, -0.111], dtype=np.float64), (640, 1)
    )
    expected = []
    running = initial.copy()
    for row in cycle_logs:
        running = running + row
        expected.append(running.copy())
    replayed = experiment.experiment007.replay_cumulative_log_growth(
        initial, cycle_logs
    )
    assert np.array_equal(replayed, np.asarray(expected))


def test_restart_checkpoint_round_trip_for_tiny_el_run(tmp_path: Path) -> None:
    condition = experiment.CONDITIONS[0]
    policy, max_step = experiment.shadow_specs()["baseline"]
    run = experiment.experiment007.run_qr_primitive(
        experiment.experiment006.VariationalDynamics(),
        run_id="experiment014_tiny_restart_preflight",
        duration=0.5,
        qr_interval=experiment.QR_INTERVAL_SECONDS,
        policy=policy,
        max_step=max_step,
        initial_reference=np.asarray(condition["state_radians"], dtype=float),
    )
    state = experiment.experiment013.restart_state_from_run(
        run,
        formulation=experiment.FORMULATION,
        physical_initial_condition=condition,
        policy_name="baseline",
    )
    checkpoint = tmp_path / "checkpoint"
    experiment.experiment013.save_restart_checkpoint(checkpoint, state)
    loaded = experiment.experiment013.load_restart_checkpoint(
        checkpoint,
        expected_formulation=experiment.FORMULATION,
        expected_policy=policy,
        expected_max_step=max_step,
        expected_qr_interval=experiment.QR_INTERVAL_SECONDS,
    )
    assert np.array_equal(loaded.reference_state, state.reference_state)
    assert np.array_equal(
        loaded.tangent_matrix_post_qr, state.tangent_matrix_post_qr
    )
    assert np.array_equal(loaded.cumulative_log_growth, state.cumulative_log_growth)
    assert loaded.metadata["elapsed_time_seconds"] == 0.5
    assert loaded.metadata["completed_qr_cycle_count"] == 2
