# Tier 3E Renderer Decision

Tier 3E consolidates the Canvas renderer workbench evidence into a production
promotion plan.

It does not wire Canvas into the production `/simulation` page. It defines what
the next production task should build, test, and keep reversible.

## Files

- `CANVAS_RENDERER_API.md` - proposed Python payload contract and JavaScript
  renderer API.
- `CANVAS_STRESS_CHECKS.md` - stress cases, metrics, and remaining edge-case
  gaps.
- `TIER_3E_RENDERER_DECISION.md` - renderer recommendation and rationale.
- `PROMOTION_PLAN.md` - scoped production migration plan, test plan, rollback
  plan, and promotion gates.
- `canvas_stress_runner.py` - compact workbench-only stress runner.
- `tier3e_results.json` - compact stress metrics; no arrays are saved.

## Run Stress Checks

From the repository root:

```bash
python development/simulation_workbench/tier_3/tier_3e_renderer_decision/canvas_stress_runner.py
```

The runner exercises representative simple/compound and
Lagrangian/Hamiltonian cases, including larger angles and 20-second sample
sets. It records payload size, finite checks, solver metadata, and construction
timing. It does not open a browser and does not save full payload arrays.

## Decision Summary

Canvas is recommended as the preferred production candidate for physical motion
and synced selected-time inspection.

Plotly should remain available for richer analytical plots, fallback views,
hover/zoom/export behavior, and accessibility-sensitive inspection.

Reduced-frame Plotly animation should not be promoted as the main motion UX.

Tier 3E does not prove numerical correctness, energy conservation, chaos
diagnostics, or long-session browser memory behavior.
