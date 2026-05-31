# Phase 9 Legacy Closeout Audit

Initial audit date: 2026-05-31
Phase 9 closeout update: 2026-06-01

This audit is intentionally conservative. It reports likely stale, superseded,
duplicated, or legacy-owned material after the Phase 9 layout and styling work.
It does not delete production files and does not treat every unreferenced symbol
as safe to remove.

## 1. Executive Summary

The production app is now clearly centered on the Dash shell, the consolidated
Equations page, and the Canvas-backed Simulation page. The largest remaining
cleanup opportunities are legacy compatibility surfaces that were intentionally
kept while Phase 6-9 work stabilized:

- Retained Plotly/Matplotlib graph helpers and model plotting methods are not
  used by the normal Simulation route, but are still documented as possible
  future analytical/fallback paths.
- The old `/lagrangian` and `/hamiltonian` page implementations in
  `app/pages/math.py` appear superseded by branch-specific renders of the
  consolidated Equations page.
- Hidden Simulation controls remain for initial-state presets and integrator
  policy selection. They are callback-active even when hidden.
- The old footer-owned Run Simulation path and test-only model-card component
  path were identified by the initial audit and removed in the conservative
  Phase 9 cleanup pass.
- The CSS file has a useful token structure, but still contains generic legacy
  selectors and a Legacy quarantine block that should be removed or re-homed in
  a future pass.
- Production code does not appear to import from `development/` or `legacy/`.
  That boundary is healthy.

Recommended posture: treat the first focused UI compatibility cleanup as done,
then handle plotting/fallback, legacy math content, and CSS quarantine items in
separate manual-decision passes. Do not remove legacy routes until the
route-preservation decision changes.

## Phase 9 Closeout Status

This report now serves as both the original conservative audit trail and the
Phase 9 closeout status record. Findings tables below still preserve the first
audit snapshot; use this status section to distinguish resolved work from items
that remain deferred or intentionally retained.

Resolved in Phase 9:

- The old footer-owned Run Simulation helper branch was removed. The footer is
  a normal-flow site footer, and Run simulation remains owned by the Simulation
  controls/sidebar.
- The legacy model-card / pre-Canvas Simulation intro component path was
  removed where it was only preserved by tests.
- CSS selectors tied directly to the removed footer-owned Run path and removed
  model-card path were deleted during the conservative cleanup pass.
- Explicit Flask server hooks and config-driven `FORCE_HTTPS` ownership were
  added with focused tests.
- Temporary Phase 8 diagnostic UI was removed from normal user-facing flow or
  kept only as hidden/non-user-facing ownership where runtime contracts still
  require it.
- The Simulation page layout, responsive modes, sidebar-owned Run dock, status
  presentation, and diagnostic presentation were consolidated without changing
  solver, result, or Canvas contracts.

Deferred after Phase 9:

- Legacy math page modules, old long-form Markdown, and reference helpers remain
  candidates for a later content/archive decision.
- Legacy CSS quarantine items, broad generic selectors, compatibility tokens,
  and uncertain dynamic selectors remain for a later CSS cleanup pass.
- `assets/nav-bar.js` math-page scroll behavior and `assets/scroll.js` remain
  deferred because they may still support preserved navigation or page behavior.
- Plotly/Matplotlib helper paths and model plotting methods remain deferred
  pending a product decision about analytical output suites or fallback views.
- Long-duration numerical validation, comparison workspace concepts, and new
  chaos diagnostics remain outside the Phase 9 closeout.

Intentionally retained:

- `/lagrangian` and `/hamiltonian` routes remain preserved legacy-compatible
  route surfaces backed by the consolidated Equations page behavior.
- Canvas renderer assets, payload contracts, and simulation runtime logic remain
  untouched.
- Hidden integrator-policy ownership and hidden initial-state preset machinery
  remain because callbacks and solver-policy/state ownership still depend on
  them, even when normal UI no longer exposes them.
- `development/` and `legacy/` remain reference/history areas and are not
  treated as production runtime imports.

Needs manual decision in Phase 10 or later:

- Decide whether retained Plotly/Matplotlib plotting helpers become product
  output surfaces, compatibility APIs, or removal candidates.
- Decide whether hidden initial-state presets should become a real user-facing
  feature, remain hidden machinery, or be removed with callback updates.
- Decide whether integrator-policy ownership should be renamed, rehomed, or
  formalized as configuration rather than hidden UI state.
