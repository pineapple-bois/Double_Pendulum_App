# Lyapunov-exponents prototype strand

This directory contains reusable, pre-production scientific references for the
Lyapunov teaching strand. Experiments remain the forensic evidence; this code
embodies only contracts already earned by that evidence. Production code must
not import this directory.

The first story is **Sensitivity to Lyapunov**:

```text
nearby physical trajectories
    -> second-bob Cartesian separation
    -> Candidate-A finite full-state separation
    -> direct infinitesimal tangent evolution
    -> logarithmic tangent stretch
    -> finite-time stretching-rate diagnostic
```

The strand now also extracts the next reusable primitive: repeated one-vector
evolve / measure / renormalise cycles producing one declared fixed-horizon
finite-time stretching rate. It extends the same mathematics; it is not a
separate mini-project.

The first repeated-evaluation apparatus is a bounded one-dimensional sweep of
the initial `theta1` coordinate. It delegates every sample to that existing
primitive and adds only ordering, per-sample outcome/provenance, timing, and
diagnostic plot/data composition.

The next apparatus is a tiny rectangular `theta1`–`theta2` reference grid. It
is a peer of the 1-D sweep: both sampling strategies call the same
Lyapunov-specific evaluator and retain the same coordinate-neutral scalar
outcome. The grid is no longer represented as a collection of theta1 sweeps.

The mathematical narrative lives beside the implementation in
[`storyboards/sensitivity_to_lyapunov.md`](storyboards/sensitivity_to_lyapunov.md).
Future visuals in this strand should use similarly story-specific local
documents, allowing their mathematics to coexist without accumulating
unrelated derivations in this README or a repository-wide document.

Broader cross-observable, compiled-evaluator, tiling, storage, rendering, and
production-delivery direction lives in
[`../../notes/chaos_prototype_architecture.md`](../../notes/chaos_prototype_architecture.md).
This README remains responsible only for the Lyapunov strand.

## Why this structure

The current story needs one small scientific kernel and one composition, not a
framework:

- `reference.py` owns semantic specifications/results, Candidate-A geometry,
  physical observables, the production-derived Euler--Lagrange flow/Jacobian,
  bounded piecewise integration, the composed sensitivity calculation, and
  the one-vector renormalised tangent calculation;
- `evaluation.py` adapts that unchanged rich NumPy/SciPy reference result to
  the neutral scalar-evaluation outcome and is the future
  reference-versus-compiled seam;
- `compiled.py` re-expresses only the explicit Euler--Lagrange flow and exact
  Jacobian-vector product as a Numba kernel while retaining the reference
  SciPy DOP853 driver, renormalisation, diagnostics, and result contracts;
- `fortran_dop853.py` composes that validated Numba RHS/JVP with the compiled
  Fortran DOP853 segment boundary accepted by Experiment 015, observes
  accepted steps for the energy diagnostic, and returns the same result and
  scalar-evaluation contracts;
- `compiled_equivalence.py` owns the bounded center-plus-corners equivalence
  assessment and separates first-call compilation cost from warmed evaluator
  throughput;
- `../state_space_fields.py` owns only the earned cross-observable outcome,
  explicit-axis line/rectangle reference sampling, and full periodic
  angular-domain contracts;
- `sensitivity_to_lyapunov.py` composes the structured reference result into
  the first four-panel pedagogical figure; it performs no validation and emits
  no narrated console story;
- `sweep.py` owns the Lyapunov-specific 1-D specification and initial-state
  substitution, then composes the neutral line sampler with the evaluator;
- `theta1_sweep.py` declares and renders the first small sweep without
  implementing any Lyapunov mathematics;
- `grid.py` owns the Lyapunov-specific rectangular specification and
  initial-state substitution, then composes the neutral rectangular sampler;
  it has no dependency on `sweep.py`;
- `theta1_theta2_grid.py` independently persists the scalar field and renders
  its basic diagnostic heatmap;
- `tests/` checks the reference contracts, Experiment 006/007 fixtures,
  neutral sampling and periodic domains, coordinate substitution,
  independent-point equivalence, and invalid/error handling;
- `storyboards/sensitivity_to_lyapunov.md` derives this visual's pedagogical
  progression and claim boundary.

This keeps files aligned with scientific responsibilities without splitting a
small prototype into a speculative `model/state/trajectory/manager` hierarchy.
The only stateful calculation object is `EulerLagrangeDynamics`, whose single
job is to compile the accepted flow and its exact symbolic Jacobian.

