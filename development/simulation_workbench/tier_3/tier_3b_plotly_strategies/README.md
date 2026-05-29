# Tier 3B Plotly Strategies

Tier 3B compares Plotly-based physical-motion strategies after Tier 3A fixed
the known stale-playback bug with `unique graph per run`.

Status: parked after first evidence pass. Plotly can be made acceptable enough,
but reduced frames are rejected as a serious product direction. The strongest
signal is that selected-time inspection is valuable, especially through the
static scrubber and selected-frame concepts.

This directory is workbench-only. It does not import or mount the production
`/simulation` page and does not change production callbacks, component IDs,
CSS, model behavior, plotting behavior, or solver behavior.

## How To Run

From the repository root:

```bash
python development/simulation_workbench/tier_3/tier_3b_plotly_strategies/plotly_strategy_preview.py
```

On systems where `python` is unavailable, use the project venv:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3b_plotly_strategies/plotly_strategy_preview.py
```

The preview starts at:

```text
http://127.0.0.1:8064/
```

To regenerate compact metrics without starting the Dash server:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3b_plotly_strategies/plotly_strategy_preview.py --metrics-only
```

## Files

- `plotly_strategy_preview.py` - minimal Dash preview and compact metrics runner.
- `TIER_3B_PLOTLY_STRATEGIES.md` - comparison report and recommendation.
- `tier3b_results.json` - compact generated metrics; no arrays or full Plotly JSON.

## Strategies Compared

- Current Plotly frames.
- Reduced Plotly frames.
- Plotly static scrubber.
- Server-selected static frame.

All strategies use a unique graph instance per run in the preview, because Tier
3A established that graph identity replacement is the accepted lifecycle guard.

## Reading The Results

Treat the JSON as measurement evidence and the report as interpretation. Tier
3B measures Python-side figure payload and construction cost. Browser
responsiveness, repeated-run memory behavior, and exact playback feel still
require manual inspection or future browser automation.

Key interpretation:

- reduced frames make a large UX compromise for modest JSON savings;
- static scrubber removes hidden Plotly animation frames and is the strongest
  inspectable Plotly candidate;
- server-selected frame is architecturally interesting but not production-ready
  while scrub rebuilds the model;
- Tier 3B should wait for the interaction contract before further development.
