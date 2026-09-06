"""Guarded compiled four-state RHS for the Experiment 020 first-flip contract."""

from __future__ import annotations

import hashlib
import math
import os
import platform
import sys
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

import llvmlite
import llvmlite.binding as llvm
import numba
import numpy as np
import scipy
from numba import njit

from ..lyapunov.reference import EulerLagrangeState, PendulumParameters, SolverSpec
from .reference import FirstFlipResult, default_solver_spec, first_flip_time


FIRST_FLIP_COMPILED_EVALUATOR = "numba_rhs_solve_ivp_first_flip_v1"
FIRST_FLIP_COMPILED_IMPLEMENTATION = "first_flip_numba_4state_rhs_v1"
VALIDATED_ENERGY_DRIFT_LIMIT = 5.0e-9
VALIDATED_EVENT_RESIDUAL_LIMIT = 1.0e-10
VALIDATED_ANGULAR_INCREMENT_LIMIT = 0.5


class FirstFlipCompiledUnavailableError(RuntimeError):
    """The validated compiled RHS cannot be initialized in this process."""


@dataclass(frozen=True)
class FirstFlipCompiledSupport:
    supported: bool
    reason: str
    system: str
    machine: str
    macos: str
    python: str
    numpy: str
    scipy: str
    numba: str
    llvmlite: str
    llvm: str


@dataclass(frozen=True)
class FirstFlipCompiledEligibility:
    eligible: bool
    reasons: tuple[str, ...] = ()


@njit(cache=True)
def compiled_physical_rhs(
    time_value: float,
    state: np.ndarray,
    length1: float,
    length2: float,
    mass1: float,
    mass2: float,
    gravity: float,
) -> np.ndarray:
    """Return the unchanged four-state absolute-angle Euler--Lagrange flow."""

    theta1, theta2, omega1, omega2 = state
    difference = theta1 - theta2
    sine = math.sin(difference)
    cosine = math.cos(difference)
    denominator = 2.0 * mass1 + mass2 - mass2 * math.cos(2.0 * difference)
    first_inner = length2 * omega2 * omega2 + length1 * omega1 * omega1 * cosine
    first_acceleration = (
        -gravity * (2.0 * mass1 + mass2) * math.sin(theta1)
        - mass2 * gravity * math.sin(theta1 - 2.0 * theta2)
        - 2.0 * mass2 * sine * first_inner
    ) / (length1 * denominator)
    second_inner = (
        length1 * omega1 * omega1 * (mass1 + mass2)
        + gravity * (mass1 + mass2) * math.cos(theta1)
        + length2 * mass2 * omega2 * omega2 * cosine
    )
    second_acceleration = 2.0 * sine * second_inner / (length2 * denominator)
    result = np.empty(4, dtype=np.float64)
    result[0] = omega1
    result[1] = omega2
    result[2] = first_acceleration
    result[3] = second_acceleration
    return result


@lru_cache(maxsize=1)
def first_flip_compiled_support() -> FirstFlipCompiledSupport:
    values = {
        "system": platform.system(),
        "machine": platform.machine(),
        "macos": platform.mac_ver()[0],
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "numba": numba.__version__,
        "llvmlite": llvmlite.__version__,
        "llvm": ".".join(str(value) for value in llvm.llvm_version_info),
    }
    checks = (
        (values["system"] == "Darwin", "operating system is not validated Darwin"),
        (values["machine"] == "arm64", "machine is not validated arm64"),
        (values["macos"] == "15.7.9", "macOS build is not validated 15.7.9"),
        (values["python"] == "3.12.3", "Python version is not validated 3.12.3"),
        (values["numpy"] == "2.5.2", "NumPy version is not validated 2.5.2"),
        (values["scipy"] == "1.18.0", "SciPy version is not validated 1.18.0"),
        (values["numba"] == "0.67.0", "Numba version is not validated 0.67.0"),
        (values["llvmlite"] == "0.49.0", "llvmlite version is not validated 0.49.0"),
        (values["llvm"] == "22.1.0", "LLVM version is not validated 22.1.0"),
        (os.environ.get("NUMBA_DISABLE_JIT") != "1", "Numba JIT is disabled"),
    )
    reason = next((message for passed, message in checks if not passed), "validated")
    return FirstFlipCompiledSupport(
        supported=all(passed for passed, _ in checks), reason=reason, **values
    )


