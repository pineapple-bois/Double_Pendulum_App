"""Investigation-only native DOP853 first-flip prototype."""

from __future__ import annotations

import ctypes
import hashlib
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Sequence

import numpy as np
from numba import carray, cfunc, types

from ....src.first_flip.compiled import compiled_physical_rhs
from ....src.first_flip.reference import (
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
from ....src.lyapunov.reference import (
    EulerLagrangeState,
    PendulumParameters,
    SolverSpec,
    simple_energy,
)
from ....src.lyapunov.s1_artifacts import (
    S1_BUILD_FLAGS,
    S1_NATIVE_DIRECTORY,
    S1_SOURCE_SHA256,
    s1_build_support,
)


PROTOTYPE_IDENTITY = "investigation_native_dop853_first_flip_v1"
NATIVE_DIRECTORY = Path(__file__).with_name("first_flip_native")
LOOP_SOURCE = NATIVE_DIRECTORY / "first_flip_loop.c"
LICENSE_SOURCE = S1_NATIVE_DIRECTORY / "LICENSE_DOP"
NATIVE_STATS_SIZE = 15
_DENSE_COUNTER_DEFECT = "                nfcn += 3;"
_DENSE_COUNTER_CORRECTION = "                *nfcn += 3;"


class NativeFirstFlipPrototypeError(RuntimeError):
    """The investigation-only native prototype could not run safely."""


@dataclass(frozen=True)
class NativeFirstFlipExecution:
    result: FirstFlipResult
    evaluator_wall_seconds: float
    native_loop_wall_seconds: float
    native_status: int
    native_dop853_status: int
    accepted_steps: int
    rejected_steps: int
    maximum_solver_step_seconds: float
    terminal_candidate_count: int
    root_iterations: int


@dataclass(frozen=True)
class _NativeRuntime:
    library: ctypes.CDLL
    rhs_callback: object
    temporary_directory: tempfile.TemporaryDirectory[str]
    library_sha256: str
    patched_dop_sha256: str


_double_pointer = types.CPointer(types.float64)
_int_pointer = types.CPointer(types.int32)


def _rhs_callback_impl(n, time_value, state, output, parameters, error):
    values = carray(state, 4)
    physical = carray(parameters, 5)
    result = compiled_physical_rhs(
        time_value,
        values,
        physical[0],
        physical[1],
        physical[2],
        physical[3],
        physical[4],
    )
    for index in range(4):
        output[index] = result[index]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _patched_dop_source() -> str:
    source_path = S1_NATIVE_DIRECTORY / "dop.c"
    source = source_path.read_text()
    if source.count(_DENSE_COUNTER_DEFECT) != 1:
        raise NativeFirstFlipPrototypeError(
            "vendored DOP853 dense-counter source does not match the reviewed input"
        )
    return source.replace(_DENSE_COUNTER_DEFECT, _DENSE_COUNTER_CORRECTION)


@lru_cache(maxsize=1)
def native_runtime() -> _NativeRuntime:
    """Build and retain one process-local investigation runtime."""

    support = s1_build_support()
    if not support.supported:
        raise NativeFirstFlipPrototypeError(support.reason)
    compiler = shutil.which("clang")
    if compiler is None:
        raise NativeFirstFlipPrototypeError("clang is unavailable")
    if not LOOP_SOURCE.is_file() or not LICENSE_SOURCE.is_file():
        raise NativeFirstFlipPrototypeError("prototype source or DOP853 license is missing")

    runtime_directory = tempfile.TemporaryDirectory(
        prefix="first-flip-native-dop853-"
    )
    build_directory = Path(runtime_directory.name)
    patched_dop = build_directory / "dop.c"
    patched_dop.write_text(_patched_dop_source())
    library_path = build_directory / "first_flip_native.so"
    command = [
        compiler,
        *S1_BUILD_FLAGS,
        "-I",
        str(build_directory),
        "-I",
        str(S1_NATIVE_DIRECTORY),
        str(LOOP_SOURCE),
        "-o",
        str(library_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        library = ctypes.CDLL(str(library_path))
        rhs_callback = cfunc(
            types.void(
                types.int32,
                types.float64,
                _double_pointer,
                _double_pointer,
                _double_pointer,
                _int_pointer,
            ),
            cache=False,
        )(_rhs_callback_impl)
    except Exception as error:
        runtime_directory.cleanup()
        raise NativeFirstFlipPrototypeError(
            f"native prototype build failed: {type(error).__name__}"
        ) from error

    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
    library.first_flip_loop.argtypes = [
        ctypes.c_void_p,
        pointer,
        pointer,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        pointer,
    ]
    library.first_flip_loop.restype = ctypes.c_int
    return _NativeRuntime(
        library=library,
        rhs_callback=rhs_callback,
        temporary_directory=runtime_directory,
        library_sha256=_sha256(library_path),
        patched_dop_sha256=_sha256(patched_dop),
    )


def _event_metadata(
    state0: np.ndarray,
    event_state_array: np.ndarray | None,
    event_index: int | None,
    parameters: PendulumParameters,
) -> tuple[
    tuple,
    EventAttribution,
    int | None,
    int | None,
    tuple[EventSurfaceResidual, ...],
    tuple[float, ...],
    float | None,
    float | None,
    float | None,
]:
    if event_state_array is None or event_index is None:
        return (), EventAttribution.NOT_APPLICABLE, None, None, (), (), None, None, None
    identity = EVENT_IDENTITIES[event_index]
    identities = (identity,)
    residuals = tuple(
        EventSurfaceResidual(
            identity=item,
            residual=_surface_value(item, event_state_array, state0),
        )
        for item in EVENT_IDENTITIES
    )
    competing_margin = min(
        abs(item.residual) for item in residuals if item.identity != identity
    )
    event_energy = float(simple_energy(event_state_array, parameters))
    initial_energy = float(simple_energy(state0, parameters))
    return (
        identities,
        EventAttribution.UNIQUE,
        identity.arm,
        identity.direction,
        residuals,
        (float(event_state_array[identity.arm + 1]),),
        competing_margin,
        event_energy,
        abs(event_energy - initial_energy) / energy_scale(parameters),
    )


def run_native_first_flip(
    initial_state: EulerLagrangeState | Sequence[float],
    parameters: PendulumParameters | None = None,
    solver_spec: SolverSpec | None = None,
    observation_horizon: float = 5.0,
) -> NativeFirstFlipExecution:
    """Execute the investigation-only native solver and construct the trusted type."""

    evaluator_started = perf_counter()
    parameters = parameters or PendulumParameters()
    solver_spec = solver_spec or default_solver_spec(parameters)
    if solver_spec.method.upper() != "DOP853":
        raise ValueError("native first-flip prototype requires DOP853")
    if solver_spec.max_step is None:
        raise ValueError("native first-flip prototype requires the declared max_step")
    horizon = float(observation_horizon)
    if not math.isfinite(horizon) or horizon <= 0.0:
        raise ValueError("observation_horizon must be positive and finite")
    state0 = _initial_state_array(initial_state)
    state = np.ascontiguousarray(state0.copy(), dtype=np.float64)
    native_parameters = np.ascontiguousarray(
        [
            parameters.length1,
            parameters.length2,
            parameters.mass1,
            parameters.mass2,
            parameters.gravity,
        ],
        dtype=np.float64,
    )
    stats = np.zeros(NATIVE_STATS_SIZE, dtype=np.float64)
    runtime = native_runtime()
    native_started = perf_counter()
    code = int(
        runtime.library.first_flip_loop(
            runtime.rhs_callback.address,
            state,
            native_parameters,
            horizon,
            solver_spec.rtol,
            solver_spec.atol,
            float(solver_spec.max_step),
            stats,
        )
    )
    native_wall = perf_counter() - native_started
    if code != 0:
        raise NativeFirstFlipPrototypeError(
            f"native first-flip loop failed with status {code} "
            f"(DOP853 status {int(stats[11])})"
        )
    if not np.all(np.isfinite(state)) or not np.all(np.isfinite(stats)):
        raise NativeFirstFlipPrototypeError("native first-flip output is non-finite")
    max_step_allowance = 64.0 * np.finfo(float).eps * max(
        1.0, abs(float(solver_spec.max_step))
    )
    if stats[8] > float(solver_spec.max_step) + max_step_allowance:
        raise NativeFirstFlipPrototypeError("native DOP853 exceeded max_step")

    event_observed = bool(round(float(stats[0])))
    event_index = int(round(float(stats[1]))) if event_observed else None
    if event_index is not None and not 0 <= event_index < len(EVENT_IDENTITIES):
        raise NativeFirstFlipPrototypeError("native event identity is invalid")
    event_time = float(stats[2]) if event_observed else None
    event_state_array = state.copy() if event_observed else None
    (
        identities,
        attribution,
        winning_arm,
        winning_direction,
        residuals,
        triggering_velocities,
        competing_margin,
        event_energy,
        event_energy_drift,
    ) = _event_metadata(state0, event_state_array, event_index, parameters)
    initial_energy = float(simple_energy(state0, parameters))
    status = (
        FirstFlipStatus.EVENT_OBSERVED
        if event_observed
        else FirstFlipStatus.RIGHT_CENSORED
    )
    raw_event_counts = tuple(
        1 if event_index == index else 0 for index in range(len(EVENT_IDENTITIES))
    )
    result = FirstFlipResult(
        status=status,
        event_observed=event_observed,
        censored=not event_observed,
        solver_success=True,
        numerically_valid=True,
        solver_message="investigation native DOP853 completed",
        attribution=attribution,
        event_time_seconds=event_time,
        dimensionless_event_time=(
            event_time / gravity_timescale(parameters)
            if event_time is not None
            else None
        ),
        event_identities=identities,
        winning_arm=winning_arm,
        winning_direction=winning_direction,
        event_state=(
            tuple(float(value) for value in event_state_array)
            if event_state_array is not None
            else None
        ),
        event_surface_residuals=residuals,
        triggering_angular_velocities=triggering_velocities,
        minimum_competing_surface_margin=competing_margin,
        initial_state=tuple(float(value) for value in state0),
        observation_horizon_seconds=horizon,
        integration_endpoint_seconds=float(stats[12]),
        gravity_timescale_seconds=gravity_timescale(parameters),
        reference_length_metres=parameters.length1,
        solver_method=solver_spec.method,
        solver_rtol=solver_spec.rtol,
        solver_atol=solver_spec.atol,
        effective_max_step_seconds=solver_spec.max_step,
        rhs_evaluations=int(round(float(stats[6]))),
        jacobian_evaluations=0,
        lu_decompositions=0,
        accepted_point_count=int(round(float(stats[7]))),
        maximum_accepted_angular_increment=float(stats[5]),
        initial_energy_joules=initial_energy,
        event_energy_joules=event_energy,
        maximum_absolute_energy_error_joules=float(stats[3]),
        maximum_normalized_energy_drift=float(stats[4]),
        event_normalized_energy_drift=event_energy_drift,
        wall_seconds=native_wall,
        raw_event_counts=raw_event_counts,
        validation_issues=(),
    )
    return NativeFirstFlipExecution(
        result=result,
        evaluator_wall_seconds=perf_counter() - evaluator_started,
        native_loop_wall_seconds=native_wall,
        native_status=code,
        native_dop853_status=int(round(float(stats[11]))),
        accepted_steps=int(round(float(stats[13]))),
        rejected_steps=int(round(float(stats[14]))),
        maximum_solver_step_seconds=float(stats[8]),
        terminal_candidate_count=int(round(float(stats[9]))),
        root_iterations=int(round(float(stats[10]))),
    )


def first_flip_time_native(
    initial_state: EulerLagrangeState | Sequence[float],
    parameters: PendulumParameters | None = None,
    solver_spec: SolverSpec | None = None,
    observation_horizon: float = 5.0,
) -> FirstFlipResult:
    return run_native_first_flip(
        initial_state,
        parameters=parameters,
        solver_spec=solver_spec,
        observation_horizon=observation_horizon,
    ).result


def prototype_source_identity() -> dict[str, object]:
    runtime = native_runtime()
    return {
        "prototype": PROTOTYPE_IDENTITY,
        "loop_source_sha256": _sha256(LOOP_SOURCE),
        "vendored_source_sha256": {
            name: _sha256(S1_NATIVE_DIRECTORY / name)
            for name in ("dop.c", "dop.h", "LICENSE_DOP")
        },
        "expected_s1_source_sha256": {
            name: S1_SOURCE_SHA256[name]
            for name in ("dop.c", "dop.h", "LICENSE_DOP")
        },
        "dense_counter_correction": (
            f"{_DENSE_COUNTER_DEFECT.strip()} -> "
            f"{_DENSE_COUNTER_CORRECTION.strip()}"
        ),
        "patched_dop_sha256": runtime.patched_dop_sha256,
        "native_library_sha256": runtime.library_sha256,
        "compiler_flags": list(S1_BUILD_FLAGS),
    }
