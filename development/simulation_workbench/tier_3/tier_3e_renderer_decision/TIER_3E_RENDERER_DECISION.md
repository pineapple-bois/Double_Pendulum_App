# Tier 3E Renderer Decision

Tier: Phase 6 / Simulation Workbench Tier 3E
Date: 2026-05-29

## Summary

Canvas should become the preferred production candidate for physical motion and
synced selected-time inspection in the future Simulation workspace.

This is a promotion-preparation decision, not a production implementation.
Canvas should not be wired into `/simulation` until the payload API, renderer
API, event matrix behavior, and promotion gates are implemented and tested.

## Recommendation

Recommended direction:

- Use Canvas for physical pendulum motion.
- Use Canvas for synchronized selected-time inspection where Tier 3C.2 already
  proved the model: motion, angular displacement cursor, theta-theta marker,
  and readout share one selected frame.
- Keep Plotly available for richer analytical views, fallback inspection,
  hover/zoom/export, and accessibility-sensitive use cases.
- Do not promote reduced-frame Plotly animation as the main motion UX.
- Preserve the Tier 3D run ID, stale-state, failure, clear, and selected-frame
  contract.

## Why Canvas Is Preferred

Canvas is preferred because it gives direct lifecycle control:

- one active run identity;
- one selected-frame state;
- one playback loop;
- immediate cancellation on run replacement, clear, failure, or stale state;
- local play, pause, reset, and scrub;
- no Python callback per animation frame;
- no Plotly queued-frame playback to fight.

Tier 3C.2 showed Canvas can render:

- physical motion;
- angular displacement time series;
- theta-theta angular state projection;
- selected-time/state readout.

Tier 3D then defined the state contract those views must obey.

## What Plotly Still Does Better

Plotly remains useful for:

- hover inspection;
- zoom and pan;
- export;
- accessibility-adjacent affordances;
- familiar analytical chart behavior;
- future deeper analysis views.

Canvas-native charts are inspectable, but they do not yet replace Plotly for
rich analytical workflows.

## Why Reduced-Frame Plotly Is Not Preferred

Tier 3B showed reduced-frame Plotly animation mostly solves the wrong problem:

- it reduces frame count by degrading motion fidelity;
- JSON savings were modest compared with the UX compromise;
- it does not provide the same explicit lifecycle control as the Canvas manager.

Reduced frames should not become the main product direction.

## Stress Evidence

Tier 3E stress checks covered:

- baseline angles;
- nonzero angular velocities;
- larger angles;
- larger angles with velocity;
- simple Lagrangian;
- simple Hamiltonian;
- compound Lagrangian;
- compound Hamiltonian;
- `5s`, `10s`, and `20s` durations;
- up to `4000` samples.

All six stress cases completed with:

- solver success;
- finite state arrays;
- finite position arrays;
- monotonic time arrays;
- requested end time matched;
- requested time count returned.

Largest measured payload:

- `690847` bytes;
- `4000` samples;
- simple Lagrangian 20-second larger-angle/nonzero-velocity case.

Interpretation:

- payload size is manageable enough to continue, but large enough to require
  monitoring;
- Canvas is not automatically a payload-size win;
- Canvas is primarily a lifecycle and interaction-quality win.

## Canvas Risks That Remain

- Payload size remains a real concern, especially if production adds more
  arrays or diagnostics.
- Canvas accessibility and export behavior are unresolved.
- Canvas-native charts lack Plotly hover, zoom, and built-in export.
- Browser memory behavior across long sessions is not yet proven.
- Automated lifecycle regression tests are missing.
- Future maintainers must keep physics and state conversion out of JavaScript.

## What Remains Untested

Tier 3E did not test:

- production `/simulation` integration;
- production callback latency;
- browser memory over long repeated sessions;
- 4000-sample clear/failure behavior in the browser;
- resize behavior with 4000-sample payloads;
- accessibility alternatives for Canvas charts;
- energy conservation;
- chaos diagnostics;
- Poincare sections;
- nearby-initial-condition divergence.

## Production Readiness

Canvas is ready for a scoped production promotion task.

It is not yet accepted as production complete.

The next task should implement the API and lifecycle contract behind a contained
production surface, verify the promotion gates, and keep rollback/fallback
available.

## Decision

Decision: **promote Canvas to the preferred production candidate for physical
motion and synced selected-time inspection.**

Do not promote:

- reduced-frame Plotly animation as the main UX;
- Canvas as a replacement for every analytical plot;
- any energy or chaos diagnostic claims.

Keep:

- Plotly as fallback or richer analytical inspection path;
- existing production outputs available until Canvas integration is accepted;
- Tier 3D event matrix as the lifecycle authority.
