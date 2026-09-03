from __future__ import annotations

import math
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from matplotlib import colors

from development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field import (
    ConsoleProgressReporter,
    OPERATIONAL_OUTPUT_DIRECTORY,
    build_manifest,
    build_parser as build_generation_parser,
    default_output_path,
    manifest_path,
    write_manifest,
)
from development.chaos_content.prototypes.state_space_maps.runners.render_finite_time_field import (
    ANGLE_TICK_LABELS,
    ANGLE_TICK_POSITIONS,
    FIELD_COLORMAP,
    build_figure,
    derivative_output_paths,
    render_persisted_field,
)
from development.chaos_content.prototypes.state_space_maps.src.generation import (
    CellState,
    CompletedTile,
    FieldDefinition,
    FieldProgress,
    FieldRunSummary,
    ProcessExecutionSpec,
    ScalarFieldValidation,
    TileShape,
    create_dataset,
    plan_tiles,
    validate_tile_plan,
    write_completed_tile,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
    LyapunovOracleValidation,
    periodic_lyapunov_field_definition,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


def test_operational_generation_defaults_are_resolution_specific() -> None:
    path = default_output_path(512)
    assert path == OPERATIONAL_OUTPUT_DIRECTORY / "finite_time_field_512.h5"
    assert manifest_path(path) == (
        OPERATIONAL_OUTPUT_DIRECTORY / "finite_time_field_512.json"
    )
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


def test_resume_progress_is_immediate_and_milestone_throttled(capsys) -> None:
    reporter = ConsoleProgressReporter(samples_per_axis=10, process_width=4)
    reporter(
        FieldProgress(
            output_path=Path("finite_time_field_10.h5"),
            mode="resume",
            completed_work_units=4,
            total_work_units=10,
            completed_cells=40,
            total_cells=100,
            evaluated_work_units=0,
            evaluated_cells=0,
            elapsed_seconds=0.0,
        )
    )
    initial = capsys.readouterr().out
    assert "Resuming finite_time_field_10.h5" in initial
    assert "4/10 work units already complete (40.0%)" in initial
    assert "6 work units remaining" in initial

    reporter(
        FieldProgress(
            output_path=Path("finite_time_field_10.h5"),
            mode="resume",
            completed_work_units=4,
            total_work_units=10,
            completed_cells=41,
            total_cells=100,
            evaluated_work_units=1,
            evaluated_cells=1,
            elapsed_seconds=1.0,
        )
    )
    assert capsys.readouterr().out == ""

    reporter(
        FieldProgress(
            output_path=Path("finite_time_field_10.h5"),
            mode="resume",
            completed_work_units=5,
            total_work_units=10,
            completed_cells=50,
            total_cells=100,
            evaluated_work_units=2,
            evaluated_cells=10,
            elapsed_seconds=2.0,
        )
    )
    milestone = capsys.readouterr().out
    assert "[ 50.0%] 5/10 work units" in milestone
    assert "50/100 cells" in milestone
    assert "5.0 cells/s" in milestone
    assert "ETA ~" in milestone


def test_manifest_uses_run_objects_and_writes_resolution_sidecar(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "finite_time_field_2.h5"
    definition = periodic_lyapunov_field_definition(2)
    execution = ProcessExecutionSpec()
    validation = ScalarFieldValidation(
        accepted=True,
        complete=True,
        issues=(),
        status_counts={
            "not_yet_computed": 0,
            "completed_valid": 3,
            "completed_invalid": 1,
            "execution_error": 0,
        },
        route_counts={"compiled_dop853": 4},
        valid_value_range=(0.1, 0.4),
    )
    summary = FieldRunSummary(
        output_path=output_path,
        mode="create",
        total_seconds=2.0,
        setup_seconds=0.2,
        evaluation_seconds=1.5,
        persistence_seconds=0.2,
        shutdown_seconds=0.1,
        evaluated_cells=4,
        preexisting_completed_cells=0,
        completed_tiles_before=0,
        pending_tiles_before=1,
        completed_tiles_after=1,
        pending_tiles_after=0,
        pool_count=1,
        recycling_events=0,
        all_workers_stopped=True,
        cells_per_second=2.0,
        maximum_worker_peak_rss_bytes=1,
        coordinator_peak_rss_bytes=1,
        artifact_bytes=1,
        validation=validation,
    )
    oracle = LyapunovOracleValidation(
        accepted=True,
        selected_indices=((0, 0),),
        maximum_rate_error_per_second=0.0,
        maximum_energy_diagnostic_error=0.0,
        comparisons=(),
    )

    payload = build_manifest(
        output_path=output_path,
        definition=definition,
        execution=execution,
        summary=summary,
        oracle=oracle,
        completed_at_utc="2026-09-03T12:00:00+00:00",
        operation_wall_seconds=2.5,
    )
    path = write_manifest(output_path, payload)
    stored = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / "finite_time_field_2.json"
    assert stored["artifact"]["hdf5_name"] == "finite_time_field_2.h5"
    assert stored["field"]["shape_theta2_theta1"] == [2, 2]
    assert stored["field"]["cell_count"] == 4
    assert stored["field"]["stored_orientation"] == (
        "values[theta2_index, theta1_index]"
    )
    assert stored["scientific_contract"]["numerical_parameters"] == dict(
        definition.numerical_parameters
    )
    assert stored["execution"]["process_policy"] == {
        "chunksize": 1,
        "maximum_cells_per_pool": 1024,
        "process_width": 4,
        "start_method": "spawn",
    }
    assert stored["persistence"]["schema_version"] == 1
    assert stored["completion"]["completed_invalid_cells"] == 1
    assert stored["completion"]["execution_error_cells"] == 0
    assert stored["oracle_validation"]["accepted"] is True


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


def test_renderer_uses_tex_pi_ticks_and_linear_magma_scale(tmp_path: Path) -> None:
    import matplotlib

    from development.chaos_content.prototypes.state_space_maps.src.generation import (
        read_authoritative_field,
    )

    dataset = tmp_path / "finite_time_field_2.h5"
    _synthetic_completed_field(dataset)
    figure = build_figure(read_authoritative_field(dataset))
    axis = figure.axes[0]
    image = axis.images[0]

    assert matplotlib.rcParams["text.usetex"] is True
    np.testing.assert_allclose(axis.get_xticks(), ANGLE_TICK_POSITIONS)
    np.testing.assert_allclose(axis.get_yticks(), ANGLE_TICK_POSITIONS)
    assert [label.get_text() for label in axis.get_xticklabels()] == list(
        ANGLE_TICK_LABELS
    )
    assert [label.get_text() for label in axis.get_yticklabels()] == list(
        ANGLE_TICK_LABELS
    )
    assert image.get_cmap().name == FIELD_COLORMAP == "magma"
    assert type(image.norm) is colors.Normalize
    assert axis.get_xlim() == (-np.pi, np.pi)
    assert axis.get_ylim() == (-np.pi, np.pi)
    assert axis.get_xlabel() == r"$\theta_1(0)\;[\mathrm{rad}]$"
    assert axis.get_ylabel() == r"$\theta_2(0)\;[\mathrm{rad}]$"
    assert figure.axes[1].get_ylabel() == (
        r"$\Lambda_T^{(1)}$ [$\mathrm{s}^{-1}$]"
    )
    matplotlib.pyplot.close(figure)


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
