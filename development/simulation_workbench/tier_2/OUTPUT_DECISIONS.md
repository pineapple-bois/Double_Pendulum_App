# Tier 2 Output Decisions

Tier: Phase 6 / Simulation Workbench Tier 2
Status: preview decision records, not production acceptance

## Candidate: Empty State

Question answered:

What will appear here after a run?

Required data:

No simulation data. It needs only the planned output regions and current trust
boundary.

What could mislead the user:

An empty workspace can look broken. Overexplaining can turn the Simulation page
back into documentation.

Numerical evidence required:

None for the empty state, but it must accurately describe which outputs are
backed by Tier 1.

Rendering or callback cost:

Negligible.

Decision:

Candidate for production promotion after copy and layout refinement.

## Candidate: Run Summary

Question answered:

What exactly did I simulate?

Required data:

Model type, system type, parameters, user-facing initial conditions, internal
solver-state convention, time interval, sample count, solver method, and
Hamiltonian conversion note where relevant.

What could mislead the user:

If user-facing angular velocities and Hamiltonian momenta are collapsed into one
field, users may misunderstand what the solver used internally.

Numerical evidence required:

Tier 1D initial-condition convention evidence and solver metadata availability.

Rendering or callback cost:

Low. It is text-only and uses data already available on model instances.

Decision:

Candidate for production promotion. It should be concise in the production UI
but keep user request and solver state distinct.

## Candidate: Numerical Diagnostics

Question answered:

Did the numerical solve appear to complete cleanly?

Required data:

Solver success, status, message, requested and returned sample counts, `nfev`,
`njev`, `nlu`, solution shape, finite-value check, monotonic-time check, and
initial-state consistency.

What could mislead the user:

Green solver metadata can be mistaken for complete physical validation.
Diagnostics must say that energy, chaos, and long-duration behavior are not
validated.

Numerical evidence required:

Tier 1b solver metadata capture and Tier 1 baseline checks.

Rendering or callback cost:

Low. The checks are cheap relative to model construction and figure building.

Decision:

Candidate for production promotion, with careful language and no energy drift
claim yet.

## Candidate: Physical Motion Preview

Question answered:

What physical motion did this simulation produce?

Required data:

Position arrays from `precompute_positions()` and the existing animation method.

What could mislead the user:

Smooth animation can look authoritative even when energy behavior and deeper
physical validation are not established.

Numerical evidence required:

Tier 1 position finite-value and shape checks, solver success, and clear warning
that this is not a conservation or chaos diagnostic.

Rendering or callback cost:

Highest of the current outputs because it carries frames and path traces. In
the Tier 2 metric run, animation payloads were about `34 KB` for `360` samples
with `36` frames.

Decision:

Accept for preview. Candidate for production only after Tier 3 investigates
animation interaction and payload strategy.

## Candidate: Angular Displacement Time Series

Question answered:

How did the angular state evolve over time?

Required data:

Time samples and the first two state columns, `theta1` and `theta2`.

What could mislead the user:

The current graph shows angles only. It does not show angular velocities,
momenta, energy, or numerical error.

Numerical evidence required:

Tier 1 finite-value, monotonic-time, shape, and solver-success checks.

Rendering or callback cost:

Moderate. In the Tier 2 metric run, time-series payloads were about `35 KB` for
`720` plotted points.

Decision:

Candidate for production promotion if labelled as angular displacement over
time, not a complete state diagnostic.

## Candidate: Theta-Theta State Projection

Question answered:

What reduced relationship is visible between the two angle coordinates?

Required data:

The first two state columns, `theta1` and `theta2`.

What could mislead the user:

Calling it a phase portrait overclaims. It is a reduced theta-theta projection,
not a full phase-space view.

Numerical evidence required:

Tier 1 shape and finite-value checks. Full phase-space or chaos claims would
need additional evidence.

Rendering or callback cost:

Moderate to low. In the Tier 2 metric run, projection payloads were about
`21 KB` for `360` plotted points.

Decision:

Revise label and copy before production. Accept for preview only as
`Theta-theta state projection`.

## Candidate: Failure Or Invalid State

Question answered:

What should the workspace show when validation or output generation fails?

Required data:

Validation or solver message, requested model/system/preset values, and a clear
status that figures are unavailable or stale.

What could mislead the user:

Leaving old graphs visible without a stale-state warning can imply the failed
request generated those outputs.

Numerical evidence required:

No new numerical evidence for simulated failure preview. Production promotion
requires real validation and solver failure paths.

Rendering or callback cost:

Low. Text-only.

Decision:

Accept for preview. Production promotion needs a dedicated callback-state plan.
