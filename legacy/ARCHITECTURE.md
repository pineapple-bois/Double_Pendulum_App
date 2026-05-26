# Dash App Architecture Guide

This document describes the architectural conventions used by the multipage
Dash app under `dash_app/`. It is intended as a reusable refactoring guide for
other Dash projects. It focuses on file structure, separation of
responsibilities, and conventions rather than domain content or feature
planning.

## 1. Overall Architectural Principles

Recommended pattern:

- Keep the app app-native. Production Dash code lives inside `dash_app/` rather
  than being scattered across notebooks, experiments, or source folders built
  for a different runtime.
- Use explicit multipage routing. A central route table should make it easy to
  see which URL renders which page module.
- Keep the app entry point thin. `app.py` should create the Dash app, configure
  the server, register routes and callbacks, and render the current page shell.
  It should not contain page internals, plotting code, or domain analysis.
- Build pages from reusable scaffolding. Shared shells, cards, titles, sliders,
  markdown blocks, graph wrappers, and navigation belong in components.
- Separate content from layout code. Long explanatory prose, equations,
  references, and interpretation text should live in content modules.
- Separate figure generation from page assembly. Page callbacks should call
  figure-builder functions instead of constructing large Plotly figures inline.
- Separate domain logic from Dash callbacks where possible. Reusable
  calculations, parameter validation, registries, simulation helpers, and
  payload builders belong in models or domain modules.
- Use assets for global CSS and lightweight browser-side behaviour. CSS and
  browser widget scripts should support the app; authoritative calculations
  should remain in Python unless there is a deliberate client-side contract.
- Align tests with responsibilities. Test routing, page rendering, component
  markup, figures, models, validation, payloads, endpoints, and browser
  lifecycle behaviour at the layer where each responsibility lives.

Avoid:

- A single `app.py` that owns every layout, callback, route, calculation, and
  plot.
- Production app code that imports from notebooks, spikes, or sandbox folders.
- Page modules that mix long prose, numerical methods, Plotly construction, and
  callback state management in one place.

## 2. Recommended Directory Structure

Recommended root:

```text
dash_app/
  app.py
  config.py
  server_hooks.py
  pages/
  components/
  content/
  figures/
  models/
  routes/
  assets/
  documentation/
  tests/
```

### `dash_app/`

Belongs here:

- The production Dash application package.
- App-native pages, components, content, figures, domain helpers, assets,
  server hooks, route endpoints, and tests.
- Documentation that records durable app conventions.

Should not belong here:

- Notebook-only code.
- One-off migration experiments.
- Generated caches, temporary output, and exploratory prototypes.

Examples:

- `dash_app/app.py`
- `dash_app/pages/`
- `dash_app/models/`
- `dash_app/assets/styles.css`

Anti-patterns to avoid:

- Importing production helpers from an archived prototype directory.
- Keeping app logic in notebooks and calling into the notebook from callbacks.

### `dash_app/app.py`

Belongs here:

- Dash object creation.
- Top-level `server = app.server` exposure.
- Server hook registration.
- JSON/API route registration where needed.
- The explicit route table mapping paths to page modules.
- App shell rendering around the selected page.
- Callback registration calls for page modules.
- Very small app-wide callbacks, such as navigation toggles.

Should not belong here:

- Page-specific layouts.
- Model mathematics or domain rules.
- Plotly figure construction.
- Large callback bodies.
- Environment parsing.

Examples:

- `ROUTES = {"/": home, "/section/model": section_model}`
- `page.layout()` inside a shared shell.
- `section_model.register_callbacks(app)`

Anti-patterns to avoid:

- Defining every page as a nested function inside `app.py`.
- Adding conditionals in `app.py` for individual model controls.

### `dash_app/config.py`

Belongs here:

- Environment-backed configuration.
- Small parsing helpers for flags and modes.
- Deployment or layout options consumed by the app shell or server hooks.

Should not belong here:

- Page copy.
- Domain constants.
- Plotly figure settings.
- Secrets hard-coded in source.

Examples:

- `DASH_LAYOUT_MODE`
- `FORCE_HTTPS`
- `DASH_DEBUG`

Anti-patterns to avoid:

- Scattering `os.environ` reads through page modules.
- Using commented-out code blocks to switch between local and production
  behaviour.

### `dash_app/pages/`

Belongs here:

- Page-level `layout()` functions.
- Page-specific helper functions that assemble readable layout sections.
- Page-specific callbacks and `register_callbacks(app)`.
- Page-specific state wiring such as `dcc.Store` or `dcc.Interval`.

Should not belong here:

- Long explanatory prose that can live in `content/`.
- Reusable domain calculations that can live in `models/`.
- Large reusable Plotly builders that can live in `figures/`.
- Generic UI primitives that can live in `components/`.

Examples:

```text
dash_app/pages/home.py
dash_app/pages/continuous/index.py
dash_app/pages/continuous/logistic_growth.py
dash_app/pages/discrete/logistic_map.py
```

Anti-patterns to avoid:

- Page files that become a dumping ground for prose, calculations, Plotly
  traces, and callback state transitions.
- Adding page-specific navigation or footer elements instead of using the app
  shell.

### `dash_app/components/`

Belongs here:

- Reusable structural UI helpers.
- App shell, navigation, footer, page headers, card primitives, markdown blocks,
  graph wrappers, controls, and shared widget wrappers.
- Shared browser/component contracts expressed as markup and data attributes.
- Shared graph config used by all `dcc.Graph` instances.

Should not belong here:

- Model mathematics.
- Page-specific copy.
- One-off wrappers that cannot plausibly be reused.
- Plotly figure construction, except graph container configuration.

Examples:

```text
dash_app/components/layout.py
dash_app/components/navigation.py
dash_app/components/model_page.py
dash_app/components/plotly_config.py
dash_app/components/phase_portrait.py
```

Anti-patterns to avoid:

- Hiding page-specific behaviour inside a component just to shorten a page file.
- Generic components with hard-coded model names or route assumptions.

### `dash_app/content/`

Belongs here:

- Markdown strings, structured text, equations, labels, references, source
  notes, module lists, and page metadata.
- Section-level content packages when a section has several pages.

Should not belong here:

- Dash component trees.
- Computation.
- Callback logic.
- Plotly figure code.

Examples:

```text
dash_app/content/home.py
dash_app/content/continuous/logistic_growth.py
dash_app/content/discrete/logistic_map.py
dash_app/content/interacting/general_2d_systems.py
```

Anti-patterns to avoid:

- Long prose embedded directly in callback-heavy page modules.
- Content modules importing Dash or Plotly.

### `dash_app/figures/`

Belongs here:

- Plotly figure-builder functions.
- Shared figure palette, stability colours, and base layout helpers.
- Domain-specific figure modules grouped by section or feature.

Should not belong here:

- Dash layout assembly.
- Long content strings.
- Input validation policy that belongs to the model layer.
- Heavy domain logic that should be reusable without Plotly.

Examples:

```text
dash_app/figures/common.py
dash_app/figures/continuous/harvesting.py
dash_app/figures/discrete/logistic_map.py
```

Anti-patterns to avoid:

- Repeating the same Plotly layout settings in every page.
- Building traces directly inside callbacks when a named builder would clarify
  the contract.

### `dash_app/models/`

Belongs here:

- Reusable domain models and domain analysis helpers.
- Dataclasses for domain results.
- Parameter schemas and validation.
- Registries of supported systems or model specs.
- Numerical integration, simulation, sampling, orbit generation, analysis, and
  payload builders.

Should not belong here:

- Dash components.
- Plotly styling.
- Page copy.
- Imports from notebooks or sandbox packages.

Examples:

```text
dash_app/models/discrete/logistic_map.py
dash_app/models/phase_portrait/systems.py
dash_app/models/phase_portrait/parameters.py
dash_app/models/phase_portrait/payloads.py
dash_app/models/phase_portrait/integration.py
```