def first_flip_compiled_eligibility(
    parameters: PendulumParameters,
    solver: SolverSpec,
    observation_horizon: float,
    initial_angular_velocities: Sequence[float] = (0.0, 0.0),
    energy_drift_limit: float = VALIDATED_ENERGY_DRIFT_LIMIT,
    event_residual_limit: float = VALIDATED_EVENT_RESIDUAL_LIMIT,
    angular_increment_limit: float = VALIDATED_ANGULAR_INCREMENT_LIMIT,
) -> FirstFlipCompiledEligibility:
    standard_parameters = PendulumParameters()
    standard_solver = default_solver_spec(standard_parameters)
    reasons: list[str] = []
    if parameters != standard_parameters:
        reasons.append("physical parameters are outside the validated unit policy")
    if solver != standard_solver:
        reasons.append("solver configuration is outside the validated policy")
    if observation_horizon != 5.0:
        reasons.append("observation horizon is outside the validated T=5 policy")
    if tuple(initial_angular_velocities) != (0.0, 0.0):
        reasons.append("initial angular velocities are outside the zero-velocity policy")
    if energy_drift_limit != VALIDATED_ENERGY_DRIFT_LIMIT:
        reasons.append("energy diagnostic policy is outside the validated policy")
    if event_residual_limit != VALIDATED_EVENT_RESIDUAL_LIMIT:
        reasons.append("event residual policy is outside the validated policy")
    if angular_increment_limit != VALIDATED_ANGULAR_INCREMENT_LIMIT:
        reasons.append("angular increment policy is outside the validated policy")
    return FirstFlipCompiledEligibility(not reasons, tuple(reasons))


def compiled_rhs(parameters: PendulumParameters) -> Callable[[float, np.ndarray], np.ndarray]:
    values = (
        parameters.length1,
        parameters.length2,
        parameters.mass1,
        parameters.mass2,
        parameters.gravity,
    )

    def evaluate(time_value: float, state: np.ndarray) -> np.ndarray:
        return compiled_physical_rhs(time_value, state, *values)

    return evaluate


@lru_cache(maxsize=4)
def initialize_compiled_rhs(parameters: PendulumParameters) -> Callable[[float, np.ndarray], np.ndarray]:
    support = first_flip_compiled_support()
    if not support.supported:
        raise FirstFlipCompiledUnavailableError(support.reason)
    function = compiled_rhs(parameters)
    try:
        output = function(0.0, np.zeros(4, dtype=np.float64))
    except Exception as error:
        raise FirstFlipCompiledUnavailableError(
            f"compiled first-flip RHS initialization failed: {type(error).__name__}"
        ) from error
    if output.shape != (4,) or not np.all(np.isfinite(output)):
        raise FirstFlipCompiledUnavailableError("compiled first-flip RHS warm-up was invalid")
    return function


def first_flip_time_compiled(
    initial_state: EulerLagrangeState | Sequence[float],
    parameters: PendulumParameters,
    solver_spec: SolverSpec,
    observation_horizon: float,
) -> FirstFlipResult:
    return first_flip_time(
        initial_state,
        parameters=parameters,
        solver_spec=solver_spec,
        observation_horizon=observation_horizon,
        _rhs_override=initialize_compiled_rhs(parameters),
    )


def first_flip_compiled_provenance(
    failure: BaseException | None = None,
) -> dict[str, object]:
    source = Path(__file__)
    support = first_flip_compiled_support()
    return {
        "implementation": FIRST_FLIP_COMPILED_IMPLEMENTATION,
        "route": FIRST_FLIP_COMPILED_EVALUATOR,
        "kernel_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "compilation": {"nopython": True, "cache": True, "fastmath": False},
        "python_abi": sys.implementation.cache_tag,
        "support": asdict(support),
        "available": failure is None and support.supported,
        "failure_type": type(failure).__name__ if failure else None,
        "failure_reason": str(failure) if failure else None,
    }
