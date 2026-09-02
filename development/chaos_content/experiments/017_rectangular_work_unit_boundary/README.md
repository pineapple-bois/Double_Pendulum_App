# 017 Rectangular work-unit boundary

**Status: accepted.**

## Question

> What rectangular unit of work gives efficient execution, deterministic
> coordinates, bounded memory, failure isolation, and resumability?

Experiment 017 must earn one capability: a reusable rectangular work-unit
contract. It is not the persistence experiment and it does not produce a
high-resolution map.

## Earned starting point

The scientific calculation remains the promoted
`evaluate_renormalized_tangent_compiled_fortran` scalar evaluator with the
unchanged `T=5 s`, `0.25 s` renormalisation, Candidate-A, tangent, solver, and
validity contracts. The two `solve_ivp` paths remain its scientific and
integration-boundary oracles.

Experiment 016 accepted the bounded collection policy on its tested host and
stack:

``` text
four warmed spawn-isolated workers
    + indexed per-cell dispatch (chunksize=1)
    + promoted scalar evaluator
```

Its `17 x 17` and `25 x 25` workloads were about `3.24x` and `3.05x` faster
than sequential execution and exactly reproduced the sequential outcomes.
Threads did not improve throughput. Process startup was approximately
`1.3--1.7 s`, so pools must be warmed and reused for bounded collections.

Experiment 016 deliberately did not earn spatial work units. Its
`CellTask` is a degree-based benchmark record; its process `chunksize` is only
an executor transport detail; and its result retains one rich
`ScalarEvaluation` per cell. Rising lifetime RSS high-water marks also left
indefinite worker reuse unresolved.

## Current path and architectural pressure

The reference rectangle path currently constructs explicit `SampleAxis`
objects, iterates in theta2-row/theta1-column order, substitutes both angles
into an observable specification, and retains nested `RectangularCell`
objects. Arrays are derived afterward with shape

``` text
(theta2_samples, theta1_samples)
```

and indexing

``` text
values[theta2_index, theta1_index].
```

Experiment 016 instead constructs a flat row-major sequence of indexed cells
and sends each cell independently to a process pool. This proves the execution
boundary but does not say:

- which cells form one spatial completion and retry unit;
- how local indices map into a larger global domain;
- how edge rectangles are represented;
- when partial results become a completed unit;
- how much rich cell data may remain resident; or
- how long a warm worker pool may safely live.

Experiment 017 must make those points explicit without moving persistence or
storage concerns forward from Experiment 018.

## Work-unit definition under investigation

A candidate tile is a half-open rectangle in **global index space**:

``` text
theta2 indices [y_start, y_stop)
theta1 indices [x_start, x_stop)
```

for a declared global field shape `(theta2_samples, theta1_samples)`. Its local
shape is `(y_stop - y_start, x_stop - x_start)`, and the only valid mapping is

``` text
global_theta2_index = y_start + local_theta2_index
global_theta1_index = x_start + local_theta1_index
```

The corresponding coordinates must be looked up from the one global theta2
and theta1 axes. A tile must not independently regenerate a `linspace`, infer
coordinates from its physical endpoints, wrap an angle, or include a local
endpoint by convention. Those alternatives can create round-off disagreement
or duplicate periodic states at tile boundaries.

A deterministic work-unit identity is the declared domain/resolution plus the
four index bounds and the observable/evaluator provenance. A traversal ordinal
is not part of identity because tile order may change. Experiment 017 need not
freeze an opaque identifier, hash, class name, or persistence encoding.

Tiles are logical completion, validation, and retry units. They are **not**
process tasks by definition. The starting candidate executes the cells within
one tile through the accepted four-worker pool with indexed per-cell dispatch,
waits for that tile attempt to resolve, compacts or summarizes its results,
then releases transient rich cell outcomes. One rectangle is not assigned to
one worker, and executor `chunksize` does not acquire spatial meaning.

## Candidate work-unit policies

Retain an untiled whole-field submission as the throughput and numerical
control. Compare it with tile-at-a-time barriers using this mechanically
defined set of index shapes, written as
`(theta2_cells, theta1_cells)`:

``` text
(1, 1)    lower-bound control: one cell cannot occupy four workers
(4, 4)    sixteen cells: four cells per accepted worker
(8, 8)    sixty-four cells: sixteen cells per accepted worker
(16, 16)  256 cells: larger retry and transient-result unit
(4, 16)   64-cell theta1-wide aspect control
(16, 4)   64-cell theta2-tall aspect control
```

