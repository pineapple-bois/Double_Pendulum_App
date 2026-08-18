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

#### Workstream 0A — Home reference inventory

Status: source inventory complete on 2026-08-18. This is a Home-scoped
correction pass, not a claim that the full application inventory above is
complete.

The reference is the clean local Population Dynamics checkout on `main` at
`7c9f1b415ca661a8c4214de6402b551a1e6d1845`. This pins the source used for the
comparison; it does not establish which commit is currently deployed at
`population-dynamics.net`.

Reference owners inspected:

| Concern | Population Dynamics owner | Double Pendulum owner |
| --- | --- | --- |
| Home composition | `app/pages/home.py` | `app/pages/home.py` |
| Home copy and links | `app/content/home.py` | `app/content/home.py` |
| Tokens, Home rules, and responsive bands | `assets/styles.css` | `assets/styles.css` |
| External font/framework effects | App bootstrap and base CSS | `pendulum_app.py` and base CSS |
| Route-level structural expectations | `tests/infrastructure/test_routing.py` | `tests/unit/test_app_content.py` |

The Home route does not use Dash-generated form-control selectors. Its
`dcc.Link` components render as anchors and are styled through explicit Home
classes. Bootstrap is still loaded in Double Pendulum, but the app's later
`body`, heading, paragraph, and Home rules own the relevant Home typography.
The Red Hat Display webfont is still downloaded, but it is not selected by the
Home font cascade after Workstream 1; its remaining explicit use is outside
this Home slice. Dependency removal remains Workstream 7.

##### Structure and surface inventory

| Concern | Population Dynamics reference | Current Double Pendulum first pass | Home lock decision |
| --- | --- | --- | --- |
| Hero composition | One unboxed `.home-hero`; `.home-hero-inner` contains only copy and Explore, followed by reading and attribution siblings | Reading and attribution are nested in `.home-lower-left` as a third grid area | Permit a minimal Home-only markup adjustment so the reference flow can be expressed without layout hacks; preserve content, routes, and information architecture |
| Hero wash | One left-to-right white gradient over the artwork | Two gradients, including a strong lower wash, with a separate mobile wash/crop | Match the restrained reference wash and centered crop, then verify contrast against the Double Pendulum artwork |
| Horizontal rhythm | `clamp(20px, 3vw, 40px)`; 38.4px at 1280px and 20px at 390px | `clamp(20px, 5vw, 72px)`; 64px at 1280px and 20px at 390px | Use a Home-scoped reference gutter without changing the shared shell token |
| Explore surface | `rgba(255,255,255,0.36)`, 14px blur, 12px radius, restrained floating shadow | `rgba(255,255,255,0.86)`, 12px blur, 12px radius, floating shadow | Reduce opacity to let the artwork read; retain the reference's single intentional panel |
| Explore rows | Transparent at rest and hover; no visible separators or row boxes; only the number turns green on hover | Top separators, padded inset rows, pale-green hover boxes, and green title/number states | Remove the extra row-box treatment; keep an explicit accessible focus-visible ring |
| Further reading | Transparent and unboxed; its inner wrapper carries width only | Translucent white bordered card with radius, shadow, blur, and padding | Remove the extra box and align it to the hero's reference content width |
| Reading links | Charcoal at rest; dark green and underlined on hover | Green at rest; dark green and underlined on hover | Match the reference rest and hover states; retain keyboard focus visibility |
| Attribution | Plain muted text plus a separate icon-only link, absolutely positioned; no surface | The complete attribution is one bordered pill link | Match the unboxed reference treatment; keep the repository target and accessible icon alternative |
| Responsive structure | Two-column desktop; single-column at 1100px; two-column Explore until 760px | Single-column at 1200px; single-column Explore at 900px | Adopt the reference Home breakpoints without changing shared shell or other pages |

##### Source-resolved Home typography inventory

The pixel values below resolve each codebase's CSS at the two required
validation widths with a 16px root. They are implementation targets for the
Home correction; browser-computed values and screenshots remain the
acceptance evidence.

