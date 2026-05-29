# Tier 1D Option 1 Hamiltonian Conversion

Tier: Phase 6 / Simulation Workbench Tier 1D
Date: 2026-05-29

## Summary

Tier 1D implements the accepted Option 1 convention:

```text
User-facing request: [theta1, theta2, omega1, omega2]
```

This convention now applies to both Lagrangian and Hamiltonian simulations. For
Hamiltonian simulations, model construction converts the user-facing angular
velocities into canonical momenta before integration.

No Simulation page layout, Dash callback IDs, plotting behavior, animation
behavior, energy diagnostics, chaos diagnostics, or new visual outputs were
introduced in this task.

## Implementation

The conversion lives in the model layer:

- `src/double_pendulum/models/initial_conditions.py`
- `src/double_pendulum/models/hamiltonian.py`
- `src/double_pendulum/models/lagrangian.py`

The helper exposes the state labels and conversion function:

- `USER_INITIAL_CONDITION_NAMES`: `[theta1, theta2, omega1, omega2]`
- `LAGRANGIAN_STATE_VARIABLE_NAMES`: `[theta1, theta2, omega1, omega2]`
- `HAMILTONIAN_STATE_VARIABLE_NAMES`: `[theta1, theta2, p_theta_1, p_theta_2]`
- `angular_velocities_to_canonical_momenta(...)`
- `hamiltonian_solver_initial_conditions(...)`

`DoublePendulumLagrangian` now records the user-facing request separately but
keeps the existing solver state:

```text
solver state: [theta1, theta2, omega1, omega2]
conversion: degrees_to_radians
```

`DoublePendulumHamiltonian` now records the user-facing request separately and
solves with canonical momenta:

```text
solver state: [theta1, theta2, p_theta_1, p_theta_2]
conversion: angular_velocities_to_canonical_momenta
```

Model instances expose:

- `user_initial_conditions_degrees`
- `user_initial_conditions_radians`
- `user_initial_condition_names`
- `solver_state_variable_names`
- `solver_state_convention`
- `initial_condition_conversion`
- `initial_canonical_momenta` for Hamiltonian models
- `initial_conditions` as the internal solver state

This is not a full `SimulationResult`, but it gives future result-contract work
the necessary distinction between user request and solver state.

## Conversion Formula

The Hamiltonian conversion uses:

```text
p = B(q) @ omega
```

For the simple model:

```text
B(q) = [
  [(m1 + m2) * l1^2, m2 * l1 * l2 * cos(theta1 - theta2)],
  [m2 * l1 * l2 * cos(theta1 - theta2), m2 * l2^2],
]
```

For the compound model:

```text
B(q) = [
  [7/12 * M1 * l1^2 + 1/4 * M2 * l1^2,
   1/4 * M2 * l1 * l2 * cos(theta1 - theta2)],
  [1/4 * M2 * l1 * l2 * cos(theta1 - theta2),
   7/12 * M2 * l2^2],
]
```

The mapping depends on initial angles, model type, lengths, and masses. It is
not a simple unit conversion.

## Nonzero Evidence

The convention audit script was rerun after implementation:

```text
.venv/bin/python development/simulation_workbench/tier_1/tier1c_hamiltonian_convention.py
```

It checked:

```text
zero tail:    [45.0, -30.0, 0.0, 0.0]
nonzero tail: [45.0, -30.0, 10.0, -5.0]
```

Results:

| Model | Request | Hamiltonian tail matches canonical momenta | Max abs difference |
| --- | --- | --- | ---: |
| simple | zero tail | true | `0.0` |
| simple | nonzero tail | true | `0.0` |
| compound | zero tail | true | `0.0` |
| compound | nonzero tail | true | `0.0` |

Before Tier 1D, the nonzero simple and compound cases did not match. After Tier
1D, nonzero UI angular velocities are converted before solving.

## Test Coverage

New numerical tests in `tests/numerical/test_initial_condition_conventions.py`
cover:

- Lagrangian initial states preserve angular velocities.
- Simple Hamiltonian nonzero angular velocities convert to canonical momenta.
- Compound Hamiltonian nonzero angular velocities convert to canonical momenta.
- Zero angular velocities map to zero momenta.
- Hamiltonian internal state no longer treats nonzero angular velocities as
  direct momentum values.
- User-facing initial conditions and solver-state conventions are recorded.

Existing model-shape, finite-value, solver-metadata, derivation-fidelity,
validation, and app-content tests remain part of the targeted validation set.

## What Changed

Changed:

- Hamiltonian model construction now converts UI angular velocities to canonical
  momenta.
- Model instances distinguish user-facing initial conditions from solver state.
- Workbench baseline evidence records both user request and internal solver
  state.

Unchanged:

- The live Simulation page layout and controls.
- Dash callback IDs.
- Plotting and animation methods.
- Solver metadata behavior.
- Lagrangian angular-velocity behavior.
- Energy diagnostics, which remain unimplemented.

## Remaining Limits

This task resolves the input convention for Hamiltonian model construction. It
does not prove full physical correctness of all equations, long-duration
stability, energy conservation, browser responsiveness, or chaos diagnostics.

Energy diagnostics should still wait for a focused formula and state-convention
audit. The current theta-theta projection remains a two-angle state projection,
not a validated full phase portrait.
