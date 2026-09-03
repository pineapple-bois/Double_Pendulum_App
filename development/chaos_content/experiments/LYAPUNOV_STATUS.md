# Lyapunov Strand Scientific Status

## Purpose

This is the living orientation document for the Chaos sandbox's Lyapunov
strand after Experiment 014 completed the targeted `1280 s` EL duration study
for Experiment 012's unsettled IC-1 and IC-3 ensembles. It records the current
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
- **Theoretically expected** identifies structure not yet established by this
  project, even if a finite-time diagnostic trends in that direction.
- **Proposed** identifies a motivated next investigation, not an accepted
  implementation decision.

## Current position

The project has progressed from finite nearby-state distances to a validated
direct tangent formulation:

| Experiment | Epistemic result | Claim boundary |
| --- | --- | --- |
| [003](foundations/003_lyapunov_distance_contract/README.md) | **Established:** a dimensionally coherent Euler–Lagrange nearby-state convention, with Candidate A retained as the primary working norm and Candidate B as a non-unique comparison. | No growth rate or exponent was estimated. |
| [004](foundations/004_finite_time_exponential_growth/README.md) | **Established:** reproducible local growth and small-perturbation collapse. **Rejected:** a defensible common approximately exponential interval under the predeclared rule. | Its finite-window rates are descriptive, not Lyapunov exponents. |
| [005](foundations/005_renormalised_local_stretching/README.md) | **Established:** direction-preserving finite-shadow resets and signed growth accumulation work mechanically. Audit-driven repair removed winding-dependent coordinates, uncontrolled step size, and reconstruction loss. **Unresolved:** the repaired long-time accumulated rate still failed tolerance and duration convergence. | No converged accumulated rate or maximal Lyapunov exponent was accepted; further finite-shadow tuning was not justified. |
| [006](foundations/006_variational_dynamics_validation/README.md) | **Established:** the independently validated Euler–Lagrange Jacobian reproduces the finite-shadow local limit in norm and signed direction as perturbation size decreases. Direct tangent evolution was materially more stable under the tested short-time tolerance and step refinements. | Acceptance covers the established `0–1.29 s` local regime and capped solver protocol only. No long-time tangent renormalisation, full spectrum, or maximal Lyapunov exponent was computed. |
| [007](lyapunov_validation/007_full_matrix_qr_tangent_dynamics/README.md) | **Established:** physical-coordinate full-matrix tangent evolution and Candidate-A-scaled periodic QR have internally consistent orthonormality, reconstruction, accumulation, and reference-validity bookkeeping. **Unresolved:** through `80 s`, the cumulative spectrum fails the predeclared duration, tolerance, step-cap, QR-interval, and one-vector agreement criteria. | All long-time runs remain numerically valid, but their four finite-time values are policy-dependent diagnostics. No converged spectrum or Lyapunov exponent was established. |
| [008](lyapunov_validation/008_common_reference_qr_isolation/README.md) | **Established:** when all tangent/QR variants are driven by one locally refined piecewise-dense reference history, Experiment 007's `0.082–0.157 s^-1` policy separation collapses to at most $6.37\times10^{-7}\ \mathrm{s^{-1}}$ at `80 s`. Numerical reference-shadow divergence is therefore the primary observed source of the prior separation. | The result is conditional on one common numerical reference history. Its finite-time vector is not a converged spectrum, and independently integrated long-time shadows need not agree pointwise. |
| [009](lyapunov_validation/009_independent_shadow_spectrum_compatibility/README.md) | **Established:** three independently integrated reference shadows decorrelate by `40 s`, remain numerically valid through `320 s`, and become substantially more compatible than at `80 s`. **Unresolved:** residual late-window fluctuation and final/late between-shadow spread remain marginally above the predeclared limits. | No statistically compatible spectrum is accepted at `320 s`; the result is neither accepted nor clearly incompatible. |
| [010](lyapunov_validation/010_independent_shadow_640s_compatibility/README.md) | **Established:** the unchanged three-shadow ensemble remains numerically valid through `640 s` and satisfies every predeclared within-shadow, final-spread, late-window, and ensemble-mean compatibility limit. | Acceptance supports one statistically compatible numerical Euler–Lagrange QR spectrum estimate for the declared initial condition and three deterministic policies; it is not universal or independently validated in canonical coordinates. |
| [011 Phases A–C](lyapunov_validation/011_hamiltonian_canonical_spectrum_crosscheck/README.md) | **Established:** Phase A validates the repository Hamiltonian, Legendre state/tangent maps, canonical reference flow, and independently Hamiltonian-derived Jacobian. Phase B validates state-dependent Candidate-A pullback QR and short-time EL equivalence. Phase C's three independently integrated canonical shadows satisfy the frozen `640 s` compatibility criteria, and the canonical ensemble satisfies the separate predeclared descriptive EL/canonical comparison rule. | The result supports one independently cross-formulated numerical spectrum estimate for the declared initial condition and deterministic policies. It is not an infinite-time proof, universal spectrum, or result over initial-condition space. |
| [012](lyapunov_validation/012_initial_condition_spectrum_robustness/README.md) | **Established:** all `18` frozen EL/canonical runs across three new zero-velocity conditions are numerically valid. IC-2 satisfies settling and same-IC formulation compatibility without demonstrating shadow independence. **Unresolved:** IC-1 and IC-3 decorrelate early but fail the `640 s` between-shadow settling limits. | The full selected-set formulation-robustness claim is unresolved. IC-2 is not classified as regular, and no result is generalized beyond the three selected conditions or to nonzero velocity. |
| [013 Phase A](lyapunov_validation/013_restart_grade_qr_continuation/README.md) | **Established:** lossless QR-boundary serialization and restart reproduce uninterrupted short EL and canonical calculations with zero observed difference. | Infrastructure validation only; it adds no long-time Lyapunov evidence and cannot retrofit missing restart arrays into Experiment 012. |
| [014](lyapunov_validation/014_unsettled_shadow_duration_convergence/README.md) | **Established:** all six from-zero EL runs are numerically valid and decorrelated through `1280 s`. IC-1 satisfies every frozen settling criterion. **Unresolved:** IC-3's final outer-component range remains `0.08894 s^-1`, above the `0.05 s^-1` limit. | The outcome-conditioned study supports one IC-specific `1280 s` ensemble claim, not a universal or infinite-time spectrum. Its mixed result closes the requirement for asymptotic settling at every future map point. |

