# 016 Independent-cell execution boundary

**Status: accepted.** Four spawn-isolated worker processes with per-cell
dispatch are the earned bounded execution policy. This policy has not been
promoted into the prototype.

## Question

> What execution strategy should evaluate many independent initial conditions
> using the accepted scalar observable?

Experiment 016 must earn one decision: the execution policy used to evaluate
collections of independent state-space cells. It is not a tile, persistence,
or map-production experiment.

## Current earned context

The workload is the promoted
`evaluate_renormalized_tangent_compiled_fortran` scalar evaluator. Its
scientific contract was established before this experiment:

- Euler--Lagrange dynamics and exact Numba JVP;
- Candidate-A geometry;
- `T=5 s` and `0.25 s` renormalisation intervals;
- initial tangent `(1, 0, 0, 0)` and zero initial angular velocities;
- signed logarithmic stretch accumulation and physical-angle rebasing;
- the accepted DOP853 tolerances and resolved step cap;
- completed-valid, completed-invalid, and bounded execution-error semantics;
  and
- accepted-step energy observation validated against the uniform-grid
  `solve_ivp` oracle in Experiment 015.

The NumPy/SymPy plus `solve_ivp` evaluator remains the mathematical oracle.
The Numba RHS/JVP plus `solve_ivp` evaluator remains the integration-boundary
oracle. Experiment 016 schedules the promoted evaluator; it does not alter or
replace any of these scalar implementations.

## Actual execution path under investigation

The current rectangular reference path is:

``` text
run_theta1_theta2_grid
    -> construct theta1/theta2 SampleAxis records
    -> sample_rectangle: nested Python theta2-row/theta1-column iteration
    -> grid-local evaluate(theta1, theta2) closure
    -> dataclasses.replace initial state and observable specification
    -> evaluate_renormalized_tangent_compiled_fortran
    -> evaluate_renormalized_tangent_runner
    -> run_renormalized_tangent_compiled_fortran
    -> shared twenty-cycle evolve / measure / renormalise driver
    -> construct a new scipy.integrate.ode DOP853 instance per cycle
    -> Python RHS-count and accepted-step callbacks
    -> Numba Euler--Lagrange RHS/JVP
    -> RenormalizedTangentResult
    -> ScalarEvaluation
    -> RectangularCell and RectangularSamplingResult
```

Thus one `T=5 s` cell constructs twenty Fortran solver instances. Experiment
015 observed approximately 6,526--6,982 RHS calls and 535--562 accepted steps
per validation cell. Once the Numba kernel is warm, the accepted scalar path
costs approximately `7 ms` on the current development host.

The likely aggregate costs to separate are:

- Python cell iteration, coordinate bookkeeping, and result assembly;
- two per-cell dataclass replacements;
- scalar evaluator timing/error adaptation and result construction;
- Numba compilation on the first call in each interpreter;
- twenty DOP853 construction/reset lifecycles per cell;
- Python RHS and `solout` callbacks around the compiled kernel;
- executor dispatch, task collection, and ordering;
- process serialization and worker initialization; and
- coordinator plus worker memory retained by rich reference results.

The experiment must measure these boundaries rather than infer them from
single-cell timings.

## Planning inspection findings

The installed SciPy `dop853` wrapper has per-instance work arrays and supports
`solout`. Unlike the installed VODE/LSODA wrappers, its Python implementation
does not use SciPy's explicit active-global-handle concurrency guard. That is
not a documented guarantee that the legacy `ode`/Fortran callback lifecycle is
thread-safe.

Both promoted solver callbacks are Python closures. The Numba kernel is
compiled in nopython mode but not with `nogil=True`. Threads may therefore
serialize materially at callback boundaries even if independent DOP853
instances are safe. Thread execution remains a guarded empirical candidate,
not an assumed optimization.

The current grid's nested evaluation closure is not suitable as a process-pool
task. An experiment-local, module-level task must receive an explicit index,
coordinates, and fixed base specification, construct the per-cell
specification, and call the promoted evaluator. This is execution-harness code,
not a prototype API change.

A minimal planning probe on the current Python/SciPy environment established
that the frozen `RenormalizedTangentSpec` and returned `ScalarEvaluation` are
pickleable (`843` and `618` bytes respectively for the center case). The Numba
kernel uses `cache=False`, so a spawn-created worker must be expected to compile
and warm its own kernel. The current host reports eight logical CPUs. No
concurrent evaluator was implemented by this probe.

