# Nonlinear Dynamics / Chaos Companion Roadmap

This roadmap is the active planning document for modernizing the Double
Pendulum Dash app into a focused companion app for nonlinear dynamics, chaos,
numerical simulation, and mathematical explanation. It is intended to evolve as
the project evolves. It is not a low-level issue tracker.

## Current status

Last audited: 2026-05-26.

- Phase 0: Complete.
  - `ROADMAP.md` exists at the repository root.
  - `legacy/ARCHITECTURE.md` exists and root `ARCHITECTURE.md` is absent.
  - `README.md` and `AGENTS.md` identify `ROADMAP.md` as the active
    modernization/planning source.
  - Documentation no longer preserves Python 3.9, `env/`, or `runtime.txt` as
    active setup or deployment guidance.
- Phase 1: Complete.
  - `.python-version` exists and declares `3.12`.
  - `runtime.txt` is absent and documentation says it must not be reintroduced.
  - `.venv/` is ignored by `.gitignore`.
  - `requirements.txt` is a top-level application/runtime dependency list:
    `dash`, `dash-bootstrap-components`, `Flask`, `gunicorn`, `matplotlib`,
    `numpy`, `plotly`, `scipy`, and `sympy`.
  - Dash imports use modern `dash` package imports rather than legacy
    `dash_core_components` or `dash_html_components`.
  - Validation on 2026-05-26: `source .venv/bin/activate && python -m pip
    install -r requirements.txt` completed with all requirements already
    satisfied; `python -m pip check` reported no broken requirements; `python
    pendulum_app.py` started the Dash development server at
    `http://127.0.0.1:8050/`; `gunicorn pendulum_app:server` listened at
    `http://127.0.0.1:8000`.
  - Note: direct `python` is not available on this machine until `.venv` is
    activated. Local server binding required running the server commands outside
    the sandbox, then stopping them after startup was confirmed.
- Phase 2: Complete.
  - Test runner is `pytest`, configured by `pytest.ini`.
  - `requirements-dev.txt` lists test-only dependencies separately from the
    top-level application/runtime dependencies in `requirements.txt`.
  - Tests are organized under `tests/unit/`, `tests/integration/`, and
    `tests/numerical/`.
  - Validation tests cover representative valid inputs plus invalid time
    intervals, lengths, masses, gravity, and initial conditions.
  - App smoke tests import `pendulum_app` without starting a server, verify the
    Flask `server` object for Gunicorn-style deployment, and check public route
    layout creation.
  - Numerical tests cover basic Lagrangian and Hamiltonian simulation output
    shape, finite values, precomputed position dimensions, and
    initial-condition consistency.
  - Lightweight symbolic fidelity tests cross-check the simple Lagrangian and
    Hamiltonian forms against the reference derivation notebooks. Full
    derivation audits, compound-equation symbolic checks, energy-conservation
    tolerances, trajectory regression fixtures, and a Hamiltonian state/input
    convention audit remain known gaps.
  - Validation on 2026-05-26: `.venv/bin/python -m pip install -r
    requirements-dev.txt` installed `pytest`; `.venv/bin/python -m pytest`
    passed with 50 tests.
- Phase 3: Complete.
  - Main reusable root-level modules have been moved into
    `src/double_pendulum/`: validation logic, symbolic math helpers, Lagrangian
    and Hamiltonian model classes, and plotting/display helpers.
  - Root-level `AppFunctions.py`, `MathFunctions.py`,
    `DoublePendulumLagrangian.py`, and `DoublePendulumHamiltonian.py` initially
    remained as compatibility wrappers. They were retired during Phase 4g after
    active imports moved to `src/double_pendulum/`.
  - `pendulum_app.py` imports the reusable package directly while still
    exposing the Flask `server` object for Gunicorn-style deployment.
  - Dash routes, layouts, callbacks, UI, and model equations were not
    restructured or rewritten. This is the intended stopping point before Phase
    4 multipage architecture work.
  - Validation on 2026-05-26: `source .venv/bin/activate && python -m pytest`
    passed with 54 tests.
