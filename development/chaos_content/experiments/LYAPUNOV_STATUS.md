# Lyapunov Strand Scientific Status

## Purpose

This is the living orientation document for the Chaos sandbox's Lyapunov
strand after the accepted QR-primitive completion of Experiment 007. It records the current
evidence boundary and the next question earned by that evidence.

[`LYAPUNOV_REVIEW.md`](LYAPUNOV_REVIEW.md) remains the historical audit of the
original Experiment 005 finite-shadow calculation. It explains why that result
required numerical repair; it is not the current status after the repaired
Experiment 005 and accepted Experiment 006.

The terms below are deliberate:

- **Established** means supported within a completed experiment's declared
  scope.
- **Rejected or unresolved** means a stronger claim failed or has not yet met
  its declared numerical requirements.
- **Theoretically expected** identifies structure not yet observed by this
  project.
- **Proposed** identifies a motivated next investigation, not an accepted
  implementation decision.

## Current position

The project has progressed from finite nearby-state distances to a validated
direct tangent formulation:

| Experiment | Epistemic result | Claim boundary |
| --- | --- | --- |
| [003](003_lyapunov_distance_contract/README.md) | **Established:** a dimensionally coherent Euler–Lagrange nearby-state convention, with Candidate A retained as the primary working norm and Candidate B as a non-unique comparison. | No growth rate or exponent was estimated. |
| [004](004_finite_time_exponential_growth/README.md) | **Established:** reproducible local growth and small-perturbation collapse. **Rejected:** a defensible common approximately exponential interval under the predeclared rule. | Its finite-window rates are descriptive, not Lyapunov exponents. |
| [005](005_renormalised_local_stretching/README.md) | **Established:** direction-preserving finite-shadow resets and signed growth accumulation work mechanically. Audit-driven repair removed winding-dependent coordinates, uncontrolled step size, and reconstruction loss. **Unresolved:** the repaired long-time accumulated rate still failed tolerance and duration convergence. | No converged accumulated rate or maximal Lyapunov exponent was accepted; further finite-shadow tuning was not justified. |
| [006](006_variational_dynamics_validation/README.md) | **Established:** the independently validated Euler–Lagrange Jacobian reproduces the finite-shadow local limit in norm and signed direction as perturbation size decreases. Direct tangent evolution was materially more stable under the tested short-time tolerance and step refinements. | Acceptance covers the established `0–1.29 s` local regime and capped solver protocol only. No long-time tangent renormalisation, full spectrum, or maximal Lyapunov exponent was computed. |
| [007](007_full_matrix_qr_tangent_dynamics/README.md) | **Established:** physical-coordinate full-matrix tangent evolution and Candidate-A-scaled periodic QR have internally consistent orthonormality, reconstruction, accumulation, reference-validity, and deterministic-repeat bookkeeping in one modest run. | Its four finite-time values are diagnostic and unsorted. No duration or numerical-policy convergence, Hamiltonian structure, or Lyapunov exponent was established. |

Experiment 007 is the current boundary. Direct tangent dynamics is locally
validated and its full-matrix QR primitive is executable. The unresolved
question is whether its cumulative finite-time estimates converge under a
separate, predeclared long-time numerical study.

## Established results

The following statements are supported by the experiment chain:

1. The current simple-model Euler–Lagrange state is

   $$
   x=(\theta_1,\theta_2,\omega_1,\omega_2).
   $$

2. Wrapped angular subtraction and ordinary velocity subtraction provide a
   deterministic local finite-state difference. Lifted winding history is a
   separate diagnostic and is not part of the local norm.
3. Candidate A is a dimensionally coherent, explicitly scaled working norm.
   It is not uniquely privileged or established as norm-independent.
4. The selected reference trajectory exhibits reproducible local perturbation
   growth, but Experiment 004 did not support a single common approximately
   exponential interval under its inference rule.
5. Repaired finite-shadow renormalisation remains numerically unresolved for a
   converged long-time accumulated stretching rate. This does not negate the
   established local instability.
6. Direct variational evolution

   $$
   \dot{x}=f(x),
   \qquad
   \dot{\delta x}=J(x)\,\delta x
   $$

   is validated for the tested local regime. Experiment 006 independently
   checked the production-derived symbolic Jacobian with directional finite
   differences and angular-periodicity tests, then observed finite shadows
   converge toward the tangent prediction in both norm and signed direction.
