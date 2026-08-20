# Minimal Initial-Condition Sensitivity Experiment

## Status

**Numerically accepted as a regular-control result; rejected only as evidence
of substantial finite-time sensitivity.** The fixed named run is retained as
valid negative evidence: all four trajectories pass the numerical policy, but
neither the principal nor tighter-reference pair reaches the predeclared
physical-separation threshold within 20 seconds. Its evidential value is that a
small perturbation does not automatically produce large visible separation on
this timescale.

The later predeclared regime-selection extension is **provisionally useful as
Outcome C**: its high-excitation candidates expose numerical-policy failures,
so no threshold-crossing sensitivity case is accepted yet.

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

## Regime-Selection Extension

### Question

Can a small, physically motivated set of simple-double-pendulum initial
conditions spanning regular to strongly nonlinear motion reveal materially
different finite-time sensitivity under the same perturbation and numerical
policy within the existing 20-second simulation horizon?

This comparison extends the local experiment without changing or replacing the
fixed `theta2_120_vs_120.001_deg` result. It is a predeclared comparison, not a
grid, parameter sweep, optimization, or search for a dramatic trajectory.

### Unchanged contract

Every case uses the same simple point-mass Euler-Lagrange model, unit SI
parameters, `theta2 += 0.001 deg` perturbation, 20-second duration, 200 Hz output
sampling, principal and tighter DOP853 policies, periodic angular difference,
normalized second-bob separation, energy-drift limits, numerical rejection
checks, and substantial-separation threshold documented above. Equal initial
energy is still deliberately not required because compensating another state
component would change the question.

The fixed gravitational scale is `E_scale = 29.43 J`. The table reports the
unshifted mechanical energy `E`, the datum-independent excitation above the
stable hanging minimum as `(E + E_scale) / E_scale`, and the signed perturbed
minus base energy difference. Expected regimes are hypotheses recorded before
integration, not results.

### Predeclared cases

The common physical parameters remain `l1 = l2 = 1 m`, `m1 = m2 = 1 kg`, and
`g = 9.81 m/s^2`. States are `(theta1, theta2, omega1, omega2)` in degrees and
degrees per second.

| Case | Base state | Perturbed state | Base `E` / J | Excitation / `E_scale` | `delta E` / J | Physical rationale and cautious expectation |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `theta2_120_vs_120.001_deg` | `(0, 120, 0, 0)` | `(0, 120.001, 0, 0)` | `-14.715000` | `0.500000` | `+1.4827735e-4` | Retained regular-control evidence: the prior accepted numerical run remained close for 20 seconds. |
| `small_angle_in_phase` | `(10, 10, 0, 0)` | `(10, 10.001, 0, 0)` | `-28.982892` | `0.015192` | `+2.9732957e-5` | Low excitation and nearly aligned links should be close to the small-angle, low-complexity regime; limited sensitivity is expected. |
| `nonlinear_bounded_release` | `(45, 60, 0, 0)` | `(45, 60.001, 0, 0)` | `-18.778435` | `0.361929` | `+1.4827885e-4` | A large-angle rest release introduces nonlinear coupling, while its total energy remains below the `theta1 = 0`, `theta2 = pi` potential barrier (`-9.81 J`); bounded nonlinear swings are expected, without assuming irregularity. |
| `second_link_rotation_access` | `(0, 0, 0, 360)` | `(0, 0.001, 0, 360)` | `-9.690791` | `0.670717` | `+1.4941488e-9` | Starting at the stable hanging geometry with second-link kinetic energy `2*pi^2 = 19.739 J` puts total energy only `0.119 J` above the `theta1 = 0`, `theta2 = pi` barrier. Energetic access to second-link rotation and separatrix-like complexity is plausible, but actual rotation is not assumed. |
| `opposed_high_energy_fixture` | `(120, -120, 120, -90)` | `(120, -119.999, 120, -90)` | `21.980125` | `1.746861` | `-9.8552756e-5` | Opposed large angles plus counter-moving nonzero velocities produce strong coupling at high excitation. The base state is an existing production numerical-test fixture, which motivates inclusion but does not establish its regime. |
| `near_inverted_release` | `(179, 179, 0, 0)` | `(179, 179.001, 0, 0)` | `29.425518` | `1.999848` | `+2.9866513e-6` | A rest release close to the both-links-up potential maximum samples a geometrically unstable, high-potential configuration. Strong finite-time sensitivity is plausible, but neither chaos nor threshold crossing is assumed. |

The five additional cases were fixed from these mechanical considerations
before any regime-comparison integration. They will all be retained and run;
no observed result may be used to replace a case while calling the replacement
predeclared.

### Reproduce the comparison

