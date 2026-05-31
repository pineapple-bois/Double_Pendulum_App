# Phase 8 Mathematical Fidelity Baseline Review

Date: 2026-05-31

## Summary

This pass reviewed the historical math reference material under
`development/math_reference/` and the current reusable implementation under
`src/double_pendulum/`. No production code was changed.

The simple Lagrangian and simple Hamiltonian formulations appear intended to
represent the same physical system: a planar double pendulum with massless rods,
point masses, angles measured from the downward vertical, positive rotation
counterclockwise, and positive gravity magnitude `g` acting through
`V = m g y` with downward positions carrying negative `y`.

For the simple model, the current Hamiltonian constructor now treats the
user-facing state as `[theta1, theta2, omega1, omega2]`, converts the angular
velocity entries to canonical momenta, and integrates
`[theta1, theta2, p_theta_1, p_theta_2]`. A small diagnostic comparison with
tight solver tolerances showed Lagrangian and Hamiltonian angular trajectories
agree to about `1e-10` radians for representative short runs. With default
`solve_ivp` tolerances, the same formulations can visibly diverge over time,
which is expected for chaotic/sensitive dynamics and is not, by itself, proof
of a state-mapping defect.

The most important remaining baseline gap is output diagnostics: Hamiltonian
solver state columns 3 and 4 are canonical momenta, not angular velocities. The
Canvas payload correctly omits Hamiltonian angular velocity time series rather
than relabeling momenta, but the codebase does not yet provide an audited
canonical-momentum-to-angular-velocity reconstruction for Hamiltonian
diagnostics.

## Historical Reference Conventions

Historical executable reference files inspected:

- `development/math_reference/README.md`
- `development/math_reference/DerivationLagrangian.ipynb`
- `development/math_reference/DevelopmentHamiltonian.ipynb`
- `development/math_reference/DoublePendulum.py`
- `development/math_reference/MathFunctions.py`
- `development/math_reference/OOP/Class_OOP.py`
- `development/math_reference/OOP/Functions_OOP.py`
- `development/math_reference/Compound_Double_Pendulum/Derivation_Compound.ipynb`
- `development/math_reference/Compound_Double_Pendulum/Functions_Compound.py`
- `development/math_reference/Compound_Double_Pendulum/DoublePendulum_Compound.py`

Angle and coordinate convention:

- The simple reference uses `x1 = l1*sin(theta1)`,
  `y1 = -l1*cos(theta1)`, `x2 = x1 + l2*sin(theta2)`, and
  `y2 = y1 - l2*cos(theta2)`.
- Therefore `theta_i = 0` places each segment vertically downward. Positive
  angles rotate toward positive `x`, which matches the app copy saying
  positive angles rotate counterclockwise.
- The vertical coordinate is positive upward in the energy expression, while
  the bobs sit at negative `y` below the pivot.

Gravity and potential energy:

- `g` is declared positive.
- Potential energy is computed as `V = m*g*h`; because `h` is the `y`
  coordinate, the simple model gives
  `V = -(m1 + m2)*g*l1*cos(theta1) - m2*g*l2*cos(theta2)`.
- The Lagrangian is `L = T - V`, so the displayed Lagrangian contains positive
  cosine terms from subtracting the negative potential.

Mass and length assumptions:

- The simple model is general in `l1`, `l2`, `m1`, `m2`, and `g`; it is not
  restricted to equal masses or equal lengths.
- The simple rods are rigid, massless, and inextensible.
- The compound model uses rod masses `M1`, `M2` and lengths `l1`, `l2`; the
  reference focuses on a uniform rod model, with some exploratory cylindrical
  support in the older compound helper.

Lagrangian state variables:

- The Lagrangian derivation rewrites the second-order system as
  `[theta1, theta2, omega1, omega2]`, with
  `omega_i = d(theta_i)/dt`.
- Historical class constructors call `np.deg2rad(initial_conditions)`, so both
  angles in degrees and angular velocities in degrees per second become radians
  and radians per second numerically.

Hamiltonian state variables and canonical momenta:

- The Hamiltonian reference derives
  `p_theta_i = partial L / partial theta_dot_i`.
- For the simple model, the reference mass matrix is:

  ```text
  B = [[(m1 + m2)*l1^2, m2*l1*l2*cos(theta1 - theta2)],
       [m2*l1*l2*cos(theta1 - theta2), m2*l2^2]]
  ```

