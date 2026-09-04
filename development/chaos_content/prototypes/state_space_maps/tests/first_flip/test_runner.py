"""Operational runner conventions for the first-flip pilot."""

from __future__ import annotations

from development.chaos_content.prototypes.state_space_maps.runners.generate_first_flip_periodic_field import (
    PILOT_OUTPUT_DIRECTORY,
    build_parser,
    default_output_path,
    manifest_path,
)


def test_default_output_is_resolution_and_horizon_specific() -> None:
    path = default_output_path(32, 5.0)
    assert path == PILOT_OUTPUT_DIRECTORY / "first_flip_field_32_T5s.h5"
    assert manifest_path(path) == PILOT_OUTPUT_DIRECTORY / "first_flip_field_32_T5s.json"

    arguments = build_parser().parse_args(
        [
            "--samples-per-axis",
            "32",
            "--observation-horizon-seconds",
            "5",
            "--create",
        ]
    )
    assert arguments.samples_per_axis == 32
    assert arguments.observation_horizon_seconds == 5.0
    assert arguments.create
    assert not arguments.resume
