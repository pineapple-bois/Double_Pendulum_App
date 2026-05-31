# Production Documentation

This directory is the durable production-facing architecture and workflow
reference for the Double Pendulum App.

It is intentionally different from `development/`. The `development/`
directory is an evidence trail for experiments, workbench notes, prototypes,
and historical decision support. Production code must not import from
`development/`; accepted ideas should be promoted deliberately into `app/`,
`src/double_pendulum/`, or `assets/` with tests.

## Repository roles

- `documentation/` records the current production architecture, contracts, and
  safe development workflow.
- `development/` records exploratory work, including the
  `development/simulation_workbench/` evidence that led to the current Canvas
  integration.
- `app/` is the Dash application layer: pages, callbacks, content,
  components, and simulation serialization helpers.
- `src/double_pendulum/` is reusable Python logic for validation, symbolic
  mechanics, numerical models, solver metadata, plotting helpers, and backend
  simulation support.
- `assets/` is Dash-served static material: CSS, JavaScript, markdown, images,
  and the production Canvas renderer asset
  `assets/simulation-canvas-renderer.js`.

## Index

- [Canvas Integration API](canvas-integration-api.md)
- [Simulation Result Contract](simulation-result-contract.md)
- [Callback Rendering Flow](callback-rendering-flow.md)
- [Development Workflow](development-workflow.md)

## Current state

Recent Simulation Workbench and Canvas integration work has substantially
completed the Phase 6/Phase 7 direction described in `ROADMAP.md`: the
Workbench produced the renderer decision and production promotion evidence, and
the live Simulation page now uses a Python-built Canvas payload rendered by a
browser-side Canvas asset.

That state is useful but not polished. The next project work should consolidate
production layout, styling, callback stability, Canvas/backend contract tests,
and safe development workflow rather than opening another broad simulation
workbench or chaos branch.