Experiment 014 is the current boundary. It leaves Experiments 010–011's
accepted anchor and Experiment 012's preregistered results unchanged. The
duration extension resolves IC-1 but not IC-3, despite healthy numerics and
continued late spread contraction. This is evidence against making an
asymptotically settled spectrum a mandatory per-pixel teaching-map contract.

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
12. Experiment 011 Phase A derives $f_H=J_s\nabla H$ and
    $D f_H=J_s\nabla^2H$ directly from the repository Hamiltonian, rather than
    transforming the EL Jacobian. State maps, energy, independent $2\pi$
    periodicity, short reference flow, directional Jacobian checks, and the
    pure-$\theta_2$ tangent all pass the predeclared limits. Refined
    EL/canonical reference separation is at most `6.04e-15` in Candidate A;
    mapped tangent norm and log-growth errors are at most `1.42e-14`.
13. Experiment 011 Phase B evaluates the state-dependent pullback factor
    $A(z_k)=S\,\mathrm{D}\Phi(z_k)$ at every QR event, resets with
    $Y_H^+=A(z_k)^{-1}Q$, and validates metric orthonormality and reconstruction
    in both canonical and mapped EL tangent coordinates. Over five `0.25 s`
    cycles, internal errors remain at most `4.61e-15`. Baseline and refined
    canonical cycle logs differ from their corresponding EL values by at most
    `3.55e-15` and `1.85e-13`, respectively; final short diagnostic vectors
    differ by at most `1.50e-13 s^-1`.
14. Experiment 011 Phase C independently evolves baseline, strict, and
    half-step canonical shadows through `640 s`. All pairs decorrelate by
    `37.96 s`, all `7680` QR cycles remain numerically valid, and every
    inherited within-shadow and between-shadow criterion passes. The canonical
    mean is approximately
    `(0.9870, 0.00742, -0.00554, -0.9897) s^-1`, with descriptive half-widths
    `(0.0206, 0.00355, 0.00272, 0.0211) s^-1`. Its largest componentwise
    displacement from the EL mean is `0.00485 s^-1`; all predeclared
    envelope-overlap, absolute-displacement, combined-six-shadow, and late-
    drift comparison checks pass.
15. Experiment 012 executes `18` additional `640 s` runs and all `46,080` QR
    cycles pass the declared validity guards. IC-1 and IC-3 reference shadows
    decorrelate by `32.6 s` and `18.3 s`, respectively, but their final/late
    between-shadow outer-component spread remains above the frozen limits in
    both formulations. IC-2 satisfies both formulation settling contracts and
    the same-IC EL/canonical rule to near machine precision, while none of its
    numerical-shadow pairs reaches Candidate-A distance `1`; its accepted
    claim is therefore policy-stable formulation agreement without
    demonstrated shadow independence.
16. Experiment 013 Phase A adds restart-grade QR-boundary state for both
    formulations: locally rebased reference coordinates, post-QR tangent
    matrix, cumulative logs, elapsed cycle bookkeeping, energy baseline, and
    source/runtime provenance. Lossless serialization followed by a short
    `0.5→1.0 s` resume reproduces uninterrupted EL and canonical cycle data
    with zero observed numerical difference in the tested runtime. This is
    infrastructure validation, not new long-time Lyapunov evidence.
17. Experiment 014 executes six new from-zero EL shadows through `1280 s`,
    accounting for all `30,720` QR cycles and preserving `42` restart-grade
    checkpoints. IC-1's final maximum component range is `0.03230 s^-1` and
    all settling limits pass. IC-3's range contracts from `0.15249 s^-1` at
    `480 s` to `0.08894 s^-1` at `1280 s`, but its final range, final sample
    SD, and late-window range still fail the frozen limits. Both ensembles
    demonstrate pairwise reference-shadow independence.

