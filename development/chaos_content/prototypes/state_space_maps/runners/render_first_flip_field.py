"""Render continuous and explicitly classified first-flip representations.

The established continuous path consumes authoritative persisted HDF5.  The
long-horizon categorical path consumes precomputed consensus classes and never
infers them from a single field.  Neither path runs dynamics.
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
from ..src.logarithmic_first_flip import (
    LOGARITHMIC_CLASS_ORDER,
    FirstFlipLogarithmicClass,
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
LOGARITHMIC_CLASS_COLORS = {
    FirstFlipLogarithmicClass.TAU_HAT_LT_1: "#FFF7EC",
    FirstFlipLogarithmicClass.TAU_HAT_1_TO_10: "#FDD49E",
    FirstFlipLogarithmicClass.TAU_HAT_10_TO_100: "#FC8D59",
    FirstFlipLogarithmicClass.TAU_HAT_100_TO_1000: "#EF6548",
    FirstFlipLogarithmicClass.TAU_HAT_1000_TO_10000: "#B30000",
    FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000: CENSORED_COLOR,
    FirstFlipLogarithmicClass.ENERGY_INACCESSIBLE: "#25324B",
    FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED: "#8E44AD",
}
LOGARITHMIC_CLASS_LABELS = {
    FirstFlipLogarithmicClass.TAU_HAT_LT_1: r"$\widehat{\tau}<1$",
    FirstFlipLogarithmicClass.TAU_HAT_1_TO_10: r"$1\leq\widehat{\tau}<10$",
    FirstFlipLogarithmicClass.TAU_HAT_10_TO_100: r"$10\leq\widehat{\tau}<100$",
    FirstFlipLogarithmicClass.TAU_HAT_100_TO_1000: (
        r"$100\leq\widehat{\tau}<1000$"
    ),
    FirstFlipLogarithmicClass.TAU_HAT_1000_TO_10000: (
        r"$1000\leq\widehat{\tau}<10000$"
    ),
    FirstFlipLogarithmicClass.NO_FLIP_OBSERVED_BY_H10000: (
        r"No flip observed by $\widehat{H}=10000$"
    ),
    FirstFlipLogarithmicClass.ENERGY_INACCESSIBLE: "Energy inaccessible",
    FirstFlipLogarithmicClass.NUMERICALLY_UNRESOLVED: "Numerically unresolved",
}


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


def build_logarithmic_consensus_figure(
    classifications: Sequence[Sequence[FirstFlipLogarithmicClass | str]],
    *,
    theta1_axis: Sequence[float],
    theta2_axis: Sequence[float],
) -> Figure:
    """Build the distinct categorical view from precomputed consensus classes.

    This function does not accept a continuous ``FieldSnapshot`` and does not
    infer consensus from a single authoritative field.  Its caller must supply
    classes already derived from the trusted per-policy outcomes.
    """

    raw = np.asarray(classifications, dtype=object)
    first_axis = np.asarray(theta1_axis, dtype=float)
    second_axis = np.asarray(theta2_axis, dtype=float)
    if raw.ndim != 2 or raw.shape != (len(second_axis), len(first_axis)):
        raise ValueError(
            "classifications must use [theta2_index, theta1_index] orientation"
        )
    if (
        first_axis.ndim != 1
        or second_axis.ndim != 1
        or len(first_axis) == 0
        or len(second_axis) == 0
        or not np.all(np.isfinite(first_axis))
        or not np.all(np.isfinite(second_axis))
        or (len(first_axis) > 1 and np.any(np.diff(first_axis) <= 0.0))
        or (len(second_axis) > 1 and np.any(np.diff(second_axis) <= 0.0))
    ):
        raise ValueError(
            "theta axes must be finite, nonempty, and strictly increasing"
        )

    normalized = np.empty(raw.shape, dtype=np.uint8)
    for index, value in np.ndenumerate(raw):
        try:
            semantic_class = (
                value
                if isinstance(value, FirstFlipLogarithmicClass)
                else FirstFlipLogarithmicClass(str(value))
            )
        except ValueError as error:
            raise ValueError(
                f"unsupported logarithmic class at {index}: {value!r}"
            ) from error
        normalized[index] = LOGARITHMIC_CLASS_ORDER.index(semantic_class)

    colors = [
        LOGARITHMIC_CLASS_COLORS[value] for value in LOGARITHMIC_CLASS_ORDER
    ]
    figure, axis = plt.subplots(figsize=(8.4, 6.4), constrained_layout=True)
    axis.imshow(
        normalized,
        origin="lower",
        interpolation="nearest",
        extent=(-np.pi, np.pi, -np.pi, np.pi),
        aspect="equal",
        cmap=ListedColormap(colors),
        vmin=-0.5,
        vmax=len(LOGARITHMIC_CLASS_ORDER) - 0.5,
    )
    axis.set_xticks(ANGLE_TICK_POSITIONS, ANGLE_TICK_LABELS)
    axis.set_yticks(ANGLE_TICK_POSITIONS, ANGLE_TICK_LABELS)
    axis.set_xlabel(r"$\theta_1(0)\;[\mathrm{rad}]$")
    axis.set_ylabel(r"$\theta_2(0)\;[\mathrm{rad}]$")
    axis.set_title(r"First-flip logarithmic consensus, $\widehat{H}=10000$")
    axis.legend(
        handles=tuple(
            Patch(
                facecolor=LOGARITHMIC_CLASS_COLORS[value],
                label=LOGARITHMIC_CLASS_LABELS[value],
            )
            for value in LOGARITHMIC_CLASS_ORDER
        ),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
    )
    return figure


def render_logarithmic_consensus(
    classifications: Sequence[Sequence[FirstFlipLogarithmicClass | str]],
    *,
    theta1_axis: Sequence[float],
    theta2_axis: Sequence[float],
    output_path: Path,
) -> dict[str, object]:
    """Write one diagnostic PNG from already-computed consensus classes."""

    output = Path(output_path)
    if output.suffix.lower() != ".png":
        raise ValueError("logarithmic consensus diagnostic output must be a PNG")
    figure = build_logarithmic_consensus_figure(
        classifications,
        theta1_axis=theta1_axis,
        theta2_axis=theta2_axis,
    )
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output, dpi=180)
    finally:
        plt.close(figure)

    normalized = np.asarray(classifications, dtype=object)
    counts = {
        value.value: sum(
            1
            for item in normalized.flat
            if (
                item
                if isinstance(item, FirstFlipLogarithmicClass)
                else FirstFlipLogarithmicClass(str(item))
            )
            is value
        )
        for value in LOGARITHMIC_CLASS_ORDER
    }
    return {
        "output_path": str(output),
        "shape_theta2_theta1": list(normalized.shape),
        "class_counts": counts,
        "source": "already_computed_consensus_classes",
        "dynamics_evaluator_imported": False,
    }


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
