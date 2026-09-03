# Finite-time one-vector stretching

This is the canonical scientific reference for the finite-time stretching
consumer of the state-space-map prototype. It defines the quantity, records
its numerical and validation provenance, and bounds the claims that may be
made from it. See the [prototype README](../../README.md) to run the workflow,
the [software architecture](../architecture.md) for dependency boundaries,
and the [pedagogical storyboard](../pedagogy/sensitivity_to_lyapunov.md) for
the teaching progression.

`../../src/lyapunov/` contains the reusable pre-production scientific
implementation. Experiments remain the forensic evidence; the implementation
embodies only contracts already earned by that evidence. Production code must
not import this prototype directory.

## Observable definition

The Euler--Lagrange state is

$$
x=(\theta_1,\theta_2,\omega_1,\omega_2).
$$

Candidate A supplies the declared tangent-space geometry

$$
S=\operatorname{diag}(1,1,T_c,T_c),
\qquad
T_c=\sqrt{L_c/g},
$$

with the experimentally validated convention $L_c=1\ \mathrm{m}$. Candidate A
is a named, dimensionally coherent working metric; it is not claimed to be a
unique norm.

The operational field sets both initial angular velocities to zero and starts
from the Candidate-A unit tangent

$$
\delta x_0=(1,0,0,0).
$$

The reference state and tangent evolve together under

$$
\frac{\mathrm{d}x}{\mathrm{d}t}=f(x),
\qquad
\frac{\mathrm{d}\delta x}{\mathrm{d}t}=J(x)\delta x,
\qquad
J(x)=\frac{\partial f}{\partial x}.
$$

At each declared renormalisation boundary $t_k$, the calculation measures the
positive Candidate-A stretch factor

$$
r_k=\left\|S\delta x(t_k^-)\right\|_2,
$$

retains the signed logarithmic increment $\log r_k$, and resets only the
tangent magnitude while preserving its evolved direction:

$$
\delta x(t_k^+)
=
S^{-1}\frac{S\delta x(t_k^-)}{r_k}.
$$

For the fixed horizon $T$, the stored scalar is

$$
\Lambda_T^{(1)}
=
\frac{1}{T}\sum_{k=1}^{n}\log r_k.
$$

The promoted field uses $T=5\ \mathrm{s}$ and a $0.25\ \mathrm{s}$
renormalisation interval. The superscript $(1)$ records a one-vector,
one-direction calculation: this is a fixed-horizon finite-time stretching
rate, not a full tangent-space spectrum or an asymptotic maximal Lyapunov
exponent.

## Numerical and scientific provenance

The NumPy/SymPy plus SciPy `solve_ivp` path is the mathematical and scientific
oracle. The compiled implementations preserve the same Candidate-A geometry,
direct Jacobian-vector evolution, DOP853 numerical policy, renormalisation,
validity definitions, and result contract. The promoted hybrid evaluator uses
the compiled DOP853 path normally and invokes the compiled-RHS `solve_ivp`
oracle only for the independently verified endpoint-step incompatibility.

The bounded reference-versus-compiled assessment fixes the existing
`T=5 s`, `0.25 s` renormalisation, pure-`theta1` tangent, zero initial angular
velocities, Candidate-A geometry, and DOP853 policy. Its validation set is the
center plus four corners of the already declared `169 deg`--`189 deg` angle
rectangle; it was fixed before compiled results were inspected.

The predeclared scalar acceptance tolerance is an absolute
`1e-8 s^-1`. Cycle log increments, final reference/tangent state, numerical
validity, energy drift, and solver evaluation counts are also compared. The
absolute tolerance is used because a defensible finite-time rate may be near
zero; it is small relative to the observed order-one rates and is ten times
the reference solver's relative tolerance before allowing wider accumulated
state comparisons.

The first compiled call includes LLVM compilation plus one evaluation. Warmed
timings are measured only after both paths have completed the validation set.
Timing is implementation evidence, not part of scientific equivalence.

## Bounded sampling evidence

The one-dimensional demonstration uses 15 uniform samples of `theta1(0)` from
`169 deg` through `189 deg`, including the
trusted `179 deg` condition. It fixes `theta2(0)=179 deg`, both initial angular
velocities at zero, the pure-`theta1` initial tangent, `T=5 s`, the `0.25 s`
renormalisation interval, Candidate-A geometry, and the accepted DOP853 solver
policy. The interval was selected symmetrically around the reference condition
before evaluating the completed sweep; it was not chosen to isolate visually
interesting behaviour.

