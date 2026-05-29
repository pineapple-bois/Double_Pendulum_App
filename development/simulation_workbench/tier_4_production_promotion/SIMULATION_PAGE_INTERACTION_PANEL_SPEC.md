# Simulation Page Interaction Panel Spec

Tier: Phase 6 / Simulation Workbench Tier 4
Task type: production planning spec for Task B
Date: 2026-05-29

This spec defines the planned production `/simulation` interaction-panel
contract for the next implementation task. It does not implement UI, Canvas,
callbacks, CSS, or renderer assets.

Authoritative inputs:

- `development/simulation_workbench/tier_3/tier_3d_interaction_contract/EVENT_MATRIX.md`
- `development/simulation_workbench/tier_4_production_promotion/ACCEPTED_DECISIONS.md`
- `development/simulation_workbench/tier_4_production_promotion/API_TIGHTENING_REQUIREMENTS.md`
- `development/simulation_workbench/tier_4_production_promotion/PRODUCTION_TASK_A_PAYLOAD_API.md`
- `development/simulation_workbench/tier_4_production_promotion/PRODUCTION_TASK_B_CANVAS_INTEGRATION.md`
- current production files inspected for this spec:
  - `app/pages/simulation.py`
  - `app/callbacks/simulation.py`
  - `app/components/simulation_controls.py`
  - `app/components/graphs.py`
  - `app/components/footer.py`
  - `app/content/simulation.py`

## Purpose

Task B should convert `/simulation` from a hidden-Plotly-output page into a
workspace with explicit result lifecycle, Canvas inspection, playback, and
diagnostics. The production rule is:

> No visual state may continue animating after its simulation result has been
> superseded.

Python remains the owner of mathematical and numerical truth. JavaScript owns
rendering, playback, selected-frame inspection, and display-only options.

## Planned Production Regions

### Control Rail

The existing left-side control rail remains the source of simulation request
inputs:

- model type
- system type
- gravity
- active masses and lengths
- initial angles and user-facing initial angular velocities
- simulation start and stop times
- unity-parameter helper
- information popup

The next task should preserve existing callback-bound control IDs. Display-only
Canvas options must not be mixed into the physics input group if doing so makes
stale-state detection harder.

### Run Action Area

The production page needs a clear run action area with:

- primary Run Simulation action
- optional Clear Output action
- current result-state label
- disabled/running affordance during a run if practical

The current Run Simulation button is footer-owned with `id="submit-val"`.
Task B should keep that ID or intentionally migrate every dependent callback.
The safest first integration is to keep `submit-val` as the run trigger while
adding a visible in-workspace run action area only if the callback contract is
migrated deliberately.

### Canvas Inspection Workspace

Canvas should eventually own the primary post-run physical and inspection
workspace:

- physical motion Canvas
- angular displacement time-series Canvas
- theta-theta angular state projection Canvas
- selected-time/state readout

All Canvas views must read one Python-built payload and one shared selected
frame. JavaScript must not compute physics, integrate trajectories, infer
Hamiltonian angular velocities, transform state conventions, compute energy, or
add chaos/comparison behavior.

### Run Summary / Status Area

The run summary should be compact and visible after success or stale success:

- result state: empty, running, success, stale, failed, or cleared
- run ID or page-session epoch
- model type and system type
- sample count and duration
- initial-condition summary with explicit user-facing units
- stale/current message

Stale output may remain inspectable, but the summary must visibly distinguish
it from current success.

### Solver / Numerical-Status Diagnostics Area

Diagnostics should surface only the accepted solver and array sanity metadata:

- solver integrator
- solver success/status/message
- requested and returned sample counts
- returned-time match flag
- solution shape
- finite/time/shape checks from the payload validation path where useful

Do not add energy diagnostics, energy drift claims, chaos diagnostics,
solver-method equivalence claims, tolerance sensitivity claims, or long-duration
scientific-validity claims.

### Playback Controls

Expected controls:

- Play
- Pause
- Reset

Playback controls operate locally in JavaScript. They must never call Python per
animation frame. Play is allowed only for a current `success` payload. Stale
payloads may be scrub-inspectable, but must not autoplay as current output.

### Scrubber

The scrubber chooses a frame or time from the active payload:

- scrubbing pauses playback
- selected frame is clamped to payload bounds
- motion, time-series cursor, projection marker, and readout update together
- scrubbing failed, cleared, or empty states should show a no-payload message

### Axes / Grid Toggles

Axes and grid are display-only options:

- toggles must not mark output stale
- toggles must not call Python
- toggles redraw the current selected frame locally
- toggles are allowed for both success and stale inspectable payloads

Trail can remain deferred unless Task B explicitly accepts it.

### Empty, Stale, Failed, And Cleared Messages

Messages should be explicit:

- `empty`: no run yet; explain that the workspace will show motion, inspection,
  run summary, and diagnostics after a run.
- `stale`: settings changed; rerun to update; output remains inspectable but
  playback is cancelled.
- `failed`: validation, solver, or output generation failed; no drawable
  success arrays may be active.
- `cleared`: output cleared; no active payload remains.

## Lifecycle Behavior

### First Page Load

State: `empty` / `idle`.

- no active payload
- no playback loop
- selected frame defaults to `0`
- useful empty message appears
- existing Plotly containers may remain hidden as fallback

### Run From Empty

State: `empty` / `idle` -> `running` -> `success` / `idle`.

- allocate a new run ID
- build a Python payload with status `success`
- selected frame resets to `0`
- draw the first frame
- show run summary and solver diagnostics

### Successful Run

State: `running` -> `success` / `idle`.

