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
  bounded piecewise integration, and the composed reference calculation;
- `sensitivity_to_lyapunov.py` composes the structured reference result into
  the first four-panel pedagogical figure; it performs no validation and emits
  no narrated console story;
- `tests/test_reference.py` checks the mathematical contracts and selected
  Experiment 006 regression fixtures;
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
contract. Experiment 007 and later work establish context for future QR
extensions but are not needed by this story.

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

## Deliberately absent

There is no simulator/manager/engine abstraction, plugin system, inheritance
tree, QR/full-spectrum API, renormalisation loop, map horizon, parameter sweep,
JIT layer, generated dataset, Dash integration, or production `/chaos`
integration. Those decisions require later prototype questions and evidence.
