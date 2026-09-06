# Native DOP853 first-flip equivalence investigation

## Decision

**FIXABLE EQUIVALENCE DEFECT — IMPLEMENT NEXT.** Both promotion blockers arise
from bounded mismatches in the first-flip staged DOP853 build. No production
source or default changed in this investigation. A separate implementation task
should apply the reviewed corrections to the first-flip-only staged source,
update its digest/provenance, and repeat the complete scientific and field gates.

## Method

The diagnostic ran one compiled operational 64×64 T=5 field, then evaluated the
same 4,096 coordinates with temporary instrumented native builds. It recorded
accepted terminal steps, event brackets/states, roots, diagnostics, and compared
the original build with isolated corrections. Five near-worst observed cases,
five max-step recovery cases, an ordinary observed case, and an ordinary
censored case received detailed native/compiled/trusted traces. No three-pair
field benchmark or large field was repeated.

```bash
PYTHONPATH=. uv run python -m development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.diagnose_first_flip_native_equivalence
```

Evidence: `../evidence/current/first_flip_native_dop853_equivalence.json`.

## Final-step blocker

Requested `max_step` was `0.009977357137720327 s`. The wrapper passes it
unchanged in `work[5]` and measures accepted callback intervals correctly. The
vendored DOP853 core contains:

```c
if ((*x + (1.01 * h) - *xend) * posneg > 0.0) {
    h = *xend - *x;
    last = 1;
}
```

Thus, when the remaining horizon is between `h` and `1.01*h`, it deliberately
expands the final step to the complete residual. All 62 rejected cells were
censored trajectories. Their final steps ranged from
`0.009981377969555894` to `0.010072477046339401 s`: excesses of
`4.020831835566119e-6` to `9.511990861907349e-5 s`, or `0.04030%` to
`0.95336%`. Five repeats of a representative cell were bitwise deterministic.

Installed SciPy does not use this exception. `RungeKutta._step_impl` first caps
`h_abs` by `max_step`, clamps `t_new` only when the capped step would pass the
bound, then recomputes `h=t_new-t`. Executable traces over the same 62 cells had
zero violations: maximum accepted step `0.00997735713772041 s` (roundoff within
the established allowance), with final steps from `0.002535339007553539` to
`0.009931822252956302 s`.

Replacing the 1.01 rule in a temporary copy with a strict reach-bound condition
removed all 62 violations and inserted a small final residual step. This is an
implementation mismatch with the trusted max-step contract, not a reason to
invent an arbitrary 1% validation allowance.

## Event-time blocker

The two symmetric worst cells were:

- indices `(theta1=6, theta2=3)`, angles
  `(-2.552544031041707, -2.84706834231575)` rad, event `arm2-`;
- indices `(58, 61)`, angles
  `(2.552544031041707, 2.84706834231575)` rad, event `arm2+`.

Native event time was `3.796636367432912 s`; compiled was
`3.796636288294918 s`; trusted Python was `3.796636288300493 s`. Native versus
compiled differed by `7.913799454902159e-8 s`, while compiled versus trusted
differed by only `5.576e-12 s`.

The native event bracket was `[3.792030677427269,
3.802008034564990]`; 42 bounded bisections gave a triggering residual within
`1e-14`. SciPy's bracket was `[3.789580171147439,
3.799557528285159]`; Brent required seven calls. Evaluating the SciPy dense
trajectory over the *native* bracket located `3.796636288294917 s`, the compiled
root to roundoff. At the native root time, the SciPy triggering surface was
`1.641372e-7`, and aligned native/SciPy state differences were already
`5.127e-7` at bracket start and `5.673e-7` at bracket end. Therefore bracketing
and root tolerance are not the cause; the accepted trajectory/dense polynomial
entering the root finder already differs.

Other near-worst symmetric cases at `(-2.258019719767664,
1.374446785945534)` and `(2.258019719767664, -1.374446785945535)` rad differed
by about `3.757e-8 s`. A fifth case differed by `1.674e-8 s` but exposed a
baseline event-state difference of `5.326e-7`, just outside the `5e-7` gate.
Classification, link/sign, and residuals remained exact.

## Adaptive-controller cause

The event cases use the same compiled four-state RHS callback, excluding a
Python-versus-compiled RHS cause. The native worst case took 387 accepted and
three rejected steps; SciPy took 383 accepted steps. Two source mismatches explain
the divergent post-rejection trajectory:

1. The vendored DOP853 rejection branch says
   `hnew = h / fmin(facc1, facc1 / safe)`. The second `facc1` is a defect: it
   ignores the computed error factor `fac11`. The companion DOPRI5 branch uses
   the expected `fac11 / safe`.
2. The first-flip wrapper uses Hairer bounds `fac1=0.3`, `fac2=6`, whereas
   installed SciPy's DOP853 controller uses minimum/maximum factors `0.2` and
   `10`. In the Hairer parameterization these map directly to `work[2]=0.2` and
   `work[3]=10.0`.

The isolated results over all 4,096 cells were:

| Temporary variant | Max-step violations | Classification mismatches | Maximum event-time difference |
| --- | ---: | ---: | ---: |
| Current native | 62 | 0 | `7.913799e-8 s` |
| Strict final step only | 0 | 0 | `7.913799e-8 s` |
| Strict + SciPy bounds, rejection defect retained | 0 | 0 | `7.129999e-8 s` |
| Strict + rejection correction, existing bounds | 0 | 0 | `4.300617e-9 s` |
| Strict + rejection correction + SciPy bounds | 0 | 0 | `7.721708e-12 s` |

The fully equivalent temporary variant is approximately at the compiled/trusted
RHS difference floor. On the original five near-worst cases its largest event-
state difference fell from `5.326e-7` to `6.552e-12`; normalized energy drift
remained at most `1.3522e-10`, angular increment at most `0.12740`, and triggering
residual at most `6.22e-15`. These are comfortably inside all existing gates.

## Relationship and next boundary

The two failures are independent at symptom level: strict terminal clamping
eliminates the 62 censored recoveries but cannot affect the pre-horizon observed
outliers. They share a root cause category—first-flip's staged vendored-DOP853
semantics do not exactly match trusted SciPy. The bounded three-part correction
addresses both without changing equations, tolerances, event definitions, or
the declared max-step policy.

No production file was changed. In particular, the S1 DOP853 source and digest
must remain untouched. The next task should apply corrections only while staging
the first-flip artifact, give the corrected source a new identity, add focused
tests for all three source transformations, rerun the 37 cases and affected
regressions, then repeat the bounded field acceptance. This investigation alone
does not authorize promotion or a default change.
