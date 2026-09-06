"""Focused promotion-candidate gates for native DOP853 first flip."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.src.first_flip import field_adapter
from development.chaos_content.prototypes.state_space_maps.src.first_flip.compiled import FIRST_FLIP_COMPILED_EVALUATOR
from development.chaos_content.prototypes.state_space_maps.src.first_flip.field_adapter import (
    FIRST_FLIP_REFERENCE_EVALUATOR,
    FirstFlipFieldSpec,
    adapt_first_flip_result,
    evaluate_first_flip_field_cell,
    first_flip_evaluator_binding,
    initialize_first_flip_field_worker,
    periodic_first_flip_field_definition,
    run_periodic_first_flip_field,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.native_artifacts import (
    FIRST_FLIP_NATIVE_EVALUATOR,
    FirstFlipNativeUnavailableError,
    ensure_first_flip_native_artifact,
    load_first_flip_native_artifact,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.native_runtime import (
    FirstFlipNativeNumericalError,
    first_flip_native_provenance,
    first_flip_time_native,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.reference import first_flip_time
from development.chaos_content.prototypes.state_space_maps.src.generation import IntegrityError, ScalarCellTask, read_authoritative_field
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import EulerLagrangeState
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import EvaluationStatus

EVIDENCE = Path(__file__).resolve().parents[2] / "investigations/performance/evidence/current/first_flip_compiled_rhs_feasibility.json"


def _task(theta1: float = -2.6179938779914944, theta2: float = -2.6179938779914944):
    return ScalarCellTask(0, 0, 0, theta2, theta1)


def test_native_dispatch_and_exact_ineligible_route() -> None:
    native = first_flip_evaluator_binding(FirstFlipFieldSpec())
    compiled = first_flip_evaluator_binding(FirstFlipFieldSpec(), force_compiled=True)
    trusted = first_flip_evaluator_binding(FirstFlipFieldSpec(observation_horizon_seconds=2.0))
    assert native.execution_routes == (FIRST_FLIP_NATIVE_EVALUATOR, FIRST_FLIP_COMPILED_EVALUATOR, FIRST_FLIP_REFERENCE_EVALUATOR)
    assert compiled.execution_routes == (FIRST_FLIP_COMPILED_EVALUATOR, FIRST_FLIP_REFERENCE_EVALUATOR)
    assert trusted.execution_routes == (FIRST_FLIP_REFERENCE_EVALUATOR,)


def test_native_artifact_cold_then_cache_hit(tmp_path: Path) -> None:
    cold = ensure_first_flip_native_artifact(tmp_path)
    library = Path(cold.directory or "") / "first_flip_native.so"
    modified = library.stat().st_mtime_ns
    warm = ensure_first_flip_native_artifact(tmp_path)
    assert warm == cold
    assert library.stat().st_mtime_ns == modified


def test_native_artifact_concurrent_request_and_corrupt_republication(tmp_path: Path) -> None:
    with ThreadPoolExecutor(max_workers=4) as pool:
        artifacts = list(pool.map(lambda _index: ensure_first_flip_native_artifact(tmp_path), range(4)))
    assert len({artifact.manifest_sha256 for artifact in artifacts}) == 1
    library = Path(artifacts[0].directory or "") / "first_flip_native.so"
    library.write_bytes(b"incomplete publication")
    repaired = ensure_first_flip_native_artifact(tmp_path)
    assert repaired.library_sha256 != artifacts[0].library_sha256 or library.stat().st_size > 1024
    incompatible = replace(repaired, key="0" * 64)
    with pytest.raises(FirstFlipNativeUnavailableError, match="incompatible"):
        load_first_flip_native_artifact(incompatible)


def test_native_initialization_failure_recovers_to_compiled(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(_parameters):
        raise FirstFlipNativeUnavailableError("controlled unavailable")
    monkeypatch.setattr(field_adapter, "initialize_native_first_flip", unavailable)
    initialize_first_flip_field_worker(FirstFlipFieldSpec())
    result = evaluate_first_flip_field_cell(_task())
    assert result.status is EvaluationStatus.COMPLETED_VALID
    assert result.evaluator == FIRST_FLIP_COMPILED_EVALUATOR
    assert result.attempted_evaluators == (FIRST_FLIP_NATIVE_EVALUATOR,)
    assert result.recovery_reason == "native_first_flip_initialization_unavailable"


def test_unsupported_native_and_double_initialization_failure_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(field_adapter, "first_flip_native_support", lambda: {"supported": False, "reason": "fixture"})
    assert first_flip_evaluator_binding(FirstFlipFieldSpec()).execution_routes[0] == FIRST_FLIP_COMPILED_EVALUATOR
    monkeypatch.setattr(field_adapter, "first_flip_native_support", lambda: {"supported": True, "reason": "fixture"})
    monkeypatch.setattr(field_adapter, "initialize_native_first_flip", lambda _p: (_ for _ in ()).throw(FirstFlipNativeUnavailableError("native unavailable")))
    monkeypatch.setattr(field_adapter, "first_flip_compiled_support", lambda: type("Support", (), {"supported": False})())
    initialize_first_flip_field_worker(FirstFlipFieldSpec())
    result = evaluate_first_flip_field_cell(_task())
    assert result.evaluator == FIRST_FLIP_REFERENCE_EVALUATOR
    assert result.attempted_evaluators == (FIRST_FLIP_NATIVE_EVALUATOR, FIRST_FLIP_COMPILED_EVALUATOR)


def test_native_rejection_recovers_and_programming_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = FirstFlipFieldSpec()
    initialize_first_flip_field_worker(spec)
    monkeypatch.setattr(field_adapter, "first_flip_time_native", lambda *a, **k: (_ for _ in ()).throw(FirstFlipNativeNumericalError("reject")))
    recovered = evaluate_first_flip_field_cell(_task())
    assert recovered.evaluator == FIRST_FLIP_COMPILED_EVALUATOR
    assert recovered.attempted_evaluators == (FIRST_FLIP_NATIVE_EVALUATOR,)
    monkeypatch.setattr(field_adapter, "first_flip_time_native", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("programming defect")))
    with pytest.raises(RuntimeError, match="programming defect"):
        evaluate_first_flip_field_cell(_task())


def test_saved_37_cases_pass_production_native_gates() -> None:
    cases = json.loads(EVIDENCE.read_text())["cases"]
    assert len(cases) == 37
    spec = FirstFlipFieldSpec()
    maxima = {"time": 0.0, "state": 0.0, "residual": 0.0, "energy": 0.0, "increment": 0.0}
    for case in cases:
        state = EulerLagrangeState(case["theta1_radians"], case["theta2_radians"], 0.0, 0.0)
        trusted = first_flip_time(state, spec.parameters, spec.solver, 5.0)
        native = first_flip_time_native(state, spec.parameters, spec.solver, 5.0)
        assert adapt_first_flip_result(trusted, spec).status is EvaluationStatus.COMPLETED_VALID
        assert adapt_first_flip_result(native, spec, evaluator=FIRST_FLIP_NATIVE_EVALUATOR).status is EvaluationStatus.COMPLETED_VALID
        assert native.status is trusted.status
        assert native.event_identities == trusted.event_identities
        assert native.raw_event_counts == trusted.raw_event_counts
        assert native.winning_arm == trusted.winning_arm
        assert native.winning_direction == trusted.winning_direction
        maxima["energy"] = max(maxima["energy"], native.maximum_normalized_energy_drift)
        maxima["increment"] = max(maxima["increment"], native.maximum_accepted_angular_increment)
        if trusted.event_time_seconds is not None:
            maxima["time"] = max(maxima["time"], abs(native.event_time_seconds - trusted.event_time_seconds))
            maxima["state"] = max(maxima["state"], float(np.max(np.abs(np.asarray(native.event_state) - np.asarray(trusted.event_state)))))
            maxima["residual"] = max(maxima["residual"], max(abs(item.residual) for item in native.event_surface_residuals if item.identity in native.event_identities))
        else:
            assert native.integration_endpoint_seconds == pytest.approx(5.0, abs=2e-14)
    assert maxima["time"] <= 5e-8
    assert maxima["state"] <= 5e-7
    assert maxima["residual"] <= 1e-10
    assert maxima["energy"] <= 5e-9
    assert maxima["increment"] < 0.5


def test_native_spawn_resume_and_cross_definition_rejection(tmp_path: Path) -> None:
    native_path = tmp_path / "native.h5"
    created = run_periodic_first_flip_field(native_path, 2, mode="create")
    resumed = run_periodic_first_flip_field(native_path, 2, mode="resume")
    snapshot = read_authoritative_field(native_path)
    assert created.all_workers_stopped and resumed.evaluated_cells == 0
    assert set(np.unique(snapshot.execution_route)) == {3}
    assert snapshot.metadata["evaluator_provenance"]["native"]["artifact"]["key"]
    with pytest.raises(IntegrityError):
        run_periodic_first_flip_field(native_path, 2, mode="resume", force_compiled=True)
    with pytest.raises(IntegrityError):
        run_periodic_first_flip_field(native_path, 2, mode="resume", force_trusted=True)
    compiled_path = tmp_path / "compiled.h5"
    trusted_path = tmp_path / "trusted.h5"
    run_periodic_first_flip_field(compiled_path, 2, mode="create", force_compiled=True)
    run_periodic_first_flip_field(trusted_path, 2, mode="create", force_trusted=True)
    with pytest.raises(IntegrityError):
        run_periodic_first_flip_field(compiled_path, 2, mode="resume")
    with pytest.raises(IntegrityError):
        run_periodic_first_flip_field(trusted_path, 2, mode="resume")


def test_native_provenance_records_corrected_dense_source() -> None:
    provenance = first_flip_native_provenance()
    identity = provenance["artifact"]["identity"]
    assert identity["dense_counter_correction"] == "nfcn += 3; -> *nfcn += 3;"
    assert identity["corrected_dop_sha256"] != identity["vendored_dop_source_sha256"]["dop.c"]