Run the deterministic comparison self-check:

```bash
uv run python development/chaos_content/experiments/initial_condition_sensitivity/regime_selection_comparison.py --self-check
```

Write the ignored comparative evidence bundle:

```bash
uv run python development/chaos_content/experiments/initial_condition_sensitivity/regime_selection_comparison.py --output-dir development/chaos_content/outputs/initial_condition_sensitivity/regime_selection --plots
```

The bundle contains `regime_manifest.json`, `regime_summary.json`,
`regime_comparison.csv`, `regime_separation_timeseries.csv`, and
`regime_comparison_diagnostics.png`.

### Comparative findings

The full predeclared set was run without replacing a case, increasing the
duration or perturbation, or changing an acceptance threshold. The result is
**Outcome C: numerical credibility becomes problematic in the candidate
high-excitation regimes**.

`E / E_scale` below uses the signed energy with the experiment's declared
potential datum. Maximum separation and crossing times are tighter-reference
values. Values marked untrusted are reported because complete finite data were
returned, but cannot support a sensitivity claim because the case failed the
numerical policy.

| Case | Physical rationale | `E / E_scale` | Maximum `d_tip` | First `d_tip >= 0.1` | Numerical status | Sensitivity status |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `theta2_120_vs_120.001_deg` | Retained regular control | `-0.500000` | `5.93180e-5` | none | accepted | rejected: below threshold |
| `small_angle_in_phase` | Low-excitation, near-small-angle motion | `-0.984808` | `8.88084e-6` | none | accepted | rejected: below threshold |
| `nonlinear_bounded_release` | Large-angle but energetically bounded release | `-0.638071` | `2.68095e-5` | none | accepted | rejected: below threshold |
| `second_link_rotation_access` | Just above the second-link upright energy barrier | `-0.329283` | `8.72665e-6` | none | accepted | rejected: below threshold |
| `opposed_high_energy_fixture` | Opposed high-angle, counter-moving fixture | `0.746861` | `1.73054` (untrusted) | `7.040 s` (untrusted) | rejected | not evaluable |
| `near_inverted_release` | Near the both-links-up potential maximum | `0.999848` | `1.87011` (untrusted) | `10.695 s` (untrusted) | rejected | not evaluable |

All 24 integrations reported solver success and returned all 4001 finite,
time-aligned samples. The maximum independent energy drifts, taking the worse
member of each pair, were:

| Case | Principal maximum | Principal limit | Reference maximum | Reference limit |
| --- | ---: | ---: | ---: | ---: |
| `theta2_120_vs_120.001_deg` | `1.59059e-6` | `1e-5` | `2.61415e-9` | `1e-7` |
| `small_angle_in_phase` | `1.25402e-8` | `1e-5` | `9.93927e-12` | `1e-7` |
| `nonlinear_bounded_release` | `3.80994e-7` | `1e-5` | `7.78223e-10` | `1e-7` |
| `second_link_rotation_access` | `2.26762e-6` | `1e-5` | `8.92325e-10` | `1e-7` |
| `opposed_high_energy_fixture` | `1.90581e-4` | `1e-5` | `3.74277e-8` | `1e-7` |
| `near_inverted_release` | `1.18832e-4` | `1e-5` | `3.40294e-8` | `1e-7` |

The two high-excitation pairs cross the physical threshold under both policies,
and their first crossing times differ by `0.000 s` and `0.030 s`. That agreement
is insufficient for acceptance. At the reference crossing, the physical-to-
numerical ratios are only `46.64` and `7.46`, below the required `100`.
The maximum same-state principal/reference disagreement later reaches `1.98346`
and `1.98336`, respectively, while the principal trajectories also violate the
energy-drift limit. The visually substantial separations are therefore retained
as untrusted diagnostic evidence, not accepted sensitivity evidence.

The four numerically accepted cases remain far below the threshold under both
policies. In particular, the original pair remains useful rather than obsolete:
it shows that the same perturbation does not automatically yield visible
separation over 20 seconds. The comparison does not justify a general statement
that 20 seconds is inadequate, because the only threshold-crossing candidates
are blocked by numerical credibility.

### Next justified experiment

The next experiment should be a **single-case numerical-policy adequacy test**
for `near_inverted_release`, the more severe of the two rejected cases. Its one
question should be whether a predeclared tighter DOP853 policy hierarchy can
pass an explicit energy bound and produce a converged threshold-crossing result
against an independently tighter reference over the unchanged 20 seconds.

That experiment should not add states, extend time, lower the threshold, or
claim sensitivity merely because the current tighter trace looks dramatic. A
timescale experiment is not yet justified; numerical-policy credibility is the
current blocker.