Anti-patterns to avoid:

- Domain helpers returning Dash components.
- Production model code depending on exploratory folders.
- Callback bodies performing validation, simulation, and formatting directly.

### `dash_app/assets/`

Belongs here:

- Dash auto-loaded CSS.
- Static images and media used by the app.
- Lightweight client-side scripts for browser-only interaction.

Should not belong here:

- Authoritative domain calculations that must be tested server-side.
- Large generated artifacts unless they are intentional static assets.
- Unscoped CSS changes that accidentally reshape unrelated pages.

Examples:

```text
dash_app/assets/styles.css
dash_app/assets/phase_portrait_widget.js
dash_app/assets/images/
```

Anti-patterns to avoid:

- CSS classes named only for colour or visual appearance, such as
  `big-green-box`, when the class should describe role.
- Browser scripts that silently duplicate server-side validation or scientific
  logic.

### `dash_app/routes/`

Belongs here:

- Flask routes or API endpoints that support app widgets.
- JSON contracts consumed by browser-side components.
- Endpoint-level request parsing and error responses.

Should not belong here:

- Page layout code.
- Long-running domain logic that belongs in `models/`.
- Business rules duplicated from validators.

Examples:

```text
dash_app/routes/phase_portrait.py
```

Anti-patterns to avoid:

- Registering endpoint logic inline in `app.py` once it becomes non-trivial.
- Returning loosely shaped payloads without tests.

### `dash_app/tests/`

Belongs here:

- Tests that mirror the app's responsibilities.
- Routing tests, layout smoke tests, component markup tests, figure tests,
  model/domain tests, validation tests, endpoint contract tests, and focused
  browser lifecycle tests.

Should not belong here:

- Tests that require modifying notebooks.
- Broad end-to-end tests for every small visual detail.
- Slow browser tests when a model, figure, or component test would cover the
  behaviour more directly.

Examples:

```text
dash_app/tests/test_routing.py
dash_app/tests/test_navigation.py
dash_app/tests/test_figures_common.py
dash_app/tests/test_phase_portrait_contract.py
dash_app/tests/test_server_hooks.py
```

Anti-patterns to avoid:

- Only testing that imports succeed.
- Testing domain behaviour through a browser when a direct model test is more
  stable and faster.

## 3. Page Architecture

Recommended pattern:

- Each page module exposes a `layout()` function.
- Page modules may expose `register_callbacks(app)` when they own callbacks.
- `app.py` owns the URL-to-page mapping and wraps each page in a shared shell.
- Page helpers should split layout into named sections when it improves
  readability.
- Page-specific callbacks should stay close to the page or feature they
  support.

Generic page shape:

```python
from dash import Input, Output, dcc, html

from dash_app.components.model_page import markdown_block, model_page_title
from dash_app.content.section import feature as content
from dash_app.figures.section.feature import make_main_figure
from dash_app.models.section.feature import DEFAULT_PARAMETERS


def _interactive_section(*children):
    return html.Section(className="feature-interactive-section", children=list(children))


def layout():
    return [
        html.Div(
            className="model-page section-model-page feature-page",
            children=[
                model_page_title(content.TITLE),
                # hero, prose, controls, figures
            ],
        )
    ]


def update_feature(parameter):
    value = float(parameter)
    return make_main_figure(value), markdown_block("Updated interpretation")


def register_callbacks(app):
    app.callback(
        Output("feature-figure", "figure"),
        Output("feature-interpretation", "children"),
        Input("feature-slider", "value"),
    )(update_feature)
```

Keep pages readable:

- Use content constants instead of inline prose blocks.
- Use figure builders instead of inline Plotly trace construction.
- Use model helpers for validation, summaries, and simulation.
- Keep callback bodies short enough that input coercion, validation, helper
  calls, and returned payloads are obvious.
- Split page layout into helper functions when a section has a clear name or
  repeated shape.

