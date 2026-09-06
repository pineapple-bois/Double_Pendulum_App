# Native DOP853 first-flip prototype

## Decision

**PROMOTE NATIVE FIRST-FLIP DOP853 NEXT.** The investigation-only prototype
passed all 37 required scientific comparisons and exceeded both performance
gates by a wide margin. Against the currently promoted compiled-RHS plus
`solve_ivp` evaluator, the distribution-weighted warm evaluator improved from
18.970 ms to 0.547 ms (**34.649×**). Conservatively charging the entire native
loop, including its physical RHS work, against the previously measured non-RHS
boundary gives **31.531× boundary acceleration**, versus the required 2.565×.

Using the existing conservative 64² model gives a projected **2.816× additional
whole-field speedup** over the promoted route. This is a projection rather than
an operational field measurement; no production dispatch or persistence path
was added.

## Reused S1 and production components

The prototype reuses rather than reimplements the integrator:

- the exact production S1 vendored `dop.c` and `dop.h` source, including the
  DOP853 tableau, error estimator, step controller, initial-step selection and
  dense-output coefficients;
- S1's validated compiler support decision, `-O2 -ffp-contract=on -fPIC
  -shared` flags and native-callback architecture;
- the promoted first-flip `compiled_physical_rhs`, exposed to C as a
  process-local Numba `cfunc`; and
- the retained DOP853 license at `src/lyapunov/s1_native/LICENSE_DOP`.

The production S1 sources and their validated SHA-256 values remain unchanged.
The prototype's C translation unit includes a temporary build copy of `dop.c`.
Dense mode revealed one dormant source defect: `nfcn += 3` increments the
counter pointer rather than its value. S1 never reaches it because S1 requests
accepted-step output without dense output. The prototype build asserts that
exact line and applies only `*nfcn += 3` to its temporary copy. The correction,
original/patched source hashes and resulting library hash are recorded in the
evidence. No compiled binary is committed.

## First-flip event machinery

The new investigation C layer is limited to the first-flip contract:

1. retain the initial lifted angles and evaluate the same four
   `direction * (theta(t) - theta(0)) - 2*pi` surfaces after accepted steps;
2. detect the same positive-direction bracket condition (`old <= 0`,
   `new >= 0`);
3. evaluate all four state components with the vendored DOP853 dense polynomial
   when a bracket is present;
4. locate each candidate using a bounded 80-iteration bisection with the same
   `4*epsilon` absolute/relative stopping scale used by SciPy's Brent call;
5. select the earliest root, retaining event ordering for equal roots within the
   accepted separated/transversal scope, replace the overshoot endpoint with
   the dense root state, and terminate; and
6. otherwise continue to T=5 and return the existing right-censored outcome.

Energy drift and maximum accepted angular increment are accumulated over the
same conceptual output sequence: initial state, accepted step endpoints, and
the dense root instead of the terminal overshoot endpoint. Python constructs the
existing `FirstFlipResult` and runs the unchanged field adapter gates.

The prototype uses dense-output mode throughout because the existing vendored
callback API decides whether to form dense coefficients before the accepted-step
callback can report a crossing. This adds three RHS evaluations per accepted
step but avoids changing the integrator. It remains substantially faster.

## Scientific validation

Validation ran before timing on the 32 saved distribution-aware cases, all five
named Experiment 020 cases (covering all four signed surfaces), and therefore
the saved near-horizon case. All **37/37** passed:

- exact observed/censored classification and completed-valid adapter outcome;
- exact unique attribution, link/sign and raw terminal event counts;
- one terminal candidate for every observed case and none for censored cases;
- censored integration endpoint exactly T=5;
- maximum event-time difference **6.670e-10 s** (gate 5e-8 s);
- maximum event-state component difference **5.967e-9** (gate 5e-7);
- maximum triggering residual **1.066e-14** (gate 1e-10);
- maximum native normalized energy drift **2.514e-10** and maximum diagnostic
  difference **1.517e-10** (gate 5e-9);
- maximum accepted angular increment **0.121553** (strict gate `< 0.5`); and
- maximum native solver step **0.00997735713772041 s**, equal to the declared
  cap within the existing floating-point allowance.

For transparency, the largest difference among all four reported surface
residuals was 6.176e-10. This is a non-triggering-surface consequence of the
small accepted event-state difference; the triggering residual itself passes
the task's explicit gate by four orders of magnitude. No grazing or
simultaneous-event semantics are claimed.

## Warm performance

Only after the scientific gate passed, each of the 32 distribution-aware cases
was warmed and measured seven times. All six order permutations of trusted,
compiled and native paths were rotated across cases/repetitions. Times include
the complete evaluator and unchanged adapter; native loop wall is also measured
inside that boundary.

| Outcome | Trusted evaluator median | Compiled evaluator median | Native evaluator median | Native loop median | Native/compiled speedup median |
| --- | ---: | ---: | ---: | ---: | ---: |
| Observed (16) | 23.836 ms | 11.361 ms | 0.385 ms | 0.321 ms | **30.146×** |
| Censored (16) | 49.540 ms | 23.592 ms | 0.656 ms | 0.619 ms | **36.077×** |

Means of case medians, used for weighting, were:

| Outcome | Trusted | Compiled | Native | Native loop |
| --- | ---: | ---: | ---: | ---: |
| Observed | 26.434 ms | 12.646 ms | 0.407 ms | 0.346 ms |
| Censored | 49.602 ms | 23.649 ms | 0.652 ms | 0.614 ms |

Weighting by the established 1,742 observed / 2,354 censored distribution:

```text
trusted evaluator = 39.749 ms/cell
compiled evaluator = 18.970 ms/cell
native evaluator = 0.547 ms/cell
native loop = 0.500 ms/cell

