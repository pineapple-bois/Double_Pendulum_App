"""Isolated S1 experiment: unchanged SciPy DOP853 with native callbacks.

No production imports this module. A C compiler is required. Build products live
in a temporary directory, never alongside the sources. No fast-math is enabled.
"""
from __future__ import annotations

import ctypes
from functools import lru_cache
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from numba import carray, cfunc, types

from ....src.lyapunov.compiled import compiled_reference_and_tangent_rhs
from ....src.lyapunov.evaluation import evaluate_renormalized_tangent_runner
from ....src.lyapunov.reference import (
    CandidateAMetric, RenormalizedTangentDiagnostics, RenormalizedTangentResult,
    RenormalizedTangentSpec, _resolved_interval_max_step,
)

NATIVE_DIRECTORY = Path(__file__).with_name("native")
BUILD_FLAGS = ("-O2", "-ffp-contract=on", "-fPIC", "-shared")
_double_ptr = types.CPointer(types.float64)
_int_ptr = types.CPointer(types.int32)


@cfunc(types.void(types.int32, types.float64, _double_ptr, _double_ptr,
                  _double_ptr, _int_ptr), cache=False)
def _rhs(n, time, state, output, parameters, error):
    y = carray(state, 8)
    p = carray(parameters, 5)
    result = compiled_reference_and_tangent_rhs(time, y, p[0], p[1], p[2], p[3], p[4])
    for j in range(8):
        output[j] = result[j]


@cfunc(types.int32(_double_ptr, types.float64, _double_ptr, _double_ptr), cache=False)
def _reset(state, tc, stretch_out, norm_error_out):
    y = carray(state, 8)
    scaled = np.empty(4)
    for j in range(4):
        scaled[j] = y[j+4] * (1.0 if j < 2 else tc)
    # NumPy's 1-D norm uses sqrt(dot); retain that reduction here.
    stretch = np.sqrt(np.dot(scaled, scaled))
    if not np.isfinite(stretch) or stretch <= 0:
        return 1
    for j in range(4):
        y[j+4] = (scaled[j]/stretch) * (1.0 if j < 2 else 1.0/tc)
    # CandidateAMetric.tangent_norm uses norm(..., axis=-1), a sum reduction.
    norm_squared = 0.0
    for j in range(4):
        value = y[j+4] * (1.0 if j < 2 else tc)
        norm_squared += value*value
    norm_error_out[0] = abs(np.sqrt(norm_squared)-1.0)
    stretch_out[0] = stretch
    for j in range(2):
        angle = (y[j]+np.pi) % (2.0*np.pi)-np.pi
        y[j] = np.pi if angle == -np.pi else angle
    return 0


@lru_cache(maxsize=1)
def native_library():
    """Compile once per process; return a handle retaining its temp directory."""
    directory = tempfile.TemporaryDirectory(prefix="s1-compiled-loop-")
    library_path = Path(directory.name)/"s1_loop.so"
    command = ["clang", *BUILD_FLAGS, str(NATIVE_DIRECTORY/"dop.c"),
               str(NATIVE_DIRECTORY/"loop.c"), "-o", str(library_path)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    library = ctypes.CDLL(str(library_path))
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
    library.s1_loop.argtypes = [ctypes.c_void_p, ctypes.c_void_p, pointer,
        pointer, pointer, ctypes.c_int, ctypes.c_double, ctypes.c_double,
        ctypes.c_double, ctypes.c_double, pointer, pointer]
    library.s1_loop.restype = ctypes.c_int
    library._temporary_directory = directory
    return library


def run_compiled_loop(spec: RenormalizedTangentSpec) -> RenormalizedTangentResult:
    """Run one cell; reject fast-path failures without any fallback or routing."""
    if spec.solver.method.upper() != "DOP853":
        raise ValueError("S1 requires DOP853.")
    metric = CandidateAMetric(spec.characteristic_length, spec.parameters.gravity)
    initial = np.asarray(spec.initial_tangent, dtype=float)
    initial_unit = initial / float(metric.tangent_norm(initial))
    state = np.concatenate((spec.initial_state.as_array(), initial_unit))
    p = spec.parameters
    parameters = np.array([p.length1, p.length2, p.mass1, p.mass2, p.gravity])
    cycles = int(round(spec.duration/spec.renormalization_interval))
    boundaries = np.linspace(0.0, spec.duration, cycles+1)
    maxstep = _resolved_interval_max_step(spec.solver, spec.characteristic_length,
                                        p.gravity, spec.renormalization_interval)
    output = np.empty((cycles, 4))
    stats = np.zeros(4)
    code = native_library().s1_loop(_rhs.address, _reset.address, state, parameters,
        boundaries, cycles, spec.solver.rtol, spec.solver.atol, maxstep,
        metric.characteristic_time, output, stats)
    if code == 40:
        raise RuntimeError("compiled DOP853 exceeded the declared max_step: "
                           f"{stats[2]} > {maxstep}.")
    if code:
        raise RuntimeError(f"S1 native loop failed with status {code}.")
    issues = []
    if stats[0] > spec.energy_drift_limit:
        issues.append("reference energy drift exceeded its declared limit")
    if stats[1] > spec.renormalization_norm_tolerance:
        issues.append("post-renormalization Candidate-A norm error exceeded its limit")
    diagnostics = RenormalizedTangentDiagnostics(
        float(stats[0]), float(stats[1]), maxstep, cycles, int(stats[3]),
        not issues, tuple(issues))
    return RenormalizedTangentResult(spec, metric, initial_unit, boundaries[1:],
        output[:, 0].copy(), output[:, 1].copy(), output[:, 2].copy(),
        output[:, 3].copy(), state[:4].copy(), state[4:].copy(), diagnostics)


def evaluate_compiled_loop(spec: RenormalizedTangentSpec):
    """Use the same neutral result adapter as the operational fast evaluator."""
    return evaluate_renormalized_tangent_runner(
        spec, runner=run_compiled_loop, evaluator="experimental_s1_compiled_loop")
