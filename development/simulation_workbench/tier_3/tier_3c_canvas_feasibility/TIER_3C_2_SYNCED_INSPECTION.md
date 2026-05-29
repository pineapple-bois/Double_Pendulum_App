# Tier 3C.2 Synced Inspection Polish

Tier: Phase 6 / Simulation Workbench Tier 3C.2
Date: 2026-05-29

## Summary

Tier 3C.2 improves the Canvas preview from motion-only playback to inspectable
motion. It adds a reference frame, optional axes/grid/origin rendering, and
scrub-synced Plotly analytical views.

This remains workbench-only. No production `/simulation` page, callback,
component ID, CSS, model mathematics, solver default, energy diagnostic, chaos
diagnostic, or Poincare section was changed.

## What Was Added

- Canvas display options for axes, grid, and origin marker.
- An explicit pivot/origin marker.
- Equal-aspect physical scaling retained in the Canvas projection.
- Canvas overlay text explaining the rendering transform.
- Angular displacement time-series Plotly view.
- Theta-theta angular state projection Plotly view.
- Shared scrubber-selected frame used by Canvas and both Plotly marker views.
- Selected-time/state readout.

## Coordinate Reference Frame

Python supplies physical bob coordinates:

- `x` increases to the right;
- `y` increases upward;
- the pivot/origin is `(0, 0)`.

Canvas screen coordinates have `y` increasing downward, so JavaScript performs a
rendering transform:

```text
physical x/y from Python -> equal-aspect screen projection -> Canvas draw calls
```

The transform is rendering-only. JavaScript does not compute equations,
integrate trajectories, alter initial conditions, or make physical claims.

The grid and axes are drawn from the payload bounds. They are visual reference
marks around the Python-computed coordinate data, not numerical diagnostics.

## Synced Selected Frame

The Dash scrubber remains the shared selected-frame control.

On scrub:

- Canvas pauses playback and draws the selected frame;
- the time-series view moves its selected-time marker;
- the theta-theta angular state projection moves its selected-state marker;
- the readout updates run ID, frame, selected time, `theta1`, and `theta2`.

The time-series and projection figures are created clientside from the same
payload. Python sends the trusted arrays once; there is no Python callback per
animation frame.

## Sync Status

Works now:

- scrub updates Canvas;
- scrub updates the time-series marker;
- scrub updates the angular state projection marker;
- scrub updates the selected-time/state readout;
- axes/grid/origin toggles redraw the current Canvas frame;
- play, pause, reset, clear, failure, and stale-run cancellation behavior are
  preserved in the Canvas manager.

Deferred:

- live Plotly marker movement during playback.

Playback currently updates Canvas and the Canvas status. It does not drive the
Dash scrubber value or Plotly markers on every animation frame. That is
intentional for this pass: syncing Plotly on every playback frame could
reintroduce callback/render pressure before Tier 3D defines the interaction
contract.

## Payload Change

Tier 3C.2 adds angular samples to the payload:

- `angular_state.theta1_deg`;
- `angular_state.theta2_deg`;
- an explicit label that the theta-theta output is an angular state projection,
  not a full phase portrait.

The Canvas renderer still only needs positions, bounds, sample count, and run
ID to draw. The angular samples support the synced inspection views.

## Updated Metrics

Regenerated compact metrics:

| Case | Samples | Payload bytes | Bytes/sample |
| --- | ---: | ---: | ---: |
| simple Lagrangian nonzero | `640` | `88425` | `138.2` |
| compound Hamiltonian nonzero | `1200` | `164761` | `137.3` |
| simple Lagrangian small angle | `2000` | `274831` | `137.4` |

The payload grew because it now carries angular state samples for synchronized
Plotly inspection. This reinforces the Tier 3C caution: Canvas is a lifecycle
and interaction candidate, not automatically a payload-size win.

## Browser Smoke Result

The preview was started at `http://127.0.0.1:8065/` and checked in browser.

Observed:

- axes/grid control was present;
- grid toggle changed state and redrew the current Canvas frame;
- Run produced a payload and drew frame zero;
- scrub updated Canvas status to the selected frame;
- scrub updated the selected-time/state readout;
- play started playback;
- pause preserved the current frame;
- reset returned to frame zero;
- play followed by Clear produced a cleared state and stopped playback;
- play followed by Simulated Failure produced a failure state and stopped
  playback;
- play followed by a new Run replaced the active run and reset to frame zero.

This is still a smoke check, not a complete browser regression suite.

## Production-Candidate Signal

Canvas is a stronger production candidate after this pass because it now
supports an inspectable reference frame and shared selected-time state. The
combination of Canvas motion plus Plotly analytical markers looks like a viable
hybrid direction:

- Canvas for physical motion and playback lifecycle;
- Plotly for analytical time series and state projections;
- one shared selected frame/time.

This still needs Tier 3D before promotion. The product must decide whether the
future workspace prioritizes autoplay, selected-time inspection, or both.

## Remaining Risks Before Tier 3D

- Browser playback and stale-state behavior still need manual inspection.
- Plotly marker sync during playback is deferred.
- Payload size increased with synced inspection arrays.
- Canvas accessibility/export behavior is still unresolved.
- The coordinate grid is visual context, not numerical validation.
- Future implementation must prevent physics from creeping into JavaScript.

## Recommended Next Task

Proceed to Tier 3D interaction contract.

Tier 3D should decide the accepted lifecycle and sync model for:

- run;
- rerun;
- clear;
- failure;
- input-stale state;
- play;
- pause;
- reset;
- scrub;
- selected time;
- whether Plotly markers should update live during playback or only on scrub.
