# Double Pendulum App Roadmap

This is the active project-control document for the Double Pendulum App. It is
not an implementation diary, callback reference, renderer API, or workbench
evidence archive.

Use this roadmap to answer:

- what baseline the project is currently building from;
- what phase is active;
- what is gated or blocked;
- what comes next;
- what is deferred;
- where implementation details live.

Last restructured: 2026-05-31.

## 1. Project Baseline

The app is stable enough to build from, but not polished enough to treat as a
finished production baseline.

Current baseline:

- The app is a Dash application with a Flask `server` object for
  Gunicorn/Heroku-style deployment.
- Public teaching routes remain centered on Home, Equations of Motion,
  Simulation, and Chaos, with legacy `/lagrangian` and `/hamiltonian` routes
  preserved.
- The `/simulation` page now uses the accepted Canvas-backed architecture.
- Python owns mathematical and numerical truth.
- Dash callbacks and memory-scoped stores manage app state and payload
  delivery.
- Browser-side JavaScript/Canvas handles rendering, playback, resizing, and
  selected-frame inspection state only.
- JavaScript must not integrate trajectories, compute physics, infer
  Hamiltonian angular velocities, or transform solver state conventions.
- Production code must not import from `development/`.
- Detailed Simulation Canvas implementation contracts live in
  `documentation/simulation-canvas/`.

Current known limits:

- The Canvas-backed Simulation runtime has a stronger numerical and callback
  baseline, but the app still needs styling, production layout, and UX
  consolidation.
- Existing tests are useful but not a complete scientific validation suite.
- Energy diagnostics, chaos diagnostics, tolerance sensitivity, solver-method
  equivalence, and long-duration scientific validity are not proven.

## 2. Completed Phase: Phase 8

**Phase 8: Numerical baseline, callback hardening, bug eradication, and
documentation control**

Phase 8 is complete at roadmap level. It established the runtime baseline
needed before styling and layout consolidation.

Completed:

- Simple-model mathematical fidelity evidence has been promoted into focused
  production tests.
- The simple-model numerical fidelity baseline is established.
- Solver-policy evidence supports `dop853_moderate`
  (`method="DOP853"`, `rtol=1e-6`, `atol=1e-8`) as the leading simple-model
  default candidate.
- `dop853_strict` remains the high-fidelity/reference candidate.
- Production solver-policy scaffolding and tests exist for simple-model runs.
- Solver failures are represented as first-class non-render-safe states.
- Canvas/backend payload tests verify that failures do not leave current
  drawable success arrays behind.
- The route-remount lifecycle bug was fixed with Canvas renderer route-state
  reset and guarded routing reinitialization.
- Manual simple-model UX performance inspection is complete for DOP853 moderate
  and DOP853 strict across representative systems, durations, and inputs.
- The stale diagnostics metadata issue has been triaged and fixed: stale
  diagnostics now identify previous-run metadata until rerun.
- A temporary Simulation integrator-policy selector exists for Phase 8 manual
  inspection and is explicitly deferred to Phase 9 removal or hiding.
- Compound-model runs showed no noticeable issue during inspection, so no
  compound-specific action was taken. If a compound issue appears later, handle
  it as a focused evidence/fidelity pass.
- Durable runtime stability documentation lives under
  `documentation/simulation-runtime/`.

Residual risks accepted or deferred:

- Browser-level coverage does not directly inspect Canvas pixels or renderer
  internals across route transitions.
- The temporary integrator-policy selector remains visible until Phase 9
  removes or hides it.

## 3. Active Phase: Phase 9

**Phase 9: Styling, production layout, and UX rules**

Phase 9 is the active phase.

Phase 9 is styling, production layout, and UX consolidation. It should improve
how the app presents the accepted runtime contract without weakening solver,
result-state, or Canvas payload protections.

Scope:

- Define production layout rules.
- Remove or hide Phase 8 diagnostic controls such as the temporary
  integrator-policy selector.
- Consolidate the Simulation page layout.
- Stabilize header, footer, sidebar, run action, output workspace, diagnostics
  placement, and responsive behavior.
