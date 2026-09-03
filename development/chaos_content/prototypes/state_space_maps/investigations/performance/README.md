# Finite-time-field performance investigation

**Status:** uniform resolution escalation is paused. The completed `1024 x 1024`
field is the current operational evidence; this investigation does not authorize
a `2048 x 2048` run or an optimisation.

## Motivation

The accepted `1024 x 1024` finite-time stretching field took about 80 minutes
and visibly improved on `512 x 512`, but the improvement does not justify
blindly quadrupling the cell count again. The immediate task is to account for
the observed cost and identify the cheapest measurements that could distinguish
contract-preserving optimisation opportunities from unavoidable integration
work.

## Question

> Where does the cost of the accepted `1024 x 1024` finite-time stretching
> field actually come from, and what are the cheapest measurements needed to
> identify worthwhile optimisation opportunities without changing the accepted
> scientific or numerical contract?

## Sandbox boundary

Everything under `investigations/` is sandbox-only. Investigation code may read
operational evidence and import the promoted prototype, but promoted `src/`,
supported runners, and tests must never import investigation code. A probe is
not a supported API, scientific contract, or optimisation merely because it is
recorded here.

The operational HDF5, JSON, PNG, and PDF files remain owned by
`outputs/finite_time_field/`. This investigation reads them without moving,
rewriting, or regenerating them. It is not Experiment 020 and does not alter the
numbered experiment archive.

## Frozen scientific and numerical contract

Performance work must preserve the same calculation:

- the one-vector Candidate-A finite-time stretching rate
  `sum(log(r_k)) / T` with `T = 5 s`;
- renormalisation every `0.25 s`, initial tangent `(1, 0, 0, 0)`, and zero
  initial angular velocities;
- the periodic half-open `[-pi, pi)` angular domain and stored
  `values[theta2_index, theta1_index]` orientation;
- the accepted DOP853 tolerances and resolved maximum-step contract;
- the compiled-DOP853 fast route and narrowly verified `solve_ivp` fallback;
- status/validity meanings, tile integrity, checksums, transactions, and resume
  compatibility.

Adaptive spatial refinement is a separate scientific sampling question and is
not part of this investigation.

## Operational evidence inspected

The primary evidence is:

- `outputs/finite_time_field/finite_time_field_1024.json`, SHA-256
  `09461da16ea169a85fd430eaf43f8729398cbf0f42737e4cd0bc7879e0de7970`;
- `outputs/finite_time_field/finite_time_field_1024.h5`, SHA-256
  `ba934d247363e2cefb9d5aa15d7bdf65f53de5a1876195219c5956e5ccc202dc`;
- `outputs/finite_time_field/001_512_squared/finite_time_field_512.h5`,
  SHA-256
  `f8b0e06c03720688955b6e5b4dfaa17bdf67682ac9065173c7b8d661058b33ff`.

No 512 JSON manifest is present. The 512 HDF5 does retain compatible field,
route, status, per-tile timing, diagnostics, and execution-policy provenance,
but it does not retain a total wall-time phase breakdown. Consequently, the
comparison below is defensible for persisted evaluation measurements, not for
whole-run 512-versus-1024 speedup.

The 512 artifact records Git revision `c53cac7`; the 1024 artifact records
`0c93940`. Between those revisions, the operational runner gained console
progress and the JSON manifest, while the generation algorithm, worker policy,
Lyapunov adapter, hybrid route, and scientific contract were unchanged.

The implementation inspected for accounting was the operational generation
runner, neutral scalar-field runner, work-unit planner, HDF5 transaction and
validation code, Lyapunov field adapter, hybrid evaluator, compiled DOP853
route, and compiled-RHS `solve_ivp` fallback.

## Measured 1024 x 1024 facts

The manifest reports a successful create with all cells valid and all workers
stopped:

| Quantity | Recorded value |
| --- | ---: |
| Cells | 1,048,576 |
| `8 x 8` work units | 16,384 |
| Operation wall time through oracle validation | 4,968.435 s (82:48) |
| Scalar-runner wall time | 4,958.228 s (82:38) |
| Effective scalar-runner throughput | 211.482 cells/s |
| Pool setup | 1,553.887 s |
| Tile evaluation | 2,855.321 s |
| Tile persistence | 48.226 s |
| Pool shutdown | 427.112 s |
| HDF5 size | 82,651,415 bytes (78.82 MiB) |
| Coordinator peak RSS | 308,084,736 bytes |
| Maximum worker peak RSS | 290,095,104 bytes |
| Spawn pools / recycling events | 1,024 / 1,023 |
| Fast compiled-DOP853 cells | 1,004,105 |
| Verified `solve_ivp` fallback cells | 44,471 |
| Invalid / execution-error cells | 0 / 0 |
| Oracle spots | 9, all accepted |

