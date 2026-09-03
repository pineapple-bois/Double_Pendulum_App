# Experiment 018: HDF5 persistence boundary

**Status: ACCEPTED for the bounded local-scientific persistence contract.**

## Question

How should completed numerical tiles become an authoritative, resumable,
verifiable scalar-field dataset?

Experiment 016 earned four warmed spawn workers with indexed per-cell dispatch.
Experiment 017 earned deterministic rectangular work units in half-open global
index space, with an accepted `8 x 8` nominal scale for the bounded regime.
This experiment asks only how completed work units cross a durable storage
boundary. It does not embed storage calls in evaluation and does not assemble a
scientific map run.

## Definition

### Storage choice

HDF5 through `h5py` is accepted for the current local-scientific boundary. It
fits the evidence now available:

- one local file can contain typed multidimensional arrays, explicit axes,
  metadata, tile records, and integrity evidence;
- hyperslab writes map directly to the earned half-open rectangular work units;
- chunked datasets support bounded tile writes and independent later reads;
- the file can be reopened and inspected without importing a dynamics
  evaluator; and
- HDF5 is mature for local scientific interchange and inspection.

Zarr remains a viable alternative if execution becomes distributed,
object-store-oriented, or naturally based on independently managed chunk
objects. Those requirements are not present in the accepted local execution
policy. A directory of chunk objects and its store/metadata coordination would
add a boundary that this experiment does not need. This result therefore
selects HDF5 for the next assembled local experiment; it does not establish a
universal storage backend.

### Durable schema

The experiment uses schema name `double_pendulum_scalar_field`, version `1`.
The stored layout is:

``` text
/
  attributes
    schema_name, schema_version
    definition_json
    static_integrity_sha256
  axes/
    theta1                  float64[theta1]
    theta2                  float64[theta2]
  field/
    values                  float64[theta2, theta1]
    status                  uint8[theta2, theta1]
    execution_route         uint8[theta2, theta1]
  tiles/
    bounds                  int64[tile, 4]
    identity                ASCII SHA-256[tile]
    state                   uint8[tile]
    checksum                ASCII SHA-256[tile]
    attempt                 uint32[tile]
    evaluation_seconds      float64[tile]
    diagnostics_json        UTF-8 JSON[tile]
    provenance_json         UTF-8 JSON[tile]
    exceptional_cells_json UTF-8 JSON[tile]
```

All rectangular arrays retain the repository convention
`values[theta2_index, theta1_index]`. Tile bounds are stored as
`(theta2_start, theta2_stop, theta1_start, theta1_stop)` with half-open stops.
Axes are authoritative coordinate lookups; a tile never regenerates its own
coordinates. The field definition records resolution in `(theta1, theta2)`
order and array shape in `(theta2, theta1)` order so the distinction is
machine-readable rather than implicit.

The status vocabulary is:

| code | meaning |
|---:|---|
| `0` | not yet computed |
| `1` | completed and numerically valid |
| `2` | completed but numerically invalid |
| `3` | bounded execution error; no scalar value |

Execution route is an independent `uint8` field. For the first Lyapunov
consumer it distinguishes `compiled_dop853`,
`compiled_rhs_solve_ivp_fallback`, and
`compiled_dop853_execution_error`. The scalar/status contract is therefore not
coupled to evaluator route, and route provenance does not require a rich Python
object per cell. Details for exceptional invalid/error cells remain sparse
tile-level JSON.

Dataset-level provenance contains the domain convention, units, resolution,
orientation, observable identity, physical and numerical parameters, evaluator
policy, software versions, and vocabularies. Tile-level provenance contains
bounds, attempt, timing, aggregate diagnostics, evaluator context, and sparse
exception details. No per-cell metadata is stored for ordinary cells.

### Completion and integrity protocol

A completed tile crosses the adapter in four ordered, flushed stages:

1. set its tile state to `writing` and clear any prior checksum;
2. write values, statuses, routes, attempt, diagnostics, and provenance;
3. recompute and store the tile SHA-256 digest from the bytes just written;
4. set the tile state to `complete` as the final authoritative marker.

Only a `complete` tile whose recomputed checksum matches is authoritative.
Readers mask `not_started`, `writing`, and corrupt tile regions back to
`NaN`/status `0`/route `0`, even if partial payload bytes are present. A
`writing` tile is retryable at the same immutable bounds. An identical write to
an already completed tile is idempotent; different content for that tile is a
conflict and is refused. A checksum-failing completed tile is reported
separately as corrupt rather than silently considered pending.

One static SHA-256 digest covers the canonical field definition, axes, and tile
plan. Each completed-tile SHA-256 covers tile identity and bounds, the three
cell arrays, attempt/timing, diagnostics, provenance, and exceptional-cell
details. HDF5 Fletcher32 is also enabled at the chunk layer. The application
digests provide semantic tile/static verification; Fletcher32 provides an
additional storage-layer corruption check rather than replacing them.

## Minimal experiment

The experiment reuses Experiment 017's coordinate-only full-periodic
`33 x 25` domain and accepted `8 x 8` nominal work units. This yields `20`
tiles, including rectangular edge tiles, and `825` cells. It uses deterministic
index-coded scalar payloads to test persistence and orientation without
running or claiming Lyapunov dynamics. The definition nevertheless records the
current fixed Lyapunov scientific/evaluator policy to prove that the first
consumer's provenance fits the neutral schema.

