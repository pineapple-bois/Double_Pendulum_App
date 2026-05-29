# Accepted Workbench Decisions

Tier: Phase 6 / Simulation Workbench Tier 4
Date: 2026-05-29

## Numerical And Trust Decisions

- Tier 1 established representative numerical sanity only.
- Tier 1 does not prove full physical correctness.
- Energy conservation and acceptable energy drift are not yet validated.
- Long-duration scientific stability remains unproven.
- Tolerance sensitivity remains unproven.
- Solver-method equivalence remains unproven.
- Chaos diagnostics remain unproven.
- User-facing initial conditions are `theta1`, `theta2`, `omega1`, `omega2`.
- Hamiltonian mode converts user-facing angular velocities to canonical momenta
  before solving.
- Solver metadata is retained and should be surfaced in diagnostics.
- The theta-theta output must not be treated as a full phase portrait.

## Output Composition Decisions

- The Simulation page should have a useful empty state.
- A successful run should expose a concise run summary.
- A successful run should expose numerical diagnostics backed by solver
  metadata and finite/shape/time checks.
- Angular displacement over time is a candidate production output when labelled
  clearly.
- The theta-theta view must be labelled as an angular state projection, not a
  full phase portrait.
- Failure and invalid states must be visible.
- Failure and invalid states must not leave stale successful animation playing.
- Energy diagnostics are deferred until formulas, state conventions, and
  expected regimes are audited.

## Renderer Decisions

- Canvas is the preferred production candidate for physical motion and synced
  selected-time inspection.
- Canvas should render physical motion, angular displacement time series,
  angular state projection, cursor/markers, and readout from one shared
  selected-frame state.
- Python computes all arrays and owns mathematical truth.
- JavaScript owns rendering and playback/inspection state only.
- JavaScript must not compute physics, integrate trajectories, infer
  Hamiltonian angular velocities, or transform state conventions.
- Plotly remains a fallback or future richer analytical inspection option.
- Reduced-frame Plotly animation should not be promoted as the main UX.

## Interaction Decisions

- The Tier 3D event matrix is the lifecycle authority.
- No visual state may continue animating after its simulation result has been
  superseded.
- New runs cancel old playback.
- Clear actions cancel playback.
- Failure states cancel playback.
- Stale input changes cancel playback.
- Stale outputs may remain inspectable, but must be visibly stale and must not
  silently animate as current.
- Scrubbing should pause playback.
- Scrubbing should update motion, time-series cursor/markers, projection
  marker, and selected-time/state readout.
- Display-only toggles such as axes and grid should not mark output stale and
  should not call Python.

## Promotion Sequence Decision

- Production Task A implements and tests the Python Canvas payload API.
- Production Task B wires the Canvas renderer into `/simulation` only after
  Task A is accepted.
- Existing Plotly output paths should remain available until Canvas integration
  passes promotion gates.
