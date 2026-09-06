# Native DOP853 first-flip promotion candidate

## Decision

**READY FOR NATIVE FIELD-LEVEL A/B.** The production-integrated candidate and
the complete affected regression matrix are green. This is readiness for the
separate bounded field-level acceptance task, not final performance acceptance.
No repeated 64×64 A/B was run here.

## Architecture

The exact validated first-flip event loop now lives under `src/first_flip/native/`.
It uses the existing compiled four-state physical RHS and the licensed SciPy
DOP853 sources already vendored for Lyapunov S1. The field hierarchy is native
DOP853, then compiled-RHS plus `solve_ivp`, then the independent trusted Python
implementation. Ineligible specifications remain on the appropriate existing
route. Typed native initialization or numerical failures recover explicitly;
unexpected exceptions propagate.

Eligibility remains the exact unit/equal-link simple model, zero velocities,
T=5, and existing solver and diagnostic policy on the validated Darwin arm64
runtime/build. No equations, tolerances, event surfaces, root semantics,
censoring, diagnostics, grid, worker count, tiling, pool lifetime, persistence
schema, or scheduling policy changed.

## Dense source and artifacts

The original S1 `dop.c` is unchanged. The first-flip artifact builder verifies
its reviewed digest, creates a private staged copy, and applies only
`nfcn += 3` → `*nfcn += 3` for dense mode. The immutable shared library and
corrected source are atomically published under an exclusive lock and validated
from a manifest before loading. Corrupt/incomplete artifacts are quarantined and
rebuilt. Runtime libraries, callback handles/addresses, and integration state
remain process-local.

The compatibility key records native/event-loop, physical-kernel, original and
corrected DOP853, and licensing digests; compiler/flags/target; OS/platform;
Python ABI; NumPy, SciPy, Numba, llvmlite, and LLVM versions. Route 3 is distinct
from compiled route 2 and trusted route 1. This identity is in evaluator
provenance and therefore in the existing HDF5 definition checksum.

## Validation

The production candidate replayed all 37 saved cases against trusted Python
`solve_ivp`; 37/37 completed-valid cases passed with exact classification,
link/sign attribution, and event counts.

- maximum event-time difference: `6.66950938921218e-10 s` (gate `5e-8`)
- maximum event-state component difference: `5.96659771590069e-09` (gate `5e-7`)
- maximum triggering residual: `1.0658141036401503e-14` (gate `1e-10`)
- maximum normalized energy drift: `2.514179297794919e-10` (gate `5e-9`)
- maximum energy-drift difference: `1.5167866207945013e-10`
- maximum accepted angular increment: `0.12155300678055267` (strictly `<0.5`)
- maximum solver step: `0.00997735713772041 s`; censored endpoint error: `0`

Focused tests cover native/compiled/trusted selection, cold and cache-hit
artifacts, concurrent requests, corrupt and incompatible artifacts, typed
initialization/numerical recovery, unexpected exception propagation, the
37-case oracle replay, spawned execution, clean shutdown, same-definition
resume, and cross-definition rejection. The focused candidate/compiled/prototype
set passed `23` tests. The completed, non-duplicated affected regression matrix
passed `77` tests in `41.24 s`; it included production first-flip, field adapter,
generation/HDF5, persistence/resume, spawn behavior, compiled recovery,
operational runners, both current performance-investigation test modules, and
Experiment 020. No failures or candidate corrections were required during the
continuation. The valid 37-case evidence was inspected but not gratuitously
regenerated.

Reproduction:

```bash
PYTHONPATH=. uv run python -m development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.validate_first_flip_native_candidate
PYTHONPATH=. uv run pytest -q development/chaos_content/prototypes/state_space_maps/tests/first_flip/test_native_candidate.py development/chaos_content/prototypes/state_space_maps/tests/first_flip/test_compiled.py development/chaos_content/prototypes/state_space_maps/investigations/performance/tests/test_first_flip_native_dop853.py
PYTHONPATH=. uv run pytest -q development/chaos_content/prototypes/state_space_maps/tests/first_flip development/chaos_content/prototypes/state_space_maps/tests/generation development/chaos_content/prototypes/state_space_maps/tests/test_operational_runners.py development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/test_first_flip_event_contract.py development/chaos_content/prototypes/state_space_maps/investigations/performance/tests
```

Evidence: `evidence/current/first_flip_native_dop853_promotion_candidate.json`.
The remaining required activity is the deliberately separate three-pair 64×64
native-versus-compiled operational A/B; no final performance claim is made here.

Final verification also passed `git diff --check`. The S1 `dop.c`, `dop.h`,
`loop.c`, and `LICENSE_DOP` SHA-256 values remain exactly
`14b9fdce…d213`, `72549b52…9444`, `10137883…fbbb`, and `ed9bf58c…3357`,
respectively; the existing S1 source and build identity are untouched.
