# Tier 4 Production Promotion Package

Tier 4 is the final Simulation Workbench handoff for the accepted Canvas
renderer direction.

It does not implement Canvas in production. It translates Tier 1-3 evidence
into scoped production tasks, API hardening requirements, tests, rollback
rules, and deferred-work boundaries.

## Why Comparison / Chaos Bridge Moved Out

The previous comparison/chaos bridge tier is no longer part of this workbench
sequence. It has moved to a future development branch to be defined later
because it raises separate scientific and pedagogical questions:

- side-by-side runs;
- perturbation controls;
- separation-over-time diagnostics;
- tolerance or solver-method comparison;
- energy-drift comparison;
- bridges to future chaos modules.

Those ideas are valuable, but they are not prerequisites for promoting the
Canvas renderer.

## Files

- `ACCEPTED_DECISIONS.md` - decisions accepted from Tiers 1-3.
- `API_TIGHTENING_REQUIREMENTS.md` - schema and safety requirements before
  production integration.
- `PRODUCTION_TASK_A_PAYLOAD_API.md` - next implementation task for Python
  payload helpers and tests.
- `PRODUCTION_TASK_B_CANVAS_INTEGRATION.md` - follow-on task for production
  `/simulation` Canvas integration.
- `PRODUCTION_TEST_PLAN.md` - required Python, browser, and performance checks.
- `ROLLBACK_AND_DEFERRED_WORK.md` - fallback path and explicitly deferred work.
- `TIER_4_PROMOTION_CLEANUP.md` - final handoff summary.

## How To Read Task A And Task B

Task A must happen first. It creates the tested Python payload API without
changing the live Simulation UI.

Task B follows only after Task A is accepted. It wires the Canvas renderer into
`/simulation` using the tested payload API and Tier 3D lifecycle contract.

## Next Production Step

Begin with `PRODUCTION_TASK_A_PAYLOAD_API.md`.

Do not wire Canvas into production until the payload schema, units,
Hamiltonian-state handling, drawable/non-drawable state rules, and tests are
accepted.
