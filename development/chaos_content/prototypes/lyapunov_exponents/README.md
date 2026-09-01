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
executes the established 1-D runner once per ordered `theta2` row, preserving
the same scalar calculation and cell-outcome semantics while making field
shape and heatmap orientation explicit.

The mathematical narrative lives beside the implementation in
[`storyboards/sensitivity_to_lyapunov.md`](storyboards/sensitivity_to_lyapunov.md).
Future visuals in this strand should use similarly story-specific local
documents, allowing their mathematics to coexist without accumulating
unrelated derivations in this README or a repository-wide document.

## Why this structure

The current story needs one small scientific kernel and one composition, not a
framework:

- `reference.py` owns semantic specifications/results, Candidate-A geometry,
  physical observables, the production-derived Euler--Lagrange flow/Jacobian,
  bounded piecewise integration, the composed sensitivity calculation, and
  the one-vector renormalised tangent calculation;
- `sensitivity_to_lyapunov.py` composes the structured reference result into
  the first four-panel pedagogical figure; it performs no validation and emits
  no narrated console story;
- `sweep.py` owns the coordinate-specific 1-D sweep specification, sample
  outcomes, timing record, and repeated calls to the reference evaluator;
- `theta1_sweep.py` declares and renders the first small sweep without
  implementing any Lyapunov mathematics;
- `grid.py` owns the coordinate-specific rectangular grid, its row/column
  convention, and the repeated 1-D row evaluations;
- `theta1_theta2_grid.py` independently persists the scalar field and renders
  its basic diagnostic heatmap;
- `tests/` checks the reference contracts, Experiment 006/007 fixtures, sweep
  substitution, independent-point equivalence, and invalid/error handling;
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

The 1-D orchestration API is:

```python
sweep = run_theta1_sweep(
    Theta1SweepSpec(
        theta1_degrees=(...),
        observable_spec=RenormalizedTangentSpec(...),
    )
)
```

`Theta1SweepResult` retains the ordered samples, total and mean timing, and the
unchanged observable specification. Each `Theta1SweepSample` retains its full
initial state, returned rate when calculation completed, numerical diagnostics,
elapsed time, and one explicit outcome: completed-valid, completed-invalid, or
execution-error. Only numerical `RuntimeError` failures are converted into a
sample outcome; programming and specification exceptions remain visible.

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

`Theta1Theta2GridResult` retains both ordered axes, cells, scalar values,
statuses, validity mask, fixed specification, and timing. Each grid cell wraps
the corresponding established 1-D sample outcome instead of reimplementing
evaluation or error handling. JSON persistence and heatmap rendering are
separate functions, so the numerical field remains available without rerunning
the observable.

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

## Deliberately absent

There is no simulator/manager/engine abstraction, plugin system, inheritance
tree, generic N-dimensional framework, adaptive/refined grid, interpolation,
state-space classification, QR/full-spectrum API, selected map horizon, JIT
layer, persistent large-map dataset, Dash integration, or production `/chaos`
integration. Those decisions require later prototype questions and evidence.
