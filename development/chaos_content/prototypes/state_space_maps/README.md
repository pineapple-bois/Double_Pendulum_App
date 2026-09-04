# State-space maps prototype

This is the connected prototype for trustworthy scalar fields over double-
pendulum state space. It brings three earned concerns under one architectural
boundary while keeping their dependencies explicit:

```text
neutral field/domain concepts
          |
          +---------------------+
          |                     |
          v                     v
     generation       scientific consumers
          |          (Lyapunov, first flip)
          +----------+----------+
                   v
             concrete runners
```

`src/state_space_fields.py` defines coordinate-neutral scalar outcomes,
reference line/rectangle sampling, and the half-open periodic angular domain.
`src/generation/` owns deterministic rectangular work units, bounded process
execution, coordinator-owned HDF5 persistence/resume, and dynamics-free
validation. It never imports observable science. `src/lyapunov/` owns Candidate-A
geometry, the finite-time renormalised tangent observable, its oracle and
compiled evaluators. `src/first_flip/` owns the Experiment 020 physical
first-completed-link-revolution reference and its capped scalar adapter. Each
consumer binds independently to neutral field generation.

Executable composition lives in `runners/`; scientific explanation and the
architectural detail live in `docs/`. Focused tests mirror those boundaries.
The existing `outputs/lyapunov/` directory contains legacy development and
validation artifacts from the prototype-development strand. Preserve those
files as historical evidence. Manually generated operational deliverables use
the separate ignored `outputs/finite_time_field/` boundary.

## Current validated boundary

The validated system combines reusable neutral scalar-field generation with
two demonstrated scientific consumers: the finite-time one-vector stretching
rate and dimensionless capped first-flip time. It preserves the declared
`[theta2, theta1]` storage orientation, exact
`[-pi, pi)` periodic axes, bounded local execution, and fail-closed persisted
resume state without making the neutral machinery depend on Lyapunov science.

The HDF5 scalar field is the authoritative scientific artifact. JSON summaries
and images are derivatives and can be regenerated from a closed, validated
artifact without rerunning dynamics.

## Documentation

- [Software architecture](docs/architecture.md) explains the neutral field,
  generation, execution, persistence, and scientific-consumer boundaries.
- [Finite-time one-vector stretching](docs/science/finite_time_stretching.md)
  defines the current observable, its provenance, and its claim boundary.
- [First-flip-time field and pilot](docs/science/first_flip_time.md) defines the
  promoted physical observable, capped-censor persistence contract, and 32×32
  pilot evidence.
- [Sensitivity to Lyapunov storyboard](docs/pedagogy/sensitivity_to_lyapunov.md)
  presents the teaching progression from nearby trajectories to renormalised
  finite-time stretching.

## First-flip pilot field

The promoted first-flip runner composes the Experiment 020 reference with the
same neutral generation and HDF5 pipeline. The accepted pilot uses 32 samples
per axis and a 5 s observation horizon:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_first_flip_periodic_field \
  --samples-per-axis 32 \
  --observation-horizon-seconds 5 \
  --create
```

Use `--resume` with the same arguments to verify and resume the checksummed
artifact. `--create` refuses to replace an existing field. The authoritative
pilot and readable manifest live in `outputs/first_flip_pilot/`; the complete
scientific, censoring, persistence, and measured-evidence record is in the
[first-flip pilot document](docs/science/first_flip_time.md). No first-flip
renderer is part of this integration.

## Manual operational finite-time field

The operational runner evaluates the already-validated one-vector Candidate-A
finite-time tangent-stretching observable over the full periodic initial-angle
domain. This packages the established system; it is not a new numbered
experiment and does not change its scientific, numerical, work-unit, process,
or persistence contracts.

The single `--samples-per-axis N` option selects the square resolution. That
value determines both axes, the field shape and cell/work-unit totals, progress
reporting, manifest metadata, and the default `finite_time_field_N.h5` and
`finite_time_field_N.json` names. Generation may take significant time. Run it
manually from the repository root; Codex and the rendering command do not start
it automatically. Generation prints lightweight coordinator-level progress at
approximately ten-percent milestones, including elapsed time, throughput, and
an explicitly approximate ETA.

The promoted execution policy uses four spawn workers and recycles each pool at
a tile boundary before it would exceed 2,048 returned cell outcomes pool-wide.
This operating point is evidence-driven: in the bounded `64 x 64` runner-level
validation it reduced mean adjusted runner wall time from 21.125 s to 16.917 s
(19.88%) while adding about 170 MiB of worker RSS across the four processes.
That is a bounded tradeoff, not a universal performance claim. Recycling
remains necessary because worker RSS continued to grow with lifetime; 4,096,
larger limits, and unlimited worker reuse remain unevidenced. See the
[performance investigation](investigations/performance/README.md) for the
measurement boundaries.

The established worked example uses `512` samples on each axis. Its
authoritative array shape is `(512, 512)` in stored `[theta2, theta1]` order,
containing 262,144 cells.

### Create

Create the authoritative HDF5 field with:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field \
  --samples-per-axis 512 \
  --create
```

