# Callback Rendering Flow

This document records the current Dash callback and Canvas rendering flow for
the Simulation page.

## User flow

1. User opens `/simulation`.
2. Dash renders the Simulation layout from `app/pages/simulation.py`.
3. The left control rail comes from `app/components/simulation_controls.py`.
4. The Canvas inspection workspace, stores, playback controls, and diagnostics
   come from `app/components/simulation_interaction.py`.
5. The initial Canvas payload store contains an `empty` non-drawable payload.
6. The user changes controls and presses `Run simulation`.
7. Python validates inputs, runs the selected backend model, builds a Canvas
   payload, and updates Dash stores.
8. A clientside callback calls
   `window.DoublePendulumCanvasRenderer.applyState(...)`.
9. The renderer draws or clears Canvas output based on payload/result state.

## Validation and simulation

Simulation callbacks live in `app/callbacks/simulation.py`.

Input validation uses `validate_inputs(...)` from
`src/double_pendulum/validation/dash.py`.

For successful runs:

- callback `update_graphs(...)` responds to `submit-val.n_clicks`;
- `build_simulation_run_result(...)` validates inputs;
- time samples are derived from the selected time interval;
- selected `model_type` and `system_type` choose
  `DoublePendulumLagrangian` or `DoublePendulumHamiltonian`;
- positions are precomputed;
- `build_canvas_motion_payload(...)` creates a success payload;
- `validate_canvas_motion_payload(...)` gates the result;
- Dash stores and status/diagnostic areas are updated together.

For input changes after a successful run:

- callback `mark_output_stale_on_input_change(...)` marks the active payload
  stale when appropriate;
- invalid inputs produce a failed non-drawable payload;
- successful previous arrays are not left behind in failed/empty states.

## Dash stores

Current memory-scoped stores:

- `canvas-motion-payload-store`
- `simulation-result-state-store`
- `simulation-playback-state-store`

Payload arrays are runtime state and should remain memory-scoped unless a
future task deliberately designs persistence.

## Canvas trigger

The server callback updates stores. A clientside callback watches those stores
and calls:

```javascript
window.DoublePendulumCanvasRenderer.applyState(payload, resultState, playbackState)
```

The renderer lives in `assets/simulation-canvas-renderer.js`, which Dash serves
automatically from the assets directory.

## Playback and selected frame

Playback controls are local browser interactions:

- play;
- pause;
- reset;
- scrub;
- axes/grid toggles;
- selected-state readout;
- frame/time indicator.

Canvas playback uses the Python-built `time_s` array to advance frames. It does
not call Python during playback and does not mutate the simulation payload.

Stale payloads may be scrubbed/inspected but not played.

## State representation

Current result states:

- `empty`: no run yet; non-drawable.
- `success`: current drawable payload; autoplay allowed.
- `stale`: previous drawable payload after inputs changed; autoplay disabled.
- `failed`: validation/model/solver/payload failure; non-drawable.
- `cleared`: supported by the payload contract, though no prominent production
  clear-control path is currently documented here.
- `running`: local browser-side state while a new run is being prepared.

## Callback-sensitive IDs

Do not rename these casually. Any rename must update all dependent layout,
callback, test, JavaScript, and documentation references together.

Control and input IDs:

- `submit-val`
- `simulation-run-validation-message`
- `scroll-target`
- `model-type`
- `system-type`
- `param_g`
- `param_l1`
- `param_l2`
- `param_m1`
- `param_m2`
- `param_M1`
- `param_M2`
- `init_cond_theta1`
- `init_cond_theta2`
- `init_cond_omega1`
- `init_cond_omega2`
- `initial-state-preset`
- `initial-state-preset-apply-store`
- `time_start`
- `time_end`
- `unity-parameters`

Canvas/state IDs:

- `canvas-motion-payload-store`
- `simulation-result-state-store`
- `simulation-playback-state-store`
- `simulation-interaction-shell`
- `canvas-inspection-workspace`
- `canvas-motion-placeholder`
- `canvas-time-series-placeholder`
- `canvas-projection-placeholder`
- `canvas-motion-view`
- `canvas-time-series-view`
- `canvas-projection-view`
- `selected-state-readout`
- `simulation-status-message`
- `run-summary-area`
- `solver-diagnostics-area`
- `simulation-play-button`
- `simulation-pause-button`
- `simulation-reset-button`
- `simulation-scrubber`
- `simulation-display-options`
- `simulation-frame-indicator`
- `simulation-renderer-sync-signal`
- `simulation-diagnostics-toggle`
- `simulation-diagnostics-content`

## Plotly paths

Legacy Plotly output containers are no longer rendered by the normal
Simulation page, and the normal run callback no longer emits Plotly figures.

Plotly-related helpers and model methods remain in the codebase as retained
fallback or future analytical-inspection paths. Current integration tests
assert that legacy Plotly output IDs are absent from the active Simulation
layout.
