# Minimal Initial-Condition Sensitivity Experiment

## Status

**Rejected as evidence of substantial finite-time sensitivity.** The fixed
named run is retained as valid negative evidence: all four trajectories pass
the numerical policy, but neither the principal nor tighter-reference pair
reaches the predeclared physical-separation threshold within 20 seconds.

The numerical configuration below must not be retuned merely to obtain an
accepted or visually dramatic result.

This is a Stage 1 sandbox experiment. It is not production code, a reusable
Chaos API, or a general test for chaos.

## Question

Can two simple-double-pendulum trajectories differing in exactly one declared
user-facing initial-state component exhibit finite-time physical separation
that remains credible under an explicit numerical acceptance policy?

## Model And Formulation

The experiment uses the **simple point-mass double pendulum** and the
**Euler-Lagrange formulation** implemented by the production
`DoublePendulumLagrangian` model.

The production model is used as a one-way, read-only dependency because it is
the repository's accepted implementation of the current simple-model equations,
coordinate geometry, initial-condition conversion, solver metadata, and named
solver policies. Production code does not import this experiment.

Euler-Lagrange state is chosen because its solver state has the same physical
meaning as the user-facing state after unit conversion:

```text
(theta1, theta2, omega1, omega2)
```

This avoids introducing canonical-momentum scaling into the first sensitivity
experiment. It does not imply that sensitivity is formulation-specific or that
Hamiltonian mechanics is unsuitable for later Chaos work.

## Named Initial-Condition Pair

The fixed experiment name is:

```text
theta2_120_vs_120.001_deg
```

Both trajectories use the same physical parameters:

```text
l1 = 1 m       l2 = 1 m
m1 = 1 kg      m2 = 1 kg
g  = 9.81 m/s^2
```

The base user-facing state is:

```text
(theta1, theta2, omega1, omega2) = (0 deg, 120 deg, 0 deg/s, 0 deg/s)
```

The perturbed state is:

```text
(theta1, theta2, omega1, omega2) = (0 deg, 120.001 deg, 0 deg/s, 0 deg/s)
```

Exactly one component, `theta2`, differs. The perturbation is
`0.001 deg = 1.7453292519943296e-5 rad`.

This pair is taken from the explicit nearby-state example in `PEDAGOGY.md`, not
from a parameter search. The perturbation is small relative to a one-radian
angular scale, is precisely representable as a user-facing decimal input, and
is far above floating-point roundoff. No alternate initial state or perturbation
will be tried if the named pair fails acceptance.

## Initial Energy Policy

Equal initial energy is **deliberately not required**.

Changing only `theta2` while keeping the other three user-facing components
identical generally changes potential energy. Enforcing equal energy would
require compensating through another angle or angular velocity, so the pair
would no longer differ in exactly one declared user-facing component. The two
choices answer different questions.

This experiment asks about local sensitivity to a stated perturbation in the
full physical initial state, not about two trajectories constrained to the same
energy surface. The initial energy difference is therefore measured and
reported rather than silently removed.

## Angle Periodicity

The solver retains raw, continuous angular coordinates. Raw angle subtraction
is not used as the primary separation measure because physically equivalent
angles can differ by an integer multiple of `2*pi`.

For the complementary angular diagnostic, each component difference is mapped
to its principal value in `[-pi, pi)`:

```text
delta_theta = (theta_a - theta_b + pi) mod (2*pi) - pi
```

The primary Cartesian measure is already periodic because positions are built
from sine and cosine. No trajectory angle is wrapped before integration, and no
unwrapping heuristic is used.

## Separation Measures

### Primary: normalized second-bob separation

Let `r2_base(t)` and `r2_perturbed(t)` be the Cartesian positions of the second
bob. The primary diagnostic is

```text
d_tip(t) = ||r2_base(t) - r2_perturbed(t)||_2 / (l1 + l2)
```

It is dimensionless, formulation-independent, periodic in both angles, and has
a direct physical interpretation: the distance between the two end bobs as a
fraction of the total pendulum length.

