# S1 solver-boundary profiling decision

Profile date: 2026-09-05 local time. Source hypothesis: `PERFORMANCE_AUDIT.md`, S1. Raw evidence: `s1_solver_boundary_profile.json`.

## Decision

**GO for a bounded, single-cell S1 compiled-loop prototype. Do not implement or promote S1 yet.**

The current measurements are enough to show that the repeated Python/solver boundary and surrounding per-segment work are material, so a prototype could plausibly produce a substantial warm-compute speedup. They do not establish an achievable speedup or numerical equivalence. Any prototype must remain separate from the production evaluator until it passes the existing scientific gates.

## Code paths profiled

The probe calls the operational single-cell entry point without changing its configuration:

```text
src/lyapunov/hybrid.py::evaluate_renormalized_tangent_hybrid
  -> compiled_dop853.py::evaluate_renormalized_tangent_compiled_dop853
  -> reference.py::_run_renormalized_tangent_with_rhs
  -> compiled_dop853.py::_integrate_compiled_dop853_segment_unchecked
  -> scipy.integrate.ode(...).integrate
  -> counted_rhs -> compiled.py::compiled_rhs/evaluate
  -> solout -> observe
```

For endpoint-cap fallback cells it additionally profiles the existing verification replay and:

```text
compiled.py::evaluate_renormalized_tangent_compiled
  -> reference.py::_run_renormalized_tangent_with_rhs
  -> reference.py::_solve_segment
  -> scipy.integrate.solve_ivp(method="DOP853")
```

`investigations/performance/probe_s1_solver_boundary.py` adds timers and `cProfile` only in the experiment process. No promoted source is instrumented.

## Configuration

- Python 3.12.3, NumPy 2.5.2, SciPy 1.18.0, Numba 0.67.0, macOS 15.7.9 ARM64, Git HEAD `c3cfb0eca3a7b070cf5d49aa0964b08cff8b8cd3` with the current task changes uncommitted.
- Four fixed cells: two T=5 fast-route and two T=5 fallback-route representatives previously recorded by `route_stratified_16_cells.json`.
- Horizons: T=5 and T=20; renormalisation interval 0.25 s.
- Five unprofiled wall repetitions per cell/horizon and one separate `cProfile` pass per cell/horizon: 40 wall measurements plus 8 profiled measurements, not a field.
- Sequential, single process. One excluded pass across every case/horizon combination warmed imports, the Numba signature, and both routes before measurement; its total 0.833 s elapsed time is excluded.
- Existing numerical configuration was retained exactly: DOP853, `rtol=1e-9`, `atol=1e-11`, resolved `max_step=0.009977357137720327` s, 0.01 s sampling, 0.25 s renormalisation, `1e-7` energy-drift limit, and `1e-12` reset-norm tolerance.
- All 48 measured evaluations completed valid. Both fast cases and both fallback cases retained their respective routes at both horizons.

Command run:

```bash
MPLCONFIGDIR=/tmp/double-pendulum-mpl PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m \
  development.chaos_content.prototypes.state_space_maps.investigations.performance.probe_s1_solver_boundary
```

The evidence file is intentionally not overwritten. To reproduce without replacing it, add `--output /tmp/s1_solver_boundary_profile.json`.

## Raw wall timing and counts

Means below are across ten unprofiled measurements in each horizon/route group (two cells times five repetitions). “Integration calls” times the exact `ode.integrate` and `solve_ivp` call bodies and therefore includes RHS and observer callbacks. “Outside calls” is the cell wall remainder around those calls.

| Horizon / observed route | Cell wall | Integration-call wall | Share | Outside calls | Compiled DOP853 calls | `solve_ivp` calls | Returned RHS evaluations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T=5 fast | 6.301 ms | 4.886 ms | 77.5% | 1.415 ms | 20 | 0 | 6,292 |
| T=5 fallback | 48.540 ms | 44.949 ms | 92.6% | 3.590 ms | 34.5 | 20 | 8,314 |
| T=20 fast | 24.528 ms | 19.249 ms | 78.5% | 5.279 ms | 80 | 0 | 25,132 |
| T=20 fallback | 180.421 ms | 169.138 ms | 93.7% | 11.283 ms | 94.5 | 80 | 32,980 |

