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
- What causes worker current RSS to grow: the retained measurements cannot
  distinguish live Python state, native allocations, allocator retention, or
  another dependency-level resource effect, and they do not diagnose a leak.
- Dispatch, serialization, scheduling, CPU availability, thermal effects, and
  within-tile load imbalance as separate quantities.
- HDF5 creation, final integrity validation, and individual oracle costs.
- Whether a 2048 field would preserve the same route distribution or per-cell
  timing. No such extrapolation is claimed.

Absence of these measurements is not evidence that a cost is negligible.

## Candidate hypotheses

1. **Worker lifecycle is the clearest contract-preserving target category.**
   This is supported by the real 39.95% wall share and the bounded lifecycle
   probes. The extended-lifetime measurement below shows a real RSS tradeoff,
   so it supports a bounded longer-lifetime A/B rather than unlimited worker
   reuse. It does not yet choose a production limit or implementation change.
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

## Worker-recycling boundary decomposition

### Historical origin and accounting semantics

The lifecycle rule originated in Experiment 017, committed in `8622586`, after
Experiment 016 had reported rising worker lifetime high-water marks but had
explicitly declined to call them live memory or a leak. Experiment 017
predeclared a single warm-pool sequence of 2,048 evaluations, current-RSS
checkpoints at 256, 512, 1,024, and 2,048 pool-wide cells, material-growth
checks of 32 MiB overall and 16 MiB after 1,024 cells, and—only if those checks
triggered—recycling controls at 512 and 1,024 cells.

The historical current-RSS measurements did trigger both checks. Median worker
RSS rose from 222,257,152 bytes at pool readiness to 267,583,488 bytes after
1,024 pool-wide evaluations and 312,483,840 bytes after 2,048. That is
90,226,688 bytes total growth, including 44,900,352 bytes after the midpoint.
The repeated 64-cell task set remained numerically equivalent throughout and
the unrecycled 2,048-cell pool stopped normally; the evidence found growth, not
a failure threshold.

Both predeclared controls reset new-pool ready RSS and preserved exact results.
The 512-cell control used four pools and took 11.393 s, while the 1,024-cell
control used two and took 8.054 s; the unrecycled control took 6.115 s. The
experiment selected the largest successful declared control to retain more
useful throughput. Thus 1,024 was a conservative accepted operational bound,
not a scientifically demonstrated cliff, a maximum imposed by the evaluator,
or proof that 2,048 cells were unsafe.

Experiment 019 (`85fe08d`) then exercised that rule in the assembled `64 x 64`
pipeline, and the promoted runner copied it in `0b8895c`. The rationale that
still applies is narrow: bound observed process residency and reset it at a
deterministic tile boundary while retaining spawn-process failure isolation.
The historical lifecycle used the then-promoted `numba_rhs_fortran_dop853`
evaluator. It did not establish the source of the RSS growth, and it preceded
the current hybrid evaluator, so current-path measurement remained necessary.

The current implementation's variable is `cells_in_pool`, not a per-worker
counter. After one entire tile's `executor.map` returns, the runner adds
`len(outcomes)`; before the next tile it recycles if the accumulated returned
outcomes plus that tile's planned cell count would exceed 1,024. Consequently:

- the unit is cell outcomes returned across the whole four-worker pool;
- accounting advances only after a complete tile attempt returns normally;
- all returned statuses count, including a bounded execution-error result;
- worker initializer warm-ups and identity-handshake tasks do not count;
- individual workers need not receive equal shares; and
- recycling occurs between tiles, never partway through one.

For full `8 x 8` tiles, one accepted pool handles 16 tiles, or 1,024 pool-wide
cells. Even division would be about 256 cells per worker, but that is not the
contract or an enforced individual limit.

### Current hypothesis and bounded probe

The current hypothesis was that extending a worker lifetime would avoid
material setup/shutdown cost but might exchange that time for continuing
per-process RSS growth. The smallest useful probe therefore needed current
RSS and throughput beyond the accepted boundary, while preserving the actual
scientific worker initializer and evaluator.

[`probe_worker_lifetime.py`](probe_worker_lifetime.py) opened one accepted
four-worker spawn pool and cycled the eight mechanically selected fast-route
cells already retained by the route-stratified probe. This avoids a rectangular
field, persistence, and unnecessary fallback work while preserving the exact
accepted finite-time specification. The task stream was fixed before running.
It retained Experiment 017's 256/512/1,024/2,048 checkpoints and added one
predeclared doubling to 4,096 pool-wide cells to distinguish an early plateau
from continuing growth in the promoted hybrid worker.