The powers of two are index-space refinements around the four-worker execution
width, not conventional image-tile choices. The two 64-cell rectangles isolate
orientation from cell count. The single-cell and untiled controls expose the
two extremes of dispatch/barrier overhead versus failure and retry
granularity.

Do not add more shapes merely to smooth a timing curve. A refinement is allowed
only if adjacent retained candidates straddle a decision without overlapping
timing evidence, or if the memory/lifecycle evidence rules out all otherwise
competitive candidates. Any refinement must bisect the unresolved dimensions
mechanically and be recorded before it is run.

## Mechanically chosen workloads

### Coordinate and coverage workload

Use a coordinate-only full-periodic domain with

``` text
theta1_samples = 33 = 4(9 - 1) + 1
theta2_samples = 25 = 3(9 - 1) + 1.
```

The unequal resolutions exercise the API's independent-axis contract. Both
dimensions leave edge tiles for the power-of-two candidates. Generate these
coordinates only through `PeriodicAngularDomain` /
`full_periodic_angle_axis`. No dynamics are needed to prove coverage, and this
test must assert that every coordinate is in `[-pi, pi)` and neither axis
contains `+pi`.

### Numerical and timing workloads

Use the same inclusive bounded degree rectangle as Experiment 016,

``` text
theta1(0), theta2(0) in [169 deg, 189 deg],
```

at `17 x 17` and `25 x 25`. These mechanically nested resolutions retain the
previous reference coordinates and avoid claiming that the promoted evaluator
has been scientifically validated across the full periodic domain.

The `17 x 17` field is the correctness and first timing workload. The
`25 x 25` field confirms that any conclusion survives the larger bounded
collection. Use three interleaved warmed repetitions per candidate. Rotate the
candidate order across repetitions; do not remove timing outliers after seeing
the result.

## Coordinate, orientation, and coverage contract

For every candidate shape on the coordinate-only periodic workload:

1. Generate clipped edge bounds with `min(start + extent, axis_samples)`.
2. Record a coverage-count array with global field shape `(25, 33)`.
3. Map every local cell to its global pair and increment that pair once.
4. Require the final coverage array to equal one everywhere.
5. Require the sum of tile cell counts to equal `33 * 25`.
6. Require every tile bound to be nonempty, in range, and half-open.
7. Verify edge-tile local shapes explicitly on both axes.
8. Verify global coordinates by direct lookup against the existing periodic
   axis helpers.
9. Require `values[local_theta2_index, local_theta1_index]` to assemble only at
   `values[global_theta2_index, global_theta1_index]`.
10. Repeat with reversed tile traversal and a deterministic permutation of
    local cell order; coverage and the assembled coordinate field must remain
    identical.

The implementation should also construct a deliberately overlapping plan and
a deliberately gapped plan and prove that validation rejects both. It must not
rely on a plausible assembled image to establish coverage.

## Numerical-equivalence contract

The untiled Experiment-016-style four-process evaluation is the numerical
baseline. For every tiled candidate on the bounded `17 x 17` and `25 x 25`
workloads, compare by global index rather than completion order.

Require:

- exactly one result for every expected global cell;
- identical coordinates and coordinate-to-state substitution;
- exact status, validity issues, error type, and error message semantics;
- equal evaluator identity, segment count, max-step provenance, numerical
  validity, and solver-evaluation count;
- finite-time rate absolute error no greater than `1e-8 s^-1`;
- energy-diagnostic absolute error no greater than `1e-8`;
- post-renormalisation norm error within the unchanged `1e-12` limit; and
- the same observable specification and global axes.

Because the same scalar evaluator is used, exact values and diagnostics are
expected and their frequency must be reported. The tolerances are fallback
scientific gates, not permission for tile-dependent numerical differences.

Run one correctness pass in row-major tile/local order and one with reversed
tile order plus a deterministic local-task permutation. The assembled values,
statuses, exceptional details, and provenance summaries must be identical.

## Failure isolation, interruption, and retry

Use a small mechanically indexed test domain and experiment-local controlled
faults; do not search the dynamics for convenient failures.

The evidence must distinguish:

- a completed-valid cell, retained as a finite value;
- a completed-invalid cell, retaining its finite value and declared issues;
- a bounded scalar numerical `RuntimeError`, retained as execution-error cell
  data by the existing evaluator boundary;
- a programming/specification `ValueError`, which propagates and invalidates
  the run rather than becoming cell or tile data; and
