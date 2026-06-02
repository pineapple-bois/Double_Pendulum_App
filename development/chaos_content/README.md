# Phase 10 Chaos Content Sandbox

This directory is the Phase 10 sandbox for new Chaos page discovery,
mathematical review, and rewritten experiments.

It is exploratory material only. Production app code must not import from this
directory, and this directory must not be used as a source of production
callbacks, layouts, assets, routes, metrics, plots, APIs, or datasets.

## Purpose

- Preserve Phase 10 discovery notes separately from the historic
  `development/chaos_branch/` work.
- Record what looked useful, stale, unsafe, or mathematically unproven in the
  historic branch.
- Provide a clean place for future rewritten chaos experiments.
- Keep all future experiments self-contained unless a read-only production
  reference is explicitly justified in the experiment notes.

## Internal Structure

- `DISCOVERY_REPORT.md` - Phase 10 discovery report for
  `development/chaos_branch/`.
- `notes/` - inventories, fidelity questions, and design/research notes.
- `experiments/` - future rewritten experiments. No legacy code should be
  copied here wholesale.
- `references/` - curated reference notes and links that may inform future
  experiments.

## Reuse Policy

Historic code from `development/chaos_branch/` may only be reused after it is
rewritten into this sandbox. Rewritten code must be self-contained inside
`development/chaos_content/` and must not depend on production app callbacks,
layouts, or assets unless the dependency is explicitly documented as read-only
reference material.

Nothing in this sandbox is production-ready unless a later Phase 10 task
promotes it deliberately with mathematical fidelity review, tests, and
production documentation.