7. A physical-coordinate tangent matrix $Y$ can be periodically
   orthonormalised in Candidate-A-scaled coordinates using
   $SY^-=QR$ and $Y^+=S^{-1}Q$ with machine-precision reconstruction and
   metric orthonormality in the tested Experiment 007 primitive.

No finite-time scalar reported by Experiments 004–006 is an accepted Lyapunov
exponent.

## Current mathematical contract

For the present Euler–Lagrange formulation, define

$$
S=\operatorname{diag}(1,1,T_c,T_c),
\qquad
T_c=\sqrt{\frac{L_c}{g}},
\qquad
L_c=1\ \mathrm{m},
$$

and use the Candidate-A tangent geometry

$$
\lVert\delta x\rVert_{\mathrm{EL}}
=\lVert S\,\delta x\rVert_2.
$$

This is the currently validated working convention, retained for continuity.
It is not a claim that Candidate A is the uniquely correct physical norm.

The validated tangent operator is

$$
J(x)=\frac{\partial f}{\partial x},
$$

constructed in Experiment 006 by symbolic differentiation of the actual
parameter-substituted first-order Euler–Lagrange flow and independently checked
at representative states. Tangent angular components are infinitesimal
coordinate-basis components and are not wrapped. Solver-facing physical angles
remain locally rebased; winding remains separate.

## Unestablished claims

The project has not established:

- convergence of any long-time tangent Lyapunov estimate or spectrum;
- the integration duration required for convergence;
- whether Experiment 006's short-time solver-policy agreement survives
  long-time tangent propagation;
- an appropriate QR/orthonormalisation interval or robustness to that choice;
- robustness to further step-cap refinement;
- convergence toward the asymptotic structure expected of a Hamiltonian flow;
- agreement between a one-vector tangent estimate and the leading QR estimate;
- robustness to tangent-basis initialization;
- agreement with an independently formulated Hamiltonian/canonical tangent
  calculation;
- a maximal Lyapunov exponent for the current reference trajectory; or
- any broader classification of the trajectory, initial-condition region, or
  double-pendulum system as chaotic.

No numerical acceptance thresholds for these questions have yet been earned.

## Next justified question

The next justified research question is:

> Do the cumulative full-matrix QR estimates from the validated
> Euler–Lagrange tangent flow converge under predeclared duration, tolerance,
> step-cap, QR-interval, and tangent-basis checks?

The natural object is now the full tangent matrix and spectrum

$$
\dot{Y}=J(x)Y,
\qquad
(\lambda_1,\lambda_2,\lambda_3,\lambda_4),
$$

rather than only a single largest-exponent estimate. Experiment 007 has made
the Candidate-A-scaled primitive executable:

$$
Z=SY,
\qquad
Z^-=QR,
\qquad
Y^+=S^{-1}Q,
$$

with a deterministic QR sign convention and accumulated logarithmic growth
from the magnitudes of the diagonal entries of $R$. The separate convergence
experiment should retain the right to question numerical policies and interval
choices; primitive coherence does not pre-accept their long-time use.

## Theoretical structure to test, not target

The autonomous double pendulum has two Hamiltonian degrees of freedom. Its
asymptotic Lyapunov spectrum is therefore theoretically expected to exhibit
Hamiltonian structure, generically including exponent pairing and neutral
directions. If Experiment 007 reaches a numerically resolved regime, quantities
such as

$$
\lambda_1+\lambda_4,
\qquad
\lambda_2,
\qquad
\lambda_3,
\qquad
\sum_{i=1}^{4}\lambda_i
$$

may be useful convergence diagnostics.

The project has not observed or established this spectrum. These expressions
are theoretical structural expectations, not target values that a calculation
should be engineered to reproduce. Finite-time QR estimates in the noncanonical
Euler–Lagrange representation need not show perfect pairing or exact neutral
values at every time.

## Conditional horizon

A plausible, evidence-dependent progression is:

```text
006  validated local variational dynamics
  ↓
007  internally coherent full-matrix scaled-QR primitive
  ↓
separate long-time Euler–Lagrange QR-spectrum convergence study
  ↓  only if earned by that study
independent Hamiltonian/canonical spectrum cross-check
  ↓  only if both formulations support it
contrasting initial conditions and carefully bounded chaos classification
  ↓  only after an individual diagnostic is trusted
state-space or parameter-space exploration
```

This is orientation, not a reserved sequence of experiment numbers or a rigid
roadmap. The convergence study may reject the estimates, reveal a new defect,
or change the next justified experiment entirely.
