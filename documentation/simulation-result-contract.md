# Simulation Result Contract

This document describes the contract between backend simulation code, Dash
callbacks, Dash stores, and Canvas rendering.

## Successful result

A successful simulation result currently means:

- user inputs pass `validate_inputs(...)`;
- a `DoublePendulumLagrangian` or `DoublePendulumHamiltonian` instance is
  constructed without exception;
- SciPy solver metadata does not report failure for the active path;
- positions are precomputed;
- `build_canvas_motion_payload(...)` creates a `success` payload;
- `validate_canvas_motion_payload(...)` returns no problems;
- the payload contains finite arrays with lengths matching `sample_count`.

Required drawable fields for Canvas are:

- `time_s`
- `theta1_deg`
- `theta2_deg`
- `x1`
- `y1`
- `x2`
- `y2`

The Canvas renderer draws physical motion, angular displacement, and
theta-theta projection from those Python-built arrays.

## Invalid or failed result

An invalid or failed result currently means one of:

- user input validation failed;
- model construction failed;
- solver metadata reports failure;
- payload construction failed;
- payload validation failed.

Failed payloads use `status: failed`, include no drawable success arrays, set
`sample_count` to `0`, and set `rendering.drawable` and
`rendering.autoplay_allowed` to false.

Cleared and empty states follow the same non-drawable-array rule.

## Stale result

When inputs change after a successful run, the last drawable payload may be
kept as `status: stale`. Stale payloads are inspectable, but they are not
current results:

- `rendering.drawable` remains true;
- `rendering.autoplay_allowed` is false;
- `rendering.stale` is true;
- playback is cancelled;
- UI copy tells the user to rerun.

Stale results must never be silently treated as fresh `success` results.

## Required, diagnostic, and display fields

Rendering-required fields:

- `schema_version`
- `run_id`
- `status`
- `sample_count`
- `time_s`
- `theta1_deg`
- `theta2_deg`
- `x1`
- `y1`
- `x2`
- `y2`
- `bounds`
- `rendering`

Diagnostic fields:

- `solver_metadata`
- `warnings`
- `errors`
- `message`
- `payload_size_bytes`
- `internal_initial_state_summary`
- `parameters`

Display/readout fields:

- `model_type`
- `system_type`
- `request_label`
- `duration_s`
- `time_units`
- `state_units`
- `position_units`
- `user_initial_conditions`
- Lagrangian `omega1_deg_per_s` and `omega2_deg_per_s` when present.

## Units

Internal model integration uses radians for angles. Lagrangian internal angular
velocities are radians per second. Hamiltonian internal momenta use canonical
momentum units.

User-facing controls use:

- angles in degrees;
- angular velocities in degrees per second;
- duration in seconds;
- model lengths, masses, and gravity in the current app's model-unit labels.

Payload display arrays currently use:

- `time_s` in seconds;
- `theta1_deg` and `theta2_deg` in degrees;
- Lagrangian `omega1_deg_per_s` and `omega2_deg_per_s` in degrees per second;
- positions in model length units.

## Hamiltonian convention

The UI still accepts user-facing angular velocities for Hamiltonian runs. The
Python model converts those angular velocities to canonical momenta before
solving.

Hamiltonian payloads must not serialize canonical momenta as angular velocity
series. If angular velocity series are needed for Hamiltonian inspection later,
they require an explicit audited backend calculation and tests.

## Validation warnings

Validation failures should be surfaced through the run validation/status areas
and represented as `failed` payloads without drawable arrays.

Payload warnings are allowed for accepted-but-limited states, such as
Hamiltonian omission of angular velocity time series. Warnings should be shown
or made inspectable through diagnostics rather than hidden.

## Current gaps

The current implementation largely satisfies the Canvas payload/status
contract, but the broader simulation-result contract is not a complete
scientific validation system.

Known gaps:

- no production energy diagnostic contract;
- no chaos diagnostic contract;
- no long-run validity guarantees;
- no documented tolerance-sensitivity acceptance thresholds;
- no solver-method equivalence contract;
- no full browser automation coverage for every Canvas lifecycle path.
