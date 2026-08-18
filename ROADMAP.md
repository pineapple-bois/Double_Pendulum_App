# Double Pendulum App Roadmap

This is the active project-control document for the Double Pendulum App. It is
not an implementation diary, callback reference, renderer API, or workbench
evidence archive.

Use this roadmap to answer:

- what baseline the project is currently building from;
- what phase is active;
- what comes next;
- what is deferred;
- where implementation details live.

Last restructured: 2026-08-18.

## 1. Project Baseline

The app has completed its visual consolidation without a broad application
rewrite. Its runtime, numerical-result handling, Canvas-backed Simulation
architecture, deployment hooks, production layout, and interactive-textbook
theme are established foundations for Chaos work.

Current application baseline:

- The app is a Dash application with a Flask `server` object for
  the production Gunicorn process deployed on Railway.
- Python 3.12 and `.python-version` define the supported runtime;
  `pyproject.toml` declares dependencies, `uv.lock` is the authoritative
  resolved environment, and the tracked `Procfile` declares the production
  process.
- `pendulum_app.py` remains thin: app creation, server exposure, layout shell,
  callback registration, and server-hook registration.
- Deployment-specific HTTPS behaviour is owned by the `FORCE_HTTPS`
  configuration flag. Local HTTP development is safe by default.
- Public teaching routes remain centered on Home, Equations of Motion,
  Simulation, and Chaos, with legacy `/lagrangian` and `/hamiltonian`
  routes preserved.
- The app shell uses a fixed header and a normal-flow footer. The Simulation
  run action is owned by the Simulation controls, not the global footer.
- Production code must not import from `development/`.

Current Simulation and numerical baseline:

- The `/simulation` page uses the accepted Canvas-backed architecture.
- Python owns mathematical and numerical truth.
- Dash callbacks and memory-scoped stores manage interaction state, solver
  results, and renderer payload delivery.
- Browser-side JavaScript/Canvas handles rendering, playback, resizing, and
  selected-frame inspection only.
- JavaScript must not integrate trajectories, compute physics, infer
  Hamiltonian angular velocities, or transform solver-state conventions.
- Solver failures are represented as non-render-safe results and cannot leave
  current drawable success arrays behind.
- The simple-model solver-policy baseline supports `dop853_moderate`
  (`method="DOP853"`, `rtol=1e-6`, `atol=1e-8`) as the normal policy and
  `dop853_strict` as the high-fidelity/reference policy.
- Route remounting, loading state, stale diagnostics, and result-state
  behaviour have focused regression coverage.
- The Simulation workspace has established desktop and responsive ownership
  for controls, run state, playback, outputs, status, and diagnostics.
- Detailed Simulation contracts live in `documentation/simulation-canvas/`
  and `documentation/simulation-runtime/`.

Current styling baseline:

- `assets/styles.css` has a semantic token layer, page-scoped production
  rules, responsive breakpoints, and a conservatively retained compatibility
  layer.
- Some legacy selectors and compatibility material remain. They should only be
  removed through evidence-based cleanup alongside the components that own
  them.
- The active Canvas renderer has its own display palette outside CSS.
- Retained Plotly and Matplotlib helpers are not part of the normal Simulation
  rendering path, but they still contain independent visual defaults.

Current known limits:

- Existing tests establish a useful runtime baseline but are not a complete
  scientific validation suite.
- Browser coverage does not directly inspect every Canvas pixel or renderer
  state across all route transitions and responsive layouts.
- Energy diagnostics, chaos diagnostics, tolerance sensitivity,
  solver-method equivalence, Lyapunov exponents, and long-duration scientific
  validity are not yet established.

## 2. Active Phase and Deferred Work

### Active phase

**Chaos is the active phase.**

The first objective is to establish a mathematically explicit and reproducible
chaos-analysis framework before replacing the current placeholder with a
production teaching surface. Work should:

- establish canonical chaos state, angle, velocity, and momentum conventions;
- define Poincare-section conventions, including wrapped-angle sections,
  crossing direction, interpolation or event handling, transient discard
  policy, and plotted coordinate or momentum pairs;
- define solver, energy-drift, failure, rejection, and non-renderable-result
  policies for long-duration runs;
- create reproducible high-resolution diagnostic data-generation pipelines;
- integrate with the accepted double-pendulum model classes where appropriate;
- keep generated diagnostic outputs out of accidental commits;
- accept at least one high-resolution diagnostic artifact as mathematically
  meaningful before production Chaos UI work begins.

The active work must preserve the numerical, callback, result-state, Canvas,
routing, deployment, and visual baseline described in Section 1. Evidence and
controlled experiments belong under `development/chaos_content/`; accepted
contracts should be promoted deliberately into production code, tests, and
documentation.

### Deferred work

- Lyapunov exponents, bifurcation analysis, and other quantitative chaos
  metrics beyond the first accepted diagnostic framework;
- production `/chaos` implementation or redesign until the framework and one
  diagnostic artifact are accepted;
- tolerance-sensitivity and solver-method-equivalence studies;
- long-duration scientific-validity claims;
- a new comparison workspace;
- additional analytical output galleries;
- major numerical-method changes;
- broad legacy removal unrelated to the active Chaos phase;
- promotion of historic `development/chaos_branch/` code or generated data;
- large generated datasets in the repository.

## 3. Documentation Map

Planning:

- `ROADMAP.md` is the active planning and phase-control document.
- `AGENTS.md` is the coding-agent operating guide.
- `README.md` is the high-level project overview, setup, and usage guide.

Durable implementation documentation:

- `documentation/README.md` explains the production documentation structure.
- `documentation/development-workflow.md` records safe local development,
  tests, browser smoke checks, and Dash server cleanup rules.
- `documentation/restyle.md` records the completed visual consolidation,
  preserved contracts, dependency outcome, and validation state.
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

- `development/chaos_content/` is the chaos diagnostics sandbox and evidence
  area. It records discovery from the historic chaos branch and houses
  controlled, reproducible chaos-content experiments and ignored diagnostic
  outputs.
- Local ignored directories such as `development/math_fidelity/`,
  `development/simulation_workbench/`, and
  `development/solver_contract/` may contain exploratory evidence, workbench
  notes, and historical implementation support. They are not required in the
  tracked repository.
- `development/` more broadly is exploratory/reference material and must not
  become a production runtime dependency. Accepted findings may later move
  deliberately into `src/double_pendulum/`, tracked tests, or durable
  `documentation/`.
- `legacy/` contains historical reference material.
