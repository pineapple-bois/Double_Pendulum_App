"""Experiment 011: validate canonical tangent and pullback-QR primitives.

The canonical flow and its Jacobian are derived directly from the repository's
symbolic simple-model Hamiltonian.  The accepted Experiment 006 Euler--Lagrange
flow is imported only as an independent comparison reference. Phase B adds a
short full-matrix QR comparison. Phase C applies that accepted primitive to
one frozen three-shadow, 640-second canonical/EL compatibility protocol.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from itertools import combinations
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
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.double_pendulum.math import functions as mechanics
from src.double_pendulum.models.initial_conditions import (
    angular_velocities_to_canonical_momenta,
)


def _load_experiment006() -> Any:
    path = (
        EXPERIMENT_ROOT.parents[1]
        / "foundations"
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


def _load_experiment007() -> Any:
    path = (
        EXPERIMENT_ROOT.parent
        / "007_full_matrix_qr_tangent_dynamics"
        / "full_matrix_qr_tangent_dynamics.py"
    )
    spec = importlib.util.spec_from_file_location("experiment007_for_011", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Experiment 007 from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


experiment007 = _load_experiment007()

EXPERIMENT_STATUS = "phases_a_b_and_c_accepted"
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

PHASE_B_DURATION_SECONDS = 1.25
PHASE_B_QR_INTERVAL_SECONDS = 0.25
PHASE_B_CYCLE_COUNT = 5
PHASE_B_QR_LIMIT = 1.0e-12
PHASE_B_BOOKKEEPING_LIMIT = 1.0e-12
PHASE_B_REPRODUCIBILITY_LIMIT = 1.0e-12
PHASE_B_MINIMUM_R_DIAGONAL = 1.0e-14
PHASE_B_MINIMUM_A_SINGULAR_VALUE = 1.0e-6
PHASE_B_MAXIMUM_A_CONDITION_NUMBER = 1.0e3
PHASE_B_MAXIMUM_PRE_QR_CONDITION_NUMBER = 1.0e12

PHASE_B_CROSS_LIMITS = {
    "baseline_reference_candidate_a": 1.0e-7,
    "refined_reference_candidate_a": 2.0e-8,
    "pre_qr_scaled_relative": 2.0e-6,
    "mapped_physical_pre_relative": 2.0e-6,
    "q_component_absolute": 2.0e-6,
    "post_reset_mapped_basis_absolute": 2.0e-6,
    "r_diagonal_relative": 2.0e-6,
    "cycle_log_absolute": 2.0e-6,
    "cumulative_log_absolute": 1.0e-5,
    "final_diagnostic_per_second": 1.0e-5,
}

PHASE_B_REFINEMENT_LIMITS = {
    "reference_candidate_a": 1.0e-6,
    "cycle_log_absolute": 1.0e-4,
    "cumulative_log_absolute": 5.0e-4,
    "final_diagnostic_per_second": 5.0e-4,
}

PHASE_C_DURATION_SECONDS = 640.0
PHASE_C_QR_INTERVAL_SECONDS = 0.25
PHASE_C_CHECKPOINTS_SECONDS = (
    80.0,
    160.0,
    240.0,
    320.0,
    400.0,
    480.0,
    560.0,
    640.0,
)
PHASE_C_LATE_WINDOW_START_SECONDS = 560.0
PHASE_C_DECORRELATION_DISTANCE = 1.0
PHASE_C_DECORRELATION_DEADLINE_SECONDS = 80.0

# The Experiment 009 -> 010 compatibility limits are inherited unchanged.
PHASE_C_MAX_CHANGE_480_TO_560 = 0.08
PHASE_C_MAX_CHANGE_560_TO_640 = 0.05
PHASE_C_MAX_WITHIN_LATE_RANGE = 0.05
PHASE_C_MAX_FINAL_BETWEEN_RANGE = 0.05
PHASE_C_MAX_FINAL_BETWEEN_SAMPLE_STD = 0.025
PHASE_C_MAX_ENSEMBLE_MEAN_CHANGE_560_TO_640 = 0.04
PHASE_C_MAX_LATE_WINDOW_BETWEEN_RANGE = 0.07

# The separate, symmetric EL/canonical descriptive compatibility rule.
PHASE_C_CROSS_MAX_MEAN_DISPLACEMENT = 0.05
PHASE_C_CROSS_MAX_COMBINED_RANGE = 0.07
PHASE_C_CROSS_MAX_COMBINED_SAMPLE_STD = 0.025
PHASE_C_CROSS_MAX_LATE_DRIFT_DIFFERENCE = 0.04

PHASE_C_EL_SHADOW_SPECTRA = {
    "baseline": {
        "560s": np.array(
            [0.9709494258667554, 0.008732086581559464,
             -0.005885748729879787, -0.9747214220438583]
        ),
        "640s": np.array(
            [0.9778962104586896, 0.010174940627774593,
             -0.00732853603361234, -0.9814938733605064]
        ),
    },
    "strict": {
        "560s": np.array(
            [0.9537961850078933, 0.003868905587555358,
             -0.002601190064398811, -0.9562595788708468]
        ),
        "640s": np.array(
            [0.9776540877769582, 0.009206594746544103,
             -0.006745952338554654, -0.9810576157103869]
        ),
    },
    "half_step": {
        "560s": np.array(
            [0.9906550449611532, 0.011072109870542605,
             -0.007371903380013738, -0.9944023972256405]
        ),
        "640s": np.array(
            [0.9942765464260072, 0.017439277518285386,
             -0.015748260833789687, -0.9970454158402113]
        ),
    },
}
PHASE_C_EL_DESCRIPTIVE_HALF_WIDTH = np.array(
    [0.023857902769064854, 0.006367167647742781,
     0.008376357453775948, 0.024798036839540072]
)


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
        "development/chaos_content/experiments/foundations/"
        "001_hamiltonian_poincare/"
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
        failed = [
            name
            for name, group in summary["groups"].items()
            if isinstance(group, dict) and "accepted" in group and not group["accepted"]
        ]
        raise AssertionError(f"Experiment 011 validation failed: {failed}")
    if "long-time" not in summary["claim_boundary"].lower() and summary["phase"].startswith("B_"):
        raise AssertionError("Phase B claim boundary changed unexpectedly.")
    if summary["phase"].startswith("A_") and summary["claim_boundary"] != "No canonical QR or Lyapunov spectrum was computed.":
        raise AssertionError("Phase A claim boundary changed unexpectedly.")


def canonicalize_canonical_state_angles(state: Sequence[float]) -> np.ndarray:
    """Rebase canonical angles while preserving momenta and tangent coordinates."""

    result = np.array(state, dtype=float, copy=True)
    if result.shape[-1] != 4:
        raise ValueError("Canonical states must have four components.")
    result[..., :2] = experiment006.wrap_angle_difference(result[..., :2])
    return result


def canonical_full_matrix_augmented_rhs(
    dynamics: CanonicalDynamics,
    time_value: float,
    augmented: Sequence[float],
) -> np.ndarray:
    """Evolve the canonical reference and four canonical tangent columns."""

    reference, tangent_matrix = experiment007.unpack_augmented_state(
        np.asarray(augmented, dtype=float)
    )
    return experiment007.pack_augmented_state(
        dynamics.flow(reference, time_value),
        dynamics.jacobian(reference, time_value) @ tangent_matrix,
    )


def canonical_pullback_qr_reset(
    reference: Sequence[float], tangent_matrix_pre: Sequence[Sequence[float]]
) -> dict[str, Any]:
    """Apply one QR reset in the state-dependent Candidate-A pullback metric."""

    canonical_reference = np.asarray(reference, dtype=float)
    tangent_pre = np.asarray(tangent_matrix_pre, dtype=float)
    if canonical_reference.shape != (4,) or tangent_pre.shape != (4, 4):
        raise ValueError("Canonical QR reset requires one state and one 4x4 matrix.")

    factor = candidate_a_pullback_factor(canonical_reference)
    singular_values = np.linalg.svd(factor, compute_uv=False)
    factor_condition = float(np.linalg.cond(factor))
    factor_determinant = float(np.linalg.det(factor))
    scaled_pre = factor @ tangent_pre
    orthogonal, upper = experiment007.positive_diagonal_qr(scaled_pre)
    diagonal = np.diag(upper)
    tangent_post = np.linalg.solve(factor, orthogonal)
    coordinate_map = inverse_tangent_map(canonical_reference)
    mapped_physical_pre = coordinate_map @ tangent_pre
    mapped_physical_post = coordinate_map @ tangent_post
    identity = np.eye(4)

    q_orthonormality_error = float(
        np.linalg.norm(orthogonal.T @ orthogonal - identity, ord=np.inf)
    )
    scaled_reconstruction_error = float(
        np.linalg.norm(scaled_pre - orthogonal @ upper, ord="fro")
        / max(1.0, float(np.linalg.norm(scaled_pre, ord="fro")))
    )
    coordinate_reconstruction_error = float(
        np.linalg.norm(tangent_pre - tangent_post @ upper, ord="fro")
        / max(1.0, float(np.linalg.norm(tangent_pre, ord="fro")))
    )
    physical_reconstruction_error = float(
        np.linalg.norm(
            mapped_physical_pre - mapped_physical_post @ upper, ord="fro"
        )
        / max(1.0, float(np.linalg.norm(mapped_physical_pre, ord="fro")))
    )
    scaled_post = factor @ tangent_post
    metric = factor.T @ factor
    pullback_orthonormality_error = float(
        np.linalg.norm(tangent_post.T @ metric @ tangent_post - identity, ord=np.inf)
    )
    reset_identity_error = float(
        np.linalg.norm(scaled_post - orthogonal, ord="fro")
    )
    pre_qr_condition = float(np.linalg.cond(scaled_pre))
    log_diagonal = np.log(diagonal)

    checks = {
        "finite_reference_tangent_and_factor": bool(
            np.all(np.isfinite(canonical_reference))
            and np.all(np.isfinite(tangent_pre))
            and np.all(np.isfinite(factor))
            and np.all(np.isfinite(orthogonal))
            and np.all(np.isfinite(upper))
            and np.all(np.isfinite(tangent_post))
        ),
        "factor_resolved_and_conditioned": bool(
            singular_values[-1] >= PHASE_B_MINIMUM_A_SINGULAR_VALUE
            and factor_condition <= PHASE_B_MAXIMUM_A_CONDITION_NUMBER
            and factor_determinant != 0.0
        ),
        "pre_qr_condition_below_guard": bool(
            np.isfinite(pre_qr_condition)
            and pre_qr_condition <= PHASE_B_MAXIMUM_PRE_QR_CONDITION_NUMBER
        ),
        "q_orthonormal": q_orthonormality_error <= PHASE_B_QR_LIMIT,
        "scaled_reconstruction": scaled_reconstruction_error <= PHASE_B_QR_LIMIT,
        "coordinate_reconstruction": coordinate_reconstruction_error
        <= PHASE_B_QR_LIMIT,
        "physical_reconstruction": physical_reconstruction_error
        <= PHASE_B_QR_LIMIT,
        "post_reset_pullback_orthonormal": pullback_orthonormality_error
        <= PHASE_B_QR_LIMIT,
        "reset_identity": reset_identity_error <= PHASE_B_QR_LIMIT,
        "positive_resolved_diagonal": bool(
            np.all(np.isfinite(diagonal))
            and np.all(diagonal >= PHASE_B_MINIMUM_R_DIAGONAL)
        ),
        "finite_log_diagonal": bool(np.all(np.isfinite(log_diagonal))),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "factor": factor,
        "factor_condition_number": factor_condition,
        "factor_determinant": factor_determinant,
        "factor_minimum_singular_value": float(singular_values[-1]),
        "coordinate_map": coordinate_map,
        "scaled_pre": scaled_pre,
        "orthogonal": orthogonal,
        "upper": upper,
        "diagonal": diagonal,
        "log_diagonal": log_diagonal,
        "tangent_matrix_post": tangent_post,
        "mapped_physical_pre": mapped_physical_pre,
        "mapped_physical_post": mapped_physical_post,
        "q_orthonormality_error": q_orthonormality_error,
        "scaled_reconstruction_relative_error": scaled_reconstruction_error,
        "coordinate_reconstruction_relative_error": coordinate_reconstruction_error,
        "physical_reconstruction_relative_error": physical_reconstruction_error,
        "post_pullback_orthonormality_error": pullback_orthonormality_error,
        "reset_identity_error": reset_identity_error,
        "pre_qr_condition_number": pre_qr_condition,
    }


def _public_canonical_reset(reset: dict[str, Any]) -> dict[str, Any]:
    return {
        "checks": reset["checks"],
        "pullback_factor": reset["factor"],
        "pullback_factor_condition_number": reset["factor_condition_number"],
        "pullback_factor_determinant": reset["factor_determinant"],
        "pullback_factor_minimum_singular_value": reset[
            "factor_minimum_singular_value"
        ],
        "scaled_pre": reset["scaled_pre"],
        "orthogonal_q": reset["orthogonal"],
        "upper_r": reset["upper"],
        "r_diagonal": reset["diagonal"],
        "log_r_diagonal": reset["log_diagonal"],
        "tangent_matrix_post": reset["tangent_matrix_post"],
        "mapped_physical_tangent_pre": reset["mapped_physical_pre"],
        "mapped_physical_tangent_post": reset["mapped_physical_post"],
        "q_orthonormality_error": reset["q_orthonormality_error"],
        "scaled_reconstruction_relative_error": reset[
            "scaled_reconstruction_relative_error"
        ],
        "coordinate_reconstruction_relative_error": reset[
            "coordinate_reconstruction_relative_error"
        ],
        "physical_reconstruction_relative_error": reset[
            "physical_reconstruction_relative_error"
        ],
        "post_pullback_orthonormality_error": reset[
            "post_pullback_orthonormality_error"
        ],
        "reset_identity_error": reset["reset_identity_error"],
        "pre_qr_condition_number": reset["pre_qr_condition_number"],
    }


def run_canonical_qr_primitive(
    dynamics: CanonicalDynamics,
    *,
    run_id: str,
    policy: Any,
    max_step: float,
    duration: float = PHASE_B_DURATION_SECONDS,
    qr_interval: float = PHASE_B_QR_INTERVAL_SECONDS,
    initial_el_state: Sequence[float] | None = None,
    initial_canonical_reference: Sequence[float] | None = None,
    initial_tangent_matrix: Sequence[Sequence[float]] | None = None,
    initial_cumulative_log_growth: Sequence[float] | None = None,
    start_time_seconds: float = 0.0,
    completed_cycle_count: int = 0,
    diagnostic_energy_baseline: float | None = None,
) -> dict[str, Any]:
    """Run the canonical pullback-QR primitive, optionally from a QR boundary."""

    if initial_el_state is not None and initial_canonical_reference is not None:
        raise ValueError("Provide either an EL initial state or a canonical restart state.")
    if not np.isfinite(start_time_seconds) or start_time_seconds < 0.0:
        raise ValueError("start_time_seconds must be finite and nonnegative.")
    if not isinstance(completed_cycle_count, int) or completed_cycle_count < 0:
        raise ValueError("completed_cycle_count must be a nonnegative integer.")
    if not math.isclose(
        completed_cycle_count * qr_interval,
        start_time_seconds,
        rel_tol=0.0,
        abs_tol=1.0e-13,
    ):
        raise ValueError("Cycle count and elapsed time do not identify one QR boundary.")
    continuation_requested = bool(
        start_time_seconds > 0.0
        or completed_cycle_count > 0
        or initial_canonical_reference is not None
        or initial_tangent_matrix is not None
        or initial_cumulative_log_growth is not None
        or diagnostic_energy_baseline is not None
    )
    if continuation_requested and initial_canonical_reference is None:
        raise ValueError("A continuation requires an explicit canonical reference.")
    boundaries = start_time_seconds + experiment007.deterministic_cycle_times(
        duration, qr_interval
    )
    if initial_canonical_reference is None:
        el_reference = np.asarray(
            INITIAL_EL_STATE if initial_el_state is None else initial_el_state,
            dtype=float,
        )
        if el_reference.shape != (4,) or not np.all(np.isfinite(el_reference)):
            raise ValueError("Initial EL state must be one finite four-state.")
        el_reference = experiment006.canonicalize_state_angles(el_reference)
        current_reference = el_to_canonical(el_reference)
    else:
        current_reference = np.array(
            initial_canonical_reference, dtype=float, copy=True
        )
        if current_reference.shape != (4,) or not np.all(np.isfinite(current_reference)):
            raise ValueError("Canonical restart state must be one finite four-state.")
        if np.any(current_reference[:2] <= -math.pi) or np.any(
            current_reference[:2] > math.pi
        ):
            raise ValueError("Restart canonical angles must use the local principal chart.")
        el_reference = canonical_to_el(current_reference)
    initial_canonical_reference = np.array(current_reference, copy=True)
    current_tangent = np.array(
        np.linalg.solve(candidate_a_pullback_factor(current_reference), np.eye(4))
        if initial_tangent_matrix is None
        else initial_tangent_matrix,
        dtype=float,
        copy=True,
    )
    if current_tangent.shape != (4, 4) or not np.all(np.isfinite(current_tangent)):
        raise ValueError("Initial canonical tangent matrix must be one finite 4x4 array.")
    initial_canonical_tangent = np.array(current_tangent, copy=True)
    initial_energy = float(
        dynamics.energy(current_reference)
        if diagnostic_energy_baseline is None
        else diagnostic_energy_baseline
    )
    if not np.isfinite(initial_energy):
        raise ValueError("Diagnostic Hamiltonian baseline must be finite.")
    cumulative_logs = np.array(
        np.zeros(4)
        if initial_cumulative_log_growth is None
        else initial_cumulative_log_growth,
        dtype=float,
        copy=True,
    )
    if cumulative_logs.shape != (4,) or not np.all(np.isfinite(cumulative_logs)):
        raise ValueError("Initial cumulative log growth must be one finite four-vector.")
    initial_cumulative_logs = np.array(cumulative_logs, copy=True)
    cycles: list[dict[str, Any]] = []
    reference_times: list[np.ndarray] = []
    reference_states: list[np.ndarray] = []
    energy_drifts: list[np.ndarray] = []
    solver_statuses: list[dict[str, Any]] = []

    for local_cycle_index, (start, end) in enumerate(
        zip(boundaries[:-1], boundaries[1:]), start=1
    ):
        cycle_index = completed_cycle_count + local_cycle_index
        reference_start = np.array(current_reference, copy=True)
        tangent_start = np.array(current_tangent, copy=True)
        requested_time = experiment007.requested_cycle_times(float(start), float(end))
        segment = experiment006.solve_one_segment(
            lambda time_value, augmented: canonical_full_matrix_augmented_rhs(
                dynamics, time_value, augmented
            ),
            experiment007.pack_augmented_state(reference_start, tangent_start),
            requested_time,
            policy,
            max_step=max_step,
        )
        solver_status = segment["solver_status"] | {"accepted": segment["accepted"]}
        solver_statuses.append(solver_status)
        if not segment["accepted"]:
            raise RuntimeError(
                f"Canonical QR cycle {cycle_index} failed: {segment['checks']}"
            )

        augmented_samples = segment["state"]
        segment_reference = augmented_samples[:, :4]
        reference_end_raw, tangent_pre = experiment007.unpack_augmented_state(
            augmented_samples[-1]
        )
        reference_end = canonicalize_canonical_state_angles(reference_end_raw)
        energy = np.array([dynamics.energy(state) for state in segment_reference])
        energy_drift = np.abs(energy - initial_energy) / experiment006.energy_scale()
        segment_energy_drift = float(np.max(energy_drift))

        reset = canonical_pullback_qr_reset(reference_end, tangent_pre)
        cycle_logs = np.asarray(reset["log_diagonal"], dtype=float)
        cumulative_logs = cumulative_logs + cycle_logs
        finite_time_diagnostic = cumulative_logs / float(end)
        accumulation_finite = bool(
            np.all(np.isfinite(cycle_logs))
            and np.all(np.isfinite(cumulative_logs))
            and np.all(np.isfinite(finite_time_diagnostic))
        )
        checks = {
            "solver_segment_valid": segment["accepted"],
            "pullback_qr_reset_valid": reset["accepted"],
            "finite_accumulation": accumulation_finite,
            "reference_energy_within_limit": segment_energy_drift
            <= experiment006.ENERGY_DRIFT_LIMIT,
        }
        cycle = {
            "cycle_index": cycle_index,
            "start_time_seconds": float(start),
            "end_time_seconds": float(end),
            "qr_interval_seconds": qr_interval,
            "accepted": all(checks.values()),
            "checks": checks,
            "reference_start": reference_start,
            "reference_end": reference_end,
            "tangent_matrix_start": tangent_start,
            "tangent_matrix_pre_qr": tangent_pre,
            **_public_canonical_reset(reset),
            "cycle_log_growth": cycle_logs,
            "cumulative_log_growth": cumulative_logs.copy(),
            "cumulative_finite_time_diagnostic_per_second": (
                finite_time_diagnostic.copy()
            ),
            "segment_maximum_normalized_reference_energy_drift": (
                segment_energy_drift
            ),
            "solver_status": solver_status,
        }
        cycles.append(cycle)

        stored_reference = canonicalize_canonical_state_angles(segment_reference)
        if local_cycle_index > 1:
            requested_time = requested_time[1:]
            stored_reference = stored_reference[1:]
            energy_drift = energy_drift[1:]
        reference_times.append(requested_time)
        reference_states.append(stored_reference)
        energy_drifts.append(energy_drift)
        current_reference = reference_end
        current_tangent = reset["tangent_matrix_post"]

    all_time = np.concatenate(reference_times)
    all_reference = np.concatenate(reference_states)
    all_energy_drift = np.concatenate(energy_drifts)
    cycle_logs_array = np.asarray(
        [cycle["cycle_log_growth"] for cycle in cycles], dtype=float
    )
    stored_cumulative = np.asarray(
        [cycle["cumulative_log_growth"] for cycle in cycles], dtype=float
    )
    end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in cycles], dtype=float
    )
    stored_diagnostic = np.asarray(
        [
            cycle["cumulative_finite_time_diagnostic_per_second"]
            for cycle in cycles
        ],
        dtype=float,
    )
    recomputed_cumulative = initial_cumulative_logs + np.cumsum(
        cycle_logs_array, axis=0
    )
    recomputed_diagnostic = recomputed_cumulative / end_times[:, None]
    cumulative_error = float(
        np.max(np.abs(recomputed_cumulative - stored_cumulative))
    )
    diagnostic_error = float(
        np.max(np.abs(recomputed_diagnostic - stored_diagnostic))
    )
    expected_output_count = 1 + sum(
        len(experiment007.requested_cycle_times(float(start), float(end))) - 1
        for start, end in zip(boundaries[:-1], boundaries[1:])
    )
    checks = {
        "all_cycles_accepted": all(cycle["accepted"] for cycle in cycles),
        "cumulative_logs_recomputed": cumulative_error
        <= PHASE_B_BOOKKEEPING_LIMIT,
        "diagnostic_recomputed": diagnostic_error <= PHASE_B_BOOKKEEPING_LIMIT,
        "global_times_strictly_monotonic": bool(np.all(np.diff(all_time) > 0.0)),
        "global_output_complete": bool(
            math.isclose(float(all_time[0]), start_time_seconds)
            and math.isclose(float(all_time[-1]), float(boundaries[-1]))
            and len(all_time) == expected_output_count
        ),
        "reference_energy_within_limit": float(np.max(all_energy_drift))
        <= experiment006.ENERGY_DRIFT_LIMIT,
    }
    return {
        "run_id": run_id,
        "accepted": all(checks.values()),
        "duration_seconds": float(boundaries[-1]),
        "integration_span_seconds": duration,
        "start_time_seconds": start_time_seconds,
        "elapsed_time_seconds": float(boundaries[-1]),
        "qr_interval_seconds": qr_interval,
        "cycle_count": completed_cycle_count + len(cycles),
        "segment_cycle_count": len(cycles),
        "completed_cycle_count_at_start": completed_cycle_count,
        "continued_from_qr_boundary": continuation_requested,
        "solver_policy": experiment006.policy_dict(policy),
        "max_step_seconds": max_step,
        "checks": checks,
        "cycles": cycles,
        "initial_el_reference": el_reference,
        "initial_canonical_reference": initial_canonical_reference,
        "initial_canonical_tangent_basis": initial_canonical_tangent,
        "initial_cumulative_log_growth": initial_cumulative_logs,
        "diagnostic_energy_baseline_joules": initial_energy,
        "final_cumulative_log_growth": stored_cumulative[-1],
        "final_diagnostic_vector_per_second": stored_diagnostic[-1],
        "terminal_reference_state": np.array(current_reference, copy=True),
        "terminal_tangent_matrix_post_qr": np.array(current_tangent, copy=True),
        "maximum_normalized_reference_energy_drift": float(
            np.max(all_energy_drift)
        ),
        "maximum_pullback_factor_condition_number": max(
            cycle["pullback_factor_condition_number"] for cycle in cycles
        ),
        "minimum_pullback_factor_singular_value": min(
            cycle["pullback_factor_minimum_singular_value"] for cycle in cycles
        ),
        "maximum_pre_qr_condition_number": max(
            cycle["pre_qr_condition_number"] for cycle in cycles
        ),
        "minimum_r_diagonal": min(
            float(np.min(cycle["r_diagonal"])) for cycle in cycles
        ),
        "maximum_q_orthonormality_error": max(
            cycle["q_orthonormality_error"] for cycle in cycles
        ),
        "maximum_scaled_reconstruction_relative_error": max(
            cycle["scaled_reconstruction_relative_error"] for cycle in cycles
        ),
        "maximum_coordinate_reconstruction_relative_error": max(
            cycle["coordinate_reconstruction_relative_error"] for cycle in cycles
        ),
        "maximum_physical_reconstruction_relative_error": max(
            cycle["physical_reconstruction_relative_error"] for cycle in cycles
        ),
        "maximum_post_pullback_orthonormality_error": max(
            cycle["post_pullback_orthonormality_error"] for cycle in cycles
        ),
        "maximum_reset_identity_error": max(
            cycle["reset_identity_error"] for cycle in cycles
        ),
        "cumulative_bookkeeping_error": cumulative_error,
        "diagnostic_bookkeeping_error": diagnostic_error,
        "solver_statistics": {
            "segments": len(solver_statuses),
            "nfev": int(sum(item["nfev"] for item in solver_statuses)),
            "njev": int(sum(item["njev"] for item in solver_statuses)),
            "nlu": int(sum(item["nlu"] for item in solver_statuses)),
            "all_segments_accepted": all(
                item["accepted"] for item in solver_statuses
            ),
        },
        "_reference_time": all_time,
        "_reference_state": all_reference,
        "_reference_as_el": canonical_to_el(all_reference),
        "_cycle_logs": cycle_logs_array,
        "_cumulative_logs": stored_cumulative,
        "_diagnostic": stored_diagnostic,
        "_terminal_reference_state": np.array(current_reference, copy=True),
        "_terminal_tangent_matrix_post_qr": np.array(current_tangent, copy=True),
    }


def compare_el_canonical_qr(
    el_run: dict[str, Any],
    canonical_run: dict[str, Any],
    *,
    policy_name: str,
) -> dict[str, Any]:
    """Compare synchronized EL and canonical QR cycles in Candidate-A geometry."""

    if el_run["cycle_count"] != canonical_run["cycle_count"]:
        raise ValueError("EL and canonical runs must have the same cycle count.")
    reference_distances: list[float] = []
    scaled_pre_relative: list[float] = []
    physical_pre_relative: list[float] = []
    q_differences: list[float] = []
    upper_differences: list[float] = []
    diagonal_relative: list[float] = []
    cycle_log_differences: list[float] = []
    cumulative_differences: list[float] = []
    post_basis_differences: list[float] = []
    cycle_records: list[dict[str, Any]] = []

    for el_cycle, canonical_cycle in zip(el_run["cycles"], canonical_run["cycles"]):
        canonical_reference = np.asarray(canonical_cycle["reference_end"], dtype=float)
        canonical_as_el = canonical_to_el(canonical_reference)
        reference_difference = _wrapped_el_difference(
            np.asarray(el_cycle["reference_end"], dtype=float), canonical_as_el
        )
        reference_distance = float(
            experiment006.candidate_a_norm(reference_difference)
        )
        el_scaled_pre = np.asarray(el_cycle["scaled_pre"], dtype=float)
        canonical_scaled_pre = np.asarray(canonical_cycle["scaled_pre"], dtype=float)
        scaled_relative = float(
            np.linalg.norm(canonical_scaled_pre - el_scaled_pre, ord="fro")
            / max(1.0, float(np.linalg.norm(el_scaled_pre, ord="fro")))
        )
        coordinate_map = inverse_tangent_map(canonical_reference)
        canonical_physical_pre = coordinate_map @ np.asarray(
            canonical_cycle["tangent_matrix_pre_qr"], dtype=float
        )
        el_physical_pre = np.asarray(el_cycle["tangent_matrix_pre_qr"], dtype=float)
        physical_relative = float(
            np.linalg.norm(canonical_physical_pre - el_physical_pre, ord="fro")
            / max(1.0, float(np.linalg.norm(el_physical_pre, ord="fro")))
        )
        el_q = np.asarray(el_cycle["orthogonal_q"], dtype=float)
        canonical_q = np.asarray(canonical_cycle["orthogonal_q"], dtype=float)
        q_difference = float(np.max(np.abs(canonical_q - el_q)))
        el_upper = np.asarray(el_cycle["upper_r"], dtype=float)
        canonical_upper = np.asarray(canonical_cycle["upper_r"], dtype=float)
        upper_difference = float(np.max(np.abs(canonical_upper - el_upper)))
        el_diagonal = np.asarray(el_cycle["r_diagonal"], dtype=float)
        canonical_diagonal = np.asarray(canonical_cycle["r_diagonal"], dtype=float)
        diagonal_difference = float(
            np.max(
                np.abs(canonical_diagonal - el_diagonal)
                / np.maximum(np.abs(el_diagonal), PHASE_B_MINIMUM_R_DIAGONAL)
            )
        )
        el_logs = np.asarray(el_cycle["cycle_log_growth"], dtype=float)
        canonical_logs = np.asarray(canonical_cycle["cycle_log_growth"], dtype=float)
        log_difference = float(np.max(np.abs(canonical_logs - el_logs)))
        el_cumulative = np.asarray(el_cycle["cumulative_log_growth"], dtype=float)
        canonical_cumulative = np.asarray(
            canonical_cycle["cumulative_log_growth"], dtype=float
        )
        cumulative_difference = float(
            np.max(np.abs(canonical_cumulative - el_cumulative))
        )
        canonical_post_as_el = coordinate_map @ np.asarray(
            canonical_cycle["tangent_matrix_post"], dtype=float
        )
        el_post = np.asarray(el_cycle["tangent_matrix_post"], dtype=float)
        post_difference = float(np.max(np.abs(canonical_post_as_el - el_post)))

        reference_distances.append(reference_distance)
        scaled_pre_relative.append(scaled_relative)
        physical_pre_relative.append(physical_relative)
        q_differences.append(q_difference)
        upper_differences.append(upper_difference)
        diagonal_relative.append(diagonal_difference)
        cycle_log_differences.append(log_difference)
        cumulative_differences.append(cumulative_difference)
        post_basis_differences.append(post_difference)
        cycle_records.append(
            {
                "cycle_index": el_cycle["cycle_index"],
                "end_time_seconds": el_cycle["end_time_seconds"],
                "reference_candidate_a_distance": reference_distance,
                "pre_qr_scaled_relative_difference": scaled_relative,
                "mapped_physical_pre_relative_difference": physical_relative,
                "q_maximum_component_difference": q_difference,
                "upper_r_maximum_absolute_difference": upper_difference,
                "r_diagonal_maximum_relative_difference": diagonal_difference,
                "cycle_log_maximum_absolute_difference": log_difference,
                "cumulative_log_maximum_absolute_difference": cumulative_difference,
                "post_reset_mapped_basis_maximum_absolute_difference": post_difference,
            }
        )

    el_final = np.asarray(el_run["final_diagnostic_spectrum_per_second"], dtype=float)
    canonical_final = np.asarray(
        canonical_run["final_diagnostic_vector_per_second"], dtype=float
    )
    final_difference = float(np.max(np.abs(canonical_final - el_final)))
    reference_limit = PHASE_B_CROSS_LIMITS[
        f"{policy_name}_reference_candidate_a"
    ]
    checks = {
        "both_runs_valid": el_run["accepted"] and canonical_run["accepted"],
        "reference_correspondence": max(reference_distances) <= reference_limit,
        "pre_qr_scaled_correspondence": max(scaled_pre_relative)
        <= PHASE_B_CROSS_LIMITS["pre_qr_scaled_relative"],
        "mapped_physical_pre_correspondence": max(physical_pre_relative)
        <= PHASE_B_CROSS_LIMITS["mapped_physical_pre_relative"],
        "positive_diagonal_q_correspondence": max(q_differences)
        <= PHASE_B_CROSS_LIMITS["q_component_absolute"],
        "post_reset_mapped_basis_correspondence": max(post_basis_differences)
        <= PHASE_B_CROSS_LIMITS["post_reset_mapped_basis_absolute"],
        "r_diagonal_correspondence": max(diagonal_relative)
        <= PHASE_B_CROSS_LIMITS["r_diagonal_relative"],
        "cycle_log_correspondence": max(cycle_log_differences)
        <= PHASE_B_CROSS_LIMITS["cycle_log_absolute"],
        "cumulative_log_correspondence": max(cumulative_differences)
        <= PHASE_B_CROSS_LIMITS["cumulative_log_absolute"],
        "final_diagnostic_correspondence": final_difference
        <= PHASE_B_CROSS_LIMITS["final_diagnostic_per_second"],
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "policy_name": policy_name,
        "cycle_comparisons": cycle_records,
        "maximum_reference_candidate_a_distance": max(reference_distances),
        "maximum_pre_qr_scaled_relative_difference": max(scaled_pre_relative),
        "maximum_mapped_physical_pre_relative_difference": max(
            physical_pre_relative
        ),
        "maximum_q_component_difference": max(q_differences),
        "maximum_upper_r_absolute_difference": max(upper_differences),
        "maximum_r_diagonal_relative_difference": max(diagonal_relative),
        "maximum_cycle_log_absolute_difference": max(cycle_log_differences),
        "maximum_cumulative_log_absolute_difference": max(cumulative_differences),
        "maximum_post_reset_mapped_basis_absolute_difference": max(
            post_basis_differences
        ),
        "final_el_diagnostic_vector_per_second": el_final,
        "final_canonical_diagnostic_vector_per_second": canonical_final,
        "maximum_final_diagnostic_difference_per_second": final_difference,
    }


def compare_phase_b_refinement(
    baseline: dict[str, Any],
    refined: dict[str, Any],
    *,
    formulation: str,
) -> dict[str, Any]:
    """Compare the compact baseline/refined QR policies within one formulation."""

    if formulation == "canonical":
        baseline_reference = baseline["_reference_as_el"]
        refined_reference = refined["_reference_as_el"]
        baseline_final = np.asarray(
            baseline["final_diagnostic_vector_per_second"], dtype=float
        )
        refined_final = np.asarray(
            refined["final_diagnostic_vector_per_second"], dtype=float
        )
    elif formulation == "el":
        baseline_reference = baseline["_reference_state"]
        refined_reference = refined["_reference_state"]
        baseline_final = np.asarray(
            baseline["final_diagnostic_spectrum_per_second"], dtype=float
        )
        refined_final = np.asarray(
            refined["final_diagnostic_spectrum_per_second"], dtype=float
        )
    else:
        raise ValueError("Formulation must be 'canonical' or 'el'.")

    reference_distance = experiment006.candidate_a_norm(
        _wrapped_el_difference(baseline_reference, refined_reference)
    )
    cycle_log_difference = np.abs(
        np.asarray(baseline["_cycle_logs"]) - np.asarray(refined["_cycle_logs"])
    )
    cumulative_difference = np.abs(
        np.asarray(baseline["_cumulative_logs"])
        - np.asarray(refined["_cumulative_logs"])
    )
    final_difference = np.abs(refined_final - baseline_final)
    maxima = {
        "maximum_reference_candidate_a_distance": float(np.max(reference_distance)),
        "maximum_cycle_log_absolute_difference": float(np.max(cycle_log_difference)),
        "maximum_cumulative_log_absolute_difference": float(
            np.max(cumulative_difference)
        ),
        "maximum_final_diagnostic_difference_per_second": float(
            np.max(final_difference)
        ),
    }
    checks = {
        "both_runs_valid": baseline["accepted"] and refined["accepted"],
        "reference_refinement": maxima["maximum_reference_candidate_a_distance"]
        <= PHASE_B_REFINEMENT_LIMITS["reference_candidate_a"],
        "cycle_log_refinement": maxima["maximum_cycle_log_absolute_difference"]
        <= PHASE_B_REFINEMENT_LIMITS["cycle_log_absolute"],
        "cumulative_log_refinement": maxima[
            "maximum_cumulative_log_absolute_difference"
        ]
        <= PHASE_B_REFINEMENT_LIMITS["cumulative_log_absolute"],
        "final_diagnostic_refinement": maxima[
            "maximum_final_diagnostic_difference_per_second"
        ]
        <= PHASE_B_REFINEMENT_LIMITS["final_diagnostic_per_second"],
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "formulation": formulation,
        **maxima,
        "baseline_final_diagnostic_vector_per_second": baseline_final,
        "refined_final_diagnostic_vector_per_second": refined_final,
        "componentwise_final_difference_per_second": final_difference,
    }


def compare_canonical_exact_repeats(
    primary: dict[str, Any], repeat: dict[str, Any]
) -> dict[str, Any]:
    """Verify deterministic reproducibility of the new canonical primitive."""

    cycle_error = float(
        np.max(np.abs(primary["_cycle_logs"] - repeat["_cycle_logs"]))
    )
    cumulative_error = float(
        np.max(np.abs(primary["_cumulative_logs"] - repeat["_cumulative_logs"]))
    )
    diagnostic_error = float(
        np.max(np.abs(primary["_diagnostic"] - repeat["_diagnostic"]))
    )
    reference_distance = float(
        experiment006.candidate_a_norm(
            _wrapped_el_difference(
                primary["_reference_as_el"][-1], repeat["_reference_as_el"][-1]
            )
        )
    )
    checks = {
        "repeat_valid": repeat["accepted"],
        "cycle_logs": cycle_error <= PHASE_B_REPRODUCIBILITY_LIMIT,
        "cumulative_logs": cumulative_error <= PHASE_B_REPRODUCIBILITY_LIMIT,
        "diagnostic": diagnostic_error <= PHASE_B_REPRODUCIBILITY_LIMIT,
        "physical_reference": reference_distance <= PHASE_B_REPRODUCIBILITY_LIMIT,
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "maximum_cycle_log_difference": cycle_error,
        "maximum_cumulative_log_difference": cumulative_error,
        "maximum_diagnostic_difference_per_second": diagnostic_error,
        "final_reference_candidate_a_distance": reference_distance,
    }


def run_phase_b(output_dir: Path | None = None) -> dict[str, Any]:
    """Run the predeclared short canonical/EL full-matrix QR validation."""

    canonical_dynamics = CanonicalDynamics()
    el_dynamics = experiment006.VariationalDynamics()
    configurations = {
        "baseline": (experiment007.SOLVER_POLICY, BASELINE_MAX_STEP),
        "refined": (experiment007.STRICTER_POLICY, REFINED_MAX_STEP),
    }
    el_runs: dict[str, Any] = {}
    canonical_runs: dict[str, Any] = {}
    cross_comparisons: dict[str, Any] = {}
    for name, (policy, max_step) in configurations.items():
        el_runs[name] = experiment007.run_qr_primitive(
            el_dynamics,
            run_id=f"phase_b_el_{name}",
            duration=PHASE_B_DURATION_SECONDS,
            qr_interval=PHASE_B_QR_INTERVAL_SECONDS,
            policy=policy,
            max_step=max_step,
        )
        canonical_runs[name] = run_canonical_qr_primitive(
            canonical_dynamics,
            run_id=f"phase_b_canonical_{name}",
            duration=PHASE_B_DURATION_SECONDS,
            qr_interval=PHASE_B_QR_INTERVAL_SECONDS,
            policy=policy,
            max_step=max_step,
        )
        cross_comparisons[name] = compare_el_canonical_qr(
            el_runs[name], canonical_runs[name], policy_name=name
        )

    canonical_repeat = run_canonical_qr_primitive(
        canonical_dynamics,
        run_id="phase_b_canonical_baseline_repeat",
        duration=PHASE_B_DURATION_SECONDS,
        qr_interval=PHASE_B_QR_INTERVAL_SECONDS,
        policy=experiment007.SOLVER_POLICY,
        max_step=BASELINE_MAX_STEP,
    )
    reproducibility = compare_canonical_exact_repeats(
        canonical_runs["baseline"], canonical_repeat
    )
    refinements = {
        "el": compare_phase_b_refinement(
            el_runs["baseline"], el_runs["refined"], formulation="el"
        ),
        "canonical": compare_phase_b_refinement(
            canonical_runs["baseline"],
            canonical_runs["refined"],
            formulation="canonical",
        ),
    }
    groups = {
        "canonical_baseline_internal": {
            "accepted": canonical_runs["baseline"]["accepted"]
        },
        "canonical_refined_internal": {
            "accepted": canonical_runs["refined"]["accepted"]
        },
        "el_baseline_internal": {"accepted": el_runs["baseline"]["accepted"]},
        "el_refined_internal": {"accepted": el_runs["refined"]["accepted"]},
        "baseline_cross_formulation": cross_comparisons["baseline"],
        "refined_cross_formulation": cross_comparisons["refined"],
        "el_numerical_refinement": refinements["el"],
        "canonical_numerical_refinement": refinements["canonical"],
        "canonical_exact_reproducibility": reproducibility,
    }
    accepted = all(group["accepted"] for group in groups.values())
    summary = {
        "experiment": "011_hamiltonian_canonical_spectrum_crosscheck",
        "phase": "B_canonical_pullback_full_matrix_qr",
        "accepted": accepted,
        "verdict": (
            "accepted_canonical_pullback_qr_and_short_time_el_equivalence"
            if accepted
            else "unresolved_or_rejected_phase_b"
        ),
        "claim_boundary": (
            "No long-time canonical spectrum, 640 s comparison, or maximal "
            "Lyapunov exponent was computed."
        ),
        "duration_seconds": PHASE_B_DURATION_SECONDS,
        "qr_interval_seconds": PHASE_B_QR_INTERVAL_SECONDS,
        "cycle_count": PHASE_B_CYCLE_COUNT,
        "initial_basis_contract": {
            "el": "Y_EL,0=S^-1",
            "canonical": "Y_H,0=A(z0)^-1",
            "correspondence": "Y_EL=C(z)Y_H and S Y_EL=A(z)Y_H=I",
        },
        "qr_sign_convention": (
            "R diagonal forced positive by paired Q-column/R-row flips; "
            "columns are not sorted"
        ),
        "policies": {
            name: experiment006.policy_dict(policy) | {"max_step_seconds": max_step}
            for name, (policy, max_step) in configurations.items()
        },
        "predeclared_limits": {
            "qr_internal": {
                "qr_and_reconstruction": PHASE_B_QR_LIMIT,
                "bookkeeping": PHASE_B_BOOKKEEPING_LIMIT,
                "reproducibility": PHASE_B_REPRODUCIBILITY_LIMIT,
                "minimum_r_diagonal": PHASE_B_MINIMUM_R_DIAGONAL,
                "minimum_pullback_factor_singular_value": (
                    PHASE_B_MINIMUM_A_SINGULAR_VALUE
                ),
                "maximum_pullback_factor_condition_number": (
                    PHASE_B_MAXIMUM_A_CONDITION_NUMBER
                ),
                "maximum_pre_qr_condition_number": (
                    PHASE_B_MAXIMUM_PRE_QR_CONDITION_NUMBER
                ),
                "normalized_energy_drift": experiment006.ENERGY_DRIFT_LIMIT,
            },
            "cross_formulation": PHASE_B_CROSS_LIMITS,
            "numerical_refinement": PHASE_B_REFINEMENT_LIMITS,
        },
        "canonical_runs": canonical_runs,
        "el_runs": el_runs,
        "cross_formulation": cross_comparisons,
        "refinement": refinements,
        "canonical_reproducibility": reproducibility,
        "groups": groups,
        "experiment_010_target_not_tested": asdict(EXPERIMENT_010_TARGET),
    }
    public_summary = _public(summary)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_path = output_dir / "summary.json"
        cycles_path = output_dir / "cycles.json"
        summary_without_cycles = dict(public_summary)
        summary_without_cycles["canonical_runs"] = {
            name: {key: value for key, value in run.items() if key != "cycles"}
            for name, run in public_summary["canonical_runs"].items()
        }
        summary_without_cycles["el_runs"] = {
            name: {key: value for key, value in run.items() if key != "cycles"}
            for name, run in public_summary["el_runs"].items()
        }
        summary_path.write_text(
            json.dumps(summary_without_cycles, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        cycles_path.write_text(
            json.dumps(
                {
                    "canonical_runs": {
                        name: run["cycles"]
                        for name, run in public_summary["canonical_runs"].items()
                    },
                    "el_runs": {
                        name: run["cycles"]
                        for name, run in public_summary["el_runs"].items()
                    },
                    "cross_formulation": public_summary["cross_formulation"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        manifest = {
            "experiment": public_summary["experiment"],
            "phase": public_summary["phase"],
            "accepted": accepted,
            "files": {
                path.name: {
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                }
                for path in (summary_path, cycles_path)
            },
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return summary


def phase_c_shadow_specs() -> dict[str, tuple[Any, float]]:
    """Return the frozen three canonical numerical-shadow policies."""

    return {
        "baseline": (experiment007.SOLVER_POLICY, BASELINE_MAX_STEP),
        "strict": (experiment007.STRICTER_POLICY, BASELINE_MAX_STEP),
        "half_step": (experiment007.SOLVER_POLICY, REFINED_MAX_STEP),
    }


def phase_c_spectrum_at_time(run: dict[str, Any], time_value: float) -> np.ndarray:
    """Return one cumulative fixed-column canonical diagnostic at a QR event."""

    cycle_index = int(round(time_value / PHASE_C_QR_INTERVAL_SECONDS)) - 1
    cycle = run["cycles"][cycle_index]
    if not math.isclose(
        float(cycle["end_time_seconds"]), time_value, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError(f"No canonical QR checkpoint at {time_value} seconds.")
    return np.asarray(
        cycle["cumulative_finite_time_diagnostic_per_second"], dtype=float
    )


def phase_c_reference_decorrelation(
    runs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Establish decorrelation of independently integrated physical shadows."""

    names = list(runs)
    common_time = np.asarray(runs[names[0]]["_reference_time"], dtype=float)
    times_identical = all(
        np.array_equal(common_time, np.asarray(runs[name]["_reference_time"]))
        for name in names[1:]
    )
    pairs: dict[str, Any] = {}
    series: dict[str, np.ndarray] = {}
    scaling = candidate_a_scaling_matrix()
    for first_name, second_name in combinations(names, 2):
        pair_name = f"{first_name}_vs_{second_name}"
        difference = _wrapped_el_difference(
            np.asarray(runs[first_name]["_reference_as_el"], dtype=float),
            np.asarray(runs[second_name]["_reference_as_el"], dtype=float),
        )
        distances = np.linalg.norm(difference @ scaling.T, axis=1)
        crossing_indices = np.flatnonzero(
            distances >= PHASE_C_DECORRELATION_DISTANCE
        )
        first_crossing = (
            float(common_time[int(crossing_indices[0])])
            if len(crossing_indices)
            else None
        )
        late = distances[
            common_time >= PHASE_C_DECORRELATION_DEADLINE_SECONDS - 1.0e-13
        ]
        series[pair_name] = distances
        pairs[pair_name] = {
            "first_threshold_crossing_seconds": first_crossing,
            "crossed_by_deadline": bool(
                first_crossing is not None
                and first_crossing <= PHASE_C_DECORRELATION_DEADLINE_SECONDS
            ),
            "final_candidate_a_distance": float(distances[-1]),
            "median_candidate_a_distance_after_deadline": float(np.median(late)),
            "maximum_candidate_a_distance": float(np.max(distances)),
        }
    checks = {
        "reference_sample_times_identical": times_identical,
        "all_pairs_decorrelated_by_80_seconds": all(
            pair["crossed_by_deadline"] for pair in pairs.values()
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "distance_threshold": PHASE_C_DECORRELATION_DISTANCE,
        "deadline_seconds": PHASE_C_DECORRELATION_DEADLINE_SECONDS,
        "pairs": pairs,
        "_time": common_time,
        "_distance_series": series,
    }


def phase_c_within_shadow_analysis(run: dict[str, Any]) -> dict[str, Any]:
    """Apply the frozen Experiment 010 settling limits to one canonical run."""

    checkpoints = {
        f"{int(time_value)}s": phase_c_spectrum_at_time(run, time_value)
        for time_value in PHASE_C_CHECKPOINTS_SECONDS
    }
    change_480_to_560 = np.abs(checkpoints["560s"] - checkpoints["480s"])
    change_560_to_640 = np.abs(checkpoints["640s"] - checkpoints["560s"])
    late_spectra = np.asarray(
        [
            cycle["cumulative_finite_time_diagnostic_per_second"]
            for cycle in run["cycles"]
            if cycle["end_time_seconds"]
            >= PHASE_C_LATE_WINDOW_START_SECONDS - 1.0e-13
        ],
        dtype=float,
    )
    late_ranges = np.ptp(late_spectra, axis=0)
    checks = {
        "480_to_560_change_within_0.08_per_second": bool(
            np.max(change_480_to_560) <= PHASE_C_MAX_CHANGE_480_TO_560
        ),
        "560_to_640_change_within_0.05_per_second": bool(
            np.max(change_560_to_640) <= PHASE_C_MAX_CHANGE_560_TO_640
        ),
        "late_component_ranges_within_0.05_per_second": bool(
            np.all(late_ranges <= PHASE_C_MAX_WITHIN_LATE_RANGE)
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "checkpoint_spectra_per_second": checkpoints,
        "component_change_480_to_560_per_second": change_480_to_560,
        "maximum_change_480_to_560_per_second": float(
            np.max(change_480_to_560)
        ),
        "component_change_560_to_640_per_second": change_560_to_640,
        "maximum_change_560_to_640_per_second": float(
            np.max(change_560_to_640)
        ),
        "late_component_ranges_per_second": late_ranges,
        "maximum_late_component_range_per_second": float(np.max(late_ranges)),
        "hamiltonian_diagnostics": {
            key: experiment007.hamiltonian_structure_diagnostics(value)
            for key, value in checkpoints.items()
        },
    }


def phase_c_between_shadow_analysis(
    runs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Apply the frozen Experiment 010 ensemble limits to canonical shadows."""

    checkpoint_statistics: dict[str, Any] = {}
    ensemble_means: dict[str, np.ndarray] = {}
    for time_value in PHASE_C_CHECKPOINTS_SECONDS:
        key = f"{int(time_value)}s"
        values = np.asarray(
            [phase_c_spectrum_at_time(run, time_value) for run in runs.values()]
        )
        mean = np.mean(values, axis=0)
        sample_std = np.std(values, axis=0, ddof=1)
        component_range = np.ptp(values, axis=0)
        ensemble_means[key] = mean
        checkpoint_statistics[key] = {
            "ensemble_mean_per_second": mean,
            "sample_standard_deviation_per_second": sample_std,
            "component_range_per_second": component_range,
            "maximum_component_range_per_second": float(np.max(component_range)),
            "maximum_sample_standard_deviation_per_second": float(
                np.max(sample_std)
            ),
            "ensemble_mean_hamiltonian_diagnostics": (
                experiment007.hamiltonian_structure_diagnostics(mean)
            ),
        }

    common_end_times = np.asarray(
        [cycle["end_time_seconds"] for cycle in next(iter(runs.values()))["cycles"]]
    )
    late_mask = common_end_times >= PHASE_C_LATE_WINDOW_START_SECONDS - 1.0e-13
    late_values = np.asarray([run["_diagnostic"][late_mask] for run in runs.values()])
    late_ranges = np.ptp(late_values, axis=0)
    maximum_late_range = float(np.max(late_ranges))
    mean_change = np.abs(ensemble_means["640s"] - ensemble_means["560s"])
    final_values = np.asarray(
        [phase_c_spectrum_at_time(run, 640.0) for run in runs.values()]
    )
    final_ranges = np.ptp(final_values, axis=0)
    final_stds = np.std(final_values, axis=0, ddof=1)
    per_shadow_late_changes = np.asarray(
        [
            np.abs(
                phase_c_spectrum_at_time(run, 640.0)
                - phase_c_spectrum_at_time(run, 560.0)
            )
            for run in runs.values()
        ]
    )
    uncertainty = np.maximum.reduce(
        [final_stds, final_ranges / 2.0, np.max(per_shadow_late_changes, axis=0)]
    )
    checks = {
        "final_component_ranges_within_0.05_per_second": bool(
            np.all(final_ranges <= PHASE_C_MAX_FINAL_BETWEEN_RANGE)
        ),
        "final_sample_standard_deviations_within_0.025_per_second": bool(
            np.all(final_stds <= PHASE_C_MAX_FINAL_BETWEEN_SAMPLE_STD)
        ),
        "ensemble_mean_change_560_to_640_within_0.04_per_second": bool(
            np.max(mean_change) <= PHASE_C_MAX_ENSEMBLE_MEAN_CHANGE_560_TO_640
        ),
        "late_window_between_range_within_0.07_per_second": bool(
            maximum_late_range <= PHASE_C_MAX_LATE_WINDOW_BETWEEN_RANGE
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "checkpoint_statistics": checkpoint_statistics,
        "ensemble_mean_component_change_560_to_640_per_second": mean_change,
        "maximum_ensemble_mean_change_560_to_640_per_second": float(
            np.max(mean_change)
        ),
        "late_window_component_ranges_per_second": np.max(late_ranges, axis=0),
        "maximum_late_window_between_range_per_second": maximum_late_range,
        "final_descriptive_uncertainty_half_width_per_second": uncertainty,
        "uncertainty_definition": (
            "componentwise maximum of final sample standard deviation, half final "
            "range, and largest absolute per-shadow 560-to-640 change"
        ),
        "_late_times": common_end_times[late_mask],
        "_late_ranges": late_ranges,
    }


def phase_c_el_evidence() -> dict[str, Any]:
    """Reconstruct the committed Experiment 010 terminal comparison evidence."""

    values_560 = np.asarray(
        [item["560s"] for item in PHASE_C_EL_SHADOW_SPECTRA.values()]
    )
    values_640 = np.asarray(
        [item["640s"] for item in PHASE_C_EL_SHADOW_SPECTRA.values()]
    )
    mean_560 = np.mean(values_560, axis=0)
    mean_640 = np.mean(values_640, axis=0)
    return {
        "internally_accepted": True,
        "provenance": (
            "Experiment 010 README and generated summary.json; values verified "
            "before the Phase C canonical runs"
        ),
        "shadow_values_560_per_second": values_560,
        "shadow_values_640_per_second": values_640,
        "ensemble_mean_560_per_second": mean_560,
        "ensemble_mean_640_per_second": mean_640,
        "ensemble_mean_change_560_to_640_per_second": mean_640 - mean_560,
        "sample_standard_deviation_640_per_second": np.std(
            values_640, axis=0, ddof=1
        ),
        "component_range_640_per_second": np.ptp(values_640, axis=0),
        "descriptive_uncertainty_half_width_per_second": (
            PHASE_C_EL_DESCRIPTIVE_HALF_WIDTH
        ),
    }


def phase_c_cross_formulation_analysis(
    *,
    canonical_runs: dict[str, dict[str, Any]],
    canonical_between: dict[str, Any],
    canonical_internal_accepted: bool,
) -> dict[str, Any]:
    """Apply the frozen symmetric descriptive EL/canonical compatibility rule."""

    el = phase_c_el_evidence()
    canonical_560 = np.asarray(
        [phase_c_spectrum_at_time(run, 560.0) for run in canonical_runs.values()]
    )
    canonical_640 = np.asarray(
        [phase_c_spectrum_at_time(run, 640.0) for run in canonical_runs.values()]
    )
    canonical_mean_560 = np.mean(canonical_560, axis=0)
    canonical_mean_640 = np.mean(canonical_640, axis=0)
    canonical_width = np.asarray(
        canonical_between["final_descriptive_uncertainty_half_width_per_second"]
    )
    el_mean_560 = np.asarray(el["ensemble_mean_560_per_second"])
    el_mean_640 = np.asarray(el["ensemble_mean_640_per_second"])
    mean_displacement = np.abs(canonical_mean_640 - el_mean_640)
    envelope_sum = canonical_width + PHASE_C_EL_DESCRIPTIVE_HALF_WIDTH
    combined_terminal = np.concatenate(
        [np.asarray(el["shadow_values_640_per_second"]), canonical_640], axis=0
    )
    combined_range = np.ptp(combined_terminal, axis=0)
    combined_std = np.std(combined_terminal, axis=0, ddof=1)
    canonical_drift = canonical_mean_640 - canonical_mean_560
    el_drift = el_mean_640 - el_mean_560
    drift_difference = np.abs(canonical_drift - el_drift)
    evaluable = bool(canonical_internal_accepted and el["internally_accepted"])
    checks = {
        "both_formulation_ensembles_internally_accepted": evaluable,
        "descriptive_envelopes_overlap_componentwise": bool(
            np.all(mean_displacement <= envelope_sum)
        ),
        "terminal_mean_displacement_within_0.05_per_second": bool(
            np.all(mean_displacement <= PHASE_C_CROSS_MAX_MEAN_DISPLACEMENT)
        ),
        "combined_six_shadow_range_within_0.07_per_second": bool(
            np.all(combined_range <= PHASE_C_CROSS_MAX_COMBINED_RANGE)
        ),
        "combined_six_shadow_sample_std_within_0.025_per_second": bool(
            np.all(combined_std <= PHASE_C_CROSS_MAX_COMBINED_SAMPLE_STD)
        ),
        "late_mean_drift_difference_within_0.04_per_second": bool(
            np.all(drift_difference <= PHASE_C_CROSS_MAX_LATE_DRIFT_DIFFERENCE)
        ),
    }
    accepted = evaluable and all(checks.values())
    verdict = (
        "accepted_descriptive_cross_formulation_compatibility"
        if accepted
        else (
            "rejected_descriptive_cross_formulation_compatibility"
            if evaluable
            else "unresolved_cross_formulation_comparison"
        )
    )
    return {
        "accepted": accepted,
        "evaluable": evaluable,
        "verdict": verdict,
        "checks": checks,
        "canonical_ensemble_mean_560_per_second": canonical_mean_560,
        "canonical_ensemble_mean_640_per_second": canonical_mean_640,
        "el_ensemble_mean_560_per_second": el_mean_560,
        "el_ensemble_mean_640_per_second": el_mean_640,
        "terminal_mean_absolute_displacement_per_second": mean_displacement,
        "descriptive_envelope_sum_per_second": envelope_sum,
        "terminal_displacement_to_envelope_sum_ratio": np.divide(
            mean_displacement,
            envelope_sum,
            out=np.zeros_like(mean_displacement),
            where=envelope_sum > 0.0,
        ),
        "combined_six_shadow_component_range_per_second": combined_range,
        "combined_six_shadow_sample_standard_deviation_per_second": combined_std,
        "canonical_ensemble_mean_change_560_to_640_per_second": canonical_drift,
        "el_ensemble_mean_change_560_to_640_per_second": el_drift,
        "late_mean_drift_absolute_difference_per_second": drift_difference,
        "el_evidence": el,
        "criterion_role": (
            "symmetric descriptive numerical compatibility; not a confidence "
            "interval or formal hypothesis test"
        ),
    }


def phase_c_public_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    """Keep provenance and extrema while excluding long private arrays/cycles."""

    return {
        key: value
        for key, value in run.items()
        if not key.startswith("_") and key != "cycles"
    }


def phase_c_numerical_extrema(runs: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Summarize inherited Phase B numerical guards over all Phase C cycles."""

    return {
        "maximum_normalized_hamiltonian_drift": max(
            run["maximum_normalized_reference_energy_drift"] for run in runs.values()
        ),
        "maximum_pullback_factor_condition_number": max(
            run["maximum_pullback_factor_condition_number"] for run in runs.values()
        ),
        "minimum_pullback_factor_singular_value": min(
            run["minimum_pullback_factor_singular_value"] for run in runs.values()
        ),
        "maximum_pre_qr_condition_number": max(
            run["maximum_pre_qr_condition_number"] for run in runs.values()
        ),
        "minimum_positive_r_diagonal": min(
            run["minimum_r_diagonal"] for run in runs.values()
        ),
        "maximum_q_orthonormality_error": max(
            run["maximum_q_orthonormality_error"] for run in runs.values()
        ),
        "maximum_scaled_reconstruction_relative_error": max(
            run["maximum_scaled_reconstruction_relative_error"]
            for run in runs.values()
        ),
        "maximum_canonical_reconstruction_relative_error": max(
            run["maximum_coordinate_reconstruction_relative_error"]
            for run in runs.values()
        ),
        "maximum_physical_reconstruction_relative_error": max(
            run["maximum_physical_reconstruction_relative_error"]
            for run in runs.values()
        ),
        "maximum_post_pullback_orthonormality_error": max(
            run["maximum_post_pullback_orthonormality_error"]
            for run in runs.values()
        ),
        "maximum_reset_identity_error": max(
            run["maximum_reset_identity_error"] for run in runs.values()
        ),
        "maximum_cumulative_bookkeeping_error": max(
            run["cumulative_bookkeeping_error"] for run in runs.values()
        ),
        "maximum_diagnostic_bookkeeping_error": max(
            run["diagnostic_bookkeeping_error"] for run in runs.values()
        ),
    }


def phase_c_internal_verdict(
    *,
    numerical_validity_accepted: bool,
    decorrelation_accepted: bool,
    within: dict[str, dict[str, Any]],
    between: dict[str, Any],
) -> str:
    if not numerical_validity_accepted or not decorrelation_accepted:
        return "numerically_unresolved_canonical_compatibility"
    if all(item["accepted"] for item in within.values()) and between["accepted"]:
        return "accepted_canonical_internal_compatibility_at_640_seconds"
    return "unresolved_or_incompatible_canonical_settling_at_640_seconds"


def _phase_c_write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_public(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_phase_c_output_bundle(
    result: dict[str, Any], output_dir: Path
) -> list[Path]:
    """Write compact but reconstructible Phase C machine evidence."""

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    checkpoint_path = output_dir / "checkpoint_spectra.csv"
    cumulative_path = output_dir / "cumulative_timeseries.csv"
    reference_path = output_dir / "reference_pair_distances.csv"
    cycles_path = output_dir / "cycles.json"
    _phase_c_write_json(summary_path, result["summary"])

    with checkpoint_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "shadow",
            "checkpoint_seconds",
            *[f"lambda_{index}_per_s" for index in range(1, 5)],
            "sum_per_s",
            "outer_pair_sum_per_s",
            "inner_pair_sum_per_s",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name, analysis in result["within"].items():
            for checkpoint_key, spectrum in analysis[
                "checkpoint_spectra_per_second"
            ].items():
                diagnostics = analysis["hamiltonian_diagnostics"][checkpoint_key]
                row = {
                    "shadow": name,
                    "checkpoint_seconds": float(checkpoint_key.removesuffix("s")),
                    "sum_per_s": diagnostics["sum_per_second"],
                    "outer_pair_sum_per_s": diagnostics[
                        "outer_pair_sum_per_second"
                    ],
                    "inner_pair_sum_per_s": diagnostics[
                        "inner_pair_sum_per_second"
                    ],
                }
                for index, value in enumerate(spectrum, start=1):
                    row[f"lambda_{index}_per_s"] = value
                writer.writerow(row)

    with cumulative_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "shadow",
            "time_seconds",
            *[f"lambda_{index}_per_s" for index in range(1, 5)],
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name, run in result["runs"].items():
            for cycle in run["cycles"]:
                row = {"shadow": name, "time_seconds": cycle["end_time_seconds"]}
                for index, value in enumerate(
                    cycle["cumulative_finite_time_diagnostic_per_second"], start=1
                ):
                    row[f"lambda_{index}_per_s"] = value
                writer.writerow(row)

    decorrelation = result["decorrelation"]
    with reference_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["time_seconds", *decorrelation["_distance_series"].keys()]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, time_value in enumerate(decorrelation["_time"]):
            writer.writerow(
                {"time_seconds": time_value}
                | {
                    name: values[index]
                    for name, values in decorrelation["_distance_series"].items()
                }
            )

    cycle_fields = (
        "cycle_index",
        "start_time_seconds",
        "end_time_seconds",
        "accepted",
        "checks",
        "cycle_log_growth",
        "cumulative_log_growth",
        "cumulative_finite_time_diagnostic_per_second",
        "pullback_factor_condition_number",
        "pullback_factor_minimum_singular_value",
        "pre_qr_condition_number",
        "r_diagonal",
        "q_orthonormality_error",
        "scaled_reconstruction_relative_error",
        "coordinate_reconstruction_relative_error",
        "physical_reconstruction_relative_error",
        "post_pullback_orthonormality_error",
        "reset_identity_error",
        "segment_maximum_normalized_reference_energy_drift",
        "solver_status",
    )
    _phase_c_write_json(
        cycles_path,
        {
            "experiment": "011_hamiltonian_canonical_spectrum_crosscheck",
            "phase": "C_long_time_canonical_ensemble",
            "shadows": {
                name: [
                    {field: cycle[field] for field in cycle_fields}
                    for cycle in run["cycles"]
                ]
                for name, run in result["runs"].items()
            },
        },
    )
    paths = [summary_path, checkpoint_path, cumulative_path, reference_path, cycles_path]
    manifest_path = output_dir / "manifest.json"
    manifest = {
        "experiment": "011_hamiltonian_canonical_spectrum_crosscheck",
        "phase": "C_long_time_canonical_ensemble",
        "output_role": "frozen 640-second canonical/EL compatibility evidence",
        "source": str(Path(__file__).relative_to(REPOSITORY_ROOT)),
        "files": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in paths
        ],
    }
    _phase_c_write_json(manifest_path, manifest)
    paths.append(manifest_path)
    return paths


def run_phase_c(output_dir: Path | None = None) -> dict[str, Any]:
    """Execute the frozen three-shadow 640-second canonical protocol."""

    dynamics = CanonicalDynamics()
    runs = {
        name: run_canonical_qr_primitive(
            dynamics,
            run_id=f"phase_c_canonical_{name}_640s",
            duration=PHASE_C_DURATION_SECONDS,
            qr_interval=PHASE_C_QR_INTERVAL_SECONDS,
            policy=policy,
            max_step=max_step,
        )
        for name, (policy, max_step) in phase_c_shadow_specs().items()
    }
    decorrelation = phase_c_reference_decorrelation(runs)
    within = {
        name: phase_c_within_shadow_analysis(run) for name, run in runs.items()
    }
    between = phase_c_between_shadow_analysis(runs)
    numerical_validity_checks = {
        f"{name}_numerically_valid": run["accepted"]
        for name, run in runs.items()
    }
    numerical_validity_accepted = all(numerical_validity_checks.values())
    internal_verdict = phase_c_internal_verdict(
        numerical_validity_accepted=numerical_validity_accepted,
        decorrelation_accepted=decorrelation["accepted"],
        within=within,
        between=between,
    )
    internal_accepted = internal_verdict.startswith("accepted_")
    cross = phase_c_cross_formulation_analysis(
        canonical_runs=runs,
        canonical_between=between,
        canonical_internal_accepted=internal_accepted,
    )
    final_stats = between["checkpoint_statistics"]["640s"]
    if internal_accepted and cross["accepted"]:
        overall_verdict = (
            "accepted_canonical_internal_and_el_canonical_compatibility"
        )
        strongest_claim = (
            "Independently integrated, decorrelated canonical Hamiltonian shadows "
            "produce compatible 640-second cumulative pullback-QR estimates, and "
            "the resulting canonical ensemble is descriptively compatible with "
            "the independently obtained Euler-Lagrange ensemble under the frozen rule."
        )
        next_question = (
            "Across a small, predeclared set of additional physical initial "
            "conditions, does independent EL/canonical agreement persist without "
            "retuning the numerical protocol?"
        )
    elif internal_accepted:
        overall_verdict = "accepted_canonical_internal_but_cross_formulation_incompatible"
        strongest_claim = (
            "The canonical shadows satisfy their internal 640-second compatibility "
            "criteria, but the canonical and Euler-Lagrange ensembles fail the "
            "predeclared descriptive cross-formulation rule."
        )
        next_question = (
            "Which long-time increment or finite-time metric effect accounts for "
            "the accepted ensembles' cross-formulation displacement?"
        )
    else:
        overall_verdict = "canonical_internal_compatibility_unresolved_at_640_seconds"
        strongest_claim = (
            "The frozen canonical protocol does not establish internal statistical "
            "compatibility at 640 seconds, so the EL/canonical ensemble comparison "
            "remains unresolved."
        )
        next_question = (
            "Which failed canonical settling, decorrelation, or numerical-validity "
            "condition must be understood before another cross-formulation test?"
        )
    summary = {
        "experiment": "011_hamiltonian_canonical_spectrum_crosscheck",
        "phase": "C_long_time_canonical_ensemble",
        "overall_verdict": overall_verdict,
        "canonical_internal_verdict": internal_verdict,
        "canonical_internal_accepted": internal_accepted,
        "el_canonical_cross_formulation_verdict": cross["verdict"],
        "el_canonical_cross_formulation_accepted": cross["accepted"],
        "question": (
            "Under a predeclared long-time canonical shadow/refinement protocol, "
            "do independently integrated cumulative canonical pullback-QR spectrum "
            "estimates become compatible with one another and with Experiment 010?"
        ),
        "frozen_protocol": {
            "shadow_count": 3,
            "shadow_names": list(runs),
            "duration_seconds": PHASE_C_DURATION_SECONDS,
            "checkpoints_seconds": list(PHASE_C_CHECKPOINTS_SECONDS),
            "late_window_seconds": [
                PHASE_C_LATE_WINDOW_START_SECONDS,
                PHASE_C_DURATION_SECONDS,
            ],
            "qr_interval_seconds": PHASE_C_QR_INTERVAL_SECONDS,
            "canonical_state_order": CANONICAL_STATE_ORDER,
            "physical_initial_state_degrees": experiment006.BASE_STATE_DEGREES,
            "metric": "A(z)=S D(Phi)(z); QR of A(z)Y",
            "qr_sign": "positive R diagonal; no tangent-column sorting",
            "shadow_policies": {
                name: experiment006.policy_dict(policy)
                | {"max_step_seconds": max_step}
                for name, (policy, max_step) in phase_c_shadow_specs().items()
            },
            "criteria_frozen_before_first_long_time_canonical_run": True,
        },
        "criteria": {
            "canonical_internal": {
                "maximum_change_480_to_560_per_second": (
                    PHASE_C_MAX_CHANGE_480_TO_560
                ),
                "maximum_change_560_to_640_per_second": (
                    PHASE_C_MAX_CHANGE_560_TO_640
                ),
                "maximum_within_late_range_per_second": (
                    PHASE_C_MAX_WITHIN_LATE_RANGE
                ),
                "maximum_final_between_range_per_second": (
                    PHASE_C_MAX_FINAL_BETWEEN_RANGE
                ),
                "maximum_final_between_sample_std_per_second": (
                    PHASE_C_MAX_FINAL_BETWEEN_SAMPLE_STD
                ),
                "maximum_ensemble_mean_change_560_to_640_per_second": (
                    PHASE_C_MAX_ENSEMBLE_MEAN_CHANGE_560_TO_640
                ),
                "maximum_late_window_between_range_per_second": (
                    PHASE_C_MAX_LATE_WINDOW_BETWEEN_RANGE
                ),
                "decorrelation_distance": PHASE_C_DECORRELATION_DISTANCE,
                "decorrelation_deadline_seconds": (
                    PHASE_C_DECORRELATION_DEADLINE_SECONDS
                ),
                "phase_b_qr_and_reconstruction_limits_retained": True,
            },
            "el_canonical_cross_formulation": {
                "descriptive_envelope_overlap_required": True,
                "maximum_terminal_mean_displacement_per_second": (
                    PHASE_C_CROSS_MAX_MEAN_DISPLACEMENT
                ),
                "maximum_combined_six_shadow_range_per_second": (
                    PHASE_C_CROSS_MAX_COMBINED_RANGE
                ),
                "maximum_combined_six_shadow_sample_std_per_second": (
                    PHASE_C_CROSS_MAX_COMBINED_SAMPLE_STD
                ),
                "maximum_late_mean_drift_difference_per_second": (
                    PHASE_C_CROSS_MAX_LATE_DRIFT_DIFFERENCE
                ),
                "interpretation": (
                    "symmetric descriptive compatibility, not confidence intervals "
                    "or a formal hypothesis test"
                ),
            },
        },
        "shadow_runs": {
            name: phase_c_public_run_summary(run) for name, run in runs.items()
        },
        "reference_decorrelation": decorrelation,
        "within_shadow": within,
        "between_shadow": between,
        "canonical_ensemble_spectrum_estimate_per_second": final_stats[
            "ensemble_mean_per_second"
        ],
        "canonical_descriptive_uncertainty_half_width_per_second": between[
            "final_descriptive_uncertainty_half_width_per_second"
        ],
        "canonical_ensemble_hamiltonian_diagnostics": (
            experiment007.hamiltonian_structure_diagnostics(
                np.asarray(final_stats["ensemble_mean_per_second"])
            )
        ),
        "el_canonical_cross_formulation": cross,
        "numerical_validity_checks": numerical_validity_checks,
        "numerical_validity_accepted": numerical_validity_accepted,
        "numerical_extrema": phase_c_numerical_extrema(runs),
        "strongest_claim": strongest_claim,
        "claim_boundary": (
            "One 640-second, three-policy canonical ensemble and its descriptive "
            "comparison with the committed Experiment 010 EL ensemble only; not an "
            "infinite-time proof, universal spectrum, or chaos classification."
        ),
        "next_question": next_question,
    }
    result = {
        "summary": summary,
        "runs": runs,
        "decorrelation": decorrelation,
        "within": within,
        "between": between,
        "cross": cross,
    }
    if output_dir is not None:
        write_phase_c_output_bundle(result, output_dir)
    return result


def assert_phase_c_self_check(result: dict[str, Any]) -> None:
    """Check consistency without requiring a scientifically positive verdict."""

    summary = result["summary"]
    expected_cycles = int(
        round(PHASE_C_DURATION_SECONDS / PHASE_C_QR_INTERVAL_SECONDS)
    )
    for run in result["runs"].values():
        if run["cycle_count"] != expected_cycles:
            raise AssertionError("Phase C cycle count is incomplete.")
        np.testing.assert_allclose(
            np.cumsum(run["_cycle_logs"], axis=0),
            run["_cumulative_logs"],
            rtol=0.0,
            atol=PHASE_B_BOOKKEEPING_LIMIT,
        )
        if not np.all(np.isfinite(run["_diagnostic"])):
            raise AssertionError("Phase C cumulative diagnostics are non-finite.")
    recomputed_internal = phase_c_internal_verdict(
        numerical_validity_accepted=summary["numerical_validity_accepted"],
        decorrelation_accepted=result["decorrelation"]["accepted"],
        within=result["within"],
        between=result["between"],
    )
    if recomputed_internal != summary["canonical_internal_verdict"]:
        raise AssertionError("Phase C internal verdict bookkeeping changed.")
    if result["cross"]["verdict"] != summary[
        "el_canonical_cross_formulation_verdict"
    ]:
        raise AssertionError("Phase C cross-formulation verdict bookkeeping changed.")


def run_crosscheck(output_dir: Path | None = None) -> dict[str, Any]:
    """Run the Phase C long-time canonical spectrum cross-check."""

    return run_phase_c(output_dir)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("a", "b", "c"), default="a")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
    )
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.output_dir is None:
        output_dir = (
            REPOSITORY_ROOT
            / "development/chaos_content/outputs"
            / {
                "a": "hamiltonian_canonical_phase_a/baseline",
                "b": "hamiltonian_canonical_phase_b/short_qr",
                "c": "hamiltonian_canonical_phase_c/640s_ensemble",
            }[args.phase]
        )
    else:
        output_dir = args.output_dir
    if args.phase == "a":
        result = run_phase_a(output_dir)
        if args.self_check:
            assert_self_check(result)
        printed = result
    elif args.phase == "b":
        result = run_phase_b(output_dir)
        if args.self_check:
            assert_self_check(result)
        printed = result
    else:
        result = run_phase_c(output_dir)
        if args.self_check:
            assert_phase_c_self_check(result)
        printed = result["summary"]
    print(json.dumps(_public(printed), indent=2, sort_keys=True))
