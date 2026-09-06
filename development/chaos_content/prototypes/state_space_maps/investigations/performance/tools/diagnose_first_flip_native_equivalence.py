"""Bounded causal diagnosis of native first-flip equivalence blockers."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.integrate._ivp.rk import DOP853
from scipy.optimize import brentq

from ....src.first_flip.compiled import compiled_rhs, first_flip_time_compiled
from ....src.first_flip.field_adapter import FirstFlipFieldSpec, run_periodic_first_flip_field
from ....src.first_flip.native_artifacts import (
    FIRST_FLIP_NATIVE_LOOP_SOURCE,
    S1_BUILD_FLAGS,
    S1_NATIVE_DIRECTORY,
    _corrected_dop_source,
)
from ....src.first_flip.native_runtime import _native_rhs_callback
from ....src.first_flip.reference import EVENT_IDENTITIES, _event_functions, first_flip_time
from ....src.generation import read_authoritative_field
from ....src.lyapunov.reference import EulerLagrangeState


PERFORMANCE = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PERFORMANCE / "evidence/current/first_flip_native_dop853_equivalence.json"
EPS4 = 4.0 * np.finfo(float).eps
_HAIRER_LAST_STEP = "if ((*x + (1.01 * h) - *xend) * posneg > 0.0)"
_STRICT_LAST_STEP = "if ((*x + h - *xend) * posneg >= 0.0)"
_REJECTION_DEFECT = "hnew = h / fmin(facc1, facc1 / safe);"
_REJECTION_CORRECTION = "hnew = h / fmin(facc1, fac11 / safe);"


def _instrumented_loop_source() -> str:
    source = FIRST_FLIP_NATIVE_LOOP_SOURCE.read_text()
    source = source.replace("#define CONTEXT_SIZE 32", "#define CONTEXT_SIZE 40")
    source = source.replace(
        "    ROOT_ITERATIONS = 25\n",
        "    ROOT_ITERATIONS = 25,\n"
        "    LAST_STEP_START = 26,\n    LAST_STEP_END = 27,\n"
        "    EVENT_BRACKET_START = 28,\n    EVENT_BRACKET_END = 29,\n"
        "    EVENT_BRACKET_START_STATE = 30,\n    EVENT_BRACKET_END_STATE = 34\n",
    )
    source = source.replace(
        "    if (nr == 1) return;\n\n",
        "    if (nr == 1) return;\n\n"
        "    p[LAST_STEP_START] = old;\n    p[LAST_STEP_END] = time;\n\n",
    )
    source = source.replace(
        "    double root_state[STATE_SIZE];\n",
        "    p[EVENT_BRACKET_START] = old;\n"
        "    p[EVENT_BRACKET_END] = time;\n"
        "    dense_state(old, con, nd, old, time - old, &p[EVENT_BRACKET_START_STATE]);\n"
        "    for (int index = 0; index < STATE_SIZE; index++) {\n"
        "        p[EVENT_BRACKET_END_STATE + index] = state[index];\n"
        "    }\n\n    double root_state[STATE_SIZE];\n",
    )
    source = source.replace(
        "    stats[14] = (double)iwork[19];\n",
        "    stats[14] = (double)iwork[19];\n"
        "    stats[15] = context[LAST_STEP_START];\n"
        "    stats[16] = context[LAST_STEP_END];\n"
        "    stats[17] = context[EVENT_BRACKET_START];\n"
        "    stats[18] = context[EVENT_BRACKET_END];\n"
        "    for (int index = 0; index < STATE_SIZE; index++) {\n"
        "        stats[19 + index] = context[EVENT_BRACKET_START_STATE + index];\n"
        "        stats[23 + index] = context[EVENT_BRACKET_END_STATE + index];\n"
        "    }\n",
    )
    return source


class NativeVariant:
    def __init__(self, root: Path, *, strict_final_step: bool, scipy_controller: bool = False, rejection_fix: bool = False):
        label = "fixed-equivalent" if rejection_fix and scipy_controller else "fixed-original" if rejection_fix else "scipy-equivalent" if scipy_controller else "strict" if strict_final_step else "baseline"
        self.directory = root / label
        self.directory.mkdir()
        dop = _corrected_dop_source()
        if strict_final_step:
            if dop.count(_HAIRER_LAST_STEP) != 1:
                raise RuntimeError("reviewed Hairer final-step condition not found")
            dop = dop.replace(_HAIRER_LAST_STEP, _STRICT_LAST_STEP)
        if rejection_fix:
            if dop.count(_REJECTION_DEFECT) != 1:
                raise RuntimeError("reviewed DOP853 rejection defect not found")
            dop = dop.replace(_REJECTION_DEFECT, _REJECTION_CORRECTION)
        (self.directory / "dop.c").write_text(dop)
        loop_source = _instrumented_loop_source()
        if scipy_controller:
            # Hairer stores the minimum shrink and maximum growth factors
            # directly; SciPy's RungeKutta constants are 0.2 and 10.
            loop_source = loop_source.replace("work[2] = 0.3;", "work[2] = 0.2;")
            loop_source = loop_source.replace("work[3] = 6.0;", "work[3] = 10.0;")
        loop = self.directory / "loop.c"
        loop.write_text(loop_source)
        library_path = self.directory / "loop.so"
        compiler = shutil.which("clang")
        if compiler is None:
            raise RuntimeError("clang unavailable")
        subprocess.run(
            [compiler, *S1_BUILD_FLAGS, "-I", str(self.directory), "-I", str(S1_NATIVE_DIRECTORY), str(loop), "-o", str(library_path)],
            check=True, capture_output=True, text=True,
        )
        self.library = ctypes.CDLL(str(library_path))
        pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
        self.library.first_flip_loop.argtypes = [ctypes.c_void_p, pointer, pointer, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double, pointer]
        self.library.first_flip_loop.restype = ctypes.c_int
        self.source_sha256 = hashlib.sha256(dop.encode()).hexdigest()

    def run(self, theta1: float, theta2: float, spec: FirstFlipFieldSpec) -> dict[str, object]:
        state = np.ascontiguousarray([theta1, theta2, 0.0, 0.0], dtype=np.float64)
        parameters = np.ascontiguousarray([1.0, 1.0, 1.0, 1.0, 9.81], dtype=np.float64)
        stats = np.zeros(27, dtype=np.float64)
        code = int(self.library.first_flip_loop(_native_rhs_callback().address, state, parameters, 5.0, spec.solver.rtol, spec.solver.atol, spec.solver.max_step, stats))
        observed = bool(round(stats[0]))
        return {
            "code": code, "observed": observed,
            "event_index": int(round(stats[1])) if observed else None,
            "event_time": float(stats[2]) if observed else None,
            "event_state": state.tolist() if observed else None,
            "maximum_step": float(stats[8]), "rhs_evaluations": int(round(stats[6])),
            "maximum_absolute_energy_error": float(stats[3]),
            "maximum_normalized_energy_drift": float(stats[4]),
            "maximum_angular_increment": float(stats[5]),
            "accepted_steps": int(round(stats[13])), "rejected_steps": int(round(stats[14])),
            "last_step_start": float(stats[15]), "last_step_end": float(stats[16]),
            "event_bracket_start": float(stats[17]) if observed else None,
            "event_bracket_end": float(stats[18]) if observed else None,
            "event_bracket_start_state": stats[19:23].tolist() if observed else None,
            "event_bracket_end_state": stats[23:27].tolist() if observed else None,
            "root_iterations": int(round(stats[10])),
        }


def _scipy_trace(state: EulerLagrangeState, rhs, spec: FirstFlipFieldSpec) -> dict[str, object]:
    y0 = state.as_array()
    events = _event_functions(y0)
    solver = DOP853(rhs, 0.0, y0, 5.0, rtol=spec.solver.rtol, atol=spec.solver.atol, max_step=spec.solver.max_step)
    surfaces = np.asarray([event(0.0, y0) for event in events])
    steps = []
    event_record = None
    while solver.status == "running":
        start = float(solver.t)
        start_state = solver.y.copy()
        solver.step()
        end = float(solver.t)
        end_state = solver.y.copy()
        dense = solver.dense_output()
        new_surfaces = np.asarray([event(end, end_state) for event in events])
        active = np.nonzero((surfaces <= 0.0) & (new_surfaces >= 0.0))[0]
        steps.append(end - start)
        if len(active):
            candidates = []
            for index in active:
                calls = [0]
                def surface(time):
                    calls[0] += 1
                    return events[index](time, dense(time))
                root = brentq(surface, start, end, xtol=EPS4, rtol=EPS4)
                candidates.append((root, int(index), calls[0]))
            root, index, calls = min(candidates)
            event_record = {
                "time": float(root), "event_index": index,
                "state": np.asarray(dense(root)).tolist(),
                "bracket_start": start, "bracket_end": end, "step_size": end - start,
                "bracket_start_state": start_state.tolist(), "bracket_end_state": end_state.tolist(),
                "bracket_surface_start": float(surfaces[index]),
                "bracket_surface_end": float(new_surfaces[index]),
                "root_function_calls": calls,
            }
            break
        surfaces = new_surfaces
    return {
        "observed": event_record is not None, "event": event_record,
        "last_step_start": start, "last_step_end": end,
        "last_step_size": end - start, "maximum_step": max(steps),
        "rhs_evaluations": int(solver.nfev), "accepted_steps": len(steps),
    }


def _result_record(result) -> dict[str, object]:
    return {
        "status": result.status.value,
        "event_time": result.event_time_seconds,
        "event_identities": [item.label for item in result.event_identities],
        "event_state": result.event_state,
        "triggering_residual": max((abs(item.residual) for item in result.event_surface_residuals if item.identity in result.event_identities), default=0.0),
        "normalized_energy_drift": result.maximum_normalized_energy_drift,
        "maximum_angular_increment": result.maximum_accepted_angular_increment,
        "rhs_evaluations": result.rhs_evaluations,
    }


def _aligned_scipy_comparison(state, rhs, native, spec):
    if not native["observed"]:
        return None
    end = float(native["event_bracket_end"])
    solution = solve_ivp(
        rhs, (0.0, end), state.as_array(), method="DOP853",
        rtol=spec.solver.rtol, atol=spec.solver.atol,
        max_step=spec.solver.max_step, dense_output=True,
    )
    times = np.asarray([
        native["event_bracket_start"], native["event_time"],
        native["event_bracket_end"],
    ])
    states = np.asarray(solution.sol(times)).T
    native_states = np.asarray([
        native["event_bracket_start_state"], native["event_state"],
        native["event_bracket_end_state"],
    ])
    identity = EVENT_IDENTITIES[int(native["event_index"])]
    event = _event_functions(state.as_array())[int(native["event_index"])]
    scipy_root = brentq(
        lambda time: event(time, solution.sol(time)),
        float(native["event_bracket_start"]),
        float(native["event_bracket_end"]), xtol=EPS4, rtol=EPS4,
    )
    return {
        "event_identity": identity.label,
        "maximum_aligned_state_difference_at_start_event_end": float(np.max(np.abs(states - native_states))),
        "aligned_state_component_differences": np.max(np.abs(states - native_states), axis=1).tolist(),
        "scipy_surface_at_native_event_time": float(event(float(native["event_time"]), states[1])),
        "scipy_root_in_native_bracket": float(scipy_root),
        "native_minus_scipy_bracket_root": float(native["event_time"] - scipy_root),
    }


def run() -> dict[str, object]:
    spec = FirstFlipFieldSpec()
    with tempfile.TemporaryDirectory(prefix="first-flip-equivalence-") as name:
        root = Path(name)
        compiled_path = root / "compiled.h5"
        field_run = run_periodic_first_flip_field(compiled_path, 64, mode="create", spec=spec, force_compiled=True)
        compiled_field = read_authoritative_field(compiled_path)
        baseline = NativeVariant(root, strict_final_step=False)
        strict = NativeVariant(root, strict_final_step=True)
        equivalent = NativeVariant(root, strict_final_step=True, scipy_controller=True)
        fixed_original = NativeVariant(root, strict_final_step=True, rejection_fix=True)
        fixed_equivalent = NativeVariant(root, strict_final_step=True, scipy_controller=True, rejection_fix=True)
        rows = []
        for j, theta2 in enumerate(compiled_field.theta2_axis):
            for i, theta1 in enumerate(compiled_field.theta1_axis):
                base = baseline.run(float(theta1), float(theta2), spec)
                fixed = strict.run(float(theta1), float(theta2), spec)
                aligned = equivalent.run(float(theta1), float(theta2), spec)
                repaired = fixed_original.run(float(theta1), float(theta2), spec)
                repaired_equivalent = fixed_equivalent.run(float(theta1), float(theta2), spec)
                compiled_value = float(compiled_field.values[j, i])
                cap = spec.dimensionless_observation_horizon
                base_value = base["event_time"] / spec.gravity_timescale_seconds if base["observed"] else cap
                fixed_value = fixed["event_time"] / spec.gravity_timescale_seconds if fixed["observed"] else cap
                aligned_value = aligned["event_time"] / spec.gravity_timescale_seconds if aligned["observed"] else cap
                repaired_value = repaired["event_time"] / spec.gravity_timescale_seconds if repaired["observed"] else cap
                repaired_equivalent_value = repaired_equivalent["event_time"] / spec.gravity_timescale_seconds if repaired_equivalent["observed"] else cap
                rows.append({
                    "theta1_index": i, "theta2_index": j,
                    "theta1": float(theta1), "theta2": float(theta2),
                    "compiled_value": compiled_value, "baseline": base, "strict": fixed, "equivalent": aligned,
                    "fixed_original": repaired, "fixed_equivalent": repaired_equivalent,
                    "baseline_difference_seconds": abs(base_value - compiled_value) * spec.gravity_timescale_seconds,
                    "strict_difference_seconds": abs(fixed_value - compiled_value) * spec.gravity_timescale_seconds,
                    "equivalent_difference_seconds": abs(aligned_value - compiled_value) * spec.gravity_timescale_seconds,
                    "fixed_original_difference_seconds": abs(repaired_value - compiled_value) * spec.gravity_timescale_seconds,
                    "fixed_equivalent_difference_seconds": abs(repaired_equivalent_value - compiled_value) * spec.gravity_timescale_seconds,
                })
        recoveries = [row for row in rows if row["baseline"]["maximum_step"] > spec.solver.max_step + 64*np.finfo(float).eps]
        observed_recoveries = sum(bool(row["baseline"]["observed"]) for row in recoveries)
        ordered = sorted((row for row in rows if row["baseline"]["observed"]), key=lambda row: row["baseline_difference_seconds"], reverse=True)
        selected = ordered[:5]
        passing_observed = next(row for row in reversed(ordered) if row["baseline_difference_seconds"] < 1e-10)
        passing_censored = next(row for row in rows if not row["baseline"]["observed"] and row not in recoveries)
        recovery_examples = recoveries[:5]
        scipy_recovery_traces = [
            _scipy_trace(
                EulerLagrangeState(row["theta1"], row["theta2"], 0.0, 0.0),
                compiled_rhs(spec.parameters), spec,
            )
            for row in recoveries
        ]
        details = []
        for category, row in [("near_worst", item) for item in selected] + [("passing_observed", passing_observed), ("passing_censored", passing_censored)] + [("max_step_recovery", item) for item in recovery_examples]:
            state = EulerLagrangeState(row["theta1"], row["theta2"], 0.0, 0.0)
            compiled_result = first_flip_time_compiled(state, spec.parameters, spec.solver, 5.0)
            trusted_result = first_flip_time(state, spec.parameters, spec.solver, 5.0)
            details.append({
                "category": category,
                "theta1_index": row["theta1_index"], "theta2_index": row["theta2_index"],
                "theta1": row["theta1"], "theta2": row["theta2"],
                "baseline_native": row["baseline"], "strict_native": row["strict"], "scipy_equivalent_native": row["equivalent"],
                "rejection_fixed_native": row["fixed_original"], "fully_equivalent_native": row["fixed_equivalent"],
                "compiled": _result_record(compiled_result), "trusted": _result_record(trusted_result),
                "compiled_trace": _scipy_trace(state, compiled_rhs(spec.parameters), spec),
                "trusted_trace": _scipy_trace(state, lambda t, y: __import__("development.chaos_content.prototypes.state_space_maps.src.first_flip.reference", fromlist=["_cached_dynamics"])._cached_dynamics(spec.parameters).flow(t, y), spec),
                "compiled_aligned_to_native_bracket": _aligned_scipy_comparison(state, compiled_rhs(spec.parameters), row["baseline"], spec),
                "native_compiled_time_difference": row["baseline_difference_seconds"],
                "strict_native_compiled_time_difference": row["strict_difference_seconds"],
                "equivalent_native_compiled_time_difference": row["equivalent_difference_seconds"],
                "rejection_fixed_native_compiled_time_difference": row["fixed_original_difference_seconds"],
                "fully_equivalent_native_compiled_time_difference": row["fixed_equivalent_difference_seconds"],
                "compiled_trusted_time_difference": abs((compiled_result.event_time_seconds or 5.0) - (trusted_result.event_time_seconds or 5.0)),
            })
        repeat_case = recoveries[0]
        repeats = [baseline.run(repeat_case["theta1"], repeat_case["theta2"], spec) for _ in range(5)]
        return {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "environment": {"python": platform.python_version(), "platform": platform.platform()},
            "specification": {"samples_per_axis": 64, "horizon": 5.0, "max_step": spec.solver.max_step, "rtol": spec.solver.rtol, "atol": spec.solver.atol},
            "compiled_field_run": {"all_workers_stopped": field_run.all_workers_stopped, "validation": asdict(field_run.validation)},
            "vendored_last_step_condition": _HAIRER_LAST_STEP,
            "strict_experiment_condition": _STRICT_LAST_STEP,
            "baseline_dop_sha256": baseline.source_sha256, "strict_dop_sha256": strict.source_sha256,
            "equivalent_dop_sha256": equivalent.source_sha256,
            "rejection_fixed_dop_sha256": fixed_original.source_sha256,
            "fully_equivalent_dop_sha256": fixed_equivalent.source_sha256,
            "summary": {
                "cell_count": len(rows), "max_step_recovery_count": len(recoveries),
                "max_step_recovery_observed_count": observed_recoveries,
                "max_step_recovery_censored_count": len(recoveries) - observed_recoveries,
                "maximum_excess_absolute": max(row["baseline"]["maximum_step"] - spec.solver.max_step for row in recoveries),
                "maximum_excess_relative": max(row["baseline"]["maximum_step"] / spec.solver.max_step - 1.0 for row in recoveries),
                "scipy_recovery_maximum_step": max(item["maximum_step"] for item in scipy_recovery_traces),
                "scipy_recovery_max_step_violation_count": int(sum(item["maximum_step"] > spec.solver.max_step + 64*np.finfo(float).eps for item in scipy_recovery_traces)),
                "scipy_recovery_final_step_minimum": min(item["last_step_size"] for item in scipy_recovery_traces),
                "scipy_recovery_final_step_maximum": max(item["last_step_size"] for item in scipy_recovery_traces),
                "baseline_maximum_event_time_difference": ordered[0]["baseline_difference_seconds"],
                "strict_maximum_event_time_difference": max(row["strict_difference_seconds"] for row in rows if row["strict"]["observed"]),
                "equivalent_maximum_event_time_difference": max(row["equivalent_difference_seconds"] for row in rows if row["equivalent"]["observed"]),
                "rejection_fixed_maximum_event_time_difference": max(row["fixed_original_difference_seconds"] for row in rows if row["fixed_original"]["observed"]),
                "fully_equivalent_maximum_event_time_difference": max(row["fixed_equivalent_difference_seconds"] for row in rows if row["fixed_equivalent"]["observed"]),
                "strict_max_step_violation_count": int(sum(row["strict"]["maximum_step"] > spec.solver.max_step + 64*np.finfo(float).eps for row in rows)),
                "baseline_classification_mismatch_count": int(sum(bool(row["baseline"]["observed"]) != (row["compiled_value"] < spec.dimensionless_observation_horizon) for row in rows)),
                "strict_classification_mismatch_count": int(sum(bool(row["strict"]["observed"]) != (row["compiled_value"] < spec.dimensionless_observation_horizon) for row in rows)),
                "equivalent_classification_mismatch_count": int(sum(bool(row["equivalent"]["observed"]) != (row["compiled_value"] < spec.dimensionless_observation_horizon) for row in rows)),
                "equivalent_max_step_violation_count": int(sum(row["equivalent"]["maximum_step"] > spec.solver.max_step + 64*np.finfo(float).eps for row in rows)),
                "rejection_fixed_max_step_violation_count": int(sum(row["fixed_original"]["maximum_step"] > spec.solver.max_step + 64*np.finfo(float).eps for row in rows)),
                "fully_equivalent_max_step_violation_count": int(sum(row["fixed_equivalent"]["maximum_step"] > spec.solver.max_step + 64*np.finfo(float).eps for row in rows)),
                "rejection_fixed_classification_mismatch_count": int(sum(bool(row["fixed_original"]["observed"]) != (row["compiled_value"] < spec.dimensionless_observation_horizon) for row in rows)),
                "fully_equivalent_classification_mismatch_count": int(sum(bool(row["fixed_equivalent"]["observed"]) != (row["compiled_value"] < spec.dimensionless_observation_horizon) for row in rows)),
                "selected_maximum_native_compiled_event_state_difference": max(
                    float(np.max(np.abs(np.asarray(item["baseline"]["event_state"]) - np.asarray(first_flip_time_compiled(EulerLagrangeState(item["theta1"], item["theta2"], 0.0, 0.0), spec.parameters, spec.solver, 5.0).event_state))))
                    for item in selected
                ),
            },
            "determinism_repeats": repeats,
            "selected_cases": details,
            "max_step_recoveries": [{key: row[key] for key in ("theta1_index", "theta2_index", "theta1", "theta2", "baseline_difference_seconds", "strict_difference_seconds", "baseline", "strict")} for row in recoveries],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace evidence: {args.output}")
    payload = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
