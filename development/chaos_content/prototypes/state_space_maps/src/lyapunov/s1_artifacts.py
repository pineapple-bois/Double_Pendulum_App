"""Validated build-once/load-many artifacts for operational S1.

The published artifact contains only immutable native code and Numba callback
cache files.  Loaded libraries, callback objects, addresses, and integration
state remain process-local.
"""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import inspect
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
from numba import carray, cfunc, types
from numba.core import config as numba_config

from . import compiled as compiled_module
from .compiled import compiled_reference_and_tangent_rhs

try:
    import fcntl
except ImportError:  # pragma: no cover - S1 is fail-closed to validated Darwin.
    fcntl = None


S1_EVALUATOR = "s1_native_dop853_v1"
S1_DOP_SOURCE_VERSION = "SciPy 1.18.0 dop.c/dop.h"
S1_BUILD_FLAGS = ("-O2", "-ffp-contract=on", "-fPIC", "-shared")
S1_NATIVE_DIRECTORY = Path(__file__).with_name("s1_native")
S1_SOURCE_SHA256: Mapping[str, str] = {
    "dop.c": "14b9fdce5f18e6ad01eb814ec7965cc51804ba49b359d4bd6cf72a958239d213",
    "dop.h": "72549b5250fbfde34026b2bf1a8e65cbfdf1854dee35971a6922bfcbb9740944",
    "loop.c": "10137883d13d23ba5dc99aa6d7b50317632191202a8107b2b9e7d3cecb39fbbb",
    "LICENSE_DOP": "ed9bf58c6d74d3fad9d92d1d67d9bff8141d8ab60de784516b0711364fd43357",
}
S1_VALIDATED_COMPILER = "Apple clang version 17.0.0 (clang-1700.6.4.2)"
S1_VALIDATED_COMPILER_TARGET = "Target: arm64-apple-darwin24.6.0"
S1_ARTIFACT_SCHEMA_VERSION = 1
S1_ARTIFACT_CACHE_ENVIRONMENT = "STATE_SPACE_MAPS_S1_ARTIFACT_CACHE"
S1_ARTIFACT_MANIFEST = "manifest.json"
S1_NATIVE_LIBRARY = "s1_loop.so"
S1_CALLBACK_CACHE = "callbacks"


class S1NativeUnavailableError(RuntimeError):
    """The validated S1 native implementation could not be built or loaded."""


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