- Decide whether old math Markdown and legacy reference helpers should be
  archived, migrated into the consolidated Equations document, or removed.
- Decide whether `assets/scroll.js` and old math-page scrolling behavior are
  still required by current navigation.

## 2. Audit Method

Evidence gathered:

- `rg --files` and `git ls-files` to separate tracked files from ignored local
  reference material.
- Import and symbol scans across `app/`, `src/`, `tests/`, `assets/`, and
  documentation.
- Route registry inspection in `app/pages/registry.py` and route metadata in
  `app/content/routes.py`.
- Dash ID and `className` reference scans across Python, JavaScript, CSS, tests,
  and docs.
- CSS selector and CSS custom-property scans in `assets/styles.css`.
- Static asset reference scans for images, Markdown files, and JavaScript.
- Stale wording scans for TODOs, temporary/Phase references, workbench mentions,
  Plotly/Matplotlib references, and legacy references.
- Existing tests were run after writing this report.

False-positive rules used:

- Dynamic Dash classes such as `simulation-status-{status}` are not treated as
  unused only because they are assembled dynamically.
- Dash-generated classes such as `Select-control`, `rc-slider-*`, and
  `dash-slider-*` are treated as dynamic/uncertain.
- Legacy `/lagrangian` and `/hamiltonian` routes are intentionally preserved by
  roadmap policy.
- `development/` and `legacy/` are reference/history areas, not production
  runtime modules.

## 3. Findings By Area

### Python/App Structure

| Finding | Classification | Evidence | Notes |
| --- | --- | --- | --- |
| `app/pages/math.py` legacy math-page layouts | LIKELY REMOVE | `app/pages/registry.py` maps `/lagrangian` and `/hamiltonian` to `app.pages.equations.get_euler_lagrange_layout` and `get_hamiltonian_layout`, not to `app.pages.math`. Tests still instantiate `math.lagrangian_layout()` and `math.hamiltonian_layout()`. | This looks superseded by the consolidated Equations page. Remove only after confirming the old long Markdown pages are no longer needed. |
| `app/content/math.py` and `assets/MarkdownScripts/mathematics_lagrangian.txt` / `mathematics_hamiltonian.txt` | LIKELY REMOVE | Used by `app/pages/math.py`, `app/components/references.py`, and tests; not used by the current route registry. | Coupled to the previous finding. The Markdown may be kept as archival source if content not fully migrated. |
| `app/components/references.py` | LIKELY REMOVE | Only used by `app/pages/math.py` and tests. Current Equations page does not call `get_references_section`. | Remove or re-home if references return to the new Equations document. |
| `app/components/cards.py` plus `MarkdownCopy`, `LinkCopy`, `ModelCard` in `app/content/simulation.py` | LIKELY REMOVE | `render_model_card` is only used by `tests/unit/test_components.py`; dataclasses are otherwise only imported by `cards.py` or tests. | Looks like a leftover from the pre-Canvas Simulation intro/model-card UI. |
| `app/components/footer.py:get_footer_section_main(include_button=True)` and `get_common_footer(include_button=True)` | LIKELY REMOVE | Production pages call `get_footer_section()` through `get_footer_wrapper`. The include-button path creates `id="submit-val"` in the footer, which conflicts conceptually with Phase 9 sidebar ownership. Tests still assert `get_footer_section_main()` returns a component. | Remove after updating tests. Keep `get_footer_section()` and the normal `site-footer` path. |
| `src/double_pendulum/app_functions.py` compatibility wrapper | NEEDS MANUAL DECISION | Only direct tracked reference is `tests/integration/test_compatibility_imports.py`. It re-exports plotting helpers and validation constants. | Could be removed if compatibility API is no longer public. If external notebooks/users rely on it, keep and document as compatibility. |
| `src/double_pendulum/plotting/helpers.py` | NEEDS MANUAL DECISION | Used by `src/double_pendulum/app_functions.py`; not used by normal Simulation callbacks. Documentation says Plotly/Matplotlib helpers are retained for future analytical/fallback paths. | Do not remove until the project decides whether retained Plotly inspection is still a Phase 10 candidate. |
| `app/components/figure_style.py` | NEEDS MANUAL DECISION | Only used by `tests/unit/test_components.py`; no production import found. | It is a small Plotly style helper. Remove with plotting cleanup if fallback path is dropped. |
| Plotting methods in model classes: `time_graph`, `phase_path`, `animate_pendulum` | NEEDS MANUAL DECISION | Methods exist in both `src/double_pendulum/models/lagrangian.py` and `src/double_pendulum/models/hamiltonian.py`. Normal Simulation callback builds Canvas payloads and does not call them. | Higher-risk removal because these methods live inside model classes and depend on Plotly/Matplotlib imports. Defer to plotting/fallback decision. |
| `odeint` integration path | KEEP | Tests cover partial metadata for `odeint`; docs explicitly mention older `odeint` partial metadata. | Looks old, but it is tested and intentionally documented. |
| Legacy route metadata for `/lagrangian` and `/hamiltonian` | KEEP | `ROADMAP.md` says legacy routes are preserved. `PUBLIC_ROUTE_ITEMS` includes both. | Keep routes even if their backing layout continues to be the consolidated Equations page. |

