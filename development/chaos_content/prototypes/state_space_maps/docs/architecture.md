# State-space-map software architecture

This document owns the software boundaries of the prototype. See the
[prototype README](../README.md) for operation and the
[finite-time-stretching reference](science/finite_time_stretching.md) and
[first-flip reference](science/first_flip_time.md) for the current observables'
mathematics and claim boundaries. The pedagogy documents for
[first flip](pedagogy/first_flip.md) and
[finite-time sensitivity](pedagogy/sensitivity_to_lyapunov.md) own the teaching
sequence rather than software policy.

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

## Observable-development contract

Future observable work follows this hierarchy:

```text
scientific primitive
    ↓
authoritative data product
    ↓
derived observable
    ↓
pedagogical representation
```

The scientific primitive states exactly what is measured and which claims it
supports. A trusted implementation establishes an independent oracle for that
meaning. The authoritative data product persists the primitive, its finite
observation limits, statuses, axes, numerical definition, provenance, and
integrity information. A derived observable uses information already present
in one or more authoritative products. A pedagogical representation chooses
how to expose a quantity to answer a learner-facing question; it does not
silently become a new scientific calculation.

Classify proposed work before choosing implementation machinery:

### A. Derived view

The required information already exists in an authoritative persisted field.
Transform the validated artifact and preserve its masks, censoring limits, and
provenance. Do not rerun dynamics. First-flip timescale bins and supported
event-before-horizon maps are examples.

### B. Existing-trajectory observable

The quantity needs new information during a trajectory, but existing validated
dynamics and integration semantics can provide it. Define the observer and its
validity/status contract, establish reference evidence, and reuse validated
integration infrastructure where the semantics match. Do not introduce a new
solver merely because the observer is new.

### C. New dynamical experiment

The quantity requires different dynamics, state, perturbation, tangent
evolution, or integration semantics. Establish a scientifically independent
trusted reference/oracle first. Reuse validated numerical infrastructure only
after bounded evidence demonstrates equivalence for the new contract.

The implementation sequence is therefore:

```text
scientific contract
    ↓
trusted oracle
    ↓
classify computational requirement
    ↓
reuse validated fast infrastructure where semantics match
    ↓
bounded equivalence validation
    ↓
production promotion only when scientific and operational gates pass
```

Do not repeat a naive performance-optimization ladder merely because an
observable is new. The trusted implementation exists to establish scientific
correctness and independence, not to prescribe the eventual production cost.
Where an already validated numerical primitive has matching semantics, reuse it
rather than rediscovering Python → compiled RHS → native solver optimization
from scratch. Infrastructure must never redefine the mathematics to enable
that reuse.

## Roadmap mapping

The [prototype roadmap](../../ROADMAP.md) maps onto this contract as follows:

- **Step 1 — Define the first-flip event contract:** the primitive physical
  observable and trusted reference.
- **Step 2 — Generate a first-flip-time map:** the authoritative persisted
  event-time data product, including dimensionless scaling and censoring.
- **Step 3 — Derive binary flip-threshold maps:** timescale and threshold views
  derived from authoritative first-flip data where the chosen horizon is
  supported; no dynamics rerun.
- **Step 4 — Finite-time stretching as a function of observation window:** a
  separate tangent-space sensitivity observable and authoritative field series.
- **Step 5 — Compare physical-event geometry with sensitivity geometry:** a
  comparative pedagogical analysis of distinct authoritative fields, not a
  conflation of event time and instability.
- **Step 6 — Compound-model comparison:** a model-specific first-flip contract
  and validation step before any simple-model implementation or conclusion is
  claimed to transfer.

## Guarded first-flip routes

The first-flip consumer retains three scientifically equivalent but
operationally distinct implementations. The independent Python `solve_ivp`
route is the trusted oracle. Compiled-RHS + `solve_ivp` preserves that event
solver while accelerating the physical RHS. For the exact validated standard
equal-link/unit-parameter, zero-velocity, T=5 definition on a supported build,
the native DOP853 event loop is the guarded production default. Native
unavailability or accepted numerical rejection recovers through compiled-RHS
`solve_ivp`, then trusted Python where required; programming errors still
propagate.

Accepted routes and prior attempts have distinct provenance. Because route and
build identity are part of the static field definition, native, compiled, and
trusted fields do not silently resume one another. This performance hierarchy
does not change the four signed event surfaces, lifted-angle convention,
censoring, diagnostics, or authoritative scalar contract described in the
[science document](science/first_flip_time.md).

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
