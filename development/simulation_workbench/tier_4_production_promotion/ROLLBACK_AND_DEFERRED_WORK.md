# Rollback And Deferred Work

Tier: Phase 6 / Simulation Workbench Tier 4

## Rollback Plan

Keep the first Canvas integration reversible.

Recommended safeguards:

- keep the existing Plotly output path available until Canvas passes browser
  smoke checks;
- isolate Canvas payload construction behind a small Python helper API;
- isolate the Canvas renderer in a single Dash-served asset;
- avoid deleting existing graph/output methods during first promotion;
- avoid changing existing callback-sensitive IDs unless all dependencies are
  migrated deliberately;
- preserve workbench reports as implementation references;
- make failure fall back to an explicit message, not a blank workspace.

If Canvas integration has production issues:

- disable or hide Canvas workspace controls;
- keep current Plotly analytical outputs available;
- revert physical motion to the current unique-graph-per-run Plotly animation
  path if needed;
- preserve Tier 3D run-ID and stale-state lessons even if renderer choice is
  rolled back;
- open a follow-up implementation task rather than patching around lifecycle
  failures silently.

## Deferred Work

Deferred scientific and numerical work:

- energy diagnostics;
- energy drift validation;
- tolerance sensitivity;
- long-duration scientific validation;
- solver-method comparison;
- side-by-side runs;
- perturbation controls;
- separation-over-time diagnostics;
- Poincare sections;
- Lyapunov exponents;
- chaos bridge modules.

Deferred interaction and renderer work:

- richer Plotly analytical inspection;
- Canvas accessibility/export strategy;
- keyboard navigation for Canvas inspection;
- tabular alternatives to Canvas charts;
- payload compression or quantization;
- automated browser lifecycle regression tests;
- bob dragging as a primary input mode.

## Comparison / Chaos Bridge Status

The comparison/chaos bridge has moved to a future development branch to be
defined later.

It is not part of the Canvas production promotion and should not block:

- Python payload API implementation;
- Canvas renderer integration;
- Tier 3D lifecycle behavior;
- run summary and numerical diagnostics promotion.

When comparison/chaos work resumes, it should define its own evidence gates for
scientific meaning, not borrow trust from Canvas renderer work.
