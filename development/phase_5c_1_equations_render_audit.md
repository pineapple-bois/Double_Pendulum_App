# Phase 5C.1 — Equations Page Render Audit

## Context

Phase 5B created the unified Equations of Motion page and moved the derivation
content into structured Python data and reusable Dash components. The page is
now accepted as the first learning page in the intended journey, but it appears
slow to load or render. This audit records evidence before any optimisation,
branch reveal behaviour, or production layout mode is implemented.

## Current page structure

- Route/page entry point: `app/pages/equations.py`.
- Route registry: `app/pages/registry.py` maps `/equations`, `/lagrangian`,
  and `/hamiltonian` to the same Equations page layout.
- Content module: `app/content/equations.py`.
- Rendering helpers: `app/components/derivation.py`.
- App-shell routing: `app/callbacks/routing.py` replaces `page-content` when
  `dcc.Location.pathname` changes.
- The top-level `pendulum_app.py` layout initially mounts the Home page inside
  `page-content`, then the routing callback swaps in the requested route.

The Equations page layout is composed as:

1. shared site header;
2. hero/orientation section;
3. mechanical model section with two model cards;
4. shared derivation trunk;
5. branch navigation cards;
6. Euler-Lagrange branch;
7. Hamiltonian branch;
8. references and footer.

Current content counts:

- Derivation sections: 3.
- Equation blocks: 27 total.
- Blocks by section:
  - shared trunk: 8 blocks;
  - Euler-Lagrange formulation: 9 blocks;
  - Hamiltonian formulation: 10 blocks.
- Equation block notes: 12.
- Collapsed equation blocks in the content data: 0.
- Introductory Markdown paragraphs: 3.
- Model cards: 2.
- Model-card Markdown detail items: 6.
- Branch cards: 2.
- Branch-card Markdown points: 4.

Runtime component count from `app.pages.equations.layout()`:

- Total Dash components: 216.
- `dcc.Markdown` components: 54.
- `html.Img` components: 3.
- `html.Details` components: 1, from the navigation/header rather than a
  derivation block.
- Serialized layout payload: about 56.6 KiB.

All derivation sections are rendered on initial Equations page layout
construction. Both the Euler-Lagrange and Hamiltonian branches are mounted
immediately; they are not lazy-rendered and are not hidden behind conditional
callbacks.

Image assets present in the Equations layout:

- `/assets/Images/Model_Simple_Transparent_NoText.png`
  - 1786 x 2168 PNG, about 142 KiB.
- `/assets/Images/Model_Compound_Transparent_NoText.png`
  - 1786 x 2168 PNG, about 218 KiB.
- Footer GitHub mark, via shared footer content.

The Home hero image is not part of the Equations page layout, but
`pendulum_app.py` initially mounts Home for the app shell. On direct navigation
to `/equations`, this may briefly place Home content in the initial payload
before the routing callback replaces it.

## Suspected cost centres

### Python layout construction

Python-side layout construction does not look like the main bottleneck. A
lightweight timing of `app.pages.equations.layout()` showed about 1.0 ms per
call on this machine. The page content is defined as Python dataclasses, so the
Equations page does not read the long derivation markdown files while building
its layout.

One caveat: `app/content/equations.py` imports references from
`app.content.math`, and `app.content.math` constructs `MATH_PAGES` by reading
the old Lagrangian and Hamiltonian markdown files at module import time. That
is an import-time cost, not repeated per Equations layout construction, but it
is still worth untangling later.

### Dash component tree size

The component tree is moderately large for a content page: 216 components and
54 Markdown components. The serialized payload is not enormous, but the client
still has to hydrate the whole tree and then typeset the mathematical content.

### Markdown component count

Each equation block renders as a separate `dcc.Markdown(mathjax=True)`
component. Each note also renders as a separate Markdown component. Additional
Markdown components are used for hero paragraphs, model-card copy, model-card
details, and branch-card points.

The current Markdown component count is high enough to suspect client-side
Markdown parsing and MathJax processing as a meaningful cost centre.

### MathJax/typesetting cost

MathJax is loaded globally in `pendulum_app.py`:

```python
external_scripts=[
    "https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.0/es5/tex-mml-chtml.js"
]
```

All Equations page Markdown is rendered with `mathjax=True` through
`render_markdown()` in `app/components/derivation.py`.

The derivation content contains about 25.4k characters across equation blocks
and notes, and the rendered Equations layout contains about 27.0k characters of
Markdown text overall. A rough delimiter count found about 267 math delimiter
pairs across the mounted Markdown components. This is an approximate count, but
it supports the hypothesis that MathJax typesetting is a primary render cost.

### Hidden/collapsed content still mounted

No derivation blocks are currently marked `collapsed=True`, so no branch content
is hidden by `html.Details` today. Even if `html.Details` were used for long
branches, the child Markdown components would still be mounted in the layout
tree and would likely still incur Dash/Markdown/MathJax work. CSS hiding or
native details disclosure alone should not be assumed to reduce initial
typesetting cost.

### Image asset size/loading

The model diagrams are large in pixel dimensions but modest in transfer size:
about 142 KiB and 218 KiB. They are unlikely to be the dominant Equations page
cost compared with MathJax-heavy Markdown rendering, though they do contribute
image decode and layout work.

