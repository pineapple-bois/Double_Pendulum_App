"""Focused regression coverage for the promoted Lyapunov field binding."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from development.chaos_content.prototypes.lyapunov_exponents.field_adapter import (
    LYAPUNOV_ROUTE_VOCABULARY,
    evaluate_lyapunov_field_cell,
    initialize_lyapunov_field_worker,
    periodic_lyapunov_field_definition,
    run_periodic_lyapunov_field,
    specification_for_cell,
    validate_lyapunov_oracle_spots,
)
from development.chaos_content.prototypes.lyapunov_exponents.hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
)
from development.chaos_content.prototypes.lyapunov_exponents.reference import (
    RenormalizedTangentSpec,
)
from development.chaos_content.prototypes.scalar_field_generation import (
    CellState,
    ScalarCellTask,
    read_authoritative_field,
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

    assert fast.evaluator == HYBRID_FAST_EVALUATOR
    assert fallback.evaluator == HYBRID_FALLBACK_EVALUATOR
    assert fast.numerically_valid
    assert fallback.numerically_valid


def test_tiny_periodic_field_is_authoritative_and_passes_oracle_gates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lyapunov_2x2.h5"
    summary = run_periodic_lyapunov_field(path, 2, mode="create")
    snapshot = read_authoritative_field(path)
    oracle = validate_lyapunov_oracle_spots(path)

    assert summary.validation.accepted
    assert summary.evaluated_cells == 4
    assert summary.pool_count == 1
    assert summary.all_workers_stopped
    assert snapshot.values.shape == (2, 2)
    assert np.all(snapshot.status == CellState.COMPLETED_VALID)
    assert set(np.unique(snapshot.execution_route)).issubset(
        {code for code, _label in LYAPUNOV_ROUTE_VOCABULARY if code}
    )
    assert oracle.accepted