- Phase 4a: Complete.
  - Introduced a minimal Dash app-layer package with `app/content/` for
    user-facing copy, page titles, route/navigation metadata, markdown paths,
    and references.
  - Introduced `app/pages/` with an explicit route-to-layout registry while
    preserving the existing pseudo-multipage layout modules and public routes.
  - Layout files now import structured content rather than owning long-form
    copy directly. Callbacks, component extraction, and a thinner app entrypoint
    remain future Phase 4 work.
  - Validation on 2026-05-26: `.venv/bin/python -m pytest` passed with 57
    tests.
- Phase 4b: Complete.
  - Added `app/callbacks/simulation.py` with `register_simulation_callbacks(app)`
    for the main simulation-page callbacks.
  - Moved the info popup, unity-parameter, model-parameter visibility,
    input-change clearing/validation, and run-simulation graph callbacks out of
    `pendulum_app.py` without changing callback IDs, inputs, outputs, states,
    validation, model, numerical, or plotting behavior.
  - Kept URL routing and the clientside home-page reinitialization callback in
    `pendulum_app.py` as app-shell wiring.
  - Validation on 2026-05-26: `.venv/bin/python -m pytest` passed with 58
    tests.
- Phase 4c: Complete.
  - Added shared UI component helpers under `app/components/` for navigation,
    page shell sections, footer, description/model cards, graph wrappers, and
    references.
  - Updated layout modules to import shared components instead of reaching into
    `layouts/layout_main.py` for navbar, title, footer, reference, and graph
    helper construction.
  - Preserved existing routes, copy, CSS classes, Dash component IDs, callback
    wiring, visual design, numerical behavior, and validation behavior.
  - Dense simulation input controls remain inline in `layouts/layout_main.py`
    until a lower-risk page/component extraction step can give them focused
    ownership.
  - Validation on 2026-05-26: `.venv/bin/python -m pytest` passed with 61
    tests.
- Phase 4d: Complete.
  - Added `app/components/simulation_controls.py` for the main simulation
    sidebar controls, grouped into focused helpers for information, model/system
    selection, physical parameters, initial conditions, and time interval
    controls.
  - Updated `layouts/layout_main.py` to call the simulation control component
    while preserving page composition, copy, CSS classes, and every
    callback-bound Dash component ID.
  - `app/callbacks/simulation.py` was not changed; callback inputs, outputs,
    states, validation behavior, plotting calls, and model logic remain
    unchanged.
  - Validation on 2026-05-26: `.venv/bin/python -m pytest` passed with 62
    tests.
- Phase 4e: Complete.
  - Added explicit page modules under `app/pages/` for the main simulation,
    derivation, chaos, and 404 fallback pages.
  - Updated `app/pages/registry.py` so `/`, `/lagrangian`, `/hamiltonian`, and
    `/chaos` resolve directly to `app/pages` layout functions while preserving
    the existing 404 fallback behavior.
  - Converted legacy `layouts/layout_main.py`, `layouts/layout_math.py`,
    `layouts/layout_chaos.py`, and `layouts/layout_404.py` into compatibility
    wrappers so there is one route-level page source of truth.
  - Preserved routes, copy, CSS classes, Dash component IDs, callback behavior,
    validation behavior, graph output wiring, numerical behavior, and model
    logic.
  - Validation on 2026-05-26: `.venv/bin/python -m pytest` passed with 64
    tests.
- Phase 4f: Complete.
  - Added `app/callbacks/routing.py` with `register_routing_callbacks(app)` for
    URL routing and the existing `initializeHomePage()` clientside
    reinitialization hook.
  - `pendulum_app.py` now creates and exposes the Dash/Flask app, assigns the
    top-level layout shell, and calls explicit callback registration functions.
  - Preserved routes, 404 fallback behavior, clientside startup behavior, copy,
    CSS classes, Dash component IDs, callback semantics, validation behavior,
    graph output wiring, numerical behavior, and model logic.
  - Validation on 2026-05-26: `.venv/bin/python -m pytest` passed with 66
    tests.