The two-dimensional demonstration uses a mechanically selected `9 x 9`
square. Both initial angle axes run uniformly from `169 deg` through `189 deg`,
so the trusted
`(179 deg, 179 deg)` condition is the center cell. Both angular velocities,
the pure-`theta1` tangent, `T=5 s`, the `0.25 s` renormalisation interval,
Candidate-A geometry, and the accepted DOP853 policy are fixed across all 81
cells. The earlier full-policy smoke grid used the same domain at `4 x 4`.

Stored arrays use one declared convention:

```text
values[theta2_index, theta1_index]
```

Thus `theta1` is the horizontal heatmap axis and array-column coordinate;
`theta2` is the vertical heatmap axis and array-row coordinate. Both axes are
stored explicitly, and the renderer supplies them directly to Matplotlib.

## Reusable API and result model

The public entry point is:

```python
result = run_sensitivity_to_lyapunov(SensitivitySpec(...))
```

The flow is explicit:

```text
SensitivitySpec
    -> run_sensitivity_to_lyapunov(...)
    -> SensitivityToLyapunovResult
         finite_pair: NearbyTrajectoryTrace
         tangent: TangentTrace
         diagnostics: NumericalDiagnostics
```

`PendulumParameters`, `EulerLagrangeState`, `SolverSpec`, and
`SensitivitySpec` say what to calculate. `Trajectory`,
`NearbyTrajectoryTrace`, `TangentTrace`, and `NumericalDiagnostics` record what
was calculated. `CandidateAMetric` has one responsibility: it makes the
accepted local geometry named and inspectable.

The default result exposes complete arrays, including both physical
trajectories, second-bob positions and separation, wrapped finite-state
differences, Candidate-A separation, the unwrapped tangent vector, its norm,
log stretch, finite-time rate, finite/tangent signed direction agreement, and
energy diagnostics. No final scalar hides the conceptual bridge.

The fixed-horizon entry point is:

```python
result = run_renormalized_tangent(
    RenormalizedTangentSpec(duration=T)
)
rate = result.finite_time_stretching_rate
```

`RenormalizedTangentResult` retains the cycle end times, Candidate-A stretch
factors, signed logarithmic increments, cumulative log stretch, cumulative
finite-time rates, terminal reference and unit tangent, and numerical
diagnostics. A future sweep can consume the final scalar without needing to
know the integration machinery, while validation and diagnostic work can
inspect the complete accumulation record.

The trusted result is exposed to sampling through one explicit adapter:

```python
evaluation = evaluate_renormalized_tangent_reference(spec)
```

It returns the cross-observable `ScalarEvaluation`: status, optional finite
value, typed Lyapunov numerical diagnostics, elapsed time, evaluator identity,
validity issues, and bounded execution-error details. The adapter catches only
the reference calculation's numerical `RuntimeError`; programming and
specification errors propagate. Any compiled evaluator must return the same
outcome semantics and be proven equivalent to this reference adapter.

The first compiled equivalent is exposed through the matching adapter:

```python
evaluation = evaluate_renormalized_tangent_compiled(spec)
```

This remains the compiled-RHS plus `solve_ivp` DOP853 oracle for the promoted
integration boundary. Both solve_ivp adapters execute the same shared
fixed-horizon driver. The reference builds its flow and exact symbolic
Jacobian from the accepted production mechanics; the Numba path writes the
same simple-model flow explicitly and propagates its directional derivative
directly as `J(x) delta_x`. Focused tests compare that eight-component RHS
with the symbolic oracle for default and non-default physical parameters.

The Experiment 015 boundary is exposed separately:

```python
result = run_renormalized_tangent_compiled_dop853(spec)
evaluation = evaluate_renormalized_tangent_compiled_dop853(spec)
```

It uses the same Numba RHS/JVP and shared evolve / measure / renormalise
driver, but integrates each `0.25 s` segment once through SciPy's compiled
DOP853 boundary exposed by `scipy.integrate.ode("dop853")`. Accepted solver
steps supply the reference
states used by the unchanged energy-drift calculation. The solve_ivp oracle
instead observes the uniform `0.01 s` diagnostic grid. Experiment 015 showed
that both diagnostics remain below the unchanged validity limit and their
maxima agree within the existing `1e-8` comparison tolerance across the five
mechanically selected `T=5 s` conditions. The distinction remains provenance;
the reference result contract has not been redefined.

