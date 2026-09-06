# First-flip compiled RHS: pre-promotion review

**The evidence is sufficient to make compiled RHS the next production-promotion
task, but not sufficient to enable it without that task's operational validation.**
No demonstrated numerical blocker or larger competing bottleneck warrants a
separate optimisation investigation first. Keep the existing event algorithm and
trusted Python RHS; promotion must close the bounded gaps below before activation.

## Scope inspected

- `FIRST_FLIP_COMPILED_RHS_FEASIBILITY.md`; its two tools,
  `../tests/test_first_flip_compiled_rhs.py`, and
  `../evidence/current/first_flip_compiled_rhs_feasibility.json`.
- `src/first_flip/{reference,field_adapter,__init__}.py`, relevant first-flip
  tests, and `runners/generate_first_flip_periodic_field.py` (paths relative to
  the state-space-maps root).
- Shared `generation/runner.py` and HDF5 definition/compatibility/checksum code,
  only for worker initialization, route selection, persistence and resume.
- `PERFORMANCE_AUDIT.md` only for its first-flip coverage and applicability.

No broad audit, benchmark rerun, large-file scan or field generation was performed.
Production code and the investigation implementation remain unchanged.

## Assessment of the feasibility evidence

The implementation changes only the physical four-state RHS. It passes a bound
Numba callable through `first_flip_time(..., _rhs_override=...)`; the same function
still owns DOP853, its tolerances and max-step, four terminal positive-direction
signed revolution surfaces, continuous lifted angles, root refinement, attribution,
energy/increment diagnostics and censoring. There is no tangent-system or S1
native-loop substitution. This is an appropriately narrow numerical change.

The saved evidence contains 37 distinct cases: all four signed events and one
near-horizon fixture, plus 16 observed-time and 16 censored spatial quantiles.
All 37 comparison records pass. Four recorded source hashes match the current
tools/reference/adapter. Worst differences are event time **1.368e-13 s**, event
state **1.707e-12**, surface residual **1.688e-13**, and normalized energy
diagnostic **1.099e-14**, comfortably inside the declared gates. Event identities,
raw event counts and RHS counts match. Evidence is strong for the tested standard
T=5 transversal cases; it is not proof for arbitrary parameters, horizons or
ill-conditioned crossings.

Warm timing is credible as a feasibility measurement: both paths are warmed,
order alternates over nine repetitions, and the timer surrounds the complete
result plus adapter. Outcome weighting uses arithmetic means of per-cell medians,
not a misleading unweighted median of speedups. The weighted compute ratio is
**2.0878×**; the reported whole-field estimate recomputes to **1.8017×**.
It remains an estimate: no compiled operational field was measured.

One important timer distinction: `FirstFlipResult.wall_seconds` and the adapter's
`elapsed_seconds` cover `solve_ivp`, excluding postprocessing; the feasibility
tool's outer timer includes postprocessing. Do not treat persisted per-cell
diagnostic wall times as equivalent to that benchmark timer.

## Material gaps, ranked

