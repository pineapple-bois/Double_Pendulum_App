"""Render a completed authoritative first-flip-time field from persisted HDF5.

Future timescale bins and threshold views belong behind explicit functions in
this module and must derive from the authoritative field within its supported
horizon. They must not persist redundant scientific fields or run dynamics.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Sequence


_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_ROOT / "xdg"))

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams.update(
    {
        "font.family": "serif",
        "text.usetex": True,
    }
)
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from ..src.generation.hdf5 import (
    CellState,
    FieldSnapshot,
    read_authoritative_field,
    validate_dataset,
)


ANGLE_TICK_POSITIONS = (
    -np.pi,
    -np.pi / 2.0,
    0.0,
    np.pi / 2.0,
    np.pi,
)
ANGLE_TICK_LABELS = (
    r"$-\pi$",
    r"$-\pi/2$",
    r"$0$",
    r"$\pi/2$",
    r"$\pi$",
)
FIELD_COLORMAP = "magma"
CENSORED_COLOR = "#43A6C6"
FIRST_FLIP_OBSERVABLE = "capped_dimensionless_first_flip_time"


def derivative_output_paths(dataset_path: Path) -> tuple[Path, Path]:
    """Return PNG and PDF paths beside the authoritative HDF5 artifact."""

    path = Path(dataset_path)
    return path.with_suffix(".png"), path.with_suffix(".pdf")


def build_figure(snapshot: FieldSnapshot) -> Figure:
    """Build the established continuous first-flip-time presentation."""

    observable = snapshot.metadata["observable_provenance"]["name"]
    if observable != FIRST_FLIP_OBSERVABLE:
        raise ValueError(
            "First-flip renderer requires observable "
            f"{FIRST_FLIP_OBSERVABLE!r}; got {observable!r}."
        )

    valid = snapshot.status == CellState.COMPLETED_VALID
    horizon = float(
        snapshot.metadata["numerical_parameters"][
            "dimensionless_observation_horizon"
        ]
    )
    physical_horizon = float(
        snapshot.metadata["numerical_parameters"]["observation_horizon_seconds"]
    )
    censored = valid & (snapshot.values == horizon)
    visible = np.ma.masked_where(~valid | censored, snapshot.values)

    figure, axis = plt.subplots(figsize=(7.2, 6.0), constrained_layout=True)
    image = axis.imshow(
        visible,
        origin="lower",
        interpolation="none",
        extent=(-np.pi, np.pi, -np.pi, np.pi),
        aspect="equal",
        cmap=FIELD_COLORMAP,
    )
    axis.imshow(
        np.ma.masked_where(~censored, np.ones(snapshot.values.shape)),
        origin="lower",
        interpolation="nearest",
        extent=(-np.pi, np.pi, -np.pi, np.pi),
        aspect="equal",
        cmap=ListedColormap((CENSORED_COLOR,)),
        vmin=0.0,
        vmax=1.0,
    )
    axis.set_xticks(ANGLE_TICK_POSITIONS, ANGLE_TICK_LABELS)
    axis.set_yticks(ANGLE_TICK_POSITIONS, ANGLE_TICK_LABELS)
    axis.set_xlabel(r"$\theta_1(0)\;[\mathrm{rad}]$")
    axis.set_ylabel(r"$\theta_2(0)\;[\mathrm{rad}]$")
    axis.set_title(
        "Dimensionless first-flip time, "
        rf"$T_{{\max}}={physical_horizon:g}\,\mathrm{{s}}$, "
        rf"$\widehat{{T}}_{{\max}}={horizon:g}$"
    )
    axis.legend(
        handles=(
            Patch(
                facecolor=CENSORED_COLOR,
                label=(
                    "No flip observed by "
                    rf"$T_{{\max}}={physical_horizon:g}\,\mathrm{{s}}$"
                ),
            ),
        ),
        loc="upper right",
    )
    colorbar = figure.colorbar(image, ax=axis)
    colorbar.set_label(r"$\widehat{\tau}_{\mathrm{flip}}$")
    return figure


def render_persisted_field(dataset_path: Path) -> dict[str, object]:
    """Validate and render one complete first-flip field without dynamics."""

    dataset_path = Path(dataset_path)
    validation = validate_dataset(dataset_path)
    if not validation.accepted:
        raise RuntimeError(
            f"Dataset failed integrity validation: {validation.issues}"
        )
    snapshot = read_authoritative_field(dataset_path)
    if snapshot.resume_state.pending_tile_indices:
        raise RuntimeError("Cannot render an incomplete authoritative field.")

    png_path, pdf_path = derivative_output_paths(dataset_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    figure = build_figure(snapshot)
    try:
        figure.savefig(png_path, dpi=600)
        figure.savefig(pdf_path, dpi=600)
    finally:
        plt.close(figure)

    valid_cells = int(
        np.count_nonzero(snapshot.status == CellState.COMPLETED_VALID)
    )
    return {
        "dataset_path": str(dataset_path),
        "png_path": str(png_path),
        "pdf_path": str(pdf_path),
        "shape_theta2_theta1": list(snapshot.values.shape),
        "rendered_valid_cells": valid_cells,
        "masked_nonvalid_cells": int(snapshot.values.size - valid_cells),
        "rendered_censored_cells": int(np.count_nonzero(censored_cells(snapshot))),
        "dynamics_evaluator_imported": False,
    }


def censored_cells(snapshot: FieldSnapshot) -> np.ndarray:
    """Return the explicit right-censored mask from authoritative field data."""

    observable = snapshot.metadata["observable_provenance"]["name"]
    if observable != FIRST_FLIP_OBSERVABLE:
        raise ValueError(
            "First-flip renderer requires observable "
            f"{FIRST_FLIP_OBSERVABLE!r}; got {observable!r}."
        )
    valid = snapshot.status == CellState.COMPLETED_VALID
    horizon = float(
        snapshot.metadata["numerical_parameters"][
            "dimensionless_observation_horizon"
        ]
    )
    return valid & (snapshot.values == horizon)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        type=Path,
        help=(
            "Completed authoritative first-flip HDF5 field. PNG and PDF "
            "derivatives are written beside it with the same filename stem."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    print(json.dumps(render_persisted_field(arguments.dataset), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