The recorded category shares of scalar-runner wall time are 57.59% tile
evaluation, 31.34% pool setup, 8.61% pool shutdown, and 0.97% tile persistence.
The remaining 73.683 s (1.49%) is not a named bucket. From the code it includes
coordinator work such as resume discovery, task construction, tile compaction,
progress calls, and final validation; the instrumentation cannot split it.

The 10.207 s difference between operation wall time and scalar-runner time
contains work before and after the timed scalar-runner body, including dataset
creation/planning and nine oracle checks. Those components are not timed
separately and must not be assigned individual costs.

## 512 x 512 versus 1024 x 1024

`analyze_persisted_timings.py` reads the existing HDF5 tile evidence only; it
does not import or invoke dynamics:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m \
  development.chaos_content.prototypes.state_space_maps.investigations.performance.analyze_persisted_timings \
  development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/001_512_squared/finite_time_field_512.h5 \
  development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_1024.h5
```

| Persisted measurement | 512 x 512 | 1024 x 1024 | Ratio/change |
| --- | ---: | ---: | ---: |
| Cells | 262,144 | 1,048,576 | 4.000x |
| Work units | 4,096 | 16,384 | 4.000x |
| HDF5 bytes | 20,719,184 | 82,651,415 | 3.989x |
| Tile-evaluation wall sum | 728.497 s | 2,855.321 s | 3.919x |
| Evaluation-phase throughput | 359.842 cells/s | 367.236 cells/s | +2.05% |
| Summed cell-evaluator time | 2,713.626 s | 10,658.766 s | 3.928x |
| Mean evaluator time per cell | 10.352 ms | 10.165 ms | -1.80% |
| Evaluator occupancy proxy | 93.12% | 93.32% | effectively stable |
| Recorded solver evaluations/cell | 6,680.411 | 6,680.451 | effectively stable |
| Fallback cells | 11,162 (4.258%) | 44,471 (4.241%) | stable fraction |

The evaluation work therefore scaled slightly better than the fourfold increase
in cells, not worse. The similar evaluator time, recorded solver-evaluation
count, fallback fraction, and four-worker occupancy argue against a new
resolution-specific per-cell slowdown at 1024. They do not establish total-run
scaling because the 512 phase summary is missing, and they do not justify a
runtime prediction for 2048.

The occupancy value is
`sum(cell evaluator elapsed) / (four workers * tile wall elapsed)`. It is a
useful upper-level utilisation proxy, not CPU utilisation: its approximately
6.7% gap combines dispatch, serialization, scheduling, and workload imbalance.

## Performance accounting from implementation

The following are implementation facts, not inferred timing results:

1. The planner creates row-major `8 x 8` work units. The coordinator dispatches
   each tile's 64 cells individually through `executor.map(..., chunksize=1)`;
   it does not dispatch one rectangular calculation per worker.
2. Execution uses four spawn-isolated workers. A pool is closed before its next
   tile would exceed 1,024 evaluated cells, so a full pool handles 16 full
   tiles. The 1024 run consequently created 1,024 pools and 4,096 worker-process
   lifetimes.
3. Every new worker imports the dependency path and runs one complete accepted
   hybrid evaluation as initialization warm-up. The Numba RHS/JVP is declared
   with `cache=False`, but existing evidence does not isolate compilation from
   import or other initialization cost.
4. Every cell tries compiled DOP853 first. Only the exact accepted maximum-step
   incompatibility enters the fallback: the evaluator replays compiled DOP853
   to verify endpoint-only excess and then runs the compiled-RHS `solve_ivp`
   calculation. Stored fallback diagnostics describe the returned calculation;
   they do not separately time the failed fast attempt, verification replay,
   and fallback.
5. The coordinator compacts results and owns all persistence. Each completed
   tile opens the HDF5 file in update mode and follows the accepted writing,
   payload, checksum, and completion-marker flush sequence. Final validation
   reopens and verifies the authoritative artifact.

## What current instrumentation can establish

- Numerical cell evaluation is the largest named 1024 bucket at 57.59%.
- Pool lifecycle is independently material: setup plus shutdown is
  1,980.999 s, or 39.95% of scalar-runner wall time. The observed means are
  1.517 s setup and 0.417 s shutdown per pool.
- Tile persistence at 0.97% is not a leading optimisation target for this run.
- Four-worker evaluator occupancy and evaluation throughput are stable between
  the two resolutions; cell dispatch is not showing a scaling collapse.
- Fallback occurrence strongly marks expensive tiles. At 1024, 10,604 of
  16,384 tiles contain at least one fallback. Fast-only tiles average 0.1312 s,
  while fallback-containing tiles average 0.1978 s, and fallback count has a
  `0.965` correlation with tile wall time.
- Relative to the fast-only tile mean, fallback-containing tiles account for
  705.9 s of associated excess tile wall time, 24.72% of the evaluation bucket.
  This is an association, not fallback's causal cost: those tiles may contain
  intrinsically harder trajectories and many fast-route cells.
- The p50/p90/p99/max 1024 tile wall times are 0.1566/0.2196/0.6293/1.4533 s,
  so evaluation has a real long tail even though the average scales cleanly.

## Bounded pool-lifecycle finding

`probe_pool_lifecycle.py` directly addressed whether pool setup is generic
spawn/identity overhead or is tied to the accepted scientific worker dependency
and warm-up path. It opened and closed three four-worker pools for a neutral
binding and three for the accepted binding:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m \
  development.chaos_content.prototypes.state_space_maps.investigations.performance.probe_pool_lifecycle \
  --repeats 3
```

