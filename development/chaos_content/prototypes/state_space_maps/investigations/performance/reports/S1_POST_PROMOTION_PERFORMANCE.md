# Lyapunov field performance after S1 promotion

The immediate target is **build-once/load-many validated S1 initialization across
recycled spawn pools**, covering both the native library and compiled callbacks.
Keep the current pool lifetime and numerical policy during that experiment.

This is the highest-return near-term target because lifecycle now consumes
**56.6% of measured 128² T=5 wall time**, and a new bounded diagnostic identifies
substantial repeated compilation inside it. However, eliminating startup alone
will not make the field inherit the successful-cell 12× speedup. **Fallback is
already the dominant warm compute cost**, and becomes more dominant with horizon.
It is the next major numerical engineering target, not a small residual.

## Evidence and scope

Used only these existing reports and their directly implicated production paths:

- `../../../PERFORMANCE_AUDIT.md`: runner timing scopes, retained-work limitations,
  historical resolution/horizon scaling, memory evidence and fallback anatomy.
- `../s1_history/S1_SOLVER_BOUNDARY_PROFILE.md`: original successful/fallback call costs and
  trusted verification/recovery execution path.
- `../s1_history/S1_COMPILED_LOOP_PROTOTYPE.md`: compiled-loop mechanism and compiler-sensitive
  numerical agreement; approximately 12× warm single-cell improvement.
- `../s1_history/S1_PROMOTION_VALIDATION.md`: broader numerical/route checks and warm timing.
- `S1_FIELD_LEVEL_BENCHMARK.md`: promoted 64² and 128² complete-run measurements,
  pool counts, route distributions and bitwise persisted equality.

Production inspection was restricted to `src/lyapunov/operational.py`, `s1.py`,
`hybrid.py`, `field_adapter.py`, and `src/generation/runner.py` and `work_units.py`.
No old raw evidence files, other investigation scripts, unrelated prototype paths
or large field artifacts were re-audited. No production file was changed.

The existing field report separates setup/evaluation/persistence, but cannot
separate current warm recovery components, cold S1 compilation components or
tile load imbalance from transport. One new diagnostic answers that question:
`../tools/probe_s1_remaining_costs.py`, with results in
`../evidence/current/s1_remaining_costs.json`.

## What the measured field times actually say

These are non-overlapping outer-wall buckets, in seconds. “Other” is subtraction,
not a measured IPC bucket. It includes creation, task preparation, compaction,
final validation/resume scans and timer-boundary remainders.

| Run | Outer wall | Setup | Tile evaluation | Persistence | Shutdown | Other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 64² S1 | 12.124 | 5.846 | 5.027 | 0.176 | 0.823 | 0.252 |
| 64² trusted | 15.434 | 2.976 | 11.056 | 0.158 | 0.993 | 0.251 |
| 128² S1 | 43.628 | 21.427 | 17.319 | 0.648 | 3.288 | 0.946 |
| 128² trusted | 68.845 | 12.772 | 50.384 | 0.737 | 4.010 | 0.942 |

At 128², S1 saves **33.065 s in evaluation**, but pays **8.655 s more setup**.
Net outer saving is 25.217 s. S1 setup is 49.1% of outer wall, shutdown 7.5%,
evaluation 39.7%, named persistence 1.5%, and other 2.2%.

There are eight pools, each limited to 2,048 **pool-wide returned cells**, not
2,048 cells per worker. Average S1 setup is 2.678 s/pool; shutdown is 0.411 s/pool.
Each pool has four separately spawned interpreters. The process-local caches in
`s1.py::native_library` and `_native_callbacks` vanish when that pool closes.
Each worker rebuilds its own temporary native library and compiles its callbacks.

The field report's suggestion that a larger grid amortises a fixed setup cost
needs qualification: **with the fixed recycling limit, the main startup cost is
not fixed per field**. Both measured grids have complete 2,048-cell pools.
Setup/pool changes from 2.923 to 2.678 s, not toward zero; setup/cell changes only
from 1.427 to 1.308 ms. Different startup timings, route mix and host effects can
explain the modest change. Increasing N alone does not amortise recycling away.

Useful unattainable upper bounds at 128², holding other work fixed:

- Remove all setup: at most **1.965×** additional speedup over current S1.
- Remove setup **and** shutdown: at most **2.307×** additional speedup.
- Remove all named persistence: only about **1.015×**.

