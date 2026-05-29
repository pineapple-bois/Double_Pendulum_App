# Tier 1C Hamiltonian Convention Audit

Tier: Phase 6 / Simulation Workbench Tier 1C
Date: 2026-05-29
Evidence script: `development/simulation_workbench/tier_1/tier1c_hamiltonian_convention.py`
Compact results: `development/simulation_workbench/tier_1/tier1c_hamiltonian_convention_results.json`

## Summary

Tier 1C audited the current state convention mismatch between the UI-shaped
initial-condition request and the Hamiltonian model state. This task did not
change production UI, callbacks, component IDs, plotting, animation, model
behavior, equations, or validation.

The audit result was direct: the Lagrangian model uses angular velocities in
the last two state columns, while the Hamiltonian model uses canonical momenta.
At the time of the Tier 1C audit, the live UI labelled the final two inputs as
angular velocities and the Hamiltonian constructor applied `np.deg2rad(...)` to
those values as if they could occupy the momentum slots directly. Tier 1D
replaced that behavior with explicit angular-velocity to canonical-momentum
conversion.

## Current Lagrangian Convention

`DoublePendulumLagrangian` uses the state order:

```text
[theta1, theta2, omega1, omega2]
```

The constructor stores:

```python
self.initial_conditions = np.deg2rad(initial_conditions)
```

For the current UI request, that means angles entered in degrees become radians
and angular velocities entered as degrees per second are treated as radians per
second after conversion. The `_system` method unpacks the state as
`th1, th2, w1, w2`, and the lambdified first-order equations use
`theta1`, `theta2`, `omega1`, and `omega2`.

## Current Hamiltonian Convention

`DoublePendulumHamiltonian` uses the solver state order:

```text
[theta1, theta2, p_theta_1, p_theta_2]
```

The `_system` method unpacks the state as `th1, th2, p_th1, p_th2`, and the
lambdified Hamiltonian equations use `theta1`, `theta2`, `p_theta_1`, and
`p_theta_2`. In the symbolic math layer, `derive_canonical_momenta(...)`
computes momenta as derivatives of the Lagrangian with respect to angular
velocities, and `compute_hamiltonian(...)` builds Hamiltonian dynamics from the
momentum vector `[p_theta_1, p_theta_2]`.

That means the final two Hamiltonian state entries are canonical momenta, not
angular velocities. After Tier 1D, the constructor accepts UI-shaped angular
velocity inputs but converts the final two values before assigning
`self.initial_conditions`.

## Current UI Convention

The simulation controls present the final two initial-condition fields as
angular velocities. The callback flow passes the four UI values through to the
selected model class. After Tier 1D, `DoublePendulumHamiltonian` performs the
conversion to canonical momenta at the model boundary.

## Why The Tier 1 Zero-Velocity Baseline Was Inconclusive

The Tier 1 baseline used:

```text
[45.0, -30.0, 0.0, 0.0]
```

The last two values are zero. For both simple and compound models, zero angular
velocity maps to zero canonical momentum. Therefore the Hamiltonian tail looked
compatible in that case even though the nonzero convention had not been
verified. The zero-tail case was useful for array sanity but misleadingly safe
for convention evidence.

## Code Inspection Evidence

Relevant current behavior:

- `src/double_pendulum/models/lagrangian.py`: Lagrangian state is unpacked as
  `th1, th2, w1, w2`.
- `src/double_pendulum/models/hamiltonian.py`: Hamiltonian state is unpacked as
  `th1, th2, p_th1, p_th2`.
- `src/double_pendulum/math/functions.py`: `derive_canonical_momenta(...)`
  differentiates the Lagrangian with respect to angular velocities.
- `src/double_pendulum/math/functions.py`: `compute_hamiltonian(...)` builds
  the Hamiltonian from a mass/inertia matrix and the momentum vector
  `[p_theta_1, p_theta_2]`.

This is enough to establish that Hamiltonian initialization requires momenta in
the final two state slots.

## Script Evidence

Before the Tier 1D implementation, the Tier 1C script instantiated simple and
compound Lagrangian/Hamiltonian models for a zero-tail request and a nonzero-tail
request:

```text
zero tail:    [45.0, -30.0, 0.0, 0.0]
nonzero tail: [45.0, -30.0, 10.0, -5.0]
```

It then compared the Hamiltonian tail at that time against the canonical momenta
that would result if the UI tail were interpreted as angular velocity.

| Model | Request | Current Hamiltonian tail | Canonical momenta from UI velocities | Match | Max abs difference |
| --- | --- | --- | --- | --- | ---: |
| simple | zero tail | `[0.0, 0.0]` | `[0.0, 0.0]` | yes | `0.0` |
| simple | nonzero tail | `[0.1745329252, -0.0872664626]` | `[0.3264796279, -0.0420940176]` | no | `0.1519467027` |
| compound | zero tail | `[0.0, 0.0]` | `[0.0, 0.0]` | yes | `0.0` |
| compound | nonzero tail | `[0.1745329252, -0.0872664626]` | `[0.1397975487, -0.0396123253]` | no | `0.0476541373` |

Both nonzero cases show that directly passing UI-labelled angular velocities
into Hamiltonian momentum slots is not equivalent to converting velocities to
canonical momenta.

## Simple Model Velocity-To-Momentum Mapping

For the simple point-mass model, the momentum mapping has the form:

```text
p = B(q) @ omega
```

with:

```text
B(q) = [
  [(m1 + m2) * l1^2, m2 * l1 * l2 * cos(theta1 - theta2)],
  [m2 * l1 * l2 * cos(theta1 - theta2), m2 * l2^2],
]
```

So:

```text
p_theta_1 = ((m1 + m2) * l1^2) * omega1
          + (m2 * l1 * l2 * cos(theta1 - theta2)) * omega2

p_theta_2 = (m2 * l1 * l2 * cos(theta1 - theta2)) * omega1
          + (m2 * l2^2) * omega2
```

The mapping depends on model parameters and the starting angles; it is not just
a unit conversion.

## Compound Model Velocity-To-Momentum Mapping

For the compound rod model, the mapping is also:

```text
p = B(q) @ omega
```

with:

```text
B(q) = [
  [7/12 * M1 * l1^2 + 1/4 * M2 * l1^2,
   1/4 * M2 * l1 * l2 * cos(theta1 - theta2)],
  [1/4 * M2 * l1 * l2 * cos(theta1 - theta2),
   7/12 * M2 * l2^2],
]
```

The compound mapping is therefore also parameter- and angle-dependent. A future
implementation must handle simple and compound models explicitly.

## Can Lagrangian And Hamiltonian Outputs Be Compared Today?

Meaningful now:

- array shape, finite-value, monotonic-time, deterministic-repeat, and solver
  metadata checks for each model independently;
- behavior-preservation tests for the current code path;
- comparison of the first two angle columns only as rendered output behavior,
  not as proof of formulation equivalence.

Unsafe now:

- claiming that Lagrangian and Hamiltonian runs represent the same physical
  initial condition when both receive the same UI-labelled nonzero angular
  velocities;
- using Hamiltonian visual output as scientific validation of a velocity-based
  request;
- interpreting the theta-theta projection as a validated phase portrait.

Requires velocity-to-momentum conversion first:

- physical comparison between Lagrangian and Hamiltonian trajectories for the
  same user-entered angular velocities;
- energy consistency checks across formulations;
- accepted Hamiltonian diagnostics in the Simulation page.

Requires a later implementation change:

- a normalized result contract that records both UI initial conditions and the
  Hamiltonian internal momentum state;
- tests that prove nonzero UI angular velocities are converted before
  Hamiltonian construction or are intentionally exposed as momenta.

## Risks Of Doing Nothing

- Hamiltonian runs may look plausible while representing a different initial
  physical state than the UI implies.
- Zero-velocity examples can continue hiding the convention issue.
- Future energy or chaos diagnostics could be built on ambiguous state data.
- Users may compare Lagrangian and Hamiltonian outputs and infer equivalence
  that the app has not established.

## Future Behavior Options

Option 1: UI always accepts angular velocities; Hamiltonian conversion happens
internally or in a simulation-result construction layer.

This is the recommended direction. It keeps the UI teachable, preserves the
current mental model for most users, and makes the Hamiltonian path physically
explicit without exposing canonical momenta as a first-run concept.

Option 2: UI exposes canonical momenta when Hamiltonian mode is selected.

This is mathematically honest but likely worse for teaching clarity and creates
mode-specific control semantics that users can easily misread.

Option 3: Hamiltonian mode is hidden or deferred until conversion is resolved.

This is safe but heavy-handed if a focused implementation task can normalize
the request before model construction.

Option 4: Hamiltonian mode remains available but is labelled provisional.

This is acceptable as an interim communication choice, but it does not solve
the data-contract problem and should not be treated as the final state.

## Recommended Convention

Future Simulation behavior should keep the UI convention as angular velocities
for both formulations, then convert those angular velocities to canonical
momenta before invoking the Hamiltonian solver. The result contract should
store both:

- UI initial conditions: `[theta1, theta2, omega1, omega2]`;
- Hamiltonian internal initial conditions: `[theta1, theta2, p_theta_1, p_theta_2]`.

This direction balances teaching clarity, scientific correctness, and backward
compatibility. It also gives future diagnostics a clear place to report the
conversion and any convention warnings.

## Tier 1D Update

Tier 1D implemented the recommended Option 1 convention. The Hamiltonian model
now accepts the same user-facing `[theta1, theta2, omega1, omega2]` request as
the Lagrangian model, then converts angular velocities to canonical momenta
before solving.

The audit script was rerun after implementation. Both nonzero Hamiltonian cases
now match the expected canonical momenta with zero max absolute difference. See
`TIER_1D_OPTION_1_HAMILTONIAN_CONVERSION.md` and
`tier1c_hamiltonian_convention_results.json` for the post-implementation
evidence.

## Recommended Next Implementation Task

Completed by Tier 1D: design and test a velocity-to-momentum conversion helper
for simple and compound models without changing the live UI. Acceptance required
nonzero initial-condition cases proving that:

- Lagrangian requests preserve angular velocities;
- Hamiltonian requests convert angular velocities to canonical momenta;
- the result contract records both UI and internal initial states;
- existing zero-tail behavior remains explainable rather than accidentally
  passing.

The conversion was implemented at the Hamiltonian model boundary so callbacks
can preserve the live UI shape.

## Claims To Avoid Until Implemented And Tested

- Do not claim current Hamiltonian runs are physically equivalent to Lagrangian
  runs for the same UI-labelled nonzero angular velocities.
- Do not claim Hamiltonian energy behavior is validated.
- Do not call the current theta-theta projection a validated phase portrait.
- Do not use attractive Hamiltonian plots as accepted scientific outputs until
  the state convention is resolved and tested.
