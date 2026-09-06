# Performance investigations

## Current state

The authoritative current assessment is
[`reports/S1_BUILD_ONCE_LOAD_MANY.md`](reports/S1_BUILD_ONCE_LOAD_MANY.md).
S1 delivers approximately **11–12× warm successful-cell acceleration**, but the
measured field-level acceleration is materially smaller. Build-once/load-many
artifacts reduced eight-pool setup by **46.7%**, while the paired 128² T=5
experiment improved median end-to-end wall by only **13.3%**, short of its 20%
acceptance gate. Expensive `solve_ivp` fallback remains the major warm and
asymptotic compute bottleneck, especially at longer horizons.

The next engineering step is to reassess S1 initialization amortisation before
starting fallback optimization; the artifact mechanism is retained because it
is correct, fail-closed, and materially reduces repeated initialization.

For first flip, the validated compiled four-state RHS is now the guarded default
for the standard T=5 unit-parameter field. The
[promotion report](reports/FIRST_FLIP_COMPILED_RHS_PROMOTION.md) records clean
scientific/operational validation and a **2.170× median 64² end-to-end speedup**;
unsupported and ineligible definitions retain the trusted Python RHS. The
[post-promotion profile](reports/FIRST_FLIP_POST_PROMOTION_PROFILE.md) finds the
remaining cost concentrated in Python DOP853 stepping/event detection and
recommends one narrow compiled solver/event-loop prototype. The subsequent
[native DOP853 prototype](reports/FIRST_FLIP_NATIVE_DOP853_PROTOTYPE.md) passed
all scientific gates. The subsequent
[production promotion candidate](reports/FIRST_FLIP_NATIVE_DOP853_PROMOTION_CANDIDATE.md)
preserved those gates. The subsequent
[bounded field validation](reports/FIRST_FLIP_NATIVE_DOP853_FIELD_VALIDATION.md)
measured a strong `5.123×` median whole-field speedup, but rejected default
promotion because 62 cells per field required max-step recovery and the maximum
native/compiled event-time difference exceeded the existing gate. The compiled
RHS + `solve_ivp` route remains the operational default.

## Investigation sequence

1. [Baseline performance audit](../../PERFORMANCE_AUDIT.md)
2. [Solver-boundary profile](s1_history/S1_SOLVER_BOUNDARY_PROFILE.md)
3. [S1 compiled-loop prototype](s1_history/S1_COMPILED_LOOP_PROTOTYPE.md)
4. [S1 promotion validation](s1_history/S1_PROMOTION_VALIDATION.md)
5. [Promoted field-level benchmark](reports/S1_FIELD_LEVEL_BENCHMARK.md)
6. [Post-promotion diagnosis](reports/S1_POST_PROMOTION_PERFORMANCE.md)
7. [Build-once/load-many implementation and acceptance](reports/S1_BUILD_ONCE_LOAD_MANY.md)

First-flip lineage: [feasibility](reports/FIRST_FLIP_COMPILED_RHS_FEASIBILITY.md)
→ [pre-promotion review](reports/FIRST_FLIP_PRE_PROMOTION_REVIEW.md) →
[promotion](reports/FIRST_FLIP_COMPILED_RHS_PROMOTION.md) →
[post-promotion profile](reports/FIRST_FLIP_POST_PROMOTION_PROFILE.md) →
[native DOP853 prototype](reports/FIRST_FLIP_NATIVE_DOP853_PROTOTYPE.md) →
[production promotion candidate](reports/FIRST_FLIP_NATIVE_DOP853_PROMOTION_CANDIDATE.md) →
[bounded field validation](reports/FIRST_FLIP_NATIVE_DOP853_FIELD_VALIDATION.md).

## Directory guide

- `reports/`: current field benchmark and latest performance conclusions.
- `tools/`: reusable current benchmark and diagnostic commands:
  `benchmark_s1_artifact_reuse.py`, `benchmark_s1_field_level.py`,
  `probe_s1_remaining_costs.py`, `analyze_persisted_timings.py`, and bounded
  first-flip compiled-RHS feasibility and promotion tooling.
- `tests/`: focused checks for current investigation-only prototypes.
- `s1_history/`: the S1 profile, prototype, validation harness, focused tests,
  and licensed prototype-native sources.
- `archive/`: superseded but reproducible one-off probes and the
  [earlier detailed investigation narrative](archive/PERFORMANCE_INVESTIGATION_HISTORY.md).
- `evidence/current/`: current field, post-promotion, and artifact-acceptance
  JSON evidence. The numbered artifact attempts are retained to show the bounded
  diagnosis that removed per-cell provenance construction overhead.
- `evidence/s1/`: route fixtures and S1 profile/prototype/validation evidence.
- `evidence/lifecycle/`: worker-lifetime and recycling evidence.

Historical JSON records retain the paths and source hashes captured when they
were produced. Reproduction commands and live script defaults use the organized
locations above.