## Candidate strategies

### Sequential baseline

Retain one explicit experiment task function and execute it in deterministic
row-major order in the coordinator process. This is the scientific and
execution baseline. The existing `run_theta1_theta2_grid` result on the small
equivalence grid must also be cross-checked so the experiment task has not
changed coordinate substitution or result semantics.

### Spawn-based process pool

Retain as a full candidate. Each worker owns its Python interpreter, Numba
kernel, Fortran integrator instances, and callbacks, providing the clearest
lifecycle isolation. Use an explicit spawn context so startup and compilation
cost are visible and the result is not dependent on inheriting initialized
Numba/Fortran state through `fork`.

Compare execution widths `1`, `2`, and `4`, capped by available logical CPUs.
Measure pool creation and per-worker warm-up separately from reuse of a warm
pool. Compare per-cell dispatch (`chunksize=1`) with one mechanically defined
amortisation control,

``` text
chunksize = max(1, ceil(cell_count / (8 * worker_count))).
```

The control targets approximately eight dispatch batches per worker. It is
executor batching only: it has no spatial meaning, resume semantics, or
standing as an Experiment 017 tile.

### Guarded thread pool

Retain only behind a mandatory preflight. Independent tasks must construct
independent `ode` instances. Run repeated width-`2` and width-`4` correctness
checks and compare every outcome with sequential execution before accepting any
thread timing as evidence.

Any crash, deadlock, callback cross-talk, nondeterministic value/status, or
solver-state contamination excludes threads immediately. If correctness passes
but throughput does not improve, report that result rather than tuning the
scientific kernel for threads.

## Excluded candidates

### Concatenated or vectorized multi-cell IVP

Excluded from Experiment 016. The current promoted evaluator is pointwise.
Concatenating cells into one adaptive IVP would couple step selection and error
control, alter per-cell failure isolation, require new batch RHS/JVP and
renormalisation machinery, and no longer be a pure execution-policy comparison.

SciPy `solve_ivp(vectorized=True)` is an RHS calling convention, not an
independent-initial-condition batch executor. It does not supply the needed
equivalent boundary.

### Custom compiled batch integrator

Excluded. No such evaluator has been earned, and implementing one would reopen
the integration-method question settled for the current scalar path. If all
simple execution candidates fail to justify promotion, a separate batch-
boundary investigation is a valid Experiment 016 outcome.

### Fork-only process execution and distributed/GPU execution

Excluded from this bounded comparison. Forking already initialized
Numba/Fortran state adds a lifecycle variable without being required to test
process isolation. Distributed schedulers and GPUs introduce deployment,
serialization, and kernel changes far beyond the next earned boundary.

## Mechanically chosen workload

Use the existing inclusive bounded rectangle

``` text
theta1(0), theta2(0) in [169 deg, 189 deg]
```

with all other scientific and numerical fields fixed. Do not use the full
periodic domain: the promoted evaluator has not yet been validated across that
domain.

Use nested uniform resolutions derived from the existing `9 x 9` grid:

- `9 x 9` (`81` cells): correctness, coordinate placement, lifecycle
  preflight, invalid/error probes, and current-grid cross-check;
- `17 x 17` (`289` cells): first warmed aggregate-throughput workload; and
- `25 x 25` (`625` cells): bounded scaling confirmation.

The refinements are mechanical: `17 = 2(9-1)+1` and
`25 = 3(9-1)+1`. They retain every original grid coordinate, including the
four corners and trusted center, while increasing aggregate work without
selecting conditions for observed Lyapunov behaviour.

## Execution and timing protocol

Record host, Python, NumPy, SciPy, Numba, process start method, logical CPU
count, and relevant environment provenance.

For each retained strategy:

1. Record import/setup time and whether the Numba kernel was already compiled.
2. Record executor construction and worker-ready time separately.
3. For processes, warm every worker through its initializer before warmed
   measurements; an identity probe must return every worker's process
   identifier and initializer warm-up duration before the pool is accepted as
   ready.
4. Run the `9 x 9` equivalence/preflight workload.
5. Run three interleaved warmed repetitions of the `17 x 17` and `25 x 25`
   workloads for each applicable width.
6. Preserve the same task list and scientific specification across strategies.
7. Tear down executors explicitly and verify that no workers remain.

