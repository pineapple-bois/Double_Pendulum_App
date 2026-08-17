# Restyle Execution Plan

> Temporary branch document.
>
> Use this file to control and record the Restyle while work is in progress on
> `feat_restyle`. It is deliberately more detailed than `ROADMAP.md`.
> At Restyle closeout, move durable architecture, workflow, and design
> decisions into their permanent owners, then remove this file unless it still
> contains unresolved work.

## 1. Control Record

| Item | Current value |
| --- | --- |
| Working branch | `feat_restyle` |
| Branch point at plan creation | `8a9f7e5` |
| Production application | `https://double-pendulum.net` |
| Visual reference | `https://population-dynamics.net` |
| New hero asset | `assets/Heros/double_pend_hero1_green.png` |
| Active roadmap phase | Restyle |
| Plan created | 2026-08-17 |
| Deployment authorised by this plan | No |

The branch point records the local Git baseline only. Before any production
release, identify and record the exact commit or platform release currently
serving `double-pendulum.net`; do not assume it is the branch point.

## 2. Purpose and Success Definition

The Restyle should give the Double Pendulum App the same recognisable
interactive-textbook language as the Population Dynamics App without changing
the mathematical model, numerical policies, callback behaviour, routes, Canvas
payload contracts, or deployment interface.

The work succeeds when:

- the app has the shared warm-white, charcoal, and green visual language;
- typography, spacing, cards, controls, header, footer, and plotting surfaces
  feel intentionally related to Population Dynamics;
- the new light green hero is legible and responsive;
- Equations remains a readable mathematical document;
- Simulation retains its established interaction and Canvas architecture;
- public routes and legacy-compatible routes still work;
- all automated tests pass;
- desktop, tablet, and mobile smoke checks pass without console or asset errors;
- a known-good production rollback target is recorded before deployment;
- no Codex-started local server is left running;
- durable decisions are documented outside this temporary file at closeout.

## 3. Safety Rules

### 3.1 Branch and change discipline

- [x] Work on `feat_restyle`, not directly on `main`.
- [ ] Confirm `git status --short` before every implementation slice.
- [ ] Preserve unrelated user changes if the worktree becomes dirty.
- [ ] Keep commits small, reviewable, and limited to one visual concern.
- [ ] Run `git diff --check` before each commit.
- [ ] Do not force-push, rewrite published history, deploy, tag, merge, or
      delete a branch unless explicitly requested.
- [ ] Do not delete the navy hero or other known-good assets during the
      Restyle; retaining them provides a fast presentation rollback.
- [ ] Do not combine scientific, numerical, or Chaos feature work with the
      Restyle.

### 3.2 Runtime and contract protections

- [ ] Preserve `pendulum_app.py`, the Flask `server` export, and the
      `Procfile` deployment entry point.
- [ ] Preserve public route paths.
- [ ] Preserve callback-bound IDs unless every layout, callback, test,
      JavaScript reference, and document owner is updated together.
- [ ] Preserve Simulation store IDs, Canvas IDs, payload schemas, and
      Python/JavaScript responsibility boundaries.
- [ ] Keep Python as the owner of mathematical and numerical truth.
- [ ] Do not introduce production imports from `development/`.
- [ ] Keep `FORCE_HTTPS` and `DASH_DEBUG` behaviour configuration-owned.
- [ ] Treat dependency removal as a separate evidence-backed slice.

### 3.3 Local server safety

- [ ] Check whether port 8050 is occupied before starting Dash.
- [ ] If occupied, identify and report the process; do not kill it blindly.
- [ ] If a temporary port is used, record it in the validation log.
- [ ] Capture the exact PID of any server started for this work.
- [ ] Stop only that exact PID.
- [ ] Verify the process has stopped before completing the validation turn.

## 4. Scope

### In scope

