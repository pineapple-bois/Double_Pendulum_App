# Phase 8 Callback Routing Stability

This note records the focused Phase 8 investigation into Simulation page
remount behavior after navigating between Dash routes.

## Bug Scenario

Reproduction path under investigation:

1. Open `/simulation`.
2. Run or begin running a simulation.
3. Navigate to `/equations` using the app navigation.
4. Navigate back to `/simulation`.
5. Run the simulation again without a hard browser reload.

Expected behavior: the remounted Simulation page starts from empty memory-scoped
stores, accepts a fresh run, clears loading state, and updates the Canvas
workspace from the new payload.

Reported behavior: after returning to `/simulation`, the simulation no longer
runs correctly until a hard page reload.

## Observed During This Pass

- Browser smoke with app navigation did not reproduce a visible completed-run
  failure in DOM-level controls: after `/simulation -> /equations ->
  /simulation`, a fresh simple Lagrangian run reached success and enabled
  playback controls.
- Code inspection found a concrete renderer lifecycle hazard: the Python/Dash
  Simulation stores are memory scoped inside the routed page and reset on
  remount, but `assets/simulation-canvas-renderer.js` kept route-scoped
  `activeRunId`, `minimumRunId`, active payload, and payload key state alive
  after the Simulation shell was removed.
- That mismatch could cause the renderer to treat the first payload from a
  remounted Simulation page as stale or older than the current client-side run
  request, especially after a run was started before leaving the page.

## Files Inspected

- `pendulum_app.py`
- `app/callbacks/routing.py`
- `app/callbacks/simulation.py`
- `app/pages/registry.py`
- `app/pages/simulation.py`
- `app/pages/equations.py`
- `app/components/simulation_controls.py`
- `app/components/simulation_interaction.py`
- `app/serialization/canvas_payload.py`
- `assets/simulation-canvas-renderer.js`
- `assets/scroll.js`
- `tests/integration/test_simulation_interaction_shell.py`
- `tests/numerical/test_canvas_payload.py`
- `documentation/simulation-canvas/`
- `documentation/phase-8-solver-fidelity-and-contract-record.md`

## Fix Applied

- The Canvas renderer now resets route-scoped state when the Simulation shell is
  removed or replaced:
  - active payload and payload key;
  - active and minimum run IDs;
  - selected frame and playback status;
  - cached metrics and result state.
- The temporary Phase 8 integrator selector is included in the renderer's
  client-side stale-input detection.
- The routing clientside callback now guards optional globals before calling
  scroll or renderer initialization helpers.

## Tests Added

- Repeated route layout generation now covers `/simulation -> /equations ->
  /simulation` and verifies fresh memory-scoped stores and default temporary
  integrator policy on remount.
- Renderer asset coverage now checks for the route-scoped reset function,
  minimum-run-id reset, shell replacement detection, and integrator-policy stale
  tracking.
- Routing callback source coverage now checks that clientside global calls are
  guarded.

## Remaining Risks

- The browser smoke performed here verified DOM-visible status, frame indicator,
  and playback enabled state, but did not provide reliable access to the
  renderer's main-world internal state.
- A dedicated browser-level regression test that can inspect Canvas pixels or
  renderer state across Dash clientside route transitions would provide stronger
  coverage.
- Follow-up closeout smoke verified that navigating away to `/equations` during
  or immediately after a run remounts `/simulation` as empty and allows a fresh
  run without hard reload.
- Loading-state behavior is documented in the manual UX closeout note. Simple
  runs were generally too fast for persistent loading text, but no sticky
  loading state remained after stale, failed, interrupted, or successful runs.

Related durable contract record:
[Phase 8 Solver Fidelity And Contract Record](phase-8-solver-fidelity-and-contract-record.md).

Related closeout record:
[Phase 8 Manual UX And Loading-State Inspection](phase-8-manual-ux-and-loading-state-inspection.md).
