# S1 compiled single-cell loop prototype

The working experiment passes the existing scientific comparison gates and the
requested warm-performance threshold on this machine: **12.26× at T=5 and 12.63×
at T=20**, measured as the median of seven per-cell speedups. It remains isolated
under `investigations/performance/`; no production evaluator was changed or
integrated, and no field was run.

## Scope and implementation

This implements S1 from `../../../PERFORMANCE_AUDIT.md`, following
`S1_SOLVER_BOUNDARY_PROFILE.md`. It does not investigate other optimisation paths.
The trusted comparison is the operational
`../../../src/lyapunov/compiled_dop853.py::evaluate_renormalized_tangent_compiled_dop853`.
Full scientific records are compared through its underlying
`run_renormalized_tangent_compiled_dop853` runner.

The experiment changes the boundary from thousands of Python callbacks per cell
to one `ctypes` call per cell:

1. `s1_compiled_loop.py::run_compiled_loop` constructs the specification-dependent
   arrays, initial Candidate-A unit tangent and cycle boundaries in Python.
2. `native/loop.c::s1_loop` runs every renormalisation segment in C, calling an
   **unchanged copy of SciPy 1.18.0's native DOP853 implementation**.
3. `_rhs`, a Numba `cfunc`, calls the existing production
   `compiled.py::compiled_reference_and_tangent_rhs` directly from native code.
   The equations and Jacobian-vector product are imported, not rewritten.
4. `loop.c::observe` checks every accepted state, reduces energy drift, and
   checks time ordering and the largest accepted-step gap in native code.
   Accepted-state Python lists, per-step copies and Python RHS counters disappear.
5. `_reset`, another Numba `cfunc`, performs Candidate-A tangent normalisation and
   reference-angle rebasing. C accumulates the log stretches and finite-time rates.
6. Python constructs the existing result/diagnostic types once after the loop.
   `evaluate_compiled_loop` uses the same neutral evaluator adapter as production.

The Numba callbacks execute native code, not a `ctypes` Python callback. The
existing RHS still allocates its small result array; removing that allocation is
outside this experiment. No Python code executes once per RHS, accepted step or
renormalisation cycle in the experimental loop.

### Preserved numerical contract

| Item | Experimental treatment |
| --- | --- |
| Solver | Exact vendored SciPy 1.18.0 DOP853 C source; no tableau/controller edits |
| Defaults | rtol `1e-9`, atol `1e-11`; values passed from the original spec |
| Maximum step | Original `_resolved_interval_max_step`; default `0.009977357137720327` seconds |
| Controller | Safety `0.9`, decrease factor `0.3`, increase factor `6`, beta `0`, automatic first step |
| Restart policy | Fresh solver work arrays at every original renormalisation boundary |
| Step budget | Original `100000` per segment; native stiffness checks retained |
| Endpoint policy | Original native `1.01*h` endpoint handling retained, including its possible max-step rejection |
| Observation | Initial state and every accepted step, as in the trusted fast runner |
| Renormalisation | Original interval `0.25` seconds, Candidate-A geometry and initial tangent |
| Angle chart | Physical angles only, wrapped to `(-pi, pi]`; tangent is not angle-wrapped |
| Energy gate | Maximum drift over all accepted reference states; original energy scale and limit `1e-7` |
| Tangent gate | Maximum post-renormalisation norm error; original limit `1e-12` |
| Observable | Sum of natural-log stretches divided by elapsed observation time |
| Failures | Native non-success, bad observations, endpoint and max-step failures raise; no fallback |

The operational fast segment solver uses the requested sampling array's
**endpoints**, observing accepted steps rather than uniform interior samples.
This experiment preserves that actual policy; it does not introduce a different
sampling grid or reduce accepted-step energy coverage. The sampling specification
is retained. A focused test checks the existing interior-sampling invariance.
The original solve_ivp fallback, routing and scientific policy are untouched.

### Exact solver source and build

`native/dop.c` and `dop.h` are byte-for-byte copies of these upstream files:

