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

Last restructured: 2026-06-02.

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

- The Canvas-backed Simulation runtime has a stronger numerical, callback,
  layout, and deployment baseline, but the app is not a complete scientific
  validation project.
- Existing tests are useful but not a complete scientific validation suite.
- Energy diagnostics, chaos diagnostics, tolerance sensitivity,
  solver-method equivalence, and long-duration scientific validity are not
  proven.

## 2. Completed Phases: Phase 8 & 9

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
- A temporary Simulation integrator-policy selector supported Phase 8 manual
  inspection and was deferred to Phase 9 for removal or hiding.
- Compound-model runs showed no noticeable issue during inspection, so no
  compound-specific action was taken. If a compound issue appears later, handle
  it as a focused evidence/fidelity pass.
- Durable runtime stability documentation lives under
  `documentation/simulation-runtime/`.

Residual risks accepted or deferred:

- Browser-level coverage does not directly inspect Canvas pixels or renderer
  internals across route transitions.

**Phase 9: Production layout, deployment hooks, styling, and UX rules**

Phase 9 is complete at roadmap level. It consolidated the accepted Phase 8
runtime into a production-presentable app baseline without weakening solver,
result-state, or Canvas payload protections.

Completed:

- Explicit Flask server hook ownership was added for deployment concerns.
- HTTPS redirect behaviour was moved behind configuration with the
  `FORCE_HTTPS` flag.
- Local development is safe by default and no longer requires commenting
  deployment code in or out.
- `pendulum_app.py` remains thin: app creation, server exposure, layout shell,
  callback registration, and server hook registration.
- Production layout rules were established for the app shell and pages.
- Fixed-header and normal-flow footer behaviour were stabilized.
- The app no longer uses a fixed footer.
- The Simulation run action is owned by the Simulation controls/sidebar, not by
  the global footer.
- Phase 8 diagnostic UI such as the temporary integrator-policy selector was
  removed from normal UI or hidden behind non-user-facing ownership.
- The Simulation page layout and responsive behaviour were consolidated around
  clear control, run, playback, output, status, and diagnostics ownership.
- User-facing status and diagnostic presentation was improved without weakening
  solver/result/Canvas contracts.
- `assets/styles.css` was organized around design tokens, scoped rules, and
  conservative legacy quarantine/cleanup.
- Ad hoc and legacy styling was rationalized where safe, with uncertain cleanup
  captured in maintenance documentation.
- Browser smoke-check expectations remain part of the UI-facing validation
  workflow.
- Focused deployment hook tests were added where implemented.

Residual risks accepted or deferred:

- Browser-level coverage still does not directly inspect Canvas pixels or
  renderer internals across all responsive layouts.
- Some legacy and compatibility material remains intentionally deferred for a
  later manual cleanup decision; see `documentation/maintenance/`.
- Scientific validation topics remain deferred as listed below.

## 3. Active Phase: Phase 10

Phase 10 is the active phase.

**Phase 10: Chaos mathematical framework, high-resolution diagnostics, and
interactive-output foundations**

Phase 10 is not a quick plotting pass and not a production `/chaos` page
redesign. The goal is to build a mathematically trustworthy chaos diagnostics
foundation for the double pendulum before any production Chaos page
implementation begins.

Initial Phase 10 sandbox work under `development/chaos_content/` inspected the
historic untracked `development/chaos_branch/` material and produced a minimal
Hamiltonian Poincare-section experiment. That work showed that short-run plot
generation is useful as a smoke test, but nowhere near sufficient for the
intended Chaos page. The project now needs systematic mathematical conventions,
long-duration numerical policies, and reproducible diagnostics before visual or
interactive outputs can be treated as meaningful.

Phase 10 scope:

- Systematically define chaos-analysis conventions for the app.
- Build from the accepted existing `DoublePendulum` model classes where
  appropriate, rather than maintaining isolated or stale duplicate mechanics.
- Establish canonical state, angle, velocity, and momentum conventions.
- Define valid Poincare-section conventions, including wrapped-angle sections,
  crossing direction, interpolation/event handling, transient discard policy,
  and plotted coordinate/momentum pairs.
- Define solver policies for long-duration chaos diagnostics.
- Define energy-drift, failure, rejection, and non-renderable-result policies
  for long runs.
- Create reproducible high-resolution diagnostic data-generation pipelines.
- Keep generated diagnostic outputs out of accidental commits.
- Support eventual interactive outputs, while avoiding premature production UI
  wiring.
- Treat high-resolution plots and interactive visualisations as products of a
  validated framework, not as standalone experiments.
- Preserve the rule that production code must not import from `development/`.

Phase 10 non-goals:

- No immediate `/chaos` page redesign.
- No production UI integration until the mathematical framework is accepted.
- No promotion of historic `development/chaos_branch/` code, generated data,
  images, CSVs, or JSON structures.
- No broad data collation without fidelity checks.
- No large generated datasets committed to the repository.
- No weakening of the existing Simulation runtime, solver/result, or Canvas
  contracts.

Phase 10 gates:

- A documented chaos-state convention exists.
- Poincare-section definitions are mathematically explicit and tested.
- Long-duration solver policies are documented and validated against
  energy-drift criteria.
- The framework integrates cleanly with the existing double-pendulum model
  classes, or clearly documents why a separate experimental implementation is
  temporarily required.
- Generated diagnostic outputs are reproducible and excluded from accidental
  commits.
- At least one high-resolution diagnostic artifact is accepted as
  mathematically meaningful before any production Chaos UI work begins.

## 4. Deferred Work

Deferred until the Phase 10 framework gates have passed:

- production `/chaos` page implementation or redesign;
- new comparison workspace;
- additional analytical Plotly output suite;
- new simulation-output galleries;
- major numerical-method changes;
- broad product/UI experimentation;
- large visual redesigns unrelated to accepted Phase 10 framework outputs.

Scientific validation topics not yet accepted by Phase 10 remain unresolved:

- tolerance sensitivity;
- solver-method equivalence;
- Lyapunov exponents and other quantitative chaos metrics;
- bifurcation analysis;
- long-duration scientific validity;
- Hamiltonian angular-velocity reconstruction beyond the current audited
  payload rules.

## 5. Completed And Superseded Phases

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

Remaining cleanup from Phase 6 and Phase 7 was absorbed into Phase 8 and
Phase 9. Durable implementation documentation belongs under `documentation/`.

## 6. Documentation Map

Planning:

- `ROADMAP.md` is the active planning and phase-control document.
- `AGENTS.md` is the coding-agent operating guide.
- `README.md` is the high-level project overview, setup, and usage guide.

Durable implementation documentation:

- `documentation/README.md` explains the production documentation structure.
- `documentation/development-workflow.md` records safe local development,
  tests, browser smoke checks, and Dash server cleanup rules.
- `documentation/maintenance/` records maintenance audits and cleanup reports,
  including the Phase 9 legacy closeout audit.
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

- `development/chaos_content/` is the Phase 10 chaos diagnostics sandbox and
  evidence area. It records discovery from the historic chaos branch and houses
  controlled, reproducible chaos-content experiments and ignored diagnostic
  outputs.
- Local ignored directories such as `development/math_fidelity/`,
  `development/simulation_workbench/`, and `development/solver_contract/` may
  contain exploratory evidence, workbench notes, and historical implementation
  support. They are not required in the tracked repo.
- `development/` more broadly is exploratory/reference material and must not
  become a production runtime dependency. Accepted Phase 10 findings may later
  move deliberately into `src/double_pendulum/`, tracked tests, or durable
  `documentation/`.
- `legacy/` contains historical reference material.