These are ceilings, not predictions for caching. Imports, handshake, process
creation and teardown remain even after reusable native artifacts are available.
Even the impossible removal of all S1 lifecycle time leaves 18.913 s at 128²:
only 3.64× faster than the measured 68.845 s trusted run, still far from 12×.

## Direct execution-path explanation

For an eligible successful cell:

```text
runner._evaluate_bound_cell
  -> field_adapter.evaluate_lyapunov_field_cell / specification_for_cell
  -> operational.evaluate_renormalized_tangent_operational
  -> S1 eligibility/build-support checks
  -> s1.evaluate_renormalized_tangent_s1
     -> compiled RHS / DOP853 / observations / resets
     -> result and build-provenance construction
```

For an endpoint-cap recovery cell, this becomes:

```text
rejected partial S1 attempt
  -> original hybrid
     -> rejected partial trusted compiled-DOP853 attempt
     -> complete trusted compiled-DOP853 endpoint verification replay
     -> complete compiled-RHS solve_ivp DOP853 calculation
```

The accepted fallback has the original uniform `t_eval` observation policy;
native S1 observes accepted steps. Replacing fallback with native S1, relaxing
the step cap or skipping verification is not a proven equivalent acceleration.
The audit records a prior cap-translation attempt that failed the numerical gate.

The field diagnostic's retained RHS count describes only the accepted result.
It omits rejected S1/trusted attempts and verification replay. Identical retained
counts and persisted values therefore do not imply identical total work.

`runner.run_scalar_field` submits 64 individual cell tasks for each 8×8 tile,
waits for that tile, compacts it, and commits it before submitting the next tile.
There is no cross-tile queue. Faster successful cells increase the relative cost
of waiting for one or a few long fallback tasks at the tile boundary.

## New bounded diagnostic