| Element | Population at 1280px | Double first pass at 1280px | Population at 390px | Double first pass at 390px |
| --- | ---: | ---: | ---: | ---: |
| Hero title | 53.12px | 76.8px | 40px | 51.2px |
| Hero description | 17.28px | 19.2px | 16.8px | 18px |
| Hero note | 14.72px | 16px | 15.68px | 16px |
| Explore heading | 15.68px | 24px | 16.8px | 24px |
| Explore number | 15.04px | 18px | 16.8px | 18px |
| Explore title | 16.32px | 18px | 18.24px | 18px |
| Explore description | 14.08px | 14px | 15.68px | 14px |
| Further-reading heading | 12.8px | 14px | 14.4px | 14px |
| Reading title | 13.76px | 16px | 16px | 16px |
| Reading role | 12.16px | 14px | 13.76px | 14px |

Weight is part of the drift as well as size. Population Dynamics leaves the
hero description and note at normal body weight, uses weight 600 for Explore
descriptions and reading roles, and compresses the Explore and reading type in
the 1024–1440px desktop/laptop band. Double Pendulum currently makes the hero
copy heavier while making the smaller supporting copy lighter.

Inventory outcomes:

- [x] Pin the exact Population Dynamics source baseline used for Home.
- [x] Inventory active Home markup, selectors, surfaces, link states, type,
      spacing, and responsive bands in both codebases.
- [x] Check Dash, Bootstrap, and external-font effects relevant to Home.
- [x] Identify the minimum structural difference that blocks a clean match.
- [x] Keep all application-wide inventory items open until their owning
      workstreams are reached.
- [x] Capture browser-computed styles and matched screenshots while
      implementing the Home reference lock below.

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

- [x] Restyle the header to a white surface with green navigation affordances.
- [x] Align header height, content width, gutters, borders, and menu panel.
- [x] Restyle the footer to the shared light treatment.
- [x] Align shared page backgrounds, links, focus states, and reusable surface
      roles. Page-specific headers, cards, typography, and layout remain owned
      by later page workstreams.
- [x] Preserve navigation labels, routes, and menu behaviour.
- [x] Verify fixed-header offsets on every non-home route.

Validation:

- [x] Navigation opens, closes, and identifies the current page.
- [x] Escape/click-outside behaviour remains intact.
- [x] Footer remains in normal document flow.
- [x] Route changes do not create header overlap.
- [x] Targeted shell and route tests pass.

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

- [x] Change the active hero reference to
      `double_pend_hero1_green.png`.
- [x] Replace the navy overlay with a restrained light wash.
- [x] Use charcoal title/body text and green/muted supporting roles.
- [x] Restyle the Explore rail as a translucent/light surface.
- [x] Align the reading list and attribution with the shared theme.
- [x] Keep the current home information architecture.
- [x] Retain the navy hero as a rollback asset.
- [x] Check focal point and crops at all target viewports.

Validation:

- [x] Title and body remain readable over the image.
- [x] The pendulum remains visible without competing with the copy.
- [x] Explore links have clear hover and focus states.
- [x] Reading and attribution remain legible.
- [x] No content is clipped at short viewport heights; the 390px layout
      scrolls normally through the attribution.

Rollback:

- Restore the navy hero path and prior home-specific CSS commit. Because the
  old asset remains tracked, no asset recovery should be needed.

#### Workstream 3A — Home reference lock before Workstream 4

Status: required correction gate. Do not begin Workstream 4 until this slice
passes. Workstreams 1 and 2 remain accepted and should not be revisited unless
a narrowly scoped Home correction exposes a regression.

Tasks:

- [x] Align the Home hero type scale, weights, line heights, and margins to the
      pinned Population Dynamics source at desktop and mobile widths.
- [x] Align the Home-only gutter, grid proportions, vertical spacing, and
      1024–1440px compression band without changing shared shell tokens.
- [x] Replace the current two-part wash and mobile crop override with the
      reference overlay model, adjusted only if the Double Pendulum artwork
      requires more contrast.
- [x] Reduce the Explore panel opacity and align its blur, padding, gaps,
      border, radius, and shadow.
