# Scalar-field runner promotion plan

**Status: implemented; the reusable runner and first Lyapunov binding are now
promoted under the coherent `prototypes/state_space_maps/` boundary. The
filesystem sketch below has been updated to show that later structural
refactor; the earned contracts are unchanged.**

## Purpose

Experiments 017--019 have earned a bounded local computation pipeline. This
note identifies the smallest promotion that can turn that evidence into a
reusable scalar-field runner without moving forensic experiment code or
redesigning the accepted contracts.

The target composition is:

``` text
field definition and exact axes
    -> observable-specific scalar adapter
    -> four warmed spawn workers, indexed per-cell dispatch
    -> 8 x 8 half-open rectangular work units
    -> recycle the worker pool at tile boundaries after at most 1,024 cells
    -> single-coordinator HDF5 completion
    -> storage and scientific validation
    -> optional rendering from the closed artifact
```

The HDF5 scalar field is authoritative. Run summaries and images are
derivatives. The promotion must preserve `values[theta2_index, theta1_index]`
and the full-periodic `[-pi, pi)` axes supplied by `PeriodicAngularDomain`.

## Evidence and promotion boundary

The accepted implementations contain three kinds of code:

| Evidence | Promote or reuse | Keep forensic |
| --- | --- | --- |
| Experiment 017 | `TileShape`, half-open global `TileBounds`, deterministic planning, clipped edge tiles, local/global index mapping, exact-coverage validation, compact value/status arrays, sparse exceptional details, and the accepted `8 x 8` / 1,024-cell lifecycle policy | candidate-shape benchmark, bounded degree fixtures, injected failures, order permutations, rich-versus-compact measurements, memory probes, max-step audit, and fallback investigation |
| Experiment 018 | HDF5 `FieldDefinition`, `CompletedTile`, cell/tile states, create/write/read/inspect operations, fail-closed completion protocol, resume discovery, duplicate/conflict handling, and static/per-tile integrity checks | deterministic synthetic field, simulated interruption hook, corruption harness, subprocess probe, evidence generation, and provisional storage comparisons |
| Experiment 019 | the orchestration sequence for discover-pending, bounded pool lifecycle, per-tile evaluation/compaction, coordinator write, resume, and final validation summary | fixed `64 x 64` workload, controlled interrupted twin run, corruption copy, nine-cell evidence harness, resource/extrapolation report, fixed output names, and experiment figure styling |

Promotion means re-expressing these contracts in prototype-owned modules. The
prototype must not import numbered experiments, and the forensic experiments
should continue to reproduce their original evidence without importing their
promoted descendants.

The neutral field concepts now live at
`prototypes/state_space_maps/src/state_space_fields.py`. They remain upstream
of both generation and observable-specific consumers rather than being folded
into the generation package.

## Smallest proposed module structure

Add one sibling neutral strand and one Lyapunov adapter:

``` text
development/chaos_content/prototypes/state_space_maps/
    src/
      state_space_fields.py               # reference outcomes/domains
      generation/
        __init__.py                       # narrow supported exports
        work_units.py                     # tile bounds, planning, coverage, tasks
        hdf5.py                            # accepted Experiment 018 schema/adapter
        runner.py                          # create/resume and process lifecycle
        validation.py                      # dynamics-free completeness/integrity
      lyapunov/
        field_adapter.py                  # task -> fixed Lyapunov spec -> hybrid result
        ...
    runners/
      generate_lyapunov_periodic_field.py # concrete API/CLI composition
    tests/
```

This is not a generic simulation framework. `state_space_maps/src/generation`
knows
about two ordered axes, rectangular scalar fields, compact statuses/routes,
work units, process execution, and HDF5. It does not know about Candidate-A,
tangent dynamics, pendulum parameters, or Lyapunov result internals.

`field_adapter.py` owns the current consumer-specific facts: replacing
`theta1(0)` and `theta2(0)` in a fixed `RenormalizedTangentSpec`, zero initial
angular velocities, warming and calling
`evaluate_renormalized_tangent_hybrid`, translating its diagnostics into tile
summaries, the three route labels, and independent solve-ivp oracle spot
checks.

No renderer module is proposed in the first promotion. Experiment 019 proves
that a renderer can consume a closed authoritative snapshot without importing
dynamics. A reusable rendering API has not yet been earned.

## Reusable specifications and results

Keep the public model small:

- `TileShape(theta2_cells, theta1_cells)` and
  `TileBounds(global_shape, theta2_start, theta2_stop, theta1_start,
  theta1_stop)` retain the accepted half-open index semantics.
