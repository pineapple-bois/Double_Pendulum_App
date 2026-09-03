# Experiment 019: assembled map-scale validation

**Status: ACCEPTED for the declared `64 x 64` full-periodic workload.**

## Question

Does the accepted execution, tiling, and persistence pipeline produce a
numerically trustworthy periodic scalar field with predictable resource cost
and reliable restart behaviour?

## Definition

Experiment 019 composes, without redesigning, the boundaries accepted by
Experiments 016--018:

``` text
canonical half-open periodic axes
    -> promoted hybrid finite-time evaluator
    -> four spawn-isolated workers, indexed cell dispatch
    -> 8 x 8 half-open rectangular work units
    -> recycle workers at tile boundaries after at most 1,024 cells
    -> one coordinator-owned HDF5 persistence adapter
    -> independently reloadable authoritative scalar field
```

The scientific policy remains `T = 5 s`, renormalisation every `0.25 s`,
initial tangent `(1, 0, 0, 0)`, zero initial angular velocities, Candidate-A
geometry, and the established solver and numerical-validity policy. The stored
orientation remains `values[theta2_index, theta1_index]`, with theta1
horizontal and theta2 vertical.

### Predeclared resolution

The substantial workload is `64 x 64`, or `4,096` cells. This was selected
before inspecting field values because:

- it is the next power-of-two full-periodic refinement beyond the roadmap's
  illustrative `32 x 32` resolution;
- it gives eight accepted `8 x 8` work units along each axis and `64` tiles in
  total;
- four groups of sixteen tiles exercise the earned 1,024-cell worker-lifetime
  bound exactly, forcing three recycling events in an uninterrupted run;
- it is 6.55 times the largest `25 x 25` workload used to earn the execution
  and tile boundaries; and
- Experiment 017's measured bounded throughput predicts a run of seconds to
  low tens of seconds, keeping an uninterrupted plus resumed comparison
  experimental rather than production scale.

The resolution is not selected for visual structure and is not evidence that
`64 x 64` is scientifically sufficient for a final map.

### Predeclared oracle selection

Nine oracle cells are the Cartesian product of axis indices
`{0, samples / 2, samples - 1}`. For 64 samples these are indices
`{0, 32, 63}` on each axis. This mechanically covers the lower periodic edge,
the domain midpoint, and the final half-open sample near `+pi`, independent of
the computed values or routes.

The compiled-RHS plus `solve_ivp` DOP853 integration-boundary oracle is
recomputed independently at those coordinates. Scalar rates use the existing
`1e-8 s^-1` absolute gate, energy diagnostics use the existing `1e-8` absolute
gate, and status/issues must agree exactly. Where the fast compiled-DOP853
route completes, the full existing Experiment 015 result comparison is also
retained. No tolerance is selected after observing the field.

## Minimal experiment

The experiment will produce:

1. one uninterrupted `64 x 64` HDF5 field;
2. an equivalent field interrupted after 20 authoritative tiles, with the
   next tile stopped after payload flush but before completion;
3. a resumed completion that skips those 20 completed tiles and retries the
   one non-authoritative tile;
4. an independently reopened comparison of both authoritative fields;
5. nine independent oracle checks;
6. a deliberately corrupted copy for fail-closed integrity evidence; and
7. one minimal heatmap rendered from the closed HDF5 file without dynamics.

The interruption point is mechanical: 20 complete tiles include one full
1,024-cell pool lifetime and four tiles from the next pool. It is large enough
to make skipping completed dynamics meaningful and does not depend on field
content.

## Numerical validity

The uninterrupted artifact contains all `4,096` expected cells and all `64`
expected tiles. Coverage has no gaps, overlaps, duplicated cell identities, or
coordinate mismatches. Both stored axes exactly equal

\[
\theta_k=-\pi+\frac{2\pi k}{64},\qquad k=0,\ldots,63.
\]

Thus `-pi` is present, `+pi` is absent, theta1 remains the horizontal/column
axis, theta2 remains the vertical/row axis, and the HDF5 field shape is exactly
`(64, 64)` in `(theta2, theta1)` order.

