# 016 Independent-cell execution boundary

**Status: planned; implementation and measurements not yet run.**

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
development/chaos_content/outputs/independent_cell_execution_boundary/
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