## Render the first visual

From the repository root:

```bash
uv run python development/chaos_content/prototypes/lyapunov_exponents/sensitivity_to_lyapunov.py
```

The command writes the first concrete prototype deliverable to the predictable
source-relative path `outputs/sensitivity_to_lyapunov.png`. Generated files in
`outputs/` are intentionally ignored by Git. The executable emits no terminal
narration: numerical regression evidence remains in the focused tests, while
the mathematical explanation remains in the local storyboard.

Run the focused tests:

```bash
uv run pytest development/chaos_content/prototypes/lyapunov_exponents/tests
```

## Run the reference-versus-compiled assessment

From the repository root:

```bash
uv run python development/chaos_content/prototypes/lyapunov_exponents/compiled_equivalence.py
```

This writes the source-relative, intentionally untracked
`outputs/reference_vs_compiled_equivalence.json`. The assessment fixes the
existing `T=5 s`, `0.25 s` renormalisation, pure-`theta1` tangent, zero initial
angular velocities, Candidate-A geometry, and DOP853 policy. Its validation
set is the center plus four corners of the already declared
`169 deg`--`189 deg` angle rectangle; it was fixed before compiled results were
inspected.

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

## Run the bounded 1-D sweep

From the repository root:

```bash
uv run python development/chaos_content/prototypes/lyapunov_exponents/theta1_sweep.py
```

This writes two source-relative, intentionally untracked deliverables:

- `outputs/theta1_finite_time_sweep.png` — the diagnostic line plot;
- `outputs/theta1_finite_time_sweep.json` — the inspectable values,
  per-sample statuses and diagnostics, fixed specification, and timing.

The executable emits no narrated console story. The demonstration uses 15
uniform samples of `theta1(0)` from `169 deg` through `189 deg`, including the
trusted `179 deg` condition. It fixes `theta2(0)=179 deg`, both initial angular
velocities at zero, the pure-`theta1` initial tangent, `T=5 s`, the `0.25 s`
renormalisation interval, Candidate-A geometry, and the accepted DOP853 solver
policy. The interval was selected symmetrically around the reference condition
before evaluating the completed sweep; it was not chosen to isolate visually
interesting behaviour.

## Run the bounded 2-D reference grid

From the repository root:

```bash
uv run python development/chaos_content/prototypes/lyapunov_exponents/theta1_theta2_grid.py
```

This writes two independent, source-relative, intentionally untracked
deliverables:

- `outputs/theta1_theta2_finite_time_grid.json` — axes, scalar field,
  per-cell statuses and diagnostics, fixed specification, and timing;
- `outputs/theta1_theta2_finite_time_grid.png` — a heatmap rendered separately
  from the persisted field.

The demonstration uses a mechanically selected `9 x 9` square: both initial
angle axes run uniformly from `169 deg` through `189 deg`, so the trusted
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
result = run_renormalized_tangent_compiled_fortran(spec)
evaluation = evaluate_renormalized_tangent_compiled_fortran(spec)
```

It uses the same Numba RHS/JVP and shared evolve / measure / renormalise
driver, but integrates each `0.25 s` segment once with SciPy's compiled
Fortran DOP853 implementation. Accepted solver steps supply the reference
states used by the unchanged energy-drift calculation. The solve_ivp oracle
instead observes the uniform `0.01 s` diagnostic grid. Experiment 015 showed
that both diagnostics remain below the unchanged validity limit and their
maxima agree within the existing `1e-8` comparison tolerance across the five
mechanically selected `T=5 s` conditions. The distinction remains provenance;
the reference result contract has not been redefined.

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
this strand now exposes a compiled-Fortran DOP853 segment runner for the same
fixed-horizon contract. The current solve_ivp paths remain available as
scientific and integration-boundary oracles.

This promotion supports a next bounded compiled batch/grid apparatus test. It
does not establish equivalence for arbitrary horizons or the full periodic
domain, threaded execution safety, high-resolution map production, or a tile
executor.

## Deliberately absent

There is no simulator/manager/engine abstraction, plugin system, inheritance
tree, generic N-dimensional framework, adaptive/refined grid, interpolation,
state-space classification, QR/full-spectrum API, selected map horizon, fully
compiled end-to-end observable or batch kernel, tile executor, persistent
large-map dataset, Dash integration, or production `/chaos` integration. Those
decisions require later prototype questions and evidence.
