# 015 Compiled Integration Boundary

**Status: accepted for the declared five-condition, fixed-horizon contract; not promoted.**

## Question

> Can SciPy's compiled Fortran DOP853 segment integrator replace the current
> Python `solve_ivp` integration boundary for the accepted fixed-horizon
> renormalized tangent observable, while preserving the established numerical
> contract and materially reducing warmed per-evaluation cost?

## Definition / fixed contract

The existing Numba-RHS plus `solve_ivp` DOP853 evaluator is the numerical
oracle. The experiment changes only the segment-integration boundary. It keeps:

- the accepted Euler--Lagrange dynamics and exact compiled JVP;
- Candidate-A tangent geometry;
- initial tangent direction `(1, 0, 0, 0)`;
- zero initial angular velocities;
- fixed horizon `T = 5 s`;
- renormalisation interval `0.25 s` and twenty exact cycle boundaries;
- signed `log(r_k)` accumulation and angle rebasing;
- DOP853 with `rtol=1e-9`, `atol=1e-11`, and resolved
  `max_step=0.009977357137720327 s`;
- post-reset Candidate-A norm tolerance `1e-12`; and
- normalized reference-energy drift limit `1e-7`.

The scalar remains

$$
\Lambda_T^{(1)}
=
\frac{1}{T}\sum_k \log(r_k).
$$

It is a fixed-horizon one-vector stretching rate, not an asymptotic Lyapunov
exponent.

## Candidate integration boundary

`FortranDop853SegmentSolver` uses `scipy.integrate.ode` with its compiled
Fortran DOP853 integrator. Each renormalisation interval is integrated to its
endpoint exactly once. A `solout` callback observes accepted solver steps for
energy validity and segment-mechanics evidence.

The adapter does not integrate successively to the existing `0.01 s` output
times. Planning evidence showed that treating every output time as a new
Fortran integration target changes the adaptive trajectory enough to fail the
established rate tolerance.

The prototype's internal renormalisation driver gained one keyword-only,
optional `segment_solver` injection point. Its default remains the existing
`_solve_segment`, so the reference and compiled prototype evaluators are
unchanged. All Fortran-specific setup, status handling, observations, and
timings remain local to this experiment.

## Minimal experiment

Three modes are measured:

1. Numba RHS/JVP with Python `solve_ivp` DOP853: the oracle.
2. The same `solve_ivp` path retaining only segment endpoints: a profiling
   control for intermediate diagnostic-output cost, not a scientific
   candidate.
3. Numba RHS/JVP with compiled Fortran DOP853, one call per renormalisation
   segment and accepted-step observation: the candidate.

A fourth timing-only execution of mode 3 disables accepted-step observation to
measure callback/instrumentation overhead. It is not assessed for scientific
equivalence.

The mechanically selected validation set is the existing centre plus four
corners:

```text
(179 deg, 179 deg)
(169 deg, 169 deg)
(169 deg, 189 deg)
(189 deg, 169 deg)
(189 deg, 189 deg)
```

The executable command is:

```bash
UV_CACHE_DIR=/tmp/codex-uv-cache \
MPLCONFIGDIR=/tmp/codex-matplotlib-cache \
XDG_CACHE_HOME=/tmp/codex-xdg-cache \
uv run python \
  development/chaos_content/experiments/015_compiled_integration_boundary/compiled_integration_boundary.py \
  --benchmark-repeats 7
```

Machine-readable evidence is written to the ignored path:

```text
development/chaos_content/outputs/compiled_integration_boundary/baseline/summary.json
```

## Numerical validity

The predeclared pointwise gates are unchanged:

- finite-time rate absolute error at most `1e-8 s^-1`;
- maximum cycle-log absolute error at most `5e-8`;
- final reference Candidate-A distance at most `1e-7`;
- final tangent Candidate-A distance at most `1e-7`;
- energy-diagnostic absolute difference at most `1e-8`; and
- exact numerical-validity classification and issue agreement.

The candidate must additionally preserve exact cycle count and boundary times,
finite positive stretch factors, signed-log identities, post-reset unit norm,
strictly increasing accepted times, exact endpoint reach, finite states,
successful Fortran return codes, and `max_step` within a floating-point
allowance. Numerical solver failure becomes `RuntimeError`; programming and
specification errors are allowed to propagate.

All five cases passed. The observed errors were:

| Initial angles (deg) | Rate error (`s^-1`) | Max cycle-log error | Final reference distance | Final tangent distance | Energy diagnostic difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| `(179, 179)` | `4.501e-9` | `1.675e-8` | `4.723e-10` | `6.157e-10` | `1.357e-10` |
| `(169, 169)` | `9.837e-11` | `1.236e-9` | `1.456e-9` | `6.034e-10` | `5.288e-11` |
| `(169, 189)` | `6.020e-10` | `7.334e-9` | `9.795e-9` | `2.032e-9` | `1.591e-10` |
| `(189, 169)` | `1.261e-10` | `5.029e-10` | `2.870e-9` | `1.473e-9` | `2.159e-10` |
| `(189, 189)` | `2.394e-10` | `1.381e-9` | `3.606e-9` | `1.329e-9` | `1.338e-11` |

