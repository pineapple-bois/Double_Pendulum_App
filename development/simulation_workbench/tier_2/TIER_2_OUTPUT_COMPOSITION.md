# Tier 2 Output Composition Preview

Tier: Phase 6 / Simulation Workbench Tier 2
Date: 2026-05-29

## Summary

Tier 2 created a workbench-only Dash preview for the first coherent post-run
Simulation workspace composition. It uses real model outputs, solver metadata,
and compact rendering metrics.

This is a sense-check of inspectable objects. It is not a production redesign,
energy-validation task, chaos task, or final acceptance of any output.

## Deliberately Not Attempted

Tier 2 did not:

- modify the live `/simulation` page;
- modify production callbacks or component IDs;
- modify production CSS;
- change model behavior or solver defaults;
- add energy diagnostics;
- add chaos diagnostics or Poincare sections;
- save screenshots, Plotly HTML, full Plotly JSON, or large arrays.

## How To Run

From the repository root:

```bash
python development/simulation_workbench/tier_2/workspace_preview_app.py
```

The app starts at:

```text
http://127.0.0.1:8062/
```

To regenerate compact metrics:

```bash
python development/simulation_workbench/tier_2/tier2_metrics.py
```

## Tested Cases

The compact metrics script ran all four baseline combinations with the
`nonzero velocities` preset, `3.0` seconds, and `120` samples per second:

| Model | System | Requested samples | Solver success | Returned samples |
| --- | --- | ---: | --- | ---: |
| simple | lagrangian | `360` | true | `360` |
| simple | hamiltonian | `360` | true | `360` |
| compound | lagrangian | `360` | true | `360` |
| compound | hamiltonian | `360` | true | `360` |

The nonzero preset is:

```text
[45.0, -30.0, 10.0, -5.0]
```

This keeps the Tier 1D Hamiltonian velocity-to-momentum convention exercised.

## Preview States

Empty state:

The app starts with a nonblank empty state listing the planned regions: run
summary, numerical diagnostics, physical motion, time series, and theta-theta
state projection. It also states that energy and chaos claims are absent.

Successful run state:

The app renders a run summary, numerical diagnostics, warnings, rendering
metrics, physical motion figure, angular displacement time series, and
theta-theta state projection.

Failure or invalid state:

The app includes a checkbox that previews a simulated invalid/failure state. It
does not force a real solver failure. The state demonstrates that old plots
should be hidden or clearly stale, and that the request/debug message should be
visible.

## Output Composition

The first-pass composition contains five candidate regions:

- run summary;
- numerical diagnostics;
- warnings and limits;
- physical motion preview;
- angular displacement time series;
- theta-theta state projection.

The warning panel is counted as part of the diagnostics/summary surface in the
compact metrics, so `output_panel_count` is `5`.

## Metrics Summary

Metrics are from `tier2_preview_results.json`. Plotly JSON sizes are compact
payload proxies from `len(fig.to_json())`; full figure JSON was not saved.

| Case | Model build | Composition total | Animation frames / JSON | Time-series points / JSON | Projection points / JSON | Warnings |
| --- | ---: | ---: | --- | --- | --- | ---: |
| simple lagrangian | `2.1343s` | `2.2701s` | `36 / 34264` | `720 / 35165` | `360 / 21482` | `3` |
| simple hamiltonian | `0.3508s` | `0.4784s` | `36 / 34341` | `720 / 35119` | `360 / 21435` | `4` |
| compound lagrangian | `2.0868s` | `2.1759s` | `36 / 34511` | `720 / 35161` | `360 / 21477` | `3` |
| compound hamiltonian | `0.4242s` | `0.5236s` | `36 / 34416` | `720 / 35161` | `360 / 21478` | `4` |

The animation method decimates frames by using every tenth sample. For `360`
samples, it builds `36` frames.

## Key Observations

- The run summary is useful because it keeps user-facing initial conditions and
  internal solver-state convention visible.
- Solver metadata belongs near the output, not hidden in developer logs.
- The warning panel is necessary; otherwise the figures look more scientifically
  accepted than Tier 1 supports.
- The animation is the most interaction-sensitive candidate because frame count
  and payload size grow with requested samples.
- The current time-series output is angle-only and should be labelled that way.
- The theta-theta output must be called a state projection, not a phase portrait.
- A failure state should hide or mark stale figures; attractive stale plots are
  worse than no plots.

## Candidate Decisions

| Output | Decision |
| --- | --- |
| Empty state | Candidate for production promotion after copy/layout refinement |
| Run summary | Candidate for production promotion |
| Numerical diagnostics | Candidate for production promotion with careful language |
| Physical motion preview | Accept for preview; production should wait for Tier 3 animation/payload study |
| Angular displacement time series | Candidate for production promotion if labelled as angle-only |
| Theta-theta state projection | Revise label/copy before production; accept for preview |
| Failure/invalid state | Accept for preview; production needs callback-state design |

See `OUTPUT_DECISIONS.md` for the detailed records.

## Recommendation

Next recommended task: Tier 3 animation and interaction experiments.

Reason:

Tier 2 suggests a coherent post-run composition, but the animation is the
highest-cost and most interaction-sensitive output. Before promotion, Tier 3
should measure animation frame strategy, payload growth, play/pause/scrub
requirements, and stale/failure behavior under repeated runs.

Production promotion can begin in parallel only for low-risk text surfaces such
as run summary and solver diagnostics, provided the copy preserves the Tier 1
trust boundary.
