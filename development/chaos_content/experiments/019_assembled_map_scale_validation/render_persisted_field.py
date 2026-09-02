"""Render an authoritative HDF5 field without importing dynamics code."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import sys
from pathlib import Path


_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_ROOT / "xdg"))

import matplotlib.pyplot as plt
import numpy as np


EXPERIMENT_ROOT = Path(__file__).resolve().parent
EXPERIMENT_018_ROOT = EXPERIMENT_ROOT.parent / "018_hdf5_persistence_boundary"
if str(EXPERIMENT_018_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_018_ROOT))

from hdf5_field_store import CellState, read_authoritative_field, validate_dataset


def render_field(dataset_path: Path, output_path: Path) -> dict[str, object]:
    validation = validate_dataset(dataset_path)
    if not validation.accepted:
        raise RuntimeError(f"Dataset failed integrity validation: {validation.issues}")
    snapshot = read_authoritative_field(dataset_path)
    if snapshot.resume_state.pending_tile_indices:
        raise RuntimeError("Cannot render an incomplete authoritative field.")

    visible = np.ma.masked_where(
        snapshot.status != CellState.COMPLETED_VALID,
        snapshot.values,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(7.2, 6.0), constrained_layout=True)
    image = axis.imshow(
        visible,
        origin="lower",
        interpolation="nearest",
        extent=(-np.pi, np.pi, -np.pi, np.pi),
        aspect="equal",
        cmap="viridis",
    )
    axis.set_xlabel(r"$\theta_1(0)$ [rad]")
    axis.set_ylabel(r"$\theta_2(0)$ [rad]")
    axis.set_title(r"Finite-time one-vector stretching rate, $T=5\,\mathrm{s}$")
    colorbar = figure.colorbar(image, ax=axis)
    colorbar.set_label(r"$\Lambda_T^{(1)}$ [$\mathrm{s}^{-1}$]")
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return {
        "dataset_path": str(dataset_path),
        "output_path": str(output_path),
        "shape_theta2_theta1": list(snapshot.values.shape),
        "rendered_valid_cells": int(
            np.count_nonzero(snapshot.status == CellState.COMPLETED_VALID)
        ),
        "masked_nonvalid_cells": int(
            np.count_nonzero(snapshot.status != CellState.COMPLETED_VALID)
        ),
        "dynamics_evaluator_imported": False,
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(render_field(arguments.dataset, arguments.output), sort_keys=True))


if __name__ == "__main__":
    _main()