- semantic theme tokens and explicit base styles;
- typography and responsive type scale;
- page, surface, border, radius, shadow, and spacing rules;
- header, navigation, footer, page headers, links, and focus states;
- home hero, Explore rail, reading list, and attribution;
- Equations document styling;
- Simulation controls, status, playback, Canvas containers, and diagnostics
  presentation;
- display-only Canvas renderer colours;
- retained Plotly presentation where it remains relevant;
- generated Dash control styling;
- evidence-based removal of Bootstrap and Red Hat Display dependencies;
- reusable interactive-textbook theme boundaries and documentation;
- browser, accessibility, route, asset, and regression validation.

### Out of scope

- physics or symbolic derivation changes;
- solver-policy changes;
- callback or payload redesign;
- new Simulation functionality;
- Chaos mathematics or production Chaos implementation;
- public-route removal;
- wholesale legacy cleanup unrelated to a Restyle dependency;
- deployment-platform migration;
- large component rewrites solely to make class names match Population
  Dynamics;
- copying the entire Population Dynamics stylesheet;
- creating a cross-app package before a vendored theme has been validated.

## 5. Target Design Contract

Population Dynamics is the reference, not a stylesheet to import wholesale.
The initial contract is:

| Role | Target |
| --- | --- |
| Page background | Warm off-white, reference `#f8f7f6` |
| Primary surface | White, reference `#ffffff` |
| Muted surface | Warm pale neutral, reference `#f3f2ef` |
| Primary text | Charcoal, reference `#1f2933` |
| Muted text | Green-grey, reference `#5f6b6b` |
| Border | Warm grey, reference `#ddd8d0` |
| Accent | Deep green, reference `#00635d` |
| Accent strong | Dark green, reference `#004c47` |
| Accent soft | Pale green, reference `#e9f1ef` |
| Font stack | Helvetica Neue, Helvetica, Arial, system UI, sans-serif |
| Base type size | 16px |
| Small radius | 8px |
| Medium radius | 12px |
| Header height | 72px reference target |
| Content width | 1400px reference target |

These values should become semantic variables. Component rules should consume
roles rather than duplicate raw colour literals.

The theme must also define:

- success, warning, danger, focus, disabled, stale, and selected states;
- accessible link and focus treatment;
- Canvas grid, axes, trace, marker, and status colours;
- Plotly paper, plot, grid, axis, trace, and modebar styling;
- Dash dropdown, radio, checklist, slider, tooltip, and disabled states;
- desktop, tablet, and mobile spacing/type behaviour.

## 6. Pre-change Baseline

Complete this section before the first production-style change.

### 6.1 Source and deployment baseline

- [x] Record the starting branch SHA:
      `50cb7ed59080b73d9057685f1762813e78f83b26`
- [x] Record `origin/main` SHA:
      `8a9f7e5914a4e2a64b11589552b29604b450f4e1`
- [ ] Record the exact currently deployed commit or platform release:
- [ ] Record the deployment mechanism and authorised operator:
- [ ] Record the previous known-good release/tag/SHA for rollback:
- [ ] Confirm the production domain is healthy before implementation:
- [ ] Confirm the worktree is clean or list intentional changes:

### 6.2 Automated baseline

- [x] Run the full test suite with the supported Python 3.12 environment.
- [x] Record test command: `.venv/bin/python -m pytest`
- [x] Record pass/fail count: 174 passed
- [x] Record duration: 9.61 seconds
- [x] Record any warnings or pre-existing failures: none
- [x] Run `git diff --check`.

### 6.3 Visual and interaction baseline

Capture or record representative evidence for:

- [ ] `/`
- [ ] `/equations`
- [ ] `/simulation`
- [ ] `/chaos`
- [ ] `/lagrangian`
- [ ] `/hamiltonian`
- [ ] unknown-route/404 behaviour
- [ ] one valid simple Euler-Lagrange run
- [ ] one valid simple Hamiltonian run
- [ ] one representative compound run
- [ ] invalid-input validation
- [ ] playback, pause, reset, scrubber, axes, and grid controls
- [ ] browser console