| Probe path | Mean setup | Median setup | Mean shutdown | Mean maximum worker warm-up |
| --- | ---: | ---: | ---: | ---: |
| Neutral spawn/identity handshake | 0.227 s | 0.225 s | 0.029 s | <0.001 s |
| Accepted Lyapunov worker | 1.424 s | 1.397 s | 0.346 s | 0.339 s |

The accepted setup is close to the real run's 1.517 s/pool, and its shutdown is
close to the real 0.417 s/pool. This supports pool lifecycle as a genuine cost
centre and shows that generic spawn/handshake alone is not its main source. The
probe does not cleanly apportion scientific-module imports, Numba compilation,
the warm-up evaluation, identity synchronization, and interpreter teardown.

The probe ran 12 accepted worker warm-up evaluations in total, evaluated no
field cells, wrote no output artifact, and left all workers stopped. It is a
small same-host observation, not a general benchmark.

## What current instrumentation cannot establish

- The 512 total, setup, persistence, shutdown, and oracle-validation times,
  because its JSON manifest is absent.
- Population-level per-cell or per-route duration distributions. HDF5 retains
  only a per-tile wall duration and the sum of cell evaluator durations; the
  bounded probe below describes 16 fixed cells rather than either full route
  population.
- How much of `solve_ivp` fallback time reflects its implementation versus the
  intrinsic integration difficulty of those trajectories. The bounded probe
  separates the existing outer phases but does not provide that counterfactual.
- How pool setup divides among child imports, Numba work, accepted warm-up, and
  handshake delay; the lifecycle probe only bounds combinations of these.
- How pool shutdown divides among executor coordination and scientific-stack
  interpreter cleanup.
- Dispatch, serialization, scheduling, CPU availability, thermal effects, and
  within-tile load imbalance as separate quantities.
- HDF5 creation, final integrity validation, and individual oracle costs.
- Whether a 2048 field would preserve the same route distribution or per-cell
  timing. No such extrapolation is claimed.

Absence of these measurements is not evidence that a cost is negligible.

## Candidate hypotheses

1. **Worker lifecycle is the clearest contract-preserving target category.**
   This is supported by the real 39.95% wall share and the bounded lifecycle
   probe. The evidence does not yet choose among import reduction, compilation
   reuse, worker-lifetime changes, or another implementation technique.
2. **Fallback creates a material part of the evaluation tail, while a large
   pre-fallback difficulty effect is not supported by the bounded sample.** The
   probe below directly locates sampled time in verification and `solve_ivp`,
   but cannot split fallback-integrator cost from intrinsic difficulty or
   identify a safe optimisation.
3. **The accepted integration itself may be the irreducible majority.** Stable
   per-cell solver work and evaluator timing support this as a possibility, not
   a conclusion. The route-stratified probe below attributes the sampled
   fallback route's phases, but it does not identify a contract-preserving way
   to reduce their cost.
4. **HDF5 tile transactions are not the first target.** Recorded tile
   persistence is under 1% of the 1024 runner time. Integrity and resume
   semantics must not be weakened to pursue that small bucket.
5. **Per-cell dispatch is not presently shown to be dominant.** The 93.3%
   evaluator occupancy proxy limits the combined visible capacity gap, but does
   not separate dispatch from imbalance and is not sufficient to redesign work
   units.