```bash
MPLCONFIGDIR=/private/tmp/state_space_maps_lifetime_mpl \
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m \
  development.chaos_content.prototypes.state_space_maps.investigations.performance.probe_worker_lifetime
```

Each worker completed the unchanged initializer warm-up before the readiness
snapshot. Every subsequent window used accepted per-cell dispatch with
`chunksize=1`. The probe observed individual PIDs with `ps`, retained the
worker-reported lifetime peak, recorded completed tasks per PID, and compared
every returned route, status, value, diagnostics record, issues, and error
fields exactly with the prior accepted evidence.

The retained run performed four initializer evaluations plus 4,096 measured
cell evaluations, 0.391% of the operational 1024-squared field. An initial
sandboxed preflight performed four initializer evaluations but stopped before
any measured task when the sandbox denied `ps`; its four workers were closed
and later confirmed absent. Total scientific evaluations performed during this
task were therefore 4,104, of which exactly 4,096 belong to the retained
lifetime measurement.

### Measured checkpoints

| Pool-wide completed cells | Cumulative cells/worker | Median worker RSS | Median growth from ready | Window throughput | Mean evaluator time | Occupancy proxy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 221.59 MiB | 0 | — | — | — |
| 256 | 63–65 | 231.66 MiB | 10.05 MiB | 543.6 cells/s | 7.210 ms | 97.99% |
| 512 | 127–129 | 242.48 MiB | 20.77 MiB | 540.1 cells/s | 7.224 ms | 97.54% |
| 1,024 | 254–258 | 264.12 MiB | 42.48 MiB | 550.1 cells/s | 7.126 ms | 98.00% |
| 2,048 | 509–514 | 306.16 MiB | 84.56 MiB | 529.7 cells/s | 7.417 ms | 98.22% |
| 4,096 | 1,018–1,029 | 392.65 MiB | 171.05 MiB | 538.0 cells/s | 7.303 ms | 98.24% |

All four workers grew at every checkpoint. Final current RSS ranged from
406,732,800 to 412,925,952 bytes, with per-worker growth from readiness ranging
from 176,128,000 to 180,011,008 bytes. A descriptive linear fit across each
worker's cumulative task count and RSS growth is 0.1666 MiB per individual
completed cell with `R² = 0.99992`. This describes the observed bounded shape;
it is not a leak rate or an extrapolation beyond 4,096 pool-wide cells.

Window throughput ranged from 529.7 to 550.1 cells/s, a 3.77% range around its
mean, and the final window was 1.0% slower than the first. Mean evaluator time
varied non-monotonically from 7.126 to 7.417 ms. There is no measured throughput
degradation with worker age in this run. Coordinator current RSS rose by 5.39
MiB, far less than the approximately 171 MiB median per-worker growth.

Setup, including four worker warm-ups and the identity handshake, took 1.453 s.
Final shutdown took 0.615 s, every worker stopped, and all eight PIDs from both
the aborted preflight and retained run were later absent. One final shutdown
does not establish how shutdown time scales with worker age.

### Correctness and resource interpretation

All 4,096 measured outcomes retained the compiled-DOP853 route and
completed-valid status. Every value and diagnostics record matched the prior
accepted result exactly; no issue or error field changed. There is no evidence
of stateful scientific drift, route instability, correctness loss, worker
failure, or performance decay over this bounded task stream.

There is also no plateau in current RSS within the measured range. Growth is
approximately proportional to work and closely repeats Experiment 017's shape
through 2,048 cells, despite using the current hybrid evaluator and fast-only
cells. This strengthens the resource rationale for bounded recycling and shows
that fallback is not required for the observed growth. It does not identify
whether the bytes are live state, native-library allocations, allocator
retention, or another process-local effect, and it must not be called a memory
leak without that evidence.

The probe is one same-host lifetime over eight repeated fast cells. Repetition
is appropriate for isolating worker age and was accepted for Experiment 017's
lifecycle test, but it does not reproduce full-field trajectory heterogeneity.
It does not test fallback-heavy work, memory pressure on the host, multiple
concurrent pools, lifetimes beyond 4,096 pool-wide cells, or repeated long-life
shutdowns. Nothing here supports unbounded worker reuse.

Machine-readable checkpoints and per-PID evidence are retained in
[`worker_lifetime_4096_cells.json`](worker_lifetime_4096_cells.json).

### Recycling decision

The current boundary is **protective in category but conservative in its exact
value**. Recycling demonstrably caps and resets continuing worker residency;
1,024 itself was selected as the larger of two successful predeclared controls,
not located as a failure threshold. The promoted probe shows that a 2,048-cell
pool remains correct and maintains throughput, but raises median current RSS by
84.56 MiB per worker from readiness, versus 42.48 MiB at the accepted boundary.