Baseline screenshots may be kept as local evidence under an ignored
`development/` location. Do not make production code depend on them, and do
not commit large screenshot sets without an explicit decision.

## 7. Implementation Work Breakdown

Each workstream should be independently reviewable and reversible.

### Workstream 0 — Inventory and baseline

Goal: establish evidence before changing presentation.

- [ ] Complete Section 6.
- [ ] Inventory active CSS tokens and hard-coded colours.
- [ ] Identify selectors generated by Dash rather than Python `className`.
- [ ] Inventory font and Bootstrap effects on computed styles.
- [ ] Inventory display colours outside CSS, especially Canvas and Plotly.
- [ ] Identify legacy selectors that overlap active Restyle targets.
- [ ] Record current computed styles for representative components.

Validation:

- [ ] No production file changed other than planning/evidence documents.
- [ ] Baseline test and route evidence recorded.

Rollback: not applicable; this slice is read-only.

### Workstream 1 — Theme tokens and base styles

Goal: establish the shared palette and typography without redesigning layouts.

Likely owners:

- `assets/styles.css`
- `pendulum_app.py` only if font loading is changed in this slice

Tasks:

- [x] Add or adapt semantic interactive-textbook tokens.
- [x] Map existing page, panel, text, border, link, focus, and status roles.
- [x] Adopt the system font stack.
- [x] Establish explicit body background, text, line-height, selection, and
      box-sizing rules.
- [x] Remove responsive root-font downscaling.
- [x] Preserve current component layouts during the token transition.
- [x] Search for remaining active navy/blue role leaks.

Validation:

- [ ] All routes render with readable typography. The requested Home,
      Equations, and Simulation routes pass; the complete route matrix remains
      a closeout gate.
- [ ] No control loses focus, disabled, error, stale, or success distinction.
      The Run action's keyboard focus treatment was verified; full state
      coverage remains a later Simulation check.
- [x] No new horizontal overflow on Home, Equations, or Simulation at the
      inspected 1280px and 390px widths.
- [x] Targeted tests pass: 59 passed in 5.76 seconds.

Rollback:

- Revert the token/base-style commit. Do not mix this slice with structural
  layout changes.

### Workstream 2 — Shared shell

Goal: align persistent application chrome and reusable surfaces.

Likely owners:

- `assets/styles.css`
- `app/components/navigation.py`
- `app/components/shell.py`
- `app/components/footer.py`

Tasks:

- [ ] Restyle the header to a white surface with green navigation affordances.
- [ ] Align header height, content width, gutters, borders, and menu panel.
- [ ] Restyle the footer to the shared light treatment.
- [ ] Align page backgrounds, page headers, links, focus states, and cards.
- [ ] Preserve navigation labels, routes, and menu behaviour.
- [ ] Verify fixed-header offsets on every non-home route.

Validation:

- [ ] Navigation opens, closes, and identifies the current page.
- [ ] Escape/click-outside behaviour remains intact.
- [ ] Footer remains in normal document flow.
- [ ] Route changes do not create header overlap.
- [ ] Targeted shell and route tests pass.

Rollback:

- Revert the shell commit independently of tokens and page-specific styling.

### Workstream 3 — Home and green hero

Goal: promote the new hero and match the Population Dynamics home language.

Likely owners:

- `app/content/home.py`
- `app/pages/home.py`
- `assets/styles.css`
- `assets/Heros/double_pend_hero1_green.png`

Tasks:

- [ ] Change the active hero reference to
      `double_pend_hero1_green.png`.
- [ ] Replace the navy overlay with a restrained light wash.
- [ ] Use charcoal title/body text and green/muted supporting roles.
- [ ] Restyle the Explore rail as a translucent/light surface.
- [ ] Align the reading list and attribution with the shared theme.
- [ ] Keep the current home information architecture.
- [ ] Retain the navy hero as a rollback asset.
- [ ] Check focal point and crops at all target viewports.

Validation:

- [ ] Title and body remain readable over the image.
- [ ] The pendulum remains visible without competing with the copy.
- [ ] Explore links have clear hover and focus states.
- [ ] Reading and attribution remain legible.
- [ ] No content is clipped at short viewport heights.

Rollback:

- Restore the navy hero path and prior home-specific CSS commit. Because the
  old asset remains tracked, no asset recovery should be needed.

### Workstream 4 — Equations and teaching surfaces

Goal: make long-form mathematical content feel like the same textbook without
reducing readability.

Likely owners:

- `assets/styles.css`
- `app/pages/equations.py`
- shared derivation/reference components only if structural changes are
  justified

Tasks:

- [ ] Align document width, paper surface, headings, body type, callouts,
      equations, figures, references, and branch navigation.
- [ ] Preserve ordinary differential notation conventions.
- [ ] Preserve legacy route rendering through the consolidated page.
- [ ] Check wide equations and images for horizontal overflow.
- [ ] Keep MathJax output visually compatible with the new type scale.

Validation:

- [ ] `/equations`, `/lagrangian`, and `/hamiltonian` render correctly.
- [ ] Branch selection and callbacks still work.
- [ ] Display equations remain readable at mobile widths.
- [ ] Existing content and component tests pass.

Rollback:

- Revert page-scoped Equations styles; avoid mixing with global token changes.

### Workstream 5 — Simulation HTML/CSS surfaces

Goal: apply the theme without disturbing interaction or numerical state.

Likely owners:

- `assets/styles.css`
- existing Simulation components only where markup change is necessary

Tasks:

- [ ] Restyle sidebar surfaces, segmented controls, dropdowns, steppers,
      inputs, sliders, Run action, status, playback controls, panels, and
      diagnostics.
- [ ] Keep established sidebar/output layout and responsive modes.
- [ ] Preserve all callback-bound and renderer-bound IDs.
- [ ] Theme generated Dash selectors deliberately.
- [ ] Verify selected, disabled, hover, focus, invalid, stale, success, and
      failure states.
- [ ] Avoid making diagnostics or controls visually ambiguous through excessive
      minimalism.

Validation:

- [ ] Valid simple Euler-Lagrange run.
- [ ] Valid simple Hamiltonian run.
- [ ] Representative compound run.
- [ ] Invalid inputs show validation rather than a server error.
- [ ] Playback, pause, reset, scrubber, axes, and grid controls work.
- [ ] Route-away/route-back remount remains stable.
- [ ] Simulation integration and numerical tests pass.

Rollback:

- Revert Simulation-scoped CSS/markup commit. If markup changes were required,
  revert them together with their tests.

### Workstream 6 — Canvas and plotting palette

Goal: align rendered outputs while keeping rendering contracts unchanged.

Likely owners:

- `assets/simulation-canvas-renderer.js`
- `app/components/figure_style.py`
- retained plotting helpers only after confirming active ownership

Tasks:

- [ ] Replace display-only Canvas navy/blue colours with semantic charcoal,
      green, muted, grid, trace, marker, stale, and surface values.
- [ ] Do not alter payload parsing, frame selection, drawing geometry,
      playback, resize, or state logic.
- [ ] Align active Plotly fonts, backgrounds, grids, axes, and traces.
- [ ] Confirm whether retained model plotting helpers are active, dormant, or
      separately deferred.

Validation:

- [ ] Motion, angular projection, and displacement views remain distinct.
- [ ] Axes, grid, traces, markers, selected frames, and stale states remain
      readable.
- [ ] Canvas behaviour is checked after running a real simulation.
- [ ] Browser console has no renderer errors.
- [ ] Canvas payload and renderer-text tests pass.

Rollback:

- Revert the palette-only commit. Palette changes must not share a commit with
  renderer behaviour changes.

### Workstream 7 — Dependency audit

Goal: remove global styling dependencies only after replacement styles are
proven.

Likely owners:

- `pendulum_app.py`
- `requirements.txt`
- tests/documentation if dependency ownership changes

Tasks:

- [ ] Confirm there are no production `dbc` components.
- [ ] Inspect computed styles before and after removing Bootstrap.
- [ ] Remove the Bootstrap external stylesheet only after explicit resets and
      component styles cover current behaviour.
- [ ] Remove the external Red Hat Display request after the system stack is
      active.
- [ ] Remove `dash-bootstrap-components` only if imports and runtime use are
      absent and a clean environment install succeeds.
- [ ] Verify `requirements.txt` remains a top-level dependency list rather
      than a full freeze.

Validation:

- [ ] Clean-environment installation succeeds.
- [ ] App import and Flask server tests pass.
- [ ] All routes and controls retain expected layout and semantics.
- [ ] Full test suite passes.

Rollback:

- Restore the dependency, import, and external stylesheet in one revertible
  commit. Do not combine dependency removal with unrelated visual refinements.

### Workstream 8 — Reusable theme boundary

Goal: leave a repeatable starting point for future interactive textbooks.

Tasks:

- [ ] Separate shared tokens/base/shell/component rules from app-specific rules.
- [ ] Add a version label or documented theme revision.
- [ ] Document shared versus subject-specific responsibilities.
- [ ] Define reusable patterns for header, footer, page header, hero, teaching
      card, control band, plot card, status message, and reading list.
- [ ] Confirm the vendored approach in both apps before proposing packaging.
- [ ] Record candidates for a future GitHub template repository.

Validation:

- [ ] The Double Pendulum App does not import Population Dynamics code.
- [ ] Theme ownership is understandable without reading page-specific CSS.
- [ ] App-specific Simulation and Equations rules remain locally owned.

Rollback:

- Revert extraction if it obscures ownership or increases coupling. A clear
  local stylesheet is preferable to a premature abstraction.

### Workstream 9 — Documentation and closeout

Tasks:

- [ ] Update durable documentation affected by actual implementation decisions.
- [ ] Update README screenshots or setup notes only where the finished app
      requires it.
- [ ] Update the roadmap status and identify the next active phase.
- [ ] Resolve or transfer every open decision and risk in this file.
- [ ] Remove stale evidence that should not be committed.
- [ ] Remove `RESTYLE.md` after durable material has been promoted, unless an
      explicit unresolved follow-up requires it to remain.

## 8. Risk Register

| Risk | Impact | Mitigation | Rollback |
| --- | --- | --- | --- |
| Global CSS changes alter every route | High | Token-first slices; route matrix after each slice | Revert token/base commit |
| Generated Dash classes differ from assumptions | High | Inspect rendered DOM and computed styles | Revert generated-control overrides |
| Callback or renderer IDs are changed during markup cleanup | High | Preserve IDs; run callback/layout tests | Revert markup and tests together |
| Canvas colours reduce distinction or contrast | High | Palette-only commit; real-run visual check | Revert Canvas palette commit |
| Bootstrap removal changes resets or controls | High | Remove last; compare computed styles; clean install | Restore dependency and stylesheet |
| Font metrics cause wrapping or overflow | Medium | Check all breakpoints and long equations | Restore prior font while adjusting scale |
| Green hero crops poorly or lowers contrast | Medium | Test focal point and overlays at target sizes | Restore navy hero path |
| Legacy routes receive less validation | Medium | Include both routes in every final route smoke | Revert Equations styles |
| Old CSS compatibility rules conflict with new theme | Medium | Evidence-based cleanup only | Restore removed selectors |
| Browser cache serves stale CSS or hero | Medium | Verify asset request/version after deploy | Redeploy known-good release |
| Visual simplification hides status meaning | High | Test all result/status states | Revert status/control styling |
| Dependency edit breaks deployment install | High | Clean install before release | Restore prior requirements |
| Production and local commits differ | High | Record exact deployed release before rollout | Redeploy recorded known-good release |
| Local server is left running | Medium | Record PID; explicit shutdown verification | Stop exact recorded PID |
| Temporary plan becomes stale documentation | Low | Closeout checklist and removal rule | Remove after promotion |

