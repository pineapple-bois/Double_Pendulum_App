"""Non-computational scaffold for Experiment 011.

This module records the intended boundary and interfaces for a future
Hamiltonian/canonical spectrum cross-check. It deliberately contains no
Hamiltonian derivation, tangent dynamics, QR integration, or numerical run.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, Sequence


EXPERIMENT_STATUS = "scaffolded_in_preparation"
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
    """One repository source identified by the scaffold inventory."""

    role: str
    path: str
    symbols: tuple[str, ...]
    authority: str


SOURCE_ASSETS = (
    SourceAsset(
        role="canonical state and EL-to-canonical initial-state map",
        path="src/double_pendulum/models/initial_conditions.py",
        symbols=(
            "HAMILTONIAN_STATE_VARIABLE_NAMES",
            "HAMILTONIAN_SOLVER_STATE_CONVENTION",
            "angular_velocities_to_canonical_momenta",
            "hamiltonian_solver_initial_conditions",
        ),
        authority="accepted_production_model_convention",
    ),
    SourceAsset(
        role="symbolic simple Hamiltonian and Hamilton equations",
        path="src/double_pendulum/math/functions.py",
        symbols=(
            "derive_canonical_momenta",
            "compute_hamiltonian",
            "compute_hamiltons_equations",
            "hamiltonian_system",
        ),
        authority="accepted_production_symbolic_asset",
    ),
    SourceAsset(
        role="production canonical solver wrapper",
        path="src/double_pendulum/models/hamiltonian.py",
        symbols=("hamiltonian_first_order_system", "DoublePendulumHamiltonian"),
        authority="accepted_production_model_convention",
    ),
    SourceAsset(
        role="explicit numerical Hamiltonian, inverse Legendre map, and RHS",
        path=(
            "development/chaos_content/experiments/"
            "001_hamiltonian_poincare/minimal_hamiltonian_poincare.py"
        ),
        symbols=(
            "inertia_matrix",
            "momenta_from_angles_and_velocities",
            "hamiltonian",
            "angular_velocities",
            "hamiltonian_rhs",
        ),
        authority="exploratory_reference_requiring_independent_verification",
    ),
)


class CanonicalModelProtocol(Protocol):
    """Small eventual interface; no implementation is supplied here."""

    def el_to_canonical(self, el_state: Sequence[float]) -> Sequence[float]: ...

    def canonical_to_el(self, canonical_state: Sequence[float]) -> Sequence[float]: ...

    def energy(self, canonical_state: Sequence[float]) -> float: ...

    def rhs(self, time: float, canonical_state: Sequence[float]) -> Sequence[float]: ...

    def jacobian(
        self, time: float, canonical_state: Sequence[float]
    ) -> Sequence[Sequence[float]]: ...


def scaffold_manifest() -> dict[str, object]:
    """Return static provenance without constructing or running a model."""

    return {
        "experiment": "011_hamiltonian_canonical_spectrum_crosscheck",
        "status": EXPERIMENT_STATUS,
        "scientific_result_available": False,
        "canonical_state_order": list(CANONICAL_STATE_ORDER),
        "el_state_order": list(EL_STATE_ORDER),
        "experiment_010_target": asdict(EXPERIMENT_010_TARGET),
        "evidence_sequence": list(EVIDENCE_SEQUENCE),
        "source_assets": [asdict(asset) for asset in SOURCE_ASSETS],
        "claim_boundary": (
            "No canonical tangent flow, QR calculation, or Hamiltonian spectrum "
            "has been implemented, computed, or accepted."
        ),
    }


def missing_source_paths(repository_root: Path) -> tuple[str, ...]:
    """Return inventory paths absent from a checkout; this performs no derivation."""

    return tuple(
        asset.path
        for asset in SOURCE_ASSETS
        if not (repository_root / asset.path).is_file()
    )


def run_crosscheck() -> None:
    """Refuse execution until Experiment 011 receives a validated contract."""

    raise NotImplementedError(
        "Experiment 011 is scaffolding only; no Hamiltonian spectrum calculation "
        "has been implemented."
    )