Landing pages and detail pages should differ:

- Landing pages introduce a section, list available modules, and provide
  navigation. They can use simpler cards and overview copy.
- Model/detail pages own a specific interactive experience. They usually have a
  title, hero, focused prose, controls, dynamic interpretation, and figures.
- Landing pages should not compress all detail-page derivations into one long
  overview.

Avoid:

- Large callback bodies inside `app.py`.
- Hidden route side effects in page modules.
- Page files that require scrolling through hundreds of lines before finding
  the layout or callback contract.

## 4. Component Architecture

Reusable components provide structural consistency. They should make pages
easier to read without hiding page-specific intent.

Recommended shared components:

- App shells and page wrappers.
- Navigation and footer.
- Page titles and headers.
- Hero cards and content cards.
- Markdown blocks with MathJax options.
- External-link markdown blocks.
- Control rows and standard sliders.
- Plot cards and graph wrappers.
- Widget roots with stable data attributes.

Recommended component rules:

- Components should describe structure, not domain mathematics.
- Components should accept content and configuration through parameters.
- Components should use stable semantic CSS class hooks.
- Shared graph wrappers should apply shared Plotly config.
- A page-specific wrapper can live in a page module until two or more pages need
  it.

Naming conventions:

- Prefer semantic class names such as `model-page`, `model-controls-card`,
  `model-plot-card`, `interactive-section-band`, and `phase-portrait-widget`.
- Add page-specific hooks alongside generic hooks, for example
  `discrete-interactive-section logistic-map-interactive-section`.
- Use modifier classes for variants, for example
  `model-interpretation-card--full`.

Avoid:

- Putting model calculations in a component helper.
- Generic components that contain page-specific copy.
- Visual-only class names that make future refactors harder.

## 5. Content Architecture

Teaching copy, explanatory prose, equations, interpretation text, references,
and source notes should live outside page code where possible.

Recommended pattern:

- Store long Markdown strings in `dash_app/content/`.
- Group content by section and page once a section grows beyond one file.
- Keep equations and prose close to their page's content module, not inside
  callbacks.
- Use structured constants for module cards, route labels, references, hero
  metadata, and page sections.
- Let pages compose content; do not make content modules render Dash layouts.

This keeps model pages focused on layout composition and interaction contracts.
It also makes copy review easier because prose can be edited without threading
through callback logic.

Avoid:

- Multi-paragraph strings embedded directly inside `layout()`.
- Content modules importing Dash components.
- Callback functions that build long explanatory Markdown strings when they
  should select from named content snippets or call a small formatter.

## 6. Figure Architecture

Plotly code should be organised around named figure-builder functions.

Recommended pattern:

- Put shared palette, stability colours, and layout helpers in
  `dash_app/figures/common.py`.
- Put feature-specific builders in `dash_app/figures/<section>/<feature>.py`.
- Have page callbacks call figure builders.
- Keep axis labels plain and readable.
- Use a shared `dcc.Graph` config through components such as `plot_card`.
- Keep interaction policy consistent: if users should interact through Dash
  controls, disable accidental Plotly zoom/pan/select tools globally.

Generic example:

```python
def make_response_figure(parameter: float) -> go.Figure:
    data = response_curve(parameter)
    fig = go.Figure()
    fig.add_trace(...)
    return apply_plotly_layout(fig, x_title="Input", y_title="Response")
```

Keep numerical logic separate where possible:

- Model modules should prepare or validate reusable data.
- Figure modules should translate prepared data into Plotly traces, labels,
  colours, ranges, and layout.
- Page callbacks should decide which figure builder to call, not how the
  figure is drawn.

Avoid:

- Copying Plotly layout settings into every page.
- Letting figure builders perform unrelated validation or business decisions.
- Building large figures inline inside callbacks.

## 7. Model/Domain Logic Architecture

Reusable mathematical, scientific, or domain-specific logic belongs in
`dash_app/models/` or another app-native domain package. Refer to these as
domain models, regardless of the subject matter.

