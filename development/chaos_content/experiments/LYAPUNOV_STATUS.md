# Lyapunov Strand Scientific Status

## Purpose

This is the living orientation document for the Chaos sandbox's Lyapunov
strand after Experiment 010 extended the long-time statistical-compatibility
test across decorrelated numerical reference shadows to `640 s`. It records
the current evidence boundary and the next question earned by that evidence.

[`LYAPUNOV_REVIEW.md`](LYAPUNOV_REVIEW.md) remains the historical audit of the
original Experiment 005 finite-shadow calculation. It explains why that result
required numerical repair; it is not the current status after the repaired
Experiment 005 and accepted Experiment 006.

The terms below are deliberate:

- **Established** means supported within a completed experiment's declared
  scope.
- **Rejected or unresolved** means a stronger claim failed or has not yet met
  its declared numerical requirements.
- **Theoretically expected** identifies structure not yet established by this
  project, even if a finite-time diagnostic trends in that direction.
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
| [007](007_full_matrix_qr_tangent_dynamics/README.md) | **Established:** physical-coordinate full-matrix tangent evolution and Candidate-A-scaled periodic QR have internally consistent orthonormality, reconstruction, accumulation, and reference-validity bookkeeping. **Unresolved:** through `80 s`, the cumulative spectrum fails the predeclared duration, tolerance, step-cap, QR-interval, and one-vector agreement criteria. | All long-time runs remain numerically valid, but their four finite-time values are policy-dependent diagnostics. No converged spectrum or Lyapunov exponent was established. |
| [008](008_common_reference_qr_isolation/README.md) | **Established:** when all tangent/QR variants are driven by one locally refined piecewise-dense reference history, Experiment 007's `0.082–0.157 s^-1` policy separation collapses to at most $6.37\times10^{-7}\ \mathrm{s^{-1}}$ at `80 s`. Numerical reference-shadow divergence is therefore the primary observed source of the prior separation. | The result is conditional on one common numerical reference history. Its finite-time vector is not a converged spectrum, and independently integrated long-time shadows need not agree pointwise. |
| [009](009_independent_shadow_spectrum_compatibility/README.md) | **Established:** three independently integrated reference shadows decorrelate by `40 s`, remain numerically valid through `320 s`, and become substantially more compatible than at `80 s`. **Unresolved:** residual late-window fluctuation and final/late between-shadow spread remain marginally above the predeclared limits. | No statistically compatible spectrum is accepted at `320 s`; the result is neither accepted nor clearly incompatible. |
| [010](010_independent_shadow_640s_compatibility/README.md) | **Established:** the unchanged three-shadow ensemble remains numerically valid through `640 s` and satisfies every predeclared within-shadow, final-spread, late-window, and ensemble-mean compatibility limit. | Acceptance supports one statistically compatible numerical Euler–Lagrange QR spectrum estimate for the declared initial condition and three deterministic policies; it is not universal or independently validated in canonical coordinates. |

Experiment 010 is the current boundary. It continues the exact Experiment 009
policies, reproduces all three committed `320 s` prefix spectra exactly, and
then advances each independently integrated reference+tangent shadow to
`640 s`. The maximum final component range falls from `0.0573` to
`0.0166 s^-1`, maximum sample standard deviation from `0.0293` to
`0.00953 s^-1`, and matched-width late-window range from `0.0967` to
`0.0501 s^-1`. All retained criteria pass.

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
8. At `80 s`, all Experiment 007 reference, energy, QR, conditioning, and
   accumulation validity checks pass. Nevertheless, the cumulative baseline
   vector changes by `0.149 s^-1` in its largest component from `40→80 s`,
   while the declared tolerance, step-cap, and QR-interval variants differ
   from baseline by `0.082–0.157 s^-1`. The long-time numerical result is
   therefore unresolved, not an accepted spectrum.
9. Experiment 008 holds one strict, half-step, locally validated reference
   history fixed while varying tangent tolerance, tangent step cap, and QR
   interval. All final and `60–80 s` differences meet the declared limits;
   final differences are only $3.32\times10^{-8}$ to
   $6.37\times10^{-7}\ \mathrm{s^{-1}}$. This isolates reference-shadow
   divergence as the primary observed source of Experiment 007's separation.
10. Experiment 009 follows baseline, strict, and half-step numerical shadows
    independently through `320 s`. All pairs decorrelate by `40 s`; all runs
    remain valid; the ensemble-mean `240→320 s` change is only
    `0.0146 s^-1`; and the `320 s` mean is approximately
    `(0.9822, 0.0124, -0.0083, -0.9878) s^-1`. The maximum final range is
    `0.0573 s^-1` and maximum late-window range is `0.0967 s^-1`, so the
    predeclared compatibility claim remains unresolved.