### Callbacks/Pages/Components/Content

| Finding | Classification | Evidence | Notes |
| --- | --- | --- | --- |
| Hidden Initial State preset dropdown and callbacks | NEEDS MANUAL DECISION | `app/components/simulation_controls.py` still renders `initial-state-preset` inside `initial-state-preset-hidden`; `app/callbacks/simulation.py` registers `apply_initial_state_preset`; tests assert hidden preset behavior. | Visible UX was removed, but hidden callback machinery remains. Decide whether presets are deferred feature infrastructure or stale. |
| Hidden integrator-policy dropdown | KEEP BUT RENAME/REHOME | `INTEGRATOR_POLICY_ID` remains hidden in controls; callbacks use it to choose solver policy; renderer uses it for stale detection; docs still call it a temporary Phase 8 selector. | The solver-policy mechanism is useful, but the hidden UI/control ownership should be renamed/re-homed away from “temporary selector” language. |
| Diagnostics shell hidden in Run dock | KEEP | Diagnostics content is hidden from normal UI but still used for callback-owned debug/status rendering. Tests assert `Show diagnostics` is absent while hidden targets exist. | Keep unless diagnostics are fully removed or moved to an explicit debug mode. |
| `app/components/graphs.py` old Plotly graph containers | NEEDS MANUAL DECISION | Helpers generate `pendulum-animation`, `phase-graph`, and `time-graph` IDs. Normal Simulation layout tests assert those IDs are absent from the active page. | Coupled to plotting/fallback decision. Safe to remove only if retained Plotly fallback is formally dropped. |
| `app/content/simulation.py` unused constants: `MODEL_SYSTEM_TITLE`, `GRAVITY_LABEL`, `INITIAL_STATE_PRESET_LABEL`, `INITIAL_STATE_PRESET_PLACEHOLDER`, `RUN_SECTION_TITLE`, `TRACE_ANIMATION_TITLE`, `PHASE_PORTRAIT_TITLE`, `TIME_GRAPH_TITLE` | LIKELY REMOVE | No tracked production/test references except definitions. Some labels reflect removed visible UI and old Plotly graph titles. | Remove after confirming no upcoming copy work needs them. |
| `app/pages/home.py` does not use the shared app shell/header/footer | KEEP | Home is registered as the `/` route and uses a full-bleed hero page. | This is current design ownership, not stale code. |
| `app/pages/chaos.py` under-development page | KEEP | Public route remains in navigation and roadmap says future chaos work is deferred. | Keep as placeholder route. |

### CSS/Design Tokens/Styles