- Improve user-facing diagnostics/presentation without weakening the
  solver/result contract.
- Consolidate styling through `assets/styles.css`.
- Remove or rationalize ad hoc styling.
- Define rules for future UI changes.
- Add Initial State help/preset UX only after layout stability is achieved.
- Use browser smoke checks for UI-facing changes, with strict Dash server
  cleanup.

Gates and non-goals:

- New simulation outputs.
- New chaos diagnostics.
- New comparison workspace.
- Additional analytical Plotly output suites.
- New chaos/comparison/product work unless explicitly approved.
- Broad visual redesigns unrelated to production layout consolidation.
- Reopening numerical/callback foundations unless a regression appears.
- Weakening solver/result contract protections.
- Reintroducing broad workbench experimentation.

## 4. Future Phase: Phase 10

**Phase 10: New work, to be defined**

Phase 10 is intentionally undefined for now.

It represents new product work after Phase 9 establishes styling/UX stability.
Phase 10 should be scoped only after that baseline exists.

Possible future directions are listed as deferred candidates, not commitments.

## 5. Deferred Work

Deferred until after Phase 9:

- new chaos diagnostics;
- new comparison workspace;
- additional analytical Plotly output suite;
- new simulation-output galleries;
- major numerical-method changes;
- broad workbench experimentation;
- large visual redesigns unrelated to production layout;
- Phase 10 product direction.

Deferred scientific validation topics:

- energy diagnostics and drift thresholds;
- chaos metrics;
- tolerance sensitivity;
- solver-method equivalence;
- long-duration scientific validity;
- Hamiltonian angular-velocity reconstruction beyond the current audited
  payload rules.

## 6. Completed And Superseded Phases

Earlier phases are complete or superseded at roadmap level. Historical detail
should not be re-expanded here.

- Phase 0 established the root roadmap direction and moved old architecture
  material into `legacy/`.
- Phase 1 modernized the Python/runtime/dependency baseline around Python 3.12,
  `.python-version`, and top-level runtime requirements.
- Phase 2 established the first pytest safety net.
- Phase 3 moved reusable math, model, plotting, and validation code under
  `src/double_pendulum/`.
- Phase 4 split the Dash app into clearer page, callback, component, content,
  and routing ownership.
- Phase 5 moved the app toward the current teaching journey and redesigned
  page structure.
- Phase 6 substantially completed the Simulation Manifesto and Workbench
  evidence programme.
- Phase 7 substantially promoted the accepted Canvas-backed Simulation
  architecture into the live app.

Remaining cleanup from Phase 6 and Phase 7 was absorbed into Phase 8 and Phase
9. Durable implementation documentation belongs under `documentation/`.

## 7. Documentation Map

Planning:

- `ROADMAP.md` is the active planning and phase-control document.
- `AGENTS.md` is the coding-agent operating guide.
- `README.md` is the high-level project overview, setup, and usage guide.

Durable implementation documentation:

- `documentation/README.md` explains the production documentation structure.
- `documentation/development-workflow.md` records safe local development,
  tests, browser smoke checks, and Dash server cleanup rules.
- `documentation/simulation-canvas/` documents the current Canvas-backed
  Simulation architecture.
- `documentation/simulation-canvas/canvas-integration-api.md` records the
  Python/JavaScript responsibility boundary and payload API.
- `documentation/simulation-canvas/simulation-result-contract.md` records the
  backend/callback/store/rendering result contract.
- `documentation/simulation-canvas/callback-rendering-flow.md` records the
  Dash callback and Canvas rendering flow.
- `documentation/simulation-runtime/` records durable Simulation runtime
  stability work, including solver fidelity, callback routing, loading state,
  diagnostics, and manual UX inspection.

Evidence and history:

- Local ignored directories such as `development/math_fidelity/`,
  `development/simulation_workbench/`, and `development/solver_contract/` may
  contain exploratory evidence, workbench notes, and historical implementation
  support. They are not required in the tracked repo.
- `development/` more broadly is exploratory/reference material and must not
  become a production runtime dependency. Accepted findings belong in
  production code, tracked tests, or `documentation/`.
- `legacy/` contains historical reference material.
