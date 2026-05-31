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

- The Canvas integration is implemented, but the app still needs numerical and
  callback hardening.
- Existing tests are useful but not a complete scientific validation suite.
- Energy diagnostics, chaos diagnostics, tolerance sensitivity, solver-method
  equivalence, and long-duration scientific validity are not proven.

## 2. Active Phase: Phase 8

**Phase 8: Numerical baseline, callback hardening, bug eradication, and
documentation control**

Phase 8 is the active phase.

Phase 8 is not styling. It is not a UX polish phase. It is not another
open-ended simulation workbench. It is not a new chaos or comparison branch.

Phase 8 exists to prove that the current app is mathematically credible and
callback-stable enough to continue.

Completed or substantially completed:

- Simple-model mathematical fidelity evidence has been promoted into focused
  production tests.
- Solver-policy evidence now supports `dop853_moderate`
  (`method="DOP853"`, `rtol=1e-6`, `atol=1e-8`) as the leading simple-model
  default candidate.
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
  inspection and remains easy to remove or hide in Phase 9.
- Durable solver fidelity and result-contract documentation exists at
  `documentation/phase-8-solver-fidelity-and-contract-record.md`.
- Durable callback, routing, manual UX, and loading-state notes exist under
  `documentation/`.

Active current work:

- Keep Phase 8 documentation links current while callback/result contracts are
  finalized.
- Keep `ROADMAP.md` concise and usable as project control.

Outstanding before Phase 8 can close:

- Decide whether to remove the temporary integrator-policy selector before
  Phase 8 closes or defer removal/hiding to Phase 9.
- Accept or separately address the residual browser-level coverage gap around
  Canvas pixels/renderer internals across route transitions.
- Ensure `documentation/` links remain current.
- Preserve the safe Dash smoke-test workflow and never leave a Codex-started
  Dash development server running.

Gates:

- Phase 9 styling/UX work must not begin until Phase 8 reaches a numerical and
  callback-stability baseline, unless the user explicitly waives that gate.
- New chaos/comparison/product work must not begin during Phase 8.
- Broad workbench experimentation must not resume during Phase 8.

Definition of done:

- The user-discovered bug is reproduced, understood, fixed, or explicitly
  documented if deferred.
- Mathematical fidelity expectations are tested for representative cases.
- Explicit simple-model solver policy is covered by production tests.
- Callback and loading-state behavior is tested.
- Canvas/backend payload assumptions are covered by focused tests.
- Solver failures are represented as first-class non-render-safe states.
- Failed, stale, empty, cleared, and successful states are distinguishable in
  tests and documentation.
- Failure states do not leave current drawable success arrays behind.
- Manual UX performance inspection is completed for representative simple
  Lagrangian and Hamiltonian runs.
- The temporary integrator-policy selector is either explicitly deferred to
  Phase 9 removal/hiding or removed before Phase 8 closes.
- `documentation/` is organized and links are current.
- `ROADMAP.md` remains concise and usable as a planning document.
- Dash smoke checks, if run, do not leave a Codex-started server running.

## 3. Next Phase: Phase 9

**Phase 9: Styling, production layout, and UX rules**

Phase 9 is next, but it is gated by Phase 8. Do not start Phase 9 styling or
UX work until Phase 8 establishes the numerical and callback-stability
baseline, unless the user explicitly redirects.

Scope:

- Define production layout rules.
- Remove or hide Phase 8 diagnostic controls such as the temporary
  integrator-policy selector.
- Consolidate the Simulation page layout.
- Stabilize header, footer, sidebar, run action, output workspace, diagnostics
  placement, and responsive behavior.
- Consolidate styling through `assets/styles.css`.
- Remove or rationalize ad hoc styling.
- Define rules for future UI changes.
- Add Initial State help/preset UX only after layout stability is achieved.
- Use browser smoke checks for UI-facing changes, with strict Dash server
  cleanup.

Out of scope:

- New simulation outputs.
- New chaos diagnostics.
- New comparison workspace.
- Additional analytical Plotly output suites.
- Broad visual redesigns unrelated to production layout consolidation.

## 4. Future Phase: Phase 10

**Phase 10: New work, to be defined**

Phase 10 is intentionally undefined for now.

It represents new product work after Phase 8 establishes numerical/callback
stability and Phase 9 establishes styling/UX stability. Phase 10 should be
scoped only after those baselines exist.

Possible future directions are listed as deferred candidates, not commitments.

## 5. Deferred Work

Deferred until after Phase 8 and Phase 9:

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

Remaining cleanup from Phase 6 and Phase 7 is absorbed into Phase 8 and Phase
9. Detailed workbench evidence remains under `development/simulation_workbench/`.
Durable implementation documentation belongs under
`documentation/simulation-canvas/`.

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
- `documentation/phase-8-solver-fidelity-and-contract-record.md` records the
  durable Phase 8 solver fidelity and result-contract work.
- `documentation/phase-8-callback-routing-stability.md` records the focused
  route-remount and callback lifecycle investigation.
- `documentation/phase-8-manual-ux-and-loading-state-inspection.md` records the
  closeout manual UX, stale diagnostics, and loading/interrupted-state
  inspection.

Evidence and history:

- `development/simulation_workbench/` contains Simulation Workbench evidence,
  renderer decisions, promotion notes, and historical implementation support.
- `development/` more broadly is exploratory/reference material and must not
  become a production runtime dependency.
- `legacy/` contains historical reference material.
