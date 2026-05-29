# Tier 3C Canvas Feasibility

Tier: Phase 6 / Simulation Workbench Tier 3C
Date: 2026-05-29

## Summary

Tier 3C opens a workbench-only Canvas feasibility spike for physical motion
playback.

The question is not whether Canvas is prettier than Plotly. The question is
whether Python can remain the sole mathematical authority while JavaScript owns
only drawing and playback lifecycle. This first pass demonstrates that a
run-scoped Python motion payload can drive a plain Canvas renderer with play,
pause, reset, scrub, clear, and simulated failure states.

Tier 3C.2 extends the same preview with reference-frame controls and
scrub-synced Plotly inspection views. Canvas now shows optional axes, grid, and
origin markers, while the shared scrubber updates Canvas, a time-series marker,
a theta-theta angular state projection marker, and a selected-state readout.

No production `/simulation` page, callback, component ID, CSS, model behavior,
plotting behavior, solver behavior, energy diagnostic, chaos diagnostic, or
Poincare section was changed.

## How To Run

Preview app:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/canvas_motion_preview.py
```

Metrics only:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/canvas_motion_preview.py --metrics-only
```

The preview app starts at:

```text
http://127.0.0.1:8065/
```

## Python And JavaScript Dependency Boundary

Plain dependency map:

```text
Python model run -> position arrays and metadata -> Dash store payload -> JavaScript Canvas manager -> draw selected frame or playback loop
```

Python side:

- constructs the simulation request;
- instantiates the current model classes;
- performs numerical integration;
- calls existing position-precompute logic;
- collects solver metadata and warnings;
- serializes trusted playback data;
- owns all mathematical truth.

Dash transport layer:

- stores the serialized motion payload in `dcc.Store`;
- sends run identity, time samples, bob positions, metadata, and warnings to the
  browser;
- does not stream every animation frame through Python callbacks.

JavaScript side:

- receives already-computed time and position arrays;
- draws rods and bobs on Canvas;
- handles play, pause, reset, and scrub;
- cancels stale playback when run identity changes;
- may show rendering status.

JavaScript must not compute equations of motion, integrate trajectories,
transform user angular velocities into canonical momenta, or make scientific
claims. There is no JavaScript physics.

## Payload Schema

The Tier 3C payload is intentionally explicit and run-scoped:

- `schema_version`;
- `kind`: `success`, `clear`, or `failure`;
- `run_id`;
- `model_type`;
- `system_type`;
- `preset_name`;
- `request_label`;
- `duration_seconds`;
- `sample_count`;
- `time`;
- `positions.x1`, `positions.y1`, `positions.x2`, `positions.y2`;
- `angular_state.theta1_deg`, `angular_state.theta2_deg`;
- `user_initial_conditions`;
- `solver_state_convention`;
- `solver_metadata`;
- `parameters`;
- `warnings`;
- `bounds`;
- `payload_byte_estimate`.

The Canvas renderer needs only `run_id`, `time`, `positions`, `bounds`, and
`sample_count` to draw. The other fields support status, diagnostics, and future
comparison.

The angular samples support synced Plotly inspection. The theta-theta output is
an angular state projection, not a full phase portrait.

Tier 3C does not reduce or cap the selected sample set to make Canvas look
cheap. The browser receives the full selected sample set and maps playback time
to the nearest available sample.

## Canvas Playback Lifecycle

The workbench JavaScript manager tracks:

- active run ID;
- active payload;
- current frame index;
- playing or paused state;
- active `requestAnimationFrame` handle;
- playback start time;
- playback start frame.

On new payload, the manager cancels any existing animation loop if the run ID
changes, replaces the active payload, resets to frame zero, and draws the first
frame or clear/failure state.

On play, it starts one `requestAnimationFrame` loop for the active run. Each
tick verifies the run ID is still current.

On pause, it cancels the loop and preserves the current frame.

On reset, it cancels playback and draws frame zero.

On scrub, it cancels playback and draws the selected frame.

On clear or failure, it cancels playback and clears the Canvas with a state
message.

Tier 3C.2 adds reference-frame options. JavaScript can draw:

- a grid based on the payload bounds;
- physical `x` and `y` axes;
- the pivot/origin marker at `(0, 0)`.

Python coordinates use physical `y` upward. Canvas screen coordinates use `y`
downward. JavaScript applies an equal-aspect display transform from physical
coordinates to screen coordinates; it does not compute physics.

The shared scrubber also updates clientside Plotly inspection views. Playback
marker sync is deferred to avoid Plotly redraws on every animation frame before
Tier 3D defines the interaction contract.

## Test Cases

Metrics were generated for:

| Case | Model | System | Preset | Duration | Samples |
| --- | --- | --- | --- | ---: | ---: |
| short simple Lagrangian | simple | Lagrangian | nonzero velocities | `4.0s` | `640` |
| moderate compound Hamiltonian | compound | Hamiltonian | nonzero velocities | `6.0s` | `1200` |
| larger simple Lagrangian | simple | Lagrangian | small angle | `8.0s` | `2000` |

The nonzero-velocity cases preserve the Tier 1D Hamiltonian convention boundary:
Python converts Hamiltonian angular velocities to canonical momenta before
solving; JavaScript never sees or performs that conversion.