| Priority | Gap and consequence | Minimum closure during promotion |
| --- | --- | --- |
| 1 | **Spawn/lifecycle and trusted recovery are untested for the candidate.** Current initialization warms cached symbolic dynamics; the compiled tool has `@njit(cache=True)` but no operational initializer, eligibility selector or recovery policy. Cache availability is not evidence of spawn safety or native-code readiness. Initializer failure can break a pool rather than fall back. | Warm and bind the numeric callable inside each worker; test cold/cache-hit starts, recycling, JIT-disabled/unavailable or failed initialization, and trusted recovery. Keep a known working Python RHS and propagate programming errors. |
| 2 | **Boundary and negative-outcome coverage is incomplete.** The near-horizon event is around 4.795 s, not an exact-cap test. Slow crossings/competing-event margins are not deliberately sampled. The comparator checks matching adapter status/outcome, but does not explicitly require completed-valid adapter results, compare adapter issue tuples, or directly assert the angular-increment gate. Two matching invalid adapter outcomes can therefore pass its current checks. | Add explicit validity/increment assertions for valid cases; retain deliberate invalid/failure cases with expected statuses. Test cap equality and nearby censoring, attribution rejection and low-speed/separated events without inventing tie/grazing tolerances. |
| 3 | **Route identity and resume are not implemented.** The prototype identity is recorded in benchmark JSON, while `adapt_first_flip_result` still labels candidate results `solve_ivp_first_flip_reference`. The binding and field vocabulary contain only that route. | Add a distinct compiled route and accepted/attempted recovery provenance; preserve the trusted route. Test definition/binding agreement and persisted route codes. Never label compiled output as the Python implementation. |
| 4 | **Build support and cache identity are incomplete.** Evidence records Python/NumPy/SciPy/Numba versions, platform and source hashes, but does not establish a supported CPU/LLVM matrix or cache failure behaviour. `cache=True` neither defines a compatibility policy nor measures cold cost. | Record kernel digest, NumPy/SciPy/Numba/llvmlite/LLVM and CPU/platform identity and numerical compilation flags. Gate supported builds; use trusted RHS otherwise. Test unavailable/unusable caches. This is Numba RHS compilation, not S1's per-worker external C-library build. |
| 5 | **The 1.80× field gain is unmeasured.** It assumes unchanged non-evaluation wall and effective scheduling. Compiled warm-up, symbolic fallback preparation, pool recycling and cell/tile imbalance could change it. | A paired bounded field benchmark must include cold initialization, recycle, writes, final validation and cleanup. Separate setup, evaluation, persistence and shutdown. |

HDF5 compatibility is intentionally strict: `assert_dataset_compatible` compares
the canonical full definition (including evaluator/software provenance and route
vocabulary), axes and tile plan/static digest. A new compiled definition should
**not silently resume an old reference-defined file**. Test rejection before any
write; continuing an old field requires its original compatible trusted definition
and binding. Do not edit an existing file's provenance to force compatibility.
Same-definition interrupted resume must still work. This is a promotion integration
gate, not a reason to redesign persistence.

The existing adapter rejects nonunique attribution and zero triggering speed;
those checks do not establish scientific resolution of near-ties or grazing.
Promotion should preserve the accepted transversal/separated scope, not claim
new event guarantees. Python-RHS recovery must not turn a numerical failure into
right-censoring or silently accept an unsupported event.

## Did PERFORMANCE_AUDIT materially cover first-flip?

**Yes, in a meaningful but limited way.** Its “First-flip field” execution trace
distinguishes the four-state lambdified flow from Lyapunov's tangent system. It
examines the 32² pilot's 4.95 million RHS calls, 13.192 s evaluation, 3.855 s setup
and 0.042 s persistence, and L4 specifically identifies per-RHS validation/numeric
expression work plus unnecessary Jacobian preparation in cached dynamics.
It recommends exactly a compiled four-state RHS under the unchanged event solver.

It was **not a first-flip high-resolution bottleneck study**: its detailed N/T
scaling, route replay, worker retention and occupancy evidence is predominantly
Lyapunov-specific. Those conclusions must not be transferred to first-flip. The
present feasibility work provides the stronger first-flip RHS attribution and
512²-based estimate; there is no need to extend the whole audit now.

## Does another obvious bottleneck change the next step?

No. In the feasibility baseline, evaluation is **85.4%** of 3,994.485 s; all
non-evaluation work is **583.049 s / 14.6%**. Even removing that entire latter
bucket would yield only **1.171×**, versus the estimated **1.802×** from RHS
compilation. The representative trusted RHS accounts for about 58.5% of evaluator
time. That directly supports the proposed change.

The current worker caches dynamics once per parameter set, so symbolic work is
not repeated per cell. Avoid accidentally retaining mandatory symbolic setup on
every successful compiled worker if it erases startup gains; measure the chosen
trusted-fallback preparation strategy. Retain the four-worker spawn/2,048-cell
pool policy for the initial promotion. Tile barriers, duplicated small diagnostic
objects and repeated HDF5 transactions exist, but no first-flip evidence makes
them a larger immediate opportunity. A new event driver or solver is unnecessary.

## Minimum production-promotion acceptance gates

