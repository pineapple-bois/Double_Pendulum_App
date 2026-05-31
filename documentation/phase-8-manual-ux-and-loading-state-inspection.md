# Phase 8 Manual UX And Loading-State Inspection

Date: 2026-05-31

This note records the closeout-oriented Phase 8 manual inspection for simple
solver policies, diagnostics freshness, and route/loading lifecycle behavior.
The detailed `development/solver_contract/` evidence directory is local-only
and ignored; this tracked note is the durable project record.

## Scope

Inspected simple-model runs with the temporary Phase 8 integrator selector:

- `simple_default`: DOP853 moderate, the default candidate;
- `simple_reference`: DOP853 strict, the reference/high-fidelity candidate;
- systems: Lagrangian and Hamiltonian;
- durations: 10s, 30s, and 60s;
- initial states:
  - default/low-energy `[0, 0, 0, 0]`;
  - screenshot-like `[0, 60, 0, 0]`;
  - nonzero-velocity `[90, 0, 572.95, -458.37]`.

Latency labels:

- instant: under 1s;
- acceptable: 1s to 4s;
- slow: over 4s;
- failed: did not produce a successful payload.

## Callback Timing Sweep

All inspected callback runs produced successful Canvas payloads.

| Policy | System | Durations | Inputs | Result |
| --- | --- | --- | --- | --- |
| DOP853 moderate | Lagrangian | 10s, 30s, 60s | all three | Mostly instant; first cold 10s default run was acceptable at 2.267s. |
| DOP853 moderate | Hamiltonian | 10s, 30s, 60s | all three | Instant; max observed 0.554s. |
| DOP853 strict | Lagrangian | 10s, 30s, 60s | all three | Instant; max observed 0.903s. |
| DOP853 strict | Hamiltonian | 10s, 30s, 60s | all three | Instant to acceptable; 60s nonzero-velocity case was acceptable at 1.055s. |

Representative 60s nonzero-velocity observations:

- moderate Lagrangian: success, instant, 0.560s, 41,054 function evaluations;
- moderate Hamiltonian: success, instant, 0.554s, 37,925 function evaluations;
- strict Lagrangian: success, instant, 0.903s, 87,755 function evaluations;
- strict Hamiltonian: success, acceptable, 1.055s, 85,643 function evaluations.

Conclusion: `dop853_moderate` feels acceptable as the simple-model default
candidate. `dop853_strict` also feels acceptable for Phase 8 inspection, though
it remains the reference/high-fidelity option rather than the default candidate.

## Browser Smoke

Observed in browser on `/simulation`:

- moderate Lagrangian run completed successfully, Canvas updated, playback
  controls enabled, diagnostics showed `simple_default`;
- switching to strict marked the previous output stale before rerun;
- strict Lagrangian rerun completed successfully and diagnostics showed
  `simple_reference`;
- switching from Lagrangian to Hamiltonian marked the previous output stale;
- strict Hamiltonian rerun completed successfully and diagnostics showed
  `simple_reference`;
- switching back to moderate marked the strict output stale;
- moderate Hamiltonian rerun completed successfully and diagnostics showed
  `simple_default`;
- changing an angle after success marked output stale, disabled Play, kept the
  scrubber inspectable, and labelled diagnostics as stale previous-run metadata;
- validation failure after editing a required input produced a non-render-safe
  failed state with no previous solver metadata shown as current;
- navigating away to `/equations` during or immediately after a run, then
  returning to `/simulation`, remounted an empty Simulation page and a fresh run
  worked without hard reload.

Loading/interrupted-state note: successful simple runs were generally too fast
for a persistent visible loading state to be reliably observed in the Python
status text. The important closeout behavior was verified: no sticky loading
state remained, stale/failed states were labelled, and fresh reruns worked.

## Stale Diagnostics Metadata

Issue reproduced/confirmed by inspection:

1. Run with DOP853 moderate.
2. Switch the integrator selector to DOP853 strict without rerunning.
3. Open diagnostics.

Before the fix, diagnostics could show the previous run's solver policy without
a clear stale marker, making old metadata look current.

Cause:

- stale payloads intentionally preserve the previous successful drawable arrays
  and solver metadata for inspection;
- `_render_solver_diagnostics(...)` rendered stale and success diagnostics with
  the same framing and success validation copy.

Fix:

- stale diagnostics now explicitly say they describe the previous successful
  run and instruct the user to rerun for current controls;
- stale diagnostics now say previous payload validation passed before inputs
  changed, rather than reporting a current validation pass;
- validation failures clear solver metadata from diagnostics instead of
  presenting previous success metadata as current.

## Tests Added Or Updated

- Diagnostics update after integrator policy change and rerun.
- Stale diagnostics are labelled as previous-run metadata.
- Validation failures after success do not reuse previous success diagnostics.
- Solver failures show current failed solver metadata and do not claim previous
  success metadata.
- Route remount still returns fresh memory-scoped Simulation stores.

## Remaining Risks

- Browser automation verified DOM-visible state and diagnostics text, but not
  Canvas pixels or renderer internals directly.
- Simple runs are fast enough that a dedicated long-running in-browser loading
  test would need artificial delay or a deliberately heavier scenario; that was
  not added to pytest.
- The temporary integrator selector still needs a Phase 9 remove/hide decision.