- [x] Remove Explore row separators and hover boxes; match reference rest and
      hover colours while preserving the global focus-visible ring.
- [x] Remove the further-reading card surface and match its heading, title,
      role, spacing, and link states.
- [x] Replace the attribution pill presentation with the reference's plain
      text and separately focusable icon-link treatment.
- [x] Make only the minimal Home markup changes needed to express the
      reference flow; preserve content, routes, IDs, callbacks, and scroll
      behaviour.
- [x] Add or refine Home structure tests for the markup adjustment.

Acceptance evidence:

- [x] At 1280 × 720, browser-computed font sizes match the inventory targets
      and the reference's desktop/laptop compression is active.
- [x] At 390 × 720, the title resolves to 40px, the copy scale matches the
      reference, and the full page scrolls normally.
- [x] Explore links are charcoal at rest; hover changes only the numbered
      affordance; keyboard focus remains unambiguous.
- [x] Reading links are charcoal at rest and dark green/underlined on hover;
      their focus treatment remains visible.
- [x] The Explore rail is the only elevated Home panel; reading and
      attribution have no card, pill, border, radius, or shadow treatment.
- [x] The hero remains readable, the artwork remains visible, and the
      transition into lower content feels continuous.
- [x] No horizontal overflow, clipped content, broken route, browser error,
      or scroll regression appears at either target width.
- [x] Focused Home tests and the full suite pass.

Completion evidence:

- At 1280 × 720, browser-computed Home type matches every source-resolved
  inventory target, including a 53.12px title, 17.28px introduction, 15.68px
  Explore heading, and 13.76px reading title.
- At 390 × 720, the title resolves to 40px and all supporting sizes match the
  mobile targets. The 1188px document scrolls to its 468px maximum offset and
  leaves the complete attribution visible.
- The document and body scroll widths equal their client widths at both target
  sizes. The green hero remains centered, legible, and visible through the
  single reference wash.
- Explore hover leaves the row transparent and changes only the number to
  `#00635d`. Reading hover resolves to `#004c47` with an underline. Explore
  and reading keyboard focus resolve to the shared 3px green outline and 4px
  pale-green ring.
- Browser diagnostics contain no warnings or errors.

Rollback:

- Revert the dedicated Home reference-lock commit. The committed Workstream 3
  first pass and retained navy hero remain available as independent fallback
  points.

#### Workstream 3B — Branded 404 routing and presentation

Status: complete. This correction is a required gate before Workstream 4.

Cause:

- The route registry already returned the custom not-found layout for unknown
  callback paths, but the Flask `before_request` guard aborted every unknown
  path matched by Dash's catch-all. A direct browser request therefore received
  Flask's generic 404 before Dash could mount the custom page.

Tasks:

- [x] Follow the Population Dynamics boundary: return the Dash index with HTTP
      404 for ordinary missing-page navigation so the route callback can mount
      the branded layout.
- [x] Preserve plain-text HTTP 404 responses for scanner, sensitive-file,
      file-like, API, and non-navigation requests.
- [x] Set `Cache-Control: no-store` on branded missing-page responses.
- [x] Align the not-found markup with the Population Dynamics composition: one
      semantic message, one Return home link, no shared header or footer, and
      no card surface.
- [x] Use the green Double Pendulum hero and the shared Home wash, with a
      subject-specific mobile focal point that keeps the pendulum visible.
- [x] Add direct-request, callback-layout, scanner-probe, structure, hero, and
      return-link regression coverage.

Acceptance evidence:

- [x] A direct GET for `/this-page-does-not-exist` returns HTTP 404, loads the
      Dash runtime, and renders the custom not-found layout.
- [x] Scanner probes including `.env`, PHP, and WordPress paths remain
      plain-text HTTP 404 responses.
- [x] The page is chromeless and contains only the expected Return home link.
- [x] At 1280 × 720 and 390 × 720, the hero fills the viewport with no
      horizontal overflow; the transparent message remains readable and the
      pendulum artwork remains visible.
- [x] Return home hover and focus-visible states match the shared theme, and
      activating the link returns successfully to `/`.
