# Tier 3B Plotly Strategy Comparison

Tier: Phase 6 / Simulation Workbench Tier 3B
Date: 2026-05-29

## Summary

Tier 3B compares Plotly-based options for the physical-motion panel after Tier
3A established that `unique graph per run` fixes the known stale-playback bug.

Current status: parked after first evidence pass.

The useful takeaway is not that Plotly is clearly the right long-term motion
renderer. The metrics mostly show that Plotly can be made acceptable enough
with careful lifecycle handling. The strongest product signal is that
selected-time inspection is valuable, while reduced-frame autoplay is not a
strong direction.

This is a workbench evidence task. It does not redesign the production
`/simulation` page, change model behavior, change solver defaults, add energy
diagnostics, add chaos diagnostics, or introduce Canvas.

## What Tier 3B Tested

The workbench preview compares four Plotly strategies:

- current Plotly frames: the existing `animate_pendulum` style with frame step
  10;
- reduced Plotly frames: a workbench-only coarser frame sequence with frame
  step 25;
- Plotly static scrubber: no frames; a Plotly slider restyles the pendulum
  trace;
- server-selected static frame: no frames; Dash builds a single selected-frame
  figure.

All strategies are mounted with unique graph identity per run. This intentionally
inherits the Tier 3A lifecycle fix so Tier 3B can focus on payload, interaction,
and production-candidate shape.

## How To Run

