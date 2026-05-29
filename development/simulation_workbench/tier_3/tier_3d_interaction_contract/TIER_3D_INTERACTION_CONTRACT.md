# Tier 3D Interaction Contract

Tier: Phase 6 / Simulation Workbench Tier 3D
Date: 2026-05-29

## Summary

Tier 3D defines the lifecycle contract for the future Simulation workspace. It
does not choose the final renderer, does not modify the production
`/simulation` page, and does not add new simulation outputs.

The contract is built around one rule:

> No visual state may continue animating after its simulation result has been
> superseded.

Tier 3C.2 showed that a Canvas-native manager can render physical motion,
angular displacement, theta-theta projection, and selected-state readout from
one Python-owned payload and one selected-frame state. Tier 3D turns that into
accepted interaction behavior: run identity, stale output, failure, clear,
playback, scrub, and input-change rules.

## Relationship To Tier 3C.2

Accepted from Tier 3C.2 as a leading production candidate:

- Canvas-native physical motion;
- Canvas-native angular displacement time series;
- Canvas-native theta-theta angular state projection;
- one selected-frame state shared by all inspection views;
- one playback loop;
- stale-run cancellation keyed by run identity;
- no Python callback per animation frame;
- no JavaScript physics.

Still unresolved:

- final renderer decision;
- Canvas accessibility and export behavior;
- payload-size strategy;
- automated browser lifecycle tests;
- whether production uses Canvas-only analytical panels, Plotly fallback, or a
  hybrid.

Tier 3E should make the renderer decision. Tier 3D only defines the state
contract that any renderer must satisfy.

## Simulation / Result States

`empty`

- No simulation has been run in this page session.
- No active payload exists.
- Playback state is `idle`.
- The workspace should show a useful empty state rather than a blank panel.

`running`

- A run request has been accepted and a result is being created.
- Previous playback must be cancelled immediately.
- The old payload may remain visible only if clearly marked as superseded or
  pending replacement.
- In the production app this state may be brief, but it should still exist in
  the mental model.

`success`

- A run completed and has an active payload.
- The payload has a unique `run_id`.
- Output is current for the visible controls.
- Playback and inspection controls are available.

`stale`

- Controls changed after the last successful run.
- The old payload may remain visible and inspectable.
- Playback must stop.
- The output must be visually distinguishable from current output with a
  message such as `Settings changed - rerun to update`.
- Pressing Run creates a new `run_id` and replaces the stale payload.

`failed`

- Validation, solver, or output generation failed.
- Playback must be cancelled.
- Previous successful animation must not continue.
- The user-visible message should distinguish validation, solver, and output
  generation failures when production error data is available.

`cleared`

- The user intentionally cleared output.
- Playback must be cancelled.
- No active payload remains.
- This is not an error state.

## Playback / Inspection States

`idle`

- A payload may be available, but playback is not active.
- The selected frame is stable.

`playing`

- Playback loop is advancing selected frame for the active `run_id`.
- The loop must check active run identity before drawing.
- Motion, time-series cursor, projection marker, and readout use the same
  selected frame.

`paused`

- Playback is stopped.
- Selected frame is preserved.

`scrubbing`

- User is directly controlling selected frame.
- Scrubbing pauses playback.
- Scrubbing updates all synchronized inspection views.

`ended`

- Playback reached the final sample.
- Selected frame remains on the last sample.
- Pressing Play may restart from zero or continue from the last sample only if
  the behavior is explicit. Recommended default: Reset returns to zero; Play
  from ended restarts at zero.

`cancelled`

- Playback stopped because the result was superseded, cleared, failed, or made
  stale.
- A cancelled loop must not continue drawing.

## Run ID Contract

- Every successful run gets a unique `run_id`.
- Every new run request invalidates old playback immediately.
- JavaScript playback checks the active `run_id`.
- If the active `run_id` changes, the old animation loop exits.
- Clear and failure states cancel playback and remove or invalidate the active
  payload.
- Stale state preserves the old payload for inspection, but marks it as no
  longer current.
- A stale payload must not animate silently as if it matches the current
  controls.

This contract does not require `run_id` values to be globally unique across
browser sessions. Page-session uniqueness is sufficient for renderer lifecycle
control.

## Stale-State Contract

