# State-space-map software architecture

This document owns the software boundaries of the prototype. See the
[prototype README](../README.md) for operation and the
[finite-time-stretching reference](science/finite_time_stretching.md) and
[first-flip pilot](science/first_flip_time.md) for the current observables'
mathematics and claim boundaries.

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
`../src/generation/` owns field work; it never imports the Lyapunov or
first-flip consumers or knows how an observable is calculated. Each scientific
adapter depends on both
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
chunksize one, recycles a pool at tile boundaries before it would exceed 2,048
cells, and lets only the coordinator write HDF5.
`generation/validation.py` reopens and validates an artifact without dynamics.

The 2,048-cell pool-wide lifetime is the promoted, evidence-backed operating
point. A bounded `64 x 64` runner validation measured about 20% lower adjusted
runner wall time than the former 1,024-cell policy, at an explicit cost of
about 170 MiB additional worker RSS across four processes. Recycling remains a
resource boundary because RSS continued to grow with worker lifetime. The
measurement does not establish 2,048 as a universal maximum-safe lifetime, and
it supplies no evidence for 4,096, larger limits, or unlimited reuse.

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

Execution policy is recorded per completed tile rather than in the static
field definition. A same-definition resume may therefore preserve completed
tiles carrying the former 1,024 limit and write pending tiles with the promoted
2,048 limit; that mixed provenance is explicit. Software provenance remains a
static compatibility input, so an artifact from a different recorded Git
revision remains fail-closed. A completed schema-valid old-policy artifact is
still readable and renderable because those operations do not resume work.

## Scientific consumer seam

An `EvaluatorBinding` contains only spawn-importable module-level worker
initialization/evaluation functions, immutable initialization arguments,
declared route labels, and an optional tile-diagnostic summarizer. This is a
small process seam, not an observable registry or plugin framework.

The neutral scalar-field machinery is reusable across observables. End-to-end
observable extensibility has now been demonstrated for the finite-time
one-vector stretching and capped first-flip-time consumers. A future consumer
would still need
its own scientific definition, evaluator evidence, route and validity
semantics, adapter, and focused tests; the neutral seam does not supply those
contracts automatically.

First-flip censoring does not require a generic schema feature. Its adapter
stores the capped dimensionless time as a completed-valid scalar, with exact
equality to the provenance-declared horizon meaning right-censored. Numerical
invalidity and execution failure continue to use the neutral status vocabulary.
This is an observable-specific scalar contract rather than a reinterpretation
of `completed_valid` for every consumer.

The accepted execution values are host- and workload-bounded evidence, not a
claim that other policies have been validated. The renderer consumes only a
closed, validated HDF5 artifact and never causes dynamics to run.

## Guarded S1 Lyapunov route

The Lyapunov consumer has an operational selector in
`src/lyapunov/operational.py`. It does not replace or modify the established
hybrid. For an eligible specification and validated build it attempts
`s1_native_dop853_v1`; a clear completed-valid result is accepted with that
distinct route identity. Ineligible specifications and unsupported builds call
the existing hybrid directly.

The initial eligibility allowlist is deliberately narrower than the complete
S1 validation set: standard unit parameters, gravity `9.81`, zero velocities,
the unmodified `(1, 0, 0, 0)` tangent, Candidate-A characteristic length `1`,
DOP853 at `rtol=1e-9` and `atol=1e-11` with the resolved default max step,
`0.25 s` renormalisation, `0.01 s` sampling, the standard energy/reset limits,
finite angles already inside `[-pi, pi)`, and duration in
`{1, 2, 5, 10, 20}` seconds. Eligibility does not alter, wrap, reflect, or
otherwise reuse an input.

The native source lives beside the operational package under
`src/lyapunov/s1_native/`. `dop.c` and `dop.h` are unchanged SciPy 1.18.0 DOP
sources and retain `LICENSE_DOP`; `loop.c` is the validated single-cell driver.
Source digests, software versions, compiler identity, target, and contraction
flags are checked against the validated macOS 15.7.9 ARM64 / Apple Clang 17.0.0
build before S1 is enabled. Compilation and Numba callbacks are lazy and their
products live in a process-local temporary directory.

S1 never decides fallback eligibility. Every S1 execution failure is passed to
the existing hybrid without interpreting the S1 message. The hybrid reruns its
trusted compiled-DOP853 path, performs its own endpoint-cap verification, and
alone selects the existing compiled-RHS `solve_ivp` fallback. Completed-invalid
S1 outcomes and diagnostics within the conservative energy/reset threshold
margin are likewise replayed through the hybrid. Programming and specification
errors still propagate.

Route code `4` denotes an accepted S1 result; the former codes `1` through `3`
retain their meanings. On recovery, the persisted route remains the route that
actually supplied the retained result. The checksummed tile record separately
stores the attempted S1 implementation and recovery reason, and tile summaries
count both. Because route vocabulary and evaluator provenance are static field
identity, pre-promotion artifacts remain readable but fail closed for resume
under the promoted definition; promoted artifacts resume normally.