- latest run ID becomes active
- old playback loops are cancelled
- Canvas payload is current
- Play, Reset, Scrub, axes, and grid controls become available
- Plotly fallback may remain available but must not be the lifecycle authority

### Run While Playing

State: `success` / `playing` -> `running` -> `success` / `idle`.

- cancel the old animation loop immediately
- allocate a new run ID
- ignore older completions if a newer run has become active
- selected frame resets to `0` for the winning payload

### Input Changes After Success

State: `success` -> `stale` / `cancelled`.

- cancel playback immediately
- preserve the last payload for visibly stale inspection
- do not call Python solely because a physics input changed
- do not clear to a blank current-looking output
- Run Simulation creates a new run ID and replaces the stale payload

### Stale Output

State: `stale` / `idle`, `paused`, or `scrubbing`.

- stale payload may remain drawn and scrub-inspectable
- Play must not start current-output playback
- summary/status area must say rerun is required
- payload status must be `stale`, not `success`

### Rerun From Stale

State: `stale` -> `running` -> `success` / `idle`.

- stale run ID is superseded
- new run ID is allocated
- stale playback cannot resume
- new payload replaces stale payload on success

### Clear

State: any -> `cleared` / `cancelled`.

- cancel playback immediately
- remove or invalidate active drawable payload
- selected frame resets to `0`
- show neutral cleared message
- no Python solver call is required

### Validation Failure

State: any -> `failed` / `cancelled`.

- validation runs before model construction
- playback cancels
- no drawable success arrays remain active
- show validation guidance in the status/error area
- old success animation must not keep playing

### Solver Failure

State: `running` -> `failed` / `cancelled`.

- failure epoch invalidates previous playback
- retain compact solver metadata when available
- no drawable success arrays are emitted
- show solver status/message

### Play

Allowed only from current `success` payload states.

- starts exactly one local loop
- loop is bound to active run ID
- each draw checks that the active run ID still matches
- from `ended`, recommended behavior is restart from frame `0`

### Pause

- cancels the local playback loop
- preserves selected frame
- does not mutate payload or call Python

### Reset

- cancels playback
- sets selected frame to `0`
- redraws all Canvas views from the same selected-frame state
- does not clear output or allocate a new run ID

### Scrub

- pauses playback
- updates selected frame/time
- redraws motion, time-series cursor, projection marker, and readout together
- does not call Python

### Axes / Grid Toggle

- redraws locally
- does not change result state
- does not mark output stale
- does not call Python

### Rapid Rerun

- every run request gets a unique epoch/run ID
- old loops cancel immediately
- latest completed request wins
- older success or failure completions must not overwrite the newer active run
- final state is latest `success` or latest `failed`

## Callback-Sensitive IDs To Preserve

Preserve these unless Task B explicitly migrates every layout and callback
reference together:

- run/action: `submit-val`
- output containers: `animation-phase-container`, `time-graph-container`,
  `time-graph-section`, `error-message`
- current graph targets: `pendulum-animation`, `phase-graph`, `time-graph`
- loading wrapper: `loading-animation-phase`
- route anchor: `scroll-target`
- controls: `model-type`, `system-type`, `param_g`, `param_l1`, `param_l2`,
  `param_m1`, `param_m2`, `param_M1`, `param_M2`, `init_cond_theta1`,
  `init_cond_theta2`, `init_cond_omega1`, `init_cond_omega2`, `time_start`,
  `time_end`, `unity-parameters`, `info-popup`, `info-button`,
  `close-info-button`

Future Canvas IDs can be added alongside these, such as:

- memory-scoped Canvas payload store
- result-state store
- Canvas workspace container
- motion Canvas
- time-series Canvas
- projection Canvas
- selected-state readout
- run summary area
- solver diagnostics area
- play, pause, reset buttons
- scrubber
- axes and grid toggles
- stale/failure/current message area

## Plotly Fallback Targets

These old Plotly output targets may remain during the first Canvas integration:

- `pendulum-animation`
- `phase-graph`
- `time-graph`
- `animation-phase-container`
- `time-graph-container`
- `time-graph-section`

They should not be removed in Task B. Plotly can remain as fallback or
analytical inspection while Canvas takes over physical motion and synchronized
selected-frame inspection. If both are visible, labels must avoid calling the
theta-theta projection a full phase portrait.

## Footer Run Simulation Button

The current production run button lives in `app/components/footer.py` inside
the simulation footer and uses `id="submit-val"`.

For Task B:

- keep `submit-val` as the run trigger unless intentionally migrating the
  callback contract;
- if adding an in-workspace run action area, either reuse the existing button
  ID in one location or migrate the callback to the new ID in the same change;
- do not leave two independent Run buttons that can race without a shared run
  epoch;
- preserve the footer path until the new interaction panel is verified.

## What Should Not Be Touched Yet

Task B should not:

- change model mathematics
- change solver defaults
- add energy diagnostics
- add chaos diagnostics
- add comparison-run features
- infer Hamiltonian angular velocities in JavaScript
- serialize Hamiltonian canonical momenta as `omega1` or `omega2`
- remove existing Plotly outputs during the first integration pass
- redesign unrelated pages
- change callback-sensitive IDs without a deliberate migration
- persist full Canvas payload arrays to local storage, session storage, URL
  state, logs, exported JSON, screenshots, notebooks, or HTML artifacts

## Task B Readiness Checklist

Before implementation starts:

- use the accepted Task A payload helper
- use memory-scoped payload storage
- keep result state separate from playback state
- cancel playback on run, stale, failure, and clear transitions
- keep display-only toggles local
- preserve the fallback path until browser lifecycle checks pass
