# S1 build-once/load-many artifacts

Build-once/load-many S1 artifacts are correct and materially reduce repeated
initialization, so the implementation is retained. The bounded acceptance result
is nevertheless **not accepted overall**: median setup across eight recycled
pools fell from 21.427 s to 11.420 s (**46.70% lower**, passing the 40% gate),
but median 128² T=5 end-to-end wall fell from 43.628 s to 37.838 s (**13.27%
lower**, failing the 20% gate).

All three paired fields were bitwise identical to the trusted operational route.
Routes, statuses, retained RHS counts, worker policy, persistence, and numerical
policy were unchanged. All workers stopped and peak promoted worker RSS was
1.71% below the established promoted baseline.

## Implementation architecture

`src/lyapunov/s1_artifacts.py` owns artifact construction, validation,
publication, loading, and process-local reconstruction. The parent coordinator
prepares one spawn-safe descriptor in `lyapunov_evaluator_binding`; every worker
receives that descriptor through the existing initializer arguments and loads
the same published build. No generation runner, pool-lifetime, worker-count, or
start-method policy changed.

The reusable artifact contains only:

- the compiled native DOP853 shared library;
- Numba cache files for the RHS and reset callbacks; and
- a manifest containing the complete compatibility identity and SHA-256 digest
  of every published file.

Each spawned process validates the descriptor and manifest, copies the immutable
callback cache into a process-local temporary directory, recreates the Numba
callback objects and their addresses there, and loads its own `ctypes.CDLL`
handle. Function pointers, callback objects, solver state, integration state,
mutable arrays, and cell results are never published or reused. Process-local
handles and temporary callback directories end with the worker and are also
clearable by the focused test helper.

## Artifact identity and integrity

The cache key is SHA-256 over canonical JSON containing the native-source and
callback-source digests, S1 artifact/runtime and compiled-RHS implementation
digests, DOP853 source identity, compiler executable/version/target/flags,
architecture, operating system, Python version/implementation/cache tag/ABI,
and NumPy, SciPy, Numba, llvmlite, and LLVM versions. Existing S1 build support
and specification eligibility remain fail-closed and unchanged in scope.

Publication uses a per-key advisory file lock plus an in-process lock. A builder
works in a private staging directory, writes and fsyncs the manifest last, then
atomically renames the completed directory into place and fsyncs its parent.
Readers hold a shared lock while validating the exact expected manifest digest,
identity, complete file set, regular-file constraints, and every file digest.
An incomplete, corrupt, stale, unsafe, or incompatible artifact cannot be loaded.
Under the exclusive lock it is moved aside, rebuilt, and removed only after the
replacement is published. Concurrent requests therefore cannot observe partial
publication or publish conflicting products.

Artifact construction or load failure becomes an unavailable S1 descriptor or
`S1NativeUnavailableError`. The operational evaluator then follows its existing
trusted recovery route. No fallback decision is inferred from an error string,
and the trusted compiled-DOP853 and `solve_ivp` fallback behavior is unchanged.

## Provenance and persistence

Field provenance records the complete deterministic artifact identity and key.
Accepted and recovered cell records carry a compact exact artifact record:
implementation, schema/key, availability, manifest digest, native-library
digest, callback-bundle digest, and any typed artifact failure. This distinguishes
the actual S1 artifact from trusted-fast and `solve_ivp` results without storing
cache paths or process-local addresses.

The artifact identity participates in the existing field-definition checksum,
so compatible runs resume normally and incompatible implementation/build
identities continue to fail closed. The HDF5 schema and checksum algorithm were
not changed. Focused tests cover stable provenance independent of cache location,
resume compatibility, recovered-attempt provenance, and trusted routing after
artifact failure.

## Reproduction and environment

