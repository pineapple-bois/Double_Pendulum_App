# Restyle Implementation Record

The Restyle was completed on `feat_restyle` in August 2026. Population
Dynamics was used as the visual reference so the two applications read as a
family of interactive textbooks, while Double Pendulum retained its own
subject matter, routes, teaching structure, and simulation architecture.

This document records the durable outcome. The detailed branch checklist,
intermediate measurements, and iteration history were intentionally retired at
closeout.

## Design language

The application now uses an app-owned semantic theme built around:

- a warm off-white page background and white content surfaces;
- charcoal text, deep green `#00635d`, and pale green supporting surfaces;
- Helvetica Neue and system sans-serif fonts at a 16px base size;
- restrained warm-grey borders and shadows with 8px and 12px radii;
- consistent heading, body, link, hover, focus-visible, disabled, validation,
  stale, success, warning, and danger states.

The Population Dynamics stylesheet was not copied wholesale. Shared visual
ideas were translated into local semantic tokens and page-scoped rules so the
Double Pendulum application remains independently maintainable.

## Surfaces updated

### Application shell and Home

- The header, navigation, dropdown menu, footer, responsive shell, and GitHub
  attribution use light surfaces and the shared typography and interaction
  language.
- The Home page uses `assets/Heros/double_pend_hero1_green.png`, a restrained
  light wash, reference-aligned typography, an unboxed reading area, and a
  lighter Explore treatment.
- Unknown navigation routes retain the branded application experience while
  returning HTTP 404. Scanner, API-like, and file-like probes retain plain 404
  responses.
- The Chaos route has a shell-preserving **Under development** placeholder.

### Teaching surfaces

- Equations, Euler-Lagrange, and Hamiltonian routes share one broad paper and
  derivation hierarchy.
- Teaching prose is intentionally broad rather than constrained to a
  half-width column. Cards and dividers are used only where they communicate a
  real comparison or section boundary.
- The lesson introduction remains single-column; no abbreviated equation
  summary competes with the full derivation.
- Model diagrams, branch selection, long equations, references, and guided
  route progression remain responsive and keyboard accessible.

### Simulation and rendered output

- The existing Simulation sidebar, callback ownership, state flow, renderer
  IDs, and payload contracts were preserved.
- Simulation figures use unboxed white presentation areas to maximise drawing
  space. Playback and display controls share a full-width, lightly framed
  **Control Centre** above the scrubber.
- Inputs, dropdowns, steppers, segmented choices, validation, status,
  diagnostics, sliders, and responsive layouts use the semantic theme.
- The Canvas renderer and retained central Plotly layout use the same surface,
  type, axis, grid, and status language. The primary series is green and the
  secondary series uses muted plum `#76546f` for clearer contrast.
- Dormant model plotting helpers were not redesigned and should be audited
  separately before being returned to production use.

## Dependency outcome

The app now owns its global styles explicitly. Source and browser comparison
confirmed that production markup did not depend on Bootstrap, so the Bootstrap
stylesheet, external Red Hat Display request, and
`dash-bootstrap-components` dependency were removed together. A clean Python
3.12 installation and app-import tests confirmed that the package is no longer
required.

## Preserved contracts

The Restyle did not intentionally change:

- public routes or callback-bound component IDs;
- symbolic or numerical model behaviour and solver policy;
- Simulation stores, result-state protections, Canvas payload schemas,
  playback behaviour, or Python/JavaScript responsibilities;
- the Flask `server` export, Gunicorn entry point, or deployment flags.

Python remains the owner of mathematical and numerical truth. The browser
renderer remains display-only.

## Validation and known follow-up

Home, Equations, Simulation, Chaos, legacy formulation routes, and branded 404
presentation were checked across desktop and mobile widths during the work.
Focused tests covered the application shell, routing, teaching content,
Simulation interaction, Canvas payloads, renderer boundaries, plotting style,
and dependency removal. Clean-environment installation also succeeded without
`dash-bootstrap-components`.

The two Equations-content assertions made stale by the teaching-content
revision were updated at closeout to test the revised structure and meaning.
The final suite passed with 182 tests.

Deployment was not authorised by the Restyle work. A release still requires a
reviewed commit, an identified production baseline and rollback release, and a
final production-like smoke check.