Recommended model responsibilities:

- Registries of supported systems, models, examples, or scenarios.
- Dataclasses for domain results and payload-friendly summaries.
- Parameter schemas, defaults, ranges, and validation.
- Analysis helpers such as fixed points, classifications, summaries, metrics,
  or derived quantities.
- Numerical integration, simulation, iteration, sampling, and root finding.
- Payload builders for browser widgets or API endpoints.
- Clear error messages for invalid inputs.

Recommended pattern:

```python
@dataclass(frozen=True)
class ScenarioSummary:
    key: str
    metric: float
    classification: str


def validate_parameters(raw: Mapping[str, object] | None) -> dict[str, float]:
    ...


def summarise_scenario(key: str, parameters: Mapping[str, float]) -> ScenarioSummary:
    ...
```

Avoid:

- Domain helpers returning Dash components.
- Production code importing from notebooks, archived apps, or sandbox folders.
- Reimplementing validation in callbacks, endpoint handlers, and browser code
  independently.
- Creating a generic framework before repeated patterns are proven.

## 8. Assets And Styling Architecture

Dash auto-loads files in `dash_app/assets/`. Use that convention deliberately.

Recommended CSS pattern:

- Keep global CSS in `dash_app/assets/styles.css`.
- Organise CSS into labelled sections such as design tokens, base styles,
  header, navigation, page shell, cards, model pages, widgets, production mode,
  and responsive rules.
- Define reusable design tokens on `:root`.
- Scope production-only or development-only layout rules under mode classes
  such as `.app-shell--production`.
- Prefer semantic CSS class hooks over brittle structural selectors.
- Use page-specific hooks when a page needs tailored spacing or layout.

Recommended layout grammar:

- Use one outlined interactive section for a coherent control/figure module.
- Inside that section, flatten inner cards where possible so the module reads as
  one interaction surface.
- Avoid deeply nested cards inside cards.
- Use header bands for substantial interactive sections when the title should
  frame controls, interpretation, and plots.

Recommended browser-side script pattern:

- Use asset scripts for lightweight browser behaviour, canvas rendering,
  lifecycle management, event binding, and display-only interactions.
- Treat data attributes as the contract between Dash markup and browser code.
- Fetch server-side JSON endpoints for authoritative computed payloads.
- Keep server-side Python responsible for validation and scientific/domain
  calculations unless there is a carefully tested client-side reason.

Avoid:

- Unscoped CSS changes that reshape unrelated pages.
- Page-specific visual hacks added to generic components.
- Browser scripts that become a second, untested implementation of domain
  logic.

## 9. Callback Architecture

Callbacks should be close to the page or feature they support. They should be
small orchestration functions, not all-in-one business logic units.

Recommended callback structure:

- Name update functions after the feature output, for example
  `update_feature_explorer`, `update_playback_state`, or
  `update_selected_summary`.
- Register callbacks in a page-level `register_callbacks(app)` function.
- Coerce and validate inputs before computation.
- Delegate model calculations to `models/`.
- Delegate figure construction to `figures/`.
- Return clearly shaped outputs in the same order as the callback declaration.
- Use `dcc.Store` for explicit per-page UI state when needed.
- Avoid hidden mutable global state.

Generic callback:

```python
def update_summary(raw_parameter):
    parameter = validate_parameter(raw_parameter)
    summary = summarise_domain_state(parameter)
    return make_summary_figure(summary), format_summary(summary)
```

Clear input/output contracts:

- Component IDs should be page-scoped, for example `feature-parameter-slider`
  rather than `slider`.
- Output IDs should describe their role, for example `feature-current-summary`
  or `feature-main-figure`.
- Multi-output callbacks should return tuples whose order is obvious from the
  registration.

Avoid:

- Callbacks that validate, simulate, classify, build Plotly traces, and format
  long text all at once.
- Callback functions that depend on side effects from previous user sessions.
- Generic callback frameworks before several pages prove the same pattern.

