# Canvas Renderer API Contract

Tier: Phase 6 / Simulation Workbench Tier 3E
Date: 2026-05-29

This document defines the production API shape recommended by Tier 3E. It is
not an implementation.

## Responsibility Boundary

Plain dependency map:

```text
Python simulation result -> Canvas payload -> Dash store -> JavaScript renderer -> Canvas views
```

Python owns:

- request validation and normalization;
- model construction;
- numerical integration;
- Hamiltonian velocity-to-momentum conversion through the model layer;
- time, state, and position arrays;
- solver metadata;
- warnings and diagnostics;
- payload construction.

Dash owns:

- transporting the payload to the browser, likely through `dcc.Store`;
- emitting result, stale, cleared, and failed states;
- avoiding Python callbacks per animation frame.

JavaScript owns:

- active run identity;
- selected-frame state;
- play, pause, reset, scrub, clear, and failure lifecycle;
- Canvas drawing;
- local display options such as axes, grid, and trail.

JavaScript must not compute equations of motion, integrate trajectories,
convert Hamiltonian angular velocities to momenta, compute energy diagnostics,
or make scientific claims.

## Python Payload Contract

Production should emit a JSON-serializable payload with this shape:

```json
{
  "schema_version": "canvas_motion_payload.v1",
  "run_id": 42,
  "status": "success",
  "model_type": "simple",
  "system_type": "lagrangian",
  "request_label": "Simple Lagrangian / nonzero velocities / 5s",
  "time": [0.0, 0.005, 0.01],
  "theta1": [45.0, 44.9, 44.8],
  "theta2": [-30.0, -29.9, -29.8],
  "omega1": [0.0, -0.1, -0.2],
  "omega2": [0.0, 0.1, 0.2],
  "x1": [0.7, 0.7, 0.7],
  "y1": [-0.7, -0.7, -0.7],
  "x2": [0.2, 0.2, 0.2],
  "y2": [-1.6, -1.6, -1.6],
  "sample_count": 1000,
  "duration": 5.0,
  "user_initial_conditions": {
    "theta1_deg": 45.0,
    "theta2_deg": -30.0,
    "omega1_deg_per_second": 10.0,
    "omega2_deg_per_second": -5.0
  },
  "internal_initial_state_summary": {
    "state_convention": "angles_and_angular_velocities",
    "values": [0.785398, -0.523599, 0.174533, -0.087266]
  },
  "state_units": {
    "theta1": "degrees",
    "theta2": "degrees",
    "omega1": "degrees/second when available and meaningful",
    "omega2": "degrees/second when available and meaningful"
  },
  "position_units": "model length units",
  "solver_metadata": {
    "integrator": "solve_ivp",
    "success": true,
    "status": 0,
    "message": "The solver successfully reached the end of the integration interval.",
    "nfev": 290,
    "requested_time_count": 1000,
    "returned_time_count": 1000,
    "returned_time_matches_requested": true,
    "solution_shape": [1000, 4]
  },
  "warnings": [
    "Theta-theta projection is not a full phase portrait."
  ],
  "bounds": {
    "min_x": -2.2,
    "max_x": 2.2,
    "min_y": -2.2,
    "max_y": 2.2
  },
  "payload_size_bytes": 175430
}
```

Required top-level fields:

- `schema_version`;
- `run_id` or equivalent animation epoch;
- `status`: `success`, `stale`, `failed`, `cleared`, or `empty`;
- `model_type`;
- `system_type`;
- `preset_name` or `request_label`;
- `time`;
- `theta1`;
- `theta2`;
- `omega1`, if available and meaningful;
- `omega2`, if available and meaningful;
- `x1`, `y1`, `x2`, `y2`;
- `sample_count`;
- `duration`;
- `user_initial_conditions`;
- `internal_initial_state_summary`;
- `state_units`;
- `position_units`;
- `solver_metadata`;
- `warnings`;
- `bounds`;
- `payload_size_bytes`.

Hamiltonian note:

- Hamiltonian solver slots three and four are canonical momenta.
- The user-facing request still accepts `omega1` and `omega2`.
- Production payloads should include user-facing angular velocities in the
  request summary.