- Phase 4: Complete.
  - Page modules now own route-level layouts under `app/pages/`.
  - User-facing copy and metadata live under `app/content/`.
  - Shared navigation, shell, footer, card, graph, reference, and simulation
    control helpers live under `app/components/`.
  - Simulation and app-shell routing callbacks are registered from
    `app/callbacks/`.
  - The app entrypoint is thin while preserving the Gunicorn-facing
    `pendulum_app:server` contract.
  - The current four-page route scope is covered by import and route-layout
    smoke tests.
- Phase 4g: Complete.
  - Proved the legacy root compatibility modules and legacy `layouts/` package
    were no longer active dependencies by repository-wide search and test
    migration.
  - Deleted `AppFunctions.py`, `MathFunctions.py`,
    `DoublePendulumLagrangian.py`, `DoublePendulumHamiltonian.py`, and the
    legacy `layouts/` package.
  - Moved the Matplotlib-to-Plotly style helper from
    `layouts/layout_matplotlib.py` to `app/components/figure_style.py`.
  - Updated tests and documentation to import from the modern `app/` and
    `src/double_pendulum/` modules.
  - Validation on 2026-05-26: `.venv/bin/python -m pytest` passed with 65
    tests.
- Phase 5a: In progress.
  - Introduced the first redesigned landing-page route at `/` and moved the
    existing interactive double-pendulum workflow to `/simulation`.
  - Removed visible navigation chrome from the home page so it reads as a full
    hero landing page.
  - Added a light academic header for simulation and content pages, with
    page-aware subtitle text and hamburger navigation to Home, Simulation,
    Lagrangian, Hamiltonian, and Chaos.
  - Simplified the 404 page into a sparse home-style error state with links
    back to Home and Simulation.
  - Follow-up polish remains for browser-level visual QA across practical
    viewport sizes and for the broader simulation/content page redesign.

## 1. Project identity

This project is the **Nonlinear Dynamics / Chaos Companion App**.

The double pendulum is the sole concrete physical system in scope. The app may
teach broader ideas from nonlinear dynamics and chaos, but it should do so
through the double pendulum as a rich, concrete case study rather than by
becoming a generic dynamical-systems catalog.

The teaching goal is pedagogical clarity around:

- nonlinear motion and sensitivity to initial conditions
- Lagrangian and Hamiltonian formulations
- numerical simulation and approximation error
- phase-space interpretation
- qualitative and quantitative chaos indicators

The public domain identity remains `double-pendulum`, so the app should not
become so generic that the double pendulum feels incidental. The broader
identity should deepen the double-pendulum story, not replace it.

## 2. Audience and teaching level

The target level is advanced undergraduate mathematics, physics, engineering,
or scientific-computing study.

The app should support:

- students meeting nonlinear dynamics or chaos for the first time
- educators who want an interactive teaching aid
- motivated self-learners
- portfolio reviewers evaluating technical judgment, pedagogy, and craft

The experience should reveal complexity progressively. A user should be able to
start with motion, parameters, and intuition before being invited into
derivations, numerical methods, phase-space structure, and chaos diagnostics.
The app should avoid presenting every detail at once.

## 3. Current state summary

The current app is a modernized Dash application with a Flask `server` object
for Gunicorn/Heroku-style deployment:

- `pendulum_app.py` creates the Dash app, exposes `server`, defines the
  top-level shell, and registers app callbacks.
- `app/content/` contains user-facing page copy, route/navigation metadata,
  markdown asset paths, and reference lists introduced during Phase 4a.
- `app/pages/` contains the explicit route-level page modules and route-to-layout
  registry for the pseudo-multipage app.
- `app/callbacks/simulation.py` registers the main simulation-page callbacks
  introduced during Phase 4b.
- `app/callbacks/routing.py` registers app-shell URL routing and clientside
  page reinitialization callbacks introduced during Phase 4f.
