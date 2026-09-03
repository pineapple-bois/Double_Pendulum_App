"""Validate restart-grade QR-boundary continuation for EL and canonical flows."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import scipy


EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
EXPERIMENTS_ROOT = EXPERIMENT_ROOT.parent


def _load_module(name: str, relative_path: str) -> Any:
    path = EXPERIMENTS_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


experiment007 = _load_module(
    "experiment007_for_013",
    "007_full_matrix_qr_tangent_dynamics/full_matrix_qr_tangent_dynamics.py",
)
experiment011 = _load_module(
    "experiment011_for_013",
    "011_hamiltonian_canonical_spectrum_crosscheck/canonical_spectrum_crosscheck.py",
)
experiment006 = experiment007.experiment006


EXPERIMENT_NAME = "restart_grade_qr_continuation"
SCHEMA_NAME = "chaos_tangent_qr_boundary_restart"
SCHEMA_VERSION = 1
FORMULATIONS = ("euler_lagrange", "canonical_hamiltonian")
TOTAL_DURATION_SECONDS = 1.0
SPLIT_TIME_SECONDS = 0.5
QR_INTERVAL_SECONDS = 0.25
MAX_STEP_SECONDS = 0.0099773571
POLICY = experiment006.SIMPLE_REFERENCE_SOLVER_POLICY
EQUIVALENCE_ABSOLUTE_LIMIT = 1.0e-13
SERIALIZED_ARRAY_FILE = "restart_arrays.npz"
METADATA_FILE = "restart_metadata.json"
CHECKPOINT_MANIFEST_FILE = "restart_manifest.json"
TANGENT_CONVENTION = "fixed_columns_positive_r_diagonal_no_sort_v1"
METRIC_IDENTIFIERS = {
    "euler_lagrange": "candidate_a_scaled_el_S_v1",
    "canonical_hamiltonian": "candidate_a_pullback_A_of_z_v1",
}
STATE_ORDERS = {
    "euler_lagrange": ["theta1", "theta2", "omega1", "omega2"],
    "canonical_hamiltonian": ["theta1", "theta2", "p_theta1", "p_theta2"],
}
VALIDATION_INITIAL_CONDITION = {
    "id": "experiment_006_reference_anchor",
    "state_degrees": [179.0, 179.0, 0.0, 0.0],
    "state_radians": np.asarray(experiment006.BASE_STATE_RADIANS).tolist(),
    "role": "short infrastructure validation only",
}


class RestartStateError(ValueError):
    """Base class for malformed or incompatible restart checkpoints."""


class RestartCompatibilityError(RestartStateError):
    """Raised when a valid checkpoint does not match the requested run."""


@dataclass(frozen=True)
class QRBoundaryRestartState:
    metadata: dict[str, Any]
    reference_state: np.ndarray
    tangent_matrix_post_qr: np.ndarray
    cumulative_log_growth: np.ndarray
    provenance_warnings: tuple[str, ...] = ()


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_value(*arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def executed_source_paths(formulation: str) -> list[Path]:
    if formulation not in FORMULATIONS:
        raise RestartStateError(f"Unknown formulation: {formulation}")
    paths = [
        EXPERIMENTS_ROOT.parent
        / "foundations"
        / "006_variational_dynamics_validation/variational_dynamics_validation.py",
        EXPERIMENTS_ROOT
        / "007_full_matrix_qr_tangent_dynamics/full_matrix_qr_tangent_dynamics.py",
        Path(__file__).resolve(),
    ]
    if formulation == "canonical_hamiltonian":
        paths.append(
            EXPERIMENTS_ROOT
            / "011_hamiltonian_canonical_spectrum_crosscheck/canonical_spectrum_crosscheck.py"
        )
    return paths


def current_provenance(formulation: str) -> dict[str, Any]:
    commit = _git_value("rev-parse", "HEAD")
    status = _git_value("status", "--porcelain", "--untracked-files=all")
    return {
        "git": {
            "available": commit is not None and status is not None,
            "commit": commit,
            "dirty_working_tree": None if status is None else bool(status),
        },
        "runtime": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
        },
        "source_sha256": {
            str(path.relative_to(REPOSITORY_ROOT)): sha256_file(path)
            for path in executed_source_paths(formulation)
        },
    }


def _policy_dict(policy: Any) -> dict[str, Any]:
    return experiment006.policy_dict(policy)


def policy_from_metadata(metadata: Mapping[str, Any]) -> Any:
    return experiment006.SolverPolicy(**dict(metadata["solver_policy"]))


def validate_restart_state(state: QRBoundaryRestartState) -> None:
    metadata = state.metadata
    required = {
        "schema_name",
        "schema_version",
        "formulation",
        "physical_initial_condition",
        "solver_policy_name",
        "solver_policy",
        "max_step_seconds",
        "qr_interval_seconds",
        "elapsed_time_seconds",
        "completed_qr_cycle_count",
        "tangent_convention",
        "metric_convention",
        "diagnostic_energy_baseline_joules",
        "state_order",
        "angle_chart",
        "winding_state_required",
        "provenance",
        "array_file",
        "array_sha256",
        "array_shapes",
        "array_dtypes",
        "array_previews",
    }
    missing = required - set(metadata)
    if missing:
        raise RestartStateError(f"Restart metadata is missing fields: {sorted(missing)}")
    if metadata["schema_name"] != SCHEMA_NAME or metadata["schema_version"] != SCHEMA_VERSION:
        raise RestartCompatibilityError("Restart schema name/version is incompatible.")
    formulation = metadata["formulation"]
    if formulation not in FORMULATIONS:
        raise RestartStateError(f"Unknown formulation: {formulation}")
    arrays = {
        "reference_state": np.asarray(state.reference_state),
        "tangent_matrix_post_qr": np.asarray(state.tangent_matrix_post_qr),
        "cumulative_log_growth": np.asarray(state.cumulative_log_growth),
    }
    expected_shapes = {
        "reference_state": (4,),
        "tangent_matrix_post_qr": (4, 4),
        "cumulative_log_growth": (4,),
    }
    for name, array in arrays.items():
        if array.shape != expected_shapes[name]:
            raise RestartStateError(
                f"{name} has shape {array.shape}; expected {expected_shapes[name]}."
            )
        if array.dtype != np.dtype("float64"):
            raise RestartStateError(f"{name} must have float64 dtype.")
        if not np.all(np.isfinite(array)):
            raise RestartStateError(f"{name} must contain only finite values.")
        if metadata["array_shapes"][name] != list(expected_shapes[name]):
            raise RestartStateError(f"Recorded shape for {name} is inconsistent.")
        if metadata["array_dtypes"][name] != "float64":
            raise RestartStateError(f"Recorded dtype for {name} is inconsistent.")
        preview = np.asarray(metadata["array_previews"][name], dtype=np.float64)
        if not np.array_equal(preview, array):
            raise RestartStateError(f"Human-auditable preview for {name} changed.")
    elapsed = float(metadata["elapsed_time_seconds"])
    interval = float(metadata["qr_interval_seconds"])
    cycles = metadata["completed_qr_cycle_count"]
    if not isinstance(cycles, int) or cycles < 0:
        raise RestartStateError("Completed QR cycle count must be nonnegative.")
    if not math.isclose(cycles * interval, elapsed, rel_tol=0.0, abs_tol=1.0e-13):
        raise RestartStateError("Elapsed time and cycle count are not one QR boundary.")
    if metadata["state_order"] != STATE_ORDERS[formulation]:
        raise RestartCompatibilityError("State ordering convention changed.")
    if metadata["tangent_convention"] != TANGENT_CONVENTION:
        raise RestartCompatibilityError("Tangent ordering/sign convention changed.")
    if metadata["metric_convention"] != METRIC_IDENTIFIERS[formulation]:
        raise RestartCompatibilityError("QR metric convention changed.")
    if metadata["winding_state_required"] is not False:
        raise RestartCompatibilityError("Unexpected winding state is required.")
    if not np.isfinite(float(metadata["diagnostic_energy_baseline_joules"])):
        raise RestartStateError("Diagnostic energy baseline must be finite.")


def restart_state_from_run(
    run: Mapping[str, Any],
    *,
    formulation: str,
    physical_initial_condition: Mapping[str, Any],
    policy_name: str,
) -> QRBoundaryRestartState:
    reference = np.asarray(run["_terminal_reference_state"], dtype=np.float64)
    tangent = np.asarray(
        run["_terminal_tangent_matrix_post_qr"], dtype=np.float64
    )
    cumulative = np.asarray(run["final_cumulative_log_growth"], dtype=np.float64)
    arrays = {
        "reference_state": reference,
        "tangent_matrix_post_qr": tangent,
        "cumulative_log_growth": cumulative,
    }
    metadata = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "experiment": EXPERIMENT_NAME,
        "source_run_id": run["run_id"],
        "formulation": formulation,
        "physical_initial_condition": dict(physical_initial_condition),
        "solver_policy_name": policy_name,
        "solver_policy": dict(run["solver_policy"]),
        "max_step_seconds": float(run["max_step_seconds"]),
        "qr_interval_seconds": float(run["qr_interval_seconds"]),
        "elapsed_time_seconds": float(run["elapsed_time_seconds"]),
        "completed_qr_cycle_count": int(run["cycle_count"]),
        "tangent_convention": TANGENT_CONVENTION,
        "metric_convention": METRIC_IDENTIFIERS[formulation],
        "diagnostic_energy_baseline_joules": float(
            run["diagnostic_energy_baseline_joules"]
        ),
        "state_order": STATE_ORDERS[formulation],
        "angle_chart": "locally canonical (-pi, pi]; no winding state",
        "winding_state_required": False,
        "provenance": current_provenance(formulation),
        "array_file": SERIALIZED_ARRAY_FILE,
        "array_sha256": None,
        "array_shapes": {name: list(value.shape) for name, value in arrays.items()},
        "array_dtypes": {name: str(value.dtype) for name, value in arrays.items()},
        "array_previews": {name: value.tolist() for name, value in arrays.items()},
    }
    state = QRBoundaryRestartState(metadata, reference, tangent, cumulative)
    validate_restart_state(state)
    return state


def save_restart_checkpoint(path: Path, state: QRBoundaryRestartState) -> None:
    validate_restart_state(state)
    path.mkdir(parents=True, exist_ok=True)
    array_path = path / SERIALIZED_ARRAY_FILE
    np.savez(
        array_path,
        reference_state=state.reference_state,
        tangent_matrix_post_qr=state.tangent_matrix_post_qr,
        cumulative_log_growth=state.cumulative_log_growth,
    )
    metadata = dict(state.metadata)
    metadata["array_sha256"] = sha256_file(array_path)
    metadata_path = path / METADATA_FILE
    write_json(metadata_path, metadata)
    write_json(
        path / CHECKPOINT_MANIFEST_FILE,
        {
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "files": {
                METADATA_FILE: {
                    "bytes": metadata_path.stat().st_size,
                    "sha256": sha256_file(metadata_path),
                },
                SERIALIZED_ARRAY_FILE: {
                    "bytes": array_path.stat().st_size,
                    "sha256": sha256_file(array_path),
                },
            },
        },
    )


def _provenance_mismatches(
    saved: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    mismatches: list[str] = []
    if saved.get("runtime") != current.get("runtime"):
        mismatches.append("runtime versions differ")
    if saved.get("source_sha256") != current.get("source_sha256"):
        mismatches.append("executed source-file hashes differ")
    if saved.get("git") != current.get("git"):
        mismatches.append("Git commit/dirty-worktree provenance differs")
    return mismatches


def load_restart_checkpoint(
    path: Path,
    *,
    expected_formulation: str | None = None,
    expected_policy: Any | None = None,
    expected_max_step: float | None = None,
    expected_qr_interval: float | None = None,
    allow_provenance_mismatch: bool = False,
) -> QRBoundaryRestartState:
    manifest = json.loads((path / CHECKPOINT_MANIFEST_FILE).read_text(encoding="utf-8"))
    if manifest.get("schema_name") != SCHEMA_NAME or manifest.get("schema_version") != SCHEMA_VERSION:
        raise RestartCompatibilityError("Checkpoint manifest schema is incompatible.")
    for name, record in manifest["files"].items():
        file_path = path / name
        if file_path.stat().st_size != record["bytes"] or sha256_file(file_path) != record["sha256"]:
            raise RestartStateError(f"Checkpoint file integrity failed: {name}")
    metadata = json.loads((path / METADATA_FILE).read_text(encoding="utf-8"))
    if metadata["array_sha256"] != sha256_file(path / SERIALIZED_ARRAY_FILE):
        raise RestartStateError("Restart array SHA-256 does not match metadata.")
    with np.load(path / SERIALIZED_ARRAY_FILE, allow_pickle=False) as arrays:
        required_arrays = {
            "reference_state",
            "tangent_matrix_post_qr",
            "cumulative_log_growth",
        }
        if set(arrays.files) != required_arrays:
            raise RestartStateError("Restart array bundle is incomplete or contains extras.")
        state = QRBoundaryRestartState(
            metadata=metadata,
            reference_state=np.array(arrays["reference_state"], copy=True),
            tangent_matrix_post_qr=np.array(
                arrays["tangent_matrix_post_qr"], copy=True
            ),
            cumulative_log_growth=np.array(
                arrays["cumulative_log_growth"], copy=True
            ),
        )
    validate_restart_state(state)
    if expected_formulation is not None and metadata["formulation"] != expected_formulation:
        raise RestartCompatibilityError("Restart formulation does not match request.")
    if expected_policy is not None and metadata["solver_policy"] != _policy_dict(expected_policy):
        raise RestartCompatibilityError("Restart solver policy does not match request.")
    if expected_max_step is not None and metadata["max_step_seconds"] != expected_max_step:
        raise RestartCompatibilityError("Restart max_step does not match request.")
    if expected_qr_interval is not None and metadata["qr_interval_seconds"] != expected_qr_interval:
        raise RestartCompatibilityError("Restart QR interval does not match request.")
    mismatches = _provenance_mismatches(
        metadata["provenance"], current_provenance(metadata["formulation"])
    )
    if mismatches and not allow_provenance_mismatch:
        raise RestartCompatibilityError(
            "Restart provenance mismatch: " + "; ".join(mismatches)
        )
    return replace(state, provenance_warnings=tuple(mismatches))


def resume_from_restart(
    state: QRBoundaryRestartState,
    *,
    additional_duration_seconds: float,
    run_id: str,
) -> dict[str, Any]:
    validate_restart_state(state)
    metadata = state.metadata
    policy = policy_from_metadata(metadata)
    common = {
        "run_id": run_id,
        "duration": additional_duration_seconds,
        "qr_interval": float(metadata["qr_interval_seconds"]),
        "policy": policy,
        "max_step": float(metadata["max_step_seconds"]),
        "initial_tangent_matrix": state.tangent_matrix_post_qr,
        "initial_cumulative_log_growth": state.cumulative_log_growth,
        "start_time_seconds": float(metadata["elapsed_time_seconds"]),
        "completed_cycle_count": int(metadata["completed_qr_cycle_count"]),
        "diagnostic_energy_baseline": float(
            metadata["diagnostic_energy_baseline_joules"]
        ),
    }
    if metadata["formulation"] == "euler_lagrange":
        return experiment007.run_qr_primitive(
            experiment006.VariationalDynamics(),
            initial_reference=state.reference_state,
            **common,
        )
    return experiment011.run_canonical_qr_primitive(
        experiment011.CanonicalDynamics(),
        initial_canonical_reference=state.reference_state,
        **common,
    )


def _run_fresh(formulation: str, *, duration: float, run_id: str) -> dict[str, Any]:
    if formulation == "euler_lagrange":
        return experiment007.run_qr_primitive(
            experiment006.VariationalDynamics(),
            run_id=run_id,
            duration=duration,
            qr_interval=QR_INTERVAL_SECONDS,
            policy=POLICY,
            max_step=MAX_STEP_SECONDS,
            initial_reference=np.asarray(experiment006.BASE_STATE_RADIANS),
        )
    return experiment011.run_canonical_qr_primitive(
        experiment011.CanonicalDynamics(),
        run_id=run_id,
        duration=duration,
        qr_interval=QR_INTERVAL_SECONDS,
        policy=POLICY,
        max_step=MAX_STEP_SECONDS,
        initial_el_state=np.asarray(experiment006.BASE_STATE_RADIANS),
    )


def _maximum_absolute(left: Any, right: Any) -> float:
    return float(
        np.max(np.abs(np.asarray(left, dtype=float) - np.asarray(right, dtype=float)))
    )


def compare_split_run(
    uninterrupted: Mapping[str, Any],
    resumed: Mapping[str, Any],
    *,
    formulation: str,
    roundtrip_exact: bool,
) -> dict[str, Any]:
    spectrum_key = (
        "final_diagnostic_spectrum_per_second"
        if formulation == "euler_lagrange"
        else "final_diagnostic_vector_per_second"
    )
    errors = {
        "terminal_reference_maximum_absolute": _maximum_absolute(
            uninterrupted["_terminal_reference_state"],
            resumed["_terminal_reference_state"],
        ),
        "post_qr_tangent_maximum_absolute": _maximum_absolute(
            uninterrupted["_terminal_tangent_matrix_post_qr"],
            resumed["_terminal_tangent_matrix_post_qr"],
        ),
        "cumulative_log_maximum_absolute": _maximum_absolute(
            uninterrupted["final_cumulative_log_growth"],
            resumed["final_cumulative_log_growth"],
        ),
        "cumulative_spectrum_maximum_absolute_per_second": _maximum_absolute(
            uninterrupted[spectrum_key], resumed[spectrum_key]
        ),
    }
    if formulation == "euler_lagrange":
        energy_left = float(
            experiment006.simple_energy(uninterrupted["_terminal_reference_state"])
        )
        energy_right = float(
            experiment006.simple_energy(resumed["_terminal_reference_state"])
        )
    else:
        dynamics = experiment011.CanonicalDynamics()
        energy_left = dynamics.energy(uninterrupted["_terminal_reference_state"])
        energy_right = dynamics.energy(resumed["_terminal_reference_state"])
    errors["final_energy_absolute_joules"] = abs(energy_left - energy_right)

    split_cycle = int(round(SPLIT_TIME_SECONDS / QR_INTERVAL_SECONDS))
    uninterrupted_tail = [
        cycle for cycle in uninterrupted["cycles"] if cycle["cycle_index"] > split_cycle
    ]
    resumed_cycles = list(resumed["cycles"])
    if len(uninterrupted_tail) != len(resumed_cycles):
        raise AssertionError("Split comparison produced different tail cycle counts.")
    cycle_fields = (
        "reference_start",
        "reference_end",
        "tangent_matrix_start",
        "tangent_matrix_pre_qr",
        "tangent_matrix_post",
        "cycle_log_growth",
        "cumulative_log_growth",
    )
    cycle_errors = {
        field: max(
            _maximum_absolute(left[field], right[field])
            for left, right in zip(uninterrupted_tail, resumed_cycles)
        )
        for field in cycle_fields
    }
    checks = {
        "restart_roundtrip_exact": roundtrip_exact,
        "all_final_numeric_errors_within_limit": all(
            value <= EQUIVALENCE_ABSOLUTE_LIMIT for value in errors.values()
        ),
        "all_post_split_cycle_errors_within_limit": all(
            value <= EQUIVALENCE_ABSOLUTE_LIMIT for value in cycle_errors.values()
        ),
        "elapsed_time_exact": uninterrupted["elapsed_time_seconds"]
        == resumed["elapsed_time_seconds"]
        == TOTAL_DURATION_SECONDS,
        "cycle_count_exact": uninterrupted["cycle_count"]
        == resumed["cycle_count"]
        == int(round(TOTAL_DURATION_SECONDS / QR_INTERVAL_SECONDS)),
        "resumed_cycle_numbering_exact": [
            cycle["cycle_index"] for cycle in resumed_cycles
        ]
        == [split_cycle + 1, split_cycle + 2],
        "uninterrupted_numerically_valid": bool(uninterrupted["accepted"]),
        "resumed_numerically_valid": bool(resumed["accepted"]),
        "cumulative_bookkeeping_within_limit": max(
            float(uninterrupted["cumulative_bookkeeping_error"]),
            float(resumed["cumulative_bookkeeping_error"]),
        )
        <= experiment007.BOOKKEEPING_ERROR_LIMIT,
    }
    return {
        "formulation": formulation,
        "accepted": all(checks.values()),
        "absolute_limit": EQUIVALENCE_ABSOLUTE_LIMIT,
        "checks": checks,
        "final_errors": errors,
        "post_split_cycle_errors": cycle_errors,
        "uninterrupted_final_cumulative_log_growth": uninterrupted[
            "final_cumulative_log_growth"
        ],
        "resumed_final_cumulative_log_growth": resumed[
            "final_cumulative_log_growth"
        ],
        "uninterrupted_final_spectrum_per_second": uninterrupted[spectrum_key],
        "resumed_final_spectrum_per_second": resumed[spectrum_key],
        "uninterrupted_final_energy_joules": energy_left,
        "resumed_final_energy_joules": energy_right,
    }


def _roundtrip_is_exact(
    original: QRBoundaryRestartState, loaded: QRBoundaryRestartState
) -> bool:
    return bool(
        np.array_equal(original.reference_state, loaded.reference_state)
        and np.array_equal(
            original.tangent_matrix_post_qr, loaded.tangent_matrix_post_qr
        )
        and np.array_equal(
            original.cumulative_log_growth, loaded.cumulative_log_growth
        )
        and original.metadata["elapsed_time_seconds"]
        == loaded.metadata["elapsed_time_seconds"]
        and original.metadata["completed_qr_cycle_count"]
        == loaded.metadata["completed_qr_cycle_count"]
        and original.metadata["solver_policy"] == loaded.metadata["solver_policy"]
        and original.metadata["provenance"] == loaded.metadata["provenance"]
    )


def write_evidence_manifest(output_root: Path) -> None:
    manifest_path = output_root / "manifest.json"
    files = sorted(
        path for path in output_root.rglob("*") if path.is_file() and path != manifest_path
    )
    write_json(
        manifest_path,
        {
            "experiment": EXPERIMENT_NAME,
            "phase": "A_restart_infrastructure_validation",
            "files": [
                {
                    "path": str(path.relative_to(output_root)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in files
            ],
        },
    )


def run_phase_a(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    contract = {
        "experiment": EXPERIMENT_NAME,
        "phase": "A_restart_infrastructure_validation",
        "question": (
            "Can the validated EL and canonical tangent-QR calculations be "
            "serialized at a QR boundary and resumed so that a split run "
            "reproduces the uninterrupted run to numerical precision?"
        ),
        "initial_condition": VALIDATION_INITIAL_CONDITION,
        "solver_policy": _policy_dict(POLICY),
        "max_step_seconds": MAX_STEP_SECONDS,
        "qr_interval_seconds": QR_INTERVAL_SECONDS,
        "total_duration_seconds": TOTAL_DURATION_SECONDS,
        "split_time_seconds": SPLIT_TIME_SECONDS,
        "equivalence_absolute_limit": EQUIVALENCE_ABSOLUTE_LIMIT,
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "long_scientific_integration_performed": False,
    }
    write_json(output_root / "contract.json", contract)
    formulation_results: dict[str, Any] = {}
    for formulation in FORMULATIONS:
        uninterrupted = _run_fresh(
            formulation,
            duration=TOTAL_DURATION_SECONDS,
            run_id=f"phase_a_{formulation}_uninterrupted",
        )
        prefix = _run_fresh(
            formulation,
            duration=SPLIT_TIME_SECONDS,
            run_id=f"phase_a_{formulation}_prefix",
        )
        original_state = restart_state_from_run(
            prefix,
            formulation=formulation,
            physical_initial_condition=VALIDATION_INITIAL_CONDITION,
            policy_name="baseline",
        )
        checkpoint_path = output_root / formulation / "checkpoint_at_0.5s"
        save_restart_checkpoint(checkpoint_path, original_state)
        loaded_state = load_restart_checkpoint(
            checkpoint_path,
            expected_formulation=formulation,
            expected_policy=POLICY,
            expected_max_step=MAX_STEP_SECONDS,
            expected_qr_interval=QR_INTERVAL_SECONDS,
        )
        roundtrip_exact = _roundtrip_is_exact(original_state, loaded_state)
        resumed = resume_from_restart(
            loaded_state,
            additional_duration_seconds=TOTAL_DURATION_SECONDS - SPLIT_TIME_SECONDS,
            run_id=f"phase_a_{formulation}_resumed",
        )
        comparison = compare_split_run(
            uninterrupted,
            resumed,
            formulation=formulation,
            roundtrip_exact=roundtrip_exact,
        )
        write_json(output_root / formulation / "comparison.json", comparison)
        formulation_results[formulation] = comparison | {
            "checkpoint_path": str(checkpoint_path.relative_to(output_root)),
            "checkpoint_elapsed_time_seconds": loaded_state.metadata[
                "elapsed_time_seconds"
            ],
            "checkpoint_completed_qr_cycles": loaded_state.metadata[
                "completed_qr_cycle_count"
            ],
            "checkpoint_provenance": loaded_state.metadata["provenance"],
            "checkpoint_provenance_warnings": loaded_state.provenance_warnings,
        }
    accepted = all(item["accepted"] for item in formulation_results.values())
    summary = {
        "experiment": EXPERIMENT_NAME,
        "phase": "A_restart_infrastructure_validation",
        "accepted": accepted,
        "verdict": (
            "accepted_restart_grade_qr_boundary_continuation"
            if accepted
            else "rejected_or_unresolved_restart_continuation"
        ),
        "contract": contract,
        "formulations": formulation_results,
        "claim_boundary": (
            "Short-run QR-boundary serialization and continuation only; no "
            "long-time Lyapunov convergence or Experiment 012 settling claim."
        ),
    }
    write_json(output_root / "summary.json", summary)
    write_evidence_manifest(output_root)
    return summary


def verify_phase_a_evidence(output_root: Path, summary: Mapping[str, Any]) -> None:
    if not summary["accepted"]:
        raise AssertionError("Experiment 013 Phase A did not meet its frozen checks.")
    for formulation in FORMULATIONS:
        checkpoint = output_root / formulation / "checkpoint_at_0.5s"
        load_restart_checkpoint(
            checkpoint,
            expected_formulation=formulation,
            expected_policy=POLICY,
            expected_max_step=MAX_STEP_SECONDS,
            expected_qr_interval=QR_INTERVAL_SECONDS,
        )
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    for record in manifest["files"]:
        path = output_root / record["path"]
        if path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
            raise AssertionError(f"Evidence hash mismatch: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "development/chaos_content/experiments/outputs/013/phase_a"
        ),
    )
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_phase_a(args.output_dir)
    if args.self_check:
        verify_phase_a_evidence(args.output_dir, summary)
    print(
        json.dumps(
            {
                "accepted": summary["accepted"],
                "verdict": summary["verdict"],
                "maximum_errors": {
                    formulation: result["final_errors"]
                    for formulation, result in summary["formulations"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if summary["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
