"""Guarded S1 native single-cell Lyapunov implementation.

This is the operational copy of the validated S1 compiled loop.  It preserves
the validated equations, SciPy 1.18.0 DOP853 source, controller, observation,
renormalisation, and diagnostic policies.  Build products are process-local
temporary files and are loaded only on a validated build.
"""

from __future__ import annotations

import ctypes
import hashlib
import platform
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Mapping

import numba
import numpy as np
import scipy
from numba import carray, cfunc, types

from .compiled import compiled_reference_and_tangent_rhs
from .evaluation import (
    RenormalizedTangentEvaluation,
    evaluate_renormalized_tangent_runner,
)
from .reference import (
    CandidateAMetric,
    PendulumParameters,
    RenormalizedTangentDiagnostics,
    RenormalizedTangentResult,
    RenormalizedTangentSpec,
    SolverSpec,
    _resolved_interval_max_step,
)


S1_EVALUATOR = "s1_native_dop853_v1"
S1_DOP_SOURCE_VERSION = "SciPy 1.18.0 dop.c/dop.h"
S1_BUILD_FLAGS = ("-O2", "-ffp-contract=on", "-fPIC", "-shared")
S1_VALIDATED_DURATIONS = (1.0, 2.0, 5.0, 10.0, 20.0)
S1_NATIVE_DIRECTORY = Path(__file__).with_name("s1_native")
S1_SOURCE_SHA256: Mapping[str, str] = {
    "dop.c": "14b9fdce5f18e6ad01eb814ec7965cc51804ba49b359d4bd6cf72a958239d213",
    "dop.h": "72549b5250fbfde34026b2bf1a8e65cbfdf1854dee35971a6922bfcbb9740944",
    "loop.c": "10137883d13d23ba5dc99aa6d7b50317632191202a8107b2b9e7d3cecb39fbbb",
    "LICENSE_DOP": "ed9bf58c6d74d3fad9d92d1d67d9bff8141d8ab60de784516b0711364fd43357",
}
S1_VALIDATED_COMPILER = "Apple clang version 17.0.0 (clang-1700.6.4.2)"
S1_VALIDATED_COMPILER_TARGET = "Target: arm64-apple-darwin24.6.0"


class S1NativeUnavailableError(RuntimeError):
    """The validated S1 native implementation could not be built or loaded."""


@dataclass(frozen=True)
class S1Eligibility:
    eligible: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class S1BuildSupport:
    supported: bool
    reason: str
    system: str
    machine: str
    macos: str
    python: str
    numpy: str
    scipy: str
    numba: str
    compiler: str | None
    compiler_target: str | None
    source_sha256: Mapping[str, str]


def _source_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((S1_NATIVE_DIRECTORY / name).read_bytes()).hexdigest()
        for name in S1_SOURCE_SHA256
    }


