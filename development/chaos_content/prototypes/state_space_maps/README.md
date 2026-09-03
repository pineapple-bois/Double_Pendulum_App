# State-space maps prototype

This is the connected prototype for trustworthy scalar fields over double-
pendulum state space. It brings three earned concerns under one architectural
boundary while keeping their dependencies explicit:

```text
neutral field/domain concepts
          |
          +----------------+
          |                |
          v                v
     generation         Lyapunov science
          |                |
          +--------+-------+
                   v
             concrete runners
```

`src/state_space_fields.py` defines coordinate-neutral scalar outcomes,
reference line/rectangle sampling, and the half-open periodic angular domain.
`src/generation/` owns deterministic rectangular work units, bounded process
execution, coordinator-owned HDF5 persistence/resume, and dynamics-free
validation. It never imports Lyapunov code. `src/lyapunov/` owns Candidate-A
geometry, the finite-time renormalised tangent observable, its oracle and
compiled evaluators, and the adapter that binds this science to neutral field
generation.

Executable composition lives in `runners/`; scientific explanation and the
architectural detail live in `docs/`. Focused tests mirror those boundaries.
The existing `outputs/lyapunov/` directory contains legacy development and
validation artifacts from the prototype-development strand. Preserve those
files as historical evidence. Manually generated operational deliverables use
the separate ignored `outputs/finite_time_field/` boundary.

## Current validated boundary

The reusable pipeline preserves
`values[theta2_index, theta1_index]`, exact `[-pi, pi)` periodic axes,
deterministic `8 x 8` work units with clipped edges, four spawn-isolated
workers with bounded lifecycle, compact status/route arrays, and fail-closed
HDF5 tile completion and checksums. The first consumer uses the promoted
hybrid finite-time Lyapunov evaluator: compiled DOP853 normally, with the
compiled-RHS `solve_ivp` oracle used only for the independently verified
endpoint `max_step` incompatibility.

The HDF5 scalar field is the authoritative scientific artifact. JSON summaries
and images are derivatives and can be regenerated from a closed, validated
artifact without rerunning dynamics.

See [the architecture document](docs/architecture.md) for neutral generation
contracts and [the Lyapunov documentation](docs/lyapunov/README.md) for the
observable, evaluators, validation evidence, and mathematical storyboard.

## Manual operational finite-time field

The operational runner evaluates the already-validated one-vector Candidate-A
finite-time tangent-stretching observable over the full periodic initial-angle
domain. This packages the established system; it is not a new numbered
experiment and does not change its scientific, numerical, work-unit, process,
or persistence contracts.

For `512` samples on each axis, the authoritative array shape is `(512, 512)`
in stored `[theta2, theta1]` order, containing 262,144 cells. Generation may
take significant time. Run it manually from the repository root; Codex and the
rendering command do not start it automatically.

### Create

Create the authoritative HDF5 field with:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field \
  --samples-per-axis 512 \
  --create
```

This writes:

```text
development/chaos_content/prototypes/state_space_maps/outputs/finite_time_field/finite_time_field_512.h5
```

The HDF5 file is the authoritative scientific artifact. `--create` refuses to
replace an existing file.

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
All operational artifacts in `outputs/finite_time_field/` are ignored by Git.
Other resolutions use the same directory and resolution-specific filename,
for example `finite_time_field_1024.*`; this is a naming convention, not a
recommendation or performance claim.

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
