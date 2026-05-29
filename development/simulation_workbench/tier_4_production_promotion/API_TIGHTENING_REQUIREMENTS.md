# API Tightening Requirements

Tier: Phase 6 / Simulation Workbench Tier 4
Date: 2026-05-29

These requirements must be resolved before Canvas is wired into the production
Simulation page.

## Units Must Be Explicit

Production payload fields must not use ambiguous names like `theta1` unless the
units are explicit nearby.

Recommended options:

- explicit field names such as `theta1_rad`, `theta2_rad`, `theta1_deg`,
  `theta2_deg`; or
- nested value/unit objects; or
- arrays grouped under a units block that is validated by tests.

The payload must distinguish:

- internal numerical units used by the model;
- display units used by Canvas labels and readouts;
- user-facing request units.

Recommended first production payload:

- use degrees for displayed angular displacement arrays;
- use model length units for `x1`, `y1`, `x2`, `y2`;
- include `state_units` and `position_units`;
- include `internal_initial_state_summary` separately from user-facing initial
  conditions.

## Hamiltonian State Must Not Be Mislabeled

Do not serialize Hamiltonian canonical momenta as `omega1` or `omega2`.

For Hamiltonian runs:

- user-facing initial angular velocities should appear in
  `user_initial_conditions`;
- internal canonical momenta should appear only in
  `internal_initial_state_summary`;
- angular velocity time series should be omitted unless Python provides an
  audited reconstruction.

JavaScript must not infer angular velocities from Hamiltonian momenta.

## Drawable And Non-Drawable States Must Be Distinct

Production payload status must distinguish:

- `success`: may contain drawable arrays;
- `stale`: may contain drawable arrays but must be visibly stale and must not
  autoplay as current;
- `failed`: must not contain drawable success arrays;
- `cleared`: must not contain drawable success arrays;
- `empty`: must not contain drawable success arrays.

This prevents the renderer from accidentally drawing old arrays after failure
or clear states.

Recommended rule:

- JavaScript draws arrays only when `status === "success"` or when `status ===
  "stale"` and the UI explicitly presents the output as stale-inspectable.

## Payload Store Should Be Memory-Scoped

Canvas payloads are runtime state. They should not be persisted accidentally.

Use memory-scoped Dash storage for Canvas payloads unless there is a deliberate
reason otherwise.

Large trajectory arrays should not be written to:

- browser local storage;
- browser session storage;
- URL query state;
- long-lived server-side artifacts;
- logs.

Compact summaries may be logged or tested, but full arrays should remain
runtime payload data.

## Timings Must Be Interpreted Carefully

Workbench stress timings may include:

- equation loading;
- lambdification;
- model construction;
- integration;
- cache effects;
- payload preparation.

Do not treat Tier 3E timings as stable production performance guarantees.

Production readiness should focus on:

- payload size;
- sample count;
- callback latency in the real page;
- browser responsiveness;
- repeated-run behavior;
- long-duration/high-sample-count behavior;
- stale playback absence.

## Schema Versioning Must Be Explicit

The payload should include a schema version such as
`canvas_motion_payload.v1`.

JavaScript should reject or safely ignore unknown schemas rather than guessing.

## Validation Must Be Cheap And Testable

Payload validation should verify:

- required fields;
- status-specific drawable rules;
- array lengths match `sample_count`;
- arrays are finite for success/stale payloads;
- time is monotonic;
- units are present;
- solver metadata is present where expected;
- Hamiltonian momentum is not mislabeled as angular velocity.

Validation should return structured problems rather than raising unhandled
renderer errors.
