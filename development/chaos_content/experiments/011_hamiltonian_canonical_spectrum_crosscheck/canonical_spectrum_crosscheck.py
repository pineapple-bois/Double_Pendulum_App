"""Experiment 011 Phase A: validate an independent canonical tangent primitive.

The canonical flow and its Jacobian are derived directly from the repository's
symbolic simple-model Hamiltonian.  The accepted Experiment 006 Euler--Lagrange
flow is imported only as an independent comparison reference.  This module
does not implement QR or a long-time spectrum calculation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp


EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.double_pendulum.math import functions as mechanics
from src.double_pendulum.models.initial_conditions import (
    angular_velocities_to_canonical_momenta,
)


def _load_experiment006() -> Any:
    path = (
        EXPERIMENT_ROOT.parent
        / "006_variational_dynamics_validation"
        / "variational_dynamics_validation.py"
    )
    spec = importlib.util.spec_from_file_location("experiment006_for_011", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Experiment 006 from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


experiment006 = _load_experiment006()

EXPERIMENT_STATUS = "phase_a_accepted"
CANONICAL_STATE_ORDER = ("theta1", "theta2", "p_theta_1", "p_theta_2")
EL_STATE_ORDER = ("theta1", "theta2", "omega1", "omega2")
EVIDENCE_SEQUENCE = (
    "canonical_state_and_formulation",
    "el_canonical_state_equivalence",
    "reference_flow_equivalence",
    "canonical_tangent_and_jacobian_validation",
    "canonical_qr_validation",
    "long_time_spectrum_comparison",
)

PARAMETERS = dict(experiment006.PARAMETERS)
INITIAL_EL_STATE = np.array(experiment006.BASE_STATE_RADIANS, dtype=float)
INITIAL_EL_TANGENT = np.array(experiment006.INITIAL_TANGENT_PHYSICAL, dtype=float)
END_TIME_SECONDS = 1.29
OUTPUT_INTERVAL_SECONDS = 0.01
BASELINE_MAX_STEP = 0.0099773571
REFINED_MAX_STEP = BASELINE_MAX_STEP / 2.0
BASELINE_POLICY = {"method": "DOP853", "rtol": 1.0e-9, "atol": 1.0e-11}
REFINED_POLICY = {"method": "DOP853", "rtol": 1.0e-11, "atol": 1.0e-13}
JACOBIAN_STEPS = tuple(10.0 ** -power for power in range(2, 9))
JACOBIAN_ASSESSMENT_STEP = 1.0e-6

LIMITS = {
    "state_roundtrip_absolute": 1.0e-12,
    "tangent_inverse_absolute": 1.0e-12,
    "state_map_directional_relative": 5.0e-6,
    "normalized_energy_equivalence": 1.0e-12,
    "initial_state_absolute": 1.0e-14,
    "periodicity_absolute": 1.0e-9,
    "jacobian_directional_relative": 5.0e-5,
    "hamiltonian_matrix_residual": 1.0e-10,
    "baseline_reference_candidate_a": 1.0e-7,
    "refined_reference_candidate_a": 2.0e-8,
    "normalized_energy_drift": 1.0e-7,
    "canonical_policy_candidate_a": 1.0e-6,
    "tangent_relative_norm": 1.0e-6,
    "tangent_log_growth_absolute": 1.0e-6,
    "tangent_direction_component": 1.0e-6,
    "tangent_direction_cosine_shortfall": 1.0e-10,
    "metric_reconstruction_absolute": 1.0e-12,
}


@dataclass(frozen=True)
class SpectrumTarget:
    """Accepted Experiment 010 comparison target, not an Experiment 011 result."""

    mean_per_second: tuple[float, float, float, float]
    descriptive_half_width_per_second: tuple[float, float, float, float]
    provenance: str


EXPERIMENT_010_TARGET = SpectrumTarget(
    mean_per_second=(0.983276, 0.012274, -0.009941, -0.986532),
    descriptive_half_width_per_second=(0.023858, 0.006367, 0.008376, 0.024798),
    provenance=(
        "development/chaos_content/experiments/"
        "010_independent_shadow_640s_compatibility/README.md"
    ),
)


@dataclass(frozen=True)
class SourceAsset:
    role: str
    path: str
    symbols: tuple[str, ...]
    authority: str


SOURCE_ASSETS = (
    SourceAsset(
        "canonical state and EL-to-canonical map",
        "src/double_pendulum/models/initial_conditions.py",
        (
            "HAMILTONIAN_STATE_VARIABLE_NAMES",
            "angular_velocities_to_canonical_momenta",
            "hamiltonian_solver_initial_conditions",
        ),
        "accepted_production_model_convention",
    ),
    SourceAsset(
        "symbolic simple Hamiltonian and Hamilton equations",
        "src/double_pendulum/math/functions.py",
        ("compute_hamiltonian", "compute_hamiltons_equations", "hamiltonian_system"),
        "accepted_production_symbolic_asset",
    ),
    SourceAsset(
        "production canonical solver wrapper",
        "src/double_pendulum/models/hamiltonian.py",
        ("hamiltonian_first_order_system", "DoublePendulumHamiltonian"),
        "accepted_production_model_convention",
    ),
    SourceAsset(
        "explicit numerical Hamiltonian reference",
        "development/chaos_content/experiments/001_hamiltonian_poincare/"
        "minimal_hamiltonian_poincare.py",
        ("inertia_matrix", "hamiltonian", "angular_velocities", "hamiltonian_rhs"),
        "exploratory_reference_not_used_as_authority",
    ),
)


class CanonicalModelProtocol(Protocol):
    def el_to_canonical(self, el_state: Sequence[float]) -> Sequence[float]: ...
    def canonical_to_el(self, canonical_state: Sequence[float]) -> Sequence[float]: ...
    def energy(self, canonical_state: Sequence[float]) -> float: ...
    def rhs(self, time: float, canonical_state: Sequence[float]) -> Sequence[float]: ...
    def jacobian(self, time: float, canonical_state: Sequence[float]) -> Sequence[Sequence[float]]: ...


def scaffold_manifest() -> dict[str, Any]:
    """Keep the committed scaffold provenance visible after Phase A."""

    return {
        "experiment": "011_hamiltonian_canonical_spectrum_crosscheck",
        "status": "scaffold_history_preserved",
        "scientific_result_available": False,
        "canonical_state_order": list(CANONICAL_STATE_ORDER),
        "el_state_order": list(EL_STATE_ORDER),
        "experiment_010_target": asdict(EXPERIMENT_010_TARGET),
        "evidence_sequence": list(EVIDENCE_SEQUENCE),
        "source_assets": [asdict(asset) for asset in SOURCE_ASSETS],
        "claim_boundary": "The scaffold itself contains no scientific result.",
    }


def missing_source_paths(repository_root: Path) -> tuple[str, ...]:
    return tuple(
        asset.path for asset in SOURCE_ASSETS if not (repository_root / asset.path).is_file()
    )


def _inertia_matrix(angles: Sequence[float]) -> np.ndarray:
    q1, q2 = np.asarray(angles, dtype=float)
    mass1 = float(PARAMETERS[mechanics.m1])
    mass2 = float(PARAMETERS[mechanics.m2])
    length1 = float(PARAMETERS[mechanics.l1])
    length2 = float(PARAMETERS[mechanics.l2])
    cross = mass2 * length1 * length2 * math.cos(q1 - q2)
    return np.array(
        [[(mass1 + mass2) * length1**2, cross], [cross, mass2 * length2**2]],
        dtype=float,
    )


def el_to_canonical(el_state: Sequence[float]) -> np.ndarray:
    state = np.asarray(el_state, dtype=float)
    q = state[..., :2]
    omega = state[..., 2:]
    flat_q = q.reshape(-1, 2)
    flat_omega = omega.reshape(-1, 2)
    momenta = np.array([_inertia_matrix(a) @ w for a, w in zip(flat_q, flat_omega)])
    return np.concatenate((q, momenta.reshape(omega.shape)), axis=-1)


def canonical_to_el(canonical_state: Sequence[float]) -> np.ndarray:
    state = np.asarray(canonical_state, dtype=float)
    q = state[..., :2]
    p = state[..., 2:]
    flat_q = q.reshape(-1, 2)
    flat_p = p.reshape(-1, 2)
    omega = np.array([np.linalg.solve(_inertia_matrix(a), b) for a, b in zip(flat_q, flat_p)])
    return np.concatenate((q, omega.reshape(p.shape)), axis=-1)


def forward_tangent_map(el_state: Sequence[float]) -> np.ndarray:
    """Return D(EL->canonical), derived from p=B(q) omega."""

    q1, q2, omega1, omega2 = np.asarray(el_state, dtype=float)
    coefficient = (
        float(PARAMETERS[mechanics.m2])
        * float(PARAMETERS[mechanics.l1])
        * float(PARAMETERS[mechanics.l2])
        * math.sin(q1 - q2)
    )
    result = np.zeros((4, 4), dtype=float)
    result[:2, :2] = np.eye(2)
    result[2:, 2:] = _inertia_matrix((q1, q2))
    result[2, 0] = -coefficient * omega2
    result[2, 1] = coefficient * omega2
    result[3, 0] = -coefficient * omega1
    result[3, 1] = coefficient * omega1
    return result


def inverse_tangent_map(canonical_state: Sequence[float]) -> np.ndarray:
    """Return D(canonical->EL) by the inverse-function theorem."""

    el_state = canonical_to_el(canonical_state)
    return np.linalg.inv(forward_tangent_map(el_state))


def candidate_a_scaling_matrix() -> np.ndarray:
    tc = experiment006.characteristic_time()
    return np.diag([1.0, 1.0, tc, tc])


def candidate_a_pullback_factor(canonical_state: Sequence[float]) -> np.ndarray:
    """Factor A(z) for ||delta z|| = ||A(z) delta z||_2."""

    return candidate_a_scaling_matrix() @ inverse_tangent_map(canonical_state)


class CanonicalDynamics:
    """Hamiltonian-derived canonical flow and independently derived Jacobian."""

    def __init__(self) -> None:
        self.state_symbols = sp.symbols("q1 q2 p1 p2", real=True)
        q1, q2, p1, p2 = self.state_symbols
        replacements = {
            mechanics.theta1: q1,
            mechanics.theta2: q2,
            mechanics.p_theta_1: p1,
            mechanics.p_theta_2: p2,
        }
        self.hamiltonian_expression = sp.simplify(
            mechanics.compute_hamiltonian("simple").subs(PARAMETERS).xreplace(replacements)
        )
        self.symplectic_matrix = sp.Matrix(
            [[0, 0, 1, 0], [0, 0, 0, 1], [-1, 0, 0, 0], [0, -1, 0, 0]]
        )
        gradient = sp.Matrix([sp.diff(self.hamiltonian_expression, item) for item in self.state_symbols])
        self.flow_expression = self.symplectic_matrix @ gradient
        self.jacobian_expression = self.flow_expression.jacobian(self.state_symbols)
        self._energy = sp.lambdify(self.state_symbols, self.hamiltonian_expression, "numpy")
        self._flow = sp.lambdify(self.state_symbols, self.flow_expression, "numpy")
        self._jacobian = sp.lambdify(self.state_symbols, self.jacobian_expression, "numpy")

    def energy(self, canonical_state: Sequence[float]) -> float:
        return float(self._energy(*np.asarray(canonical_state, dtype=float)))

    def flow(self, canonical_state: Sequence[float], time_value: float = 0.0) -> np.ndarray:
        del time_value
        return np.asarray(self._flow(*np.asarray(canonical_state, dtype=float)), dtype=float).reshape(4)

    def jacobian(self, canonical_state: Sequence[float], time_value: float = 0.0) -> np.ndarray:
        del time_value
        return np.asarray(self._jacobian(*np.asarray(canonical_state, dtype=float)), dtype=float).reshape(4, 4)

    def augmented_rhs(self, time_value: float, augmented: Sequence[float]) -> np.ndarray:
        state = np.asarray(augmented, dtype=float)
        return np.concatenate(
            (self.flow(state[:4], time_value), self.jacobian(state[:4], time_value) @ state[4:])
        )


REPRESENTATIVE_EL_STATES = np.array(
    [
        INITIAL_EL_STATE,
        [0.3, -0.7, 1.2, -0.8],
        [-2.9, 2.7, -1.5, 2.2],
        [math.pi - 1.0e-7, -math.pi + 2.0e-7, 0.4, -0.3],
    ],
    dtype=float,
)
STATE_MAP_DIRECTIONS = np.array(
    [[0.3, -0.4, 0.7, -0.2], [-0.2, 0.5, -0.3, 0.8]], dtype=float
)
JACOBIAN_DIRECTIONS = np.array(
    [[0.3, -0.4, 0.7, -0.2], [-0.6, 0.2, 0.1, 0.75], [0.1, 0.8, -0.5, 0.3]],
    dtype=float,
)
PERIODIC_SHIFTS = ((1, 0), (0, -2), (3, -1), (-2, 4))


def _time_grid() -> np.ndarray:
    count = int(round(END_TIME_SECONDS / OUTPUT_INTERVAL_SECONDS)) + 1
    return np.linspace(0.0, END_TIME_SECONDS, count)


def _solve(rhs: Any, initial: np.ndarray, policy: dict[str, Any], max_step: float) -> dict[str, Any]:
    time = _time_grid()
    result = solve_ivp(
        rhs,
        (0.0, END_TIME_SECONDS),
        np.asarray(initial, dtype=float),
        t_eval=time,
        max_step=max_step,
        **policy,
    )
    states = np.asarray(result.y.T, dtype=float)
    return {
        "accepted": bool(
            result.success
            and result.t.shape == time.shape
            and np.allclose(result.t, time, rtol=0.0, atol=1.0e-13)
            and states.shape == (len(time), len(initial))
            and np.all(np.isfinite(states))
        ),
        "time": np.asarray(result.t, dtype=float),
        "state": states,
        "statistics": {
            "success": bool(result.success),
            "message": str(result.message),
            "nfev": int(result.nfev),
            "njev": int(result.njev),
            "nlu": int(result.nlu),
            "max_step_seconds": max_step,
            "requested_samples": len(time),
            "returned_samples": len(result.t),
        },
    }


def _wrapped_el_difference(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    difference = np.asarray(second) - np.asarray(first)
    result = np.array(difference, copy=True)
    result[..., :2] = experiment006.wrap_angle_difference(result[..., :2])
    return result


def _relative_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.linalg.norm(actual - expected) / max(np.linalg.norm(expected), 1.0e-15))


def _public(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.bool_, np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {key: _public(item) for key, item in value.items() if not key.startswith("_")}
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    return value


def validate_state_maps(dynamics: CanonicalDynamics) -> dict[str, Any]:
    state_roundtrips: list[float] = []
    canonical_roundtrips: list[float] = []
    tangent_inverse_errors: list[float] = []
    directional_errors: list[float] = []
    production_map_errors: list[float] = []
    step = 1.0e-6
    for el_state in REPRESENTATIVE_EL_STATES:
        canonical = el_to_canonical(el_state)
        state_roundtrips.append(float(np.max(np.abs(canonical_to_el(canonical) - el_state))))
        canonical_roundtrips.append(
            float(np.max(np.abs(el_to_canonical(canonical_to_el(canonical)) - canonical)))
        )
        production_p = angular_velocities_to_canonical_momenta(PARAMETERS, el_state, "simple")
        production_map_errors.append(float(np.max(np.abs(production_p - canonical[2:]))))
        forward = forward_tangent_map(el_state)
        inverse = inverse_tangent_map(canonical)
        tangent_inverse_errors.append(float(np.max(np.abs(inverse @ forward - np.eye(4)))))
        for direction in STATE_MAP_DIRECTIONS:
            numerical = (el_to_canonical(el_state + step * direction) - el_to_canonical(el_state - step * direction)) / (2 * step)
            directional_errors.append(_relative_error(numerical, forward @ direction))
    initial_canonical = el_to_canonical(INITIAL_EL_STATE)
    checks = {
        "el_roundtrip": max(state_roundtrips) <= LIMITS["state_roundtrip_absolute"],
        "canonical_roundtrip": max(canonical_roundtrips) <= LIMITS["state_roundtrip_absolute"],
        "production_forward_map": max(production_map_errors) <= LIMITS["state_roundtrip_absolute"],
        "tangent_inverse": max(tangent_inverse_errors) <= LIMITS["tangent_inverse_absolute"],
        "state_map_directional_fd": max(directional_errors) <= LIMITS["state_map_directional_relative"],
        "initial_state": np.max(np.abs(initial_canonical[:2] - INITIAL_EL_STATE[:2])) <= LIMITS["initial_state_absolute"] and np.max(np.abs(initial_canonical[2:])) <= LIMITS["initial_state_absolute"],
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "maximum_el_roundtrip_absolute_error": max(state_roundtrips),
        "maximum_canonical_roundtrip_absolute_error": max(canonical_roundtrips),
        "maximum_production_map_absolute_error": max(production_map_errors),
        "maximum_tangent_inverse_absolute_error": max(tangent_inverse_errors),
        "maximum_state_map_directional_relative_error": max(directional_errors),
        "initial_canonical_state": initial_canonical,
    }


def validate_energy_and_periodicity(dynamics: CanonicalDynamics) -> dict[str, Any]:
    energy_errors: list[float] = []
    direct_energy_errors: list[float] = []
    periodic_energy: list[float] = []
    periodic_flow: list[float] = []
    periodic_jacobian: list[float] = []
    scale = experiment006.energy_scale()
    mass1 = float(PARAMETERS[mechanics.m1])
    mass2 = float(PARAMETERS[mechanics.m2])
    length1 = float(PARAMETERS[mechanics.l1])
    length2 = float(PARAMETERS[mechanics.l2])
    gravity = float(PARAMETERS[mechanics.g])
    for el_state in REPRESENTATIVE_EL_STATES:
        canonical = el_to_canonical(el_state)
        energy = dynamics.energy(canonical)
        energy_errors.append(abs(energy - float(experiment006.simple_energy(el_state))) / scale)
        q = canonical[:2]
        p = canonical[2:]
        potential = -(mass1 + mass2) * gravity * length1 * math.cos(q[0]) - mass2 * gravity * length2 * math.cos(q[1])
        direct = 0.5 * float(p @ np.linalg.solve(_inertia_matrix(q), p)) + potential
        direct_energy_errors.append(abs(energy - direct) / scale)
        for n1, n2 in PERIODIC_SHIFTS:
            shifted = canonical + np.array([2 * math.pi * n1, 2 * math.pi * n2, 0.0, 0.0])
            periodic_energy.append(abs(dynamics.energy(shifted) - energy))
            periodic_flow.append(float(np.max(np.abs(dynamics.flow(shifted) - dynamics.flow(canonical)))))
            periodic_jacobian.append(float(np.max(np.abs(dynamics.jacobian(shifted) - dynamics.jacobian(canonical)))))
    maximum_periodicity = max(periodic_energy + periodic_flow + periodic_jacobian)
    checks = {
        "el_energy_equivalence": max(energy_errors) <= LIMITS["normalized_energy_equivalence"],
        "independent_matrix_energy_equivalence": max(direct_energy_errors) <= LIMITS["normalized_energy_equivalence"],
        "canonical_periodicity": maximum_periodicity <= LIMITS["periodicity_absolute"],
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "maximum_normalized_el_energy_difference": max(energy_errors),
        "maximum_normalized_direct_energy_difference": max(direct_energy_errors),
        "maximum_periodic_energy_absolute_error": max(periodic_energy),
        "maximum_periodic_flow_absolute_error": max(periodic_flow),
        "maximum_periodic_jacobian_absolute_error": max(periodic_jacobian),
    }


def _reference_runs(dynamics: CanonicalDynamics) -> dict[str, Any]:
    el_dynamics = experiment006.VariationalDynamics()
    initial_canonical = el_to_canonical(INITIAL_EL_STATE)
    runs: dict[str, Any] = {}
    for name, policy, max_step in (
        ("baseline", BASELINE_POLICY, BASELINE_MAX_STEP),
        ("refined", REFINED_POLICY, REFINED_MAX_STEP),
    ):
        el_run = _solve(lambda time, state: el_dynamics.flow(state, time), INITIAL_EL_STATE, policy, max_step)
        canonical_run = _solve(lambda time, state: dynamics.flow(state, time), initial_canonical, policy, max_step)
        canonical_as_el = canonical_to_el(canonical_run["state"])
        separation = experiment006.candidate_a_norm(_wrapped_el_difference(el_run["state"], canonical_as_el))
        el_energy = experiment006.simple_energy(el_run["state"])
        canonical_energy = np.array([dynamics.energy(state) for state in canonical_run["state"]])
        scale = experiment006.energy_scale()
        runs[name] = {
            "accepted": el_run["accepted"] and canonical_run["accepted"],
            "maximum_el_canonical_candidate_a_distance": float(np.max(separation)),
            "final_el_canonical_candidate_a_distance": float(separation[-1]),
            "maximum_normalized_el_energy_drift": float(np.max(np.abs(el_energy - el_energy[0])) / scale),
            "maximum_normalized_canonical_energy_drift": float(np.max(np.abs(canonical_energy - canonical_energy[0])) / scale),
            "el_solver_statistics": el_run["statistics"],
            "canonical_solver_statistics": canonical_run["statistics"],
            "_el": el_run["state"],
            "_canonical": canonical_run["state"],
            "_canonical_as_el": canonical_as_el,
        }
    canonical_policy_distance = experiment006.candidate_a_norm(
        _wrapped_el_difference(runs["baseline"]["_canonical_as_el"], runs["refined"]["_canonical_as_el"])
    )
    checks = {
        "baseline_flow_equivalence": runs["baseline"]["maximum_el_canonical_candidate_a_distance"] <= LIMITS["baseline_reference_candidate_a"],
        "refined_flow_equivalence": runs["refined"]["maximum_el_canonical_candidate_a_distance"] <= LIMITS["refined_reference_candidate_a"],
        "all_energy_drifts": max(runs[name][key] for name in runs for key in ("maximum_normalized_el_energy_drift", "maximum_normalized_canonical_energy_drift")) <= LIMITS["normalized_energy_drift"],
        "canonical_policy_refinement": float(np.max(canonical_policy_distance)) <= LIMITS["canonical_policy_candidate_a"],
        "solver_success": all(runs[name]["accepted"] for name in runs),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "runs": runs,
        "maximum_baseline_refined_canonical_candidate_a_distance": float(np.max(canonical_policy_distance)),
    }


def validate_jacobian(dynamics: CanonicalDynamics, reference_runs: dict[str, Any]) -> dict[str, Any]:
    trajectory = reference_runs["runs"]["refined"]["_canonical"]
    states = [el_to_canonical(item) for item in REPRESENTATIVE_EL_STATES]
    states.extend(trajectory[index] for index in (43, 87, 129))
    records: list[dict[str, Any]] = []
    assessment_errors: list[float] = []
    structural_residuals: list[float] = []
    symplectic = np.array(dynamics.symplectic_matrix.tolist(), dtype=float)
    for state_index, state in enumerate(states):
        jacobian = dynamics.jacobian(state)
        structural_residuals.append(float(np.linalg.norm(jacobian.T @ symplectic + symplectic @ jacobian, ord=np.inf)))
        for direction_index, raw_direction in enumerate(JACOBIAN_DIRECTIONS):
            direction = raw_direction / np.linalg.norm(raw_direction)
            expected = jacobian @ direction
            errors: dict[str, float] = {}
            for step in JACOBIAN_STEPS:
                numerical = (dynamics.flow(state + step * direction) - dynamics.flow(state - step * direction)) / (2 * step)
                error = _relative_error(numerical, expected)
                errors[f"{step:.0e}"] = error
                if math.isclose(step, JACOBIAN_ASSESSMENT_STEP, rel_tol=0.0, abs_tol=1.0e-18):
                    assessment_errors.append(error)
            records.append({"state_index": state_index, "direction_index": direction_index, "relative_error_by_step": errors})
    checks = {
        "directional_finite_difference": max(assessment_errors) <= LIMITS["jacobian_directional_relative"],
        "hamiltonian_matrix_structure": max(structural_residuals) <= LIMITS["hamiltonian_matrix_residual"],
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "tested_state_count": len(states),
        "tested_direction_count_per_state": len(JACOBIAN_DIRECTIONS),
        "maximum_assessment_relative_error": max(assessment_errors),
        "maximum_hamiltonian_matrix_residual": max(structural_residuals),
        "records": records,
    }


def validate_tangent(dynamics: CanonicalDynamics) -> dict[str, Any]:
    el_dynamics = experiment006.VariationalDynamics()
    initial_canonical = el_to_canonical(INITIAL_EL_STATE)
    initial_canonical_tangent = forward_tangent_map(INITIAL_EL_STATE) @ INITIAL_EL_TANGENT
    el_run = _solve(el_dynamics.augmented_rhs, np.concatenate((INITIAL_EL_STATE, INITIAL_EL_TANGENT)), REFINED_POLICY, REFINED_MAX_STEP)
    canonical_run = _solve(dynamics.augmented_rhs, np.concatenate((initial_canonical, initial_canonical_tangent)), REFINED_POLICY, REFINED_MAX_STEP)
    el_tangent = el_run["state"][:, 4:]
    canonical_tangent = canonical_run["state"][:, 4:]
    mapped_tangent = np.array([inverse_tangent_map(state) @ vector for state, vector in zip(canonical_run["state"][:, :4], canonical_tangent)])
    el_norm = experiment006.candidate_a_norm(el_tangent)
    mapped_norm = experiment006.candidate_a_norm(mapped_tangent)
    norm_relative = np.abs(mapped_norm - el_norm) / el_norm
    log_error = np.abs(np.log(mapped_norm / mapped_norm[0]) - np.log(el_norm / el_norm[0]))
    el_direction = experiment006.normalized_scaled_direction(el_tangent)
    mapped_direction = experiment006.normalized_scaled_direction(mapped_tangent)
    component_error = np.max(np.abs(mapped_direction - el_direction), axis=1)
    cosine = np.sum(mapped_direction * el_direction, axis=1)
    checks = {
        "solver_success": el_run["accepted"] and canonical_run["accepted"],
        "relative_norm": float(np.max(norm_relative)) <= LIMITS["tangent_relative_norm"],
        "log_growth": float(np.max(log_error)) <= LIMITS["tangent_log_growth_absolute"],
        "direction_components": float(np.max(component_error)) <= LIMITS["tangent_direction_component"],
        "signed_direction_cosine": float(np.min(cosine)) >= 1.0 - LIMITS["tangent_direction_cosine_shortfall"],
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "initial_canonical_tangent": initial_canonical_tangent,
        "maximum_relative_candidate_a_norm_error": float(np.max(norm_relative)),
        "maximum_absolute_log_growth_error": float(np.max(log_error)),
        "maximum_scaled_direction_component_error": float(np.max(component_error)),
        "minimum_signed_direction_cosine": float(np.min(cosine)),
        "final_el_candidate_a_norm": float(el_norm[-1]),
        "final_mapped_canonical_candidate_a_norm": float(mapped_norm[-1]),
        "el_solver_statistics": el_run["statistics"],
        "canonical_solver_statistics": canonical_run["statistics"],
    }


def validate_metric_contract(reference_runs: dict[str, Any]) -> dict[str, Any]:
    trajectory = reference_runs["runs"]["refined"]["_canonical"]
    condition_numbers: list[float] = []
    determinants: list[float] = []
    reconstruction_errors: list[float] = []
    for state in trajectory:
        factor = candidate_a_pullback_factor(state)
        condition_numbers.append(float(np.linalg.cond(factor)))
        determinants.append(float(np.linalg.det(factor)))
        reconstruction_errors.append(float(np.max(np.abs(factor @ np.linalg.inv(factor) - np.eye(4)))))
    fixed_momentum_scales = np.array(
        [
            (float(PARAMETERS[mechanics.m1]) + float(PARAMETERS[mechanics.m2])) * float(PARAMETERS[mechanics.l1]) ** 2 / experiment006.characteristic_time(),
            float(PARAMETERS[mechanics.m2]) * float(PARAMETERS[mechanics.l2]) ** 2 / experiment006.characteristic_time(),
        ]
    )
    checks = {
        "finite": bool(np.all(np.isfinite(condition_numbers + determinants + reconstruction_errors))),
        "nonsingular": min(abs(value) for value in determinants) > 0.0,
        "reconstruction": max(reconstruction_errors) <= LIMITS["metric_reconstruction_absolute"],
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "recommended_contract": "state-dependent Candidate-A pullback A(z)=S D(canonical_to_EL)(z)",
        "future_qr_reset": "Z=A(z)Y=QR; reset Y=A(z)^(-1)Q",
        "maximum_factor_condition_number": max(condition_numbers),
        "minimum_absolute_factor_determinant": min(abs(value) for value in determinants),
        "maximum_inverse_reconstruction_error": max(reconstruction_errors),
        "secondary_fixed_scaling_momentum_scales": fixed_momentum_scales,
        "conventional_boundary": "The pullback preserves the validated EL metric; no finite-time canonical QR metric is unique.",
    }


def _production_flow_symbolic_check(dynamics: CanonicalDynamics) -> dict[str, Any]:
    q1, q2, p1, p2 = dynamics.state_symbols
    replacements = {
        mechanics.theta1: q1,
        mechanics.theta2: q2,
        mechanics.p_theta_1: p1,
        mechanics.p_theta_2: p2,
        mechanics.omega1: dynamics.flow_expression[0],
        mechanics.omega2: dynamics.flow_expression[1],
    }
    equations = mechanics.hamiltonian_system("simple")
    rhs = [equation.rhs.subs(PARAMETERS).xreplace(replacements) for equation in equations]
    differences = [sp.simplify(actual - expected) for actual, expected in zip(dynamics.flow_expression, rhs)]
    return {"accepted": all(value == 0 for value in differences), "simplified_differences": [str(value) for value in differences]}


def run_phase_a(output_dir: Path | None = None) -> dict[str, Any]:
    dynamics = CanonicalDynamics()
    state_maps = validate_state_maps(dynamics)
    energy_periodicity = validate_energy_and_periodicity(dynamics)
    references = _reference_runs(dynamics)
    jacobian = validate_jacobian(dynamics, references)
    tangent = validate_tangent(dynamics)
    metric = validate_metric_contract(references)
    production_flow = _production_flow_symbolic_check(dynamics)
    groups = {
        "production_flow_ordering": production_flow,
        "state_map_validation": state_maps,
        "energy_and_periodicity_validation": energy_periodicity,
        "reference_flow_validation": references,
        "jacobian_validation": jacobian,
        "tangent_validation": tangent,
        "metric_analysis": metric,
    }
    accepted = all(group["accepted"] for group in groups.values())
    summary = {
        "experiment": "011_hamiltonian_canonical_spectrum_crosscheck",
        "phase": "A_canonical_reference_and_tangent_primitive",
        "accepted": accepted,
        "verdict": "accepted_canonical_reference_and_tangent_primitive" if accepted else "unresolved_or_rejected_phase_a",
        "claim_boundary": "No canonical QR or Lyapunov spectrum was computed.",
        "canonical_state_order": list(CANONICAL_STATE_ORDER),
        "el_state_order": list(EL_STATE_ORDER),
        "parameters": {str(key): value for key, value in PARAMETERS.items()},
        "initial_el_state": INITIAL_EL_STATE,
        "duration_seconds": END_TIME_SECONDS,
        "output_interval_seconds": OUTPUT_INTERVAL_SECONDS,
        "policies": {
            "baseline": BASELINE_POLICY | {"max_step": BASELINE_MAX_STEP},
            "refined": REFINED_POLICY | {"max_step": REFINED_MAX_STEP},
        },
        "predeclared_limits": LIMITS,
        "groups": groups,
        "experiment_010_target_not_tested": asdict(EXPERIMENT_010_TARGET),
    }
    public_summary = _public(summary)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_path = output_dir / "summary.json"
        jacobian_path = output_dir / "jacobian_validation.json"
        summary_path.write_text(json.dumps(public_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        jacobian_path.write_text(json.dumps(_public(jacobian), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest = {
            "experiment": public_summary["experiment"],
            "phase": public_summary["phase"],
            "accepted": accepted,
            "files": {
                path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
                for path in (summary_path, jacobian_path)
            },
        }
        (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def assert_self_check(summary: dict[str, Any]) -> None:
    if not summary["accepted"]:
        failed = [name for name, group in summary["groups"].items() if not group["accepted"]]
        raise AssertionError(f"Phase A validation failed: {failed}")
    if summary["claim_boundary"] != "No canonical QR or Lyapunov spectrum was computed.":
        raise AssertionError("Experiment claim boundary changed unexpectedly.")


def run_crosscheck() -> None:
    """Deliberately refuse the future long-time spectrum calculation."""

    raise NotImplementedError("Experiment 011 Phase A does not implement canonical QR or a Hamiltonian spectrum.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "development/chaos_content/outputs/hamiltonian_canonical_phase_a/baseline",
    )
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = run_phase_a(args.output_dir)
    if args.self_check:
        assert_self_check(result)
    print(json.dumps(_public(result), indent=2, sort_keys=True))
