# Tier 4 Promotion Cleanup

Tier: Phase 6 / Simulation Workbench Tier 4
Date: 2026-05-29

## Summary

Integration D promotes the accepted Canvas path to the normal production
Simulation output.

Current production result:

- `/simulation` renders the Canvas-powered Simulation output as the primary
  output surface.
- Successful runs build and store the Task A Canvas payload, result state,
  playback state, run summary, and solver diagnostics.
- Legacy Plotly graph sections are no longer rendered on the normal Simulation
  page and Plotly figures are no longer generated in the normal run callback.
- Plotly graph helper functions and model plotting methods remain in the
  codebase as dormant rollback/future analytical-inspection helpers rather
  than being purged during this cleanup.
- The Canvas renderer remains isolated in `assets/simulation-canvas-renderer.js`
  and the Python payload API remains isolated under `app/serialization/`.

The following historical handoff text records the promotion path that led to
that result.

The Simulation Workbench now has a clear production handoff.

Canvas is the preferred candidate for physical motion and synced selected-time
inspection, but production implementation should happen in two steps:

1. Production Task A: implement and test the Python Canvas payload API.
2. Production Task B: wire the Canvas renderer into `/simulation` using the
   tested payload API.

## User Problem Solved By The Accepted Path

The current Simulation workspace needs motion and inspection outputs that stay
tied to the correct simulation result.

The accepted path solves:

- stale animation risk;
- unclear post-run workspace behavior;
- lack of shared selected-time inspection;
- fragile renderer lifecycle;
- insufficient separation between mathematical truth and browser rendering.

## Ready For Production Promotion

Ready to promote through scoped tasks:

- Canvas as preferred physical motion renderer candidate;
- Canvas-native synced selected-time inspection candidate;
- run summary and numerical diagnostics using retained solver metadata;
- empty, success, stale, failed, and cleared state concepts;
- Tier 3D event matrix as lifecycle authority.

## Not Ready

Not ready for production claims:

- energy diagnostics;
- energy drift validation;
- chaos diagnostics;
- solver-method equivalence;
- tolerance sensitivity;
- long-duration scientific validity;
- Canvas accessibility/export completeness;
- full replacement of Plotly analytical inspection.

## API Tightening Required

Before integration:

- units must be explicit;
- internal numerical units and display units must be distinct;
- Hamiltonian canonical momenta must not be mislabeled as angular velocities;
- failed, cleared, and empty payloads must not contain drawable success arrays;
- payload storage should be memory-scoped;
- payload size must be measurable;
- timings must be interpreted cautiously.

## Task A Should Implement

Production Task A should implement:

- `build_canvas_motion_payload(...)`;
- `validate_canvas_motion_payload(...)`;
- `estimate_canvas_payload_size(...)`;
- `summarise_canvas_payload(...)`;
- tests for schema, units, array lengths, finite arrays, solver metadata,
  Hamiltonian nonzero velocity behavior, status rules, and payload size.

Task A should not change the live UI.

## Task B Should Implement

Production Task B should implement:

- Canvas workspace layout;
- memory-scoped Canvas payload store;
- result state store;
- production JavaScript renderer asset;
- play, pause, reset, scrub controls;
- axes/grid toggles if accepted;
- stale/failure/empty state styling;
- clientside lifecycle behavior following Tier 3D.

Task B should preserve existing Plotly outputs until Canvas passes promotion
gates.

## Likely Production Files

Likely files to inspect/change during Task B:

- `app/pages/simulation.py`;
- `app/callbacks/simulation.py`;
- `app/components/graphs.py`;
- `app/components/footer.py`;
- `app/components/simulation_controls.py`;
- `app/content/simulation.py`;
- `assets/styles.css`;
- new asset such as `assets/simulation-canvas-renderer.js`;
- payload helper module from Task A;
- tests under `tests/unit/`, `tests/numerical/`, and `tests/integration/`.

## Workbench-Only Code

Workbench-only code should remain under:

- `development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/`;
- `development/simulation_workbench/tier_3/tier_3d_interaction_contract/`;
- `development/simulation_workbench/tier_3/tier_3e_renderer_decision/`;
- `development/simulation_workbench/tier_4_production_promotion/`.

Production code should not import workbench modules.

## Required Tests And Checks

Task A:

- Python payload tests.

Task B:

- browser smoke checks for run, play, pause, reset, scrub, stale, clear,
  failure, rapid reruns, resize, and longer-duration payloads;
- targeted model/metadata/convention tests;
- app route/content smoke checks if layout changes.

## Trusted Numerical Assumptions

Trusted for promotion planning:

- representative simple/compound and Lagrangian/Hamiltonian runs are array-sane
  under Tier 1 and Tier 3E checks;
- solver metadata is retained;
- Hamiltonian user-facing angular velocities are converted to canonical
  momenta before solving;
- positions can be precomputed for Canvas payloads.

Not trusted:

- energy behavior;
- chaos metrics;
- long-duration scientific validity;
- physical correctness beyond current evidence.

## If The Promoted Path Fails

If Canvas integration fails promotion gates:

- keep or restore existing Plotly output path;
- do not delete workbench evidence;
- preserve the payload API if useful and tested;
- defer renderer promotion;
- write a focused follow-up task rather than merging a partial lifecycle fix.

## Final Handoff

The next implementation task should be Production Task A.

Do not start Canvas integration until the payload API and tests are accepted.
