"""Focused regression coverage for the promoted Lyapunov field binding."""

from __future__ import annotations

import math
from dataclasses import replace
import json
from pathlib import Path

import h5py
import numpy as np
import pytest


from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
    LYAPUNOV_ROUTE_VOCABULARY,
    evaluate_lyapunov_field_cell,
    initialize_lyapunov_field_worker,
    lyapunov_evaluator_binding,
    periodic_lyapunov_field_definition,
    run_periodic_lyapunov_field,
    specification_for_cell,
    validate_lyapunov_oracle_spots,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    RenormalizedTangentSpec,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.s1 import (
    S1_EVALUATOR,
    s1_build_support,
)
from development.chaos_content.prototypes.state_space_maps.src.generation import (
    CellState,
    IntegrityError,
    ProcessExecutionSpec,
    ScalarCellTask,
    TileShape,
    create_dataset,
    plan_tiles,
    read_authoritative_field,
    run_scalar_field,
    validate_dataset,
)


def _task(theta1_degrees: float, theta2_degrees: float) -> ScalarCellTask:
    return ScalarCellTask(
        linear_index=0,
        theta2_index=0,
        theta1_index=0,
        theta2_coordinate=math.radians(theta2_degrees),
        theta1_coordinate=math.radians(theta1_degrees),
    )


def test_adapter_preserves_fixed_policy_and_fast_fallback_routes() -> None:
    spec = RenormalizedTangentSpec()
    substituted = specification_for_cell(_task(170.0, 171.0), spec)
    assert substituted.duration == spec.duration
    assert substituted.renormalization_interval == spec.renormalization_interval
    assert substituted.initial_tangent == spec.initial_tangent
    assert substituted.solver == spec.solver
    assert substituted.initial_state.theta1 == math.radians(170.0)
    assert substituted.initial_state.theta2 == math.radians(171.0)
    assert substituted.initial_state.omega1 == 0.0
    assert substituted.initial_state.omega2 == 0.0

    initialize_lyapunov_field_worker(spec)
    fast = evaluate_lyapunov_field_cell(_task(179.0, 179.0))
    fallback = evaluate_lyapunov_field_cell(_task(177.75, 170.25))

    expected_fast = (
        S1_EVALUATOR if s1_build_support().supported else HYBRID_FAST_EVALUATOR
    )
    assert fast.evaluator == expected_fast
    assert fallback.evaluator == HYBRID_FALLBACK_EVALUATOR
    assert fast.numerically_valid
    assert fallback.numerically_valid
    if s1_build_support().supported:
        assert fallback.attempted_evaluators == (S1_EVALUATOR,)


def test_tiny_periodic_field_is_authoritative_and_passes_oracle_gates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lyapunov_2x2.h5"
    summary = run_periodic_lyapunov_field(path, 2, mode="create")
    resumed = run_periodic_lyapunov_field(path, 2, mode="resume")
    snapshot = read_authoritative_field(path)
    oracle = validate_lyapunov_oracle_spots(path)

    assert summary.validation.accepted
    assert summary.evaluated_cells == 4
    assert summary.pool_count == 1
    assert summary.all_workers_stopped
    assert resumed.evaluated_cells == 0
    assert resumed.preexisting_completed_cells == 4
    assert snapshot.values.shape == (2, 2)
    assert np.all(snapshot.status == CellState.COMPLETED_VALID)
    assert set(np.unique(snapshot.execution_route)).issubset(
        {code for code, _label in LYAPUNOV_ROUTE_VOCABULARY if code}
    )
    assert oracle.accepted
    assert snapshot.metadata["evaluator_provenance"]["s1"]["implementation"] == (
        S1_EVALUATOR
    )
    assert snapshot.metadata["evaluator_provenance"]["s1"]["artifact"]["key"]
    assert (
        snapshot.metadata["evaluator_provenance"]["s1"]["artifact"][
            "schema_version"
        ]
        == 1
    )


def test_promotion_definition_fails_closed_against_prepromotion_resume(
    tmp_path: Path,
) -> None:
    promoted = periodic_lyapunov_field_definition(2)
    legacy = replace(
        promoted,
        evaluator_provenance={
            "policy": "targeted_hybrid",
            "normal_route": HYBRID_FAST_EVALUATOR,
            "fallback_route": HYBRID_FALLBACK_EVALUATOR,
        },
        route_vocabulary=promoted.route_vocabulary[:-1],
    )
    plan = plan_tiles(legacy.field_shape, TileShape(*legacy.nominal_tile_shape))
    path = tmp_path / "prepromotion.h5"
    create_dataset(path, legacy, tuple(unit.bounds for unit in plan))

    with pytest.raises(IntegrityError, match="definition.*differs"):
        run_periodic_lyapunov_field(path, 2, mode="resume")


def test_tiny_recovery_persists_accepted_route_attempt_and_resumes(
    tmp_path: Path,
) -> None:
    if not s1_build_support().supported:
        pytest.skip("S1 recovery provenance requires the validated native build")
    definition = replace(
        periodic_lyapunov_field_definition(1),
        theta1_axis=(math.radians(177.75),),
        theta2_axis=(math.radians(170.25),),
        nominal_tile_shape=(1, 1),
    )
    execution = ProcessExecutionSpec(
        process_width=1,
        chunksize=1,
        maximum_cells_per_pool=1,
    )
    path = tmp_path / "s1_recovery_1x1.h5"
    created = run_scalar_field(
        path,
        definition,
        lyapunov_evaluator_binding(),
        execution=execution,
        mode="create",
    )
    resumed = run_scalar_field(
        path,
        definition,
        lyapunov_evaluator_binding(),
        execution=execution,
        mode="resume",
    )
    snapshot = read_authoritative_field(path)
    route_codes = {label: code for code, label in LYAPUNOV_ROUTE_VOCABULARY}
    with h5py.File(path, "r") as source:
        exceptional = json.loads(source["tiles/exceptional_cells_json"][0])
        diagnostics = json.loads(source["tiles/diagnostics_json"][0])

    assert created.validation.accepted
    assert validate_dataset(path).accepted
    assert resumed.evaluated_cells == 0
    assert snapshot.execution_route[0, 0] == route_codes[HYBRID_FALLBACK_EVALUATOR]
    assert exceptional[0]["execution_route"] == HYBRID_FALLBACK_EVALUATOR
    assert exceptional[0]["attempted_evaluators"] == [S1_EVALUATOR]
    assert exceptional[0]["recovery_reason"] == "s1_execution_error"
    assert exceptional[0]["attempt_provenance"][S1_EVALUATOR][
        "implementation"
    ] == S1_EVALUATOR
    assert exceptional[0]["attempt_provenance"][S1_EVALUATOR]["artifact"][
        "available"
    ] is True
    assert exceptional[0]["attempt_provenance"][S1_EVALUATOR]["artifact"]["key"]
    assert diagnostics["attempted_evaluator_counts"] == {S1_EVALUATOR: 1}
    assert diagnostics["recovery_reason_counts"] == {"s1_execution_error": 1}