- `ScalarCellTask` carries a linear index, both global indices, and both exact
  coordinates. The runner creates it; an observable adapter interprets the
  coordinates.
- `ProcessExecutionSpec` records the accepted width, dispatch chunksize, spawn
  method, and maximum cells per pool. Its initial supported policy is exactly
  four workers, chunksize one, and 1,024 cells per pool; configurability must
  not imply that other values are validated.
- Experiment 018's `FieldDefinition` remains the durable field specification:
  axes, units, periodic convention, tile shape, scalar dtype, route
  vocabulary, and observable/physical/numerical/evaluator/software provenance.
- `FieldRunSummary` reports the artifact path, create/resume mode, pre-existing
  and newly completed tiles/cells, cell-state and route counts, pool/recycling
  counts, setup/evaluation/write/total times, coarse resource observations,
  and final validation result. It is not authoritative scientific storage.

The minimum process seam is a small spawn-safe evaluator binding: a
module-level worker initializer, a module-level `ScalarCellTask` evaluator,
and immutable initializer arguments. This is required by the accepted spawn
lifecycle. It should be a structural protocol or a small frozen record, not an
inheritance hierarchy, registry, or plugin system. Returned cell evaluations
must retain the existing `ScalarEvaluation` value/status/error semantics.

## Proposed runner API

The initial API should be explicit about file lifecycle:

``` python
summary = run_scalar_field(
    output_path,
    field_definition,
    evaluator_binding,
    execution=accepted_process_execution_spec(),
    mode="create",  # or "resume"
)
```

`create` must use exclusive creation and refuse an existing path. `resume`
must require an existing artifact, validate static metadata, axes, tile plan,
and checksums, and refuse any mismatch or corrupt completed tile before
starting workers. There should be no ambiguous create-or-resume default.

The runner derives the deterministic tile plan from the field shape and
nominal tile shape, discovers only non-authoritative tiles, evaluates one work
unit at a time through indexed per-cell dispatch, compacts rich outcomes, and
writes through the single coordinator-owned adapter. A programming or
specification exception propagates and leaves the tile non-authoritative. A
bounded scalar execution error remains cell data under the existing status
contract. A failed work unit is retryable because no completion marker is
written.

The first implementation should add a public check that the requested
`FieldDefinition` and derived tile plan exactly match an existing artifact.
This exposes an already required resume invariant; it does not alter the HDF5
transaction semantics.

## Validation and provenance boundaries

Validation has two layers:

1. Neutral validation checks static integrity, checksums, exact tile coverage,
   axes, orientation, legal status/route codes, complete authoritative state,
   finite completed-valid values, and `NaN` execution-error values. It never
   imports a dynamics evaluator.
2. Observable-specific validation independently recomputes a mechanically
   declared set of coordinates through an oracle and applies that observable's
   established numerical gates. For the first Lyapunov runner, retain the
   Cartesian product of indices `{0, N/2, N-1}` on each axis and the existing
   Experiment 015 tolerances.

Dataset-level provenance remains immutable in `FieldDefinition`. Ordinary
cells use compact `uint8` status and execution-route arrays. Tile-level JSON
retains attempt, timing, aggregate diagnostics, and sparse invalid/error
details. A resumed run must not rewrite the creation provenance. Operational
session information may be returned and written to a non-authoritative JSON
summary; adding durable run-history semantics to the HDF5 schema is deferred.

Rendering is downstream of successful reopen and validation:

``` text
closed HDF5 artifact -> authoritative snapshot -> observable-specific renderer
```

A renderer receives only the artifact path and output path. It must not receive
an evaluator or cause missing dynamics to run. It masks non-valid cells using
stored status and may label the field using stored metadata. Rendering failure
does not alter field completion.

## First tangible runner milestone

The first implementation milestone is not the `512 x 512` run. It is a
promoted runner that passes small, cheap regression fixtures for fresh create,
interruption, exact resume, field completeness, corruption refusal, spawn
worker recycling, Lyapunov route preservation, oracle spots, and rendering
from persisted data. Existing Experiments 017--019 remain the numerical
evidence; the promotion tests should use synthetic tiles and at most tiny
scientific fields.

Once that milestone passes, the intended first separately authorised
operational use is:

