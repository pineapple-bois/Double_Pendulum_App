# Native DOP853 first-flip field validation

## Decision

**KEEP COMPILED-RHS SOLVE_IVP DEFAULT.** The native candidate exceeded the
performance gate, but failed two mandatory operational/scientific gates: every
native field recovered 62 cells through compiled-RHS + `solve_ivp`, and the
maximum native/compiled observed event-time difference was `7.913799e-8 s`,
above the unchanged `5e-8 s` limit.

The candidate remains available only through the explicit
`enable_native_candidate=True` investigation switch. Normal field execution
selects the previously promoted compiled-RHS + `solve_ivp` route. No DOP853,
tolerance, event, multiprocessing, persistence, or rendering policy was changed
to rescue the result.

## Environment and workload

The benchmark ran on Darwin arm64/macOS 15.7.9 with Python 3.12.3, NumPy 2.5.2,
SciPy 1.18.0, and Numba 0.67.0. Each create used the same 64×64 periodic grid,
unit/equal-link simple model, zero velocities, T=5, DOP853 tolerances and
`max_step`, four spawn workers, 8×8 tiles, and 2,048-cell pool lifetime. Each
field used two pools with one recycling event. Orders were N/C, C/N, N/C. Fresh
native and Numba cache roots made the first native run cold.

```bash
PYTHONPATH=. uv run python -m development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.benchmark_first_flip_native_field_validation
```

## Measurements

Wall is the outer create wall; component timings come from the operational
runner.

| Pair/order | Route | Wall (s) | cells/s | Setup (s) | Evaluation (s) | Persistence (s) | Shutdown (s) | Peak worker RSS |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 N/C | Native candidate | 6.587 | 621.9 | 3.250 | 1.512 | 0.156 | 0.793 | 237,191,168 B |
| 1 N/C | Compiled solve_ivp | 27.043 | 151.5 | 2.770 | 23.066 | 0.158 | 0.770 | 223,559,680 B |
| 2 C/N | Compiled solve_ivp | 29.129 | 140.6 | 2.583 | 25.315 | 0.174 | 0.766 | 223,903,744 B |
| 2 C/N | Native candidate | 5.686 | 720.4 | 2.848 | 1.585 | 0.170 | 0.787 | 225,247,232 B |
| 3 N/C | Native candidate | 5.527 | 741.2 | 2.752 | 1.550 | 0.163 | 0.779 | 225,918,976 B |
| 3 N/C | Compiled solve_ivp | 30.280 | 135.3 | 2.627 | 26.437 | 0.182 | 0.752 | 224,346,112 B |

Paired whole-field speedups were `4.106×`, `5.123×`, and `5.479×`; median
`5.123×`. Evaluation-only speedups were `15.257×`, `15.975×`, and `17.054×`;
median `15.975×`. Performance passed the required `1.5×` gate.

## Correctness and routes

All six authoritative field validations and all stricter trusted-Python spot
checks passed, and every worker stopped. Each field contained 1,742 observed and
2,354 censored completed-valid cells, with zero invalid or execution-error
cells. Axes, status arrays, observed masks, and censor masks were identical in
every pair. Persisted per-cell event attribution is not part of the HDF5 schema;
the unchanged adapter semantics and stricter oracle checks were used.

Compiled comparison fields recorded exactly 4,096
`numba_rhs_solve_ivp_first_flip_v1` cells. Native candidate fields recorded
4,034 `native_dop853_first_flip_v1` cells and 62 compiled recovery cells, with no
trusted-Python cells. The intended native-only route distribution therefore
failed.

Bounded diagnosis showed all 62 recoveries came from the existing fail-closed
max-step check. The vendored DOP853 final-step rule may combine the residual
horizon into a last accepted step up to roughly 1% above the declared cap; the
candidate correctly rejects those attempts. Changing that integrator behavior
requires a separate numerical implementation and validation task and was out of
scope. Independently, the paired persisted fields had a maximum observed event-
time difference of `7.913799454902159e-8 s`, exceeding `5e-8 s`.

Checksums and structural validation passed for all fields. Different HDF5 file
hashes are expected because route/provenance definitions are deliberately
distinct. Evidence:
`../evidence/current/first_flip_native_field_validation_64.json`.

## Acceptance

- Axes/status/observed/censor equality: pass.
- Observed event-time gate: fail.
- Authoritative validation and stricter spots: pass.
- Worker lifecycle: pass; two pools/run, one recycle/run, all stopped.
- No unexpected fallback: fail; 62 compiled recoveries per native field.
- Median whole-field speedup ≥1.5×: pass at 5.123×.
- Final promotion acceptance: fail.

No large field was run and no further optimization was attempted.