native vs compiled evaluator = 34.649x
native vs trusted evaluator = 72.604x
prior non-RHS boundary / entire native loop = 31.531x
```

The native path performs more RHS evaluations because it forms dense output on
every accepted step: observed mean 4,030 versus 3,202 for `solve_ivp`, and
censored mean 7,552 versus 6,036. This approximately 25% increase is included in
the measured native timings and is not hidden by the boundary calculation.

Cold process-local compilation/build/load was 0.911 s. The task asked for warm
boundary feasibility; build-once/load-many and spawn lifecycle belong to a later
promotion task and are not inferred from this number.

## Conservative 64² projection

The projection retains the promoted baseline's median 29.553 s total and
25.694 s evaluation, plus the post-promotion profile's fixed 6.075 s evaluation
residual for adapter/provenance, dispatch and worker imbalance. Only ideal
four-worker cell compute is replaced by the measured weighted native evaluator:

```text
native cell compute = 0.547 ms * 4096 / 4 = 0.561 s
projected evaluation = 6.075 + 0.561 = 6.635 s
projected total = (29.553 - 25.694) + 6.635 = 10.494 s
additional whole-field speedup = 29.553 / 10.494 = 2.816x
```

This exceeds the required 1.5× even while treating all previously unexplained
operational evaluation wall as fixed. An optional field was not run: the
cell-level margin is decisive, and adding investigation-only multiprocessing or
persistence infrastructure would violate the task's narrow scope.

## Limitations and promotion risks

- The root procedure is bounded bisection rather than SciPy's Brent
  implementation. It passed the accepted transversal/separated cases but needs
  explicit promotion validation at cap boundaries and against stricter oracle
  spots.
- Dense coefficients are currently generated after every accepted step. A later
  promotion must decide whether to retain this simple measured policy or enable
  on-demand dense construction without changing DOP853 semantics. It must not
  tune numerical policy merely to reduce the extra evaluations.
- The S1 source's dense counter correction must be reviewed and incorporated as
  an explicitly identified compatible artifact input; production S1 source
  identity must not be silently changed.
- The current prototype uses a temporary library and process-local Numba
  callback. Production promotion requires guarded build identity, atomic
  artifacts, worker-local callback reconstruction, unavailable-build recovery,
  provenance and strict resume compatibility.
- The accepted sample does not establish grazing, tied/simultaneous, other-T,
  other-parameter or unsupported-build behavior.
- The 64² result is projected, not measured. Promotion still needs an
  alternating operational field A/B including worker initialization,
  persistence and cleanup.

## Reproduction and validation

```bash
PYTHONDONTWRITEBYTECODE=1 \
NUMBA_CACHE_DIR=/tmp/first-flip-native-final2-numba \
MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m \
development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.benchmark_first_flip_native_dop853 \
  --repetitions 7
```

The final scientific/timing run completed in 20.78 s. Evidence:
`../evidence/current/first_flip_native_dop853_prototype.json`.

Focused prototype test and repository checks are reported with the task handoff.

**PROMOTE NATIVE FIRST-FLIP DOP853 NEXT**
