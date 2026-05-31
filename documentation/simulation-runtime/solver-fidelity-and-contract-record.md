# Simulation Solver Fidelity And Contract Record

Date: 2026-05-31

## Purpose

Phase 8 investigated mathematical fidelity, simple-model
Lagrangian/Hamiltonian drift, solver cost, app-like runtime cost, and
solver-failure/result contracts before broad production solver-policy changes.
The work moved from exploratory evidence into production scaffolding and tests
for explicit solver policy, solver metadata, and non-render-safe failed
results.

## Evidence Locations

These local evidence paths may be ignored and absent from a fresh tracked
checkout. This document is the durable summary.

- `development/math_fidelity/BASELINE_REVIEW.md`
- `development/math_fidelity/DRIFT_INVESTIGATION.md`
- `development/math_fidelity/SOLVER_COST_BENCHMARK.md`
- `development/math_fidelity/APP_LIKE_COST_BENCHMARK.md`
- `development/math_fidelity/SOLVER_POLICY_RECOMMENDATION.md`
- `development/solver_contract/SOLVER_CONTRACT_AUDIT.md`
- `development/solver_contract/IMPLEMENTATION_PLAN.md`
- `development/solver_contract/UX_PERFORMANCE_INSPECTION.md`

## Main Findings

- The observed simple-model Lagrangian/Hamiltonian mismatch was primarily
  solver-policy driven in the tested cases.
- Simple Hamiltonian initial angular velocities are converted to canonical
  momenta correctly in the tested production path.
- Bare default `solve_ivp` is risky as an unqualified app-facing simple-model
  policy.
- `dop853_moderate` became the leading simple-model default candidate:
  `method="DOP853"`, `rtol=1e-6`, `atol=1e-8`.
- `dop853_strict` remains the high-fidelity/reference candidate:
  `method="DOP853"`, `rtol=1e-9`, `atol=1e-11`.
- Solver failures must be non-render-safe. Failed or partial trajectories must
  not serialize as drawable Canvas success payloads.

## Production Scaffold Implemented

- `src/double_pendulum/models/solver_policy.py` defines explicit named solver
  policies.
- `src/double_pendulum/models/results.py` defines minimal result-state
  primitives and `render_safe`.
- `src/double_pendulum/models/metadata.py` records policy name, method,
  tolerances, solver status, function evaluations, requested/returned samples,
  returned-time match, and solution shape.
- Simple model constructors accept a `SolverPolicy`.
- Canvas payload serialization rejects failed solver metadata for drawable
  success payloads.
- Simulation callback results distinguish validation failures from solver
  failures with a failure reason.

## Temporary Phase 8 Diagnostic UI

The Simulation controls include a temporary integrator-policy selector below
Gravity. It is for manual Phase 8 inspection only and exposes named policies,
not raw tolerance inputs:

- `DOP853 moderate - default candidate`;
- `DOP853 strict - high fidelity`;
- `SciPy default - baseline/risky`.

The selector applies to simple-model Lagrangian and Hamiltonian runs. Compound
models do not claim this simple-model evidence-backed policy yet. The selector
should be removed or hidden in Phase 9 production layout work while retaining
the internal solver policy contract.

## Tests Added

New or updated tests cover:

- named solver policies and policy-to-kwargs mapping;
- passing policies into simple Lagrangian and Hamiltonian construction;
- simple Lagrangian/Hamiltonian agreement under the default candidate;
- simple energy drift smoke checks;
- Hamiltonian energy checks that reconstruct omega from canonical momenta;
- solver metadata policy fields;
- deterministic solver-failure metadata;
- failed solver results as non-render-safe;
- Canvas payload rejection of failed solver metadata for drawable success
  payloads;
- Simulation callback validation failure versus solver failure behavior;
- temporary integrator selector presence and policy mapping.

## Remaining Gaps

- Compound-model solver-policy evidence has not yet been gathered.
- Production payload schema and result contract should remain aligned as
  callback behavior evolves.
- Long-duration chaos behavior is out of scope for this pass.

Manual UX and loading-state inspection for the simple-model policies is
recorded in
`documentation/simulation-runtime/manual-ux-and-loading-state-inspection.md`.

## Phase 9 Note

Phase 9 should remove or hide the temporary integrator selector as part of
production layout/styling consolidation. The internal solver policy objects,
solver metadata, and non-render-safe failure contract should remain.