- an explicitly injected work-unit/executor failure outside the scalar
  adapter, which fails that tile attempt rather than fabricating cell results.

If any non-cell-data task fails during a tile attempt, no partial cells from
that attempt count as a completed tile. Previously completed unrelated tiles
must remain byte-for-byte unchanged, and later unrelated work must not inherit
the failed tile's coordinates or results. Catch only an experiment-declared
operational work-unit failure or a specifically identified executor lifecycle
failure; unexpected programming exceptions still propagate.

Retry the failed work unit from its immutable domain, bounds, and scientific
specification, preferably through a fresh pool for the recovery check. Require
the reconstructed global/local task association to match the original exactly
and the successful retry to equal a clean uninterrupted evaluation.

Also exercise an in-memory interruption boundary: complete a mechanical prefix
of the tile plan, stop before the next tile, reconstruct the same plan, skip the
already completed work-unit identities, and finish the field. The result must
equal uninterrupted execution. This demonstrates deterministic resume
information only; Experiment 018 owns durable resume state and atomic storage.

## Memory and process lifecycle investigation

Measure tile/result memory outside timed regions where practical. Record both
coordinator and worker observations at pool-ready, before and after tile
attempts, after an assembled field, and before shutdown.

On the current macOS host, collect:

- `resource.getrusage(...).ru_maxrss` as a lifetime high-water mark; and
- current RSS by PID using the host process-status facility, sampled between
  evaluations rather than inside solver timing.

Record units and collection failures explicitly. Do not interpret
`ru_maxrss` decreases, infer current residency from a high-water value, or
call monotonic allocator retention a leak without deeper evidence.

For each tile candidate measure:

- transient rich-result count and serialization size;
- compact-array byte count and serialization size as a representation control;
- coordinator RSS change while assembling and after releasing rich outcomes;
- per-worker current and peak RSS keyed by PID;
- cells evaluated by each worker; and
- total and maximum per-tile wall time.

After choosing a provisional performance/correctness candidate, reuse one warm
pool for a mechanically bounded `2048`-cell lifecycle sequence. Sample memory
at pool-ready and after at least `256`, `512`, `1024`, and `2048` completed
cells, always at tile boundaries. Repeating coordinates is acceptable for this
lifecycle measurement; it is not scientific field evidence.

If current RSS plateaus within measurement resolution, retain one warm pool for
the bounded run and report the observed range. If current RSS continues to
grow materially, activate only the predeclared recycling controls: recreate
the entire pool between tiles after approximately `512` or `1024` completed
cells. Record warm-up cost, total throughput, RSS reset, and exact numerical
equivalence. Never recycle a pool midway through a tile attempt.

A recycling limit is earned only if current-memory evidence requires it and a
tested limit actually resets the observed residency while preserving useful
throughput. If current RSS cannot be measured defensibly, the experiment may
accept only a bounded pool-per-run lifecycle and must leave indefinite worker
reuse as an explicit nonclaim.

## Result-representation question

Compare, rather than assume, these experiment-local representations:

1. the current rich per-cell `ScalarEvaluation` outcomes; and
2. compact tile arrays plus sparse exceptional-cell details and tile-level
   summaries.

At minimum a completed tile result must preserve:

- global field shape and both global coordinate-axis specifications;
- half-open tile bounds and local shape;
- scalar values in `(local_theta2, local_theta1)` array order;
- a status value for every local cell with a one-to-one mapping to the existing
  `EvaluationStatus` vocabulary;
- sparse global/local-indexed validity issues and execution-error details;
- observable specification and evaluator identity;
- counts by status;
- maximum energy drift and post-reset norm error;
- aggregate solver-evaluation count and evaluator elapsed time;
- tile-attempt wall time and attempt number; and
- enough immutable identity information to reproduce the work unit.

Finite completed-invalid scalar values must not be discarded or replaced by
`NaN`. A missing value is permitted only when the existing `ScalarEvaluation`
has `value=None` (for example an execution error or a non-finite invalid
result), and the separate status array must retain that distinction. A tile
failure is attempt metadata, not a fourth scalar evaluation status.

The compact candidate may use `float64` values and an in-memory compact status
code if the mapping is explicit and round-trips exactly. Pickle size and NumPy
array bytes are measurement controls only; they do not choose an Experiment
018 storage format. No durable schema, checksum, compression, or file layout is
earned here.

## Timing and decision protocol

Keep one warmed four-process pool per interleaved timing block. Within a tile,
submit indexed cells with `chunksize=1`; complete and compact one tile before
starting the next. Record pool startup/warm-up separately and exclude it from
warmed tile throughput while also reporting end-to-end cost.