| Finding | Classification | CSS labels | Evidence | Notes |
| --- | --- | --- | --- | --- |
| `assets/styles.css` Legacy quarantine block | LIKELY REMOVE | UNREFERENCED SELECTOR, DYNAMIC/UNCERTAIN USAGE | Section 12 contains `.header .navbar`, `.nav-link`, `.description-*`, `.models-container`, `.simple-model`, `.compound-model`, `.footer-bar`, `.run-simulation-group`, `.info-*`, `.navbar`, `.footer-section`. Tests assert some old classes are absent from current layouts. | Remove in a dedicated CSS cleanup pass after removing old footer/cards/math-page helpers. |
| `.description-*`, `.models-container`, `.simple-model`, `.compound-model`, `.image-description`, `.model-*`, `.image-container` | LIKELY REMOVE | UNREFERENCED SELECTOR | These are produced by `app/components/cards.py`, which appears test-only. | Remove with `cards.py` if that component is deleted. |
| `.footer-bar`, `.run-simulation-group`, `.footer-text-box`, `.info-*` | LIKELY REMOVE | UNREFERENCED SELECTOR / DUPLICATED STYLE | Current production footer uses `.site-footer`, `.site-footer-link`, and `.site-footer-icon`; `get_footer_section_main` is not used by pages. | Remove with old footer-owned Run path. |
| `.header .navbar`, `.header .nav-links-container`, `.nav-link`, `.navbar`, `.footer-section` | SAFE TO REMOVE | UNREFERENCED SELECTOR | Current navigation uses `.site-header`, `.site-nav`, `.site-nav-link`, etc. No app source creates `.navbar` or `.nav-link`. | Low-risk CSS removal candidate. |
| Generic pre-Phase-9 control selectors near the Shared components section: `.inputs`, `.input-group`, `.side-bar`, `.graph-section`, `.time-graph-section`, `.button`, `.button-show` | NEEDS MANUAL DECISION | DUPLICATED STYLE / DYNAMIC/UNCERTAIN USAGE | Simulation now has page-scoped `.simulation-layout ...` rules that override many of these. Some generic classes are still emitted by Simulation components. | Do not remove casually. Either re-scope all active users or delete after visual verification. |
| `.body-chaos`, `.not-found-layout`, `.not-found-content-container`, `.custom-text` | LIKELY REMOVE | UNREFERENCED SELECTOR | Current Chaos/404 pages use `.chaos-layout`, `.chaos-content-container`, `.not-found-page`, `.not-found-panel`, etc. | Looks stale from earlier page shells. |
| `.button-show`, `.button-hide`, `.input-subtext`, `.initial-conditions-input-bottom`, `.slider-label`, `.playback-header-status` | LIKELY REMOVE | UNREFERENCED SELECTOR | Static scan found no app/test references. | Check generated Dash output before deletion; several are harmless but likely old. |
| `.Select-control`, `.dash-slider-*`, `.rc-slider-*` selectors | KEEP | DYNAMIC/UNCERTAIN USAGE | These classes are generated by Dash Dropdown/Slider internals and are not expected in Python `className` strings. | Keep unless browser inspection confirms Dash version no longer emits them. |
| Dynamic status classes: `.simulation-status-success`, `.simulation-status-stale`, `.simulation-status-failed`, `.simulation-status-cleared`, `.simulation-status-empty`, `.simulation-run-validation-*` | KEEP | DYNAMIC/UNCERTAIN USAGE | Callback code builds classes from runtime status values. Static class scanning undercounts these. | Keep. |
| Unused design tokens: `--base-font-size`, `--border-emphasis`, `--border-width`, `--focus-ring`, `--footer-surface`, `--footer-text`, `--header-text`, `--radius-*`, `--shadow-*`, `--space-*`, `--transition-standard`, success/warning/danger light tokens | KEEP BUT RENAME/REHOME | LEGACY COMPATIBILITY TOKEN | CSS variable scan found zero `var(...)` usage for these tokens in tracked `assets/styles.css`. | These may be intentional Phase 9 token foundations. Either start using them consistently or move unused foundations to a token backlog note. |
| Old `--academic-*` token system | SAFE TO REMOVE from active CSS; KEEP in ignored archive | LEGACY COMPATIBILITY TOKEN | No `--academic-*` tokens are present in tracked `assets/styles.css`. Ignored local `legacy/old_styles.css` still contains them. | Active CSS already migrated. Ignored archive can remain local reference or be deleted locally. |

### JavaScript/Canvas/Assets