Report at least:

- total wall time;
- cells per second and effective seconds per cell;
- median and interquartile range across warmed repetitions;
- executor startup and worker warm-up cost;
- execution width and observed scaling efficiency;
- task-dispatch/result-collection time where separable;
- evaluator-reported elapsed-time sum versus enclosing wall time;
- task and result serialization sizes for process execution; and
- coarse coordinator and aggregate worker peak-memory evidence from the
  standard-library process resource counters, keyed by process identifier and
  normalized for platform-specific units.

Wall-clock assertions do not belong in unit tests. Timing order should be
rotated or interleaved, and any outlier policy must be declared before results
are removed or summarized.

## Numerical-equivalence and placement contract

The sequential experiment-task result is the execution baseline. The current
sequential rectangle sampler is the independent coordinate-placement oracle on
the `9 x 9` grid.

Every retained strategy must preserve:

``` text
values[theta2_index, theta1_index]
```

and must return every declared `(theta2_index, theta1_index)` exactly once.
Completion order may differ; assembled order may not.

For every cell verify:

- exact coordinate and linear-index association;
- no missing, duplicated, or unexpected cells;
- exact status, validity issues, error type, and error message semantics;
- equal segment count, max-step provenance, and numerical-validity state;
- scalar rate difference no greater than the established `1e-8 s^-1` gate;
- energy-diagnostic difference no greater than the established `1e-8` gate;
- post-renormalisation norm behaviour within the unchanged `1e-12` limit; and
- identical solver-evaluation counts where the same promoted evaluator
  completed normally.

Because the same evaluator is executed, exact scalar/diagnostic equality is
the expected result and its frequency should be reported. The existing
tolerances are fallback scientific gates, not permission to accept a weaker
concurrent implementation.

Use a separate small harness probe to verify outcome semantics:

- a deliberately strict energy limit produces completed-invalid data in the
  correct cell;
- a controlled bounded numerical `RuntimeError` becomes execution-error data;
  and
- a controlled programming/specification error propagates and fails the run
  rather than becoming a cell outcome.

Do not search for a physical initial condition that happens to make the solver
fail.

## Lifecycle and concurrency risks

The experiment must resolve or explicitly retain these risks:

- absence of a SciPy DOP853 concurrency guard is not proof of thread safety;
- Python RHS/accepted-step callbacks and a non-`nogil` Numba kernel may prevent
  useful thread scaling;
- each spawn worker pays imports and Numba compilation unless explicitly
  warmed and reused;
- a failed worker, broken pool, or task exception must not silently lose or
  duplicate coordinates;
- returning rich `ScalarEvaluation` diagnostics has serialization and memory
  cost that may be visible at the current `~7 ms` scalar time;
- oversubscription may occur if numerical dependencies create internal thread
  pools, so relevant thread-count environment settings must be recorded; and
- results may complete out of order even though final placement must remain
  deterministic.

The chosen policy needs a documented worker/executor lifecycle. Thread safety,
process isolation, warm-up, shutdown, and programming-error propagation cannot
remain implicit.

## Acceptance boundary and possible outcomes

Experiment 016 accepts an execution policy only if it:

1. preserves every numerical, status, failure, and placement contract;
2. has deterministic, complete result association;
3. has measured aggregate throughput and coarse resource evidence;
4. separates and explains startup/warm-up costs;
5. has a defensible solver, callback, and worker lifecycle; and
6. materially improves or otherwise justifies its complexity relative to the
   sequential baseline on the bounded steady workloads.

No numerical speedup threshold is predeclared. A claimed improvement must be
larger than run-to-run spread, persist on both warmed aggregate workloads, and
remain meaningful after startup and memory costs are reported. If two policies
are practically equivalent, prefer the simpler lifecycle; do not manufacture a
winner from noise.

Valid outcomes include:

- retain sequential execution because concurrency cost or risk is not
  justified;
- accept a declared thread-pool width after its safety preflight and sustained
  throughput evidence;
- accept a declared spawn-process width and dispatch policy; or
- accept none of the candidates and require a separate batch-boundary
  investigation before Experiment 017.

The output is the execution-policy decision and its evidence. It is not a
general executor framework.

## Explicit nonclaims and non-goals

Experiment 016 does not earn or implement:

- tile coordinates, tile size, spatial chunk semantics, or resumability;
- persistence, HDF5/Zarr selection, or an authoritative map dataset;
- a full-periodic-domain validation or high-resolution field;
- rendering, UI, or production integration;
- a new observable, horizon, tangent direction, validity rule, or solver;
- a custom integrator or compiled batch kernel;
- distributed, GPU, or cluster execution; or
- thread safety beyond the exact tested library versions and workload.

Temporary executor chunks are dispatch details only and must not be promoted
as the Experiment 017 tile contract.

## Stop condition

Stop when the bounded evidence supports one execution-policy decision, or
demonstrates that none of the retained scalar-evaluator strategies is worth
promotion. Do not begin tile design to rescue or embellish the result.

## Expected evidence and artifacts

The implementation pass should add only experiment-local code and focused
tests beside this README. Expected ignored evidence under

``` text
development/chaos_content/experiments/outputs/016/
```

includes a machine-readable summary containing:

- frozen workload and software/host provenance;
- cold/setup/warm timing separation;
- per-strategy and per-width throughput distributions;
- equivalence, status, placement, and failure summaries;
- process serialization and coarse memory evidence;
- lifecycle/safety findings; and
- the final execution-policy decision or explicit no-promotion outcome.

A timing plot is optional and derivative. No persisted scientific map, tile
dataset, or production asset belongs to this experiment.

## Implementation and evidence

The experiment-local harness is
`independent_cell_execution_boundary.py`. It represents every evaluation as a
module-level, pickleable `CellTask` carrying its linear index, both axis
indices, and both coordinates. The worker reconstructs the per-condition
specification from the fixed base specification and calls the existing
promoted scalar evaluator. It does not contain dynamics, tangent,
renormalisation, or solver code.

The harness executes the declared sequential, guarded-thread, and explicit
spawn-process paths, records indexed `CellOutcome` values, applies the
equivalence and failure-semantics gates, and records timing and coarse process
resource evidence. The current neutral rectangle sampler is independently
cross-checked on the `9 x 9` workload.

Run the accepted assessment with:

``` bash
uv run python development/chaos_content/experiments/execution_and_acceleration/016_independent_cell_execution_boundary/independent_cell_execution_boundary.py
```

The compact ignored evidence is written to:

``` text
development/chaos_content/experiments/outputs/016/baseline/summary.json
```

## Findings

### Runtime and cold boundary

The accepted run used macOS 15.7.9 on arm64, Python 3.12.3, NumPy 2.5.2,
SciPy 1.18.0, Numba 0.67.0, and an eight-logical-CPU host. Numerical-library
thread-count environment variables were fixed to one. The experiment module
import took `0.754 s`. The first complete scalar evaluation, including the
previously uncompiled Numba kernel, took `0.274 s`.

Spawn workers were not declared ready until each had imported its own runtime,
compiled/warmed its own Numba kernel, and returned its PID. Worker readiness
took `1.309 s`, `1.507 s`, and `1.653 s` for widths one, two, and four. The
evaluation portion of each worker's warm-up was `0.258--0.330 s`; the remainder
is spawn/import/dispatch cost. Explicit shutdown took `0.697--0.984 s`, and all
worker processes and executor threads were confirmed stopped.

### Numerical, placement, and error semantics

The current neutral rectangle sampler and the experiment's indexed sequential
task path produced the same `81` outcomes. Every scalar value and full
diagnostic record matched exactly. The result digest was
`4feb4fbb82bb6a3aa2b8826d5611774c97b8005633829c5d0b2a8a5949b65ec6`.

Both guarded thread widths and every spawn-process width and dispatch control
passed the `9 x 9` comparison. Across each comparison:

- all `81` coordinates occurred exactly once in the declared
  `values[theta2_index, theta1_index]` association;
- scalar and energy-diagnostic errors were exactly zero;
- all `81` scalar values and all `81` diagnostic records matched exactly;
- status, issues, error fields, evaluator provenance, segment counts,
  max-step provenance, and solver-evaluation counts agreed exactly; and
- the largest candidate post-reset norm error was
  `3.331e-16`, below the unchanged `1e-12` limit.

The completed-invalid probe, bounded numerical `RuntimeError` translation, and
propagating programming `ValueError` all behaved identically under sequential,
thread, and process execution. No cell was dropped, duplicated, misplaced, or
silently converted into another status.

### Warmed throughput

Each entry is the median of three interleaved warmed repetitions. The spread is
the interquartile range of wall time.