This is enough evidence to justify testing—not adopting—a 2,048-cell bounded
lifetime as the first runner optimisation candidate. It is not evidence for
4,096 as a production limit: that point adds about 171 MiB per worker and was
included to establish the non-plateau shape.

On a full-tile 1024-squared run, a 2,048-cell schedule would mechanically halve
the pool count from 1,024 to 512. Applying half of the observed 1,980.999 s
lifecycle bucket suggests about 990 s of potentially avoidable lifecycle time.
That arithmetic shows why the candidate is worth measuring; it is not a speedup
prediction because longer-lived shutdown cost, host memory pressure, and
full-field behaviour have not been measured under the candidate schedule.

## Preregistered 1,024-versus-2,048 A/B

### Question and fixed design

The A/B asked how much active policy wall time is saved by omitting the
midpoint four-worker lifecycle, and what worker RSS is added by allowing the
same pool to cross from 1,024 to 2,048 returned cell outcomes. Policy A was the
accepted sequence of two 1,024-cell pools; Policy B was one 2,048-cell pool.
Nothing else changed.

[`probe_worker_lifetime_ab.py`](probe_worker_lifetime_ab.py) used the same
ordered scientific stream for every run: the eight mechanically selected
persisted-fast cells from the route probe, repeated cyclically 256 times and
partitioned into thirty-two ordered 64-cell batches. Its full-stream SHA-256
was fixed as
`77ef4095246df80472f0d9ffc852e07670310d6bea18bf729cdeb709e55bb38d`.
Both policies processed the same first and second 1,024-cell halves; only A
closed and replaced the pool between them. This isolates worker lifetime and
does not deliberately overrepresent fallback work.

The preregistered paired order was:

```text
repetition 1: A then B
repetition 2: B then A
repetition 3: A then B
```

A `--design-only` invocation printed that order and stream digest before any
timing run. The experiment then ran exactly three A and three B repetitions,
with no sample expansion. Each A repetition created eight worker-process
lifetimes and required eight initializer evaluations; each B repetition
created four lifetimes and required four initializer evaluations. The complete
measurement therefore contains 12,288 timed scientific cells plus 36 required
initializer warm-ups.

The primary `active wall` measure is the phase sum
`setup + scientific evaluation + shutdown`. It excludes RSS subprocesses,
correctness comparisons, JSON construction, and coordinator garbage collection
so Policy A is not penalized for the extra observations required by its second
pool. The separately retained outer wall includes that observation work and
supports the same conclusion.

### All six runs

| Sequence | Pair/order | Policy | Pools | Setup | Evaluation | Shutdown | Active wall | Evaluation throughput | Maximum endpoint worker RSS |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1/A-first | A | 2 | 3.269 s | 3.827 s | 0.917 s | 8.013 s | 535.1 cells/s | 265.91 MiB |
| 2 | 1/B-second | B | 1 | 1.474 s | 4.207 s | 0.520 s | 6.202 s | 486.8 cells/s | 307.34 MiB |
| 3 | 2/B-first | B | 1 | 1.482 s | 3.803 s | 0.460 s | 5.746 s | 538.5 cells/s | 306.06 MiB |
| 4 | 2/A-second | A | 2 | 2.885 s | 3.743 s | 0.849 s | 7.476 s | 547.2 cells/s | 264.53 MiB |
| 5 | 3/A-first | A | 2 | 2.868 s | 4.448 s | 0.826 s | 8.142 s | 460.4 cells/s | 264.75 MiB |
| 6 | 3/B-second | B | 1 | 1.618 s | 4.629 s | 0.480 s | 6.727 s | 442.5 cells/s | 308.16 MiB |

Policy A's two pool lifetimes, Policy B's 1,024 and 2,048 checkpoints, all
per-PID current and peak RSS observations, task counts, route/status counts,
and exact comparisons are retained separately in
[`worker_lifetime_ab_2048_cells.json`](worker_lifetime_ab_2048_cells.json).

### Paired wall and lifecycle comparison

| Pair | A active wall | B active wall | B saving | B saving | Removed lifecycle | B evaluation penalty |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8.013 s | 6.202 s | 1.811 s | 22.60% | 2.191 s | 0.380 s |
| 2 | 7.476 s | 5.746 s | 1.731 s | 23.15% | 1.791 s | 0.060 s |
| 3 | 8.142 s | 6.727 s | 1.415 s | 17.38% | 1.596 s | 0.181 s |