The adapter passes the externally declared `max_step` directly to that
compiled boundary and checks every observed accepted-step gap against the same
external value. Experiment 017 later established that the legacy DOP853
endpoint rule may enlarge a final segment step by less than one percent to
land exactly on the endpoint. A proposed conservative internal translation,
`nextafter(max_step / 1.01, 0)`, removed those endpoint overshoots but exceeded
the existing `1e-8 s^-1` finite-time-rate equivalence gate at the trusted
`(179 deg, 179 deg)` fixture. The translation was therefore rejected and not
promoted. The accepted-step post-check and bounded execution-error semantics
remain authoritative; the external numerical policy was neither weakened nor
reinterpreted.

## Execution paths

The strand now exposes three purposeful evaluation roles:

1. `evaluate_renormalized_tangent_reference` is the NumPy/SymPy plus
   `solve_ivp` mathematical/scientific oracle.
2. `evaluate_renormalized_tangent_compiled_dop853` is the promoted Numba
   RHS/JVP plus compiled-DOP853 fast evaluator. Its numerical and accepted-step
   policies are unchanged.
3. `evaluate_renormalized_tangent_hybrid` is a routing/recovery policy around
   existing evaluators. It returns the fast result normally and uses
   `evaluate_renormalized_tangent_compiled`, the compiled-RHS plus `solve_ivp`
   integration-boundary oracle, only after independently verifying the known
   endpoint `max_step` incompatibility.

The reusable hybrid entry point is:

```python
evaluation = evaluate_renormalized_tangent_hybrid(spec)
```

It retains the existing `ScalarEvaluation` contract. The `evaluator` field
records the actual route as one of:

```text
compiled_dop853
compiled_rhs_solve_ivp_fallback
compiled_dop853_execution_error
```

The max-step error message is only a prefilter. A fallback additionally
replays accepted-step observation and requires the reported excess to be the
sole final accepted step into a completed renormalisation endpoint, with the
unchanged external cap and the verified legacy `1.01 h` endpoint bound. If
those mechanics do not verify, the original execution error remains an error.
Unrelated `RuntimeError` outcomes are not retried and programming or
specification exceptions continue to propagate.

Experiment 017 accepted this hybrid boundary on the established `17 x 17` and
`25 x 25` bounded fields: it routed exactly the prior 14 and 19 endpoint errors
to exact solve_ivp results, preserved all other fast results, remained
orientation- and tile-invariant, and retained about a `4.5x` field-level
speedup over all-solve_ivp evaluation. This is a bounded execution claim. The
fallback frequency and throughput over the full periodic domain are not yet
established, and the hybrid API does not introduce tile, persistence, or
production-delivery semantics.

## Sampling APIs

The 1-D orchestration API is:

```python
sweep = run_theta1_sweep(
    Theta1SweepSpec(
        theta1_degrees=(...),
        observable_spec=RenormalizedTangentSpec(...),
    )
)
```

`Theta1SweepResult` retains the unchanged observable specification and a
neutral `LineSamplingResult`: its named axis, ordered `(index, coordinate)`
samples, scalar evaluation outcomes, total timing, and mean timing. The exact
initial state is reproducible from the fixed specification plus each sampled
coordinate. The sweep accepts an evaluator callable; it does not own Lyapunov
integration or failure translation.

The rectangular API is similarly specific:

```python
grid = run_theta1_theta2_grid(
    Theta1Theta2GridSpec(
        theta1_degrees=(...),
        theta2_degrees=(...),
        observable_spec=RenormalizedTangentSpec(...),
    )
)
```

`Theta1Theta2GridResult` retains the fixed specification and a neutral
`RectangularSamplingResult`: both named axes, cells, scalar values, statuses,
validity mask, and timing. Each neutral cell records `(y_index, x_index)`, its
two coordinates, and one scalar evaluation outcome. The exact Lyapunov initial
state remains reproducible from the fixed specification and coordinates. The
grid independently accepts the evaluator and has no dependency on `sweep.py`.
JSON persistence and heatmap rendering remain separate, so the numerical field
is available without rerunning the observable.

## Full periodic angular-domain contract

The cross-observable domain API defines a full axis in radians as

```python
axis = full_periodic_angle_axis(samples=N)
domain = PeriodicAngularDomain(
    theta1_samples=N1,
    theta2_samples=N2,
)
```

with

```text
theta[k] = -pi + 2*pi*k/N,  k = 0, ..., N-1.
```

The domain is therefore `[-pi, pi)`: `-pi` is included and the physically
duplicate `+pi` endpoint is not. `resolution` reports
`(theta1_samples, theta2_samples)` while `field_shape` reports the stored-array
order `(theta2_samples, theta1_samples)`. The existing bounded demonstrations
remain degree-based for fixture continuity; `Theta1Theta2GridSpec` can consume
the periodic domain without duplicating endpoints. No large full-periodic
field is evaluated by this strand.

