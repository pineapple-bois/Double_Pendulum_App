# Canvas Production Promotion Plan

Tier: Phase 6 / Simulation Workbench Tier 3E
Date: 2026-05-29

This plan scopes the next production task. It does not implement Canvas in the
production `/simulation` page.

## Proposed Production Architecture

Python / Dash:

- receive and validate the simulation request;
- construct or consume the future simulation result object;
- build a Canvas motion/inspection payload;
- store payload in `dcc.Store`;
- emit result state: `empty`, `running`, `success`, `stale`, `failed`, or
  `cleared`;
- update run summary and numerical diagnostics;
- preserve solver metadata and warnings.

JavaScript:

- expose a Canvas renderer asset;
- load payloads by run ID;
- draw physical motion;
- draw angular displacement time-series cursor/markers;
- draw theta-theta angular state projection marker;
- manage play, pause, reset, scrub, clear, and failure states;
- cancel stale playback on run ID change;
- avoid Python callbacks per animation frame;
- never compute physics.

CSS / Layout:

- provide a Simulation workspace container;
- provide Canvas panels for motion and inspection;
- provide play/pause/reset/scrub controls;
- provide axes/grid/trail toggles where accepted;
- provide stale, failure, cleared, running, and empty state styling.

## Likely Production Files To Inspect Or Change

Do not change these until the production promotion task is explicitly started.

Likely layout files:

- `app/pages/simulation.py`;
- `app/components/graphs.py`;
- `app/components/footer.py`;
- any shared control/component helper under `app/components/`.

Likely callback files:

- `app/callbacks/simulation.py`;
- possibly app-shell callback registration in `pendulum_app.py` only if new
  clientside callbacks require registration changes.

Likely JavaScript / assets:

- new production renderer asset under `assets/`, for example
  `assets/simulation-canvas-renderer.js`;
- existing assets should be inspected for naming and lifecycle patterns.

Likely CSS:

- `assets/styles.css`.

Likely model/payload helpers:

- app-layer serialization helper, for example `app/serialization/`;
- model-independent numerical helpers under `src/double_pendulum/` only if
  payload construction needs reusable non-Dash logic.

Likely tests:

- `tests/numerical/`;
- `tests/unit/`;
- `tests/integration/`;
- any future browser/manual smoke checklist for `/simulation`.

## Implementation Steps

1. Add a production payload helper.
2. Add tests for payload schema, shape, finite values, solver metadata, and
   Hamiltonian nonzero velocity behavior.
3. Add the production Canvas renderer asset behind isolated IDs or a feature
   switch.
4. Add a `dcc.Store` for Canvas payload and explicit result state.
5. Add clientside lifecycle callbacks for play, pause, reset, scrub, clear,
   stale state, and failure state.
6. Keep existing Plotly outputs available until Canvas behavior is accepted.
7. Run browser smoke checks against short and long payloads.
8. Only then decide whether to make Canvas the default physical motion view.

## Python Test Plan

Required tests:

- payload schema includes required fields;
- `time`, `theta1`, `theta2`, `x1`, `y1`, `x2`, `y2` lengths equal
  `sample_count`;
- payload arrays are finite for representative cases;
- payload includes solver metadata;
- payload includes user-facing initial conditions;
- payload includes internal initial state summary;
- Hamiltonian nonzero velocity payload records canonical-momentum internal
  convention and does not serialize momentum slots as angular velocities;
- large duration/sample-count payload summary remains compact enough for
  accepted limits;
- failure payloads do not expose drawable success arrays;
- clear payloads remove active drawable arrays.

Recommended representative Python cases:

- simple Lagrangian baseline;
- simple Hamiltonian nonzero velocity;
- compound Lagrangian larger angles;
- compound Hamiltonian larger velocity;
- 20-second / 4000-sample case.

## JavaScript / Browser Test Plan

Required manual or automated checks:

- initial empty state;
- successful run loads payload and draws frame zero;
- play;
- pause;
- reset;
- scrub;
- axes toggle;
- grid toggle;
- optional trail toggle if included;
- input change after success marks output stale and cancels playback;
- run after stale output creates a new run ID;
- clear cancels playback and clears payload;
- validation failure cancels playback;
- solver failure cancels playback;
- output-generation failure cancels playback;
- rapid repeated runs;
- browser resize;
- 20-second / 4000-sample payload;
- clear after large payload;
- failure after large payload;
- no old visual state continues animating after supersession.

Browser checks should explicitly verify the Tier 3D event matrix.

## Rollback / Fallback Plan

Keep the integration reversible:

- isolate Canvas payload construction behind a small helper API;
- isolate JavaScript renderer behind a single asset and stable function names;
- keep existing Plotly graph outputs available during the promotion window;
- consider a feature flag or workbench-only toggle before making Canvas default;
- do not remove current Plotly animation path until Canvas passes promotion
  gates;
- make failure fall back to a clear message rather than a blank workspace.

If Canvas integration fails:

- leave Plotly analytical outputs active;
- revert the Canvas workspace region to the current unique-graph-per-run Plotly
  animation path;
- preserve the Tier 3D stale-state and run-ID lessons even if renderer choice
  changes.

## Promotion Gates

Canvas production integration is accepted only when:

- payload API is implemented and tested;
- JavaScript renderer API is implemented and tested;
- Tier 3D event matrix behavior is verified;
- stress cases pass or limitations are documented;
- no stale playback is observed;
- clear/failure states cancel playback;
- input changes mark output stale;
- selected frame drives all synced views;
- JavaScript contains no physics, integration, or Hamiltonian conversion;
- payload size is monitored and reported;
- no energy or chaos claims are introduced;
- browser smoke checks pass for short and long cases;
- rollback path remains available.

## Explicit Non-Goals

Do not include in the Canvas promotion task:

- energy diagnostics;
- chaos diagnostics;
- Poincare sections;
- nearby-initial-condition comparison;
- bob dragging as a primary input mode;
- production redesign beyond the scoped motion/inspection workspace;
- final removal of Plotly analytical outputs.