@lru_cache(maxsize=1)
def s1_build_support() -> S1BuildSupport:
    """Return the fail-closed allowlist decision for the validated S1 build."""

    system = platform.system()
    machine = platform.machine()
    macos = platform.mac_ver()[0]
    python_version = platform.python_version()
    compiler_path = shutil.which("clang")
    compiler = None
    compiler_target = None
    compiler_error = None
    if compiler_path is None:
        compiler_error = "clang was not found"
    else:
        try:
            completed = subprocess.run(
                [compiler_path, "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            lines = completed.stdout.splitlines()
            compiler = lines[0] if lines else None
            compiler_target = next(
                (line for line in lines if line.startswith("Target: ")),
                None,
            )
        except (OSError, subprocess.SubprocessError) as error:
            compiler_error = f"clang version probe failed: {type(error).__name__}"

    try:
        hashes = _source_hashes()
    except OSError as error:
        hashes = {}
        source_error = f"native source inspection failed: {type(error).__name__}"
    else:
        source_error = None

    checks = (
        (system == "Darwin", "operating system is not validated Darwin"),
        (machine == "arm64", "machine is not validated arm64"),
        (macos == "15.7.9", "macOS build is not validated 15.7.9"),
        (python_version == "3.12.3", "Python version is not validated 3.12.3"),
        (np.__version__ == "2.5.2", "NumPy version is not validated 2.5.2"),
        (scipy.__version__ == "1.18.0", "SciPy version is not validated 1.18.0"),
        (numba.__version__ == "0.67.0", "Numba version is not validated 0.67.0"),
        (compiler_error is None, compiler_error or ""),
        (compiler == S1_VALIDATED_COMPILER, "compiler version is not validated"),
        (
            compiler_target == S1_VALIDATED_COMPILER_TARGET,
            "compiler target is not validated",
        ),
        (source_error is None, source_error or ""),
        (hashes == dict(S1_SOURCE_SHA256), "native source digest is not validated"),
    )
    reason = next((message for passed, message in checks if not passed), "validated")
    return S1BuildSupport(
        supported=all(passed for passed, _message in checks),
        reason=reason,
        system=system,
        machine=machine,
        macos=macos,
        python=python_version,
        numpy=np.__version__,
        scipy=scipy.__version__,
        numba=numba.__version__,
        compiler=compiler,
        compiler_target=compiler_target,
        source_sha256=hashes,
    )


def s1_build_provenance() -> dict[str, object]:
    """Return JSON-safe source and validated-build identity."""

    return {
        "implementation": S1_EVALUATOR,
        "dop_source": S1_DOP_SOURCE_VERSION,
        "build_flags": list(S1_BUILD_FLAGS),
        **asdict(s1_build_support()),
    }


def s1_specification_eligibility(spec: RenormalizedTangentSpec) -> S1Eligibility:
    """Constrain S1 to the initially validated standard periodic-field policy."""

    state = spec.initial_state.as_array()
    reasons: list[str] = []
    if not (-np.pi <= state[0] < np.pi and -np.pi <= state[1] < np.pi):
        reasons.append("initial angles are outside the validated [-pi, pi) chart")
    if not np.array_equal(state[2:], np.zeros(2)):
        reasons.append("initial angular velocities are not the validated zero values")
    if spec.parameters != PendulumParameters():
        reasons.append("physical parameters differ from the validated standard values")
    if spec.initial_tangent != (1.0, 0.0, 0.0, 0.0):
        reasons.append("initial tangent differs from the validated standard vector")
    if spec.duration not in S1_VALIDATED_DURATIONS:
        reasons.append("duration is outside the validated horizon allowlist")
    if spec.renormalization_interval != 0.25:
        reasons.append("renormalisation interval differs from 0.25 seconds")
    if spec.sampling_interval != 0.01:
        reasons.append("sampling interval differs from 0.01 seconds")
    if spec.energy_drift_limit != 1.0e-7:
        reasons.append("energy-drift limit differs from the validated standard limit")
    if spec.renormalization_norm_tolerance != 1.0e-12:
        reasons.append("reset-norm limit differs from the validated standard limit")
    if spec.characteristic_length != 1.0:
        reasons.append("characteristic length differs from the validated standard value")
    if spec.solver != SolverSpec():
        reasons.append("solver configuration differs from the validated standard policy")
    return S1Eligibility(eligible=not reasons, reasons=tuple(reasons))


_double_ptr = types.CPointer(types.float64)
_int_ptr = types.CPointer(types.int32)


@lru_cache(maxsize=1)
def _native_callbacks():
    """Compile and retain the validated native RHS/reset callbacks lazily."""

    @cfunc(
        types.void(
            types.int32,
            types.float64,
            _double_ptr,
            _double_ptr,
            _double_ptr,
            _int_ptr,
        ),
        cache=False,
    )
    def rhs(n, time, state, output, parameters, error):
        y = carray(state, 8)
        p = carray(parameters, 5)
        result = compiled_reference_and_tangent_rhs(
            time, y, p[0], p[1], p[2], p[3], p[4]
        )
        for index in range(8):
            output[index] = result[index]

    @cfunc(
        types.int32(_double_ptr, types.float64, _double_ptr, _double_ptr),
        cache=False,
    )
    def reset(state, characteristic_time, stretch_out, norm_error_out):
        y = carray(state, 8)
        scaled = np.empty(4)
        for index in range(4):
            scaled[index] = y[index + 4] * (
                1.0 if index < 2 else characteristic_time
            )
        stretch = np.sqrt(np.dot(scaled, scaled))
        if not np.isfinite(stretch) or stretch <= 0:
            return 1
        for index in range(4):
            y[index + 4] = (scaled[index] / stretch) * (
                1.0 if index < 2 else 1.0 / characteristic_time
            )
        norm_squared = 0.0
        for index in range(4):
            value = y[index + 4] * (
                1.0 if index < 2 else characteristic_time
            )
            norm_squared += value * value
        norm_error_out[0] = abs(np.sqrt(norm_squared) - 1.0)
        stretch_out[0] = stretch
        for index in range(2):
            angle = (y[index] + np.pi) % (2.0 * np.pi) - np.pi
            y[index] = np.pi if angle == -np.pi else angle
        return 0

    return rhs, reset


@lru_cache(maxsize=1)
def native_library():
    """Build once per process and retain its temporary-directory lifetime."""

    support = s1_build_support()
    if not support.supported:
        raise S1NativeUnavailableError(support.reason)
    compiler_path = shutil.which("clang")
    if compiler_path is None:
        raise S1NativeUnavailableError("clang became unavailable after validation")
    directory = tempfile.TemporaryDirectory(prefix="s1-operational-loop-")
    library_path = Path(directory.name) / "s1_loop.so"
    command = [
        compiler_path,
        *S1_BUILD_FLAGS,
        str(S1_NATIVE_DIRECTORY / "dop.c"),
        str(S1_NATIVE_DIRECTORY / "loop.c"),
        "-o",
        str(library_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        library = ctypes.CDLL(str(library_path))
    except (OSError, subprocess.SubprocessError) as error:
        directory.cleanup()
        raise S1NativeUnavailableError(
            f"validated S1 native build/load failed: {type(error).__name__}"
        ) from error
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
    library.s1_loop.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        pointer,
        pointer,
        pointer,
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
        pointer,
        pointer,
    ]
    library.s1_loop.restype = ctypes.c_int
    library._temporary_directory = directory
    return library


def run_renormalized_tangent_s1(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentResult:
    """Run one S1 cell without eligibility selection or recovery routing."""

    if spec.solver.method.upper() != "DOP853":
        raise ValueError("S1 requires DOP853.")
    metric = CandidateAMetric(spec.characteristic_length, spec.parameters.gravity)
    initial = np.asarray(spec.initial_tangent, dtype=float)
    initial_unit = initial / float(metric.tangent_norm(initial))
    state = np.concatenate((spec.initial_state.as_array(), initial_unit))
    parameters = spec.parameters
    native_parameters = np.array(
        [
            parameters.length1,
            parameters.length2,
            parameters.mass1,
            parameters.mass2,
            parameters.gravity,
        ]
    )
    cycles = int(round(spec.duration / spec.renormalization_interval))
    boundaries = np.linspace(0.0, spec.duration, cycles + 1)
    max_step = _resolved_interval_max_step(
        spec.solver,
        spec.characteristic_length,
        parameters.gravity,
        spec.renormalization_interval,
    )
    output = np.empty((cycles, 4))
    stats = np.zeros(4)
    rhs, reset = _native_callbacks()
    code = native_library().s1_loop(
        rhs.address,
        reset.address,
        state,
        native_parameters,
        boundaries,
        cycles,
        spec.solver.rtol,
        spec.solver.atol,
        max_step,
        metric.characteristic_time,
        output,
        stats,
    )
    if code == 40:
        raise RuntimeError(
            "compiled DOP853 exceeded the declared max_step: "
            f"{stats[2]} > {max_step}."
        )
    if code:
        raise RuntimeError(f"S1 native loop failed with status {code}.")
    issues: list[str] = []
    if stats[0] > spec.energy_drift_limit:
        issues.append("reference energy drift exceeded its declared limit")
    if stats[1] > spec.renormalization_norm_tolerance:
        issues.append(
            "post-renormalization Candidate-A norm error exceeded its limit"
        )
    diagnostics = RenormalizedTangentDiagnostics(
        maximum_normalized_reference_energy_drift=float(stats[0]),
        maximum_post_renormalization_norm_error=float(stats[1]),
        max_step_seconds=max_step,
        segment_count=cycles,
        solver_function_evaluations=int(stats[3]),
        numerically_valid=not issues,
        validity_issues=tuple(issues),
    )
    return RenormalizedTangentResult(
        spec=spec,
        metric=metric,
        initial_unit_tangent=initial_unit,
        cycle_end_time=boundaries[1:],
        stretch_factor=output[:, 0].copy(),
        log_stretch_increment=output[:, 1].copy(),
        cumulative_log_stretch=output[:, 2].copy(),
        cumulative_finite_time_rate=output[:, 3].copy(),
        final_reference_state=state[:4].copy(),
        final_unit_tangent=state[4:].copy(),
        diagnostics=diagnostics,
    )


def evaluate_renormalized_tangent_s1(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentEvaluation:
    """Adapt S1 to the shared scalar result without performing recovery."""

    evaluation = evaluate_renormalized_tangent_runner(
        spec,
        runner=run_renormalized_tangent_s1,
        evaluator=S1_EVALUATOR,
    )
    return replace(
        evaluation,
        implementation_provenance=s1_build_provenance(),
    )
