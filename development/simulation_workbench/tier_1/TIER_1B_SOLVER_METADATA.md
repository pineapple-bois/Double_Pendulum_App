# Tier 1b Solver Metadata Capture

Tier: Phase 6 / Simulation Workbench Tier 1b
Date: 2026-05-29

## Summary

Tier 1 identified that the model classes called `solve_ivp` and then discarded
the returned `OdeResult`, keeping only `sol.y.T` as `pendulum.sol`. Tier 1b adds
compact production metadata capture while preserving existing simulation arrays,
plotting behavior, animation behavior, callbacks, component IDs, and UI.

## Previously Missing

Before this change, model instances did not retain:

- solver success
- solver status
- solver message
- function evaluation count
- Jacobian evaluation count
- LU decomposition count
- raw returned solver time samples
- requested versus returned time sample counts
- whether returned solver samples matched requested `t_eval`

The app could therefore render plausible-looking outputs without knowing
whether `solve_ivp` reported success.

## What Is Now Captured

Model instances now expose:

- `pendulum.solver_metadata`
- `pendulum.solver_time`

`solver_metadata` is a compact `SolverMetadata` dataclass under
`src/double_pendulum/models/metadata.py`. For the `solve_ivp` path it records:

- `integrator`
- `success`
- `status`
- `message`
- `nfev`
- `njev`
- `nlu`
- `requested_time_count`
- `returned_time_count`
- `requested_time_start`
- `requested_time_end`
- `returned_time_start`
- `returned_time_end`
- `returned_time_matches_requested`
- `solution_shape`
- `solver_kwargs`

The full SciPy `OdeResult` object is not stored.

## odeint Metadata

The `odeint` path remains behavior-preserving and exposes partial metadata.
Because `odeint` does not return the same status object as `solve_ivp` in the
current call path, these fields are intentionally `None`:

- `success`
- `status`
- `message`
- `nfev`
- `njev`
- `nlu`

The `odeint` metadata still records the integrator name, requested and returned
sample counts, time endpoints, returned-time match status, solution shape, and
explicit solver kwargs.

## Why This Improves Future Diagnostics

The Simulation page can eventually distinguish:

- a completed solve from a failed or partial solve;
- requested samples from returned samples;
- solver/runtime issues from plotting/rendering issues;
- visually plausible outputs from outputs backed by solver success evidence.

No live UI was changed in this task because Tier 1b is a model-layer trust
improvement. Future UI work should consume this metadata only after the result
contract and output composition are accepted.

## Remaining Blockers

- Hamiltonian initial-condition convention remains unaudited.
- Runtime energy arrays and energy drift diagnostics remain unavailable.
- Solver tolerances and method choices are still not exposed in the UI.
- The current theta-theta projection remains a state projection, not a validated
  full phase portrait.

## Validation

The new metadata path is covered by `tests/numerical/test_solver_metadata.py`.
The updated workbench baseline script records the compact metadata in
`development/simulation_workbench/tier_1/tier1_baseline_results.json` without
saving full solver results or large artifacts.
