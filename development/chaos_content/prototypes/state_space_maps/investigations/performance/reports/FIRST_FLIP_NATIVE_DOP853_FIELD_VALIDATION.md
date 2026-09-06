# Native DOP853 first-flip field validation

## Corrected-build final decision

**PROMOTE NATIVE FIRST-FLIP DEFAULT.** The first-flip-specific v2 build passed
every scientific, operational, route, and performance gate. The ordinary
eligible T=5 unit/equal-link zero-velocity definition now selects native
DOP853, retaining compiled-RHS + `solve_ivp` and trusted Python as explicit
recovery routes. Eligibility and all numerical policy are unchanged.

The v2 artifact stages four explicit differences from the unchanged S1
vendored input: the prior dense-counter pointer correction, strict terminal
horizon clamping, the `fac11 / safe` rejection factor, and controller bounds
0.2 / 10. Route and implementation identities are
`native_dop853_first_flip_v2` and
`first_flip_native_dop853_event_loop_v2`; artifact schema 2, the correction
set, controller settings, corrected DOP853 digest
`f013d13d46f84b5b18ff7c1e64169bdce442afdd642f2fedae1c63a187c3d337`,
and first-flip loop digest
`7d55721cb3bf7385f85c798a30fa1ba4894db5bc0b31471aced9a43b6ad892c8`
make prior artifacts and persisted definitions incompatible by construction.

### Corrected scientific and regression validation

The saved 37-case production comparison passed 37/37 against independent
trusted Python `solve_ivp`:

- maximum event-time difference: `5.062616992290714e-14 s`;
- maximum event-state component difference: `1.6145973447123652e-12`;
- maximum triggering residual: `1.2434497875801753e-14`;
- maximum normalized energy drift: `2.100683503766073e-10`;
- maximum normalized energy-drift difference: `1.3037481390084807e-14`;
- maximum accepted angular increment: `0.12142339598095131`;
- maximum accepted solver step: `0.00997735713772041 s` for declared
  `0.009977357137720327 s` (floating-point roundoff within the existing
  `2e-14 s` validation allowance);
- censored endpoint error: zero.

The complete affected matrix passed `80` tests. This covers production
first-flip, field generation/HDF5, persistence/resume, spawn, fallback,
operational runners, Experiment 020, and performance-investigation tests.
After switching the eligible default, the default-dispatch and default native
spawn/resume checks also passed.

```bash
MPLCONFIGDIR=/tmp/codex-mpl-cache NUMBA_CACHE_DIR=/tmp/codex-numba-cache .venv/bin/python -m pytest -q development/chaos_content/prototypes/state_space_maps/tests/first_flip development/chaos_content/prototypes/state_space_maps/tests/generation development/chaos_content/prototypes/state_space_maps/tests/test_operational_runners.py development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/test_first_flip_event_contract.py development/chaos_content/prototypes/state_space_maps/investigations/performance/tests
.venv/bin/python -m development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.validate_first_flip_native_candidate --output development/chaos_content/prototypes/state_space_maps/investigations/performance/evidence/current/first_flip_native_dop853_corrected_validation.json
```

### Corrected 64×64 operational A/B

The environment and field definition match the original run below. A fresh
temporary native/Numba cache was used and run order remained N/C, C/N, N/C.

| Pair/order | Route | Wall (s) | cells/s | Setup (s) | Evaluation (s) | Persistence (s) | Shutdown (s) | Peak worker RSS |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 N/C | Native v2 | 5.838 | 701.6 | 3.177 | 0.976 | 0.170 | 0.852 | 238,321,664 B |
| 1 N/C | Compiled solve_ivp | 30.222 | 135.5 | 2.653 | 26.245 | 0.174 | 0.870 | 224,509,952 B |
| 2 C/N | Compiled solve_ivp | 32.587 | 125.7 | 2.932 | 28.287 | 0.188 | 0.896 | 224,264,192 B |
| 2 C/N | Native v2 | 4.914 | 833.5 | 2.816 | 0.886 | 0.165 | 0.748 | 225,198,080 B |
| 3 N/C | Native v2 | 5.345 | 766.4 | 3.197 | 0.856 | 0.167 | 0.812 | 227,360,768 B |
| 3 N/C | Compiled solve_ivp | 31.016 | 132.1 | 3.244 | 26.550 | 0.178 | 0.757 | 224,952,320 B |

Paired whole-field speedups were `5.177×`, `6.631×`, and `5.803×`; median
`5.803×`. Evaluation-only speedups were `26.886×`, `31.943×`, and `31.021×`;
median `31.021×`.

Every field had 4,096 completed-valid cells: 1,742 observed and 2,354 censored,
with zero invalid or execution-error cells. Axes, status arrays, and
observed/censored masks were identical. Maximum observed event-time difference
was `7.721707642648554e-12 s`. Each native field recorded exactly 4,096
`native_dop853_first_flip_v2` cells, zero compiled recoveries, and zero trusted
recoveries; each comparison field recorded exactly 4,096
`numba_rhs_solve_ivp_first_flip_v1` cells. All authoritative validations and
stricter trusted-Python spots passed, every run used two pools/one recycle, and
all workers stopped cleanly.

```bash
MPLCONFIGDIR=/tmp/codex-mpl-cache .venv/bin/python -m development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.benchmark_first_flip_native_field_validation --output development/chaos_content/prototypes/state_space_maps/investigations/performance/evidence/current/first_flip_native_corrected_field_validation_64.json
```

Corrected evidence is preserved separately in
`../evidence/current/first_flip_native_dop853_corrected_validation.json` and
`../evidence/current/first_flip_native_corrected_field_validation_64.json`.
The original failed v1 evidence and analysis below are retained as promotion
history.

## Original v1 decision

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