## 10. Testing Architecture

Tests should map to architectural responsibilities.

Recommended tests:

- Page rendering: known routes render the intended shell, title, and page root.
- Routing: unknown routes render a dedicated not-found page rather than silently
  falling back.
- Component markup: shared navigation, shells, graph wrappers, and widget roots
  emit stable class names, IDs, data attributes, and configs.
- Figure builders: shared palette/layout conventions, trace counts, axis
  labels, ranges, and interaction settings.
- Domain analysis: fixed points, classifications, summaries, simulations,
  integrations, or equivalent domain behaviours.
- Parameter validation: defaults, bounds, unknown parameters, non-finite
  values, and clear exceptions.
- Callback payload shapes: update functions return expected components,
  figures, stores, styles, or JSON-ready values.
- Endpoint contracts: API routes validate input and return versioned,
  predictable payloads.
- Browser lifecycle tests: use only where browser behaviour is genuinely part
  of the feature, such as a custom canvas widget, resize lifecycle, or client
  event queue.

Recommended testing style:

- Prefer direct unit tests for models and figure builders.
- Prefer layout/component tree tests for Dash markup contracts.
- Use browser tests sparingly for behaviour that cannot be covered reliably at
  lower layers.
- Include isolation tests when production code must not import from prototypes
  or sandbox packages.

Avoid:

- Relying only on full browser tests for all confidence.
- Testing implementation details that make harmless layout refactors painful.
- Leaving extracted model helpers untested while only testing the page around
  them.

## 11. Refactoring Checklist For Another Dash App

Use this checklist when moving an unrelated Dash app toward this architecture.

- Move route/page code out of `app.py`.
- Create an explicit route table in `app.py`.
- Make `app.py` responsible only for app creation, shell rendering, callback
  registration, and app-wide callbacks.
- Create `pages/` modules with `layout()` functions.
- Add page-level `register_callbacks(app)` functions for page-specific
  callbacks.
- Extract reusable shells, navigation, cards, markdown blocks, controls, and
  graph wrappers into `components/`.
- Move explanatory prose, equations, references, labels, and module metadata
  into `content/`.
- Move Plotly construction into `figures/` modules.
- Add shared Plotly palette, layout, and graph interaction config.
- Move domain calculations, registries, schemas, validation, simulations, and
  payload builders into `models/`.
- Centralise environment-backed settings in `config.py`.
- Move deployment/server hooks into `server_hooks.py` or a similarly named
  server module.
- Move Flask/JSON endpoints into `routes/` once they become non-trivial.
- Consolidate CSS hooks in `assets/styles.css`.
- Rename visual-only CSS classes to semantic role-based names.
- Replace nested card stacks with one coherent interactive section where
  appropriate.
- Add tests around each extracted responsibility.
- Add route tests for known and unknown paths.
- Add component tests for shared markup and graph config.
- Add figure tests for shared layout and feature-specific builders.
- Add model tests for validation and domain behaviour.
- Add endpoint contract tests for JSON routes.
- Identify code that should remain app-specific, such as page order, domain
  wording, section names, and bespoke interactions.

## 12. Anti-Patterns

This architecture is designed to avoid:

- `app.py` containing all routes, layouts, callbacks, plotting, and domain
  logic.
- Long prose embedded directly in page layout files.
- Plotting code duplicated across pages.
- Callbacks that perform validation, simulation, plotting, and text formatting
  all at once.
- Production app code importing from notebooks, archived apps, sandbox folders,
  or prototype packages.
- CSS classes named only for visual appearance rather than semantic role.
- Deeply nested cards inside cards inside cards.
- Page-specific hacks leaking into generic components.
- Browser scripts duplicating server-side validation or calculations without a
  tested contract.
- Unversioned JSON payloads for custom browser widgets.
- Environment-specific behaviour controlled by commented code instead of
  configuration.
- Generic abstraction frameworks introduced before the app has repeated,
  stable patterns.