- Production payloads should not serialize Hamiltonian momentum slots as
  `omega1` or `omega2`.
- If angular velocity time-series are desired for Hamiltonian runs, add a
  dedicated audited reconstruction step in Python.

## Suggested Python Helper API

Keep the production helper small:

```python
def build_canvas_motion_payload(simulation_result, *, run_id: int) -> dict:
    """Return a JSON-serializable Canvas payload for a completed simulation."""


def validate_canvas_motion_payload(payload: dict) -> list[str]:
    """Return schema/shape/finite-value problems without mutating payload."""


def estimate_canvas_payload_size(payload: dict) -> int:
    """Return compact JSON byte estimate for payload monitoring."""


def summarise_canvas_payload(payload: dict) -> dict:
    """Return compact diagnostics for logs, tests, and UI summaries."""
```

Recommended eventual location:

- `app/serialization/` or `app/components/` for Dash-facing payload helpers;
- `src/double_pendulum/` only for reusable numerical/model data helpers that
  should remain independent of Dash;
- `assets/` for the production JavaScript renderer.

Preferred split:

- model/result data stays under `src/double_pendulum/`;
- UI payload formatting stays under the app layer;
- browser rendering stays in a Dash-served JavaScript asset.

## JavaScript Renderer API

Production should expose one renderer object per Simulation workspace:

```javascript
const renderer = createCanvasSimulationRenderer({
  motionCanvas,
  timeSeriesCanvas,
  projectionCanvas,
  statusElement,
  readoutElement,
});
```

Required methods:

`loadPayload(payload)`

- Validates schema enough to avoid renderer crashes.
- Cancels any active loop if `payload.run_id` differs from the active run.
- Replaces active payload.
- Sets selected frame to `0` for a new success payload.
- Draws initial frame for success.
- Shows failed, cleared, empty, or stale state when appropriate.

`play()`

- Starts playback only for an active success payload.
- Does not start duplicate loops.
- Binds the loop to active `run_id`.
- On each frame, exits immediately if the active `run_id` changed.
- Advances shared selected-frame state.
- Redraws motion, time-series cursor, projection marker, and readout.

`pause()`

- Cancels the animation frame loop.
- Preserves selected frame.
- Sets playback state to `paused`.

`reset()`

- Cancels playback.
- Sets selected frame to `0`.
- Redraws all synced views.

`scrub(frameIndex)`

- Cancels playback or enters scrub state.
- Clamps frame index to payload bounds.
- Updates selected frame/time.
- Redraws all synced views.

`clear()`

- Cancels playback.
- Removes active payload.
- Clears all Canvas panels.
- Sets state to `cleared`.

`showFailure(messageOrPayload)`

- Cancels playback.
- Removes or invalidates drawable payload.
- Shows failure state.
- Prevents old success animation from continuing.

`setOptions({ axes, grid, trail })`

- Updates local display options.
- Does not mark output stale.
- Does not call Python.
- Redraws current selected frame if a payload is available.

`resize()`

- Resizes backing Canvas dimensions for current layout/device pixel ratio.
- Redraws current selected frame.
- Does not change selected frame or run ID.

`destroy()`

- Cancels any active animation loop.
- Removes event listeners if the renderer registered them.
- Clears references to payload and DOM nodes where practical.

## Required Renderer Invariants

- Active `run_id` is checked before every playback draw.
- A new run, clear, failure, or stale transition cancels old playback.
- Selected frame is shared across all Canvas panels.
- JavaScript never mutates scientific arrays.
- JavaScript never computes physics.
- Python is not called per animation frame.
- Stale output is visually distinct from current output.
- Failure and clear states cannot leave old successful motion playing.

## Deferred API Questions

- Whether payload arrays should be flat top-level arrays or nested under
  `positions` and `angular_state`.
- Whether production should compress or quantize payload values.
- Whether Canvas-native analytical views need keyboard navigation and table
  equivalents for accessibility.
- Whether Plotly should be used for optional analytical drill-down while Canvas
  owns motion playback.
