# S1 promoted field-level benchmark

The promoted S1 path preserves the trusted persisted field exactly on both
bounded grids and improves complete field-creation throughput. At `64 x 64`,
end-to-end creation is **1.273x faster** and the tile-evaluation phase is
**2.199x faster**. Because that run completed quickly and passed all comparison
gates, the permitted `128 x 128` confirmation was also run; end-to-end creation
is **1.578x faster** and tile evaluation is **2.909x faster** there.

No numerical policy, S1 eligibility, fallback logic, provenance,
multiprocessing policy, persistence, rendering, or production implementation
was changed for this benchmark. No `512 x 512` or larger field was run.

## Reproduction

Run from the repository root. Each command refuses to overwrite its JSON
artifact. The two HDF5 fields are created in a temporary directory, read back
and compared, hashed into the JSON evidence, and then removed.

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m \
development.chaos_content.prototypes.state_space_maps.investigations.performance.benchmark_s1_field_level \
  --samples-per-axis 64 \
  --duration 5 \
  --output development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_field_level_benchmark_64.json
```

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m \
development.chaos_content.prototypes.state_space_maps.investigations.performance.benchmark_s1_field_level \
  --samples-per-axis 128 \
  --duration 5 \
  --output development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_field_level_benchmark_128.json
```

The execution order was promoted S1 followed by forced pre-S1 trusted hybrid.
The forced comparison binding calls the unchanged
`evaluate_renormalized_tangent_hybrid` directly. Both routes use the same
periodic coordinates, physical and numerical specification, `8 x 8` tiling,
HDF5 transaction/checksum path, and accepted process policy: four spawn
workers, chunksize one, and at most 2,048 returned cells per pool.

## Environment

Both measurements were made on 2026-09-05 at Git HEAD
`0d92f841468c9ad95fa78d2d180dc711d9a58f40`, the committed S1 promotion. The
JSON records the benchmark-only untracked files present for each run.

| Component | Value |
| --- | --- |
| Platform | macOS 15.7.9, ARM64 |
| Python | 3.12.3 |
| NumPy | 2.5.2 |
| SciPy | 1.18.0 |
| Numba | 0.67.0 |
| Compiler | Apple Clang 17.0.0 (`clang-1700.6.4.2`) |
| Compiler target | `arm64-apple-darwin24.6.0` |
| S1 flags | `-O2 -ffp-contract=on -fPIC -shared` |
| Duration | 5 s |

The JSON artifacts retain the complete S1 build/source identity, source hashes,
Git status, HDF5 hashes, numerical parameters, and raw runner phase results.

## Field-level performance

The outer wall time surrounds the complete `create` call, including initial
HDF5 creation. Runner time begins immediately after creation and includes
resume discovery, pool lifecycle, cell evaluation, persistence, final
validation, and resume-state discovery. Reported cells/s below use the outer
wall time.

| Grid / route | Cells | Outer wall | Cells/s | Runner total | Setup | Tile evaluation | Persistence | Shutdown | Pools |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 64 promoted S1 | 4,096 | 12.124 s | 337.840 | 12.117 s | 5.846 s | 5.027 s | 0.176 s | 0.823 s | 2 |
| 64 trusted pre-S1 | 4,096 | 15.434 s | 265.391 | 15.431 s | 2.976 s | 11.056 s | 0.158 s | 0.993 s | 2 |
| 128 promoted S1 | 16,384 | 43.628 s | 375.542 | 43.621 s | 21.427 s | 17.319 s | 0.648 s | 3.288 s | 8 |
| 128 trusted pre-S1 | 16,384 | 68.845 s | 237.984 | 68.841 s | 12.772 s | 50.384 s | 0.737 s | 4.010 s | 8 |

| Grid | Outer-wall speedup | Runner-total speedup | Tile-evaluation speedup |
| --- | ---: | ---: | ---: |
| 64 x 64 | **1.273x** | 1.274x | 2.199x |
| 128 x 128 | **1.578x** | 1.578x | 2.909x |