Run from the repository root. The command refuses to overwrite existing JSON,
uses a fresh cache for every lifecycle repetition and promoted field pair, and
removes temporary HDF5 fields after authoritative read-back comparison.

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m \
development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.benchmark_s1_artifact_reuse
```

The final evidence is
`../evidence/current/s1_build_once_load_many.json`. Two earlier complete runs are
retained as `s1_build_once_load_many_attempt1.json` and
`s1_build_once_load_many_attempt2.json`; they exposed avoidable per-cell artifact
provenance construction, which was replaced by one process-local immutable
provenance record before the final run. No numerical path was changed.

| Component | Value |
| --- | --- |
| Platform | macOS 15.7.9, ARM64 |
| Python | 3.12.3 |
| NumPy | 2.5.2 |
| SciPy | 1.18.0 |
| Numba | 0.67.0 |
| llvmlite / LLVM | 0.49.0 / 22.1.0 |
| Compiler | Apple Clang 17.0.0 (`clang-1700.6.4.2`) |
| Compiler target | `arm64-apple-darwin24.6.0` |
| S1 flags | `-O2 -ffp-contract=on -fPIC -shared` |
| Field | 128×128, T=5, 8×8 tiles |
| Process policy | spawn, four workers, chunksize one, 2,048 returned cells/pool |

The evidence records Git HEAD/status, complete identities, source hashes, raw
worker timings, PIDs, RSS, routes, statuses, diagnostics, and equality results.

## Pool-lifecycle result

The established pre-reuse 128²-equivalent setup measurement is 21.427 s for
eight pools. Three build-once/load-many repetitions produced:

| Repetition | First cold preparation | Effective eight-pool setup | Warm pool setup median | Worker initialization median | Worker initialization range |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.856 s | 11.969 s | 1.312 s | 0.124 s | 0.121–0.400 s |
| 2 | 0.488 s | 11.420 s | 1.322 s | 0.129 s | 0.120–0.286 s |
| 3 | 0.476 s | 11.099 s | 1.306 s | 0.123 s | 0.119–0.293 s |

The first truly cold build cost was 0.856 s. Later pools loaded the already
published compatible artifact; their median worker initialization was about
0.123 s rather than the previously diagnosed 1.3–1.6 s rebuild cost. All 96
spawned lifecycle workers stopped.

## Three paired 128² fields

Orders were S1/trusted, trusted/S1, then S1/trusted. Each promoted run includes
its first artifact creation in outer wall time.

| Pair | Promoted wall | Promoted cells/s | Trusted wall | Paired speedup | Promoted setup + cold build | Promoted evaluation |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 36.860 s | 444.490 | 72.215 s | 1.959× | 11.390 s | 20.526 s |
| 2 | 37.838 s | 433.002 | 67.341 s | 1.780× | 11.693 s | 21.013 s |
| 3 | 40.198 s | 407.587 | 66.733 s | 1.660× | 12.468 s | 22.646 s |

Median promoted outer wall was 37.838 s, versus the established promoted
baseline of 43.628 s. The benchmark's required baseline-relative improvement is
therefore 13.27%, even though paired speedups against the forced trusted route
range from 1.660× to 1.959×.

Every run completed 16,384 valid cells with no invalid or execution-error cell.
Each promoted field contained 15,654 accepted S1 results and 730 accepted
`compiled_rhs_solve_ivp_fallback` recoveries; each trusted field contained
15,654 trusted-fast and the identical 730 fallback cells. Retained accepted-result
RHS evaluations were exactly 109,507,382 for every route. For all three pairs:

- axes, statuses, fallback masks, and routes matched exactly;
- values were bitwise identical, including NaNs;
- maximum absolute rate difference was 0 /s, with zero cells exceeding the
  existing 1e-8 /s tolerance; and
- the promoted S1 mask exactly matched the trusted-fast mask.

Maximum promoted worker peak RSS was 242,696,192 bytes, versus the established
246,923,264-byte baseline (ratio 0.9829). All lifecycle and field workers stopped;
no worker leak was observed.

## Validation

```text
177 passed in 31.67s
```

This combined the state-space-map production tests with the focused S1-history
tests. It covers artifact cold/warm/repeated loads, process and thread
concurrency, callback reconstruction, incomplete/atomic publication, corruption,
stale identity, unsupported builds, provenance, trusted recovery, cleanup,
generation, persistence/resume, operational behavior, and existing S1 cases.

The existing seven-repetition promotion validation also passed: 104/104 cases
at each of T=1, 2, 5, 10, and 20; 240/240 prefix traces; all robustness cases;
zero rate, cycle-log, final-reference, final-tangent, and norm-diagnostic errors;
and a worst energy-diagnostic difference of 3.622e-16. No tolerance was changed.

## Acceptance and remaining bottleneck

| Gate | Result |
| --- | --- |
| Eight-pool setup at least 40% lower | **PASS** — 46.70% lower |
| 128² wall at least 20% lower | **FAIL** — 13.27% lower |
| Scientific/status/route equality | **PASS** |
| No worker leaks | **PASS** |
| Worker RSS increase no more than 10% | **PASS** — 1.71% lower |

The mechanism is retained because it removes redundant compilation, is
fail-closed, passes scientific validation, and cuts measured setup materially.
The overall acceptance result remains failed. Initialization is no longer the
only field-scale limiter: the unchanged expensive `solve_ivp` recoveries and
their tile tails remain the dominant warm compute cost. This task deliberately
does not optimize that path or scheduling.

## Files changed

- `src/lyapunov/s1_artifacts.py`: artifact identity, build/load, integrity,
  concurrency, process-local reconstruction, and provenance.
- `src/lyapunov/s1.py`: use the artifact-backed native library/callback handles;
  numerical loop and eligibility remain unchanged.
- `src/lyapunov/field_adapter.py`: prepare once in the parent and configure each
  existing worker initializer.
- `tests/lyapunov/test_s1_artifacts.py` and
  `tests/lyapunov/test_field_adapter.py`: focused artifact, recovery, provenance,
  persistence, and reconstruction coverage.
- `investigations/performance/tools/benchmark_s1_artifact_reuse.py`: bounded
  lifecycle and alternating-order field acceptance tool.
- `investigations/performance/evidence/current/s1_build_once_load_many*.json`:
  final and retained diagnostic evidence.
- this report and `investigations/performance/README.md`: current conclusion and
  navigation.

NEXT: reassess S1 initialization amortisation before fallback optimisation