- full periodic `theta1, theta2 in [-pi, pi)`;
- `512 x 512` samples and field shape `(512, 512)`;
- `T=5 s`, `0.25 s` renormalisation, initial tangent `(1, 0, 0, 0)`, zero
  angular velocities, Candidate-A geometry, and the unchanged hybrid evaluator;
- `8 x 8` work units, four spawn workers, chunksize one, and recycling after
  at most 1,024 cells; and
- one authoritative HDF5 artifact under the ignored chaos-content outputs
  tree, plus a non-authoritative JSON completion summary and optional image.

A concrete CLI should be Lyapunov-specific rather than introduce an observable
registry:

``` bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field \
  --samples-per-axis 512 \
  --output development/chaos_content/prototypes/state_space_maps/outputs/lyapunov/lyapunov_finite_time_512.h5 \
  --create
```

After interruption, the identical command uses `--resume` instead of
`--create`. Resume must report the verified completed/pending/corrupt tile
counts before starting and must not reevaluate completed cells.

Completion should report cell-state and route counts, finite valid-value range,
tile and pool counts, recycling events, total/setup/evaluation/persistence
times, cells per second, coarse coordinator/worker memory, HDF5 and raw payload
sizes, neutral validation issues, and nine Lyapunov oracle results. A
`--render PATH` option may run only after validation, or rendering may remain a
separate command.

This configuration contains 262,144 cells, 4,096 exact `8 x 8` tiles, and 256
pool lifetimes under the literal accepted lifecycle. Its raw
value/status/route payload is 2,621,440 bytes (2.5 MiB). Applying Experiment
019's measured 205.54 cells/s linearly gives about 1,275 seconds, or 21.3
minutes. That is a planning estimate, not an authorization or runtime
guarantee; startup, HDF5 metadata, fallback frequency, memory, and throughput
at this scale remain unmeasured.

## Dependency direction

``` text
state_space_maps/src/state_space_fields.py
        ^
        |
state_space_maps/src/generation/work_units.py
        ^                 ^
        |                 |
state_space_maps/src/generation/runner.py -> state_space_maps/src/generation/hdf5.py
        ^
        |
state_space_maps/src/lyapunov/field_adapter.py -> state_space_maps/src/lyapunov/hybrid.py
        ^
        |
state_space_maps/runners/generate_lyapunov_periodic_field.py
```

Neutral modules must not import `src/lyapunov` or numbered experiments.
The Lyapunov adapter may import both neutral generation contracts and the
existing Lyapunov evaluator. Production application code must not import this
development prototype.

## Experiment archive strand index

Do not move or renumber experiment directories. A future
`development/chaos_content/experiments/INDEX.md` can preserve the chronological
ledger while adding a second, non-exclusive strand view:

- Poincare prior work: Experiment 001;
- sensitivity, finite separation, and local-tangent foundations: Experiments
  002--006;
- tangent spectrum and convergence/claim-boundary investigations: Experiments
  007--014;
- scalar evaluator and integration acceleration: Experiment 015 plus the
  endpoint-snap/fallback follow-ups retained inside Experiment 017; and
- state-space field computation: Experiments 016--019.

Each index entry should link to the unchanged numbered directory and record
status, strongest earned claim, superseding evidence where applicable, and
prototype contract carried forward. This is navigation, not a filesystem
taxonomy; an experiment may be cross-listed where its evidence serves more
than one strand.

## Explicit deferrals and unresolved evidence

Do not refactor the existing reference line/rectangle samplers, Lyapunov
science, hybrid routing, Experiment 018 schema, accepted tile size, or worker
lifetime during runner promotion. Do not add a generic observable registry,
storage-backend interface, renderer framework, distributed execution, JAX,
custom integration, UI wiring, or production package placement.

The first promotion does not need new scientific evidence, but it must make
three operational points explicit:

- resume across changed software/evaluator provenance should fail closed until
  schema compatibility or migration is separately earned;
- the `64 x 64` fallback fraction is not a forecast for `512 x 512` or
  `12000 x 12000`; and
- the literal 1,024-cell recycling rule produces many pool startups, while the
  literal `8 x 8` rule produces substantial tile metadata. Neither policy may
  be changed merely inside the promotion. Measurements from the authorised
  `512 x 512` run may justify a later operational-scale experiment.

## Next task

Promote the neutral work-unit and HDF5 modules first, with focused synthetic
tests. Then implement the runner and Lyapunov adapter by re-expressing the
Experiment 019 composition against those promoted APIs. Validate with tiny
create/resume and oracle fixtures only; do not execute the `512 x 512` field
until that run is separately authorised.
