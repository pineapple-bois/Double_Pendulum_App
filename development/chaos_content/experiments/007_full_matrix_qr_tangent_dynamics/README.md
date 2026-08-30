# 007 Full-Matrix QR Tangent Dynamics

**Status: accepted for the full-matrix QR primitive only; no convergence
claim.**

This experiment is the minimal executable full-matrix QR extension of the
direct Euler–Lagrange tangent dynamics validated by Experiment 006. It asks:

> Can the validated tangent dynamics be extended from one tangent vector to a
> four-vector basis with periodic QR renormalisation in the existing
> Candidate-A geometry, with self-consistent mathematical and numerical
> bookkeeping?

The task validates the QR primitive only. The four reported finite-time values
are diagnostics, not a converged Lyapunov spectrum or a maximal Lyapunov
exponent.

## Foundation retained from Experiment 006

The experiment imports the sandbox-local `VariationalDynamics` implementation
from [`006_variational_dynamics_validation`](../006_variational_dynamics_validation/README.md)
as a read-only validated dependency. It does not rederive or replace the
production-derived symbolic Jacobian.

The reference problem remains

$$
x=(\theta_1,\theta_2,\omega_1,\omega_2),
\qquad
x_0=(179^\circ,179^\circ,0,0),
$$

with the simple Euler–Lagrange model, unit lengths and masses, and
$g=9.81\ \mathrm{m\,s^{-2}}$. The tangent matrix $Y\in\mathbb{R}^{4\times4}$
stores physical-coordinate tangent vectors in its columns and evolves as

$$
\dot{Y}=J(x)Y.
$$

Candidate A supplies the working tangent geometry:

$$
S=\operatorname{diag}(1,1,T_c,T_c),
\qquad
T_c=\sqrt{\frac{1\ \mathrm{m}}{g}},
\qquad
\lVert\delta x\rVert_{\mathrm{EL}}=\lVert S\delta x\rVert_2.
$$

Candidate A remains an explicit validated working convention, not a uniquely
privileged physical norm.

## QR map and bookkeeping contract

The initial physical tangent basis is

$$
Y_0=S^{-1}I,
$$

so its scaled representation $Z_0=SY_0$ is exactly the Euclidean identity.
After each tangent segment, form

$$
Z_k^-=SY_k^-,
\qquad
Z_k^-=Q_kR_k.
$$

NumPy's reduced QR is made deterministic by flipping corresponding columns of
$Q_k$ and rows of $R_k$ so every diagonal entry of $R_k$ is positive. The
post-reset physical basis is

$$
Y_k^+=S^{-1}Q_k.
$$

This must satisfy both

$$
(SY_k^+)^{\mathsf T}(SY_k^+)=I
$$

and the physical reconstruction identity

$$
Y_k^-=Y_k^+R_k.
$$

The signed orientation convention is fixed by positive $R_{k,ii}$; no column
sorting or finite-time exponent reordering is performed. Per-cycle growth is

$$
\ell_{k,i}=\log |R_{k,ii}|,
$$

with cumulative diagnostic estimates

$$
L_{N,i}=\sum_{k=1}^{N}\ell_{k,i},
\qquad
\Lambda_{N,i}=\frac{L_{N,i}}{t_N}.
$$

## Minimal numerical run

Only one baseline configuration is interpreted:

- total duration: `5.0 s`;
- QR interval: `0.25 s` (`20` cycles);
- requested diagnostic sampling: `0.01 s` within each cycle;
- DOP853 baseline policy: `rtol=1e-9`, `atol=1e-11`;
- explicit Experiment 006 step cap:
  $h_{\max}=\min(T_c/32,0.25/25)=0.0099773571\ \mathrm{s}$;
- deterministic local angular rebasing to $(-\pi,\pi]$ at QR boundaries.

The tangent basis is unchanged by the $2\pi$ reference-chart rebase because
that local coordinate transition has identity derivative. Winding is not a
tangent coordinate.

An exact repeat of this same configuration is used only to check deterministic
reproducibility. It is not a tolerance, duration, step-size, QR-interval, or
basis-initialization sweep.

## Primitive acceptance checks

Every cycle must satisfy:

1. solver success, complete requested output, and finite reference/tangent
   state;
2. QR orthonormality error
   $\lVert Q^{\mathsf T}Q-I\rVert_\infty\le10^{-12}$;
3. scaled QR reconstruction relative error
   $\lVert Z^- - QR\rVert_F/\max(1,\lVert Z^-\rVert_F)\le10^{-12}$;
4. physical reconstruction relative error
   $\lVert Y^- - Y^+R\rVert_F/\max(1,\lVert Y^-\rVert_F)\le10^{-12}$;
