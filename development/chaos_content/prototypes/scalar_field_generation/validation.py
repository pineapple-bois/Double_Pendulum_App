"""Dynamics-free validation for authoritative scalar-field artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from .hdf5 import (
    STATUS_VOCABULARY,
    CellState,
    FieldDefinition,
    assert_dataset_compatible,
    read_authoritative_field,
    validate_dataset,
)
from .work_units import TileWorkUnit, validate_tile_plan


@dataclass(frozen=True)
class ScalarFieldValidation:
    accepted: bool
    complete: bool
    issues: tuple[str, ...]
    status_counts: dict[str, int]
    route_counts: dict[str, int]
    valid_value_range: tuple[float, float] | None


def validate_authoritative_field(
    path: Path,
    definition: FieldDefinition,
    work_units: Sequence[TileWorkUnit],
    *,
    require_complete: bool = True,
) -> ScalarFieldValidation:
    """Validate storage, coverage, state semantics, and declared provenance."""

    coverage = validate_tile_plan(definition.field_shape, work_units)
    issues: list[str] = []
    if not coverage.accepted:
        issues.append("work-unit plan does not cover the field exactly once")
    try:
        resume = assert_dataset_compatible(
            path,
            definition,
            tuple(unit.bounds for unit in work_units),
        )
    except (OSError, RuntimeError) as error:
        return ScalarFieldValidation(
            accepted=False,
            complete=False,
            issues=(*issues, str(error)),
            status_counts={},
            route_counts={},
            valid_value_range=None,
        )
    storage = validate_dataset(path)
    issues.extend(storage.issues)
    snapshot = read_authoritative_field(path)
    complete = not resume.pending_tile_indices and not resume.corrupt_tile_indices
    if require_complete and not complete:
        issues.append("authoritative field is incomplete")

    status_counts = {
        label: int(np.count_nonzero(snapshot.status == code))
        for code, label in STATUS_VOCABULARY.items()
    }
    route_vocabulary = {
        int(code): label
        for code, label in snapshot.metadata["execution_route_vocabulary"].items()
    }
    route_counts = {
        label: int(np.count_nonzero(snapshot.execution_route == code))
        for code, label in route_vocabulary.items()
    }
    valid_mask = snapshot.status == CellState.COMPLETED_VALID
    valid_range = None
    if np.any(valid_mask):
        valid_range = (
            float(np.min(snapshot.values[valid_mask])),
            float(np.max(snapshot.values[valid_mask])),
        )
    return ScalarFieldValidation(
        accepted=not issues,
        complete=complete,
        issues=tuple(issues),
        status_counts=status_counts,
        route_counts=route_counts,
        valid_value_range=valid_range,
    )
