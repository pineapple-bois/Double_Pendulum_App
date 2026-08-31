from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("restart_grade_qr_continuation.py")
SPEC = importlib.util.spec_from_file_location("restart_grade_qr_continuation", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
experiment = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = experiment
SPEC.loader.exec_module(experiment)


@pytest.fixture(scope="module")
def phase_a_evidence(tmp_path_factory: pytest.TempPathFactory):
    output = tmp_path_factory.mktemp("experiment013")
    summary = experiment.run_phase_a(output)
    experiment.verify_phase_a_evidence(output, summary)
    return output, summary


def _checkpoint(output: Path, formulation: str) -> Path:
    return output / formulation / "checkpoint_at_0.5s"


def _refresh_checkpoint_manifest(path: Path) -> None:
    metadata_path = path / experiment.METADATA_FILE
    array_path = path / experiment.SERIALIZED_ARRAY_FILE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["array_sha256"] = experiment.sha256_file(array_path)
    experiment.write_json(metadata_path, metadata)
    experiment.write_json(
        path / experiment.CHECKPOINT_MANIFEST_FILE,
        {
            "schema_name": experiment.SCHEMA_NAME,
            "schema_version": experiment.SCHEMA_VERSION,
            "files": {
                experiment.METADATA_FILE: {
                    "bytes": metadata_path.stat().st_size,
                    "sha256": experiment.sha256_file(metadata_path),
                },
                experiment.SERIALIZED_ARRAY_FILE: {
                    "bytes": array_path.stat().st_size,
                    "sha256": experiment.sha256_file(array_path),
                },
            },
        },
    )


def test_phase_a_split_runs_are_accepted(phase_a_evidence) -> None:
    _, summary = phase_a_evidence
    assert summary["accepted"]
    assert summary["verdict"] == "accepted_restart_grade_qr_boundary_continuation"
    for formulation in experiment.FORMULATIONS:
        result = summary["formulations"][formulation]
        assert result["accepted"]
        assert all(result["checks"].values())
        assert max(result["final_errors"].values()) <= experiment.EQUIVALENCE_ABSOLUTE_LIMIT
        assert max(result["post_split_cycle_errors"].values()) <= experiment.EQUIVALENCE_ABSOLUTE_LIMIT


@pytest.mark.parametrize("formulation", experiment.FORMULATIONS)
def test_restart_arrays_and_metadata_round_trip_exactly(
    phase_a_evidence, formulation: str
) -> None:
    output, _ = phase_a_evidence
    state = experiment.load_restart_checkpoint(
        _checkpoint(output, formulation),
        expected_formulation=formulation,
        expected_policy=experiment.POLICY,
        expected_max_step=experiment.MAX_STEP_SECONDS,
        expected_qr_interval=experiment.QR_INTERVAL_SECONDS,
    )
    metadata = state.metadata
    assert state.reference_state.dtype == np.float64
    assert state.tangent_matrix_post_qr.dtype == np.float64
    assert state.cumulative_log_growth.dtype == np.float64
    assert np.array_equal(
        state.reference_state,
        np.asarray(metadata["array_previews"]["reference_state"], dtype=np.float64),
    )
    assert np.array_equal(
        state.tangent_matrix_post_qr,
        np.asarray(
            metadata["array_previews"]["tangent_matrix_post_qr"], dtype=np.float64
        ),
    )
    assert np.array_equal(
        state.cumulative_log_growth,
        np.asarray(
            metadata["array_previews"]["cumulative_log_growth"], dtype=np.float64
        ),
    )
    assert metadata["elapsed_time_seconds"] == experiment.SPLIT_TIME_SECONDS
    assert metadata["completed_qr_cycle_count"] == 2
    assert metadata["provenance"]["runtime"]["numpy_version"] == np.__version__
    assert state.provenance_warnings == ()


def test_incompatible_policy_and_formulation_are_rejected(phase_a_evidence) -> None:
    output, _ = phase_a_evidence
    checkpoint = _checkpoint(output, "euler_lagrange")
    with pytest.raises(experiment.RestartCompatibilityError, match="formulation"):
        experiment.load_restart_checkpoint(
            checkpoint, expected_formulation="canonical_hamiltonian"
        )
    with pytest.raises(experiment.RestartCompatibilityError, match="solver policy"):
        experiment.load_restart_checkpoint(
            checkpoint, expected_policy=experiment.experiment006.STRICTER_POLICY
        )
    with pytest.raises(experiment.RestartCompatibilityError, match="max_step"):
        experiment.load_restart_checkpoint(
            checkpoint, expected_max_step=experiment.MAX_STEP_SECONDS / 2.0
        )
    with pytest.raises(experiment.RestartCompatibilityError, match="QR interval"):
        experiment.load_restart_checkpoint(
            checkpoint, expected_qr_interval=experiment.QR_INTERVAL_SECONDS / 2.0
        )


def test_invalid_shapes_and_missing_cumulative_logs_are_rejected(
    phase_a_evidence, tmp_path: Path
) -> None:
    output, _ = phase_a_evidence
    original = experiment.load_restart_checkpoint(
        _checkpoint(output, "euler_lagrange")
    )
    malformed = replace(original, reference_state=np.zeros(3, dtype=np.float64))
    with pytest.raises(experiment.RestartStateError, match="reference_state has shape"):
        experiment.validate_restart_state(malformed)
    malformed = replace(
        original, tangent_matrix_post_qr=np.zeros((4, 3), dtype=np.float64)
    )
    with pytest.raises(
        experiment.RestartStateError, match="tangent_matrix_post_qr has shape"
    ):
        experiment.validate_restart_state(malformed)

    missing = tmp_path / "missing_logs"
    experiment.save_restart_checkpoint(missing, original)
    np.savez(
        missing / experiment.SERIALIZED_ARRAY_FILE,
        reference_state=original.reference_state,
        tangent_matrix_post_qr=original.tangent_matrix_post_qr,
    )
    _refresh_checkpoint_manifest(missing)
    with pytest.raises(experiment.RestartStateError, match="incomplete"):
        experiment.load_restart_checkpoint(missing)


def test_schema_and_provenance_mismatch_guards(
    phase_a_evidence, tmp_path: Path
) -> None:
    output, _ = phase_a_evidence
    original = experiment.load_restart_checkpoint(
        _checkpoint(output, "canonical_hamiltonian")
    )

    schema_path = tmp_path / "schema_mismatch"
    experiment.save_restart_checkpoint(schema_path, original)
    metadata_path = schema_path / experiment.METADATA_FILE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["schema_version"] = experiment.SCHEMA_VERSION + 1
    experiment.write_json(metadata_path, metadata)
    _refresh_checkpoint_manifest(schema_path)
    with pytest.raises(experiment.RestartCompatibilityError, match="schema"):
        experiment.load_restart_checkpoint(schema_path)

    provenance_path = tmp_path / "provenance_mismatch"
    experiment.save_restart_checkpoint(provenance_path, original)
    metadata_path = provenance_path / experiment.METADATA_FILE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    first_source = next(iter(metadata["provenance"]["source_sha256"]))
    metadata["provenance"]["source_sha256"][first_source] = "0" * 64
    experiment.write_json(metadata_path, metadata)
    _refresh_checkpoint_manifest(provenance_path)
    with pytest.raises(experiment.RestartCompatibilityError, match="provenance"):
        experiment.load_restart_checkpoint(provenance_path)
    loaded = experiment.load_restart_checkpoint(
        provenance_path, allow_provenance_mismatch=True
    )
    assert loaded.provenance_warnings == ("executed source-file hashes differ",)


def test_evidence_manifest_covers_checkpoint_artifacts(phase_a_evidence) -> None:
    output, summary = phase_a_evidence
    experiment.verify_phase_a_evidence(output, summary)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    covered = {record["path"] for record in manifest["files"]}
    for formulation in experiment.FORMULATIONS:
        prefix = f"{formulation}/checkpoint_at_0.5s/"
        assert prefix + experiment.METADATA_FILE in covered
        assert prefix + experiment.SERIALIZED_ARRAY_FILE in covered
        assert prefix + experiment.CHECKPOINT_MANIFEST_FILE in covered
