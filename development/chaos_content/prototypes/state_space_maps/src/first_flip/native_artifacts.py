"""Validated immutable artifacts for the native first-flip DOP853 candidate.

The shared library is published once under a content/runtime identity. Loaded
libraries, callback handles and callback addresses remain process-local.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path, PurePath
from typing import Iterator, Mapping

import llvmlite
import llvmlite.binding as llvm
import numba
import numpy as np
import scipy

from ..lyapunov.s1_artifacts import (
    S1_BUILD_FLAGS,
    S1_DOP_SOURCE_VERSION,
    S1_NATIVE_DIRECTORY,
    S1_SOURCE_SHA256,
    s1_build_support,
)
from . import compiled as compiled_module

try:
    import fcntl
except ImportError:  # pragma: no cover - candidate is fail-closed on Darwin.
    fcntl = None


FIRST_FLIP_NATIVE_EVALUATOR = "native_dop853_first_flip_v1"
FIRST_FLIP_NATIVE_IMPLEMENTATION = "first_flip_native_dop853_event_loop_v1"
FIRST_FLIP_NATIVE_ARTIFACT_SCHEMA = 1
FIRST_FLIP_NATIVE_CACHE_ENVIRONMENT = "STATE_SPACE_MAPS_FIRST_FLIP_NATIVE_CACHE"
FIRST_FLIP_NATIVE_LIBRARY = "first_flip_native.so"
FIRST_FLIP_NATIVE_MANIFEST = "manifest.json"
FIRST_FLIP_NATIVE_DIRECTORY = Path(__file__).with_name("native")
FIRST_FLIP_NATIVE_LOOP_SOURCE = FIRST_FLIP_NATIVE_DIRECTORY / "first_flip_loop.c"
FIRST_FLIP_NATIVE_LOOP_SHA256 = "e43c6d7d382a1fb01fdfd39c1e027dbc1a238a38b6022a8a8b4079f62e59d95d"
_DENSE_COUNTER_DEFECT = "                nfcn += 3;"
_DENSE_COUNTER_CORRECTION = "                *nfcn += 3;"


class FirstFlipNativeUnavailableError(RuntimeError):
    """The validated native candidate could not be safely built or loaded."""


@dataclass(frozen=True)
class FirstFlipNativeArtifact:
    available: bool
    key: str
    directory: str | None
    manifest_sha256: str | None
    library_sha256: str | None
    identity: Mapping[str, object]
    failure_type: str | None = None
    failure_reason: str | None = None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _corrected_dop_source() -> str:
    source = (S1_NATIVE_DIRECTORY / "dop.c").read_text()
    if source.count(_DENSE_COUNTER_DEFECT) != 1:
        raise FirstFlipNativeUnavailableError(
            "vendored DOP853 dense-counter source does not match the reviewed input"
        )
    return source.replace(_DENSE_COUNTER_DEFECT, _DENSE_COUNTER_CORRECTION)


def corrected_dop_sha256() -> str:
    return hashlib.sha256(_corrected_dop_source().encode()).hexdigest()


@lru_cache(maxsize=1)
def first_flip_native_support():
    support = s1_build_support()
    try:
        loop_ok = _sha256(FIRST_FLIP_NATIVE_LOOP_SOURCE) == FIRST_FLIP_NATIVE_LOOP_SHA256
        corrected_dop_sha256()
    except (OSError, FirstFlipNativeUnavailableError):
        loop_ok = False
    supported = support.supported and loop_ok and fcntl is not None
    reason = "validated" if supported else (
        support.reason if not support.supported else "first-flip native source identity is not validated"
    )
    return {"supported": supported, "reason": reason, "s1_support": asdict(support)}


@lru_cache(maxsize=1)
def first_flip_native_artifact_identity() -> dict[str, object]:
    support = s1_build_support()
    runtime_source = Path(__file__).with_name("native_runtime.py")
    return {
        "schema_version": FIRST_FLIP_NATIVE_ARTIFACT_SCHEMA,
        "implementation": FIRST_FLIP_NATIVE_IMPLEMENTATION,
        "route": FIRST_FLIP_NATIVE_EVALUATOR,
        "dop_source": S1_DOP_SOURCE_VERSION,
        "vendored_dop_source_sha256": {
            name: _sha256(S1_NATIVE_DIRECTORY / name)
            for name in ("dop.c", "dop.h", "LICENSE_DOP")
        },
        "expected_vendored_dop_source_sha256": {
            name: S1_SOURCE_SHA256[name]
            for name in ("dop.c", "dop.h", "LICENSE_DOP")
        },
        "dense_counter_correction": "nfcn += 3; -> *nfcn += 3;",
        "corrected_dop_sha256": corrected_dop_sha256(),
        "native_loop_source_sha256": _sha256(FIRST_FLIP_NATIVE_LOOP_SOURCE),
        "artifact_implementation_sha256": _sha256(Path(__file__)),
        "runtime_implementation_sha256": _sha256(runtime_source),
        "physical_rhs_implementation_sha256": _sha256(Path(compiled_module.__file__)),
        "compiler": support.compiler,
        "compiler_target": support.compiler_target,
        "compiler_path": str(Path(path).resolve()) if (path := shutil.which("clang")) else None,
        "compiler_flags": list(S1_BUILD_FLAGS),
        "system": support.system,
        "machine": support.machine,
        "macos": support.macos,
        "platform": platform.platform(),
        "python": support.python,
        "python_implementation": platform.python_implementation(),
        "python_cache_tag": sys.implementation.cache_tag,
        "python_soabi": sysconfig.get_config_var("SOABI"),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "numba": numba.__version__,
        "llvmlite": llvmlite.__version__,
        "llvm": ".".join(str(item) for item in llvm.llvm_version_info),
    }


def first_flip_native_artifact_key(identity: Mapping[str, object] | None = None) -> str:
    encoded = json.dumps(dict(identity or first_flip_native_artifact_identity()), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def first_flip_native_cache_directory() -> Path:
    configured = os.environ.get(FIRST_FLIP_NATIVE_CACHE_ENVIRONMENT)
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            raise FirstFlipNativeUnavailableError(f"{FIRST_FLIP_NATIVE_CACHE_ENVIRONMENT} must be absolute")
        return path
    user = str(os.getuid()) if hasattr(os, "getuid") else "user"
    return Path(tempfile.gettempdir()) / f"state-space-maps-first-flip-native-{user}"


_REQUEST_LOCK = threading.RLock()


def _prepare_root(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise FirstFlipNativeUnavailableError("native artifact root is not a real directory")
    return path.resolve()


@contextlib.contextmanager
def _artifact_lock(root: Path, key: str, exclusive: bool) -> Iterator[None]:
    if fcntl is None:
        raise FirstFlipNativeUnavailableError("validated artifact locking is unavailable")
    root = _prepare_root(root)
    descriptor = os.open(root / f".{key}.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _files(directory: Path) -> dict[str, str]:
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_dir() or path.name == FIRST_FLIP_NATIVE_MANIFEST:
            continue
        if path.is_symlink() or not path.is_file():
            raise FirstFlipNativeUnavailableError("native artifact contains a non-regular file")
        result[path.relative_to(directory).as_posix()] = _sha256(path)
    return result


def _safe_relative(value: str) -> bool:
    path = PurePath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def _build(directory: Path, key: str, identity: Mapping[str, object]) -> None:
    support = first_flip_native_support()
    if not support["supported"]:
        raise FirstFlipNativeUnavailableError(str(support["reason"]))
    compiler = shutil.which("clang")
    if compiler is None:
        raise FirstFlipNativeUnavailableError("clang became unavailable")
    corrected = directory / "dop.c"
    corrected.write_text(_corrected_dop_source())
    library = directory / FIRST_FLIP_NATIVE_LIBRARY
    command = [compiler, *S1_BUILD_FLAGS, "-I", str(directory), "-I", str(S1_NATIVE_DIRECTORY), str(FIRST_FLIP_NATIVE_LOOP_SOURCE), "-o", str(library)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except Exception as error:
        raise FirstFlipNativeUnavailableError(f"native artifact build failed: {type(error).__name__}") from error
    files = _files(directory)
    if FIRST_FLIP_NATIVE_LIBRARY not in files or "dop.c" not in files:
        raise FirstFlipNativeUnavailableError("native artifact build was incomplete")
    manifest = {"schema_version": FIRST_FLIP_NATIVE_ARTIFACT_SCHEMA, "key": key, "identity": dict(identity), "files": files}
    with (directory / FIRST_FLIP_NATIVE_MANIFEST).open("x") as target:
        json.dump(manifest, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")
        target.flush()
        os.fsync(target.fileno())


def _read(directory: Path, key: str, identity: Mapping[str, object], expected_manifest: str | None = None) -> FirstFlipNativeArtifact:
    try:
        manifest_bytes = (directory / FIRST_FLIP_NATIVE_MANIFEST).read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise FirstFlipNativeUnavailableError(f"native artifact manifest unavailable: {type(error).__name__}") from error
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    if expected_manifest not in (None, manifest_sha):
        raise FirstFlipNativeUnavailableError("native artifact manifest digest changed")
    if manifest.get("schema_version") != FIRST_FLIP_NATIVE_ARTIFACT_SCHEMA or manifest.get("key") != key or manifest.get("identity") != dict(identity):
        raise FirstFlipNativeUnavailableError("native artifact identity is incompatible")
    files = manifest.get("files")
    if not isinstance(files, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not _safe_relative(k) for k, v in files.items()) or _files(directory) != files:
        raise FirstFlipNativeUnavailableError("native artifact file validation failed")
    library_sha = files.get(FIRST_FLIP_NATIVE_LIBRARY)
    if library_sha is None or files.get("dop.c") != identity["corrected_dop_sha256"]:
        raise FirstFlipNativeUnavailableError("native artifact components are incomplete")
    return FirstFlipNativeArtifact(True, key, str(directory), manifest_sha, library_sha, dict(identity))


def ensure_first_flip_native_artifact(cache_directory: Path | None = None) -> FirstFlipNativeArtifact:
    support = first_flip_native_support()
    if not support["supported"]:
        raise FirstFlipNativeUnavailableError(str(support["reason"]))
    identity = first_flip_native_artifact_identity()
    key = first_flip_native_artifact_key(identity)
    root = _prepare_root(cache_directory or first_flip_native_cache_directory())
    final = root / key
    with _REQUEST_LOCK, _artifact_lock(root, key, True):
        try:
            return _read(final, key, identity)
        except FirstFlipNativeUnavailableError:
            pass
        discarded = None
        if final.exists():
            discarded = root / f".{key}.invalid-{uuid.uuid4().hex}"
            os.replace(final, discarded)
        stage = Path(tempfile.mkdtemp(prefix=f".{key}.build-", dir=root))
        try:
            _build(stage, key, identity)
            os.replace(stage, final)
            artifact = _read(final, key, identity)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        finally:
            if discarded is not None:
                shutil.rmtree(discarded, ignore_errors=True)
        return artifact


def load_first_flip_native_artifact(artifact: FirstFlipNativeArtifact) -> FirstFlipNativeArtifact:
    identity = first_flip_native_artifact_identity()
    key = first_flip_native_artifact_key(identity)
    if not artifact.available or artifact.directory is None or artifact.manifest_sha256 is None or artifact.key != key or dict(artifact.identity) != identity:
        raise FirstFlipNativeUnavailableError(artifact.failure_reason or "native artifact descriptor is incompatible")
    directory = Path(artifact.directory)
    if directory.name != key:
        raise FirstFlipNativeUnavailableError("native artifact directory identity is incompatible")
    with _artifact_lock(directory.parent, key, False):
        return _read(directory, key, identity, artifact.manifest_sha256)


def unavailable_first_flip_native_artifact(error: BaseException) -> FirstFlipNativeArtifact:
    identity = first_flip_native_artifact_identity()
    return FirstFlipNativeArtifact(False, first_flip_native_artifact_key(identity), None, None, None, identity, type(error).__name__, str(error))


def prepare_first_flip_native_artifact_for_workers() -> FirstFlipNativeArtifact | None:
    if not first_flip_native_support()["supported"]:
        return None
    try:
        return ensure_first_flip_native_artifact()
    except FirstFlipNativeUnavailableError as error:
        return unavailable_first_flip_native_artifact(error)
