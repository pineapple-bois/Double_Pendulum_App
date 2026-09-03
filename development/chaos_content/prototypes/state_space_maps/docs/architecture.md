# State-space-map software architecture

This document owns the software boundaries of the prototype. See the
[prototype README](../README.md) for operation and the
[finite-time-stretching reference](science/finite_time_stretching.md) for the
current observable's mathematics and claim boundary.

## Dependency direction

The dependency direction is deliberately one way:

```text
neutral field/domain concepts
        -> neutral generation, execution, persistence, validation
        <- scientific consumer adapter
        -> concrete generation runner

validated HDF5 artifact
        -> renderer
```

`../src/state_space_fields.py` owns coordinate-neutral scalar outcomes,
explicit-axis reference sampling, and the half-open periodic angular domain.
`../src/generation/` owns field work; it never imports the Lyapunov consumer or
knows how an observable is calculated. The scientific adapter depends on both
the neutral contracts and its own evaluator, then the concrete runner composes
them. Rendering is downstream of persistence and does not depend on dynamics.

## Neutral generation boundary

The supported stored-array convention is always:

```text
values[theta2_index, theta1_index]
```

`generation/work_units.py` plans deterministic `8 x 8` nominal half-open index
rectangles with clipped edges. `generation/hdf5.py` owns authoritative float64
values, uint8 status/route arrays, provenance, tile completion markers,
checksums, and the fail-closed reader. `generation/runner.py` evaluates pending
tiles through four spawn-isolated workers, dispatches indexed cells with
chunksize one, recycles a pool at tile boundaries before it would exceed 1,024
cells, and lets only the coordinator write HDF5.
`generation/validation.py` reopens and validates an artifact without dynamics.

The neutral orchestration API is:

```python
summary = run_scalar_field(
    output_path,
    field_definition,
    evaluator_binding,
    mode="create",  # or "resume"
)
```

`create` refuses an existing path. `resume` requires an existing artifact and
requires the requested definition, axes, provenance, and tile plan to match
exactly before workers start. Verified complete tiles are skipped; writing or
not-started tiles are retried. Corrupt complete tiles fail closed.

## Scientific consumer seam

An `EvaluatorBinding` contains only spawn-importable module-level worker
initialization/evaluation functions, immutable initialization arguments,
declared route labels, and an optional tile-diagnostic summarizer. This is a
small process seam, not an observable registry or plugin framework.

The neutral scalar-field machinery is reusable across observables. End-to-end
observable extensibility, however, has only been demonstrated for the current
finite-time one-vector stretching consumer. A future consumer would still need
its own scientific definition, evaluator evidence, route and validity
semantics, adapter, and focused tests; the neutral seam does not supply those
contracts automatically.

The accepted execution values are host- and workload-bounded evidence, not a
claim that other policies have been validated. The renderer consumes only a
closed, validated HDF5 artifact and never causes dynamics to run.