For each candidate report:

- tile count and edge-tile shapes per workload;
- median and interquartile range of total field wall time;
- cells per second and effective seconds per cell;
- distribution of per-tile wall times;
- evaluator elapsed-time sum versus wall time;
- process utilization or cells per worker;
- result-compaction time;
- coordinator and worker memory evidence;
- failed/retried tile counts; and
- numerical/coverage acceptance summaries.

First discard any candidate that fails coverage, numerical, status, failure,
retry, or lifecycle gates. A performance improvement or loss is meaningful
only when its timing spread is separated on both bounded workloads. If several
candidates overlap the fastest acceptable timing spread on both workloads,
prefer the smallest work unit because it provides finer retry/failure and
memory granularity. Prefer a square over an equal-cell rectangular shape when
their evidence overlaps; do not encode orientation without a measured reason.

If no one size is stable across both workloads and the lifecycle study, report
the Pareto set or a bounded policy/range rather than manufacture a fixed size.
Any accepted rule must be expressed in index cells, state its edge behaviour,
and include any earned pool-lifetime bound.

## Acceptance boundary

Experiment 017 accepts a rectangular work-unit contract only if it:

1. maps local indices deterministically to global coordinates;
2. covers each declared domain exactly once without periodic duplication;
3. preserves `values[theta2_index, theta1_index]` globally and locally;
4. reproduces untiled values, statuses, issues, errors, and provenance;
5. is invariant to tile and local-cell traversal order;
6. bounds transient coordinator memory and has a defensible tested worker-pool
   lifetime for the bounded regime;
7. confines a work-unit failure without accepting its partial results;
8. reconstructs and retries the same work unit deterministically;
9. supports an in-memory interrupted/resumed assembly equivalent to an
   uninterrupted run;
10. records sufficient tile timing, validity, diagnostics, and provenance for
    a later persistence decision; and
11. selects a fixed scale, bounded range, or mechanical rule from measured
    throughput/memory/failure tradeoffs rather than convention.

A valid outcome is that no candidate deserves promotion, or that only a range
can be earned. Failure to resolve indefinite worker memory does not permit a
silent unbounded lifecycle claim.

## Explicit nonclaims and non-goals

Experiment 017 does not earn or implement:

- HDF5, Zarr, or any other persistent field backend;
- durable resume metadata, dataset checksums, or file-backed scheduling;
- a storage chunk shape or an assumption that storage chunks equal execution
  tiles;
- a full-periodic Lyapunov-equivalence claim;
- a high-resolution or `12000 x 12000` field;
- rendering, UI, or production integration;
- a new observable or a change to the finite-time Lyapunov contract;
- a custom integrator, compiled batch kernel, thread policy, GPU, or
  distributed executor;
- one-process-per-tile ownership;
- dynamic/adaptive spatial refinement; or
- thread safety or performance beyond the already bounded Experiment 016
  evidence.

The experiment may describe the information that persistence will need, but
Experiment 018 owns its durable encoding, integrity, atomicity, and resume
protocol.

## Stop condition

Stop once the bounded evidence accepts or rejects a rectangular work-unit
policy and records any required worker-lifetime bound. Do not add persistence,
rendering, or a larger field to make the result appear more complete.

## Expected evidence and artifacts

The implementation pass should add only experiment-local tile planning,
assembly, measurement, controlled-failure, and focused-test code. It may use
Experiment 016 as the untiled execution/evidence oracle, but the new tile
contract must not inherit its degree-specific `CellTask` as a spatial model.
Scientific and coordinate contracts should be imported from the prototype
modules rather than copied.

Compact ignored evidence should live under:

``` text
development/chaos_content/outputs/rectangular_work_unit_boundary/
```

It should contain:

- environment and frozen scientific/execution provenance;
- candidate shapes and exact generated bounds;
- coverage and periodic-coordinate results;
- numerical, status, placement, and order-invariance comparisons;
- failure, retry, and in-memory interruption evidence;
- per-shape timing distributions;
- rich-versus-compact size evidence;
- current and peak memory observations with measurement limitations;
- any recycling comparison activated by the refinement rule; and
- the accepted work-unit policy/range or explicit rejection.

No persisted scientific field, tile dataset, or rendered map belongs to this
experiment.

## Implementation and evidence

