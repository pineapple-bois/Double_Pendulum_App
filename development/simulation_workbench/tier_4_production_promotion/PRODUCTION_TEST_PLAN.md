# Production Test Plan

Tier: Phase 6 / Simulation Workbench Tier 4

This plan defines the checks required before Canvas production promotion is
accepted.

## Python Tests

Payload schema:

- required fields exist;
- schema version is present;
- status values are validated;
- drawable and non-drawable states are distinguished.

Payload arrays:

- `time` length equals `sample_count`;
- angular displacement array lengths equal `sample_count`;
- position array lengths equal `sample_count`;
- arrays are finite for success/stale payloads;
- time is monotonic;
- time endpoints match request.

Units:

- angular units are explicit;
- position units are explicit;
- user-facing initial-condition units are explicit;
- internal initial-state units/convention are explicit.

Solver metadata:

- metadata is included for successful solve payloads;
- requested and returned sample counts are included;
- solver success/status/message are included.

Representative cases:

- simple Lagrangian payload;
- simple Hamiltonian payload with nonzero angular velocities;
- compound Lagrangian payload;
- compound Hamiltonian payload with nonzero angular velocities;
- longer-duration/high-sample-count payload summary.

State behavior:

- failed payload does not contain drawable success arrays;
- cleared payload does not contain drawable success arrays;
- empty payload does not contain drawable success arrays;
- stale payload is distinguishable from success;
- no energy diagnostics are implied;
- Hamiltonian momentum is not mislabeled as angular velocity.

## Browser / Manual Smoke Checks

Page and run flow:

- Simulation page loads;
- useful empty state appears before first run;
- successful run renders Canvas workspace;
- run summary appears;
- numerical diagnostics appear.

Playback and inspection:

- play works;
- pause works;
- reset works;
- scrub updates motion;
- scrub updates time-series cursor/markers;
- scrub updates projection marker;
- scrub updates selected-time/state readout;
- playback updates synced views from the same selected-frame state.

Display options:

- axes toggle works;
- grid toggle works;
- optional trail toggle works if included;
- display toggles do not call Python;
- display toggles do not mark output stale.

Lifecycle:

- changing inputs after success marks output stale;
- stale output does not keep playing as current;
- rerun creates new run ID and cancels old animation;
- clear cancels playback;
- validation failure cancels playback;
- solver failure cancels playback;
- output-generation failure cancels playback;
- rapid repeated runs leave only the latest run active;
- browser resize redraws without changing selected frame.

Stress:

- longer-duration case around the old 20-second scenario if feasible;
- clear after large payload;
- failure after large payload;
- rerun after large payload;
- repeated-run responsiveness.

## Performance Checks

Record:

- payload size bytes;
- sample count;
- payload build time;
- callback duration where measurable;
- time to first useful visual;
- browser responsiveness;
- repeated-run behavior;
- long-duration/high-sample-count behavior.

Do not overinterpret workbench timings. Production checks should measure the
real callback path and browser behavior.

## Regression Checks

Run targeted existing tests relevant to:

- model construction;
- solver metadata;
- Hamiltonian initial-condition conversion;
- validation;
- app content or route smoke checks.

If production callbacks or page layout change, include integration tests or
manual route smoke checks for `/simulation`.

## Acceptance

Production promotion is accepted only when:

- Python payload tests pass;
- browser lifecycle checks pass;
- no stale playback is observed;
- no JavaScript physics is introduced;
- no energy or chaos claims are introduced;
- fallback/rollback remains available.
