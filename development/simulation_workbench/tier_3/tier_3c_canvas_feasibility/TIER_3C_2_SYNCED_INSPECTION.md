# Tier 3C.2 Canvas-Native Synced Inspection

Tier: Phase 6 / Simulation Workbench Tier 3C.2
Date: 2026-05-29

## Summary

Tier 3C.2 revises the Canvas preview so Canvas is tested as the synchronized
motion and inspection renderer, not only the physical motion renderer.

The active preview now uses Canvas-native panels for:

- physical pendulum motion;
- angular displacement time series;
- theta-theta angular state projection;
- selected-time/state readout.

The earlier Plotly analytical panels are removed from the active preview. Plotly
remains useful for future analytical views, but it should not define the Tier
3C.2 architecture.

## Why Plotly Panels Were Removed

The previous Plotly-panel direction proved a useful idea, but the wrong
architecture for this spike. It mixed a Canvas playback lifecycle with Plotly
inspection redraws, which made Tier 3C less clear.

Tier 3C.2 now tests the cleaner question:

Can one JavaScript Canvas manager render motion and synced inspection from one
Python-owned payload and one selected-frame state?

Plotly is deferred as a possible future fallback for richer analytical
inspection, hover, export, and accessible chart features.

## Responsibility Boundary

Plain dependency map:

```text
Python model run -> arrays and metadata -> Dash payload -> JavaScript Canvas manager -> draw selected frame and synced inspection views
```

Python owns:

- simulation request construction;
- model construction;
- numerical integration;
- Hamiltonian velocity-to-momentum conversion through existing model behavior;
- bob position arrays;
- angle/state arrays;
- solver metadata;
- warning metadata;
- run identity;
- payload preparation.

Dash owns:

- transporting the run-scoped payload to the browser;
- storing the latest payload in `dcc.Store`;
- not streaming animation frames through Python callbacks.

JavaScript owns:

- active run ID;
- selected frame;
- playback state;
- play, pause, reset, and scrub;
- stale-run cancellation;
- Canvas rendering;
- current-time cursor;
- projection marker;
- status/readout updates.

JavaScript must not own equations of motion, numerical integration, physical
correctness, velocity-to-momentum conversion, energy diagnostics, or chaos
diagnostics.

## Canvas Payload Schema

The active payload includes:

- `schema_version`;
- `kind`;
- `run_id`;
- `model_type`;
- `system_type`;
- `preset_name`;
- `time`;
- `positions.x1`, `positions.y1`, `positions.x2`, `positions.y2`;
- `angular_state.theta1_deg`, `angular_state.theta2_deg`;
- `sample_count`;
- `duration_seconds`;
- `user_initial_conditions`;
- `solver_metadata`;
- `warnings`;
- `bounds`;
- `payload_byte_estimate`.

Full arrays exist only in the live Dash payload. Compact results JSON omits
arrays.

## Canvas Panel Architecture

The JavaScript manager has one shared payload and one shared selected frame.

It uses separate draw functions:

- `drawMotion(frame)`;
- `drawTimeSeries(frame)`;
- `drawProjection(frame)`;
- `selectedReadout(frame)`.

The playback loop advances the shared selected frame and redraws all three
Canvas panels from the same state. Scrub does the same, without Python
callbacks per frame.

## Canvas Panels

Motion view:

- rods;
- bobs;
- optional trail;
- pivot marker;
- optional axes;
- optional grid;
- equal-aspect physical scaling.

Time-series view:

- `theta1(t)`;
- `theta2(t)`;
- optional axes/grid;
- current-time cursor;
- selected `theta1` and `theta2` markers.

Angular state projection:

- theta-theta angular state projection;
- optional axes/grid;
- selected-state marker.

This projection is not a full phase portrait.

## Axes, Grid, And Coordinate Mapping

Python supplies physical coordinates:

- `x` increases to the right;
- `y` increases upward;
- the pivot is the physical anchor at `(0, 0)`.

Canvas screen coordinates have `y` increasing downward, so JavaScript applies a
rendering transform. The transform preserves equal physical scale for the
motion view. This is rendering only; it is not physics.

Axes and grid can be toggled. The pivot is visually anchored with a marker, but
the preview no longer labels it as “origin.”

## Sync Status

Works now:

- scrub updates motion Canvas;
- scrub updates time-series cursor and markers;
- scrub updates angular projection marker;
- scrub updates selected-time/state readout;
- playback updates all three Canvas panels from the same selected-frame state;
- axes/grid toggles redraw all Canvas panels;
- play, pause, reset, clear, failure, and stale-run cancellation remain in one
  Canvas manager.

Partial or deferred:

- no Plotly analytical fallback is active in Tier 3C.2;
- no export, hover, or accessibility layer exists yet;
- no automated browser regression exists for Canvas lifecycle behavior.

## Updated Metrics

Regenerated compact metrics:

| Case | Samples | Payload bytes | Bytes/sample |
| --- | ---: | ---: | ---: |
| simple Lagrangian nonzero | `640` | `88425` | `138.2` |
| compound Hamiltonian nonzero | `1200` | `164761` | `137.3` |
| simple Lagrangian small angle | `2000` | `274831` | `137.4` |

The payload carries physical positions plus angular samples. Canvas-native
inspection strengthens the interaction model, but it does not make Canvas a
payload-size win.

## Production-Candidate Signal

Canvas is a stronger production candidate after this revision because it can
own the full synced inspection loop:

- physical motion;
- selected-time inspection;
- time-series cursor;
- angular projection marker;
- playback lifecycle;
- stale-run cancellation.

This does not mean Canvas is ready for production promotion. Tier 3D still
needs to define the accepted interaction contract.

## Remaining Risks Before Tier 3D

- Browser lifecycle behavior needs fuller manual or automated coverage.
- Payload size remains a real concern.
- Canvas accessibility/export behavior is unresolved.
- Canvas-native charts lack Plotly hover, zoom, and export behavior.
- Future maintainers must keep physics out of JavaScript.
- The grid and axes are visual context, not numerical validation.

## Recommended Next Task

Proceed to Tier 3D interaction contract.

Tier 3D should decide the accepted lifecycle and sync model for run, rerun,
clear, failure, input-stale state, play, pause, reset, scrub, selected time,
and whether production needs Canvas-native charts, Plotly analytical fallback,
or a hybrid split.
