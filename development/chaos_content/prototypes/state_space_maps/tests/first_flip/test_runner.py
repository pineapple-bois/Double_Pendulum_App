"""Operational runner conventions for reusable first-flip fields."""

from __future__ import annotations

from development.chaos_content.prototypes.state_space_maps.runners.generate_first_flip_periodic_field import (
    FIRST_FLIP_OUTPUT_DIRECTORY,
    build_parser,
    default_output_path,
    manifest_path,
)


def test_default_output_is_resolution_and_horizon_specific() -> None:
    path = default_output_path(48, 7.5)
    assert path == FIRST_FLIP_OUTPUT_DIRECTORY / "first_flip_field_48_T7p5s.h5"
    assert manifest_path(path) == (
        FIRST_FLIP_OUTPUT_DIRECTORY / "first_flip_field_48_T7p5s.json"
    )

    arguments = build_parser().parse_args(
        [
            "--samples-per-axis",
            "48",
            "--observation-horizon-seconds",
            "7.5",
            "--output",
            "custom_first_flip.h5",
            "--resume",
        ]
    )
    assert arguments.samples_per_axis == 48
    assert arguments.observation_horizon_seconds == 7.5
    assert arguments.output.as_posix() == "custom_first_flip.h5"
    assert not arguments.create
    assert arguments.resume