- It then uses `[p_theta_1, p_theta_2]^T = B [theta_dot_1, theta_dot_2]^T`
  and `[theta_dot_1, theta_dot_2]^T = B^-1 [p_theta_1, p_theta_2]^T`.
- The Hamiltonian is built as `H = 1/2 * p.T * B^-1 * p + V`, representing
  total mechanical energy.

Known simplifications and approximations:

- Non-conservative forces are neglected.
- Small-angle behavior is described only as a qualitative approximation in the
  markdown copy; the production/reference equations are nonlinear.
- Symbolic expressions apply trig simplifications such as
  `1 - cos(delta)^2 = sin(delta)^2`.

## Production Code Conventions

Production files inspected:

- `src/double_pendulum/math/functions.py`
- `src/double_pendulum/models/lagrangian.py`
- `src/double_pendulum/models/hamiltonian.py`
- `src/double_pendulum/models/initial_conditions.py`
- `src/double_pendulum/models/metadata.py`
- `src/double_pendulum/plotting/helpers.py`
- `src/double_pendulum/validation/inputs.py`
- `app/callbacks/simulation.py`
- `app/serialization/canvas_payload.py`
- `app/content/simulation.py`
- `app/components/simulation_controls.py`
- `documentation/simulation-canvas/canvas-integration-api.md`
- `tests/unit/test_derivation_fidelity.py`
- `tests/numerical/test_initial_condition_conventions.py`
- `tests/numerical/test_models.py`
- `tests/numerical/test_canvas_payload.py`

Coordinate and sign convention:

- `src/double_pendulum/math/functions.py` uses the same simple coordinate
  definitions as the historical executable reference:
  `x1 = l1*sin(theta1)`, `y1 = -l1*cos(theta1)`,
  `x2 = x1 + l2*sin(theta2)`, `y2 = y1 - l2*cos(theta2)`.
- The same file computes `V = m*g*h` and `L = T - V`.
- `app/content/simulation.py` states that angles are measured in degrees and
  that positive angles rotate counterclockwise.

Lagrangian implementation:

- `DoublePendulumLagrangian` builds equations through
  `form_lagrangian`, `euler_lagrange_system`, `simplify_system`,
  `create_matrix_equation`, and `first_order_system`.
- Its solver state is explicitly named
  `[theta1, theta2, omega1, omega2]`.
- The constructor stores user input in degrees, converts all four values with
  `user_initial_conditions_to_radians`, and integrates that angular-velocity
  state directly.

Hamiltonian implementation:

- `compute_hamiltonian` constructs the same simple mass matrix `B` and
  potential energy as the historical Hamiltonian reference.
- `compute_hamiltons_equations` uses
  `theta_dot_i = partial H / partial p_theta_i` and
  `p_dot_theta_i = -partial H / partial theta_i`.
- `DoublePendulumHamiltonian` declares the user-facing input convention as
  `[theta1, theta2, omega1, omega2]`, but the solver state convention as
  `[theta1, theta2, p_theta_1, p_theta_2]`.
- `angular_velocities_to_canonical_momenta` converts the user angular
  velocities to canonical momenta using the model mass matrix before
  integration.

Physical parameter handling:

- The callback chooses `{m1, m2}` for the simple model and `{M1, M2}` for the
  compound model, always including `l1`, `l2`, and `g`.
- Validation allows positive bounded lengths, masses, and gravity values.

Solver/time-grid configuration:

- `app/callbacks/simulation.py` sets `time_steps = int((time_end - time_start)
  * 200)` and `time_vector = [time_start, time_end, time_steps]`.
- Both production model classes build `self.time` with `np.linspace(start, end,
  count)`.
- Both classes default to `scipy.integrate.solve_ivp`, with `odeint` still
  supported as an alternate integrator path.
- No default `rtol` or `atol` is supplied by the app callback, so SciPy defaults
  apply unless callers pass overrides.

## Lagrangian vs Hamiltonian Comparison

If both formulations represent the same physical system with the same physical
initial state, then the angular coordinates should agree up to numerical error:

```text
theta_L(t) ~= theta_H(t)
```

The state vectors are not directly comparable column-for-column:

```text
Lagrangian state:  [theta1, theta2, omega1, omega2]
Hamiltonian state: [theta1, theta2, p_theta_1, p_theta_2]
```

The correct simple-model initial mapping is:

```text
p_theta_1 = ((m1 + m2)*l1^2)*omega1
            + (m2*l1*l2*cos(theta1 - theta2))*omega2

p_theta_2 = (m2*l1*l2*cos(theta1 - theta2))*omega1
            + (m2*l2^2)*omega2
```

The inverse mapping for Hamiltonian output diagnostics is:

```text
[omega1, omega2]^T = B^-1 [p_theta_1, p_theta_2]^T
```

That inverse mapping is exactly what Hamilton's equations use internally for
`theta_dot`, but production payloads currently do not serialize a reconstructed
Hamiltonian angular velocity time series.

Small local diagnostic checks:

- Simple model, unity parameters, initial state `[0, 60, 0, 0]`,
  interval `[0, 1]`, 200 samples, tight `solve_ivp` tolerances
  `rtol=1e-10`, `atol=1e-12`: maximum angular-coordinate difference was about
  `8.6e-11` radians.
- Simple model, parameters `l1=1`, `l2=1.5`, `m1=3`, `m2=1`, `g=9.81`,
  initial state `[90, 0, 572.95, -458.37]`, interval `[0, 0.2]`, 80 samples,
  tight tolerances: maximum angular-coordinate difference was about
  `3.2e-10` radians. The Hamiltonian momentum tail differed from the direct
  user angular-velocity tail, as expected.
- With default solver tolerances, the `[0, 60, 0, 0]` short comparison differed
  by about `0.003` radians over one second. Tight tolerances largely removed
  that discrepancy, suggesting tolerance sensitivity rather than a simple
  state-mapping sign error for this case.

These diagnostics are evidence only and should become focused tests in a later
Phase 8 pass if accepted.

## Initial-State Mapping

The user-facing app inputs are currently angles and angular velocities:

```text
theta1, theta2, omega1, omega2
```

The UI labels angles as degrees and angular velocities as degrees per second.

Lagrangian path:

- Converts all four values with `np.deg2rad`.
- Uses the resulting values directly as
  `[theta1, theta2, omega1, omega2]`.

Hamiltonian path:

- Converts all four user values with `np.deg2rad`.
- Uses angles as radians.
- Converts angular velocities from radians per second to canonical momenta with
  the appropriate mass matrix.
- Integrates `[theta1, theta2, p_theta_1, p_theta_2]`.

High-confidence baseline conclusion: the current Hamiltonian constructor does
not appear to treat angular velocities as momenta at initialization. That
failure mode is covered by existing focused numerical tests.

Open diagnostic gap: no audited helper currently reconstructs full Hamiltonian
`omega1(t)`, `omega2(t)` arrays from `theta(t), p(t)` for output diagnostics.
Any angular-state projection that expects velocities must either omit the
Hamiltonian velocity series, as the Canvas payload currently does, or perform
the inverse mass-matrix conversion explicitly.

## Units and Degree/Radian Conversion

Reference and production both use:

- user angles in degrees;
- user angular velocities in degrees per second;
- internal angles in radians;
- internal angular velocities in radians per second for Lagrangian state;
- internal canonical momentum units for Hamiltonian momentum state;
- time in seconds;
- gravity in length units per second squared.

Important note: `np.deg2rad` is dimensionally acceptable for angular velocity
values expressed as degrees per second because it multiplies by `pi/180`,
yielding radians per second.

The Canvas payload labels:

- `theta1_deg` and `theta2_deg` as degrees;
- Lagrangian `omega1_deg_per_s` and `omega2_deg_per_s` as degrees/second;
- Hamiltonian internal momenta as `canonical_momentum_internal_units`.

The payload validator rejects Hamiltonian payloads that expose Lagrangian
velocity array fields.

## Bob-Position Reconstruction

The production Lagrangian and Hamiltonian classes both reconstruct displayed
positions from the first two solution columns:

```text
x1 = l1*sin(theta1)
y1 = -l1*cos(theta1)
x2 = x1 + l2*sin(theta2)
y2 = y1 - l2*cos(theta2)
```

This is consistent for the simple point-mass model and is also what the
renderer payload receives. Because the Hamiltonian state's first two columns
are still angles, position reconstruction is not affected by the momentum
state convention.

