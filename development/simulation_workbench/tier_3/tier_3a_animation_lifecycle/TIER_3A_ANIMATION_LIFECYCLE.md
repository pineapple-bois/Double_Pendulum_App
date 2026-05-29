# Tier 3A Animation Lifecycle

Tier: Phase 6 / Simulation Workbench Tier 3A
Date: 2026-05-29

## Summary

Tier 3A began the animation and interaction tier by isolating the known Plotly
stale-playback lifecycle risk in a small workbench preview.

The workbench preview exposed several identity strategies. Manual inspection
found that `unique graph per run` solved the stale-playback issue, while
`unique uirevision` and `fixed uirevision` did not show a noticeable difference
from each other.

The selected strategy has now been wired into the production `/simulation` page
as a narrow follow-up patch. The production callback now replaces the graph
components inside stable output containers for each run, input-stale state, and
validation-error state. This keeps the page shape intact while giving Plotly a
fresh graph instance so queued playback from a superseded result is cancelled.

This Tier 3A closeout did not modify model behavior, plotting math, solver
behavior, energy diagnostics, chaos diagnostics, Canvas rendering, or the broad
renderer strategy.

## Known Bug

The known risk:

If a Plotly animation is playing and the user changes model or simulation state,
the old animation may continue for the remaining queued playback time before
the new state fully takes over.

This is a trust issue because the user can see motion from one simulation while
the controls, summary, or diagnostics imply another simulation.

Expected future behavior:

- a new run cancels old animation immediately;
- clear/reset cancels old animation immediately;
- failure states do not allow old successful animations to keep playing;
- changed inputs either mark output stale or prevent stale playback;
- no visual state continues animating after its simulation result is superseded.

## Workbench Preview

Preview script:

```text
development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py
```

Run from the repository root:

```bash
python development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py
```

The local environment used for this task does not expose `python` on PATH, so
the verified command was:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py
```

The preview app starts at:

```text
http://127.0.0.1:8063/
```

Controls:

- model type: simple or compound;
- system type: Lagrangian or Hamiltonian;
- initial-condition preset;
- animation identity strategy;
- run animation;
- clear output;
- simulated failure.

Identity strategies exposed:

- fixed graph id;
- unique `uirevision`;
- fixed `uirevision`;
- unique graph per run.

The preview intentionally uses existing model classes and existing Plotly
animation output methods.

## Test Sequences To Attempt

Manual reproduction sequence:

1. Run animation.
2. Click Plotly's Play button inside the figure.
3. While motion is playing, click Run Animation again with the same request.
4. Repeat while switching model type.
5. Repeat while switching system type.
6. Repeat while switching initial-condition preset.
7. Repeat while clicking Clear Output.
8. Repeat while clicking Simulated Failure.
9. Repeat the above for each identity strategy.

Questions to answer:

- does stale playback happen when rerunning the same request?
- does stale playback happen when switching model type?
- does stale playback happen when switching system type?
- does stale playback happen when switching preset?
- does clear/reset stop old playback?
- does simulated failure stop old playback?
- do `uirevision` or graph identity changes appear relevant?

## Observed Behavior

Automated browser reproduction was not completed in the initial Tier 3A scaffold.
The preview app server was started successfully and exposed the intended manual
reproduction controls.

Manual follow-up inspection recorded the useful result:

- `unique graph per run` appeared to fully fix the stale-playback bug by
  inspection;
- there was no noticeable difference between `unique uirevision` and
  `fixed uirevision`;
- the strategy was promoted to production for the existing `/simulation` page;
- production-side manual verification after the patch confirmed the bug is fixed.

Current evidence status:

- stale playback before mitigation: known production bug by manual observation;
- `unique graph per run` relevance: confirmed useful by workbench inspection;
- production `/simulation` fix: confirmed by user manual inspection;
- `uirevision` relevance: not selected; no meaningful difference observed;
- clear/reset stop behavior: addressed by replacing graph instances with fresh
  empty graphs, but still worth including in future regression scripts;
- simulated failure stop behavior: production validation-error path also
  replaces graph instances, but future automated regression coverage would be
  useful.

## Metrics Gathered

Compact metrics were generated with:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/animation_lifecycle_preview.py --metrics-only
```

Request used:

- preset: nonzero velocities `[45.0, -30.0, 10.0, -5.0]`;
- duration: `4.0` seconds;
- sample count: `640`;
- frame decimation: current model method uses every tenth sample, yielding
  `64` frames.

| Model | System | Build time | Frames | Traces | Points | Approx JSON bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| simple | lagrangian | `0.0708s` | `64` | `3` | `1475` | `54385` |
| simple | hamiltonian | `0.0158s` | `64` | `3` | `1475` | `54381` |
| compound | lagrangian | `0.0154s` | `64` | `3` | `1475` | `54840` |
| compound | hamiltonian | `0.0164s` | `64` | `3` | `1475` | `54755` |

The compact results are stored in `tier3a_results.json`. No full Plotly JSON,
HTML, screenshots, images, or arrays were saved.

## Mitigation Decision

Accepted mitigation for this bug:

- assign unique graph identity per run;
- also replace graph instances on input-stale and validation-error paths;
- keep stable wrapper/container IDs so the surrounding layout and callbacks stay
  understandable;
- do not rely on `uirevision` as the primary stale-playback fix.

Production implementation notes:

- initial layout still contains the historical graph IDs;
- after a successful run, the graph components receive run-suffixed IDs;
- after changed inputs or validation errors, fresh empty graph instances replace
  old graph instances and the output containers are hidden;
- callbacks now target stable container `children` rather than stale-prone graph
  `figure` props.

Candidate items left for future Tier 3 work:

- define explicit play/pause/reset/scrub interaction contracts;
- measure reduced-frame payloads;
- test a static physical view plus scrubber;
- consider clientside trace updates only if future interaction requirements
  justify the extra complexity.

## Current Lifecycle Assessment

Status: fixed for the known production stale-playback bug.

The narrow Plotly lifecycle issue that started Tier 3A is closed for the current
production `/simulation` page by the `unique graph per run` strategy. The fix is
based on manual inspection, not an automated browser regression test.

Remaining risk:

- future interaction work can still reintroduce stale state if it updates only
  figure props instead of replacing graph identity;
- there is no automated browser test that presses Plotly Play and verifies
  cancellation;
- this does not decide the final renderer strategy for a redesigned Simulation
  workspace;
- this does not validate energy, chaos behavior, long-duration numerical
  stability, or broader scientific claims.

## Recommended Next Sub-Tier

Tier 3A is closed.

Recommended next work:

- add a small regression/smoke task later if browser automation can reliably
  exercise Plotly's Play button and detect stale playback;
- proceed to Tier 3D interaction contract when defining play, pause, reset,
  scrub, stale-output, and failure-state behavior for the future workspace;
- defer Tier 3C Canvas feasibility unless future payload or interaction evidence
  shows that Plotly remains too costly or fragile.