Command, from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m development.chaos_content.prototypes.state_space_maps.investigations.performance.tools.probe_s1_remaining_costs
```

It refuses to overwrite its JSON. Rerun with a new path such as
`--output /tmp/s1-remaining-costs-rerun.json`.

Design: select 16 sparse 8×8 tiles from a 128-point periodic axis using tile rows
and columns `{0,5,10,15}`. Evaluate those **1,024 cells at each of T=5 and T=20**,
using four spawn workers and the actual per-cell runner. One fresh pool is used
per horizon. Four paired control comparisons per horizon add 512 calls per pool,
for **1,536 returned cells per pool**, below the existing 2,048 limit. No field
creation, HDF5, rendering or production numerical change occurs.

Process-local wrappers time whole existing function calls, returning their results
unchanged. The four warm phases are disjoint: S1 attempt, trusted attempt,
verification, accepted solve_ivp fallback. Callback/build timers are nested in S1
and are used separately for cold initialization, not added again to warm totals.
Raw per-cell and per-worker records, controls and build identity are retained.

Both pools stopped cleanly. All 2,048 attributed cells were valid. All eight
control comparisons (512 paired cell-result comparisons) had exact scientific
results, statuses, diagnostics and route/attempt provenance. The diagnostic uses
the currently validated macOS ARM64 build; exact Git/build identity is in JSON.

### Cold initialization

| Horizon | Pool setup | Pool shutdown | Mean callback compilation per worker | Mean native build/load per worker | Worker initializer elapsed range |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 2.967 s | 0.622 s | 0.585 s | 0.985 s | 1.423–1.769 s |
| 20 | 3.167 s | 0.451 s | 0.530 s | 0.741 s | 1.396–1.664 s |

These worker costs overlap across the four workers; **do not multiply by four
and call that pool wall**. Compilation competes for host resources. At T=5,
setup minus the longest initializer is approximately 1.198 s: process creation,
imports, handshake and other readiness costs are not eliminated by artifact reuse.

T=20 worker warm-up uses the existing base spec, which itself falls back. It
therefore also spends about 0.215 s per worker in trusted attempt + verification
+ solve_ivp. Native callback/build reuse alone will not remove that warm-up work.

### Warm per-cell attribution

Times below are means in milliseconds, measured inside the four-worker probe.
Worker total includes spec construction, selection, provenance and RSS collection.

| Horizon / route | Cells | Worker total | S1 attempt | Trusted rejected attempt | Verification replay | Accepted solve_ivp fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T=5 S1 success | 980 | 0.679 | 0.644 | 0 | 0 | 0 |
| T=5 fallback | 44 | 49.894 | 0.194 | 1.900 | 7.624 | 40.121 |
| T=20 S1 success | 896 | 2.386 | 2.346 | 0 | 0 | 0 |
| T=20 fallback | 128 | 203.089 | 1.045 | 12.519 | 30.613 | 158.844 |

Fallback is about **73.5×** the cost of a successful S1 cell at T=5 and **85.1×**
at T=20. It accounts for **76.7%** and **92.4%** of summed warm worker time in
these respective samples, despite comprising only 4.30% and 12.50% of cells.
The accepted solve_ivp calculation is about 80.4%/78.2% of a fallback cell's cost.
Rejected S1 work is only about 0.4%/0.5% of that cost. Avoiding just the extra S1
attempt cannot materially change field throughput.

Successful-cell worker overhead outside the S1 adapter is about 35–39 microseconds.
Eligibility/spec/dataclass/resource work is real at millions of cells, but is
not comparable to current lifecycle or fallback costs. The S1 adapter itself
also includes result/provenance preparation, so 0.644 ms is not pure native time.

### Tile waiting versus IPC

| Horizon | Sum tile wall | Sum worker busy / 4 | Sum per-tile maximum worker busy | Busy / four-worker capacity |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 0.998 s | 0.715 s | 0.964 s | 71.7% |
| 20 | 8.324 s | 7.033 s | 8.291 s | 84.5% |

At T=5, 0.249 s of the 0.282 s gap above perfectly balanced worker time is
explained by unequal amounts of work assigned to the busiest worker in each tile.
Only 0.034 s remains above that assigned-work bound. At T=20 those numbers are
1.258 s and 0.033 s. Transport, dispatch gaps and result handling can occur inside
the worker span too; this is not an exact isolated IPC measurement. Nevertheless,
the timing does **not** support describing the whole gap as serialization cost.
The dominant observed capacity loss is consistent with slow-cell tile tails.

This occupancy is a wall-time capacity proxy, not CPU utilisation. The probe
returns additional timing metadata and does not perform field compaction or
persistence. Control timings show host variability: instrumented/plain ratios
range about 0.97–1.36 at T=5 and 0.87–1.03 at T=20. In particular, one T=5 pair
is noisy. No correction factor or precise field-level IPC saving is inferred.

## Reconciliation with the 128² field

The sparse probe is not the full benchmark's task population. To distinguish
costs, reweight its route-conditioned means to the **measured field counts**
(15,654 successful, 730 fallback), then divide summed worker time by four.
This is an illustrative balanced-worker accounting, not another measured run.

| Component | Estimated balanced-worker seconds at 128² T=5 |
| --- | ---: |
| Successful S1 cells, including per-cell worker overhead | 2.657 |
| Rejected S1 attempts on recovery cells | 0.035 |
| Rejected trusted attempts | 0.347 |
| Full verification replays | 1.391 |
| Accepted solve_ivp fallback calculations | 7.322 |
| Remaining recovery wrapper work | 0.010 |
| Total idealised evaluation | **11.763** |
| Actual field tile-evaluation wall | **17.319** |
| Unexplained by this cross-sample balanced model | **5.556** |

That last row includes population/timing differences, imbalance, IPC and scheduling;
it must not be relabelled as measured coordinator overhead. The separate sparse
probe demonstrates why substantial tile-tail loss is plausible after S1.

This decomposition explains why another 2× improvement to the successful kernel
alone would remove only about 1.33 balanced-worker seconds at 128², whereas
repeated setup is 21.427 measured seconds and accepted fallback alone is about
7.32 balanced-worker seconds plus its contribution to tails.

Reusing/compiling trusted rejection and verification could remove at most about
1.74 balanced-worker seconds in this model if their cost vanished. Keeping the
same fallback but removing duplicate trusted work is therefore a secondary
opportunity, not a substitute for dealing with the accepted fallback computation.

## Scaling to practical fields

Let `C=N²`, pool budget `B=2048`, worker count `P=4`, and fallback frequency `f(T)`.

```text
wall ≈ fixed creation/build cost
     + ceil(C/B) × (pool setup + shutdown)
     + C × [(1-f) × successful_cost(T)
            + f × (rejected_S1 + trusted_attempt + verification + fallback)]
         / (P × effective occupancy)
     + coordinator/commit/final-validation work
