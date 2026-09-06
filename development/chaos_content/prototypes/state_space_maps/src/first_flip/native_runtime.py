"""Guarded native DOP853 first-flip production candidate."""

from __future__ import annotations

import ctypes
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Sequence

import numpy as np
from numba import carray, cfunc, types

from ..lyapunov.reference import EulerLagrangeState, PendulumParameters, SolverSpec, simple_energy
from .compiled import compiled_physical_rhs, first_flip_compiled_eligibility
from .native_artifacts import (
    FIRST_FLIP_NATIVE_EVALUATOR,
    FIRST_FLIP_NATIVE_IMPLEMENTATION,
    FIRST_FLIP_NATIVE_LIBRARY,
    FirstFlipNativeArtifact,
    FirstFlipNativeUnavailableError,
    ensure_first_flip_native_artifact,
    first_flip_native_artifact_identity,
    first_flip_native_artifact_key,
    first_flip_native_support,
    load_first_flip_native_artifact,
    unavailable_first_flip_native_artifact,
)
from .reference import (
    EVENT_IDENTITIES,
    EventAttribution,
    EventSurfaceResidual,
    FirstFlipResult,
    FirstFlipStatus,
    _initial_state_array,
    _surface_value,
    default_solver_spec,
    energy_scale,
    gravity_timescale,
)

NATIVE_STATS_SIZE = 15


class FirstFlipNativeNumericalError(RuntimeError):
    """A known native solver/output failure that may use trusted recovery."""


@dataclass(frozen=True)
class FirstFlipNativeExecution:
    result: FirstFlipResult
    native_status: int
    native_dop853_status: int
    accepted_steps: int
    rejected_steps: int
    maximum_solver_step_seconds: float
    terminal_candidate_count: int
    root_iterations: int


_double_pointer = types.CPointer(types.float64)
_int_pointer = types.CPointer(types.int32)


def _rhs_callback_impl(n, time_value, state, output, parameters, error):
    values = carray(state, 4)
    physical = carray(parameters, 5)
    result = compiled_physical_rhs(time_value, values, physical[0], physical[1], physical[2], physical[3], physical[4])
    for index in range(4):
        output[index] = result[index]


@lru_cache(maxsize=1)
def _native_rhs_callback():
    return cfunc(
        types.void(types.int32, types.float64, _double_pointer, _double_pointer, _double_pointer, _int_pointer),
        cache=True,
    )(_rhs_callback_impl)


_ACTIVE_ARTIFACT: FirstFlipNativeArtifact | None = None


def configure_first_flip_native_artifact(artifact: FirstFlipNativeArtifact | None) -> None:
    global _ACTIVE_ARTIFACT
    _ACTIVE_ARTIFACT = artifact


@lru_cache(maxsize=4)
def _validated_artifact(key: str, directory: str, manifest_sha256: str) -> FirstFlipNativeArtifact:
    return load_first_flip_native_artifact(
        FirstFlipNativeArtifact(True, key, directory, manifest_sha256, None, first_flip_native_artifact_identity())
    )


def _runtime_artifact() -> FirstFlipNativeArtifact:
    artifact = _ACTIVE_ARTIFACT or ensure_first_flip_native_artifact()
    if not artifact.available or artifact.directory is None or artifact.manifest_sha256 is None:
        raise FirstFlipNativeUnavailableError(artifact.failure_reason or "native artifact unavailable")
    return _validated_artifact(artifact.key, artifact.directory, artifact.manifest_sha256)


@lru_cache(maxsize=4)
def _library(key: str, directory: str):
    del key
    try:
        library = ctypes.CDLL(str(Path(directory) / FIRST_FLIP_NATIVE_LIBRARY))
    except OSError as error:
        raise FirstFlipNativeUnavailableError(f"native library load failed: {type(error).__name__}") from error
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
    library.first_flip_loop.argtypes = [ctypes.c_void_p, pointer, pointer, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, pointer]
    library.first_flip_loop.restype = ctypes.c_int
    return library


def initialize_native_first_flip(parameters: PendulumParameters = PendulumParameters()) -> None:
    if parameters != PendulumParameters():
        raise FirstFlipNativeUnavailableError("parameters are outside the native validated policy")
    artifact = _runtime_artifact()
    callback = _native_rhs_callback()
    if callback.address <= 0:
        raise FirstFlipNativeUnavailableError("native callback reconstruction failed")
    _library(artifact.key, artifact.directory or "")


def clear_first_flip_native_process_runtime() -> None:
    global _ACTIVE_ARTIFACT
    _ACTIVE_ARTIFACT = None
    _native_rhs_callback.cache_clear()
    _validated_artifact.cache_clear()
    _library.cache_clear()


def _event_metadata(state0, event_state, event_index, parameters):
    if event_state is None or event_index is None:
        return (), EventAttribution.NOT_APPLICABLE, None, None, (), (), None, None, None
    identity = EVENT_IDENTITIES[event_index]
    residuals = tuple(EventSurfaceResidual(item, _surface_value(item, event_state, state0)) for item in EVENT_IDENTITIES)
    initial_energy = float(simple_energy(state0, parameters))
    event_energy = float(simple_energy(event_state, parameters))
    return (
        (identity,), EventAttribution.UNIQUE, identity.arm, identity.direction, residuals,
        (float(event_state[identity.arm + 1]),),
        min(abs(item.residual) for item in residuals if item.identity != identity),
        event_energy, abs(event_energy - initial_energy) / energy_scale(parameters),
    )