- `app/components/` contains shared Dash component helpers for navigation,
  shell sections, footers, graph wrappers, references, and simple cards
  introduced during Phase 4c, plus the simulation control panel introduced
  during Phase 4d, plus the converted Matplotlib/Plotly figure style helper
  retired from the old `layouts/` package during Phase 4g.
- `src/double_pendulum/` contains reusable logic:
  - `validation/` for input validation, constants, and Dash error rendering.
  - `math/` for symbolic mechanics helpers.
  - `models/` for Lagrangian and Hamiltonian model classes.
  - `plotting/` for shared figure/display helpers.
- `assets/` contains Dash-served CSS, JavaScript, markdown/LaTeX content,
  existing app images, and newer hero image experiments under `assets/Heros`.
- `tests/` is organized into unit, integration, and numerical coverage from the
  Phase 2 foundation.

Important modernization context:

- Python 3.12 is the active development runtime.
- `.venv/` is the local development environment.
- `.python-version` is the runtime source of truth for future Heroku deployment.
- `runtime.txt` has intentionally been removed and must not be reintroduced.
- `requirements.txt` should continue moving toward top-level
  application/runtime dependencies only, not a full transitive freeze.
- The old app is still associated with an old Heroku dyno, but the active
  direction is modernization first and redeployment later.

The `development/` directory contains exploratory and reference work rather
than production app code. In particular:

- `development/math_reference/` preserves earlier derivations, notebooks, and
  OOP experiments that led toward the app.
- `development/chaos_branch/` contains prototype work for Poincare sections,
  ensembles, data collation, integration-cost analysis, and future chaos
  features.
- These files are useful historical and technical references, but production
  code should not depend on them until relevant pieces are reviewed, tested, and
  migrated into the modern source layout.

## 4. Target architecture

`legacy/ARCHITECTURE.md` is useful inspiration for separating Dash pages,
components, content, figures, models, and callbacks. It is not the active source
of truth for this project and should be adapted to the nonlinear dynamics /
double-pendulum domain.

Because this app needs reusable mathematical, numerical, plotting, validation,
and chaos-analysis code, the target architecture should include a proper `src/`
package as well as a cleaner Dash app package.

A likely future structure is:

```text
src/
  double_pendulum/
    models/
    math/
    numerics/
    chaos/
    plotting/
    validation/
app/
  pages/
  components/
  layouts/
  callbacks/
  content/
  assets/
tests/
  unit/
  integration/
  regression/
development/
legacy/
```

This exact structure is a starting point, not a commandment. Names should be
adapted as code is migrated and real module boundaries become clearer.

The migration should be incremental. The first objective is not to make the tree
look perfect; it is to make responsibilities clearer while preserving behavior
and building tests around the physics and app contracts.

## 5. Refactoring principles

- Separate mathematical model code from Dash UI code.
- Separate simulation and numerical integration from plotting.
- Separate page layout from callbacks where it improves clarity and testability.
- Keep user-facing pages pedagogically clean: explanations, controls, plots, and
  navigation should support learning rather than expose implementation clutter.
- Preserve `DoublePendulumLagrangian` and `DoublePendulumHamiltonian` initially.
  They are important behavior anchors while tests are still thin.
- Treat a future model factory, shared simulator interface, or unified result
  schema as lower priority until correctness tests exist.
- Avoid rewriting physics/model code before there are tests for shape,
  finite-value behavior, parameter handling, and numerical sanity.
- Keep migration commits behavior-preserving where possible so regressions are
  easier to isolate.

## 6. Proposed phased roadmap

### Phase 0: Documentation and project direction

Set the new direction before large code movement begins.

Key work:

- Create this roadmap.
- Move the generic architecture dump to `legacy/ARCHITECTURE.md`.
- Clean stale deployment/setup guidance from `README.md` and `AGENTS.md`.
- Clarify that modernization has priority over preserving the old deployed
  state.
- Establish `ROADMAP.md` as the active planning document.

Definition of done:

- `ROADMAP.md` exists at the repository root.
- `legacy/ARCHITECTURE.md` is historical reference, not active architecture
  policy.
- Documentation no longer tells future agents to preserve Python 3.9 or
  reintroduce `runtime.txt`.