- [SciPy v1.18.0 dop.c](https://github.com/scipy/scipy/blob/v1.18.0/scipy/integrate/src/dop.c)
- [SciPy v1.18.0 dop.h](https://github.com/scipy/scipy/blob/v1.18.0/scipy/integrate/src/dop.h)

`LICENSE_DOP` accompanies them. The unused DOPRI5 routine remains in the vendored
source to keep it unchanged; the experiment only calls `dopri853`.

SHA-256:

```text
dop.c  14b9fdce5f18e6ad01eb814ec7965cc51804ba49b359d4bd6cf72a958239d213
dop.h  72549b5250fbfde34026b2bf1a8e65cbfdf1854dee35971a6922bfcbb9740944
```

`native_library()` builds once per process with Apple Clang:
`-O2 -ffp-contract=on -fPIC -shared`. There is no fast-math flag. Shared-library
products live in a `TemporaryDirectory` outside the repository. Numba callbacks
use `cache=False`; no compiled products are committed. Building requires `clang`;
the measured Python environment is the existing `.venv`, without dependency edits.

## Bounded failed attempt and correction

The first build used `-ffp-contract=off`. All eight screened persisted-fast cells
passed the comparison at T=5, but four of the seven successful T=20 cells failed.
For example, `(145,57)` had rate error `0.005547912650844866 /s` and final
Candidate-A state distance `0.3049067845348522`; `(294,27)` had rate error
`6.771459709686845e-5 /s`. These are failures, despite small energy drift, and were
not accepted as “equivalent chaos.” The eighth cell failed the trusted max-step
gate at T=20.

Inspection of the installed `_dop` binary with `otool -tvV` found 224 fused
multiply-add/subtract instructions. This supported one bounded correction:
enable ordinary expression contraction to match the installed solver build.
No numerical policy, tolerance, observation or equation changed. After switching
to `-ffp-contract=on`, short-segment checks at T=0.25 and complete checks at T=5
and T=20 recovered identical rates, final states and tangents on the seven-cell
cohort. The final tests and benchmark below use this corrected build.

The failed-build figures above are diagnostic console results, not warm benchmark
measurements. The checked-in JSON records the final build and hashes its source.
The initial attempt can be reconstructed in a separate experimental copy by
changing only the documented contraction flag; it is not an alternative solver.

## Comparison design and cohort

The first two cells are exactly those in the S1 solver-boundary report. Five
additional cells are the other persisted-fast representatives from
`../evidence/s1/route_stratified_16_cells.json` that also succeed on the trusted fast path at
T=20. This spans near-equilibrium, low-stretch interior and strongly stretching
trajectories. Selection is based on trusted route success, not prototype speed or
agreement. All seven are used at **both** horizons.

| Cell | theta1 (radians) | theta2 (radians) |
| --- | ---: | ---: |
| fast_equilibrium | -3.141592653589793 | -3.141592653589793 |
| fast_interior | -0.5645049299419158 | -0.4417864669110645 |
| fast_145_57 | -2.791845033951867 | -2.2518837966161214 |
| fast_294_27 | -2.9759227284981438 | -1.337631247036279 |
| fast_583_606 | 0.5767767762450009 | 0.43565054375952217 |
| fast_729_957 | 2.7304858024364416 | 1.3314953238847362 |
| fast_1023_1023 | 3.135456730438251 | 3.135456730438251 |

All have zero initial angular velocities and otherwise use the original defaults.
The index suffix is `(theta2_index, theta1_index)` in the existing 1024 grid; only
these individual specifications were evaluated, not the grid.

The screened `(878,958)` cell, at `(theta1,theta2) =
(2.736621725587984, 2.2457478734645786)`, is explicitly excluded from the common
successful cohort. Both implementations succeed at T=5 and reject it at T=20
with exactly the same reported accepted-step gap:
`0.010039818867229044 > 0.009977357137720327`. The JSON retains both outcomes;
tests retain this rejection and one original S1 fallback cell. Neither rejection
invokes a fallback.

## Warm benchmark

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m development.chaos_content.prototypes.state_space_maps.investigations.performance.s1_history.benchmark_s1_compiled_loop \
  --repetitions 11
```

The command above produced `../evidence/s1/s1_compiled_loop_benchmark.json`. It refuses to
overwrite evidence. For a rerun, append `--output /tmp/s1-compiled-loop-rerun.json`
using a path that does not already exist.

Both full evaluators are warmed for every cell and horizon before any timing.
The same process then performs 11 paired repetitions, alternating evaluator order
and reversing cell order on alternate repetitions. `perf_counter` surrounds the
complete evaluator calls, including Python setup, result construction and the
shared scalar adapter. Compilation and numerical comparison calls are excluded.
Garbage collection remains enabled. Raw individual times, per-cell medians,
specifications, diagnostics, source hashes and environment are saved in JSON.
The aggregate is the **median of per-cell ratios of median times**, not a ratio
of pooled execution times.

Environment: Python 3.12.3, NumPy 2.5.2, SciPy 1.18.0, Numba 0.67.0;
macOS 15.7.9 ARM64; Apple Clang 17.0.0 (`clang-1700.6.4.2`). Baseline Git HEAD:
`1d10f88faf4ad8e93642383fe2cd1e4037207f59`. Initial worktree status was clean.

| T | Cell | Trusted median ms | Prototype median ms | Speedup | RHS calls, both |
| ---: | --- | ---: | ---: | ---: | ---: |
| 5 | fast_equilibrium | 6.250 | 0.455 | 13.724× | 6292 |
| 5 | fast_interior | 6.329 | 0.480 | 13.185× | 6292 |
| 5 | fast_145_57 | 6.547 | 0.541 | 12.108× | 6560 |
| 5 | fast_294_27 | 6.971 | 0.593 | 11.764× | 7099 |
| 5 | fast_583_606 | 6.282 | 0.482 | 13.036× | 6292 |
| 5 | fast_729_957 | 6.619 | 0.540 | 12.256× | 6607 |
| 5 | fast_1023_1023 | 6.660 | 0.555 | 12.010× | 6736 |
| 20 | fast_equilibrium | 24.949 | 1.757 | 14.201× | 25132 |
| 20 | fast_interior | 24.788 | 1.799 | 13.780× | 25132 |
| 20 | fast_145_57 | 27.142 | 2.202 | 12.329× | 27689 |
| 20 | fast_294_27 | 27.711 | 2.237 | 12.387× | 28146 |
| 20 | fast_583_606 | 25.110 | 1.826 | 13.752× | 25132 |
| 20 | fast_729_957 | 26.911 | 2.131 | 12.628× | 27234 |
| 20 | fast_1023_1023 | 27.109 | 2.177 | 12.453× | 27259 |

| Horizon | Median trusted ms | Median prototype ms | Median per-cell speedup | Minimum required |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 6.547 | 0.540 | **12.256×** | 1.5× |
| 20 | 26.911 | 2.131 | **12.628×** | 1.5× |

Every measured cell improves; no anomalous slow cell is hidden in the aggregate.
These are warm single-cell results on one machine, not field-throughput or
multiprocessing claims. No CPU affinity, thermal control or multi-machine study
was performed. Cold import/JIT/build latency is deliberately outside this warm
criterion and is not claimed to improve.

## Numerical agreement

`compiled_equivalence.py::compare_results` is reused without edits or relaxed
thresholds. The benchmark additionally requires both results to be valid,
identical cycle-end times and identical RHS counts. All **14/14** comparisons pass.

| Quantity | Maximum observed difference across all 14 | Existing absolute gate |
| --- | ---: | ---: |
| Final finite-time rate | 0 /s | `1e-8 /s` |
| Per-cycle log stretch | 0 | `5e-8` |
| Final reference Candidate-A distance | 0 | `1e-7` |
| Final unit tangent Candidate-A distance | 0 | `1e-7` |
| Maximum energy-drift diagnostic | `3.018e-16` | `1e-8` |
| Stretch factors | 0 | Recorded supplemental comparison |
| Cumulative logs and per-cycle rates | 0 | Recorded supplemental comparison |
| Validity and issue tuples | All identical; all valid | Exact agreement |
| Segment counts / cycle ends / RHS counts | All identical | Additional checks |

The largest prototype normalized energy drift is `1.262151330329743e-10`, below
the original `1e-7` gate. The largest post-renormalisation norm error is
`2.220446049250313e-16`, below `1e-12`. Scalar C energy evaluation changes only
the last few rounding bits of the diagnostic relative to NumPy's vector
calculation; it does not feed back into the trajectory or normalisation.
Per-cell rates, all comparison errors and both full diagnostic records are in
the JSON, alongside the timings.

Agreement is demonstrated on this environment and cohort, not proven for every
state or compiler. In particular, exact trajectory agreement depends on floating
point contraction and reduction behaviour. A SciPy/compiler/architecture change
must rerun these unmodified gates; energy conservation alone is insufficient.
Matching RHS counts is supporting evidence, not a stored trace proving every
intermediate step is identical.

## Focused tests and validation

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m pytest -q -p no:cacheprovider \
  development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_history/tests/test_s1_compiled_loop.py
```

Result: **21 passed in 2.97s**. Coverage:

- Fourteen cell/horizon scientific comparisons with unchanged gates, RHS counts,
  cycle counts, max-step policy and stretch/log/cumulative-rate identities.
- Two rejected-fast-path cases, preserving the max-step rejection and neutral
  error outcome without running a fallback.
- Deliberately tighter energy and norm limits in test specifications only, proving
  that each gate still produces the trusted invalidity status and issue tuple.
- Non-default physical parameters, non-axis initial tangent, characteristic
  length, rtol/atol/max-step and renormalisation interval.
- Operational accepted-step sampling invariance and rejection of another solver.

No production tests were edited. No full application suite, field, rendering,
persistence or worker experiment was run for this isolated single-cell change.
The vendored source hashes were checked against the retrieved originals.

## Files and repository state

All new files are within this investigation:

- `s1_compiled_loop.py`: native build, compiled callbacks and single-cell adapter.
- `native/loop.c`: compiled segment loop, observation reduction and gates.
- `native/dop.c`, `dop.h`, `LICENSE_DOP`: unchanged upstream solver and license.
- `tests/test_s1_compiled_loop.py`: focused tests.
- `benchmark_s1_compiled_loop.py`: reproducible bounded comparison command.
- `../evidence/s1/s1_compiled_loop_benchmark.json`: final warm timings and numerical evidence.
- `S1_COMPILED_LOOP_PROTOTYPE.md`: this report.

Inspection was limited to S1 audit/profile material, its existing cell evidence,
the referenced `compiled_dop853.py`, `compiled.py`, `reference.py`,
`compiled_equivalence.py`, `evaluation.py`, the local SciPy DOP853 wrapper/binary,
and the matching upstream solver source. Production code and configuration have
no changes. No promotion or integration was performed.

Final `git status --short`:

```text
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/S1_COMPILED_LOOP_PROTOTYPE.md
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/benchmark_s1_compiled_loop.py
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_compiled_loop.py
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_compiled_loop_benchmark.json
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_native/
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/test_s1_compiled_loop.py
```

## Recommendation

GO — numerical agreement passes the existing scientific gates and median warm speedup is at least 1.5× at both T=5 and T=20.