No finite-time scalar or vector reported by Experiments 004–009 was an
accepted Lyapunov exponent or spectrum. Experiments 010 and 011 Phase C now
support independently formulated, descriptively compatible long-time
numerical spectrum estimates within their matched three-shadow protocols.
Experiment 012 extends numerical-validity evidence to three additional states
and accepts limited same-IC agreement at IC-2. Experiment 014 adds an IC-1
`1280 s` independent-shadow settling result but leaves IC-3 unresolved. None
of these results is a universal spectrum for the double pendulum.

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

For the canonical state

$$
z=(q_1,q_2,p_1,p_2),
\qquad p=B(q)\omega,
$$

Experiment 011 Phase A validates the independently Hamiltonian-derived
operator $D f_H(z)$. Phases B and C validate the Candidate-A pullback factor
and QR reset over the short cross-formulation interval and the complete
three-shadow `640 s` protocol:

$$
A(z)=S\,\mathrm{D}(z\mapsto x),
\qquad
\lVert\delta z\rVert=\lVert A(z)\delta z\rVert_2.
$$

$$
A(z_k)Y_{H,k}^-=Q_kR_k,
\qquad
Y_{H,k}^+=A(z_k)^{-1}Q_k.
$$

This is a validated comparison convention, not a unique canonical norm. A
fixed dimensionless canonical metric remains possible but would introduce a
finite-time metric transient.

## Unestablished claims

The project has not established:

- compatibility across a larger or probabilistically defined numerical-shadow
  ensemble;
- whether any fixed duration is generally sufficient under other
  formulations, norms, tangent bases, or physical initial conditions;
- whether the common-reference QR-interval and tangent-policy collapse remains
  negligible at substantially longer duration;
- convergence toward the asymptotic structure expected of a Hamiltonian flow;
- agreement between a one-vector tangent estimate and the leading QR estimate;
- robustness to tangent-basis initialization;
- a maximal Lyapunov exponent for the current reference trajectory;
- whether EL/canonical robustness holds across the complete Experiment 012
  selected set, because IC-3 remains unsettled even at `1280 s`; or
- any broader classification of an initial-condition region or the
  double-pendulum system as chaotic.

The accepted Experiment 010 limits apply only to its completed continuation
design. They do not turn its descriptive uncertainty envelope into a formal
confidence interval.

## Next justified question

The next justified research question is no longer another automatic duration
extension. It is:

> What fixed horizon, finite-time tangent-QR observable, and explicit
> uncertainty/validity labelling form a scientifically honest contract for a
> teaching-oriented state-space map?

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
from the magnitudes of the diagonal entries of $R$. Experiment 011 Phase C
retains $A(z)=S\,\mathrm{D}(z\mapsto x)$ and $Y^+=A(z)^{-1}Q$ through three
independently decorrelated canonical shadows and accepts the resulting
cross-formulation comparison. Experiment 012 tested the fixed three-condition
design, Experiment 013 supplied restart-grade continuation, and Experiment 014
then extended the two unsettled EL ensembles to `1280 s`. Because IC-1 settles
but IC-3 does not, further duration is not assumed to be the right default for
map construction. A map contract should expose a fixed-horizon finite-time
quantity and its validity boundary rather than silently promote every pixel to
an asymptotic exponent.

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

Experiment 010's EL `640 s` mean has total sum `-0.000924 s^-1`, while
Experiment 011 Phase C's canonical mean has total sum `-0.000800 s^-1`,
outer-pair sum `-0.002684 s^-1`, inner-pair sum `0.001884 s^-1`, and middle
magnitudes `0.007421` and `0.005537 s^-1`. These are supporting finite-time
diagnostics only. The project has not proven the Hamiltonian asymptotic
spectrum. The expressions remain theoretical structural expectations, not
target values that a calculation should be engineered to reproduce.

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
  ↓
011 Phase A  independent canonical reference/tangent primitive accepted
  ↓
011 Phase B  canonical pullback-QR primitive and short EL equivalence accepted
  ↓
011 Phase C  independent canonical ensemble and EL/canonical compatibility accepted
  ↓
012  three-condition protocol numerically valid; IC-2 limited agreement accepted,
     IC-1/IC-3 ensemble settling unresolved at 640 s
  ↓
013 Phase A  restart-grade EL/canonical QR-boundary continuation accepted
  ↓
014  targeted 1280 s EL extension: IC-1 settles; IC-3 remains unsettled
  ↓  asymptotic per-pixel settling is not the map contract
predeclare a fixed-horizon finite-time tangent-QR map observable and validity labels
  ↓  only after that individual diagnostic contract is accepted
carefully bounded state-space exploration
```

This is orientation, not a reserved sequence of experiment numbers or a rigid
roadmap. Experiment 014 closes the targeted duration study with a mixed result;
future evidence may still change the map contract.