5. post-reset Candidate-A orthonormality error at most $10^{-12}$;
6. positive finite $R_{ii}$ values no smaller than $10^{-14}$;
7. finite cycle logs, cumulative logs, and finite-time estimates;
8. pre-QR condition number below the broad pathology guard $10^{12}$; and
9. normalized reference energy drift at most the inherited $10^{-7}$ limit.

Independent recomputation must recover the stored cumulative sums and rates to
$10^{-12}$. The exact-repeat cycle logs, final cumulative values, reference
end state, and final diagnostic spectrum must agree within $10^{-12}$.

These are internal-consistency and obvious-pathology guards. They are not
long-time Lyapunov convergence thresholds.

## Required evidence

The generated bundle records:

- configuration, inherited Jacobian provenance, solver policy, and claim
  boundary;
- every cycle's reference endpoints, $Y^-$, $Z^-$, $Q$, $R$, $Y^+$,
  diagonal growth, cumulative logs, and finite-time spectrum;
- QR, reconstruction, orthonormality, conditioning, solver, and energy checks;
- exact-repeat reproducibility diagnostics; and
- compact static plots of cumulative finite-time values and QR validity.

## Findings

The declared `5.0 s`, `20`-cycle run passes every primitive check. The final
cumulative log-growth vector, in fixed basis-column order, is

$$
(5.19689710, 5.93242807, -4.17413182, -7.46644574).
$$

Dividing only by the elapsed `5.0 s` gives the diagnostic finite-time values

$$
(1.03937942, 1.18648561, -0.83482636, -1.49328915)
\ \mathrm{s^{-1}}.
$$

The values are deliberately neither sorted nor interpreted as asymptotic
exponents. Their sum is `-0.10225048 s^-1`; no Hamiltonian pairing, neutral
direction, or zero-sum criterion is imposed on this short primitive run.

### QR and reset consistency

All cycles pass. The recorded maxima are:

| Diagnostic | Maximum |
| --- | ---: |
| $Q^{\mathsf T}Q-I$ infinity norm | $1.57\times10^{-15}$ |
| scaled $Z^--QR$ relative error | $6.66\times10^{-16}$ |
| physical $Y^--Y^+R$ relative error | $4.26\times10^{-16}$ |
| post-reset Candidate-A orthonormality error | $1.70\times10^{-15}$ |
| reset-map $SY^+-Q$ error | $1.84\times10^{-16}$ |

The smallest positive $R_{ii}$ is `0.227361`, well above the $10^{-14}$
resolution guard. The largest pre-QR scaled-basis condition number is
`41.5463`, far below the broad $10^{12}$ pathology guard. Independent
recomputation gives zero recorded cumulative-log and finite-time-rate
bookkeeping error.

### Reference and reproducibility

Every DOP853 segment returns complete finite output. The `20` segments require
`8272` RHS evaluations under the inherited Experiment 006 baseline policy and
step cap. Maximum normalized reference energy drift is
$5.70\times10^{-11}$, inside the inherited $10^{-7}$ limit.

The exact deterministic repeat has zero recorded difference in cycle logs,
cumulative logs, final finite-time values, and final Candidate-A reference
state distance. This repeat verifies reproducibility of the fixed primitive;
it is not a numerical refinement study.

### Decision

Experiment 007 is accepted for the limited claim that the validated
Experiment 006 tangent dynamics admits an internally coherent four-vector
Candidate-A-scaled QR extension for this modest run. The separate convergence
question has now been made executable, not answered.

## Claim boundary

Success may establish only that the validated Experiment 006 tangent dynamics
admits an internally coherent four-vector Candidate-A-scaled QR extension for
this modest deterministic run.

This experiment does not test convergence with duration, tolerance,
`max_step`, QR interval, or tangent-basis initialization. It does not implement
Hamiltonian/canonical dynamics, multiple initial conditions, chaos
classification, or production UI. It does not establish a maximal Lyapunov
exponent or a converged Lyapunov spectrum.

## Reproduction commands

From the repository root:

```bash
MPLCONFIGDIR=/tmp/double-pendulum-mpl \
XDG_CACHE_HOME=/tmp/double-pendulum-cache \
PYTHONDONTWRITEBYTECODE=1 \
.venv/bin/python \
development/chaos_content/experiments/007_full_matrix_qr_tangent_dynamics/full_matrix_qr_tangent_dynamics.py \
--output-dir development/chaos_content/outputs/full_matrix_qr_tangent_dynamics/baseline \
--self-check
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
development/chaos_content/experiments/006_variational_dynamics_validation \
development/chaos_content/experiments/007_full_matrix_qr_tangent_dynamics
```