After generation and oracle validation succeed, this writes:

```text
development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_512.h5
development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_512.json
```

The HDF5 file is the authoritative scientific artifact. `--create` refuses to
replace an existing file. The JSON sidecar is a human-readable manifest of the
field definition, scientific and software provenance, execution policy, run
timings and throughput, route/status counts, and oracle-validation result. It
is not authoritative and is not required for resume or rendering.

### Resume

If generation is interrupted, resume the same artifact with:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field \
  --samples-per-axis 512 \
  --resume
```

Resume uses the validated compatibility checks, completion markers, checksums,
and tile state. It skips checksum-valid completed tiles, retries interrupted
tiles, and fails closed instead of replacing an incompatible or corrupt field.
Keep the same repository revision and locked software environment between
create and resume because those provenance values are part of compatibility.
At startup it reports the already-completed and remaining work units, then
continues with the same lightweight progress milestones. A successful resumed
run writes or refreshes the JSON manifest only after final validation passes.

The pool limit is recorded in each completed tile's execution provenance; it
is not part of the static HDF5 field definition. If the field definition and
software provenance still match, resuming an incomplete artifact across this
policy change is deliberately compatible: old completed tiles retain `1024`
and newly completed tiles record `2048`. An artifact made by an earlier
repository revision will normally still fail closed because its Git provenance
differs. Completed, internally valid old-policy HDF5 artifacts remain readable
and renderable without resuming them.

### Render

After generation completes, render the persisted HDF5 field with:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.render_finite_time_field \
  development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_512.h5
```

The single render command reads and validates the persisted HDF5 data, then
saves the same Matplotlib figure directly as:

```text
development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_512.png
development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_512.pdf
```

Rendering does not import or invoke the Lyapunov evaluator, scalar-field
runner, dynamics, or computation workers. PNG and PDF are derivative visual
representations and may be regenerated; retain the authoritative HDF5 file.
The JSON manifest is likewise optional: rendering reads only HDF5. All
operational artifacts in `outputs/finite_time_field/` are ignored by Git.

### Changing resolution

Choose another square resolution by changing only `--samples-per-axis`. For
example, creation at `1024 × 1024` is selected with:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field \
  --samples-per-axis 1024 \
  --create
```

This naturally selects `finite_time_field_1024.h5` and
`finite_time_field_1024.json` in the same operational output directory. Pass
that HDF5 path to the same rendering command to obtain matching
`finite_time_field_1024.png` and `finite_time_field_1024.pdf` derivatives.
Resume likewise uses the same resolution value. A custom `--output foo.h5`
keeps all derivative naming coherent: the manifest is `foo.json`, and the
renderer writes `foo.png` and `foo.pdf`. The `1024` example is a naming and
usage example, not a recommendation or performance claim.

Inspect the exact CLI options with:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field --help
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.render_finite_time_field --help
```

## Nonclaims

This remains development prototype code. It does not establish arbitrary-
horizon Lyapunov validity, production-scale throughput, a universal fallback
frequency, distributed execution, a general storage abstraction, renderer or
UI architecture, or readiness for a `12000 x 12000` run. The separate
`initial_condition_sensitivity/` prototype is not part of this hierarchy.