The experiment performs, in order:

- fresh file creation and all-uncomputed inspection;
- completed-tile write and exact reopen/readback;
- idempotent duplicate completion and refusal of conflicting completion;
- an interruption after payload flush but before checksum/completion;
- restart discovery, authoritative masking, and deterministic retry;
- completion of only the discovered pending tiles;
- exact full-field/axis/status/route readback and coordinate checks;
- inspection in a separate process using only the persistence module; and
- deliberate mutation of one completed scalar followed by checksum validation.

The deterministic fixture includes `823` completed-valid cells, one
completed-invalid cell, and one execution-error cell. Its route field contains
`775` fast, `49` fallback, and one fast-error route entries. These counts test
encoding only; they are not measurements of the full periodic Lyapunov field.

Ignored machine-readable evidence and HDF5 artifacts are written under:

``` text
development/chaos_content/experiments/outputs/018/
  reference_scalar_field.h5
  corrupted_scalar_field.h5
  summary.json
```

## Numerical/data validity

The fresh artifact reopened with all `825` cells in the not-yet-computed state.
The first tile and final field reproduced values, statuses, routes, and axes
exactly. Checks at global indices `(theta2, theta1) = (0, 0)`, `(7, 8)`, and
`(24, 32)` confirmed that stored values and coordinates follow the declared
orientation across tile interiors and edges. The periodic axes remained in
`[-pi, pi)` with no duplicated `+pi` endpoint.

The interrupted tile reopened in state `writing`; its already flushed payload
was invisible through the authoritative reader and its entire region appeared
not yet computed. Retry with the same bounds completed successfully. Resume
then identified tiles `0` and `1` as complete, so completion of the dataset
scheduled only tiles `2` through `19`. Discovery and skipping required no
dynamics evaluator.

An identical duplicate returned `already_complete_identical`. A changed value
for the same completed tile raised a conflict. After deliberate mutation of
cell `[0, 0]` in a copied file, validation rejected the artifact, identified
tile `0` as corrupt, and excluded it from the authoritative completed set.

## Static inspection

`hdf5_field_store.py` owns the storage schema, transactions, resume discovery,
validation, and authoritative reader. It imports only standard-library,
NumPy, and `h5py` code. `persistence_boundary.py` is the experiment harness and
the only layer that adapts the accepted Experiment 017 work units and current
Lyapunov provenance into the neutral store.

Independent subprocess inspection accepted the uncorrupted artifact, recovered
all `20` completed tiles and all field metadata, and required no prototype or
dynamics evaluator. The uncorrupted file was approximately `107 KiB`; storage
size at this fixture scale is not a production extrapolation.

The following choices are earned for the next local assembled experiment:

- HDF5 as the local authoritative scalar-field container;
- explicit axes plus half-open global integer tile bounds;
- dense float64 values and compact uint8 status/route arrays;
- a last-written tile completion marker;
- static and per-completed-tile SHA-256 verification;
- deterministic resume from verified completion state; and
- strict duplicate/conflict handling.

The exact compression level, chunk dimensions beyond alignment with the
accepted reference tile scale, diagnostic JSON evolution, checksum algorithm,
and long-term schema migration policy remain provisional. Parallel HDF5
writers, SWMR operation, filesystem crash guarantees beyond HDF5 flush/close,
and storage performance at map scale were not investigated. The accepted
execution policy should initially hand completed tiles to one coordinator-side
writer unless a later experiment earns another lifecycle.

## Acceptance

**Verdict: ACCEPT.** A completed rectangular work unit can be written to an
authoritative HDF5 scalar-field artifact, reopened, independently verified, and
used to discover restart state without rerunning completed dynamics. The
artifact preserves axes, orientation, scientific/evaluator provenance, compact
cell-state distinctions, route provenance, tile identity, and integrity
evidence. Partial and corrupt work are fail-closed rather than promoted to
completed data.

The strongest earned claim is limited to small deterministic local files and a
single coordinator-side writer. This experiment does not claim that the
Lyapunov observable has been evaluated across the full periodic domain, that
HDF5 is optimal for distributed execution, that current chunks/compression are
production-optimal, or that the pipeline is ready for `12000 x 12000` output.
It does not earn rendering, UI integration, a durable scheduler, or a
high-resolution production run.

## Findings

The persistent boundary is materially simpler than the execution boundary: a
completed tile is converted to three compact arrays plus tile-level metadata,
then passed to a single storage adapter. Neither the observable nor the worker
pool knows about HDF5. The completion marker and semantic checksums make restart
state a property of the stored artifact rather than a guess based on non-fill
values.

HDF5 won this bounded comparison because the accepted use case is local,
array-shaped, typed, and single-file. Zarr's strongest advantages remain tied
to a future distributed/object-store requirement that has not been earned.
The main unresolved operational constraint for Experiment 019 is to preserve a
single-writer ownership model while assembling process-produced tiles.

## Next experiment

Experiment 019 should validate the assembled accepted execution, tile, and
persistence boundaries on a bounded periodic scalar-field run. It should test
uninterrupted versus interrupted/resumed equivalence, oracle spot checks,
throughput, memory, storage size, and inspection from persisted numerical data.
It should not revisit schema technology unless assembled evidence contradicts
this experiment's single-writer HDF5 boundary.
