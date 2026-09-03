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
- Per-cell or per-route duration distributions. HDF5 retains only a per-tile
  wall duration and the sum of cell evaluator durations.
- How fallback time divides among the failed fast attempt, verification replay,
  and `solve_ivp`, or how much of the fallback association is simply harder
  dynamics.
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
2. **Fallback and heterogeneous trajectory difficulty create a material part
   of the evaluation tail.** The persisted correlation is strong and consistent
   at both resolutions, but it cannot attribute causality or identify a safe
   optimisation.
3. **The accepted integration itself may be the irreducible majority.** Stable
   per-cell solver work and evaluator timing support this as a possibility, not
   a conclusion; route-stratified timing is still missing.
4. **HDF5 tile transactions are not the first target.** Recorded tile
   persistence is under 1% of the 1024 runner time. Integrity and resume
   semantics must not be weakened to pursue that small bucket.
5. **Per-cell dispatch is not presently shown to be dominant.** The 93.3%
   evaluator occupancy proxy limits the combined visible capacity gap, but does
   not separate dispatch from imbalance and is not sufficient to redesign work
   units.

## Cheapest next discriminating measurements

The next useful measurement is a route-stratified, single-process timing probe
over a small fixed set of coordinates selected mechanically from the persisted
1024 route map—for example eight evenly distributed fast cells and eight
fallback cells, after one unmeasured warm-up. It should record the unchanged
hybrid evaluator's total time and, from a sandbox wrapper, the fast attempt,
endpoint verification, and fallback phases. This would answer whether fallback
machinery itself explains the tile association or merely marks difficult
trajectories. Sixteen cells are enough for discrimination; a field is not.

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
Run the proposed 16-cell route-stratified timing probe next, then use its result
alongside a narrowly decomposed lifecycle measurement to choose—or reject—a
specific implementation change. Uniform resolution escalation remains paused
until that decision is evidence-backed.