## Route-stratified 16-cell measurement

The bounded probe in
[`probe_route_stratified_cells.py`](probe_route_stratified_cells.py) used the
persisted 1024 route map only to stratify the sample. Within each route stratum,
it sorted cells in row-major `(theta2_index, theta1_index)` order and selected
population ranks `floor(k * (M - 1) / 7)` for `k = 0,...,7`. This produced eight
cells from the 1,004,105-cell fast population and eight from the 44,471-cell
fallback population. A selection-only invocation recorded this fixed set
before any probe timing was run; persisted timing was not a selection input.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m \
  development.chaos_content.prototypes.state_space_maps.investigations.performance.probe_route_stratified_cells \
  development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_1024.h5 \
  --selection-only

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m \
  development.chaos_content.prototypes.state_space_maps.investigations.performance.probe_route_stratified_cells \
  development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_1024.h5
```

The following are the selected cells and observed phase times. Coordinates are
in radians, and indices follow the stored `[theta2, theta1]` orientation.
`Replay` is the full compiled-DOP853 endpoint-verification replay; `Fallback`
is the accepted compiled-RHS `solve_ivp` calculation.

| Persisted stratum | `theta2, theta1` index | `theta2, theta1` coordinate | Total (ms) | Fast attempt (ms) | Replay (ms) | Fallback (ms) | First violating segment |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Fast | `(0, 0)` | `(-3.141593, -3.141593)` | 6.548 | 6.511 | — | — | — |
| Fast | `(145, 57)` | `(-2.251884, -2.791845)` | 6.375 | 6.358 | — | — | — |
| Fast | `(294, 27)` | `(-1.337631, -2.975923)` | 6.856 | 6.839 | — | — | — |
| Fast | `(440, 420)` | `(-0.441786, -0.564505)` | 6.176 | 6.162 | — | — | — |
| Fast | `(583, 606)` | `(0.435651, 0.576777)` | 6.161 | 6.147 | — | — | — |
| Fast | `(729, 957)` | `(1.331495, 2.730486)` | 6.375 | 6.361 | — | — | — |
| Fast | `(878, 958)` | `(2.245748, 2.736622)` | 6.442 | 6.428 | — | — | — |
| Fast | `(1023, 1023)` | `(3.135457, 3.135457)` | 6.527 | 6.513 | — | — | — |
| Fallback | `(0, 12)` | `(-3.141593, -3.067962)` | 51.113 | 7.277 | 6.847 | 36.969 | 19 |
| Fallback | `(171, 983)` | `(-2.092350, 2.890020)` | 43.896 | 0.397 | 6.925 | 36.556 | 1 |
| Fallback | `(270, 470)` | `(-1.484893, -0.257709)` | 41.226 | 0.322 | 6.147 | 34.743 | 1 |
| Fallback | `(389, 47)` | `(-0.754719, -2.853204)` | 46.390 | 3.350 | 6.731 | 36.294 | 10 |
| Fallback | `(635, 171)` | `(0.754719, -2.092350)` | 44.888 | 2.657 | 6.503 | 35.714 | 8 |
| Fallback | `(754, 204)` | `(1.484893, -1.889864)` | 48.164 | 5.298 | 6.724 | 36.128 | 16 |
| Fallback | `(852, 826)` | `(2.086214, 1.926680)` | 41.063 | 0.327 | 6.143 | 34.579 | 1 |
| Fallback | `(1023, 958)` | `(3.135457, 2.736622)` | 44.569 | 2.473 | 6.466 | 35.616 | 8 |

One separate accepted hybrid call warmed the current process in 0.329 s. The
16 measured calls then ran sequentially and interleaved the strata at each
selection rank. Investigation-local wrappers timed the three existing call
boundaries without replacing their implementations or editing promoted code:
the compiled fast attempt, `_verify_endpoint_max_step_incompatibility`, and the
compiled-RHS fallback. The wrapper remainder averaged 0.018 ms for fast cells
and 0.016 ms for fallback cells. Full cell-level records, including statuses,
values, diagnostics, and selection ranks, are retained in
[`route_stratified_16_cells.json`](route_stratified_16_cells.json).

### Measured facts

| Measurement | Persisted fast (8) | Persisted fallback (8) |
| --- | ---: | ---: |
| Mean total hybrid time | 6.433 ms | 45.164 ms |
| Median total hybrid time | 6.409 ms | 44.729 ms |
| Total-time range | 6.161–6.856 ms | 41.063–51.113 ms |
| Mean compiled fast attempt | 6.415 ms | 2.763 ms |
| Mean verification replay | — | 6.561 ms |
| Mean `solve_ivp` fallback | — | 35.825 ms |
| Final solver evaluations, mean | 6,565 | 8,158 |
| Persisted/observed route agreement | 8/8 | 8/8 |
| Persisted/observed status agreement | 8/8 | 8/8 |

All 16 observed values exactly matched their persisted values at stored
precision. Each fallback candidate reproduced the accepted maximum-step
incompatibility, passed endpoint-only verification, and returned through the
persisted fallback route. The fallback-group mean was 7.02 times the fast-group
mean, a mean difference of 38.731 ms.

For sampled fallback cells, the two phases entered only because fallback was
eligible—verification replay plus `solve_ivp`—averaged 42.386 ms, or 93.85% of
their total hybrid time. The `solve_ivp` phase alone averaged 35.825 ms. This
directly explains where elapsed time occurs once a cell takes the fallback
route; it does not make the stronger claim that all `solve_ivp` time is
avoidable fallback overhead rather than integration work for that trajectory.

### Derived evidence and limits

The verification replay is the cleanest available view of a complete compiled
calculation for a fallback cell. Its 6.143–6.925 ms range and 6.561 ms mean are
close to the fast cells' complete compiled-attempt range of 6.147–6.839 ms and
6.415 ms mean. Within this small mechanically selected sample, there is no
evidence that fallback trajectories are already materially slower on the
complete compiled path before fallback. This is evidence against a large
pre-fallback trajectory-difficulty effect; it is not equivalence proof for the
full route populations.

Failed fast-attempt duration ranged from 0.322 to 7.277 ms and followed how far
the evaluator progressed before the first violating segment (segments 1–19).
Those partial attempts cannot be compared directly with complete fast-route
evaluations as a measure of intrinsic trajectory difficulty. Likewise, final
solver-evaluation counts come from different integrator implementations and do
not isolate trajectory difficulty or cost per solver evaluation.

The sample is fixed, small, unpaired, and timed sequentially in one warmed
process. It establishes phase composition and route reproducibility for these
16 cells, not population confidence intervals, worker-process timings, or a
causal counterfactual in which the same fallback cell completes on the accepted
fast route. Finer attribution inside `solve_ivp`, or a controlled same-cell
comparison that bypasses an accepted route decision, would require either
additional sandbox instrumentation or a different numerical execution and is
not justified by this measurement.

### Fallback decision

Fallback is a real, reproducibly expensive route, and the extra sampled time is
observed overwhelmingly after fallback eligibility: replay plus `solve_ivp`.
It therefore remains a meaningful secondary cost centre. The probe does not
identify a safe way to remove that work while preserving the verified fallback
semantics, and fallback represents only 4.241% of the operational 1024 cells.
It does not yet justify an independent optimisation implementation.

Worker lifecycle remains the primary investigation target because it already
accounts for 39.95% of the real scalar-runner wall time and has a demonstrated
accepted-path versus neutral-spawn gap. Fallback should be revisited only when
a specific contract-preserving alternative can be stated and tested; broad
fallback profiling is not the next cheapest decision-changing measurement.

## Cheapest next discriminating measurements

If a concrete lifecycle intervention is later proposed, the next check should
be a three-to-five-pool cold-start A/B using this same probe shape. It must keep
four spawn workers, the accepted initializer result, worker-stop verification,
and the 1,024-cell lifetime policy unless changing that operational policy is
separately justified. Synthetic evaluator/persistence probes are lower priority
because current evidence already places persistence below 1% and shows high
evaluation occupancy.

Expensive broad profiling, another uniform field, and a 2048 run are not needed
to answer these next questions.

## Acceptance and decision boundary

A performance change is worth implementing only after a bounded measurement
identifies a material real-run bucket and an A/B probe demonstrates a meaningful
same-host reduction. Any candidate must preserve values, statuses, route
classification, oracle acceptance, HDF5 integrity, and resume behavior under
the frozen scientific/numerical contract. Negative measurements are retained as
useful evidence.

## Next action

There is already enough evidence to prioritize **worker lifecycle/setup** as a
promising optimisation target category. There is not enough evidence to select
a particular optimisation, and the numerical evaluation bucket remains larger.
The completed route-stratified probe makes fallback a measured secondary cost
centre but does not expose removable work under the accepted semantics. The
next action is to formulate one concrete worker-lifecycle hypothesis and test
it with a bounded cold-start A/B before changing operational code. Uniform
resolution escalation remains paused until that decision is evidence-backed.