Potential compound-model mismatch: the symbolic compound Lagrangian uses
center-of-mass positions with `x1 = l1/2*sin(theta1)` and
`x2 = x1 + l2/2*sin(theta2)`. For two rods connected in series, the second
rod's center of mass would normally be measured from the first hinge endpoint:

```text
x2_expected = l1*sin(theta1) + (l2/2)*sin(theta2)
y2_expected = -l1*cos(theta1) - (l2/2)*cos(theta2)
```

The current symbolic compound baseline instead uses the first rod center of
mass as the offset. This behavior is inherited from the historical compound
reference and should be checked before relying on compound-model fidelity.
The display position reconstruction still draws bob/end positions, not rod
centers of mass, for both model types.

## Energy or Invariant Checks

The historical Hamiltonian material explicitly identifies `H = T + V` as total
mechanical energy and an integral of motion for the conservative system.

Production code can symbolically construct `H`, but the live model classes and
Canvas payload currently do not compute, serialize, validate, or threshold
energy drift. `app/serialization/canvas_payload.py` explicitly rejects energy
diagnostic keys in the current payload schema.

Energy conservation therefore remains an unavailable invariant check in the
current app baseline.

## Potential Irregularities

1. Hamiltonian velocity diagnostics are intentionally absent. This is safe for
   the Canvas payload, but any current or future angular-state projection that
   expects `omega` for Hamiltonian runs must use `B^-1 p`, not raw solver
   columns 3 and 4.

2. Default solver tolerances can produce visible Lagrangian/Hamiltonian
   divergence even when the formulations match under tight tolerances. This is
   especially relevant for chaotic or high-energy states and should not be
   interpreted as a mathematical sign error without tolerance sensitivity
   evidence.

3. User-facing markdown files contain transcription errors in simple-model
   coordinates/energy: `assets/MarkdownScripts/mathematics_lagrangian.txt`
   shows `theta1` where executable reference and production code use `theta2`
   for the second segment position and part of `V2`. The Hamiltonian markdown
   has similar simple-coordinate copy near the top, while later equations use
   the correct Hamiltonian mass matrix/potential form.

4. Existing `tests/numerical/test_models.py` has a test named
   `test_first_solution_row_matches_initial_conditions_in_radians` that includes
   `DoublePendulumHamiltonian` only with zero angular velocities. That test
   passes because zero velocities map to zero momenta; the name would be
   misleading for nonzero Hamiltonian velocities. More explicit tests already
   exist in `test_initial_condition_conventions.py`.

5. Compound-model symbolic center-of-mass placement appears physically
   suspicious for a serial compound pendulum. Because production matches the
   historical reference, this is an inherited baseline issue rather than a new
   regression.

6. The public information markdown says the maximum time interval is
   120 seconds, while current validation uses 60 seconds. This is not a
   mathematical-formulation issue, but it is a units/documentation mismatch.

7. The app callback computes sample count as `int(duration * 200)`. Very short
   accepted durations could produce low sample counts. The validation currently
   requires only `time_start < time_end`; no minimum sample-count guard was
   observed in this pass.

## Recommended Next Checks

1. Add a small accepted Phase 8 numerical equivalence check for simple
   Lagrangian vs simple Hamiltonian angular coordinates with tight solver
   tolerances and nonzero angular velocities.

2. Add an audited helper for Hamiltonian momentum-to-angular-velocity
   reconstruction:

   ```text
   omega(t) = B(theta(t))^-1 p(t)
   ```

   Then decide whether Hamiltonian angular velocity diagnostics should be
   serialized or intentionally remain omitted.

3. Run tolerance-sensitivity checks for representative low-energy,
   high-energy, and known-chaotic initial states before treating visual
   divergence as a formulation defect.

4. Add energy calculation and drift diagnostics outside the current Canvas
   payload schema first, then promote only after a clear payload contract
   update.

5. Audit compound-model center-of-mass coordinates against a trusted mechanics
   derivation before adding compound fidelity tests.

6. Correct mathematical markdown transcription errors after the production math
   baseline is agreed.

7. Clarify or rename the zero-velocity Hamiltonian initial-row test so it does
   not imply nonzero canonical momenta should equal `deg2rad` user velocities.

8. Consider documenting app-level sample-count policy and minimum duration if
   Phase 8 callback hardening touches solver setup.