The non-integrator remainder is already 22–25% of fast-cell wall time. Fallback cells execute a failed fast prefix plus a complete compiled-DOP853 verification replay and a complete `solve_ivp` result. The mean compiled call counts are fractional because the two fixed fallback cases fail after different segment counts.

## Profiler attribution

The profiler pass is separate because profiling inflates wall time. These are means over the two cells per horizon/route. “Total RHS calls” counts `compiled.py::compiled_rhs` invocations across all attempted, replayed, and returned routes; it is more complete than the returned-result diagnostic.

| Horizon / route | Profile wall | Total RHS calls | Fast counter self | `solout` bridge cumulative | Native DOP853 self | `solve_ivp` cumulative | Python `rk_step` self |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T=5 fast | 10.639 ms | 6,292 | 0.844 ms | 0.672 ms | 1.653 ms | 0 | 0 |
| T=5 fallback | 72.056 ms | 20,362.5 | 1.625 ms | 1.223 ms | 3.162 ms | 50.274 ms | 13.871 ms |
| T=20 fast | 40.402 ms | 25,132 | 3.352 ms | 2.596 ms | 6.466 ms | 0 | 0 |
| T=20 fallback | 256.819 ms | 65,759 | 4.445 ms | 3.346 ms | 8.586 ms | 196.149 ms | 54.117 ms |

On the fast path, the directly visible RHS counter plus accepted-step `solout` bridge accounts for about 14.3–14.7% of profiled wall, before assigning any cost to the Numba dispatch/return-array boundary. The native DOP853 driver itself records only about 15.5–16.0% as self time; its cumulative time includes callbacks. The unprofiled outer remainder independently shows that repeated segment construction, validation, renormalisation, and diagnostics are not negligible.

Fallback magnifies the boundary cost rather than hiding it. Total RHS calls are 2.45 times the returned count at T=5 and 1.99 times at T=20 because discarded fast work is not in the returned diagnostic. `solve_ivp` consumes 70–76% of profiled fallback wall, and its Python `rk_step` self time alone is about 19–21%.

## Interpretation

The evidence supports the mechanism behind S1:

- A successful fast cell crosses the RHS callback boundary 6,292 times at T=5 and 25,132 times at T=20, with 20 and 80 separately constructed solver segments.
- Directly attributable callback work is material and scales nearly linearly with horizon. The separate outside-integrator wall share remains above one fifth on the fast path.
- These non-overlapping seams are large enough that an Amdahl-style warm-cell gain around 1.5x is plausible if a compiled loop removes much of both. This is an opportunity bound, not a measured speedup.
- Fallback cells are about 7.7x slower than fast cells at T=5 and 7.4x at T=20 in this deliberately stratified sample. A fast-only prototype cannot claim equivalent field-wide gains. The audit's persisted fallback fractions (4.26% at T=5 and 11.50% at T=20) mean fallback handling becomes increasingly important at longer horizons.

Therefore S1 has enough evidence for the next requested step: a single-cell prototype using the identical DOP853 policy and existing oracle comparisons. There is not enough evidence to replace either current route, batch cells, or alter the fallback policy.

## Limitations

- Four route-stratified cells establish mechanism, not population distributions or field throughput.
- `cProfile` perturbs runtime; profiler timings must not be compared directly with unprofiled wall timings.
- The `ode.integrate` wall timer includes native integration, RHS dispatch, Numba computation, allocation, and observer callbacks. Only profiler self/cumulative relationships partially separate them.
- `compiled_rhs_binding` self time includes Numba kernel execution as well as dispatch and array return, so it is not labelled pure boundary overhead.
- `solve_ivp` DOP853 is Python-driven; its cumulative time cannot be treated as native solver time.
- The probe does not count rejected steps separately, inspect allocations, estimate cold worker/JIT cost, or include multiprocessing and persistence.
- No alternative integrator or compiled loop was run, so this experiment demonstrates plausibility rather than speedup or equivalence.
