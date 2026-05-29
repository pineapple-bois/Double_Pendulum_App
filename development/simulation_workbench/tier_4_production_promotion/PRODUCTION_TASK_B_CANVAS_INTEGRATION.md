# Production Task B: Canvas Integration Into `/simulation`

Tier: Phase 6 / Simulation Workbench Tier 4
Task type: production implementation plan

## Goal

Wire the accepted Canvas renderer into the production `/simulation` workflow
using the tested payload API from Production Task A.

Task B must preserve the Tier 3D event matrix:

> No visual state may continue animating after its simulation result has been
> superseded.

## Prerequisite

Task A must be accepted first. Do not start Task B until the Python payload API
and tests exist.

## Production Architecture

Python / Dash side:

- run simulation from existing controls;
- create Canvas payload through the tested helper;
- include solver metadata and warnings;
- store payload in memory-scoped `dcc.Store` or equivalent;
- emit result state: `empty`, `running`, `success`, `stale`, `failed`,
  `cleared`;
- avoid Python callbacks per animation frame.

JavaScript side:

- load latest payload;
- manage active run ID;
- manage selected frame;
- draw Canvas motion;
- draw Canvas angular time series;
- draw Canvas angular projection;
- draw selected-time/state readout;
- handle play/pause/reset/scrub locally;
- cancel stale playback on new run ID, clear, failure, or stale state;
- never compute physics, integration, energy, chaos metrics, or Hamiltonian
  state conversion.

CSS / layout side:

- Canvas workspace panels;
- playback controls;
- scrubber;
- axes/grid/trail toggles if accepted;
- empty/stale/failed/current state styling.

## Files Likely To Change

Inspect before editing:

- `app/pages/simulation.py` - production Simulation layout.
- `app/callbacks/simulation.py` - current run callback and output flow.
- `app/components/graphs.py` - current output graph helpers.
- `app/components/footer.py` - current Run Simulation footer behavior.
- `app/components/simulation_controls.py` - current control helpers.
- `app/content/simulation.py` - labels/copy if new status text is needed.
- `assets/styles.css` - production workspace and state styling.
- new asset such as `assets/simulation-canvas-renderer.js`.
- payload helper module from Task A.
- tests under `tests/unit/`, `tests/numerical/`, and `tests/integration/`.

Do not change callback-sensitive IDs unless the production task explicitly
updates every dependent callback and layout reference.

## Likely New Component IDs

Exact names may change during implementation, but expect IDs for:

- Canvas workspace container;
- motion Canvas;
- time-series Canvas;
- projection Canvas;
- Canvas payload store;
- result state store;
- play button;
- pause button;
- reset button;
- scrubber;
- axes toggle;
- grid toggle;
- optional trail toggle;
- stale/failure/current message area;
- selected-time/state readout;
- run summary area;
- numerical diagnostics area.

## Browser Behavior To Preserve

Task B must verify:

- new run cancels old playback;
- clear cancels playback;
- failure cancels playback;
- stale input changes cancel playback;
- stale output is visibly stale;
- stale output does not silently animate as current;
- scrub updates motion, time-series cursor/markers, projection marker, and
  readout;
- reset returns selected frame to zero;
- axes/grid toggles redraw locally without Python;
- no visual state continues after its run is superseded.

## Suggested Implementation Order

1. Add layout containers and stores behind the existing Simulation page flow.
2. Add production Canvas renderer asset with the API from Tier 3E.
3. Add clientside callback or initialization path for renderer events.
4. Update the existing simulation callback to produce payload/result state using
   Task A helper.
5. Preserve existing Plotly outputs during the first integration pass.
6. Add stale-state detection when controls change after success.
7. Add failure/clear state handling.
8. Run the production test plan and browser smoke checks.

## Acceptance Criteria

Task B is accepted only when:

- tested payload API is used;
- Canvas renderer loads success payloads;
- play/pause/reset/scrub work locally;
- stale, clear, failure, and rerun behavior follows the Tier 3D event matrix;
- existing callback-sensitive IDs are preserved or migrated deliberately;
- no JavaScript physics is introduced;
- existing Plotly fallback remains available during the promotion window;
- browser smoke checks pass for short and longer-duration cases.