S1 worker setup is intentionally included. It is higher because each fresh
spawn pool performs the validated native build and lazy callback compilation;
the unchanged 2,048-cell recycling policy creates two pools at 64 and eight at
128. The larger grid amortises that fixed cost more effectively. No policy was
tuned in response to these measurements.

## Scientific and persisted comparison

Both HDF5 artifacts were reopened through the authoritative reader. The
existing absolute rate tolerance remains `1e-8 /s`.

| Comparison | 64 x 64 | 128 x 128 |
| --- | ---: | ---: |
| Axes identical | yes | yes |
| Status arrays identical | yes | yes |
| Values bitwise identical, including NaNs | yes | yes |
| Maximum absolute value difference | 0 /s | 0 /s |
| Cells exceeding `1e-8 /s` | 0 | 0 |
| Fallback masks identical | yes | yes |
| Promoted S1 mask equals trusted-fast mask | yes | yes |
| Completed-invalid cells | 0 | 0 |
| Execution-error cells | 0 | 0 |
| Comparison accepted | yes | yes |

The retained-result solver RHS totals are also identical between routes:

| Grid | Promoted S1 RHS evaluations | Trusted RHS evaluations |
| --- | ---: | ---: |
| 64 x 64 | 27,405,702 | 27,405,702 |
| 128 x 128 | 109,507,382 | 109,507,382 |

These totals describe the result retained for each cell. They deliberately do
not add the work from a rejected S1 attempt before trusted recovery, because the
existing tile diagnostic contract reports the accepted result's diagnostics.

## Route and provenance distribution

| Grid / route | Accepted S1 | Trusted fast | solve_ivp fallback | S1 attempts recovered | Invalid | Failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 64 promoted | 3,886 | 0 | 210 | 210 | 0 | 0 |
| 64 trusted | 0 | 3,886 | 210 | 0 | 0 | 0 |
| 128 promoted | 15,654 | 0 | 730 | 730 | 0 | 0 |
| 128 trusted | 0 | 15,654 | 730 | 0 | 0 | 0 |

The promoted fallback shares are 5.127% at 64 and 4.456% at 128. Every promoted
fallback records `s1_native_dop853_v1` as an attempted evaluator and
`s1_execution_error` as the recovery reason. The accepted persisted route is
still `compiled_rhs_solve_ivp_fallback`, matching the trusted field cell for
cell. The trusted-fast count and promoted-S1 count are identical on each grid.

Promoted HDF5 files are larger because the checksummed exceptional-cell records
retain S1 attempt/build provenance for recovered cells: 494,376 versus 339,192
bytes at 64, and 1,894,903 versus 1,323,759 bytes at 128. This is the already
promoted provenance contract, not a benchmark-specific change.

## Limitations

- This is one create run per route and resolution on one validated machine, not
  a randomized or repeated field-level timing study. The fixed promoted-first
  order and ambient system load may affect timing.
- The benchmark establishes equality on two deterministic full-periodic grids
  at T=5. It does not extend S1 eligibility or establish other durations,
  platforms, compilers, or dependency builds.
- The 64 and 128 fields exercise spawn startup, tiling, persistence, pool
  recycling, S1 success, and verified solve_ivp fallback, but they do not model
  the total runtime or route distribution of a 512 or larger field.
- Temporary HDF5 products were intentionally removed after comparison. Their
  SHA-256 hashes and full persisted summaries remain in the JSON artifacts;
  use `--work-directory` on a rerun to retain both fields for inspection.
- Rendering was not invoked because it is downstream of the identical,
  validated HDF5 arrays and outside the throughput question.

## Decision

The promoted operational S1 route passes the bounded field-level correctness
gate and produces a material real-run improvement. The result supports retaining
the current promotion unchanged; it does not justify a numerical,
multiprocessing, persistence, or eligibility-policy change.
