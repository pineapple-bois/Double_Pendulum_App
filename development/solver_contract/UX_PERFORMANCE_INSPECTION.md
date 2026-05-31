# UX Performance Inspection Checklist

Date: 2026-05-31

This checklist is for manual inspection after the solver-policy scaffold and
failure contract are in place. It is not a pytest benchmark plan. Pytest should
stay focused on deterministic correctness and contract behavior, not long
interactive performance measurements.

## Setup

1. Start the app locally using the normal development workflow.
2. Open `/simulation`.
3. Keep browser devtools available if payload transfer, JSON parse, or Canvas
   rendering needs inspection.
4. Stop the exact Dash process you started after inspection.

## Runs To Inspect

For each run, record subjective latency as:

```text
instant / acceptable / slow
```

Also note whether the loading state appears, clears, and leaves the page in the
expected final state.

## Temporary Integrator Selector

The Simulation page currently includes `Integrator policy (temporary Phase 8
diagnostic)` below the Gravity control. This selector is for manual comparison
during Phase 8 only. It should be removed or hidden during Phase 9 production
layout work.

Inspect each simple-model case with:

- `DOP853 moderate - default candidate`;
- `DOP853 strict - high fidelity`;
- `SciPy default - baseline/risky`.

For each policy, confirm that diagnostics reflect the selected policy when
visible:

- policy name;
- method;
- `rtol`;
- `atol`;
- solver success/status/message;
- requested versus returned samples.

### Default Simple Run

- Model: Simple
- Formulations: Euler-Lagrange and Hamiltonian
- Initial state: current default controls
- Durations: 10s, 30s, 60s
- Expected: run completes, Canvas output is drawable, playback controls enable
  appropriately.

### Screenshot-Like Simple Case

- Model: Simple
- Initial state: `[0, 60, 0, 0]`
- Formulations: Euler-Lagrange and Hamiltonian
- Durations: 10s, 30s, 60s
- Expected: run completes, no stale animation is shown as current output.

### Nonzero-Velocity Case

- Model: Simple
- Initial state: `[90, 0, 572.95, -458.37]`
- Suggested parameters from evidence lab when available:
  `l1=1`, `l2=1.5`, `m1=3`, `m2=1`, `g=9.81`
- Formulations: Euler-Lagrange and Hamiltonian
- Durations: 10s, 30s, 60s
- Expected: run completes under the selected policy or fails cleanly with no
  drawable success payload.

### Baseline/Risky Failure Recovery

- Policy: `SciPy default - baseline/risky`
- Use the nonzero-velocity case at 60s if it is still a failure-prone local
  fixture.
- Expected: if the solver fails, the run is marked failed, playback is
  cancelled or disabled, and no stale animation is presented as current
  output.

## Failure-State Checks

If a solver failure or forced failure path is available in a local branch:

- Confirm the run-status area reports a failure rather than success.
- Confirm diagnostics show solver status/message and method/tolerances when
  exposed.
- Confirm the Canvas does not keep a stale successful animation as current
  output.
- Confirm playback is cancelled or disabled.
- Confirm failed payloads do not contain drawable arrays.

## Diagnostics To Note

When exposed by the UI, record:

- solver policy name;
- method;
- `rtol`;
- `atol`;
- solver success/status/message;
- function evaluations;
- requested versus returned samples.

## Optional Browser Devtools Notes

Record only if useful:

- payload transfer size;
- JSON parse time;
- main-thread rendering spikes;
- Canvas frame-rate issues;
- any console errors.

## Sign-Off Questions

- Are 10s runs effectively instant?
- Are 30s runs acceptable for teaching use?
- Are 60s runs acceptable under the selected simple-model policy?
- Do Hamiltonian and Lagrangian runs feel comparable enough for the same
  default policy?
- Does a failure state feel clear and recoverable?
- Is any perceived slowness caused by solving, payload transfer, JSON parsing,
  or Canvas rendering?