@dataclass(frozen=True)
class S1Artifact:
    """Spawn-safe identity for immutable published S1 build products."""

    available: bool
    key: str
    directory: str | None
    manifest_sha256: str | None
    native_library_sha256: str | None
    callback_artifact_sha256: Mapping[str, str]
    identity: Mapping[str, object]
    failure_type: str | None = None
    failure_reason: str | None = None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hashes() -> dict[str, str]:
    return {
        name: _sha256(S1_NATIVE_DIRECTORY / name)
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
        (fcntl is not None, "validated artifact locking is unavailable"),
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


_double_ptr = types.CPointer(types.float64)
_int_ptr = types.CPointer(types.int32)


def _rhs_callback_impl(n, time, state, output, parameters, error):
    y = carray(state, 8)
    p = carray(parameters, 5)
    result = compiled_reference_and_tangent_rhs(
        time, y, p[0], p[1], p[2], p[3], p[4]
    )
    for index in range(8):
        output[index] = result[index]


def _reset_callback_impl(state, characteristic_time, stretch_out, norm_error_out):
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


def _callback_source_digest() -> str:
    source = "\n".join(
        (
            inspect.getsource(_rhs_callback_impl),
            inspect.getsource(_reset_callback_impl),
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def s1_artifact_identity() -> dict[str, object]:
    """Return the complete compatibility identity used for artifact reuse."""

    support = s1_build_support()
    return {
        "schema_version": S1_ARTIFACT_SCHEMA_VERSION,
        "implementation": S1_EVALUATOR,
        "dop_source": S1_DOP_SOURCE_VERSION,
        "native_source_sha256": dict(support.source_sha256),
        "callback_source_sha256": _callback_source_digest(),
        "s1_artifact_implementation_sha256": _sha256(Path(__file__)),
        "s1_runtime_implementation_sha256": _sha256(
            Path(__file__).with_name("s1.py")
        ),
        "compiled_rhs_implementation_sha256": _sha256(
            Path(compiled_module.__file__)
        ),
        "compiler": support.compiler,
        "compiler_target": support.compiler_target,
        "compiler_path": (
            str(Path(path).resolve()) if (path := shutil.which("clang")) else None
        ),
        "compiler_flags": list(S1_BUILD_FLAGS),
        "system": support.system,
        "machine": support.machine,
        "macos": support.macos,
        "platform": platform.platform(),
        "python": support.python,
        "python_implementation": platform.python_implementation(),
        "python_cache_tag": sys.implementation.cache_tag,
        "python_soabi": sysconfig.get_config_var("SOABI"),
        "numpy": support.numpy,
        "scipy": support.scipy,
        "numba": support.numba,
        "llvmlite": llvmlite.__version__,
        "llvm": ".".join(str(item) for item in llvm.llvm_version_info),
    }


def s1_artifact_key(identity: Mapping[str, object] | None = None) -> str:
    encoded = json.dumps(
        dict(identity or s1_artifact_identity()),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def s1_artifact_cache_directory() -> Path:
    configured = os.environ.get(S1_ARTIFACT_CACHE_ENVIRONMENT)
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            raise S1NativeUnavailableError(
                f"{S1_ARTIFACT_CACHE_ENVIRONMENT} must be an absolute path"
            )
        return path
    user = str(os.getuid()) if hasattr(os, "getuid") else "user"
    return Path(tempfile.gettempdir()) / f"state-space-maps-s1-artifacts-{user}"


_CALLBACK_COMPILATION_LOCK = threading.RLock()
_ARTIFACT_REQUEST_LOCK = threading.RLock()


def _compile_callbacks(cache_directory: Path):
    cache_directory.mkdir(parents=True, exist_ok=True)
    with _CALLBACK_COMPILATION_LOCK:
        previous_cache = numba_config.CACHE_DIR
        numba_config.CACHE_DIR = str(cache_directory)
        try:
            rhs = cfunc(
                types.void(
                    types.int32,
                    types.float64,
                    _double_ptr,
                    _double_ptr,
                    _double_ptr,
                    _int_ptr,
                ),
                cache=True,
            )(_rhs_callback_impl)
            reset = cfunc(
                types.int32(
                    _double_ptr,
                    types.float64,
                    _double_ptr,
                    _double_ptr,
                ),
                cache=True,
            )(_reset_callback_impl)
        finally:
            numba_config.CACHE_DIR = previous_cache
    return rhs, reset


def _prepare_cache_root(cache_directory: Path) -> Path:
    try:
        cache_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if cache_directory.is_symlink() or not cache_directory.is_dir():
            raise S1NativeUnavailableError(
                "S1 artifact cache root is not a real directory"
            )
        return cache_directory.resolve()
    except OSError as error:
        raise S1NativeUnavailableError(
            f"S1 artifact cache root is unavailable: {type(error).__name__}"
        ) from error


@contextlib.contextmanager
def _artifact_lock(
    cache_directory: Path,
    key: str,
    *,
    exclusive: bool,
) -> Iterator[None]:
    if fcntl is None:
        raise S1NativeUnavailableError("validated artifact locking is unavailable")
    root = _prepare_cache_root(cache_directory)
    try:
        descriptor = os.open(root / f".{key}.lock", os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as error:
        raise S1NativeUnavailableError(
            f"S1 artifact lock is unavailable: {type(error).__name__}"
        ) from error
    locked = False
    try:
        try:
            fcntl.flock(
                descriptor,
                fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH,
            )
            locked = True
        except OSError as error:
            raise S1NativeUnavailableError(
                f"S1 artifact lock failed: {type(error).__name__}"
            ) from error
        yield
    finally:
        if locked:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _manifest_files(directory: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_dir() or path.name == S1_ARTIFACT_MANIFEST:
            continue
        if path.is_symlink() or not path.is_file():
            raise S1NativeUnavailableError("S1 artifact contains a non-regular file")
        relative = path.relative_to(directory).as_posix()
        files[relative] = _sha256(path)
    return files


def _write_json_atomically_unpublished(path: Path, payload: Mapping[str, object]) -> None:
    with path.open("x", encoding="utf-8") as target:
        json.dump(payload, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")
        target.flush()
        os.fsync(target.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _build_artifact(directory: Path, key: str, identity: Mapping[str, object]) -> None:
    support = s1_build_support()
    if not support.supported:
        raise S1NativeUnavailableError(support.reason)
    compiler_path = shutil.which("clang")
    if compiler_path is None:
        raise S1NativeUnavailableError("clang became unavailable after validation")
    native_path = directory / S1_NATIVE_LIBRARY
    command = [
        compiler_path,
        *S1_BUILD_FLAGS,
        str(S1_NATIVE_DIRECTORY / "dop.c"),
        str(S1_NATIVE_DIRECTORY / "loop.c"),
        "-o",
        str(native_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        callbacks = _compile_callbacks(directory / S1_CALLBACK_CACHE)
    except Exception as error:
        raise S1NativeUnavailableError(
            f"validated S1 artifact build failed: {type(error).__name__}"
        ) from error
    if not native_path.is_file() or any(callback.address <= 0 for callback in callbacks):
        raise S1NativeUnavailableError("validated S1 artifact build was incomplete")
    files = _manifest_files(directory)
    callback_files = {
        name: digest
        for name, digest in files.items()
        if name.startswith(f"{S1_CALLBACK_CACHE}/")
    }
    if S1_NATIVE_LIBRARY not in files or not callback_files:
        raise S1NativeUnavailableError("validated S1 artifact files were incomplete")
    _write_json_atomically_unpublished(
        directory / S1_ARTIFACT_MANIFEST,
        {
            "schema_version": S1_ARTIFACT_SCHEMA_VERSION,
            "key": key,
            "identity": dict(identity),
            "files": files,
        },
    )
    _fsync_directory(directory)


def _safe_manifest_relative_path(value: str) -> bool:
    path = PurePath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def _read_artifact(
    directory: Path,
    key: str,
    identity: Mapping[str, object],
    *,
    expected_manifest_sha256: str | None = None,
) -> S1Artifact:
    manifest_path = directory / S1_ARTIFACT_MANIFEST
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise S1NativeUnavailableError(
            f"S1 artifact manifest is unavailable: {type(error).__name__}"
        ) from error
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if expected_manifest_sha256 not in (None, manifest_sha256):
        raise S1NativeUnavailableError("S1 artifact manifest digest changed")
    if (
        manifest.get("schema_version") != S1_ARTIFACT_SCHEMA_VERSION
        or manifest.get("key") != key
        or manifest.get("identity") != dict(identity)
    ):
        raise S1NativeUnavailableError("S1 artifact identity is incompatible")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise S1NativeUnavailableError("S1 artifact file manifest is invalid")
    if any(
        not isinstance(name, str)
        or not isinstance(digest, str)
        or not _safe_manifest_relative_path(name)
        for name, digest in files.items()
    ):
        raise S1NativeUnavailableError("S1 artifact file manifest is unsafe")
    actual_files = _manifest_files(directory)
    if actual_files != files:
        raise S1NativeUnavailableError("S1 artifact file digest validation failed")
    native_digest = files.get(S1_NATIVE_LIBRARY)
    callback_digests = {
        name: digest
        for name, digest in files.items()
        if name.startswith(f"{S1_CALLBACK_CACHE}/")
    }
    if native_digest is None or not callback_digests:
        raise S1NativeUnavailableError("S1 artifact components are incomplete")
    return S1Artifact(
        available=True,
        key=key,
        directory=str(directory),
        manifest_sha256=manifest_sha256,
        native_library_sha256=native_digest,
        callback_artifact_sha256=callback_digests,
        identity=dict(identity),
    )


def load_s1_artifact(artifact: S1Artifact) -> S1Artifact:
    """Validate an exact published descriptor without rebuilding it."""

    identity = s1_artifact_identity()
    key = s1_artifact_key(identity)
    if not artifact.available or artifact.directory is None:
        raise S1NativeUnavailableError(
            artifact.failure_reason or "S1 artifact is unavailable"
        )
    if artifact.key != key or dict(artifact.identity) != identity:
        raise S1NativeUnavailableError("S1 artifact descriptor is incompatible")
    directory = Path(artifact.directory)
    if directory.name != key:
        raise S1NativeUnavailableError("S1 artifact directory identity is incompatible")
    with _artifact_lock(directory.parent, key, exclusive=False):
        return _read_artifact(
            directory,
            key,
            identity,
            expected_manifest_sha256=artifact.manifest_sha256,
        )


def _ensure_s1_artifact(cache_directory: Path | None = None) -> S1Artifact:
    """Build once under an exclusive lock or load one compatible artifact."""

    support = s1_build_support()
    if not support.supported:
        raise S1NativeUnavailableError(support.reason)
    identity = s1_artifact_identity()
    key = s1_artifact_key(identity)
    root = _prepare_cache_root(cache_directory or s1_artifact_cache_directory())
    final = root / key
    with _ARTIFACT_REQUEST_LOCK:
        with _artifact_lock(root, key, exclusive=True):
            try:
                return _read_artifact(final, key, identity)
            except S1NativeUnavailableError:
                pass
            discarded: Path | None = None
            if final.exists():
                discarded = root / f".{key}.invalid-{uuid.uuid4().hex}"
                os.replace(final, discarded)
            stage = Path(tempfile.mkdtemp(prefix=f".{key}.build-", dir=root))
            try:
                _build_artifact(stage, key, identity)
                os.replace(stage, final)
                _fsync_directory(root)
                artifact = _read_artifact(final, key, identity)
            except Exception:
                shutil.rmtree(stage, ignore_errors=True)
                raise
            finally:
                if discarded is not None:
                    shutil.rmtree(discarded, ignore_errors=True)
            return artifact


def ensure_s1_artifact(cache_directory: Path | None = None) -> S1Artifact:
    """Return a compatible artifact or one typed fail-closed build error."""

    try:
        return _ensure_s1_artifact(cache_directory)
    except S1NativeUnavailableError:
        raise
    except OSError as error:
        raise S1NativeUnavailableError(
            f"validated S1 artifact publication failed: {type(error).__name__}"
        ) from error


def unavailable_s1_artifact(error: BaseException) -> S1Artifact:
    identity = s1_artifact_identity()
    return S1Artifact(
        available=False,
        key=s1_artifact_key(identity),
        directory=None,
        manifest_sha256=None,
        native_library_sha256=None,
        callback_artifact_sha256={},
        identity=identity,
        failure_type=type(error).__name__,
        failure_reason=str(error),
    )


def prepare_s1_artifact_for_workers() -> S1Artifact | None:
    """Create one spawn-safe descriptor, preserving fail-closed support."""

    if not s1_build_support().supported:
        return None
    try:
        return ensure_s1_artifact()
    except S1NativeUnavailableError as error:
        return unavailable_s1_artifact(error)


_ACTIVE_ARTIFACT: S1Artifact | None = None


def configure_s1_artifact(artifact: S1Artifact | None) -> None:
    """Select a parent-prepared descriptor for this process."""

    global _ACTIVE_ARTIFACT
    _ACTIVE_ARTIFACT = artifact


@lru_cache(maxsize=4)
def _validated_runtime_artifact(
    key: str,
    directory: str,
    manifest_sha256: str,
) -> S1Artifact:
    descriptor = S1Artifact(
        available=True,
        key=key,
        directory=directory,
        manifest_sha256=manifest_sha256,
        native_library_sha256=None,
        callback_artifact_sha256={},
        identity=s1_artifact_identity(),
    )
    return load_s1_artifact(descriptor)


def _runtime_artifact() -> S1Artifact:
    artifact = _ACTIVE_ARTIFACT
    if artifact is None:
        artifact = ensure_s1_artifact()
    if not artifact.available or artifact.directory is None or artifact.manifest_sha256 is None:
        raise S1NativeUnavailableError(
            artifact.failure_reason or "S1 artifact is unavailable"
        )
    return _validated_runtime_artifact(
        artifact.key,
        artifact.directory,
        artifact.manifest_sha256,
    )


@lru_cache(maxsize=4)
def _callbacks_for_artifact(key: str, directory: str):
    del key
    runtime_directory = tempfile.TemporaryDirectory(prefix="s1-callback-runtime-")
    runtime_cache = Path(runtime_directory.name) / S1_CALLBACK_CACHE
    try:
        shutil.copytree(Path(directory) / S1_CALLBACK_CACHE, runtime_cache)
        rhs, reset = _compile_callbacks(runtime_cache)
    except Exception as error:
        runtime_directory.cleanup()
        raise S1NativeUnavailableError(
            f"validated S1 callback load failed: {type(error).__name__}"
        ) from error
    rhs._s1_temporary_directory = runtime_directory
    reset._s1_temporary_directory = runtime_directory
    return rhs, reset


def _native_callbacks():
    """Reconstruct and retain process-local callback handles and addresses."""

    artifact = _runtime_artifact()
    return _callbacks_for_artifact(artifact.key, artifact.directory or "")


@lru_cache(maxsize=4)
def _library_for_artifact(key: str, directory: str):
    del key
    library_path = Path(directory) / S1_NATIVE_LIBRARY
    try:
        library = ctypes.CDLL(str(library_path))
    except OSError as error:
        raise S1NativeUnavailableError(
            f"validated S1 native load failed: {type(error).__name__}"
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
    return library


def native_library():
    """Load and retain the validated shared library in this process."""

    artifact = _runtime_artifact()
    return _library_for_artifact(artifact.key, artifact.directory or "")


def clear_s1_process_runtime() -> None:
    """Drop process-local handles for tests; published artifacts remain intact."""

    global _ACTIVE_ARTIFACT
    _ACTIVE_ARTIFACT = None
    _validated_runtime_artifact.cache_clear()
    _callbacks_for_artifact.cache_clear()
    _library_for_artifact.cache_clear()
    _runtime_build_provenance.cache_clear()


@lru_cache(maxsize=8)
def _runtime_build_provenance(
    key: str,
    available: bool,
    manifest_sha256: str | None,
    native_library_sha256: str | None,
    callback_artifact_sha256: tuple[tuple[str, str], ...],
    failure_type: str | None,
    failure_reason: str | None,
) -> dict[str, object]:
    callback_bundle_sha256 = hashlib.sha256(
        json.dumps(
            dict(callback_artifact_sha256),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "implementation": S1_EVALUATOR,
        "dop_source": S1_DOP_SOURCE_VERSION,
        "supported": s1_build_support().supported,
        "artifact": {
            "schema_version": S1_ARTIFACT_SCHEMA_VERSION,
            "key": key,
            "available": available,
            "manifest_sha256": manifest_sha256,
            "native_library_sha256": native_library_sha256,
            "callback_bundle_sha256": callback_bundle_sha256,
            "failure_type": failure_type,
            "failure_reason": failure_reason,
        },
    }


def s1_build_provenance(*, runtime_artifact: bool = False) -> dict[str, object]:
    """Return JSON-safe build and, when requested, actual artifact identity."""

    if runtime_artifact:
        artifact = _ACTIVE_ARTIFACT
        if artifact is None:
            try:
                artifact = _runtime_artifact()
            except S1NativeUnavailableError as error:
                artifact = unavailable_s1_artifact(error)
        return _runtime_build_provenance(
            artifact.key,
            artifact.available,
            artifact.manifest_sha256,
            artifact.native_library_sha256,
            tuple(sorted(artifact.callback_artifact_sha256.items())),
            artifact.failure_type,
            artifact.failure_reason,
        )
    identity = s1_artifact_identity()
    return {
        "implementation": S1_EVALUATOR,
        "dop_source": S1_DOP_SOURCE_VERSION,
        "build_flags": list(S1_BUILD_FLAGS),
        **asdict(s1_build_support()),
        "artifact": {
            "schema_version": S1_ARTIFACT_SCHEMA_VERSION,
            "key": s1_artifact_key(identity),
            "identity": identity,
        },
    }