## Default reference contract

The declared first workflow matches the accepted local Experiment 006 case:

- simple point-mass model with `l1 = l2 = m1 = m2 = 1` and `g = 9.81` in SI;
- Euler--Lagrange state order `(theta1, theta2, omega1, omega2)`;
- reference state `(179 deg, 179 deg, 0, 0)`;
- finite perturbation `(0, 1e-6, 0, 0)` radians;
- a unit Candidate-A tangent in that same pure-`theta2` direction;
- `0–1.29 s` at `0.01 s` output spacing;
- DOP853 with `rtol=1e-9`, `atol=1e-11`, and
  `max_step=min(Tc/32, 0.25/25)` (equal for the default constants);
- `0.25 s` physical-angle chart rebasing, never applied to tangent components;
- Candidate-A finite-distance local ceiling `1e-2`;
- normalized energy-drift limit `1e-7`.

The implementation imports the accepted production symbolic mechanics from
`src/double_pendulum/`. It does not import experimental scripts or outputs.
Experiments 002 and 003 supply the physical and finite-state concepts;
Experiment 006 supplies the validated direct-tangent and bounded numerical
contract. Experiment 007 supplies the one-vector evolve / measure /
renormalise convention: a pure-`theta1` Candidate-A unit tangent, `0.25 s`
cycles, signed `log(r_k)` accumulation, physical-reference angle rebasing, and
unwrapped tangent components. Its `0–5 s` prefix is the default regression
horizon. The interval is a declared numerical policy, not a demonstrated
physical timescale or convergence condition.

## Claim boundary

This prototype supports a strong but deliberately local statement:

> For the declared initial state, pure-`theta2` direction, Candidate-A
> geometry, and bounded `0–1.29 s` numerical policy, direct Euler--Lagrange
> tangent evolution reproduces the normalized finite-shadow limit in norm and
> signed direction and yields a reproducible finite-time logarithmic
> stretching diagnostic.

It does not establish an asymptotic maximal Lyapunov exponent, a converged
spectrum, norm independence, a universal chaos classification, or a map
observable. The default endpoint rate must therefore be labelled a
**finite-time stretching-rate diagnostic**, not “the Lyapunov exponent.”

For the renormalised calculation, the supported statement is equally exact
and finite: for the declared initial condition, initial direction, Candidate-A
geometry, solver policy, renormalisation interval, and horizon `T`,
`finite_time_stretching_rate` is

```text
(sum of the signed per-cycle Candidate-A log stretch increments) / T.
```

Numerical validity means the integrations, energy diagnostic, and unit-norm
resets meet their declared bounds. It does not mean the scalar has settled as
`T` grows. Experiments 010–014 are retained as evidence for that distinction:
future maps should be allowed to evaluate a predeclared fixed horizon without
requiring independent asymptotic settling at every initial condition.

The sweep plot is an apparatus diagnostic. Variation along its sampled line is
not interpreted as a general chaos classification, an asymptotic result, or a
map of the state space.

The same boundary applies to the small grid heatmap: it validates repeated
evaluation, data orientation, and persistence, but it is not a production
chaos map and its visual texture is not a classification.

The NumPy/SciPy implementation remains the scientific oracle. Reusable
sampling, future storage, and rendering concerns are now cross-observable, but
the Lyapunov specification, Candidate-A geometry, tangent integration, and
validity diagnostics remain local scientific contracts. High-performance map
work has therefore begun with reference-versus-compiled equivalence rather
than silently replacing this implementation.

That first pointwise equivalence step is now established for the declared
five-condition validation set. Experiment 015 additionally established and
this strand now exposes a compiled DOP853 segment runner for the same
fixed-horizon contract. The current solve_ivp paths remain available as
scientific and integration-boundary oracles.

This promotion supports reusable bounded periodic field generation. It does
not establish scientific equivalence for arbitrary horizons, parameters, or
continuous initial conditions, nor operational readiness for high-resolution
production.

## Deliberately absent

There is no simulator/manager/engine abstraction, plugin system, inheritance
tree, generic N-dimensional framework, adaptive/refined grid, interpolation,
state-space classification, QR/full-spectrum API, selected map horizon, fully
compiled end-to-end observable or batch kernel, distributed executor, storage
backend abstraction, renderer framework, Dash integration, or production
`/chaos` integration. Those decisions require later prototype questions and
evidence.