The candidate saved time in all three pairs. Mean active wall was 7.877 s for
A and 6.225 s for B: a mean paired saving of 1.652 s, or 21.04% of the
accepted-policy time. Individual savings ranged from 1.415 to 1.811 s. Outer
wall including observation averaged 8.078 s for A and 6.383 s for B, a similar
1.695 s difference.

Mean lifecycle time was 3.871 s for A and 2.012 s for B. Avoiding the midpoint
pool saved 1.859 s of lifecycle time on average: 1.482 s of setup/warm-up and
0.377 s of shutdown. B's scientific evaluation phase was 0.207 s slower on
average, offsetting 11.1% of that lifecycle benefit and leaving the observed
1.652 s net saving. The expected mechanism therefore explains the total-wall
result; no unexplained speedup in numerical evaluation is needed.

### Evaluation throughput

The scientific phase was not identical between policies. Mean evaluation time
was 4.006 s for A and 4.213 s for B. Using aggregate cells divided by aggregate
evaluation time gives 511.2 cells/s for A and 486.1 cells/s for B, a 4.91%
lower candidate throughput. B's evaluation time was longer in every pair by
1.6%, 4.1%, or 9.9%.

This is a modest, consistent paired difference and must not be hidden. It is
also not evidence that worker age caused the difference: within B, the second
1,024-cell half was slower than the first in two runs and faster in one, and
the interleaved host timings varied materially for both policies. With only
three pairs, the cause and repeatability of the approximately 5% aggregate
evaluation difference remain unresolved. The lifecycle saving is large enough
that B still reduced total wall in every pair.

### RSS tradeoff

Within Policy B, median worker RSS rose by 41.75, 42.02, and 42.39 MiB between
the 1,024 and 2,048 checkpoints. Comparing each run's maximum endpoint worker
RSS, B incurred 41.44, 41.53, and 43.41 MiB more than paired A, for a 42.13 MiB
mean additional per-worker endpoint. B's maximum endpoints were
306.06–308.16 MiB; A's were 264.53–265.91 MiB. The worker-reported lifetime
peaks agreed with these observed endpoint maxima at the measurement resolution.

One A repetition's second fresh pool ended at an unusually low 227.43 MiB
median despite completing correctly; its first pool reached the normal 264.75
MiB maximum. The cause is not instrumented and may reflect allocator or OS
residency behaviour. The paired resource comparison therefore uses maximum
endpoint RSS across both A pools rather than silently treating that low
terminal sample as the protective boundary. The raw terminal observation is
retained in the evidence.

The candidate's explicit bounded resource price is consequently about 42 MiB
of additional current RSS per worker, or about 168 MiB across four workers, for
this task stream. This is consistent with the preceding lifetime probe and is
not evidence for a plateau, a leak diagnosis, or safety beyond 2,048 cells.

### Correctness and termination

All 12,288 returned cell outcomes preserved the fixed ordered task stream and
the compiled-DOP853 fast route. Every status remained completed-valid, and
every value, diagnostics record, issue list, and error field exactly matched
the prior accepted evidence. There were no correctness failures. All 36 worker
processes stopped cleanly and were independently confirmed absent after the
probe.

### Decision and limitations

The A/B is positive for treating 2,048 as a **promoted-runner optimisation
candidate**, not for changing the runner immediately. It gives a repeatable
17.38–23.15% active-wall benefit attributable to one removed pool lifecycle,
with exact scientific stability and a quantified approximately 42 MiB
per-worker RSS cost. It does not justify unlimited reuse, 4,096 as another
candidate, or a universal 2,048 limit.

Before changing the promoted default, the candidate still needs a focused
runner-level validation that:

1. exercises actual `run_scalar_field` tile traversal with the explicit
   2,048-cell execution spec in a temporary artifact, including create/resume,
   pool-count, provenance, integrity, and worker-stop assertions;
2. includes a mechanically fixed representative fast/fallback route mix and
   oracle checks, because this A/B deliberately isolated lifecycle with
   fast-only cells;
3. confirms the roughly 5% evaluation-throughput difference is either
   repeatable and accepted within the net benefit or attributable to bounded
   host/order noise; and
4. makes the approximately 168 MiB aggregate worker-RSS increase an explicit
   host resource acceptance criterion.

Only after those checks pass should a separate implementation task change the
accepted default and its documentation/tests. This measurement did not invoke
the runner, persistence, create, or resume.

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
The completed A/B justifies 2,048 as a bounded promoted-runner optimisation
candidate, not as the new policy. The next action is the focused runner-level
validation above, with the observed evaluation-throughput difference and
approximately 168 MiB aggregate worker-RSS increase treated as explicit gates.
No production limit or implementation should change before that evidence is
accepted. Uniform resolution escalation remains paused.