The experiment-local implementation is
`rectangular_work_unit_boundary.py`. It imports Experiment 016's accepted
spawn-worker lifecycle and per-cell evaluator adapter, together with the
prototype's observable and periodic-domain contracts. It adds no prototype
API. Its focused tests are in `test_rectangular_work_unit_boundary.py`.

The retained machine-readable evidence is ignored by Git at:

``` text
development/chaos_content/outputs/rectangular_work_unit_boundary/baseline/summary.json
```

The accepted run used macOS 15.7.9 on arm64, Python 3.12.3, NumPy 2.5.2,
SciPy 1.18.0, Numba 0.67.0, eight logical CPUs, four spawn workers, and
executor `chunksize=1`. Numerical-library thread counts were fixed to one.

### Coordinate, coverage, and order findings

Every candidate exactly covered the coordinate-only `(25, 33)` periodic
field. All `825` expected global cells occurred once, all local indices mapped
by offset into `values[theta2_index, theta1_index]`, and all coordinates came
from the shared half-open axes. No `+pi` endpoint occurred. Reversed tile
traversal and reversed local traversal produced the same assembled coordinate
field. Deliberately duplicated and omitted `8 x 8` work units were rejected,
detecting `64` overlapped and `64` missing cells respectively.

For the accepted `8 x 8` shape, the full-periodic coordinate workload produced
`20` work units with clipped local shapes `(8, 8)`, `(8, 1)`, `(1, 8)`, and
`(1, 1)`. This is coordinate-contract evidence only; no full-periodic
Lyapunov field was evaluated.

Every candidate also reproduced the untiled process result exactly on the
bounded `17 x 17` and `25 x 25` fields. Across the retained row-major and
permuted checks there were no missing, duplicate, misplaced, status-mismatched,
issue-mismatched, error-mismatched, or provenance-mismatched cells. Scalar and
energy-diagnostic differences were exactly zero. All `289` and `625` scalar
records and available diagnostic records matched exactly, and the largest
post-reset Candidate-A norm error was `3.331e-16`, below the unchanged
`1e-12` limit. Every candidate produced the same `17 x 17` field digest in
both traversal orders.

### Status and failure findings

The bounded scientific workloads were not all successful: the promoted scalar
evaluator returned `(valid, invalid, error)` counts of `(275, 0, 14)` for
`17 x 17` and `(606, 0, 19)` for `25 x 25`. Direct inspection showed that the
errors were bounded `RuntimeError` outcomes from the promoted evaluator's
declared `max_step` enforcement. Tiling reproduced their coordinates, status,
type, message, and absent values exactly; it did not create or hide them.
Reported field energy maxima (`9.152e-10` and `3.260e-10`) and reset errors
therefore summarize completed evaluations, not the execution-error cells.
This pre-existing evaluator behaviour is an explicit limitation to resolve
before treating a later assembled field as a scientifically complete map.

The controlled `4 x 4` fault workload produced `14` valid cells, one finite
completed-invalid cell, and one bounded scalar execution-error cell. An
injected work-unit failure left no partial result for that work unit and did
not change previously completed units. Reconstructing its immutable identity
and tasks produced a clean second-attempt result. Reconstructing a plan after
an in-memory interruption skipped the same two completed work units and
matched uninterrupted assembly. A controlled programming `ValueError`
propagated instead of becoming data. These checks earn an in-memory retry and
completion boundary, not durable resume state.

### Timing findings

Each entry is the median of three interleaved warmed repetitions; brackets
show the first and third quartiles. Pool startup is excluded.

| policy / tile shape | `17 x 17` wall [Q1, Q3] | cells/s | `25 x 25` wall [Q1, Q3] | cells/s |
|---|---:|---:|---:|---:|
| untiled control | 0.526 [0.522, 0.539] s | 549.2 | 1.133 [1.124, 1.169] s | 551.4 |
| `1 x 1` | 2.039 [2.035, 2.040] s | 141.8 | 4.460 [4.455, 4.545] s | 140.1 |
| `4 x 4` | 0.562 [0.557, 0.568] s | 514.6 | 1.208 [1.198, 1.267] s | 517.2 |
| `8 x 8` | 0.552 [0.545, 0.589] s | 523.1 | 1.157 [1.152, 1.213] s | 540.1 |
| `16 x 16` | 0.549 [0.538, 0.570] s | 526.2 | 1.198 [1.195, 1.209] s | 521.7 |
| `4 x 16` | 0.637 [0.587, 0.637] s | 453.9 | 1.154 [1.153, 1.187] s | 541.7 |
| `16 x 4` | 0.537 [0.537, 0.559] s | 537.7 | 1.204 [1.178, 1.274] s | 519.2 |

