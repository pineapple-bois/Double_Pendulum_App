"""Spawn-importable synthetic evaluator used only by focused runner tests."""

from __future__ import annotations

from development.chaos_content.prototypes.state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)

from development.chaos_content.prototypes.scalar_field_generation.work_units import (
    ScalarCellTask,
)


_OFFSET = 0.0


def initialize(offset: float) -> None:
    global _OFFSET
    _OFFSET = offset


def evaluate(task: ScalarCellTask) -> ScalarEvaluation[None]:
    value = _OFFSET + 1000.0 * task.theta2_index + task.theta1_index
    if task.linear_index == 1:
        return ScalarEvaluation(
            status=EvaluationStatus.COMPLETED_INVALID,
            value=value,
            diagnostics=None,
            elapsed_seconds=0.0,
            evaluator="synthetic",
            validity_issues=("controlled invalidity",),
        )
    if task.linear_index == 2:
        return ScalarEvaluation(
            status=EvaluationStatus.EXECUTION_ERROR,
            value=None,
            diagnostics=None,
            elapsed_seconds=0.0,
            evaluator="synthetic",
            error_type="ControlledError",
            error_message="controlled execution failure",
        )
    return ScalarEvaluation(
        status=EvaluationStatus.COMPLETED_VALID,
        value=value,
        diagnostics=None,
        elapsed_seconds=0.0,
        evaluator="synthetic",
    )


def summarize(evaluations) -> dict[str, object]:
    return {"synthetic_evaluation_count": len(evaluations)}


def raise_programming_error(task: ScalarCellTask) -> ScalarEvaluation[None]:
    raise ValueError(f"controlled programming error at {task.linear_index}")