### Phase 1: Stack and dependency modernization

Make the local and future deployment runtime explicit and boring.

Key work:

- Use Python 3.12 locally.
- Use `.venv/` for local development.
- Use `.python-version` as the Heroku Python runtime source of truth.
- Keep `runtime.txt` removed.
- Keep `requirements.txt` focused on top-level app/runtime dependencies.
- Continue modernizing Dash imports and compatibility details.
- Clean `.gitignore` so generated caches, virtual environments, local IDE files,
  and intentionally ignored prototype assets are handled deliberately.

Definition of done:

- A fresh `.venv/` can install `requirements.txt`.
- `python pendulum_app.py` starts the app locally.
- `gunicorn pendulum_app:server` can import and serve the app locally.
- No docs or deployment files depend on `runtime.txt`.
- Dependency documentation explains top-level dependencies versus archived
  historical freezes.

### Phase 2: Test foundation

Build a safety net before deeper extraction or model rewrites.

Key work:

- Establish a clear test layout under `tests/`.
- Keep or migrate input validation tests.
- Add tests for app import and startup smoke behavior.
- Add numerical sanity tests for the model classes.
- Add tests for simulation output shape and finite values.
- Add basic parameter validation tests around invalid time intervals, lengths,
  masses, gravity, and initial conditions.

Definition of done:

- Tests run with one documented command.
- The test suite imports the app without starting a server.
- Validation behavior is covered for representative valid and invalid inputs.
- Lagrangian and Hamiltonian simulations have basic finite-value and shape tests.
- Known gaps are documented rather than hidden.

### Phase 3: Codebase extraction

Move reusable logic into a source package while keeping behavior equivalent.

Key work:

- Introduce `src/double_pendulum/` or an equivalent package structure.
- Move reusable math helpers out of root-level modules.
- Separate model, numerics, plotting, validation, and UI concerns.
- Keep existing public page behavior stable while moving code.
- Preserve `DoublePendulumLagrangian` and `DoublePendulumHamiltonian` as
  compatibility anchors until their responsibilities can be split safely.

Definition of done:

- Core double-pendulum logic can be imported without Dash.
- Plotting functions can be called independently from page callbacks.
- Validation logic is testable without constructing Dash pages.
- Existing simulation workflows still produce time graphs, phase graphs, and
  animations.
- Tests cover the moved code paths.

### Phase 4: Multipage app architecture

Give the Dash app a clearer page and callback structure.

Immediate pages in scope:

- landing page
- main simulation
- derivation
- chaos

Key work:

- Establish an app package structure for pages, callbacks, components, layouts,
  and content.
- Keep URL routing explicit.
- Move long explanatory content into content modules or structured markdown
  assets where appropriate.
- Keep callbacks close to the page or feature they serve unless shared behavior
  justifies extraction.
- Preserve existing routes until a deliberate route migration is planned.

Definition of done:

- Page modules have clear ownership of layout and page-specific callback
  registration.
- Shared controls, graph wrappers, and navigation live in reusable components.
- The app entrypoint is thin and understandable.
- The current four-page scope works locally.

Status: Complete as of Phase 4g. The page, content, callback, component, and
route-registry boundaries are explicit, legacy compatibility wrappers have been
retired, and `.venv/bin/python -m pytest` passed with 66 tests on 2026-05-26.

### Phase 5: Pedagogical UI redesign

Redesign the interface after the architecture can support it.

Key work:

- Complete a visual redesign once model, plotting, validation, and page
  boundaries are cleaner.
- Use `assets/Heros` as visual inspiration for the new identity.
- Assume the color palette may be redesigned completely.
- Keep the aesthetic restrained, academic, calm, and suitable for nonlinear
  dynamics and chaos.
- Use visual fidelity to support mathematical clarity, not to compete with it.

Definition of done:

- The first viewport clearly signals double-pendulum identity.
- The main simulation workflow is easier to scan and teach from.
- Mathematical explanations are progressive and readable.
- Visual assets and palette choices reinforce the app's learning goals.
- The redesign is validated in browser across practical viewport sizes.

