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

Last restructured: 2026-08-17.

## 1. Project Baseline

The app is stable enough to restyle without a broad application rewrite. Its
runtime, numerical-result handling, Canvas-backed Simulation architecture,
deployment hooks, and production layout are established foundations.

Current application baseline:

- The app is a Dash application with a Flask `server` object for
  Gunicorn/Heroku-style deployment.
- Python 3.12, `.python-version`, `requirements.txt`, and the tracked
  `Procfile` define the supported runtime and deployment path.
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

## 2. Restyle

### Goal

Give the Double Pendulum App the same recognisable interactive-textbook look as
the Population Dynamics App while preserving the double pendulum's subject
identity and the existing application architecture.

Population Dynamics is the visual reference implementation. The intended shared
language is:

- a warm off-white page background;
- white content surfaces;
- charcoal primary text;
- deep green accents with pale green secondary surfaces;
- a Helvetica Neue/system font stack;
- a 16px base type scale with restrained, fluid headings;
- 8px and 12px corner radii;
- quiet borders and shadows;
- generous document spacing;
- consistent white headers, footers, cards, controls, and plotting surfaces.

The objective is not to copy the complete Population Dynamics stylesheet or
force both apps into identical page structures. The shared theme should be
semantic and reusable; subject-specific teaching layouts remain app-owned.

### Restyle workstreams

#### 1. Establish the shared theme contract

- Treat the Population Dynamics palette, typography, spacing, radii, borders,
  shadows, content width, and header height as the source design.
- Introduce neutral interactive-textbook token names and map existing
  Double Pendulum role tokens onto them.
- Retain semantic roles such as page, surface, text, muted text, accent,
  border, success, warning, and danger rather than using raw colours in
  components.
- Use the Helvetica Neue/system stack and remove the current responsive
  root-font downscaling.
- Do not replace either application's complete stylesheet wholesale.

#### 2. Restyle the shared application shell

- Align the header, navigation menu, footer, page background, content width,
  headings, links, focus states, cards, controls, and document surfaces with
  the shared theme.
- Preserve public routes, callback-bound component IDs, store IDs, and Canvas
  renderer IDs.
- Keep the Equations page as a readable mathematical document rather than
  turning it into a dashboard.
- Keep the Simulation page's sidebar, playback area, Canvas grid, status, and
  diagnostics ownership while applying the shared visual language.
- Standardise generated Dash controls, including sliders, dropdowns, radio
  controls, checklists, and tooltips, so framework defaults do not leak into
  the theme.

#### 3. Promote the new home hero

- Use `assets/Heros/double_pend_hero1_green.png` as the intended Restyle home
  hero.
- Preserve the current full-height home composition: introduction on the left,
  Explore rail on the right, and reading/attribution content below.
- Replace the dark navy overlay treatment with the lighter Population
  Dynamics-style wash and readable charcoal/green typography.
- Verify text contrast across desktop and mobile crops.
- Keep hero artwork subject-specific; only its palette, visual weight, and
  composition belong to the shared template.

#### 4. Theme non-CSS visual surfaces

- Update the Canvas renderer's display-only palette to use the shared charcoal,
  green, muted, grid, status, and surface colours.
- Do not change renderer physics boundaries, payload schemas, playback
  behaviour, or solver/result contracts.
- Centralise any retained Plotly styling so fonts, paper backgrounds, grids,
  axes, traces, and modebar presentation follow the shared theme.
- Review dormant Matplotlib/Plotly model helpers separately; do not allow their
  legacy colours to drive production architecture.

#### 5. Simplify global styling dependencies

- Audit the Bootstrap stylesheet after the theme base and resets are in place.
- If browser and test evidence confirms that production markup does not depend
  on it, remove the unused Bootstrap theme and
  `dash-bootstrap-components` dependency.
- Remove the external Red Hat Display font request after the system font stack
  is active.
- Own base element styling explicitly so removing global dependencies does not
  introduce browser-default drift.

#### 6. Create the reusable interactive-textbook starting point

- Separate shared theme rules from app-specific Simulation, Equations, Chaos,
  and home-content rules.
- Keep a vendored, version-labelled shared theme asset in each app initially.
- Define reusable shell patterns for the app frame, header, footer, page
  header, hero, teaching card, control band, plot card, status message, and
  reading list.
- Document which tokens and components are shared and which are deliberately
  subject-specific.
- Use the accepted result as the basis of a GitHub template repository for
  future interactive textbooks.
- Consider a versioned shared package only after the theme has been exercised
  successfully in multiple apps and regular cross-app updates justify the
  added release overhead.

### Implementation sequence

1. Adopt the shared tokens, base typography, and explicit resets.
2. Restyle the header, footer, page surfaces, and shared controls.
3. Activate and tune the new green home hero.
4. Restyle the Equations and Simulation layouts without changing behaviour.
5. Update the Canvas and retained plotting palettes.
6. Remove confirmed-unused global styling dependencies.
7. Extract and document the reusable interactive-textbook theme boundary.

### Restyle acceptance gates

- Home, Equations, Simulation, Chaos, `/lagrangian`, and `/hamiltonian`
  retain their route behaviour.
- Simulation callbacks, result-state protections, Canvas payloads, playback,
  diagnostics, and validation behaviour remain unchanged.
- The full automated test suite passes.
- Desktop, tablet, and mobile layouts have no unintended overflow or clipped
  controls.
- The new hero remains legible at representative crops and breakpoints.
- Dash controls and Canvas outputs use the shared palette without unthemed
  framework defaults.
- Text, controls, links, focus indicators, and status states retain accessible
  contrast.
- Browser smoke checks report no missing assets or JavaScript errors.
- Any locally started Dash process is stopped explicitly after validation.

## 3. Active Phase and Deferred Work

### Active phase

**Restyle is the active phase.**

The initial feasibility review is complete and the light green double-pendulum
hero is available at `assets/Heros/double_pend_hero1_green.png`. Work should
follow the sequence and gates in Section 2.

The Restyle must not weaken the numerical, callback, result-state, Canvas,
routing, or deployment baseline described in Section 1.

### Deferred work

The chaos-analysis framework remains important, but is deferred until the
Restyle reaches its acceptance gates. When resumed, it should:

- establish canonical chaos state, angle, velocity, and momentum conventions;
- define mathematically explicit Poincare-section conventions, including
  wrapped-angle sections, crossing direction, interpolation/event handling,
  transient discard policy, and plotted coordinate/momentum pairs;
- define solver, energy-drift, failure, rejection, and non-renderable-result
  policies for long-duration runs;
- create reproducible high-resolution diagnostic data-generation pipelines;
- integrate with the accepted double-pendulum model classes where appropriate;
- keep generated diagnostic outputs out of accidental commits;
- accept at least one high-resolution diagnostic artifact as mathematically
  meaningful before production Chaos UI work begins.

Also deferred:

- production `/chaos` implementation or redesign;
- Lyapunov exponents, bifurcation analysis, and other quantitative chaos
  metrics;
- tolerance-sensitivity and solver-method-equivalence studies;
- long-duration scientific-validity claims;
- a new comparison workspace;
- additional analytical output galleries;
- major numerical-method changes;
- broad legacy removal unrelated to the Restyle;
- promotion of historic `development/chaos_branch/` code or generated data;
- large generated datasets in the repository;
- a packaged cross-app theme dependency before a vendored theme has proved
  stable across multiple apps.

## 4. Documentation Map

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