Chosen behavior:

- stale output remains visible for comparison with the last completed run;
- stale output remains scrub-inspectable;
- animation pauses or cancels when controls change;
- a clear message says the settings changed and a rerun is needed;
- Run creates a new run ID and replaces the stale payload.

Rationale:

- preserving the last result helps users understand what changed;
- pausing prevents stale motion from masquerading as current;
- requiring rerun keeps Python as the only owner of simulation truth.

## Selected-Frame Contract

After a successful run:

- selected frame resets to `0`;
- selected time resets to the first sample;
- playback state is `idle`;
- all inspection views draw frame `0`.

After Reset Playback:

- selected frame becomes `0`;
- selected time becomes the first sample;
- playback stops.

After scrub:

- selected frame becomes the scrubbed frame;
- selected time is derived from the payload time array;
- playback pauses;
- motion, time-series cursor, projection marker, and readout update together.

After playback reaches the end:

- selected frame becomes the final sample;
- playback state becomes `ended`;
- views remain on the final sample until reset, scrub, rerun, clear, or failure.

After new run:

- selected frame resets to `0`;
- selected time resets to the first sample;
- stale playback for the old run is cancelled.

After failure or clear:

- selected frame resets to `0`;
- selected time resets to `0`;
- no active payload is available.

## Failure-State Contract

Validation failure:

- should happen before solver construction;
- should cancel playback;
- should not keep old animation active;
- should show validation guidance.

Solver failure:

- should retain solver metadata when available;
- should cancel playback;
- should show solver status/message;
- should not create a drawable success payload.

Output generation failure:

- should cancel playback;
- should show which output failed where possible;
- should not allow a partial or old animation to keep playing as current.

## Clear / Reset Contract

Clear:

- cancels playback;
- removes active payload;
- sets simulation state to `cleared`;
- resets selected frame/time;
- shows a neutral cleared state.

Reset Playback:

- does not clear output;
- does not create a new run ID;
- stops playback;
- returns selected frame to zero for active or stale inspectable output.

## Input-Change Behavior

Changing model type, system type, preset, initial conditions, duration, sample
count, or solver options after success should:

- mark output stale;
- stop playback;
- keep the last payload visible only with stale styling/message;
- preserve selected frame for inspection unless the user clears or reruns;
- avoid Python calls until Run is clicked.

Changing axes, grid, or other purely visual display options should:

- not mark output stale;
- not create a new run ID;
- not call Python;
- redraw locally.

## Canvas-Native Sync Behavior

Accepted for further production testing:

- one selected-frame state drives motion, time-series cursor, angular projection
  marker, and readout;
- one playback loop advances the selected frame;
- play, pause, reset, scrub, clear, failure, and rerun share one cancellation
  path;
- JavaScript renders already-computed arrays only;
- Python owns equations, integration, state conversion, positions, metadata,
  and warnings.

Not accepted as final production decision:

- Canvas as the only analytical renderer;
- Canvas accessibility/export adequacy;
- payload encoding and compression strategy;
- automated lifecycle coverage.

## Preview

`interaction_contract_preview.py` demonstrates the state contract without
running the solver. It shows:

- simulation/result state;
- playback/inspection state;
- active run ID;
- selected frame/time;
- active/stale/failed/cleared output status;
- input changes marking output stale;
- failures cancelling playback;
- clear cancelling playback.

The preview is intentionally not a renderer experiment. It exists so the
interaction rules can be clicked through before they are implemented in the
production Simulation workspace.

## What Remains Unresolved

- Final renderer decision belongs to Tier 3E.
- Canvas accessibility/export limitations need a concrete plan.
- Payload-size strategy needs design work.
- Automated browser tests for stale playback are still missing.
- Production implementation must decide how to show running state during real
  solver work.
- Production implementation must integrate validation and solver metadata
  without changing the trusted numerical contract.

## Recommendation For Tier 3E

Proceed to Tier 3E renderer decision only after this interaction contract is
accepted.

Tier 3E should compare:

- Canvas-native motion plus Canvas-native synced inspection;
- Canvas motion plus Plotly analytical fallback;
- Plotly-only analytical views with Canvas only for motion;
- production risk, accessibility, export, payload, maintainability, and test
  strategy for each.