The Home hero image is much larger, about 2.4 MiB. It is not part of the
Equations page layout, but direct route loading may initially mount Home before
the routing callback swaps in Equations. This is a routing/app-shell concern
worth measuring separately.

### CSS/layout/reflow cost

The Equations page uses normal CSS grid/flexbox, cards, shadows, and horizontal
overflow on MathJax containers. Nothing obvious suggests CSS is the first
bottleneck, but equation typesetting can cause layout shifts as MathJax replaces
source text with rendered math.

## Evidence gathered

Files inspected:

- `pendulum_app.py`
- `app/pages/equations.py`
- `app/pages/registry.py`
- `app/callbacks/routing.py`
- `app/components/derivation.py`
- `app/content/equations.py`
- `app/content/math.py`
- `assets/styles.css`
- `assets/Images/Model_Simple_Transparent_NoText.png`
- `assets/Images/Model_Compound_Transparent_NoText.png`
- `assets/Heros/double_pend_hero1_navy.png`

Concrete observations:

- `app/pages/equations.py` renders every derivation section in one layout call:

```python
*[
    render_derivation_section(section)
    for section in DERIVATION_SECTIONS[1:]
],
```

- `render_equation_block()` creates one `dcc.Markdown(mathjax=True)` for every
  block body and another for every visible note.
- No current `EquationBlock` has `collapsed=True`.
- Both mathematical branches are mounted immediately on initial Equations page
  render.
- `app/pages/registry.py` preserves `/lagrangian` and `/hamiltonian` by mapping
  both to `equations_layout`.
- `app/content/equations.py` stores content as Python dataclasses, not as one
  large imported markdown blob.
- The old markdown files are still read at `app.content.math` import time
  because `MATH_PAGES` is constructed eagerly.
- Model diagram sizes:
  - simple: 1786 x 2168 PNG, 142 KiB;
  - compound: 1786 x 2168 PNG, 218 KiB.
- Home hero size:
  - 1536 x 1024 PNG, 2.4 MiB.
- Lightweight layout timing:
  - `app.pages.equations.layout()` best observed time: about 1.04 ms;
  - median observed time: about 1.06 ms;
  - this suggests server-side Python construction is not the main issue.

## Findings

Evidence-backed findings:

1. The page mounts all derivation content immediately, including both branches.
   There is no lazy rendering for branch content.
2. The page creates 54 MathJax-enabled Markdown components, including 39 from
   equation block bodies and notes alone.
3. Python layout construction is fast in isolation, around 1 ms per call in the
   lightweight local timing.
4. The model diagrams are not tiny files, but their combined size is only about
   360 KiB. They are unlikely to dominate compared with MathJax-heavy content.
5. `html.Details` or CSS hiding would not be enough by itself if the expensive
   Markdown children remain mounted.
6. Direct route loads may pay an additional app-shell cost because the initial
   top-level layout mounts Home before the routing callback replaces it.

Likely but not yet proven findings:

1. MathJax typesetting is probably the main perceived render cost on the
   Equations page.
2. Reducing initially mounted branch Markdown is likely to improve first render
   more than image optimisation.
3. The initial Home mount may affect direct `/equations` loads, especially if
   the Home hero image starts loading before the route callback replaces the
   page.

## Recommended next experiment

Run one focused experiment: lazy-render the Euler-Lagrange and Hamiltonian
branch content so the initial Equations page mounts only the hero, model
orientation, shared derivation trunk, branch navigation, references, and footer.

This should be a true mount/unmount experiment, not merely a visual hide:

- Do not place both branch component trees in the initial layout.
- Render a branch only after the user chooses it, or render one explicitly
  selected branch based on a lightweight state/anchor strategy.
- Preserve all existing content data and old public routes.
- Keep `/lagrangian` and `/hamiltonian` resolving during the experiment.

Rationale:

- The branches account for 19 of 27 equation blocks.
- The branches account for most of the densest mathematical content.
- Hiding without unmounting would not address the suspected Markdown/MathJax
  cost.
- This experiment aligns with the planned Phase 5C progressive-disclosure work
  while producing measurable performance evidence.

## Non-findings and uncertainties

- Browser performance timings were not collected in this audit.
- No Chrome performance profile was captured.
- No Dash network waterfall was captured.
- MathJax execution time was not measured directly.
- It is unclear whether the initial Home layout causes the 2.4 MiB hero image
  to begin loading before direct `/equations` route replacement completes.
- The exact split between Markdown parsing cost and MathJax typesetting cost is
  unknown.
- No permanent instrumentation was added.
- No performance optimisation was implemented.

## Suggested acceptance criteria for the next optimisation

- Initial Equations page render mounts fewer than 35 `dcc.Markdown` components.
- Initial Equations page render excludes at least one full mathematical branch
  from the component tree.
- The selected branch still renders correctly when requested.
- `/equations`, `/lagrangian`, and `/hamiltonian` continue to resolve.
- Existing tests pass.
- A before/after browser timing or performance note is recorded, including at
  least one observable metric such as time to usable content, Markdown component
  count, serialized layout size, or MathJax completion time if practical.
