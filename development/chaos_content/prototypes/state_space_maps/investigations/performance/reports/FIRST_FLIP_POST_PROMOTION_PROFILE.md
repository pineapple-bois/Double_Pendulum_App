# First-flip post-promotion profile

## Decision

**PROTOTYPE COMPILED SOLVER/EVENT LOOP.** The remaining cost is large enough,
and concentrated enough at the Python/SciPy boundary, to justify one narrow
investigation-only prototype. The corrected profile attributes **82.3%** of
representative compiled-evaluator wall to solver/event work outside the
compiled physical RHS. A conservative operational projection requires that
boundary to become about **2.565×** faster to achieve a further 1.5× whole-field
speedup. A 3× boundary improvement projects **1.573×** at 64²; the theoretical
ceiling, while retaining measured non-evaluation and worker/scheduling wall, is
**2.204×**.

This is a feasibility decision, not a measured compiled-loop speedup. No new
solver path is implemented or promoted here.

## Scope and method

The probe uses the promoted production `first_flip_time_compiled` path with the
validated unit/equal-link parameters, zero initial velocities, T=5, DOP853,
existing tolerances and `max_step`, and the existing four terminal positive-
direction event surfaces. It reuses the 32 distribution-aware coordinates from
the accepted feasibility evidence: 16 observed-time quantiles and 16 censored
spatial quantiles. Each case is warmed and measured five times with alternating
uninstrumented/profiled order.

Temporary timing wrappers surround the existing compiled RHS, DOP853 step,
four event callbacks, active-event detection, DOP853 dense-output construction
and evaluation, SciPy root solve, and existing post-solve helpers. SciPy still
performs every step, event check, dense interpolation and root solve. Production
code and numerical inputs are untouched.

Fine-grained timing added 13.4% wall to observed cases and 13.9% to censored
cases. The tables below therefore use the uninstrumented evaluator wall and
conservatively remove all measured probe inflation, pro rata, from the two
instrument-sensitive buckets (DOP853 stepping and residual orchestration).
Direct RHS, event, dense-output, root and diagnostic timings are left unchanged.
The raw and adjusted measurements are both retained in JSON evidence.

All 32 profiled results retained the baseline status, observed/censored result,
event identities, raw event counts, RHS evaluation count and event time within
the existing 5e-8 s gate.

Environment: macOS 15.7.9 ARM64, Python 3.12.3, NumPy 2.5.2, SciPy 1.18.0,
Numba 0.67.0. Evidence:
`../evidence/current/first_flip_post_promotion_profile.json`.

## Measurements

Values are the mean across the 16 cases of each case's five-run median. The
component rows are instrumentation-adjusted estimates against uninstrumented
wall; percentages use the corresponding uninstrumented evaluator time.

| Component | Observed | Observed share | Censored | Censored share |
| --- | ---: | ---: | ---: | ---: |
| Total `first_flip_time` evaluator | 12.820 ms | 100.0% | 23.851 ms | 100.0% |
| Compiled physical RHS | 2.188 ms | 17.1% | 4.112 ms | 17.2% |
| DOP853 stepping outside RHS | 7.776 ms | 60.7% | 14.620 ms | 61.3% |
| Active-event detection outside callbacks | 1.877 ms | 14.6% | 3.560 ms | 14.9% |
| Four event callbacks | 0.241 ms | 1.9% | 0.453 ms | 1.9% |
| Dense-output construction outside RHS | 0.016 ms | 0.13% | 0 | 0 |
| Dense-output evaluations during root solve | 0.052 ms | 0.40% | 0 | 0 |
| Root algorithm outside event/dense calls | 0.014 ms | 0.11% | 0 | 0 |
| Other `solve_ivp` orchestration | 0.559 ms | 4.4% | 1.008 ms | 4.2% |
| Post-solve attribution/diagnostics/result | 0.081 ms | 0.63% | 0.078 ms | 0.33% |
| Pre-solve evaluator work | 0.009 ms | 0.07% | 0.010 ms | 0.04% |

Observed cases averaged 3,202.25 RHS evaluations, 266.06 accepted points,
1,070.13 event-callback calls and one root location. Censored cases averaged
6,035.75 RHS evaluations, 503.5 accepted points, 2,014 event-callback calls and
no root location. Their profiles are nearly identical per integration step;
censored cells cost more because they run the entire horizon, not because they
exercise a different expensive operation.

Within the observed post-solve 0.081 ms, energy calculation used 0.032 ms,
accepted angular-increment calculation 0.009 ms, event record/surface work
0.007 ms, structural validation 0.005 ms, and residual array/result construction
about 0.028 ms. The censored split is similarly immaterial. There is no useful
post-solve optimization target at T=5.

