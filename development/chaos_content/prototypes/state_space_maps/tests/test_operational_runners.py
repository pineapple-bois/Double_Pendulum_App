from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field import (
    OPERATIONAL_OUTPUT_DIRECTORY,
    build_parser as build_generation_parser,
    default_output_path,
)
from development.chaos_content.prototypes.state_space_maps.runners.render_finite_time_field import (
    derivative_output_paths,
    render_persisted_field,
)
from development.chaos_content.prototypes.state_space_maps.src.generation import (
    CellState,
    CompletedTile,
    FieldDefinition,
    TileShape,
    create_dataset,
    plan_tiles,
    validate_tile_plan,
    write_completed_tile,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
    periodic_lyapunov_field_definition,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


def test_operational_generation_defaults_are_resolution_specific() -> None:
    path = default_output_path(512)
    assert path == OPERATIONAL_OUTPUT_DIRECTORY / "finite_time_field_512.h5"
    assert "outputs/lyapunov" not in path.as_posix()

    arguments = build_generation_parser().parse_args(
        ["--samples-per-axis", "512", "--create"]
    )
    assert arguments.samples_per_axis == 512
    assert arguments.output is None
    assert arguments.create
    assert not arguments.resume


def test_512_definition_and_established_plan_are_calculation_free() -> None:
    definition = periodic_lyapunov_field_definition(512)
    plan = plan_tiles(definition.field_shape, TileShape(*definition.nominal_tile_shape))
    coverage = validate_tile_plan(definition.field_shape, plan)

    assert definition.field_shape == (512, 512)
    assert coverage.accepted
    assert coverage.planned_cell_count == 262_144
    assert len(plan) == 4_096


def _synthetic_completed_field(path: Path) -> None:
    definition = FieldDefinition(
        theta1_axis=(-math.pi, 0.0),
        theta2_axis=(-math.pi, 0.0),
        coordinate_unit="radians",
        periodic=True,
        periodic_interval="[-pi, pi)",
        nominal_tile_shape=(2, 2),
        observable_provenance={
            "name": "one_vector_finite_time_tangent_stretching_rate"
        },
        physical_parameters={},
        numerical_parameters={"duration_seconds": 5.0},
        evaluator_provenance={"name": "synthetic_test_fixture"},
        software_provenance={"revision": "test"},
        route_vocabulary=((0, "not_yet_computed"), (1, "synthetic")),
    )
    plan = plan_tiles(definition.field_shape, TileShape(2, 2))
    create_dataset(path, definition, tuple(unit.bounds for unit in plan))
    write_completed_tile(
        path,
        0,
        CompletedTile(
            bounds=plan[0].bounds.as_tuple,
            values=np.asarray(((0.1, 0.2), (0.3, 0.4)), dtype="<f8"),
            status=np.full((2, 2), CellState.COMPLETED_VALID, dtype=np.uint8),
            execution_route=np.ones((2, 2), dtype=np.uint8),
            attempt=1,
            evaluation_seconds=0.0,
            diagnostics={"fixture": True},
            provenance={"fixture": "rendering"},
        ),
    )


def test_renderer_writes_png_and_pdf_from_persisted_hdf5(tmp_path: Path) -> None:
    dataset = tmp_path / "finite_time_field_2.h5"
    _synthetic_completed_field(dataset)

    result = render_persisted_field(dataset)
    png_path, pdf_path = derivative_output_paths(dataset)

    assert result["shape_theta2_theta1"] == [2, 2]
    assert result["rendered_valid_cells"] == 4
    assert result["masked_nonvalid_cells"] == 0
    assert result["dynamics_evaluator_imported"] is False
    assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert pdf_path.read_bytes().startswith(b"%PDF")


def test_renderer_refuses_an_incomplete_field(tmp_path: Path) -> None:
    definition = FieldDefinition(
        theta1_axis=(-math.pi, 0.0),
        theta2_axis=(-math.pi, 0.0),
        coordinate_unit="radians",
        periodic=True,
        periodic_interval="[-pi, pi)",
        nominal_tile_shape=(2, 2),
        observable_provenance={"name": "synthetic"},
        physical_parameters={},
        numerical_parameters={"duration_seconds": 5.0},
        evaluator_provenance={"name": "synthetic"},
        software_provenance={"revision": "test"},
        route_vocabulary=((0, "not_yet_computed"), (1, "synthetic")),
    )
    path = tmp_path / "incomplete.h5"
    plan = plan_tiles(definition.field_shape, TileShape(2, 2))
    create_dataset(path, definition, tuple(unit.bounds for unit in plan))

    with pytest.raises(RuntimeError, match="incomplete authoritative field"):
        render_persisted_field(path)


def test_renderer_import_does_not_load_lyapunov_modules() -> None:
    module = (
        "development.chaos_content.prototypes.state_space_maps.runners."
        "render_finite_time_field"
    )
    script = (
        f"import {module}; import sys; "
        "assert not any(name.startswith("
        "'development.chaos_content.prototypes.state_space_maps.src.lyapunov'"
        ") for name in sys.modules)"
    )
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPOSITORY_ROOT,
        check=True,
    )
