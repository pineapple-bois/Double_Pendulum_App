# Tier 3A Animation Lifecycle

Tier 3A starts the animation and interaction tier by isolating the known Plotly
stale-playback risk.

Status: closed. Manual inspection found that `unique graph per run` fixes the
known stale-playback bug, and the strategy has been wired into the production
`/simulation` page.

The preview is workbench-only. It does not import or mount the production
`/simulation` page and does not change production callbacks, component IDs,
CSS, model behavior, plotting behavior, or solver behavior.

## How To Run

From the repository root:

```bash
python development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py
```

On systems where `python` is unavailable, use the project venv:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py
```

The preview starts at:

```text
http://127.0.0.1:8063/
```

To regenerate compact metrics without starting the Dash server:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py --metrics-only
```

## Files

- `animation_lifecycle_preview.py` - minimal Dash lifecycle preview.
- `TIER_3A_ANIMATION_LIFECYCLE.md` - investigation report and first evidence.
- `tier3a_results.json` - compact generated metrics; no arrays or full Plotly JSON.

## Manual Reproduction Result

Observed result:

- `unique graph per run` fully fixed the stale-playback issue by inspection;
- `unique uirevision` and `fixed uirevision` had no noticeable difference;
- the production page now replaces graph instances inside stable output
  containers for successful runs, stale-input states, and validation errors.

## Original Manual Reproduction Focus

Use the preview to test:

- play animation, then rerun the same request;
- play animation, then switch model type;
- play animation, then switch system type;
- play animation, then switch initial-condition preset;
- play animation, then clear/reset;
- play animation, then trigger simulated failure;
- compare fixed graph identity, `uirevision`, and unique graph identity.

The report now records the manual result and Tier 3A closeout. Future work
should add automated browser regression coverage if Plotly playback can be
inspected reliably.