Current status: Phase 5a has established the route split and first visual
direction: `/` is now the chromeless landing page, `/simulation` owns the
interactive simulation workflow, non-home teaching pages use a light shared
header with hamburger navigation, and unknown routes use a simplified 404.
The next Phase 5 work should concentrate on browser polish, responsive visual
QA, and redesigning the simulation/content pages without disturbing numerical
or callback behavior.

### Phase 6: Math fidelity and numerical validation

Raise confidence in the mathematical and numerical behavior.

Key work:

- Build toward Level 3 numerical testing:
  - output shape and finite-value tests
  - initial-condition consistency tests
  - energy sanity checks
  - numerical drift checks under suitable tolerances
  - trajectory consistency checks for representative parameter sets
- Define tolerances explicitly and document why they are acceptable.
- Compare Lagrangian and Hamiltonian behavior where the state definitions make
  comparison meaningful.
- Avoid overclaiming exact conservation in chaotic or numerically sensitive
  regimes.

Definition of done:

- Representative simulations have documented sanity expectations.
- Energy and drift checks exist for suitable regimes and tolerances.
- Numerical failures are distinguishable from UI failures.
- Model changes cannot silently break basic physical plausibility.

### Phase 7: Chaos content scaffolding

Develop chaos content carefully after the simulation foundations are stable.

Future content scaffolding:

- sensitivity to initial conditions
- phase-space interpretation
- Poincare sections
- Lyapunov exponents
- bifurcation-style scans
- sensitivity experiments and side-by-side trajectories
- numerical integration error and tolerance demonstrations

These are future teaching modules, not immediate high-priority implementation
targets. The `development/chaos_branch/` work should inform this phase, but it
should not be promoted wholesale without tests and review.

Definition of done:

- Chaos concepts are introduced progressively from visible motion to phase-space
  structure to quantitative diagnostics.
- Prototype chaos code has been reviewed and migrated intentionally.
- New metrics have tests or clearly documented limitations.
- Expensive computations have realistic performance boundaries.

### Phase 8: Deployment refresh

Redeploy only after local modernization is stable.

Key work:

- Prepare future Heroku deployment using `.python-version`.
- Do not reintroduce `runtime.txt`.
- Validate the production start command after the local architecture and
  dependencies are modernized.
- Revisit HTTPS redirect behavior as explicit configuration rather than
  commented code.
- Document deployment assumptions once they are verified against the target
  Heroku stack.

Definition of done:

- Local tests and smoke checks pass.
- Heroku runtime selection is driven by `.python-version`.
- `Procfile` and the app entrypoint agree.
- Deployment instructions are current and reproducible.

## 7. Page scope

Immediate page scope is limited to:

- landing page
- main simulation
- derivation
- chaos

Additional pages are future work. They should not drive the first refactor.
The first refactor should make the current teaching flow easier to maintain,
test, and improve.

## 8. UI and fidelity direction

The current UI may be completely redesigned in a later phase. The app should
not be constrained by the existing visual treatment once the architecture is
ready for a redesign.

`assets/Heros` should be treated as visual inspiration for the future identity.
The likely direction is a complete palette redesign, but the final palette is
still to be confirmed.

Visual fidelity should support mathematical clarity. Motion, phase-space
structure, derivation steps, and numerical interpretation should remain the
center of the experience.

## 9. Math/model fidelity goals

The existing `DoublePendulumLagrangian` and `DoublePendulumHamiltonian` classes
should be preserved initially because they encode the current working behavior.

Priorities:

- tested correctness before premature abstraction
- energy sanity checks where physically and numerically appropriate
- numerical stability under documented solver tolerances
- parameter validation before expensive simulations run
- trajectory consistency for representative initial conditions
- clear separation between state definitions for Lagrangian and Hamiltonian
  formulations

Factory-style model creation, shared simulator interfaces, and unified result
objects may become useful later. They are lower priority than test coverage and
behavior-preserving extraction.

## 10. Testing strategy