- [x] Browser diagnostics contain no warnings or errors.
- [x] Focused routing/content tests and the full suite pass.

Rollback:

- Revert the Workstream 3B server-hook, 404 layout/content/style, and test
  changes together. The prior request guard will restore the generic Flask 404
  without affecting known public routes.

### Workstream 4 — Equations and teaching surfaces

Status: Population Dynamics reference inventory complete on 2026-08-18;
Double Pendulum implementation pending.

Goal: make the Equations routes read as chapters from the same interactive
textbook as Population Dynamics without weakening the mathematical hierarchy,
route behaviour, or long-form readability.

#### Reference baseline and scope

The reference remains the clean local Population Dynamics checkout on `main`
at `7c9f1b415ca661a8c4214de6402b551a1e6d1845`. The deployed production pages
were also inspected at `population-dynamics.net` on 2026-08-18 to distinguish
the production teaching presentation from development-mode fallback styles.

Representative reference pages:

- `/continuous` for a chapter landing page with title, synopsis, mathematical
  hero, prose, and an Explore rail;
- `/continuous/logistic-growth` for a compact model lesson with one hero,
  one interactive band, figures, interpretation, and chapter navigation;
- `/discrete/periodicity` for a long mathematical chapter which alternates
  prose, display equations, a disclosure, interactive bands, figures, and a
  final hand-off without losing its reading rhythm;
- the Interacting and Probabilistic page sources for variants of the same
  teaching grammar rather than one-off layout rules.

Reference owners inspected:

| Concern | Population Dynamics owner | Double Pendulum owner |
| --- | --- | --- |
| App paper and page frame | `app/components/layout.py`, `assets/styles.css` | `app/pages/equations.py`, `assets/styles.css` |
| Lesson title, hero, equation summary, controls, plots, and chapter hand-off | `app/components/model_page.py` | `app/pages/equations.py`, `app/components/derivation.py` |
| Landing-page prose and Explore patterns | `app/pages/continuous/index.py`, `app/pages/discrete/index.py`, `app/pages/interacting/index.py` | No direct equivalent; useful as a teaching-pattern reference only |
| Long-form theory and disclosure patterns | `app/pages/discrete/periodicity.py`, related page-specific CSS | `app/content/equations.py`, `app/components/derivation.py` |
| Markdown and MathJax rhythm | `.math-markdown` and equation-panel rules | `.equation-markdown` and retained legacy Markdown routes |
| References and onward progression | `.model-further-reading`, `chapter_navigation()` | `app/components/references.py`, branch controls, legacy reference data |
| Structural regression coverage | routing and section-progression tests | `tests/unit/test_app_content.py`, Equations callback tests |

This workstream owns the teaching surface inside the shared shell. It does not
redesign the shared header/footer, change the accepted Double Pendulum
title/subtitle treatment, restyle Plotly traces, remove dependencies, or alter
the Simulation workspace. Plot containers may adopt the teaching-surface
geometry here; Plotly internals remain Workstream 6.

#### Fact-finding: the Population Dynamics teaching grammar

Population Dynamics production pages use a hierarchy of surfaces rather than
a uniform card system:

1. **One broad paper.** A route is presented as one white document surface
   within the 1400px shell. At 1280px the deployed model page resolves to
   1203.2px wide. The paper is square-edged, quietly bordered and shadowed,
   with 28px top, fluid 50px maximum inline, and 34px bottom padding.
2. **A visible route title before the lesson hero.** The route H1 is 2.2rem
   with 1.1 line height. The hero then supplies a more explanatory teaching
   headline rather than repeating the same title at a larger scale.
3. **One strong opening composition.** Model lessons use a two-column white
   hero with a 2px deep-green border, 12px radius, restrained shadow, and 30px
   padding. The copy sits beside a pale neutral equation/parameter panel whose
   inner equation blocks are white, 8px-radius surfaces.
4. **Body prose is mostly unboxed.** Direct theory and interpretation sections
   become transparent in production mode. Whitespace and occasional short,
   centred hairlines establish progression; each paragraph is not turned into
   a separate card.