| Finding | Classification | Evidence | Notes |
| --- | --- | --- | --- |
| `assets/simulation-canvas-renderer.js` | KEEP | Tests assert renderer globals, Canvas IDs, route reset behavior, and responsibility boundaries. Documentation identifies it as production renderer. | Current production asset. Do not remove or rewrite as part of cleanup. |
| `PLOTLY_FRAME_SAMPLE_STEP` name inside Canvas renderer | KEEP BUT RENAME/REHOME | Renderer uses the constant to choose sparse motion trace samples; tests assert the string exists. | The name is stale now that Canvas is primary. Rename in a focused renderer-safe pass only, with tests updated. |
| `assets/scroll.js` | NEEDS MANUAL DECISION | Defines `initializeHomePage()` but attaches to Simulation `submit-val` and scrolls to `scroll-target`. Routing callback calls `initializeHomePage()` when pathname is `/simulation`. | The name is stale, and the behavior may be redundant now that Run is sidebar-owned and the workbench is already in view. It may also attach duplicate listeners after route remounts. Needs browser check before removal. |
| `assets/nav-bar.js` hamburger behavior | KEEP | Handles click-outside, Escape, scroll-close behavior for `.site-nav-menu`. | Active after Phase 9 hamburger fixes. |
| `assets/nav-bar.js` legacy math scroll code for `lagrangian-link` / `hamiltonian-link` | LIKELY REMOVE | No current navigation source creates those IDs. | Split/remove this part while keeping hamburger behavior. |
| `assets/custom-header.html` | KEEP | Loaded by `pendulum_app.py` as `app.index_string`. | Current Dash index shell. |
| Tracked image assets in `assets/Images/` and `assets/Heros/` | KEEP | Home uses `double_pend_hero1_navy.png`; Equations uses the simple/compound model images; footer/home use `github-mark.png`; README uses `Screenshot.png` and `Models_Joint_White.png`. | No tracked image appears obviously unused. |
| Ignored local `assets/DoublePendulumImages/` and `assets/.DS_Store` | SAFE TO REMOVE locally | Local ignored asset/reference material | `git status --ignored assets` shows both ignored. They are not tracked production material. | Optional local cleanup only; no production patch needed. |

### Tests

| Finding | Classification | Evidence | Notes |
| --- | --- | --- | --- |
| Tests that preserve old math Markdown and `legacy/simulation_intro_content.md` | NEEDS MANUAL DECISION | `tests/unit/test_app_content.py` reads legacy simulation intro and old math Markdown via `MATH_PAGES`. | Useful as migration guardrails earlier; now may keep stale legacy material alive. |
| Tests that instantiate `app/pages/math.py`, `app/components/graphs.py`, `app/components/cards.py`, `app/components/figure_style.py`, and `get_footer_section_main()` | LIKELY REMOVE | `tests/unit/test_components.py` checks these helpers return Dash components. | These tests should be retired with the corresponding legacy helpers. |
| Tests asserting old Plotly output IDs are absent from active Simulation layout | KEEP | Integration tests list retired IDs and assert callbacks do not target active Plotly layout components. | These are valuable regression guards while Plotly helpers still exist. |
| Tests for hidden integrator policy and hidden preset controls | NEEDS MANUAL DECISION | Integration tests assert hidden control presence and callback behavior. | Update only after product decision on hidden controls. |
| Renderer asset text test asserting `PLOTLY_FRAME_SAMPLE_STEP` | KEEP BUT RENAME/REHOME | Test protects current renderer behavior but encodes stale naming. | Rename after renderer constant is renamed. |

### Documentation/Development/Legacy Material

| Finding | Classification | Evidence | Notes |
| --- | --- | --- | --- |
| Production code imports from `development/` or `legacy/` | KEEP | `rg` found no production imports from those areas. | Boundary is healthy. |
| `ROADMAP.md` says the temporary integrator selector remains visible | LIKELY REMOVE / UPDATE | The selector is now hidden in CSS/markup. | Documentation is stale; update when Phase 9 is formally closed. |
| `README.md` says `scroll.js` scrolls from Run Simulation to input/figures section | LIKELY REMOVE / UPDATE | Current Simulation run action is sidebar-owned; `scroll.js` behavior/name is questionable. | Update after deciding whether `scroll.js` remains. |
| `README.md` and `documentation/README.md` still say Phase 9 is active | NEEDS MANUAL DECISION | User says most of Phase 9 is complete; roadmap still marks Phase 9 active. | Do not update in this audit unless Phase 9 is formally closed. |
| `documentation/simulation-runtime/*` references temporary Phase 8 integrator selector | KEEP BUT RENAME/REHOME | These are historical runtime-stability documents. | Add a Phase 9 closeout note later instead of rewriting historical evidence. |
| `legacy/ARCHITECTURE.md` and `legacy/simulation_intro_content.md` | KEEP | Tracked historical reference by design. | Do not remove unless project decides to slim tracked history. |
| Ignored local `legacy/old_styles.css`, `legacy/requirements-old-freeze.txt`, `legacy/old_references.md`, `legacy/markdown_derivations/` | KEEP or SAFE TO REMOVE locally | These are ignored by `.gitignore`, except tracked legacy files listed above. | Treat as local reference. Not part of production runtime. |
| Ignored local `development/*` evidence directories | KEEP | `.gitignore` intentionally excludes workbench/evidence directories. | Keep as local evidence; production must not import it. |

## 4. Recommended Removal Candidates

Most conservative first-pass candidates:

1. SAFE TO REMOVE: CSS `.header .navbar`, `.header .nav-links-container`,
   `.nav-link`, `.navbar`, and `.footer-section`.
2. LIKELY REMOVE: Old footer-owned Run path:
   `get_footer_section_main(include_button=True)`, `get_common_footer(...,
   include_button=True)`, `.footer-bar`, `.run-simulation-group`,
   `.footer-text-box`, and `.info-*` styles.
3. LIKELY REMOVE: Legacy model-card component path:
   `app/components/cards.py`, `MarkdownCopy`, `LinkCopy`, `ModelCard`, and the
   related `.description-*`, `.models-container`, `.simple-model`,
   `.compound-model`, `.image-description`, `.model-*`, `.image-container`
   styles.
4. LIKELY REMOVE: Superseded long-form math page path:
   `app/pages/math.py`, `app/content/math.py`, `app/components/references.py`,
   and old Markdown files, if the consolidated Equations page is confirmed as
   canonical for `/lagrangian` and `/hamiltonian`.
5. LIKELY REMOVE: Stale `assets/nav-bar.js` smooth-scroll code for
   `lagrangian-link` and `hamiltonian-link`, while keeping hamburger behavior.

Candidates that need a product/architecture decision first:

1. Hidden initial-state preset machinery.
2. Hidden integrator-policy selector UI versus non-UI solver-policy ownership.
3. Retained Plotly/Matplotlib helpers and model plotting methods.
4. `assets/scroll.js` behavior and naming.

## 5. Items To Keep Despite Looking Old

- `/lagrangian` and `/hamiltonian` routes: intentionally preserved public
  routes.
- `assets/simulation-canvas-renderer.js`: current production renderer.
- Dynamic Simulation status and validation classes: built from runtime states.
- Dash-generated Dropdown/Slider selectors: likely generated by component
  internals.
- `odeint` metadata path: tested and documented as a partial-metadata legacy
  path.
- `development/` and `legacy/` reference material: non-production history,
  intentionally separated.
- Tracked images under `assets/Images/` and `assets/Heros/`: all have current
  README/UI references.

## 6. Manual Decisions Required

1. Should retained Plotly/Matplotlib inspection remain a Phase 10 candidate?
   If yes, keep plotting helpers but document them as dormant/fallback. If no,
   remove `app/components/graphs.py`, `app/components/figure_style.py`,
   `src/double_pendulum/plotting/`, `src/double_pendulum/app_functions.py`, and
   model plotting methods in a dedicated pass.
2. Should hidden Initial State presets be kept as deferred UX infrastructure?
   If yes, rename/document them as hidden deferred infrastructure. If no,
   remove the hidden dropdown, callbacks, preset content, tests, and renderer
   stale-input dependency if present.
3. Should the integrator-policy selector stay hidden, become config-owned, or be
   removed from UI entirely? Solver policy itself should not be removed without
   a numerical/runtime decision.
4. Should old long-form math Markdown remain as archived source material after
   the consolidated Equations page? If yes, move it under `legacy/` or
   documentation rather than keeping production app modules alive.
5. Should `assets/scroll.js` still exist now that Run is sidebar-owned and the
   workbench starts at the top of the Simulation page?
6. Should unused design tokens remain as a forward-looking token foundation, or
   should Phase 9 end with only actively used tokens?

## 7. Suggested Cleanup Order For A Future Removal Pass

1. Update roadmap/docs with a small Phase 9 closeout note and remove stale
   statements that say hidden controls are still visible.
2. Remove or re-home the footer-owned Run path and its CSS/tests.
3. Remove card/model-intro legacy components and their CSS/tests.
4. Decide whether old math pages/Markdown are archived or deleted; then remove
   `app/pages/math.py`, `app/content/math.py`, and `app/components/references.py`
   if confirmed.
5. Split `assets/nav-bar.js`: keep menu behavior, remove obsolete math-scroll
   IDs.
6. Decide the hidden preset and hidden integrator-policy path; remove or
   re-home tests and docs accordingly.
7. Make the Plotly/Matplotlib fallback decision. If removal is approved, do it
   as a separate high-signal PR because it touches model classes, dependencies,
   tests, and docs.
8. Run a CSS cleanup pass after Python/component removals so selector deletion
   is evidence-backed by the updated markup.
9. Re-run full tests and a browser smoke test for `/`, `/simulation`,
   `/equations`, `/lagrangian`, `/hamiltonian`, and `/chaos`.