Testing is still an important project risk, but Phase 2 establishes the first
reliable safety net. The suite is intentionally foundational rather than a full
numerical validation project.

Run the suite from the activated Python 3.12 virtual environment with:

```bash
python -m pytest
```

Recommended layers:

- Unit tests for validation, parameter conversion, math helpers, and small
  numerical utilities.
- Numerical tests for model output shape, finite values, initial-condition
  consistency, energy sanity, and drift under explicit tolerances.
- App smoke tests for import, route layout creation, and callback-level behavior
  where practical.
- Regression fixtures for selected representative simulations once the model
  APIs stabilize.
- Browser smoke checks for the main user flow after UI changes.

Major model rewrites should wait until the core numerical tests exist.

Chaos metrics are harder to test because sensitivity is the point. Early chaos
work should be scaffolded carefully with tests for invariants, shapes,
finite-values, deterministic seeds where applicable, and qualitative fixture
expectations rather than brittle exact trajectories.

## 11. Development directory integration plan

`development/` should be treated as exploratory/prototype/reference material
unless code is explicitly promoted.

Current classification:

- `development/math_reference/`: historical derivations, notebooks, resource
  images, and early OOP model work. Useful for explanation, validation ideas,
  and provenance.
- `development/chaos_branch/`: future integration work around Poincare maps,
  ensembles, cost analysis, data collation, and chaos experiments.

Promotion path:

1. Identify one useful prototype capability.
2. Review the code for dependencies, performance assumptions, and mathematical
   assumptions.
3. Write tests around the intended behavior.
4. Move a small, focused implementation into `src/double_pendulum/`.
5. Connect it to the Dash app only after the package-level behavior is stable.

Production app code should not import unstable prototype modules from
`development/`. Prototype notebooks and scripts can inform implementation, but
they should not become hidden runtime dependencies.

## 12. Documentation alignment

`README.md`, `AGENTS.md`, and `ROADMAP.md` should eventually agree about:

- project identity
- supported Python version
- local environment setup
- deployment source of truth
- active page scope
- testing expectations
- the role of `development/` and `legacy/`

`legacy/ARCHITECTURE.md` is historical inspiration from another multipage Dash
app. It may contain language from a different domain and should not be treated
as active architecture policy.

`ROADMAP.md` is the active planning document.

## 13. Risks and sequencing notes

- Avoid UI redesign before architecture extraction; otherwise visual work will
  be coupled to unstable module boundaries.
- Avoid model rewrites before tests; otherwise regressions in physics and
  numerics will be hard to detect.
- Avoid chaos feature expansion before simulation foundations are stable.
- Avoid deployment work until local modernization is stable.
- Avoid importing from `development/` in production code without review and
  tests.
- Avoid allowing the companion-app identity to become too generic; the double
  pendulum remains the concrete system.

## 14. Definition of done by phase

Phase 0 is done when the roadmap exists, the old architecture guide lives under
`legacy/`, and stale deployment-preservation language has been cleaned.

Phase 1 is done when Python 3.12, `.venv/`, `.python-version`, top-level
dependencies, modern imports, and ignored/generated files are documented and
locally verified.

Phase 2 is done when validation, app import/startup, and basic numerical sanity
tests run reliably with a documented command.

Phase 3 is done when reusable math, model, numerics, plotting, and validation
logic can be imported from a source package without Dash and existing behavior
is still covered.

Phase 4 is done when the landing, main simulation, derivation, and chaos pages
live in a clean multipage Dash architecture with explicit routing and callback
ownership.

Phase 5 is done when the redesigned UI supports the teaching flow, uses the new
visual direction deliberately, and has been browser-checked across relevant
viewports.

Phase 6 is done when representative simulations have shape, finite-value,
initial-condition, energy, drift, and trajectory consistency checks under
documented tolerances.

Phase 7 is done when chaos teaching modules are scaffolded from reviewed and
tested code rather than raw prototypes.

Phase 8 is done when future deployment is verified using `.python-version`,
without `runtime.txt`, after local modernization and smoke checks are stable.
