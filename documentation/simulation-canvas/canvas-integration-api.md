# Canvas Integration API

This document records the accepted production Canvas integration boundary and
the payload shape currently implemented in the repository.

## Authority boundary

Python owns the mathematical truth.

JavaScript owns rendering, playback, selected-frame inspection, resize handling,
and local control state only.

JavaScript must not:

- integrate trajectories;
- compute physics;
- infer Hamiltonian angular velocities;
- transform solver state conventions;
- relabel canonical momenta as angular velocities.

Canvas is the preferred renderer for physical motion and synced selected-time
inspection. Plotly and Matplotlib remain in the codebase as retained plotting
helpers, rollback/fallback options, and possible future analytical inspection
paths, but the normal Simulation run callback no longer generates legacy Plotly
figures.

## Current production files

- Payload builder and validator: `app/serialization/canvas_payload.py`
- Dash state stores and Canvas targets:
  `app/components/simulation_interaction.py`
- Simulation callback wiring: `app/callbacks/simulation.py`
- Browser renderer: `assets/simulation-canvas-renderer.js`
- Current numerical tests: `tests/numerical/test_canvas_payload.py`
- Current integration shell tests:
  `tests/integration/test_simulation_interaction_shell.py`

## Payload schema

Current schema version:

```text
canvas_motion_payload.v1
```

The payload is built by `build_canvas_motion_payload(...)`. It is JSON
serializable and memory-scoped in Dash via `dcc.Store`.

Common fields currently emitted:

- `schema_version`
- `run_id`
- `status`
- `model_type`
- `system_type`
- `request_label`
- `sample_count`
- `duration_s`
- `time_units`
- `state_units`
- `position_units`
- `user_initial_conditions`
- `internal_initial_state_summary`
- `solver_metadata`
- `warnings`
- `errors`
- `message`
- `bounds`
- `rendering`
- `payload_size_bytes`

Drawable success or stale payloads also include:

- `time_s`
- `theta1_deg`
- `theta2_deg`
- `x1`
- `y1`
- `x2`
- `y2`
- `parameters`

Lagrangian payloads additionally include audited angular velocity arrays:

- `omega1_deg_per_s`
- `omega2_deg_per_s`

Hamiltonian payloads intentionally omit angular velocity time series. The
solver state uses canonical momenta, and the payload carries a warning:
Hamiltonian angular velocity time series are omitted because the solver state
uses canonical momenta.

## Status model

Current payload statuses are:

- `success`: drawable and autoplay-eligible.
- `stale`: drawable for inspection, but autoplay is disabled and the payload
  must not be treated as current output.
- `failed`: non-drawable; contains no success arrays.
- `cleared`: non-drawable; contains no success arrays.
- `empty`: non-drawable pre-run state; contains no success arrays.

The browser renderer also has a local `running` state while a new run is being
prepared, but `running` is not a Python payload status.

For `success` and `stale`, `rendering.drawable` is true. For `failed`,
`cleared`, and `empty`, `rendering.drawable` is false and drawable arrays must
not be present.

## Parameters and units

The payload currently serializes model parameters under:

```text
parameters.values
```

Symbol keys are stringified, for example `l1`, `l2`, `g`, `m1`, `m2`, `M1`, or
`M2` depending on model type.

Current unit labels:

- `time_units.time_s`: `seconds`
- `theta1_deg`, `theta2_deg`: `degrees`
- Lagrangian `omega1_deg_per_s`, `omega2_deg_per_s`: `degrees/second`
- `position_units`: `model_length_units`
- parameter length units: `model_length_units`
- parameter mass units: `model_mass_units`
- parameter gravity units: `model_length_units/second^2`
- Hamiltonian canonical momenta: `canonical_momentum_internal_units`

The application does not yet provide a richer dimensional-units system.

## Initial conditions and state conventions

User-facing initial conditions are always:

```text
theta1, theta2, omega1, omega2
```

The UI collects those values in degrees and degrees per second.

Lagrangian solver state convention:

```text
angles_and_angular_velocities
```

Hamiltonian solver state convention:

```text
angles_and_canonical_momenta
```

For Hamiltonian simulations, Python converts user-facing angular velocities to
canonical momenta before integration. JavaScript must not reverse-engineer,
infer, or display those momenta as angular velocity series.

## Solver metadata

The current payload includes `solver_metadata` from
`src/double_pendulum/models/metadata.py`.

Current metadata fields include:

- `policy_name`
- `integrator`
- `method`
- `rtol`
- `atol`
- `success`
- `status`
- `message`
- `nfev`
- `njev`
- `nlu`
- `requested_time_count`
- `returned_time_count`
- `requested_time_start`
- `requested_time_end`
- `returned_time_start`
- `returned_time_end`
- `returned_time_matches_requested`
- `solution_shape`
- `solver_kwargs`

For `solve_ivp`, success/status/message fields are populated from SciPy. The
older `odeint` path exposes partial metadata and does not claim solver status.

## Payload size

Payloads include `payload_size_bytes`, calculated as a compact JSON byte
estimate by `estimate_canvas_payload_size(...)`.

Payload size is measurable, but compression, quantization, streaming, and final
large-run acceptance thresholds are deferred. Long-duration runs should not be
assumed safe merely because the current payload schema is compact enough for
representative tests.

## Deferred or planned fields

The Simulation Workbench discusses energy diagnostics, chaos diagnostics,
runtime timings, and richer validation data. These are not production payload
fields unless they appear in the current code and tests.

Deferred:

- energy diagnostics and drift claims;
- chaos diagnostics;
- tolerance-sensitivity evidence;
- solver-method equivalence;
- long-duration scientific validity;
- payload compression or quantization;
- richer dimensional unit metadata.

## Known limitations

- Energy diagnostics are deferred unless separately implemented and tested.
- Chaos diagnostics are deferred.
- Long-duration scientific validity is not proven.
- Tolerance sensitivity is not proven.
- Solver-method equivalence is not proven.
- Hamiltonian state conventions require care because the internal state is
  canonical momenta, not angular velocities.
- Canvas accessibility/export completeness is not yet established.