Every cell completed-valid. There were no completed-invalid cells, execution
errors, or authoritative not-yet-computed cells, so the recorded non-valid
location list is empty. The finite-time rates range from
`-0.058411161449944536 s^-1` to `5.768436622055366 s^-1`. This range describes
this fixed-horizon observable on this discrete field; it is not a binary chaos
classification or an asymptotic-exponent claim.

Execution routes were:

| route | cells | fraction |
|---|---:|---:|
| compiled-DOP853 fast path | `3,886` | `94.873%` |
| compiled-RHS `solve_ivp` fallback | `210` | `5.127%` |
| retained execution error | `0` | `0%` |

The fallback fraction is evidence for exactly these 4,096 sampled coordinates.
It must not be treated as universal, continuous-domain, or
resolution-independent.

All nine predeclared oracle cells used the fast path and passed the complete
existing compiled-DOP853 versus compiled-RHS/`solve_ivp` comparison. Worst
observed errors were:

| comparison | worst error | gate |
|---|---:|---:|
| finite-time rate | `1.502e-9 s^-1` | `1e-8 s^-1` |
| per-cycle log stretch | `9.327e-9` | `5e-8` |
| final reference Candidate-A distance | `2.356e-9` | `1e-7` |
| final tangent Candidate-A distance | `3.500e-9` | `1e-7` |
| energy diagnostic | `5.464e-11` | `1e-8` |

All oracle validity classifications and issue lists agreed exactly. Persisted
cell coordinates, scalar values, route provenance, and retained spot
diagnostics also agreed with independently recomputed hybrid evaluations.

## Static inspection

`assembled_map_scale_validation.py` is an experiment-local composition harness.
It reuses Experiment 017's domain/work-unit planning and Experiment 018's HDF5
adapter. It supplies only the exact-radian periodic cell task, hybrid worker
lifecycle, compact-result conversion, resource measurements, oracle checks,
and assembled evidence needed by this experiment. Neither the evaluator nor
HDF5 adapter knows about the other.

The existing Experiment 016 task record is specific to its bounded degree
rectangle and its worker initializer targets the pre-hybrid evaluator. Rather
than altering that forensic experiment, Experiment 019 retains its accepted
four-process, indexed `chunksize=1` execution policy in a thin periodic/hybrid
adapter. The accepted `8 x 8` work-unit and 1,024-cell lifecycle semantics are
unchanged.

The closed HDF5 file was reopened by the dynamics-independent Experiment 018
inspector. It recovered `64` checksum-valid completed tiles, the exact axes,
all scientific/numerical/evaluator metadata, and the same `4,096` cell-state
records without evaluating dynamics. A separate dynamics-free process rendered
`persisted_field.png` from the authoritative arrays. The image is a derivative
inspection artifact and played no role in numerical acceptance.

## Acceptance

The experiment accepts only if the completed and resumed artifacts preserve
the exact periodic axes, orientation, coverage, cell states, route provenance,
scientific metadata, and tile integrity; all predeclared oracle checks pass;
the resumed field equals the uninterrupted field; accepted failure semantics
remain fail-closed; resource costs are measured; and the closed artifact can be
inspected and rendered without rerunning dynamics.

A plausible heatmap is not acceptance evidence.

**Verdict: ACCEPT.** Every declared gate passed. The computation-plan exit
condition is earned for the bounded, measured local pipeline: it is a
validated, resumable, throughput-characterised scalar-field generator whose
authoritative numerical output preserves coordinates, scientific provenance,
values, validity, execution route, and completion state and can be inspected
or rendered later without rerunning dynamics.

This does not authorize or establish practical readiness for a
`12000 x 12000` run. The extrapolation below exposes substantial operational
cost that must be considered before such a run is separately authorized.

## Findings

### Persistence, interruption, and failure composition

The uninterrupted run completed all 64 tiles with four worker pools and three
recycling events. The equivalent interrupted run completed tiles `0--19`, then
wrote tile `20` only through its payload flush. Reopening found exactly 20
authoritative completed tiles and tile `20` in `writing` state. The
authoritative reader masked all 64 cells in that partial tile as not computed.

