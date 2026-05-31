# Production Documentation

This directory is the durable production-facing architecture and workflow
reference for the Double Pendulum App.

It is intentionally different from `development/`. The `development/`
directory is an evidence trail for experiments, workbench notes, prototypes,
and historical decision support. Production code must not import from
`development/`; accepted ideas should be promoted deliberately into `app/`,
`src/double_pendulum/`, or `assets/` with tests.

## Repository roles

- `documentation/` records durable production architecture, contracts, and
  safe development workflow.
- `documentation/simulation-canvas/` records the current Canvas-backed
  Simulation architecture, payload contract, callback/rendering flow, and
  implementation assumptions.
- `development/` records exploratory work, including the
  `development/simulation_workbench/` evidence that led to the current Canvas
  integration.
- `ROADMAP.md` is the active planning document. It should stay concise and
  point into this directory for implementation detail.
- `app/` is the Dash application layer: pages, callbacks, content,
  components, and simulation serialization helpers.
- `src/double_pendulum/` is reusable Python logic for validation, symbolic
  mechanics, numerical models, solver metadata, plotting helpers, and backend
  simulation support.
- `assets/` is Dash-served static material: CSS, JavaScript, markdown, images,
  and the production Canvas renderer asset
  `assets/simulation-canvas-renderer.js`.

## Index

- [Simulation Canvas Architecture](simulation-canvas/)
- [Development Workflow](development-workflow.md)

## Current state

Recent Simulation Workbench and Canvas integration work has substantially
completed the Phase 6/Phase 7 direction described in `ROADMAP.md`: the
Workbench produced the renderer decision and production promotion evidence, and
the live Simulation page now uses a Python-built Canvas payload rendered by a
browser-side Canvas asset.

That state is useful but not polished. The active Phase 8 work should focus on
numerical baseline, callback hardening, bug eradication, and documentation
control rather than styling, new chaos/comparison work, or another broad
simulation workbench.