## Metrics Summary

Compact metrics are stored in `tier3c_results.json`. Full arrays are not saved
there.

| Case | Samples | Payload bytes | Bytes/sample | Model build | Precompute | Payload prep |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| simple Lagrangian nonzero | `640` | `88425` | `138.2` | `2.0148s` | `0.000021s` | `0.0017s` |
| compound Hamiltonian nonzero | `1200` | `164761` | `137.3` | `0.3704s` | `0.000028s` | `0.0032s` |
| simple Lagrangian small angle | `2000` | `274831` | `137.4` | `0.0210s` | `0.000040s` | `0.0056s` |

The first simple Lagrangian model build includes cache/equation warmup effects,
so it should not be read as pure integration time.

The Tier 3C.2 payload is larger than the original Tier 3C payload because it now
includes `theta1` and `theta2` arrays for synced analytical inspection.

## Comparison With Tier 3B Plotly Evidence

Tier 3B larger simple Lagrangian metrics:

- current Plotly frames: `200` frames, about `158897` JSON bytes;
- reduced Plotly frames: `80` frames, about `143997` JSON bytes;
- static scrubber: `0` frames, `100` slider steps, about `139773` JSON bytes;
- selected frame: `0` frames, about `124572` JSON bytes.

Tier 3C.2 Canvas payload for the same sample count is about `274831` bytes
because it sends all time samples, all four position arrays, and angular state
arrays for synced inspection. That is not smaller than the measured Plotly
payloads in this first encoding.

This is important: Canvas does not automatically win on transport size. Its
promise is lifecycle control, local playback state, explicit stale-run
cancellation, and a clean path to selected-time inspection without Plotly frame
queues. Payload encoding would need later work before claiming a size win.

## Stale-State Behavior

Implemented behavior:

- every run, clear, and simulated failure gets a new `run_id`;
- JavaScript cancels any active animation loop when a new run ID arrives;
- clear and failure states cancel playback and clear the Canvas;
- play does not start multiple loops for the same active run;
- scrub cancels playback and draws the selected frame;
- reset cancels playback and returns to frame zero.
- axes/grid/origin toggles redraw the current frame without changing physics;
- scrub updates Canvas, Plotly markers, and the selected-state readout.

Observed in this task:

- server start was verified;
- compact metrics were generated;
- browser smoke verified axes/grid toggle, scrub sync, play, pause, reset,
  new-run cancellation, clear, and simulated failure.
- playback-driven Plotly marker sync is deferred.

Manual sequences to complete:

- play animation, then run a new request;
- play animation, then switch model type and run;
- play animation, then switch system type and run;
- play animation, then switch preset and run;
- play animation, then clear;
- play animation, then simulated failure;
- rapidly repeat runs;
- scrub while playing;
- reset after scrub;
- play after scrub.

## What Canvas Does Well

Canvas gives direct control over the playback lifecycle. The code can cancel
`requestAnimationFrame` immediately when run identity changes. That maps well to
the Tier 3 doctrine that no visual state should continue after its simulation
result is superseded.

Canvas also keeps playback local to the browser. Python does not receive a
callback for every animation frame.

Canvas makes selected-time inspection feel architecturally natural because the
renderer can draw any precomputed sample by index.

Tier 3C.2 strengthens this signal: Canvas can serve as the physical motion
surface while Plotly handles analytical inspection views tied to the same
selected frame.

## What Canvas Does Poorly

Canvas is not self-describing in the way Plotly figures are. It does not provide
built-in axes, hover, export, accessibility, or modebar behavior.

Plain JavaScript introduces maintenance burden. Future work would need careful
tests around run identity, browser resizing, scrub behavior, and stale-state
cancellation.

The first payload encoding is larger than comparable Tier 3B Plotly payloads
for the larger case. Canvas should not be promoted with a payload-size claim
until encoding choices are studied.

Adding synced analytical state increased payload size further. That may be an
acceptable tradeoff for inspectability, but it should be decided explicitly in
Tier 3D or Tier 3E.

## Risks

Maintenance risk:

- custom JavaScript must remain small and explicit;
- renderer state needs tests or reliable manual checks;
- future refactors could accidentally move physics into JavaScript.

Integration risk:

- Dash assets must be scoped carefully;
- future production callbacks need a clean result-contract boundary;
- payload serialization size may matter for larger runs.

Accessibility and export limitations:

- Canvas content is not inherently accessible;
- there is no built-in Plotly export modebar;
- keyboard control, screen-reader text, and image export would require extra
  work.

## Recommendation

Canvas should remain a production candidate for physical motion playback, but
it is not ready for promotion yet.

Recommended next task:

Continue with a deeper Canvas interaction spike or Tier 3D interaction contract
focused on the accepted selected-time idea:

- define whether the future workspace needs autoplay, scrub, selected-time
  inspection, or both;
- manually inspect the Tier 3C preview lifecycle;
- compare Canvas against a refined Plotly static scrubber path;
- study payload encoding only after the interaction contract is clearer.

Do not claim Canvas is better solely because it feels smooth once. The credible
claim from this pass is narrower: Canvas gives a clean Python/JavaScript
boundary and a strong lifecycle model, while payload and production integration
remain open.
