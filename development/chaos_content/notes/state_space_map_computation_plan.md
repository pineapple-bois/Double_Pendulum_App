# State-space map computation plan

**Status: completed through Experiment 019; the bounded local-pipeline exit
condition is earned.**

## Purpose and destination

This note defines the next earned sequence from one trusted scalar observable
to efficient, trustworthy two-dimensional state-space fields. It is a roadmap
of research questions and acceptance boundaries, not an implementation or
package design.

The destination is a validated, resumable, throughput-characterised
scalar-field generator whose numerical output is authoritative and can be
rendered later without rerunning the underlying dynamics.

``` text
trusted scalar observable
    +
promoted fast scalar evaluator
            |
            v
016  execution boundary
            |
            v
017  tile boundary
            |
            v
018  persistence boundary
            |
            v
019  assembled map-scale validation
            |
            v
high-resolution state-space field generation
```

Each experiment earns one new capability. A later stage must not absorb an
unresolved decision from an earlier one merely to produce a larger run.

## Earned starting point

The repository already contains:

- a NumPy/SymPy plus `solve_ivp` mathematical oracle;
- a Numba RHS/JVP plus `solve_ivp` integration-boundary oracle;
- the promoted Numba RHS/JVP plus Fortran DOP853 fast scalar evaluator;
- coordinate-neutral completed-valid, completed-invalid, and execution-error
  outcomes for one scalar evaluation;
- explicit line and sequential rectangular reference sampling;
- the array convention
  `values[theta2_index, theta1_index]`;
- the canonical full periodic angular domain
  `theta1, theta2 in [-pi, pi)`, with no duplicated `+pi` endpoint;
- a small JSON reference field whose heatmap can be rendered without
  recomputing the observable; and
- Experiment 015 evidence for the declared five-condition, `T=5 s` evaluator
  contract and its accepted-step energy diagnostic.

These are reference contracts, not a map engine. In particular, the current
neutral rectangle sampler executes sequentially and retains rich Python
objects per cell. That is appropriate for inspectable reference grids but is
not presumed to be the large-field execution or storage representation.

## Frozen scientific contract

Experiments 016--019 may change how independent evaluations are scheduled,
grouped, retried, or stored. They must not silently change:

- the finite-time observable semantics or result meaning;
- the Euler--Lagrange dynamics;
- the tangent/JVP semantics;
- Candidate-A geometry;
- initial tangent-direction and renormalisation semantics;
- signed logarithmic stretch accumulation;
- solver and numerical-validity policy;
- valid, invalid, and bounded execution-error distinctions;
- coordinate-to-initial-state substitution;
- `values[theta2_index, theta1_index]` orientation; or
- the half-open periodic-domain convention.

The promoted Fortran DOP853 evaluator is the current fast implementation. The
two `solve_ivp` paths remain the mathematical and integration-boundary oracles.
For apparatus validation, the current declared `T=5 s`, `0.25 s`
renormalisation, `(1, 0, 0, 0)` tangent, zero initial angular velocities,
Candidate-A geometry, tolerances, and step cap remain fixed unless a separate
scientific experiment earns a change.

This freezes the instrument used to evaluate computation machinery; it does
not claim that this horizon or observable is a final production-map choice. A
scientific-contract change would require renewed reference equivalence before
the computation sequence could rely on it.

## 016 -- execution boundary

**Research question:** What execution strategy should evaluate many
independent initial conditions using the accepted scalar observable?

This experiment may compare sequential, process-based, thread-based, or
batch-oriented approaches where they are actually viable. It must not select a
winner in advance. The mechanically chosen workload, cold/setup treatment,
and warmed timing method must be declared before results are interpreted.

The acceptance boundary is an execution policy that:

- reproduces the sequential promoted-evaluator values, statuses, validity
  issues, and coordinate association under the established tolerances;
- preserves programming/specification errors rather than converting them into
  cell data;
- isolates only the already bounded numerical execution failures;
- has measured throughput, setup cost, memory behaviour, and deterministic
  output ordering; and
- has a justified lifecycle model for Numba and SciPy's Fortran DOP853
  interface.

The earned output is an execution-policy decision for collections of cells,
not a map engine, tile contract, or storage system.

## 017 -- tile boundary

