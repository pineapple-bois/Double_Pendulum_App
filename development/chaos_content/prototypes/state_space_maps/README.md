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
Generated artifacts live under the ignored `outputs/` tree, with Lyapunov
artifacts under `outputs/lyapunov/`.

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

## Separately authorised 512 x 512 run

The first planned operational field is deliberately bounded to `512 x 512`.
It has not been run by this refactor. When separately authorised, create it
from the repository root with:

```bash
uv run python -m development.chaos_content.prototypes.state_space_maps.runners.generate_lyapunov_periodic_field \
  --samples-per-axis 512 \
  --output development/chaos_content/prototypes/state_space_maps/outputs/lyapunov/lyapunov_finite_time_512.h5 \
  --create
```

After interruption, use the same command with `--resume`. Create refuses an
existing artifact; resume requires a compatible existing artifact and skips
checksum-valid completed tiles.

## Nonclaims

This remains development prototype code. It does not establish arbitrary-
horizon Lyapunov validity, production-scale throughput, a universal fallback
frequency, distributed execution, a general storage abstraction, renderer or
UI architecture, or readiness for a `12000 x 12000` run. The separate
`initial_condition_sensitivity/` prototype is not part of this hierarchy.