| strategy | width | dispatch | 17 x 17 wall / IQR | 17 x 17 cells/s | 25 x 25 wall / IQR | 25 x 25 cells/s |
|---|---:|---|---:|---:|---:|---:|
| sequential | 1 | direct | 2.021 / 0.068 s | 143.0 | 4.313 / 0.050 s | 144.9 |
| threads | 2 | per cell | 1.995 / 0.080 s | 144.9 | 4.628 / 0.193 s | 135.1 |
| threads | 4 | per cell | 1.982 / 0.003 s | 145.8 | 4.319 / 0.170 s | 144.7 |
| spawn processes | 1 | per cell | 2.052 / 0.085 s | 140.9 | 4.463 / 0.055 s | 140.0 |
| spawn processes | 2 | per cell | 1.021 / 0.003 s | 283.1 | 2.289 / 0.056 s | 273.1 |
| spawn processes | 4 | per cell | 0.624 / 0.052 s | 463.4 | 1.415 / 0.069 s | 441.7 |

The two-process per-cell path achieved approximately `1.98x` and `1.88x`
speedups over sequential execution. The four-process path achieved `3.24x`
and `3.05x`, or approximately 81% and 76% parallel efficiency, on `17 x 17`
and `25 x 25` respectively. Its improvement was separated from sequential
run-to-run spread on both workloads.

The mechanical amortisation controls also passed all contracts, but did not
earn a distinct policy. At width four their `17 x 17` and `25 x 25` medians
were `0.648 s` and `1.384 s`; their interquartile ranges overlapped the
per-cell results on both workloads. The simpler `chunksize=1` dispatch is
therefore retained. Executor batching remains an implementation detail, not a
tile.

Threads completed their repeated correctness preflights without observed
Fortran state contamination on this exact software stack. They did not improve
aggregate throughput. This is consistent with the Python callback and
non-`nogil` Numba boundary remaining serializing pressure, but the timing does
not by itself prove which callback or lock dominates.

### Resource interpretation

The serialized fixed specification, indexed task, and representative outcome
were `843`, `147`, and `844` bytes. Serialization volume was therefore not the
dominant cost at these cell durations.

Spawn-worker peak RSS began near `221--223 MB` after initialization. The four
worker processes reached an aggregate lifetime high-water mark of about
`1.78 GB` during the per-cell measurements, while the later amortized control
reached about `1.89 GB`. The coordinator's lifetime peak reached about
`1.95 GB` over the entire interleaved experiment. These are coarse,
process-lifetime `ru_maxrss` high-water marks: they are neither simultaneous
live-memory measurements nor evidence of a diagnosed leak. Their growth does
mean this experiment does not justify indefinitely reusing these workers for a
large field. Bounded worker lifetime and current-memory behaviour must be
resolved with the later work-unit boundary before high-resolution execution.

The sum of evaluator-reported elapsed times was approximately `3.92` times the
four-process wall time on the accepted path, consistent with useful concurrent
execution rather than coordinator-only timing artifacts.

## Verdict

**ACCEPT: use an explicit spawn-process execution boundary with four warmed,
isolated workers and per-cell (`chunksize=1`) dispatch for bounded collections
of the promoted scalar evaluator on this host.**

This policy wins because process isolation provides a defensible owner for
each Python/Numba/Fortran callback lifecycle, preserves every value, diagnostic,
status, error, and coordinate contract, and produces a sustained material
throughput improvement. The pool must be created with spawn, every worker must
warm before steady measurement or use, results must retain explicit indices,
and the pool must be shut down explicitly. Startup cost means this is not a
policy for one or a handful of cells.

The strongest earned claim is narrower than “multiprocessing scales chaos
maps”: on the declared bounded `[169 deg, 189 deg]^2`, `T=5 s` workload and the
recorded Python/SciPy/Numba stack, four warm spawn-isolated processes evaluate
independent promoted finite-time-stretching cells about three times faster than
sequential execution while returning exactly identical reference result
records.

This experiment does not promote the harness, establish a tile or worker-
recycling contract, validate the full periodic domain, explain the rising RSS
high-water marks, establish performance at other horizons, or support a
12,000 x 12,000 run. Those remain outside the claim. Experiment 017 may use the
earned process boundary while investigating a bounded rectangular work unit;
it must not treat executor chunks as already-earned tile semantics.
