# Tier 2 Simulation Workspace Preview

Tier 2 is a workbench-only preview of a coherent post-run Simulation workspace.
It uses real model outputs and compact rendering metrics, but it does not
redesign the production `/simulation` page.

## How To Run

From the repository root:

```bash
python development/simulation_workbench/tier_2/workspace_preview_app.py
```

The app starts on:

```text
http://127.0.0.1:8062/
```

To regenerate compact metrics:

```bash
python development/simulation_workbench/tier_2/tier2_metrics.py
```

## Files

- `workspace_preview_app.py` - self-contained Dash preview app.
- `output_composition.py` - workbench-only simulation and output composition helpers.
- `tier2_metrics.py` - compact figure and preview metrics helpers.
- `tier2_preview_results.json` - compact generated metrics; no arrays or figure JSON.
- `TIER_2_OUTPUT_COMPOSITION.md` - report for this preview.
- `OUTPUT_DECISIONS.md` - candidate output decision records.

## Tier 1 Assumptions

Tier 2 builds on the Tier 1 closeout:

- representative simple/compound and Lagrangian/Hamiltonian runs construct;
- solver metadata is retained;
- time/state/position arrays pass foundational shape and finite-value checks;
- Hamiltonian requests use UI angular velocities and convert to canonical
  momenta before solving.

## Not Yet Trusted

This preview does not validate energy conservation, chaos diagnostics,
long-duration behavior, tolerance sensitivity, solver-method equivalence,
browser memory behavior, or the theta-theta projection as a full phase portrait.

Read `OUTPUT_DECISIONS.md` as a decision aid, not as production acceptance.