**Research question:** What rectangular unit of work gives efficient
execution, deterministic coordinates, bounded memory, failure isolation, and
resumability?

This experiment starts only after 016 has selected an execution policy. It
must preserve explicit independent theta axes, the half-open periodic domain,
and

``` text
values[theta2_index, theta1_index].
```

The acceptance boundary is a reusable rectangular work-unit contract that:

- maps tile-local indices unambiguously to global theta1/theta2 coordinates;
- covers a declared domain exactly once, without gaps, overlaps, or duplicated
  periodic endpoints;
- produces the same field values and statuses regardless of traversal order;
- bounds peak memory and confines execution failure to the affected work unit;
- can be retried to reproduce the same coordinates and scientific
  specification; and
- records enough tile-level timing, validity, and provenance for later
  execution and resume decisions.

No tile size is frozen here. Experiment 017 must select it from measured
execution, memory, and failure-isolation evidence. Its output is a tiled
evaluation boundary, not persistence.

## 018 -- persistence boundary

**Research question:** How should completed numerical tiles become an
authoritative, resumable, verifiable scalar-field dataset?

This is the first stage allowed to choose a storage technology. HDF5 remains a
leading local-scientific candidate and Zarr remains viable, but neither is an
earned commitment before Experiment 018 compares the needs of the accepted
tile and execution contracts.

The persistence contract must preserve at least:

- domain, axes, resolution, coordinate units, periodic convention, and array
  orientation;
- observable, physical, numerical, evaluator, and software provenance;
- scalar value dtype and any status/validity dtype;
- completed-valid, completed-invalid, execution-error, and not-yet-computed
  distinctions without requiring rich Python objects per cell;
- tile completion and resume state;
- deterministic association between stored cells and coordinates;
- integrity or checksum evidence where appropriate; and
- reopening and validation without rerunning completed dynamics.

The numerical scalar field is the authoritative scientific artifact. Images,
heatmaps, and other renderings are downstream derivatives and must not control
the storage contract.

## 019 -- assembled map-scale validation

**Research question:** Does the accepted execution, tiling, and persistence
pipeline produce a numerically trustworthy periodic scalar field with
predictable resource cost and reliable restart behaviour?

This is the first experiment allowed to resemble a substantial real map run.
It must remain bounded and materially smaller than the eventual
`12000 x 12000` target.

The acceptance boundary requires:

- exact half-open periodic axes and agreed field orientation after assembly;
- no missing, duplicated, or silently overwritten cells;
- mechanically selected oracle spot checks across the assembled domain;
- preserved values, statuses, validity evidence, and provenance after reload;
- an interrupted-and-resumed run that is equivalent to uninterrupted
  completion;
- verified tile integrity and bounded retry/failure behaviour;
- measured total throughput, setup cost, peak memory, storage size, and a
  justified extrapolation with stated limits; and
- rendering or inspection from persisted numerical data without dynamics
  recomputation.

Its earned output is evidence that the assembled computation pipeline is ready
for a separately authorised high-resolution generation run. It is not itself
the `12000 x 12000` production run.

## Explicit non-goals and nonclaims

This sequence does not include:

- production UI or application integration;
- renderer architecture or visual-design decisions;
- a new chaos observable introduced merely for performance work;
- a custom integrator unless later evidence specifically earns that separate
  investigation;
- a premature HDF5 or Zarr commitment;
- an arbitrary tile-size commitment;
- a `12000 x 12000` run before execution, tiling, persistence, and assembled
  validation are accepted;
- an assumption that threads, processes, or batching are safe or fastest;
- a claim that the promoted evaluator is validated for arbitrary horizons,
  parameters, tangent directions, or the full periodic domain; or
- a claim that a visually plausible field is numerically valid.

The map computation boundaries should remain cross-observable where the
earned concepts are genuinely neutral. The Lyapunov finite-time rate is the
first trusted consumer, not the definition of execution, tiling, persistence,
or a scalar field.

## Exit condition

This strand exits after Experiment 019 has earned all of the following:

> A validated, resumable, throughput-characterised scalar-field generator
> whose authoritative numerical output preserves coordinates, scientific
> provenance, values, validity and completion state, and can be inspected or
> rendered later without rerunning the underlying dynamics.

Only then is a high-resolution state-space field generation run an execution
decision rather than an unresolved architecture experiment.
