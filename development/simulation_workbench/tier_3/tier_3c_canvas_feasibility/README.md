# Tier 3C Canvas Feasibility

Tier 3C tests whether Python-generated double-pendulum position data can drive
a lightweight browser Canvas renderer for physical motion playback.

This is a workbench-only feasibility spike. It does not replace Plotly
analytical plots, redesign `/simulation`, modify production callbacks, change
model behavior, or make a final renderer decision.

Tier 3C.2 adds inspectability polish: axes/grid/origin display options and
scrub-synced Plotly analytical views.

## Python And JavaScript Boundary

Plain dependency map:

```text
Python model run -> position arrays and metadata -> Dash store payload -> JavaScript Canvas manager -> draw selected frame or playback loop
```

Python owns:

- simulation request construction;
- current model-class instantiation;
- numerical integration;
- position precompute;
- solver metadata and warnings;
- serialization of trusted playback data;
- all mathematical truth.

Dash owns:

- transporting the run-scoped motion payload through `dcc.Store`;
- carrying run identity, time samples, bob positions, metadata, and warnings to
  the browser;
- avoiding server callbacks for every animation frame.

JavaScript owns:

- receiving already-computed time and position arrays;
- drawing rods and bobs on Canvas;
- play, pause, reset, and scrub;
- drawing optional axes, grid, and origin reference marks;
- cancelling stale playback when run identity changes;
- lightweight render status.

JavaScript must not compute equations of motion, integrate trajectories,
convert angular velocities to canonical momenta, or make scientific claims.
There is no JavaScript physics.

## How To Run

From the repository root:

```bash
python development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/canvas_motion_preview.py
```

On systems where `python` is unavailable, use the project venv:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/canvas_motion_preview.py
```

The preview starts at:

```text
http://127.0.0.1:8065/
```

To regenerate compact metrics without starting the Dash server:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/canvas_motion_preview.py --metrics-only
```

## Files

- `canvas_motion_preview.py` - Dash preview and compact metrics runner.
- `assets/canvas_motion.js` - workbench-only Canvas playback manager.
- `TIER_3C_CANVAS_FEASIBILITY.md` - feasibility report and recommendation.
- `TIER_3C_2_SYNCED_INSPECTION.md` - focused note on reference frame and synced inspection.
- `tier3c_results.json` - compact metrics; no full arrays are saved.

## Reference Frame And Inspection

Python supplies physical coordinates with `x` increasing right and `y`
increasing upward. Canvas screen coordinates have `y` increasing downward, so
JavaScript applies an equal-aspect rendering transform before drawing. This is
only a display transform.

The preview includes toggles for:

- axes;
- grid;
- origin/pivot marker.

The shared scrubber updates:

- the Canvas frame;
- a marker on the angular displacement time series;
- a marker on the theta-theta angular state projection;
- a selected-time/state readout.

Playback marker sync is deferred. Playback updates Canvas locally; Plotly marker
updates happen on scrub so the preview avoids Python callbacks or Plotly redraws
on every animation frame.

## What This Can Prove

The preview can show whether a browser Canvas can draw Python-computed bob
positions, handle play/pause/reset/scrub locally, and cancel stale playback
when a new run ID arrives.

It does not prove physical correctness, energy behavior, long-duration
stability, accessibility readiness, export support, or final production fit.

## Manual Stale-State Checks

Use the preview to inspect:

- play animation, then run a new request;
- play animation, then switch model type and run;
- play animation, then switch system type and run;
- play animation, then switch preset and run;
- play animation, then clear;
- play animation, then trigger simulated failure;
- rapidly repeat runs;
- scrub while playing;
- reset after scrub;
- play after scrub.
