# Tier 3D Event Matrix

Tier: Phase 6 / Simulation Workbench Tier 3D
Date: 2026-05-29

This matrix defines the expected interaction behavior for the future Simulation
workspace. It is renderer-agnostic, but it assumes the Tier 3C.2 direction of
one shared selected-frame state across physical motion, angular time series,
angular projection, and readout.

Central rule:

> No visual state may continue animating after its simulation result has been
> superseded.

## State Vocabulary

Simulation/result states:

- `empty`: no run has occurred in the page session.
- `running`: a new run is being generated.
- `success`: a current payload exists and matches visible controls.
- `stale`: controls changed after the last successful run.
- `failed`: validation, solver, or output generation failed.
- `cleared`: user intentionally cleared output.

Playback/inspection states:

- `idle`: selected frame is stable and playback is not active.
- `playing`: selected frame advances over time for the active run.
- `paused`: playback is stopped and selected frame is preserved.
- `scrubbing`: user is directly selecting a frame/time.
- `ended`: playback reached the final sample.
- `cancelled`: playback stopped because output was superseded, failed, cleared,
  or made stale.

## Matrix

| Event | Current State | Next State | Run ID Behavior | Selected-Frame Behavior | Animation-Loop Behavior | Payload Behavior | User-Visible Message / Status | Python Called? | JavaScript Local? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Initial page load | none | `empty` / `idle` | `run_id` absent or `0` | frame `0`, no selected time | no loop | no payload | Useful empty state describing what will appear after run | no | yes |
| Run clicked from empty state | `empty` / `idle` | `running`, then `success` / `idle` if run succeeds | allocate new unique run ID | reset to frame `0` | cancel any existing loop defensively | create success payload | `Run completed` plus summary/diagnostics | yes | no for run; yes for draw |
| Run clicked while animation is playing | `success` / `playing` | `running`, then `success` / `idle` if run succeeds | old run invalidated immediately; new run ID allocated | reset to frame `0` for new payload | old loop cancels before new result draws | replace old payload on success | `New run requested; previous playback cancelled` | yes | yes for cancellation |
| Run clicked while previous run is stale | `stale` / `cancelled` or `scrubbing` | `running`, then `success` / `idle` if run succeeds | stale run ID superseded; new run ID allocated | reset to frame `0` | no stale loop may resume | replace stale payload | `Rerun completed; output is current` | yes | yes for draw |
| Successful run completion | `running` | `success` / `idle` | new run ID becomes active | frame `0` | old loops already cancelled | active success payload stored | `Success` with run summary and metadata | no additional call | yes for initial draw |
| Validation failure | `empty`, `success`, `stale`, or `running` | `failed` / `cancelled` | may allocate failure epoch; must invalidate old active playback | reset to frame `0` | cancel loop immediately | no drawable success payload | validation error message | no solver call; validation only | yes for cancellation |
| Solver failure | `running` | `failed` / `cancelled` | failure epoch invalidates previous playback | reset to frame `0` | cancel loop immediately | no drawable success payload; retain solver metadata if available | solver status/message | yes | yes for cancellation |
| Output generation failure | `running` | `failed` / `cancelled` | failure epoch invalidates previous playback | reset to frame `0` | cancel loop immediately | no accepted drawable payload; partial output must not animate | output-specific failure message | yes if model ran | yes for cancellation |
| Clear clicked | any | `cleared` / `cancelled` | invalidate or remove active payload run ID | reset to frame `0` | cancel loop immediately | remove active payload | `Output cleared` | no | yes |
| Reset playback clicked | `success` or `stale` | simulation state unchanged / `idle` | unchanged | reset to frame `0` | cancel loop | keep payload | `Reset to first frame` | no | yes |
| Reset playback clicked | `failed`, `cleared`, or `empty` | unchanged / `cancelled` or `idle` | unchanged | frame `0` | no loop | no payload | `No active payload to reset` | no | yes |
| Play clicked | `success` / `idle`, `paused`, `scrubbing`, or `ended` | `success` / `playing` | unchanged; loop bound to active run ID | advance from selected frame; if `ended`, recommended restart from frame `0` | start one loop only | keep payload | `Playing run N` | no | yes |
| Play clicked | `stale` | `stale` / `cancelled` | unchanged stale run ID | preserve selected frame | do not start loop | keep stale payload inspectable | `Settings changed - rerun to play current output` | no | yes |
| Play clicked | `failed`, `cleared`, or `empty` | unchanged / `cancelled` or `idle` | unchanged | frame `0` | do not start loop | no payload | `Cannot play without a successful payload` | no | yes |
| Pause clicked | `success` / `playing` | `success` / `paused` | unchanged | preserve selected frame | cancel loop | keep payload | `Paused` | no | yes |
| Pause clicked | not playing | simulation state unchanged / current playback state or `idle` | unchanged | preserve selected frame | no loop | unchanged | `Playback is not active` | no | yes |
| Scrub while idle | `success` / `idle` | `success` / `scrubbing` | unchanged | set to scrubbed frame/time | no loop | keep payload | selected time/state readout updates | no | yes |
| Scrub while playing | `success` / `playing` | `success` / `scrubbing` | unchanged | set to scrubbed frame/time | cancel loop; scrub pauses playback | keep payload | `Scrubbed to frame N` | no | yes |
| Scrub after failure | `failed` / `cancelled` | unchanged | unchanged | frame remains `0` | no loop | no drawable payload | `No inspectable payload` | no | yes |
| Input changed after successful run | `success` | `stale` / `cancelled` | active run ID remains as last result, but marked stale | preserve selected frame for inspection | cancel loop | keep payload, mark stale | `Settings changed - rerun to update` | no | yes |
| Model type changed after successful run | `success` | `stale` / `cancelled` | same as input change | preserve selected frame | cancel loop | keep payload, mark stale | `Model changed - rerun to update` | no | yes |
| System type changed after successful run | `success` | `stale` / `cancelled` | same as input change | preserve selected frame | cancel loop | keep payload, mark stale | `System changed - rerun to update` | no | yes |
| Preset changed after successful run | `success` | `stale` / `cancelled` | same as input change | preserve selected frame | cancel loop | keep payload, mark stale | `Preset changed - rerun to update` | no | yes |
| Axes/grid toggled | `success` or `stale` | simulation/playback state unchanged | unchanged | unchanged | unchanged; redraw only | unchanged | visual option updated | no | yes |
| Trail toggled, if present | `success` or `stale` | simulation/playback state unchanged | unchanged | unchanged | unchanged; redraw only | unchanged | trail option updated | no | yes |
| Rapid repeated runs | any | last completed request wins; final state `success` or `failed` | each request gets a new epoch/run ID; older completions must not reactivate | reset to frame `0` for winning run | every prior loop cancelled | winning payload only | `Latest run active` or latest failure | yes | yes for cancellation |
| Browser resize | `success` or `stale` | unchanged | unchanged | unchanged | unchanged | unchanged | renderer redraws at new size | no | yes |
| Playback reaches final sample | `success` / `playing` | `success` / `ended` | unchanged | final frame | stop loop | keep payload | `Playback ended` | no | yes |
| Clear clicked while running | `running` | `cleared` / `cancelled` | pending run epoch invalidated | frame `0` | cancel any old loop | discard old/pending payload | `Output cleared` | no additional call | yes |
| Failure arrives after newer success | older pending `running`, newer `success` | newer `success` remains active | older failure epoch ignored if not active | unchanged for newer run | no change to newer loop | keep newer payload | no stale older failure should overwrite current run | no | yes |

## Production Notes

- The production implementation should use a run epoch or equivalent identity
  for every request, including failure and clear events.
- Stale output can remain inspectable, but production styling must make it
  visibly different from current output.
- Display-only options such as axes, grid, and trail must not mark output stale.
- Scrubbing should pause playback because selected-frame inspection is an
  explicit user action.
- The event matrix deliberately avoids energy, chaos, and physical validation
  claims.