5. **Boundaries are retained when they communicate function.** Comparison
   areas, interactive explorers, equation summaries, current-value notes,
   disclosures, figure groups, and chapter hand-offs remain visually bounded.
6. **Interactive material is grouped as a chapter band.** A muted heading band
   names the activity, while its controls, interpretation, and plots share one
   enclosing surface. Nested control and plot cards are flattened in
   production mode so an interactive does not become a stack of boxes.
7. **The typography stays compact and book-like.** Deployed model pages resolve
   body Markdown to 16px with a 26.4px line height. Supporting prose is regular
   weight; hierarchy comes from size, spacing, colour, and labels rather than
   making every paragraph semibold.
8. **Long chapters repeat a predictable sequence.** The 6918px Periodicity
   page remains legible by alternating unboxed theory, deliberate dividers,
   four named interactive bands, one disclosure, and a final chapter hand-off.
9. **Math overflow is local.** Wide tables, plots, and equations own their own
   horizontal overflow. The document itself does not widen or acquire a page-
   level horizontal scrollbar.
10. **The last surface points somewhere.** Model pages end with one concise
    guided hand-off, separating chapter progression from the global menu.

Source- and browser-resolved reference targets:

| Element | Population Dynamics production reference | Current Double Pendulum source | Workstream 4 direction |
| --- | --- | --- | --- |
| Document width at 1280px | 1203.2px within the 1400px shell | 1020px maximum with additional width subtraction | Use the shared 1400px shell and fluid 20–50px document padding; remove the extra narrow-document calculation |
| Paper surface | One white, square-edged, subtle bordered/shadowed route surface | White paper, but narrower with a stronger floating-document effect | Retain one paper and quieten its border/shadow; do not add a second global card |
| Route H1 | 2.2rem / 1.1, before the hero | Page title is inside the intro card at 3rem / 1.05 | Introduce a standalone route title and make the hero headline a distinct teaching statement |
| Hero headline | `clamp(1.55rem, 2.4vw, 2.15rem)` / 1.12 | Same text doubles as the 3rem route title | Use the reference scale and avoid duplicate title copy |
| Body Markdown | 1rem / 1.65, regular weight | 1rem / 1.56, weight 600 across core prose | Move derivation prose to regular weight and 1.65 line height; reserve semibold/bold for labels and headings |
| Eyebrow | 0.78rem, weight 750, 0.05em tracking | Small uppercase label, weight 800, no tracking | Match the compact tracked label convention |
| Lesson hero | 2px green border, 12px radius, two columns, 30px padding | Single-column inset callout with a 5px green left rule | Build a subject-specific copy/equation hero using the shared reference geometry |
| Theory sections | Transparent, borderless, shadowless prose sections | Unboxed derivation blocks, but separated by large 60px/44px section gaps | Keep them unboxed and compress the hierarchy to the reference's 18–34px rhythm |
| Purposeful sub-surfaces | Pale equation panels, 8px notes, meaningful interactive groups | Large intro box, 500px-minimum model cards, branch cards, notes | Keep comparison, branch, equation, and note boundaries; remove arbitrary minimum heights and excess elevation |
| Section headings | 1.25rem functional H2s; 0.88rem tracked uppercase H3 labels where appropriate | 2rem section H2s and 1.15–1.25rem block headings | Reduce the repeated middle hierarchy so the route title and hero remain dominant |
| Chapter completion | One copy/action hand-off row | Branch selection mounts content but the chapter has no final onward action | Add one subject-appropriate end hand-off without replacing global navigation |
| Mobile | Hero and multi-column groups stack at 1100px; at 760px a 20px shell inset combines with the fluid 20px paper padding | Comparison and branch grids wait until 900px; paper becomes full width at 650px with 20px internal padding | Stack pressure-point grids at 1100px, preserve the reference's nested mobile inset, and keep local math overflow |

#### Double Pendulum implementation map

##### A. Establish the document and reading hierarchy

- [ ] Replace the 1020px Equations-specific width calculation with the shared
      1400px shell width and the Population Dynamics production paper model.