1. **Narrow eligibility and independent oracle.** Initially enable only the
   measured standard equal-link/unit-parameter, zero-velocity T=5 policy and
   validated builds. Other currently accepted specs continue through Python RHS.
   Keep the default trusted `first_flip_time` and stricter reference spots
   independent; do not redirect the oracle through compiled dispatch.
2. **Scientific checks.** Replay all 37 saved coordinates; require event-time
   difference `<=5e-8 s`, event-state component difference `<=5e-7`, triggering
   residual and residual difference `<=1e-10`, each normalized energy drift and
   its difference `<=5e-9`, accepted angular increment **strictly <0.5**, and exact
   observed/censored/invalid/failure classification, attribution, link/sign,
   raw event counts, adapter issue tuples and RHS counts for these regression
   fixtures. Require completed-valid outcomes explicitly where expected. Compare
   the final adapted dimensionless scalar, converting the physical time tolerance
   by the gravity timescale; do not require bitwise event-time equality.
3. **Small targeted edges.** Add the existing evidence's low-crossing-speed and
   small competing-margin cases where retained, with a few neighbouring inputs
   and stricter trusted solves. Exercise periodic lifts without wrapping the
   integrated state. Test synthetic exact-cap, tied/unresolved, zero-speed,
   invalid-energy/increment and solver-failure result adaptation, plus a small
   numerical event/censor boundary bracket. At the cap the field value is exactly
   the cap and strict `<` thresholds remain unchanged. Do not expand eligibility
   or loosen gates to accommodate a disagreement.
4. **Worker and recovery checks.** Run a small four-worker spawn batch through
   the real adapter, comparing each outcome to the serial trusted oracle. Force
   cold and cache-hit initialization and unavailable compilation/build support;
   establish bounded trusted selection rather than failed initializer loops.
   Test that numerical rejection remains invalid/error unless an explicitly
   recorded trusted replay yields an accepted result. Do not catch arbitrary
   programming exceptions or manufacture censored results.
5. **Bounded field/persistence/performance gate.** Use three paired,
   alternating-order **64² T=5** create runs with the unchanged 8×8 tiles and
   2,048-cell pool budget, exercising two pools per run. Include cold worker costs
   and report cache state. Require identical axes/status/censor masks, exact cap
   values, observed-time differences within `5e-8 s`, correct route/attempt
   provenance, authoritative checksum validation, stricter spots and all workers
   stopped. Use a tiny interrupted/resumed fixture for same-definition recovery,
   mismatched-definition rejection and compiled-unavailable trusted-route
   persistence. Require median whole-field speedup **>=1.5×**, matching the
   feasibility decision threshold, with setup and peak worker RSS reported.
   No 512² run is needed. Failure of any scientific or operational gate blocks
   activation; a warm-cell win alone does not override it.

These are acceptance tests for the next promotion task, not additional optimisations
or a new numerical algorithm. None was implemented in this review.

## Inexpensive checks performed

```bash
PYTHONDONTWRITEBYTECODE=1 NUMBA_CACHE_DIR=/tmp/first-flip-review-numba \
MPLCONFIGDIR=/tmp/double-pendulum-mpl .venv/bin/python -m pytest -q -p no:cacheprovider \
  development/chaos_content/prototypes/state_space_maps/investigations/performance/tests/test_first_flip_compiled_rhs.py \
  development/chaos_content/prototypes/state_space_maps/tests/first_flip -k 'not tiny_field'
```

Result: **16 passed, 1 deselected in 4.92 s**. The field-generating test was
excluded; these tests do not close the compiled-route spawn/persistence gap.
Numba cache products were directed outside the repository.

Read-only inline Python checks parsed the referenced feasibility JSON, asserted
all 37 comparison/check sets pass, recomputed the worst errors and 1.801727 field
estimate, and checked all four recorded SHA-256 source fingerprints: **all match**.
`rg`, `sed`, `cat`, `git diff --check` and `git status --short` supplied the source
inspection and final checks. The historical 54-test result remains reported
evidence, not a claim that this review reran that entire suite.

Only this review file was added. Final `git status --short`:

```text
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/reports/FIRST_FLIP_PRE_PROMOTION_REVIEW.md
```

PROMOTE COMPILED RHS NEXT
