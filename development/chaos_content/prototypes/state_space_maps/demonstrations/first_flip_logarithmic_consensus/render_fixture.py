"""Render the non-scientific all-classes first-flip consensus fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from ...runners.render_first_flip_field import render_logarithmic_consensus
from ...src.logarithmic_first_flip import (
    LONG_HORIZON_HAT,
    FirstFlipLogarithmicClass,
    TrustedPolicyFirstFlipOutcome,
    TrustedPolicyOutcomeStatus,
    classify_zero_velocity_consensus,
)


HERE = Path(__file__).resolve().parent
DEFAULT_FIXTURE = HERE / "fixture.json"
DEFAULT_OUTPUT = HERE / "first_flip_logarithmic_consensus_fixture.png"


def load_fixture_classes(
    fixture_path: Path = DEFAULT_FIXTURE,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Classify the fixture's synthetic outcomes without running dynamics."""

    payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    if payload["artifact_kind"] != "non_scientific_semantic_fixture":
        raise ValueError("fixture must explicitly declare its non-scientific role")
    if float(payload["dimensionless_horizon"]) != LONG_HORIZON_HAT:
        raise ValueError("fixture horizon must match the supported long horizon")

    theta1_axis = np.asarray(payload["theta1_axis"], dtype=float)
    theta2_axis = np.asarray(payload["theta2_axis"], dtype=float)
    classes = np.empty((len(theta2_axis), len(theta1_axis)), dtype=object)
    assigned = np.zeros(classes.shape, dtype=bool)
    for cell in payload["cells"]:
        theta2_index, theta1_index = cell["index_theta2_theta1"]
        if assigned[theta2_index, theta1_index]:
            raise ValueError("fixture cell indices must be unique")
        outcomes = tuple(
            TrustedPolicyFirstFlipOutcome(
                policy=item["policy"],
                status=TrustedPolicyOutcomeStatus(item["status"]),
                dimensionless_event_time=item.get("dimensionless_event_time"),
            )
            for item in cell["outcomes"]
        )
        result = classify_zero_velocity_consensus(
            theta1_axis[theta1_index],
            theta2_axis[theta2_index],
            outcomes,
        )
        expected = FirstFlipLogarithmicClass(cell["expected_class"])
        if result is not expected:
            raise ValueError(
                f"fixture expectation mismatch at {(theta2_index, theta1_index)}"
            )
        classes[theta2_index, theta1_index] = result
        assigned[theta2_index, theta1_index] = True
    if not np.all(assigned):
        raise ValueError("fixture must assign every displayed cell")
    return theta1_axis, theta2_axis, classes


def render_fixture(
    fixture_path: Path = DEFAULT_FIXTURE,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, object]:
    """Execute fixture outcomes -> consensus classification -> renderer."""

    theta1_axis, theta2_axis, classes = load_fixture_classes(fixture_path)
    result = render_logarithmic_consensus(
        classes,
        theta1_axis=theta1_axis,
        theta2_axis=theta2_axis,
        output_path=output_path,
    )
    return {
        **result,
        "fixture_path": str(fixture_path),
        "artifact_kind": "non_scientific_semantic_fixture",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    print(
        json.dumps(
            render_fixture(arguments.fixture, arguments.output),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