Update this table when a new material risk is discovered.

## 9. Validation Matrix

### 9.1 Viewports

Use representative sizes and record any deliberate variation:

| Class | Reference viewport | Status |
| --- | --- | --- |
| Mobile | 390 × 844 | Pending |
| Tablet portrait | 768 × 1024 | Pending |
| Compact desktop | 1280 × 720 | Pending |
| Standard desktop | 1440 × 900 | Pending |
| Wide desktop | 1920 × 1080 | Pending |

### 9.2 Route and behaviour matrix

| Route | Visual | Responsive | Interaction | Console/assets | Status |
| --- | --- | --- | --- | --- | --- |
| `/` | Hero, copy, Explore, reading | All targets | Links/focus | No errors | Pending |
| `/equations` | Document, equations, figures | All targets | Branch selection | No errors | Pending |
| `/lagrangian` | Consolidated branch | Mobile/desktop | Route/branch | No errors | Pending |
| `/hamiltonian` | Consolidated branch | Mobile/desktop | Route/branch | No errors | Pending |
| `/simulation` | Controls and Canvas | All targets | Full simulation smoke | No errors | Pending |
| `/chaos` | Placeholder/content | Mobile/desktop | Navigation | No errors | Pending |
| Unknown route | 404 presentation | Mobile/desktop | Navigation recovery | No errors | Pending |

### 9.3 Automated validation

Minimum final commands:

```bash
python -m pytest
git diff --check
git status --short
```

Run focused tests after each slice rather than waiting for the full closeout.
Record commands and results in the log below.

## 10. Commit and Review Strategy

Preferred commit boundaries:

1. planning and baseline evidence;
2. semantic tokens and base typography;
3. shared shell;
4. home and hero;
5. Equations surfaces;
6. Simulation HTML/CSS surfaces;
7. Canvas/Plotly palette;
8. dependency cleanup;
9. reusable theme/documentation boundary;
10. final fixes and closeout.

Rules:

- [ ] One concern per commit.
- [ ] No renderer behaviour change in a palette commit.
- [ ] No dependency removal in a visual refinement commit.
- [ ] No numerical or Chaos work in this branch.
- [ ] Each commit has focused validation evidence.
- [ ] Review the complete branch diff against the recorded baseline before
      merge.

## 11. Release and Rollback Plan

This section describes required due diligence; it does not authorise deployment.

### 11.1 Pre-release gates

- [ ] Branch review is complete.
- [ ] Full tests pass.
- [ ] Route and viewport matrix passes.
- [ ] Production-like local run passes.
- [ ] Clean installation/deployment build passes if dependencies changed.
- [ ] Exact deployed baseline and known-good rollback release are recorded.
- [ ] Release operator and deployment mechanism are confirmed.
- [ ] Asset caching behaviour is understood.
- [ ] No secrets or local-only files are included.
- [ ] Final diff contains only intended Restyle work.

### 11.2 Rollout

- [ ] Prefer a preview/staging deployment if the platform supports it.
- [ ] Smoke-test the preview using the final release candidate.
- [ ] Deploy the reviewed commit, not an uncommitted working tree.
- [ ] Immediately verify home, Simulation, Equations, assets, and server health.
- [ ] Monitor application logs and user-visible errors during the initial
      release window.
- [ ] Record the new deployed release identifier and time.

### 11.3 Rollback triggers

Rollback should be preferred over live patching if production shows:

- route or app-import failure;
- missing CSS, JavaScript, hero, or Canvas assets;
- broken Simulation callbacks or renderer behaviour;
- materially unreadable content or controls;
- mobile overflow that blocks interaction;
- repeated browser-console or server errors;
- dependency/build failure;
- performance regression that prevents normal use.

### 11.4 Rollback paths

Use the narrowest safe path:

1. **Hero-only issue:** restore the navy hero reference and redeploy.
2. **CSS/theme issue:** revert the responsible atomic styling commit.
3. **Canvas presentation issue:** revert the palette-only renderer commit.
4. **Dependency/build issue:** restore the previous dependency and external
   stylesheet commit.
5. **Unknown or cross-cutting issue:** redeploy the recorded known-good
   production release/SHA.

After rollback:

- [ ] Verify the production domain and core routes.
- [ ] Confirm Simulation can run.
- [ ] Record the incident and failed release identifier.
- [ ] Reproduce locally before preparing a corrected release.

Do not delete the previous release, branch, or hero asset until the new release
has remained stable through the agreed observation period.

## 12. Decision Log

| Date | Decision | Reason | Durable owner at closeout |
| --- | --- | --- | --- |
| 2026-08-17 | Use `feat_restyle` for the work | Isolate a deployed-app redesign from `main` | Git history |
| 2026-08-17 | Make Restyle the active roadmap phase | The previous phase checklist was stale | `ROADMAP.md` |
| 2026-08-17 | Use Population Dynamics as the visual reference | Establish a recognisable family of interactive textbooks | Design/theme documentation |
| 2026-08-17 | Do not copy the full Population Dynamics stylesheet | App-specific structures and legacy selectors differ | Theme documentation |
| 2026-08-17 | Use the new light green double-pendulum hero | Match the family palette while preserving subject identity | Home content/assets |
| 2026-08-17 | Keep a vendored theme before packaging | Minimise deployment and release coupling during validation | Theme documentation |
| 2026-08-17 | Keep this plan temporary | Prevent a branch checklist from becoming stale architecture documentation | Restyle closeout |
| 2026-08-18 | Retain dark shell, home overlays, Canvas, Plotly, markup, and dependencies during Workstream 1 | Keep the token/base slice independently reviewable and respect later workstream ownership | This plan and later workstream commits |

Add decisions when they affect scope, safety, architecture, deployment, or
rollback.

## 13. Validation and Progress Log

| Date | Slice | Command/check | Result | Evidence or follow-up |
| --- | --- | --- | --- | --- |
| 2026-08-17 | Planning | Branch check | `feat_restyle` at `8a9f7e5` | Worktree clean before creating this file |
| 2026-08-17 | Planning | Green hero inspection | 1536 × 1024 PNG; visually suitable | Activation remains an implementation task |
| 2026-08-18 | Pre-change baseline | `.venv/bin/python -m pytest` | 174 passed in 9.61s | No inherited failures |
| 2026-08-18 | Workstream 1 | Focused content/import/Simulation tests | 59 passed in 5.76s | No failures |
| 2026-08-18 | Workstream 1 | Full suite | 174 passed in 7.94s | No failures |
| 2026-08-18 | Workstream 1 | Home, Equations, and Simulation at 1280px and 390px | No horizontal overflow; green focus outline verified; no browser warnings/errors | Page-specific legacy styling remains for later workstreams |

Append results; do not rewrite failed evidence into a success-only history.

## 14. Current Progress

- [x] Restyle feasibility reviewed.
- [x] Green hero created and placed under `assets/Heros/`.
- [x] `ROADMAP.md` restructured with Restyle as the active phase.
- [x] Work isolated on `feat_restyle`.
- [x] Temporary execution and rollback plan created.
- [ ] Pre-change source, deployment, test, and visual baseline recorded.
- [x] Theme tokens implemented.
- [ ] Shared shell restyled.
- [x] Green hero activated.
- [ ] Equations restyled.
- [ ] Simulation HTML/CSS surfaces restyled.
- [ ] Canvas/plotting palette updated.
- [ ] Styling dependencies audited.
- [ ] Reusable theme boundary documented.
- [ ] Full validation completed.
- [ ] Release and rollback targets recorded.
- [ ] Durable documentation updated.
- [ ] Temporary plan removed at closeout.