The 64² observed/censored weighting is 1,742/2,354. It gives an uninstrumented
representative evaluator of 19.160 ms/cell, of which 3.294 ms (17.2%) is the
compiled RHS and 15.769 ms (82.3%) is the solver/event boundary. Within that
boundary, DOP853 stepping is the main cost (61.1% of evaluator wall), followed
by active-event detection (14.8%); the four surface callbacks themselves are
only 1.9%. Dense output plus root refinement is about 0.18% weighted and 0.64%
even for observed cells.

A one-cell `cProfile` cross-check found 57,036 Python calls for a representative
censored cell: 502 DOP853 steps, 6,026 RHS dispatches and 2,012 surface callback
calls. `rk_step`, `_step_impl`, event-sign detection and error-norm machinery
dominated outside the RHS. This corroborates the direct timers: the opportunity
is compiling the complete step/event loop, not changing root refinement or
micro-optimizing the four scalar surfaces.

## Whole-field ceilings

The projection starts from the promoted 64² medians: 29.553 s total and
25.694 s evaluation. The representative cell cost implies 19.620 s at ideal
four-worker throughput. The remaining 6.075 s of measured evaluation wall is
held fixed as a conservative allowance for adapter/provenance work, task
dispatch, worker imbalance and other operational effects. Setup, persistence
and shutdown (3.859 s combined) are also held fixed. Only the profiled cell-level
solver/event boundary is accelerated.

| Boundary acceleration | Projected evaluation | Projected total | Additional whole-field speedup |
| ---: | ---: | ---: | ---: |
| 2× | 17.621 s | 21.479 s | 1.376× |
| 3× | 14.930 s | 18.788 s | **1.573×** |
| 5× | 12.777 s | 16.635 s | 1.777× |
| 10× | 11.162 s | 15.021 s | 1.967× |
| Infinite (theoretical) | 9.547 s | 13.406 s | 2.204× |

The exact modeled requirement for 1.5× whole-field is a 2.565× acceleration of
the non-RHS boundary. This is plausible for a compiled loop because roughly 76%
of evaluator wall is repeated Python DOP853 stepping plus NumPy-based active-
event detection, and the one-cell cross-check exposes tens of thousands of
Python calls. It is not assured: the 3× case clears the gate by only 4.9%, so
the prototype must measure end-to-end behavior rather than rely on kernel-only
timings.

Individual-component ceilings reinforce the decision:

| Component hypothetically eliminated | Whole-field ceiling |
| --- | ---: |
| DOP853 stepping outside RHS | 1.683× |
| Active-event detection | 1.109× |
| Compiled RHS itself | 1.129× |
| Other `solve_ivp` orchestration | 1.029× |
| Four event callbacks | 1.013× |
| Dense output and root algorithm together | about 1.001× |
| Post-solve work | 1.003× |

No isolated event-callback, root, RHS or diagnostic optimization can meet the
gate. Only crossing the whole solver/event boundary has sufficient ceiling.

## Narrow next experiment

Build one investigation-only compiled/native four-state loop, with no production
dispatch or persistence integration. It should:

- retain the same DOP853 tableau, adaptive error policy, `rtol`, `atol` and
  `max_step`;
- inline or directly call the already validated compiled physical RHS;
- evaluate the same four signed surfaces after accepted steps, with terminal
  positive crossings only;
- use the same DOP853 dense interpolant and root tolerance/selection behavior
  needed to reproduce SciPy's event time and state;
- return enough data to run the existing attribution, censoring, energy,
  angular-increment and adapter gates unchanged; and
- compare first on the same 32 distribution-aware cells plus the five named
  Experiment 020 cases, then only on a bounded field if those scientific gates
  pass.

The prototype should be rejected immediately for any outcome, attribution,
event-count or censoring disagreement, or for violation of the existing event
time/state/residual/energy/increment gates. Its performance gate should be at
least 2.565× on the measured solver/event boundary and at least 1.5× in a
bounded operational projection before any later promotion is considered.

## Risks and limitations

- Reproducing SciPy's DOP853 controller is easier than reproducing its complete
  terminal-event behavior. Dense interpolation, bracket handling, simultaneous
  surfaces and earliest-root ordering are the scientific risk.
- These accepted cases are transversal and separated. They do not authorize new
  grazing or tie semantics.
- Per-call timers perturb a short evaluator. The explicit inflation correction
  is conservative but cannot make every subcomponent exact; the stable
  observed/censored proportions and `cProfile` call structure are stronger than
  sub-0.1 ms distinctions.
- The fixed 6.075 s operational evaluation residual prevents the projection
  from assuming ideal four-worker scaling. Some of it may scale with cell cost,
  making the projection conservative, but that is not claimed.
- A compiled loop still has to perform the DOP853 arithmetic and event tests.
  The theoretical ceiling is not an expected result.
- This profile covers only the validated standard T=5 field and does not make a
  claim about other horizons, parameters or runtime builds.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m \
development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.profile_first_flip_post_promotion \
  --repetitions 5
```

The run completed in 8.49 s. Import/compile and focused first-flip validation are
reported with the task handoff.

**PROTOTYPE COMPILED SOLVER/EVENT LOOP**