Resume skipped the `1,280` cells in the 20 completed tiles, retried tile `20`,
and evaluated only the remaining 44 work units. Its final values, statuses,
route arrays, axes, scientific metadata, tile numerical diagnostics, tile
provenance, and sparse exceptional records exactly matched the uninterrupted
artifact. Both files passed every static and per-tile checksum.

The resumed sequence evaluated `4,160` cells in total because the 64-cell
non-authoritative interrupted attempt was correctly repeated. It took
`22.458 s`, versus `19.928 s` uninterrupted, an observed interruption/resume
overhead of `2.530 s`. It used five pools across the two process sessions;
every worker stopped.

A copied dataset with one deliberately changed completed scalar was rejected,
and tile `0` was identified as corrupt. A conflicting completion attempt was
also refused. Execution-error encoding was verified to require status
`execution_error` and a `NaN` scalar; no actual execution-error cell occurred
in this field.

### Measured resources

The uninterrupted run measured:

| quantity | observed value |
|---|---:|
| end-to-end wall time | `19.928 s` |
| effective throughput | `205.54 cells/s` |
| effective cost | `4.865 ms/cell` |
| four-pool setup/warm-up | `6.265 s` |
| tile evaluation wall sum | `11.207 s` |
| HDF5 persistence | `0.170 s` |
| pool shutdown | `1.918 s` |
| worker pools / recycling events | `4 / 3` |
| coordinator peak RSS | `195,805,184 bytes` |
| maximum observed worker RSS | `283,475,968 bytes` |
| maximum observed four-worker current RSS | `1,115,045,888 bytes` |

Persistence consumed about `0.85%` of end-to-end wall time at this scale. New
worker pools began around `232--234 MB` per worker; final observations varied
by workload and reached the recorded maximum above. These measurements support
the bounded recycling behaviour but do not diagnose the source of worker RSS
growth or predict indefinite process reuse.

The authoritative arrays occupy `40,960` raw bytes: `32,768` values plus
`4,096` status and `4,096` route bytes. The HDF5 artifact is `339,192` bytes
(`331.2 KiB`) including axes, 64 tile records, JSON provenance/diagnostics,
checksums, HDF5 metadata, and compression. At this small resolution, fixed
metadata dominates; the ratio is not a production compression forecast.

### Qualified `12000 x 12000` extrapolation

A `12000 x 12000` field contains `144,000,000` cells. If the observed
`205.54 cells/s` end-to-end throughput scaled linearly, compute time would be
about `700,606 s`, or `8.11 days`. This is an arithmetic projection, not a
runtime guarantee.

Keeping the current bounded policies literally would imply:

- `2,250,000` separate `8 x 8` work units;
- `140,625` worker-pool lifetimes at no more than 1,024 cells each;
- `1,440,000,000` raw bytes (`1.34 GiB`) for value/status/route arrays alone;
- about `5,971 s` (`1.66 h`) of tile persistence if the measured per-tile
  flush cost scaled linearly; and
- about `11.11 GiB` if this experiment's whole-file bytes-per-cell ratio scaled
  literally.

The raw `1.34 GiB` array size is mechanically determined. The `11.11 GiB`
file projection is deliberately weak because fixed metadata dominates the
64x64 file, compression depends on the future field, and millions of HDF5 tile
records have not been validated. Startup, process recycling, filesystem
flushes, metadata structures, caching, contention, and failure frequency also
cannot be assumed linear. In particular, the observed `5.127%` fallback rate
must not be used as a production fallback forecast.

The extrapolation makes the remaining decision visible: correctness and
restart semantics are assembled, but literally carrying the bounded `8 x 8`
and 1,024-cell lifecycle policies to 144 million cells would create millions
of tile commits and over one hundred thousand process pools. Production-scale
authorization should first decide whether that measured cost is acceptable or
whether new evidence must earn a coarser operational scale without changing
the scientific/storage contracts.

## Next step

The map-computation roadmap's bounded exit condition is complete. The next
step is a separate high-resolution generation decision informed by the
measured eight-day linear estimate, storage bounds, and extreme tile/pool
counts. A moderate scaling confirmation or a narrowly scoped operational-scale
experiment may be warranted before authorizing `12000 x 12000`; neither should
alter the accepted observable, coordinate, result-state, integrity, or
single-writer authoritative-field contracts without new contradictory
evidence.