For this experiment, **substantial finite-time physical separation** is defined
before execution as:

```text
max_t d_tip(t) >= 0.1
```

That corresponds to an end-bob distance of at least `0.2 m` for the named
parameters. The threshold is a descriptive scale for this one experiment, not
a chaos classifier.

### Complementary: both-bob configuration separation

The complementary physical diagnostic is

```text
d_configuration(t)
    = sqrt((||delta_r1(t)||_2^2 + ||delta_r2(t)||_2^2) / 2) / (l1 + l2)
```

This prevents a conclusion from depending only on the end bob. A separate
periodicity-aware angular configuration distance,

```text
d_angle(t) = sqrt(delta_theta1(t)^2 + delta_theta2(t)^2)
```

is reported in radians for mathematical inspection. Angular velocities are not
combined with angles into a Euclidean state norm because their units differ and
no nondimensional state metric has yet been accepted.

## Integration And Sampling

Each trajectory is integrated over:

```text
t in [0, 20] seconds
```

with `4001` requested, evenly spaced samples, including both endpoints. The
sampling interval is therefore exactly `0.005 s` (`200 Hz`). Adaptive solver
steps remain owned by `solve_ivp`; the requested grid provides time-aligned
diagnostic output and does not impose a fixed integration step.

Twenty seconds is the existing Simulation default duration and is short enough
to inspect without extending into a long-duration scientific-validity claim.
Acceptance depends on crossing a fixed physical-separation threshold, not on a
single narrow sampled peak. The reported threshold-crossing time is only
resolved to the `0.005 s` output interval.

## Solver And Reference Policies

The principal run uses the accepted production simple-model policy:

```text
method = DOP853
rtol   = 1e-6
atol   = 1e-8
```

The tighter comparison uses the accepted production simple-model reference
policy:

```text
method = DOP853
rtol   = 1e-9
atol   = 1e-11
```

Both members of a pair always use identical parameters, requested times, and
solver policy. The tighter run is not assumed to be exact. It is used to ask
whether the finite-time sensitivity conclusion survives a three-order-of-
magnitude reduction in both requested tolerances.

Numerical disagreement is measured independently for the base and perturbed
states by comparing the principal and reference end-bob positions:

```text
e_numerical(t) = max(
    ||r2_base_principal(t) - r2_base_reference(t)||_2,
    ||r2_perturbed_principal(t) - r2_perturbed_reference(t)||_2
) / (l1 + l2)
```

This is compared with the reference pair separation at the first time the
reference pair reaches `d_tip = 0.1`. At that time the physical perturbation
effect must be at least `100` times the same-state solver-policy disagreement.
This ratio is the experiment's explicit distinction between paired physical
separation and the numerical disagreement exposed by the two policies.

Both principal and reference pairs must reach the substantial-separation
threshold, and their first threshold-crossing times must agree within `0.5 s`
(`2.5%` of the integration duration). This accepts the finite-time descriptive
conclusion without claiming pointwise long-time trajectory equivalence.

## Independent Energy Diagnostic

Energy is calculated locally from the simple-model physical state rather than
read from the model or inherited from the Poincare experiment:

```text
T = 0.5*(m1+m2)*l1^2*omega1^2
  + 0.5*m2*l2^2*omega2^2
  + m2*l1*l2*omega1*omega2*cos(theta1-theta2)

V = -(m1+m2)*g*l1*cos(theta1) - m2*g*l2*cos(theta2)

E = T + V
```

The drift is normalized by a fixed gravitational energy scale rather than by
`|E(0)|`, so it is not affected by an arbitrary shift of the potential datum:

```text
E_scale = g*((m1+m2)*l1 + m2*l2)
drift(t) = |E(t) - E(0)| / E_scale
```

The predeclared limits are:

```text
principal maximum normalized drift <= 1e-5
reference maximum normalized drift <= 1e-7
```

