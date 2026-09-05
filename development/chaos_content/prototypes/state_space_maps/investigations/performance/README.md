# Performance investigations

## Current state

The authoritative current assessment is
[`reports/S1_POST_PROMOTION_PERFORMANCE.md`](reports/S1_POST_PROMOTION_PERFORMANCE.md).
S1 delivers approximately **11–12× warm successful-cell acceleration**, but the
measured field-level acceleration is materially smaller: **1.273× at 64²** and
**1.578× at 128²** for the bounded T=5 runs. Post-promotion analysis identified
repeated S1 initialization and lifecycle cost as the immediate optimization
target. Expensive `solve_ivp` fallback remains the major warm and asymptotic
compute bottleneck, especially at longer horizons.

The next engineering step is therefore **build-once/load-many validated S1
native and callback artifacts**, without changing the numerical or field policy.

## Investigation sequence

1. [Baseline performance audit](../../PERFORMANCE_AUDIT.md)
2. [Solver-boundary profile](s1_history/S1_SOLVER_BOUNDARY_PROFILE.md)
3. [S1 compiled-loop prototype](s1_history/S1_COMPILED_LOOP_PROTOTYPE.md)
4. [S1 promotion validation](s1_history/S1_PROMOTION_VALIDATION.md)
5. [Promoted field-level benchmark](reports/S1_FIELD_LEVEL_BENCHMARK.md)
6. [Post-promotion diagnosis](reports/S1_POST_PROMOTION_PERFORMANCE.md)

## Directory guide

- `reports/`: current field benchmark and latest performance conclusions.
- `tools/`: reusable current benchmark and diagnostic commands:
  `benchmark_s1_field_level.py`, `probe_s1_remaining_costs.py`, and
  `analyze_persisted_timings.py`.
- `s1_history/`: the S1 profile, prototype, validation harness, focused tests,
  and licensed prototype-native sources.
- `archive/`: superseded but reproducible one-off probes and the
  [earlier detailed investigation narrative](archive/PERFORMANCE_INVESTIGATION_HISTORY.md).
- `evidence/current/`: current field and post-promotion JSON evidence.
- `evidence/s1/`: route fixtures and S1 profile/prototype/validation evidence.
- `evidence/lifecycle/`: worker-lifetime and recycling evidence.

Historical JSON records retain the paths and source hashes captured when they
were produced. Reproduction commands and live script defaults use the organized
locations above.
