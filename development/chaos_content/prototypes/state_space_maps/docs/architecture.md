# State-space-map architecture

The neutral modules under `../src/` promote the cross-observable computation boundaries accepted by
Experiments 017--019. It owns deterministic rectangular work units, the local
HDF5 scientific artifact, bounded spawn-process execution, resume, and
dynamics-free validation. It does not know how a scalar observable is
calculated.

The supported array convention is always:

``` text
values[theta2_index, theta1_index]
```

`generation/work_units.py` plans `8 x 8` nominal half-open index rectangles with clipped
edges. `generation/hdf5.py` owns the authoritative float64 values, uint8 status/route
arrays, provenance, tile completion markers, checksums, and fail-closed
reader. `generation/runner.py` evaluates pending tiles through four spawn-isolated
workers, dispatches indexed cells with chunksize one, recycles a pool at tile
boundaries before it would exceed 1,024 cells, and lets only the coordinator
write HDF5. `generation/validation.py` reopens and validates an artifact without dynamics.

The public orchestration API is:

``` python
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

An `EvaluatorBinding` contains only spawn-importable module-level worker
initialization/evaluation functions, immutable initialization arguments,
declared route labels, and an optional tile-diagnostic summarizer. This is a
small process seam, not an observable registry or plugin framework.

The accepted default execution values are host- and workload-bounded evidence,
not a claim that other policies have been validated. Rendering is deliberately
downstream: it consumes a closed, validated HDF5 artifact and never causes
dynamics to run.
