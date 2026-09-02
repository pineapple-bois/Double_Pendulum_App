# 017 Rectangular work-unit boundary

**Status: planned; implementation and measurements not yet run.**

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