The worst errors remain inside their corresponding predeclared gates without
case-specific tuning.

## Energy-sampling distinction

The result contract has not been silently redefined:

- the oracle energy diagnostic observes the uniform `0.01 s` grid;
- the candidate observes accepted Fortran DOP853 steps.

Across the five cases, both diagnostics remained below `1e-7`. Their largest
absolute difference was `2.159e-10`, well inside the existing `1e-8`
comparison gate. The candidate's largest accepted-step gap was
`0.00997735713772041 s`, equal to the declared `max_step` within floating-point
allowance and slightly smaller than the oracle diagnostic interval.

| Initial angles (deg) | Oracle maximum drift | Candidate maximum drift |
| --- | ---: | ---: |
| `(179, 179)` | `1.868e-10` | `5.103e-11` |
| `(169, 169)` | `9.812e-11` | `4.525e-11` |
| `(169, 189)` | `1.891e-10` | `2.994e-11` |
| `(189, 169)` | `2.642e-10` | `4.831e-11` |
| `(189, 189)` | `4.234e-11` | `2.896e-11` |

This supports accepted-step observation as a defensible validity diagnostic
for this experiment: it is at least as temporally dense in maximum gap, retains
the unchanged energy limit, and agrees numerically with the oracle maximum.
It does not establish that the two sampling schemes are generally identical.

## Performance evidence

The standalone run triggered Numba compilation separately in `0.2578 s`.
After that warm-up, the first complete Fortran candidate evaluation took
`7.18 ms`.

Seven interleaved repetitions over three mechanically selected cases produced
21 warmed observations per mode:

| Mode | Complete median | Complete IQR | Segment-solver median | Segment-solver IQR |
| --- | ---: | ---: | ---: | ---: |
| `solve_ivp` oracle | `37.85 ms` | `2.21 ms` | `36.91 ms` | `1.87 ms` |
| `solve_ivp` endpoint-only control | `25.07 ms` | `1.02 ms` | `24.23 ms` | `0.94 ms` |
| Fortran DOP853 candidate | `7.03 ms` | `0.36 ms` | `5.67 ms` | `0.21 ms` |
| Fortran without accepted-step observation | `6.41 ms` | `0.29 ms` | `5.30 ms` | `0.21 ms` |

The candidate provides a warmed complete-observable speedup of `5.38x`, above
the predeclared `2x` gate. Accepted-step observation costs approximately
`0.622 ms`, or a `1.097x` observed/unobserved timing ratio, and does not remove
the material speedup.

The oracle used 8,008--8,272 RHS evaluations across the full validation set;
the candidate used 6,526--6,982. The candidate observed 535--562 accepted steps
per complete evaluation. In the warmed three-case timing set the corresponding
ranges were 8,188--8,272 oracle RHS evaluations, 6,748--6,832 for the
endpoint-only control, 6,831--6,982 candidate RHS evaluations, and 554--562
candidate accepted steps.

## Acceptance criteria

The verdict is **ACCEPT** only if every pointwise, mechanics, validity, and
energy gate passes with one fixed policy and warmed complete-observable speedup
is at least `2x`. Failure of any scientific gate, case-specific tuning,
unverifiable solver mechanics, indefensible energy monitoring, or loss of the
material speedup gives **REJECT**. **UNRESOLVED** is reserved for a genuinely
ambiguous numerical-contract result requiring deeper review.

## Findings

**Verdict: ACCEPT.**

The Fortran DOP853 segment boundary passed all five pointwise comparisons, all
segment-mechanics checks, the unchanged numerical-validity classifications,
the explicit energy-sampling assessment, and the material-speedup gate. No
numerical failures or case-specific policy adjustments occurred.

The endpoint-only `solve_ivp` control attributes roughly one third of the
current complete runtime to intermediate diagnostic-output handling. The much
larger candidate improvement shows that the Python adaptive-integration loop
and its orchestration are also material costs.

## Strongest earned claim

For the declared five initial conditions, `T=5 s` policy, Candidate-A
one-vector observable, and existing tolerances and step cap, integrating each
renormalisation segment once with SciPy's compiled Fortran DOP853 reproduces
the accepted `solve_ivp` result within every predeclared numerical gate while
reducing warmed complete-evaluation time by approximately `5.38x` on this
machine.

## Explicit nonclaims

This experiment does not establish:

- an asymptotic Lyapunov exponent;
- equivalence for all initial conditions, horizons, parameters, or tangent
  directions;
- bitwise identity between the Python and Fortran DOP853 implementations;
- identical energy maxima under arbitrary sampling policies;
- suitability for threaded concurrent execution;
- batch, grid, tile, storage, or production readiness; or
- acceptance of a custom fixed-step, adaptive RK, or reimplemented DOP853
  method.

The candidate remains experiment-local and has not been promoted into the
prototype evaluator API.

## Next step

The next decision is a separate promotion review of this exact segment
boundary. That review should consider the lifecycle and concurrency properties
of SciPy's older `ode` interface and preserve the accepted-step energy
provenance. Only after promotion should a small compiled batch/grid apparatus
test measure composition with state-space sampling. No custom integrator is
earned by this experiment.