- [ ] Keep one white route-level paper with a restrained border and shadow;
      avoid rounded/elevated wrappers around the whole chapter.
- [ ] Give the paper 28px top, fluid 20–50px inline, and approximately 34px
      bottom padding, then tune only where MathJax or the model images require
      additional breathing room.
- [ ] Add a standalone 2.2rem route H1 before the teaching hero. Preserve the
      shared shell's existing Double Pendulum title/subtitle treatment.
- [ ] Establish a repeatable vertical scale based on 18, 20, 28, and 34px
      intervals instead of repeated 52–60px gaps.

##### B. Recompose the opening lesson

- [ ] Convert the current left-rule introduction box into the reference's
      purposeful green-framed lesson hero: copy on the left and a pale equation
      summary on the right.
- [ ] Use a teaching headline distinct from `Equations of Motion`; retain the
      existing introduction and mathematical meaning rather than padding the
      hero with decorative copy.
- [ ] Give the equation panel one concise shared starting equation or
      formulation map derived from existing content. Do not introduce a new
      scientific claim merely to fill the panel.
- [ ] Stack the hero at 1100px and preserve local overflow inside its equation
      block at narrow widths.

##### C. Flatten prose while preserving semantic surfaces

- [ ] Render derivation sections and ordinary interpretation blocks as
      unboxed document flow with consistent headings, paragraph measure, and
      restrained hairline transitions.
- [ ] Set teaching prose to 16px, normal weight, approximately 1.65 line
      height, and a readable 68–72ch maximum where the layout permits.
- [ ] Use compact tracked green eyebrows, 1.25rem functional section headings,
      and smaller uppercase labels only for genuine equation/parameter
      metadata.
- [ ] Retain pale-green or pale-neutral note treatment for assumptions,
      coordinate conventions, warnings, and equation annotations; use a
      narrow accent rule rather than a floating card shadow.
- [ ] Style disclosures as in-flow teaching aids with a green summary and
      clear open spacing. Preserve native keyboard and screen-reader behaviour.

##### D. Keep subject-specific comparison and branch interactions

- [ ] Keep the Simple/Compound comparison because it communicates a physical
      modelling choice, but remove arbitrary 500px minimum heights, reduce
      image dominance, and use quiet borders without stacked shadows.
- [ ] Preserve both model images, alternative text, descriptions, and detail
      lists. Let the cards equalise naturally on desktop and stack at the
      reference's 1100px pressure point.
- [ ] Keep the Euler–Lagrange/Hamiltonian branch controls as buttons with their
      current IDs, `aria-pressed` values, callback ownership, and lazy mounting.
- [ ] Present the branch choice as one deliberate chapter-selection surface;
      use pale green for active/hover state and avoid giving the selected card
      a large floating shadow.
- [ ] Keep selected branch content in the same paper so route transitions do
      not look like a second application or nested document.

##### E. Equations, references, and chapter progression

- [ ] Keep MathJax equations on white or pale-neutral teaching surfaces and
      preserve normal text contrast around them.
- [ ] Give each display equation or genuinely wide table its own horizontal
      overflow boundary. Do not use page-wide overflow and do not shrink math
      until it becomes unreadable.
- [ ] Preserve upright ordinary differential notation such as
      `\frac{\mathrm{d}}{\mathrm{d}t}` and standard `\partial` notation.
- [ ] Consolidate the retained Lagrangian/Hamiltonian reference data into a
      chapter-end further-reading/reference pattern when its branch is mounted.
      Use an unboxed list or narrow green rule rather than a large References
      card.
- [ ] End each mounted branch with one concise guided hand-off, such as return
      to the Equations overview or continue to Simulation. This supplements,
      and does not replace, the shared menu.

##### F. Responsive and dependency boundaries

- [ ] At 1100px, stack the opening hero, model comparison, and branch choices
      before their content becomes cramped.
- [ ] At 760px, use the reference's 20px shell inset plus fluid 20px paper
      padding, keep headings within the reference scale, and allow long display
      equations to scroll locally.
- [ ] Remove page-level horizontal overflow at 390px without clipping equation
      content, disclosure summaries, model images, or branch focus rings.
