"""Phase 6 / Tier 1C/1D Hamiltonian convention audit helper.

Run from the repository root:

    .venv/bin/python development/simulation_workbench/tier_1/tier1c_hamiltonian_convention.py

The script records compact evidence about the UI-shaped initial-condition
convention and Hamiltonian solver state. It does not modify production model
behavior.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "double_pendulum_app_matplotlib_cache"),
)
os.environ.setdefault(
    "XDG_CACHE_HOME",
    str(Path(tempfile.gettempdir()) / "double_pendulum_app_cache"),
)


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (
            (candidate / "AGENTS.md").is_file()
            and (candidate / "TIER4_README.md").is_file()
            and (candidate / "src" / "double_pendulum").is_dir()
        ):
            return candidate
    raise RuntimeError(f"Could not find repository root from {start}")


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian


OUTPUT_PATH = Path(__file__).with_name("tier1c_hamiltonian_convention_results.json")
TIME_VECTOR = [0.0, 0.1, 5]
TOLERANCE = 1e-12
REQUESTS_DEGREES = {
    "zero_tail": [45.0, -30.0, 0.0, 0.0],
    "nonzero_tail": [45.0, -30.0, 10.0, -5.0],
}


@dataclass(frozen=True)
class ConventionCase:
    model_type: str
    parameters: dict[Any, float]
    parameter_values: dict[str, float]


CASES = [
    ConventionCase(
        model_type="simple",
        parameters={l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81},
        parameter_values={"l1": 1.0, "l2": 1.0, "m1": 1.0, "m2": 1.0, "g": 9.81},
    ),
    ConventionCase(
        model_type="compound",
        parameters={l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81},
        parameter_values={"l1": 1.0, "l2": 1.0, "M1": 1.0, "M2": 1.0, "g": 9.81},
    ),
]


def shape_of(array) -> list[int]:
    return [int(value) for value in np.shape(array)]


def canonical_momenta_from_ui_velocities(case: ConventionCase, request_degrees: list[float]) -> np.ndarray:
    th1, th2, omega_1, omega_2 = np.deg2rad(request_degrees)
    delta_cos = np.cos(th1 - th2)

    if case.model_type == "simple":
        length_1 = case.parameter_values["l1"]
        length_2 = case.parameter_values["l2"]
        mass_1 = case.parameter_values["m1"]
        mass_2 = case.parameter_values["m2"]
        b11 = (mass_1 + mass_2) * length_1**2
        b12 = mass_2 * length_1 * length_2 * delta_cos
        b22 = mass_2 * length_2**2
    elif case.model_type == "compound":
        length_1 = case.parameter_values["l1"]
        length_2 = case.parameter_values["l2"]
        mass_1 = case.parameter_values["M1"]
        mass_2 = case.parameter_values["M2"]
        b11 = (7.0 / 12.0) * mass_1 * length_1**2 + 0.25 * mass_2 * length_1**2
        b12 = 0.25 * mass_2 * length_1 * length_2 * delta_cos
        b22 = (7.0 / 12.0) * mass_2 * length_2**2
    else:
        raise ValueError(f"Unsupported model type: {case.model_type}")

    return np.array(
        [
            b11 * omega_1 + b12 * omega_2,
            b12 * omega_1 + b22 * omega_2,
        ]
    )


def list_floats(values) -> list[float]:
    return [float(value) for value in values]


def run_case(case: ConventionCase, request_name: str, request_degrees: list[float]) -> dict[str, Any]:
    lagrangian = DoublePendulumLagrangian(
        case.parameters,
        list(request_degrees),
        list(TIME_VECTOR),
        model=case.model_type,
    )
    hamiltonian = DoublePendulumHamiltonian(
        case.parameters,
        list(request_degrees),
        list(TIME_VECTOR),
        model=case.model_type,
    )

    expected_momenta = canonical_momenta_from_ui_velocities(case, request_degrees)
    current_hamiltonian_tail = hamiltonian.initial_conditions[2:]
    difference = current_hamiltonian_tail - expected_momenta

    return {
        "model_type": case.model_type,
        "request_name": request_name,
        "parameters": case.parameter_values,
        "ui_request_degrees": list(request_degrees),
        "ui_request_radians": list_floats(np.deg2rad(request_degrees)),
        "lagrangian_state_variables": ["theta1", "theta2", "omega1", "omega2"],
        "hamiltonian_state_variables": ["theta1", "theta2", "p_theta_1", "p_theta_2"],
        "lagrangian_internal_initial_conditions": list_floats(lagrangian.initial_conditions),
        "hamiltonian_internal_initial_conditions": list_floats(hamiltonian.initial_conditions),
        "hamiltonian_current_tail": list_floats(current_hamiltonian_tail),
        "canonical_momenta_if_tail_is_angular_velocity": list_floats(expected_momenta),
        "tail_minus_expected_canonical_momenta": list_floats(difference),
        "max_abs_tail_momentum_difference": float(np.max(np.abs(difference))),
        "current_tail_matches_canonical_momenta": bool(
            np.allclose(current_hamiltonian_tail, expected_momenta, atol=TOLERANCE, rtol=0)
        ),
        "lagrangian_state_shape": shape_of(lagrangian.sol),
        "hamiltonian_state_shape": shape_of(hamiltonian.sol),
        "solver_success": {
            "lagrangian": getattr(lagrangian.solver_metadata, "success", None),
            "hamiltonian": getattr(hamiltonian.solver_metadata, "success", None),
        },
    }


def main() -> int:
    results = [
        run_case(case, request_name, request_degrees)
        for case in CASES
        for request_name, request_degrees in REQUESTS_DEGREES.items()
    ]
    summary = {
        "tier": "Phase 6 / Tier 1C and Tier 1D",
        "purpose": "Hamiltonian state-convention audit and conversion evidence",
        "time_vector": TIME_VECTOR,
        "tolerance": TOLERANCE,
        "notes": [
            "Tier 1D keeps UI initial conditions as theta1, theta2, omega1, omega2.",
            "The Hamiltonian constructor converts UI angular velocities to canonical momenta before solving.",
            "For Hamiltonian equations, the final two state values are canonical momenta.",
            "The zero-tail request is still checked, but the nonzero-tail request is the meaningful convention proof.",
        ],
        "momentum_mapping": {
            "simple": "p = [[(m1 + m2) * l1^2, m2 * l1 * l2 * cos(theta1 - theta2)], [m2 * l1 * l2 * cos(theta1 - theta2), m2 * l2^2]] @ omega",
            "compound": "p = [[7/12*M1*l1^2 + 1/4*M2*l1^2, 1/4*M2*l1*l2*cos(theta1 - theta2)], [1/4*M2*l1*l2*cos(theta1 - theta2), 7/12*M2*l2^2]] @ omega",
        },
        "results": results,
    }

    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print("Phase 6 / Tier 1C/1D Hamiltonian convention audit")
    print(f"Wrote compact JSON summary: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    for result in results:
        print(
            f"- {result['model_type']} {result['request_name']}: "
            f"tail_matches_canonical_momenta={result['current_tail_matches_canonical_momenta']} "
            f"max_abs_difference={result['max_abs_tail_momentum_difference']:.12g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
