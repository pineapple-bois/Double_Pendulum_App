"""Integrity and lifecycle coverage for reusable operational S1 artifacts."""

from __future__ import annotations

import json
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from development.chaos_content.prototypes.state_space_maps.src.lyapunov import (
    operational as operational_module,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov import (
    s1_artifacts as artifacts,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
    HYBRID_FAST_EVALUATOR,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.operational import (
    S1_RECOVERY_EXECUTION_ERROR,
    evaluate_renormalized_tangent_operational,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    RenormalizedTangentSpec,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.s1 import (
    S1_EVALUATOR,
    clear_s1_process_runtime,
    configure_s1_artifact,
    ensure_s1_artifact,
    load_s1_artifact,
    s1_artifact_identity,
    s1_artifact_key,
    s1_build_provenance,
    s1_build_support,
    unavailable_s1_artifact,
)


def _concurrent_load(cache_directory: str) -> tuple[int, str, int, int]:
    artifact = ensure_s1_artifact(Path(cache_directory))
    configure_s1_artifact(artifact)
    rhs, reset = artifacts._native_callbacks()
    artifacts.native_library()
    time.sleep(0.05)
    return os.getpid(), artifact.key, rhs.address, reset.address


@pytest.fixture(autouse=True)
def _clear_process_runtime() -> None:
    clear_s1_process_runtime()
    yield
    clear_s1_process_runtime()


def _require_supported_build() -> None:
    if not s1_build_support().supported:
        pytest.skip("S1 artifacts require the validated native build")


def test_cold_creation_warm_load_and_repeated_load_do_not_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_supported_build()
    calls = 0
    build = artifacts._build_artifact

    def counted_build(directory, key, identity):
        nonlocal calls
        calls += 1
        return build(directory, key, identity)

    monkeypatch.setattr(artifacts, "_build_artifact", counted_build)
    cold = ensure_s1_artifact(tmp_path)
    warm = ensure_s1_artifact(tmp_path)
    repeated = ensure_s1_artifact(tmp_path)

    assert calls == 1
    assert cold == warm == repeated
    assert Path(cold.directory or "").name == cold.key
    assert cold.native_library_sha256
    assert len(cold.callback_artifact_sha256) >= 4


def test_concurrent_spawn_requests_publish_once_and_reconstruct_callbacks(
    tmp_path: Path,
) -> None:
    _require_supported_build()
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=4, mp_context=context) as executor:
        records = tuple(
            executor.map(_concurrent_load, (str(tmp_path),) * 8, chunksize=1)
        )

    process_ids = {record[0] for record in records}
    keys = {record[1] for record in records}
    assert len(process_ids) == 4
    assert len(keys) == 1
    assert all(rhs > 0 and reset > 0 for _, _, rhs, reset in records)
    assert len([path for path in tmp_path.iterdir() if path.is_dir()]) == 1
    assert not tuple(tmp_path.glob("*.build-*"))
    assert "address" not in json.dumps(ensure_s1_artifact(tmp_path).__dict__)


def test_concurrent_thread_requests_do_not_duplicate_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_supported_build()
    calls = 0
    build = artifacts._build_artifact

    def counted_build(directory, key, identity):
        nonlocal calls
        calls += 1
        return build(directory, key, identity)

    monkeypatch.setattr(artifacts, "_build_artifact", counted_build)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = tuple(executor.map(lambda _index: ensure_s1_artifact(tmp_path), range(8)))

    assert calls == 1
    assert len({result.key for result in results}) == 1


def test_incomplete_publication_is_never_loaded(tmp_path: Path) -> None:
    _require_supported_build()
    key = s1_artifact_key()
    incomplete = tmp_path / key
    incomplete.mkdir()
    (incomplete / artifacts.S1_NATIVE_LIBRARY).write_bytes(b"partial")

    artifact = ensure_s1_artifact(tmp_path)

    assert artifact.available
    assert load_s1_artifact(artifact) == artifact
    assert not tuple(tmp_path.glob(f".{key}.invalid-*"))


def test_corrupt_artifact_fails_closed_and_is_rebuilt_by_coordinator(
    tmp_path: Path,
) -> None:
    _require_supported_build()
    artifact = ensure_s1_artifact(tmp_path)
    native = Path(artifact.directory or "") / artifacts.S1_NATIVE_LIBRARY
    native.write_bytes(native.read_bytes() + b"corrupt")

    with pytest.raises(artifacts.S1NativeUnavailableError, match="digest"):
        load_s1_artifact(artifact)

    rebuilt = ensure_s1_artifact(tmp_path)
    assert load_s1_artifact(rebuilt) == rebuilt


def test_stale_or_incompatible_identity_is_not_reused(tmp_path: Path) -> None:
    _require_supported_build()
    artifact = ensure_s1_artifact(tmp_path)
    incompatible = replace(
        artifact,
        identity={**artifact.identity, "numba": "incompatible"},
    )

    with pytest.raises(artifacts.S1NativeUnavailableError, match="incompatible"):
        load_s1_artifact(incompatible)


def test_unsupported_environment_cannot_create_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        artifacts,
        "s1_build_support",
        lambda: SimpleNamespace(supported=False, reason="unsupported fixture"),
    )
    with pytest.raises(artifacts.S1NativeUnavailableError, match="unsupported fixture"):
        ensure_s1_artifact(tmp_path)


def test_runtime_provenance_identifies_actual_validated_artifact(
    tmp_path: Path,
) -> None:
    _require_supported_build()
    artifact = ensure_s1_artifact(tmp_path)
    configure_s1_artifact(artifact)
    provenance = s1_build_provenance(runtime_artifact=True)

    assert provenance["implementation"] == S1_EVALUATOR
    assert provenance["artifact"]["available"] is True
    assert provenance["artifact"]["key"] == artifact.key
    assert provenance["artifact"]["manifest_sha256"] == artifact.manifest_sha256
    assert provenance["artifact"]["native_library_sha256"]
    assert provenance["artifact"]["callback_bundle_sha256"]
    assert "identity" not in provenance["artifact"]
    assert s1_build_provenance()["artifact"]["identity"] == s1_artifact_identity()


def test_persistent_provenance_is_independent_of_cache_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first-cache"
    second = tmp_path / "second-cache"
    monkeypatch.setenv(artifacts.S1_ARTIFACT_CACHE_ENVIRONMENT, str(first))
    first_provenance = s1_build_provenance()
    monkeypatch.setenv(artifacts.S1_ARTIFACT_CACHE_ENVIRONMENT, str(second))
    second_provenance = s1_build_provenance()

    assert first_provenance == second_provenance
    assert str(first) not in json.dumps(first_provenance)
    assert str(second) not in json.dumps(second_provenance)


def test_artifact_failure_recovers_through_trusted_operational_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_supported_build()
    failed = unavailable_s1_artifact(
        artifacts.S1NativeUnavailableError("controlled artifact failure")
    )
    configure_s1_artifact(failed)
    monkeypatch.setattr(
        operational_module,
        "s1_build_support",
        lambda: SimpleNamespace(supported=True),
    )

    result = evaluate_renormalized_tangent_operational(RenormalizedTangentSpec())

    assert result.evaluator == HYBRID_FAST_EVALUATOR
    assert result.attempted_evaluators == (S1_EVALUATOR,)
    assert result.recovery_reason == S1_RECOVERY_EXECUTION_ERROR
    assert result.attempt_provenance[S1_EVALUATOR]["artifact"]["available"] is False