11. Experiment 010 extends exactly those three runs to `640 s`. Their final
    vectors are statistically compatible under the retained criteria, with
    ensemble mean approximately
    `(0.9833, 0.0123, -0.0099, -0.9865) s^-1`. The final component ranges are
    at most `0.0166 s^-1`, sample standard deviations at most `0.00953 s^-1`,
    and maximum `560–640 s` between-shadow range `0.0501 s^-1`. All numerical
    guards and within-shadow settling limits pass.

No finite-time scalar or vector reported by Experiments 004–009 was an
accepted Lyapunov exponent or spectrum. Experiment 010 now supports a
statistically compatible long-time numerical spectrum estimate within its
declared three-shadow protocol, with descriptive componentwise half-widths
`(0.0239, 0.00637, 0.00838, 0.0248) s^-1`. This remains a bounded numerical
claim, not a universal spectrum for the double pendulum.

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

- compatibility beyond the accepted `640 s` three-shadow protocol, or across
  a larger or probabilistically defined numerical-shadow ensemble;
- whether `640 s` is generally sufficient under other formulations, norms,
  tangent bases, or physical initial conditions;
- whether the common-reference QR-interval and tangent-policy collapse remains
  negligible at substantially longer duration;
- convergence toward the asymptotic structure expected of a Hamiltonian flow;
- agreement between a one-vector tangent estimate and the leading QR estimate;
- robustness to tangent-basis initialization;
- agreement with an independently formulated Hamiltonian/canonical tangent
  calculation;
- a maximal Lyapunov exponent for the current reference trajectory; or
- any broader classification of the trajectory, initial-condition region, or
  double-pendulum system as chaotic.

The accepted Experiment 010 limits apply only to its completed continuation
design. They do not turn its descriptive uncertainty envelope into a formal
confidence interval.

## Next justified question

The next justified research question is:

> Does an independently formulated Hamiltonian/canonical tangent QR
> calculation reproduce the statistically compatible Euler–Lagrange spectrum
> estimate accepted by Experiment 010?

The natural object remains the full tangent matrix and cumulative spectrum

$$
\dot{Y}=J(x)Y,
\qquad
(\lambda_1,\lambda_2,\lambda_3,\lambda_4),
$$

rather than only a single largest-exponent estimate. Experiments 007–010 have
made the Candidate-A-scaled primitive executable, separated tangent/QR
discretisation from reference-shadow divergence, and established compatibility
for the declared three-shadow Euler–Lagrange ensemble by `640 s`:

$$
Z=SY,
\qquad
Z^-=QR,
\qquad
Y^+=S^{-1}Q,
$$

with a deterministic QR sign convention and accumulated logarithmic growth
from the magnitudes of the diagonal entries of $R$. The next stage should be
an independent formulation cross-check, not another automatic duration
extension or a broadened physical-initial-condition study.

## Theoretical structure to test, not target

The autonomous double pendulum has two Hamiltonian degrees of freedom. Its
asymptotic Lyapunov spectrum is therefore theoretically expected to exhibit
Hamiltonian structure, generically including exponent pairing and neutral
directions. For the accepted Experiment 010 estimate, quantities
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

Experiment 010's `640 s` ensemble mean has total sum `-0.000924 s^-1`, outer-
pair sum `-0.003257 s^-1`, inner-pair sum `0.002333 s^-1`, and middle
magnitudes `0.012274` and `0.009941 s^-1`. This is supporting finite-time
evidence only. The project has not independently established the Hamiltonian
asymptotic spectrum. These expressions remain theoretical structural
expectations, not target values that a calculation should be engineered to
reproduce, and finite-time QR estimates in the noncanonical Euler–Lagrange
representation need not pair perfectly at every time.

## Conditional horizon

A plausible, evidence-dependent progression is:

```text
006  validated local variational dynamics
  ↓
007  internally coherent full-matrix QR; first 80 s convergence matrix unresolved
  ↓
008  common-reference isolation: reference-shadow divergence is primary observed source
  ↓
009  three decorrelated shadows: strong but incomplete compatibility by 320 s
  ↓
010  unchanged 640 s continuation: declared statistical compatibility accepted
  ↓  only because a common numerical estimate is now earned
independent Hamiltonian/canonical spectrum cross-check
  ↓  only if both formulations support it
contrasting initial conditions and carefully bounded chaos classification
  ↓  only after an individual diagnostic is trusted
state-space or parameter-space exploration
```

This is orientation, not a reserved sequence of experiment numbers or a rigid
roadmap. The convergence study may reject the estimates, reveal a new defect,
or change the next justified experiment entirely.