Preview app:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3b_plotly_strategies/plotly_strategy_preview.py
```

Metrics only:

```bash
.venv/bin/python development/simulation_workbench/tier_3/tier_3b_plotly_strategies/plotly_strategy_preview.py --metrics-only
```

The preview app starts at:

```text
http://127.0.0.1:8064/
```

## Case Matrix

| Case | Model | System | Preset | Duration | Samples |
| --- | --- | --- | --- | ---: | ---: |
| short simple Lagrangian | simple | Lagrangian | nonzero velocities | `4.0s` | `640` |
| moderate compound Hamiltonian | compound | Hamiltonian | nonzero velocities | `6.0s` | `1200` |
| larger simple Lagrangian | simple | Lagrangian | small angle | `8.0s` | `2000` |

The nonzero-velocity preset keeps the Tier 1D Hamiltonian convention in play for
the compound Hamiltonian case.

## Metrics Summary

Compact metrics were generated into `tier3b_results.json`. The table below
summarizes figure build time and Plotly payload size. Model construction time is
stored in the JSON separately and is not interpreted as rendering time.

| Case | Strategy | Frames | Slider steps | Figure build | JSON bytes |
| --- | --- | ---: | ---: | ---: | ---: |
| short simple Lagrangian | current frames | `64` | `0` | `0.0242s` | `54406` |
| short simple Lagrangian | reduced frames | `26` | `0` | `0.0102s` | `49578` |
| short simple Lagrangian | static scrubber | `0` | `32` | `0.0062s` | `47983` |
| short simple Lagrangian | selected frame | `0` | `0` | `0.0034s` | `43127` |
| moderate compound Hamiltonian | current frames | `120` | `0` | `0.0245s` | `95279` |
| moderate compound Hamiltonian | reduced frames | `48` | `0` | `0.0157s` | `86287` |
| moderate compound Hamiltonian | static scrubber | `0` | `60` | `0.0055s` | `83642` |
| moderate compound Hamiltonian | selected frame | `0` | `0` | `0.0035s` | `74576` |
| larger simple Lagrangian | current frames | `200` | `0` | `0.0361s` | `158897` |
| larger simple Lagrangian | reduced frames | `80` | `0` | `0.0237s` | `143997` |
| larger simple Lagrangian | static scrubber | `0` | `100` | `0.0066s` | `139773` |
| larger simple Lagrangian | selected frame | `0` | `0` | `0.0034s` | `124572` |

## Observations

Current Plotly frames remain usable for short runs, but payload grows directly
with frame count. The larger case reached `200` frames and about `159 KB` of
Plotly JSON for the motion figure alone.

Reduced frames are the weakest strategic signal in this pass. They cut visible
motion frames aggressively, but the JSON savings are modest relative to the UX
compromise. In the larger simple Lagrangian case, current frames use `200`
frames and about `159 KB`; reduced frames cut to `80` frames but still sit near
`144 KB`. The same pattern appears in the short and moderate cases: large
frame-count cuts, relatively small payload savings. This degrades the thing the
user actually sees while only partially addressing payload.

The static scrubber removes Plotly animation frames entirely and produces
smaller payloads than frame playback in every measured case. It also has faster
figure-build times and avoids hidden queued playback. In the larger case it
builds in about `0.0066s` with `0` frames and `100` slider steps, compared with
current frames at about `0.0361s` and `200` frames. This suggests a strong
interaction idea: selected-time inspection is valuable, even if Plotly is not
the final playback renderer.

The server-selected frame has the smallest figure payload because it sends only
one visible motion state. In the current workbench preview it rebuilds the model
on scrub, so it should not be promoted as-is. Its real value is as a design
signal: a selected-frame interaction can be very compact if future architecture
stores trusted position arrays and updates only the selected motion state.

Overall, Tier 3B should be read as evidence that Plotly is workable, not as
evidence that Plotly animation frames are the right long-term renderer.

## Lifecycle And Reset Behavior

Tier 3B does not reopen the Tier 3A stale-playback decision. Every preview run
uses unique graph identity. Clear and simulated failure states also replace the
graph instance, matching the production mitigation pattern.

Manual browser responsiveness has not yet been recorded for all strategies.
The preview exists so those observations can be added without touching
production.

## Strategy Decisions

Current Plotly frames: revise.

They are acceptable as the legacy baseline and can remain in production with
the Tier 3A graph-identity guard, but they are not the best default candidate
for a future redesigned workspace.

Reduced Plotly frames: reject as a serious product direction.

Reduced frames solve the wrong problem. They degrade playback smoothness and
still leave most of the payload in place. They may remain a tactical emergency
knob for unusually heavy runs, but they should not be treated as the main
Simulation workspace direction.

Static scrubber: strong candidate for safe inspectable motion.

It has lower payload, no queued animation frames, and clearer user control. It
may be the better first motion composition if the product values trust and
inspection over continuous playback. The deeper product insight is selected-time
inspection: users should be able to inspect exactly where the system is at a
chosen time, regardless of the eventual playback renderer.

Server-selected frame: defer.

The concept is compact, but the current implementation is too server-heavy for
scrubbing because it rebuilds the model. Revisit only after a result contract
or clientside data path exists. Treat it as pointing toward the right
architecture rather than being the architecture itself.

Clientside Plotly trace update: defer.

It may combine compact payload with smoother interaction, but it introduces
custom JavaScript complexity. It belongs after the interaction contract is
clearer, not as a casual Tier 3B addition.

## Recommendation

Plotly remains credible for the near-term production motion view if all motion
graphs use unique graph identity per run and if frame count is bounded.

For the future Simulation workspace, prefer this order:

1. Static scrubber as the safest inspectable motion candidate.
2. Current Plotly frames only as the legacy baseline.
3. Server-selected frame and clientside trace update as deferred implementation
   ideas.
4. Reduced Plotly frames rejected except as a possible emergency cap.

Recommended next work:

- park Tier 3B until the interaction contract clarifies whether selected-time
  inspection is the primary motion interaction;
- proceed to Tier 3D interaction contract to decide whether autoplay, selected
  time, scrubber, or a hybrid belongs in the future workspace;
- defer Tier 3C Canvas unless manual responsiveness or payload evidence shows
  Plotly is still too fragile or expensive.

## What This Does Not Prove

This comparison does not prove physical correctness, energy conservation,
long-duration stability, browser memory safety under many repeated runs, or
the final production renderer decision. It only compares compact Plotly motion
payloads and interaction shapes using the current trusted Tier 1/Tier 2
boundaries.