The fastest median was `16 x 4` on `17 x 17` and `4 x 16` on `25 x 25`, so
the experiment did not earn an orientation-specific rectangle. The `8 x 8`
spread overlapped each corresponding fastest spread; `16 x 4` also qualified,
but both contain `64` cells and the predeclared square preference selects
`8 x 8`. The `1 x 1` barrier exposed the expected loss of worker occupancy.
No geometric refinement was triggered because a declared candidate satisfied
the correctness and overlapping-spread rule on both workloads.

For `8 x 8`, effective median cost was `1.912 ms/cell` and `1.852 ms/cell`.
The maximum observed tile attempt was `0.204 s` and `0.154 s`; median total
compaction cost was below `2 ms` per field. Evaluator elapsed sums were about
`3.76x--3.81x` wall time, consistent with the retained four-worker execution
policy. Warm tile barriers made `8 x 8` only about 5% slower than the untiled
control on `17 x 17` and about 2% slower on `25 x 25` in the retained medians.

### Result-representation findings

An `8 x 8` attempt holds at most `64` rich outcomes transiently. On the
`25 x 25` workload, the maximum rich tile pickle was `14,150` bytes, the
corresponding compact tile pickle was `3,368` bytes, and its `float64` value
plus `uint8` status arrays occupied `576` bytes. Summed compact serialization
was `40,872` bytes versus `140,817` bytes for rich outcomes, a ratio of
`0.290`. Compact arrays plus sparse exceptional details and tile summaries are
therefore the accepted in-memory result boundary. This comparison does not
define a persistence schema or storage dtype contract.

### Memory and lifecycle findings

Live RSS was sampled by PID between tile attempts; `ru_maxrss` remained a
separate lifetime high-water measure. With one warm pool reused for `2,048`
evaluations, median worker current RSS rose from about `222.3 MB` at readiness
to `267.6 MB` after `1,024` cells and `312.5 MB` after `2,048` cells. Total
growth was `90,226,688` bytes and growth after the midpoint was `44,900,352`
bytes, exceeding the experiment's predeclared operational material-growth
checks of 32 MiB total and 16 MiB after `1,024` cells. Coordinator current RSS
remained `171,851,776` bytes at every lifecycle checkpoint; its observed
lifetime peak was `188,153,856` bytes.

This activated both declared recycling controls. Recycling after `512` cells
used four pools and took `11.393 s` end to end. Recycling after `1,024` cells
used two pools and took `8.054 s`; both preserved exact numerical results,
stopped every worker, and reset new-pool ready medians to about `222--223 MB`.
The unrecycled control took `6.115 s`, so recycling has a measurable startup
cost. The earned lifecycle rule is therefore to recreate the entire pool only
at tile boundaries after at most `1,024` completed cells. This is a bounded
operational policy, not a diagnosis of a leak or evidence about indefinite
worker reuse.

## Verdict

**ACCEPT: use `8 x 8` nominal rectangular work units, expressed as half-open
global `(theta2, theta1)` index bounds with clipped edge tiles, and recycle the
four-worker spawn pool at tile boundaries after at most `1,024` cells.**

Each tile is a completion, validation, retry, timing, and compact-result unit;
it is not assigned to one worker. Its cells retain Experiment 016's indexed
per-cell dispatch. A completed tile contains local `(theta2, theta1)`
`float64` values, explicit `uint8` statuses with a reversible vocabulary,
sparse exceptional-cell details, aggregate diagnostics, evaluator/scientific
provenance, attempt metadata, and immutable global bounds. Partial outcomes do
not complete a failed tile.

The strongest earned claim is that, for the two bounded declared workloads on
the recorded host and stack, this `8 x 8` work-unit contract covers and
assembles the domain deterministically, is invariant to traversal order,
exactly preserves the untiled evaluator's values and result semantics, confines
and retries controlled work-unit failures, keeps rich coordinator retention to
one tile, and has a measured worker-lifetime bound. It does not claim that
`8 x 8` is optimal for another host, observable, horizon, full-periodic
Lyapunov field, persistence backend, or high-resolution production run.

The next stage may investigate persistence using this earned logical
completion unit, but it must keep storage chunking conceptually independent.
Before assembled scientific map validation, the promoted evaluator's bounded
`max_step` execution-error cells found in these workloads require a focused
contract audit; Experiment 017 does not alter or reinterpret them.