- [ ] Do not change Bootstrap/Red Hat loading in this workstream. Record any
      computed-style interference for Workstream 7 rather than combining the
      dependency audit with the teaching redesign.

Likely owners:

- `assets/styles.css`
- `app/pages/equations.py`
- `app/components/derivation.py`
- `app/components/references.py` if branch references are promoted into the
  consolidated teaching page
- `app/content/equations.py` only for a concise, scientifically existing hero
  equation/headline or chapter hand-off copy
- focused content/layout tests

Preservation constraints:

- Preserve `/equations`, `/lagrangian`, and `/hamiltonian` route behaviour.
- Preserve every branch button ID, `equations-branch`,
  `equations-branch-output`, callback, and selected-branch lazy-mount contract.
- Preserve mathematical copy, formulae, Simple/Compound distinctions, image
  paths, alternative text, and ordinary differential notation unless a
  separately reviewed content correction is required.
- Do not turn the Equations page into a dashboard and do not import Population
  Dynamics components or CSS.

Validation:

- [ ] At 1280px the paper follows the reference shell proportion, ordinary
      prose resolves to 16px/approximately 1.65, and the title/hero hierarchy
      matches the source-resolved targets above.
- [ ] At 390px the hero, model comparison, and branch choices are single
      column; the document has no horizontal overflow.
- [ ] `/equations`, `/lagrangian`, and `/hamiltonian` render the correct shared
      trunk and only the selected branch.
- [ ] Branch controls work by mouse and keyboard, keep visible focus, and
      expose correct `aria-pressed` state.
- [ ] Wide display equations remain readable through local scrolling and do
      not widen the document.
- [ ] Model images remain sharp, contained, and correctly labelled.
- [ ] References and the final guided hand-off contain valid links and do not
      obscure or duplicate global navigation.
- [ ] Browser diagnostics show no MathJax, missing-asset, callback, or overflow
      errors.
- [ ] Focused Equations/content tests and the full suite pass.

Rollback:

- Implement this as an Equations-scoped CSS/markup slice and revert it as one
  unit. Do not mix the teaching-surface work with Plotly palette, Simulation,
  dependency-removal, or shared-shell changes.

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
| 2026-08-18 | Complete the shared-shell restyle in CSS without markup changes | Existing semantic classes and native `details`/`summary` behaviour already provide the required structure and accessibility hooks | Shared shell CSS |
| 2026-08-18 | Restyle Home with page-scoped CSS and retain the 404's existing treatment | Keep Workstream 3 independently reversible without changing the shared shell, chromeless route structure, or unrelated page presentation | Home CSS and later 404 work if desired |
| 2026-08-18 | Reopen Home as a source-locked correction gate before Workstream 4 | The first pass matched the palette but drifted from the reference type scale, link states, and deliberately unboxed lower content | Home CSS, markup, and tests |
| 2026-08-18 | Pin Population Dynamics `7c9f1b4` for the Home comparison | Give the correction measurable source ownership and prevent a moving visual target | This plan; durable theme documentation at closeout |
| 2026-08-18 | Serve the Dash index with HTTP 404 for ordinary unknown navigation while retaining plain 404s for probes | Let the custom callback-owned 404 resolve without weakening scanner and sensitive-path hardening | Server hooks, routing tests, and durable deployment documentation at closeout |
| 2026-08-18 | Match the Population Dynamics 404 composition with the Double Pendulum hero | Keep the error route recognisably within the interactive-textbook family and subject identity | 404 layout, content, and CSS |
| 2026-08-18 | Use the Population Dynamics production teaching hierarchy for Workstream 4: one broad paper, one strong lesson hero, mostly unboxed prose, and boundaries only where they communicate function | This hierarchy, rather than card density, is the repeating visual grammar that makes short and very long Population Dynamics lessons feel like one textbook | Equations layout/components/CSS and durable theme documentation at closeout |

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
| 2026-08-18 | Workstream 2 | Focused component/content/route tests | 45 passed in 0.97s | No failures |
| 2026-08-18 | Workstream 2 | Full suite | 174 passed in 8.06s | No failures |
| 2026-08-18 | Workstream 2 | Home, Equations, and Simulation at 1280px and 390px | Exact 72px header/body alignment; no horizontal overflow or brand/menu collision; menu and active states verified | Home remains deliberately outside the persistent shell; one existing informational `scroll.js` retry log and no new browser warnings/errors |
| 2026-08-18 | Workstream 2 | Non-home route shell sweep | `/equations`, `/lagrangian`, `/hamiltonian`, `/simulation`, and `/chaos` have no header overlap | Footer remains static/in normal flow on every inspected shell route |
| 2026-08-18 | Workstream 3 | Focused Home/content/route tests | 39 passed in 0.89s | No failures |
| 2026-08-18 | Workstream 3 | Full suite | 174 passed in 7.93s | No failures |
| 2026-08-18 | Workstream 3 | Home at 1280 × 720 and 390 × 720 | Hero, overlay, Explore hover/focus, reading transition, attribution, and complete scroll path verified; no horizontal overflow | Green hero loaded; no new browser warnings/errors; temporary responsive harness removed |
| 2026-08-18 | Workstream 0A | Source inventory against Population Dynamics `7c9f1b4` | Home markup, CSS, responsive bands, dependency effects, and source-resolved type sizes recorded | Documentation-only pass; browser-computed comparison deferred to Workstream 3A implementation |
| 2026-08-18 | Workstream 3A | Focused Home/content/import tests | 40 passed in 1.08s | New structure test covers the reference flow, numbered Explore links, and separate attribution link |
| 2026-08-18 | Workstream 3A | Full suite | 175 passed in 7.95s | No failures |
| 2026-08-18 | Workstream 3A | Home at 1280 × 720 and 390 × 720 | All inventoried type sizes matched; hover/focus, overlay, scroll end, and artwork visibility verified; no horizontal overflow | No browser warnings/errors; responsive viewport override reset after inspection |
| 2026-08-18 | Workstream 3B | Focused server-hook, import/routing, and content tests | 49 passed in 0.94s | Branded navigation 404 plus plain scanner, API, and file-like 404 paths covered |
| 2026-08-18 | Workstream 3B | Full suite | 177 passed in 8.14s | No failures |
| 2026-08-18 | Workstream 3B | Unknown route at 1280 × 720 and 390 × 720 | Direct request remained HTTP 404; custom hero, mobile focal point, Return home navigation, hover/focus, and overflow verified | No browser warnings/errors; responsive viewport override reset and local server stopped |
| 2026-08-18 | Workstream 4 fact finding | Population Dynamics `7c9f1b4` source inventory plus deployed `/continuous`, `/continuous/logistic-growth`, and `/discrete/periodicity` review | Production paper, type, hero, prose, interactive, equation, disclosure, progression, and responsive patterns mapped to Double Pendulum owners and constraints | Documentation-only teaching-surface pass; implementation remains pending |

Append results; do not rewrite failed evidence into a success-only history.

## 14. Current Progress

- [x] Restyle feasibility reviewed.
- [x] Green hero created and placed under `assets/Heros/`.
- [x] `ROADMAP.md` restructured with Restyle as the active phase.
- [x] Work isolated on `feat_restyle`.
- [x] Temporary execution and rollback plan created.
- [ ] Pre-change source, deployment, test, and visual baseline recorded.
- [x] Theme tokens implemented.
- [x] Shared shell restyled.
- [x] Green hero activated and Home first pass completed.
- [x] Home reference lock completed before Workstream 4.
- [x] Branded 404 routing and presentation completed before Workstream 4.
- [x] Workstream 4 Population Dynamics teaching-surface inventory recorded.
- [ ] Equations restyled.
- [ ] Simulation HTML/CSS surfaces restyled.
- [ ] Canvas/plotting palette updated.
- [ ] Styling dependencies audited.
- [ ] Reusable theme boundary documented.
- [ ] Full validation completed.
- [ ] Release and rollback targets recorded.
- [ ] Durable documentation updated.
- [ ] Temporary plan removed at closeout.