```

- Imports, native compilation and callback compilation are currently **per spawned
  worker/pool**, not one-time field costs. Artifact reuse can make compilation
  fixed per compatible artifact/build, leaving a per-worker load cost.
- Successful and recovery work scale per cell and roughly with T; fallback
  frequency changes the mixture. Rejected prefix length also varies per cell/T.
- With 8×8 tiling, commits and tile barriers scale as `C/64`; transport sends one
  task/result per cell with chunksize one. Full-field validation/copies scale with C.
- Larger N does not fix a fixed `B`. Wider pools or longer lifetimes are not free
  multipliers: memory, retention and long-horizon recovery still need bounds.

### T=5 scale scenario, not a field prediction

Holding the 128² timings, four-worker hardware, route mixture and pool policy
constant gives these simple linear-in-C budgets. High-resolution historical
fallback shares are slightly lower (about 4.23–4.26% versus 4.456% at 128²), but
there is no new large-field measurement to justify a precise correction.

| N | Cells | Pools / spawned workers | Setup | Shutdown | Evaluation | Persistence + other | Total scenario |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 512 | 262,144 | 128 / 512 | 5.71 min | 0.88 min | 4.62 min | 0.43 min | **11.63 min** |
| 1024 | 1,048,576 | 512 / 2,048 | 22.86 min | 3.51 min | 18.47 min | 1.70 min | **46.54 min** |
| 2048 | 4,194,304 | 2,048 / 8,192 | 91.42 min | 14.03 min | 73.89 min | 6.80 min | **186.15 min** |

At 2048² this policy rebuilds the same native source thousands of times and makes
65,536 tile commits. A faster successful cell does not erase either count.
Historical near-linear evaluation scaling supports using C as a first-order
model, but does not validate these end-to-end forecasts or current memory limits.

### Longer horizons change the priority of compute work

The audit's historical fallback frequencies are 2.29%, 2.67%, 4.26%, 6.75% and
11.50% for T=1,2,5,10,20. These are accepted-route observations, not independent
long-horizon scientific convergence evidence. S1 preserves that fallback policy.

Reweighting the new timings to `f5=730/16384` and historical `f20=0.114971` gives:

| Quantity | T=5 | T=20 |
| --- | ---: | ---: |
| Mixed worker time per cell | 2.872 ms | 25.461 ms |
| Recovery/fallback share of worker time | 77.4% | 91.7% |
| Accepted solve_ivp share of worker time | 62.2% | 71.7% |

That is **8.87× more mixed compute for 4× the horizon** in this illustrative
post-S1 model. Successful S1 time alone rises only 3.51×. Thus fallback frequency
amplifies the remaining compute problem; the successful-cell speedup must not be
extrapolated directly to T=20 fields.

At T=20, balanced-worker compute alone is about **27.81 / 111.24 / 444.96 minutes**
for 512² / 1024² / 2048². Using the probe's 84.5% occupancy and the measured T=5
lifecycle/pool gives approximately **39.50 / 158.02 / 632.06 minutes**, before
coordinator/persistence costs. These are sensitivity scenarios, not promises:
the probe's spatial distribution and host load differ; T=20 setup and retention
can also change. They show why initialization reuse alone cannot make long-T
2048² runs inexpensive. After that reuse, fallback must be addressed.

The audit's pre-S1 512² peak-worker RSS rises from about 318 MiB at T=5 to 627 MiB
at T=20 with the same pool budget. The new short probe peaks at about 232/251 MiB,
but does not validate longer worker reuse. Do not raise or remove the 2,048 limit
based on this limited observation.

## Ranked next-step sequence

| Rank | Remaining target | Why / scope |
| ---: | --- | --- |
| **1** | **Reusable validated S1 initialization artifacts across spawn pools** | Largest measured T=5 wall bucket; 1.3–1.6 s/worker of repeated callback/build work is directly observed. No solver-policy change required. |
| 2 | Accepted solve_ivp fallback computation | Dominates warm work, especially at long T. A separately compiled fallback-equivalent loop must preserve its controller, dense/t_eval observations and gates; S1 is not a drop-in replacement. |
| 3 | Bounded cross-tile scheduling to reduce fallback tails | Current tile barrier exposes worker imbalance after fast-cell acceleration. Keep persistence tiles independent of scheduling; do not start with larger IPC chunks or whole tiles per worker. |
| 4 | Trusted rejection/verification replay cost | Real but smaller than accepted fallback. Any reuse must preserve authoritative endpoint-only verification and full-horizon error semantics. |
| 5 | Remaining imports/teardown, then safe worker reuse | Artifact reuse leaves lifecycle work. Reassess retention with the promoted mixed route before extending lifetimes; do not infer safe reuse from S1-only cells. |
| 6 | Successful-cell adapter/provenance and coordinator/persistence | Tens of microseconds per successful cell and small current wall buckets; relevant after the larger costs fall. Preserve checksums, readback, transactional completion and provenance. |

This is an engineering sequence by expected return and risk, not a claim that
startup dominates every T. At long horizons fallback is the dominant numerical
cost already. Changes to tolerances, the cap, reset policy, reflection/lift
canonicalisation, GPU batching or rendering are not the immediate target.

## Exactly one immediate optimisation target

**Build-once/load-many validated S1 initialization across recycled spawn pools.**

**Mechanism and eventual component:** change `src/lyapunov/s1.py::native_library`
and `_native_callbacks` packaging/loading so spawned workers load compatible
compiled artifacts instead of independently regenerating them. Use a build/source/
ABI-keyed artifact identity; retain process-local handles and reconstruct callback
addresses in each interpreter. A pointer address is not a shareable compiled
artifact. Cover both the C library and callback code; a C-only cache leaves the
measured roughly 0.53–0.59 s callback compilation per worker.

Do not change the pool budget, start method, equations, solver state or routing
to achieve the saving. First establish reuse at the current lifecycle. The exact
choice of prebuilt distribution versus safely cached compiled artifacts belongs
to the bounded implementation experiment, not an untested claim in this report.

**Expected payoff:** eliminating roughly 1.3–1.6 s of repeated per-worker
initialization could remove order 10–13 s over eight pools before accounting for
the initial artifact build, loading, overlap and contention differences. This is
a mechanism estimate, not additive four-worker CPU time and not a measured field
saving. An order **20–30% T=5 end-to-end reduction** is worth testing; eliminating
the complete lifecycle bucket is not credible for this target alone.

**Risks:** stale/mismatched binaries, wrong contraction flags, incompatible
Numba/LLVM/Python/NumPy ABI, bad callback lifetime/address handling, concurrent
build races, incomplete cache writes and misleading provenance. Last-bit changes
can amplify at T=20. Fail closed to the existing trusted path on unsupported or
invalid builds. Do not reuse numerical solver state or cache cell results.

**Bounded acceptance experiment:**

1. Under the identical validated environment and unchanged pool policy, compare
   repeated initialization of eight four-worker pools before/after the candidate.
   Include artifact creation in the first cold job, record cache-hit/load costs
   separately, and verify invalidated/missing/concurrently requested artifacts.
2. Run three paired, alternating-order 128² T=5 create comparisons including
   first-job artifact creation and all eight recycling events. Preserve the
   existing trusted field comparison. This is a future acceptance experiment;
   it was not run or implemented here.
3. Gate with the established numerical validation set at T=1,2,5,10,20, exact
   accepted field values/statuses/routes, recovery/provenance checks, worker
   cleanup, and unchanged memory ceiling. Include unsupported-build and corrupted
   artifact tests. No 512² or larger run is needed for this decision.

**Success:** median total setup across the eight pools is at least **40% lower**,
and median 128² end-to-end wall is at least **20% lower**, with initial artifact
creation included, no numerical/status/route gate failures, no leaked workers,
and no more than 10% increase in peak worker RSS relative to the paired baseline.
Both performance conditions must pass; a warm-cache-only microbenchmark is
insufficient. **Failure:** either threshold or any correctness/cleanup gate fails.
Do not compensate by enlarging pool lifetimes or loosening numerical policy;
retain the evidence and move the engineering priority to the accepted fallback
compute path.

## Files changed and validation

Added only this report, `../tools/probe_s1_remaining_costs.py`, and
`../evidence/current/s1_remaining_costs.json`.
The diagnostic finished at both horizons, all attributed outcomes were valid,
all controls agreed exactly, and both pools reported every worker stopped.
No production optimisation was implemented. Final source-hash and Git checks
verify the artifact matches its diagnostic and no tracked production file changed.

`git status --short`:

```text
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/S1_POST_PROMOTION_PERFORMANCE.md
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/probe_s1_remaining_costs.py
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_remaining_costs.json
```

NEXT: Build-once/load-many validated S1 native and callback artifacts across recycled spawn pools