def run_native_first_flip(
    initial_state: EulerLagrangeState | Sequence[float],
    parameters: PendulumParameters | None = None,
    solver_spec: SolverSpec | None = None,
    observation_horizon: float = 5.0,
) -> FirstFlipNativeExecution:
    parameters = parameters or PendulumParameters()
    solver_spec = solver_spec or default_solver_spec(parameters)
    eligibility = first_flip_compiled_eligibility(parameters, solver_spec, observation_horizon)
    if not eligibility.eligible:
        raise ValueError("native first-flip specification is ineligible: " + "; ".join(eligibility.reasons))
    state0 = _initial_state_array(initial_state)
    if state0[2] != 0.0 or state0[3] != 0.0:
        raise ValueError("native first-flip requires zero initial angular velocities")
    if not math.isfinite(observation_horizon) or observation_horizon <= 0.0 or solver_spec.max_step is None:
        raise ValueError("native first-flip requires a finite horizon and max_step")
    initialize_native_first_flip(parameters)
    artifact = _runtime_artifact()
    state = np.ascontiguousarray(state0.copy(), dtype=np.float64)
    physical = np.ascontiguousarray([parameters.length1, parameters.length2, parameters.mass1, parameters.mass2, parameters.gravity], dtype=np.float64)
    stats = np.zeros(NATIVE_STATS_SIZE, dtype=np.float64)
    started = perf_counter()
    code = int(_library(artifact.key, artifact.directory or "").first_flip_loop(
        _native_rhs_callback().address, state, physical, float(observation_horizon), solver_spec.rtol, solver_spec.atol, float(solver_spec.max_step), stats
    ))
    wall = perf_counter() - started
    if code != 0:
        raise FirstFlipNativeNumericalError(f"native loop failed with status {code} (DOP853 {int(stats[11])})")
    if not np.all(np.isfinite(state)) or not np.all(np.isfinite(stats)):
        raise FirstFlipNativeNumericalError("native first-flip output is non-finite")
    allowance = 64.0 * np.finfo(float).eps * max(1.0, abs(float(solver_spec.max_step)))
    if stats[8] > float(solver_spec.max_step) + allowance:
        raise FirstFlipNativeNumericalError("native DOP853 exceeded max_step")
    observed = bool(round(float(stats[0])))
    event_index = int(round(float(stats[1]))) if observed else None
    if event_index is not None and not 0 <= event_index < len(EVENT_IDENTITIES):
        raise FirstFlipNativeNumericalError("native event identity is invalid")
    event_time = float(stats[2]) if observed else None
    event_state = state.copy() if observed else None
    identities, attribution, arm, direction, residuals, velocities, margin, event_energy, event_drift = _event_metadata(state0, event_state, event_index, parameters)
    initial_energy = float(simple_energy(state0, parameters))
    result = FirstFlipResult(
        status=FirstFlipStatus.EVENT_OBSERVED if observed else FirstFlipStatus.RIGHT_CENSORED,
        event_observed=observed, censored=not observed, solver_success=True, numerically_valid=True,
        solver_message="native DOP853 first-flip candidate completed", attribution=attribution,
        event_time_seconds=event_time, dimensionless_event_time=event_time / gravity_timescale(parameters) if event_time is not None else None,
        event_identities=identities, winning_arm=arm, winning_direction=direction,
        event_state=tuple(float(value) for value in event_state) if event_state is not None else None,
        event_surface_residuals=residuals, triggering_angular_velocities=velocities,
        minimum_competing_surface_margin=margin, initial_state=tuple(float(value) for value in state0),
        observation_horizon_seconds=float(observation_horizon), integration_endpoint_seconds=float(stats[12]),
        gravity_timescale_seconds=gravity_timescale(parameters), reference_length_metres=parameters.length1,
        solver_method=solver_spec.method, solver_rtol=solver_spec.rtol, solver_atol=solver_spec.atol,
        effective_max_step_seconds=solver_spec.max_step, rhs_evaluations=int(round(float(stats[6]))),
        jacobian_evaluations=0, lu_decompositions=0, accepted_point_count=int(round(float(stats[7]))),
        maximum_accepted_angular_increment=float(stats[5]), initial_energy_joules=initial_energy,
        event_energy_joules=event_energy, maximum_absolute_energy_error_joules=float(stats[3]),
        maximum_normalized_energy_drift=float(stats[4]), event_normalized_energy_drift=event_drift,
        wall_seconds=wall, raw_event_counts=tuple(1 if event_index == i else 0 for i in range(4)), validation_issues=(),
    )
    return FirstFlipNativeExecution(result, code, int(round(stats[11])), int(round(stats[13])), int(round(stats[14])), float(stats[8]), int(round(stats[9])), int(round(stats[10])))


def first_flip_time_native(*args, **kwargs) -> FirstFlipResult:
    return run_native_first_flip(*args, **kwargs).result


def first_flip_native_provenance(failure: BaseException | None = None) -> dict[str, object]:
    artifact = _ACTIVE_ARTIFACT
    if artifact is None and failure is None:
        try:
            artifact = _runtime_artifact()
        except FirstFlipNativeUnavailableError as error:
            failure = error
    if artifact is None:
        artifact = unavailable_first_flip_native_artifact(failure or FirstFlipNativeUnavailableError("not initialized"))
    return {
        "implementation": FIRST_FLIP_NATIVE_IMPLEMENTATION,
        "route": FIRST_FLIP_NATIVE_EVALUATOR,
        "support": first_flip_native_support(),
        "artifact": {
            "key": artifact.key,
            "available": artifact.available and failure is None,
            "manifest_sha256": artifact.manifest_sha256,
            "native_library_sha256": artifact.library_sha256,
            "identity": dict(artifact.identity),
            "failure_type": type(failure).__name__ if failure else artifact.failure_type,
            "failure_reason": str(failure) if failure else artifact.failure_reason,
        },
    }