for each trajectory independently. These are experiment acceptance bounds, not
new production solver guarantees. They are deliberately looser than the solver
tolerances because local truncation tolerance does not translate directly into
an invariant-error bound over a nonlinear trajectory.

## Rejection And Acceptance

A trajectory is rejected if any of the following holds:

- `solve_ivp` reports failure;
- returned time samples do not exactly match all `4001` requested samples;
- the solution shape is not `(4001, 4)`;
- any state, position, energy, or separation value is non-finite;
- requested times are not strictly increasing and identical across all four
  integrations;
- its normalized energy drift exceeds the policy-specific bound.

The named experiment is accepted only if all four trajectories pass those
checks and all of the following are true:

- the input states differ only in `theta2` by exactly `0.001 deg`;
- the measured initial separations agree with the declared geometry;
- both principal and reference pairs reach `d_tip >= 0.1`;
- their first crossing times differ by no more than `0.5 s`;
- at the reference crossing time, reference pair separation divided by
  `e_numerical` is at least `100`;
- periodic angular separation and the Cartesian diagnostics contain no
  non-finite or wrapping-generated discontinuity;
- the machine-readable output records every individual check and does not emit
  a successful status when any check fails.

Failure is retained as evidence. The configuration must not be lengthened,
retuned, or replaced by a search inside this experiment.

## Reproducible Commands

Run the deterministic self-check:

```bash
uv run python development/chaos_content/experiments/initial_condition_sensitivity/minimal_initial_condition_sensitivity.py --self-check
```

Write the principal diagnostic bundle, including the tighter comparison:

```bash
uv run python development/chaos_content/experiments/initial_condition_sensitivity/minimal_initial_condition_sensitivity.py --output-dir development/chaos_content/outputs/initial_condition_sensitivity/principal --plots
```

The bundle contains:

- `manifest.json`;
- `summary.json`;
- `trajectory_separation.csv`;
- `sensitivity_diagnostics.png` when `--plots` is requested.

Generated bundles are ignored sandbox artifacts, not production assets.

## Permitted Claim

If every acceptance check passes, the strongest permitted conclusion is:

> For the named `theta2_120_vs_120.001_deg` initial-condition pair and the
> declared numerical policies, a `0.001 deg` difference in `theta2` produced
> substantial finite-time physical trajectory separation.

The experiment cannot establish proof of chaos, exponential divergence, a
Lyapunov exponent, a general sensitivity law, behaviour across a region of
initial conditions, or solver-independent long-time dynamics.

## Findings

The fixed named run was executed without changing its pair, duration, metric,
or thresholds.

All four integrations succeeded, returned all `4001` requested finite samples,
and passed their independent normalized energy-drift limits:

| Trajectory | Maximum normalized energy drift | Limit |
| --- | ---: | ---: |
| base, principal | `1.2569e-6` | `1e-5` |
| perturbed, principal | `1.5906e-6` | `1e-5` |
| base, reference | `2.6142e-9` | `1e-7` |
| perturbed, reference | `2.4522e-9` | `1e-7` |

The initial normalized end-bob separation was `8.72665e-6`, matching the
declared geometry. The maximum observed values were:

```text
principal maximum d_tip = 5.96319e-5 at t = 19.535 s
reference maximum d_tip = 5.93180e-5 at t = 19.535 s
```

The predeclared substantial-separation threshold was `0.1`. Neither pair
reached it. The maximum same-state principal/reference end-bob disagreement was
`3.07857e-6`, and the close principal/reference maxima show that the negative
result is not caused by the moderate policy alone.

The initial energies deliberately differed by `1.48277e-4 J`, or
`5.03831e-6` of the fixed gravitational energy scale, because only `theta2`
was perturbed.

No permitted sensitivity claim is supported. In particular, the experiment
does not establish that the pair never separates over a longer interval; it
establishes only that this fixed 20-second experiment did not produce the
substantial finite-time separation required by its contract. The stop condition
prohibits lengthening the run or searching for a replacement pair in this task.
