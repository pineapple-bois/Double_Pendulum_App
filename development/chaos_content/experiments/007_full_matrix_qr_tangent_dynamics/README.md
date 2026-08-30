# 007 Full-Matrix QR Tangent Dynamics

**Status: full-matrix QR primitive accepted; convergence investigation
completed with the spectrum numerically unresolved through `80 s`.**

The first iteration of this experiment is the minimal executable full-matrix
QR extension of the direct Euler–Lagrange tangent dynamics validated by
Experiment 006. It asks:

> Can the validated tangent dynamics be extended from one tangent vector to a
> four-vector basis with periodic QR renormalisation in the existing
> Candidate-A geometry, with self-consistent mathematical and numerical
> bookkeeping?

That primitive is accepted. The second iteration applies the predeclared
duration, tolerance, step-cap, and QR-interval matrix below. Its four reported
finite-time values remain diagnostics, not a converged Lyapunov spectrum or a
maximal Lyapunov exponent.

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

### Primitive decision

The QR primitive is accepted for the limited claim that the validated
Experiment 006 tangent dynamics admits an internally coherent four-vector
Candidate-A-scaled QR extension for this modest run. The convergence iteration
below does not revoke that primitive result.

## Convergence investigation contract

The second Experiment 007 iteration asks whether the cumulative four-component
QR estimate converges under compact duration and numerical refinement. The
accepted QR map is unchanged.

### Fixed comparison matrix

The baseline is extended once to `80 s`. Its cumulative values at `20`, `40`,
and `80 s` provide the duration ladder without integrating separate duplicate
prefixes. At `80 s`, compare exactly four controlled variants:

| Case | Tolerances | `max_step` | QR interval |
| --- | --- | ---: | ---: |
| baseline | `rtol=1e-9`, `atol=1e-11` | `0.0099773571 s` | `0.25 s` |
| strict tolerance | `rtol=1e-11`, `atol=1e-13` | baseline | `0.25 s` |
| half step cap | baseline | `0.0049886786 s` | `0.25 s` |
| short QR interval | baseline | baseline | `0.125 s` |
| long QR interval | baseline | baseline | `0.5 s` |

The common step cap is retained for both QR-interval variants so that those
runs isolate the orthonormalisation interval rather than silently changing two
policies. No other durations, tolerances, step caps, QR intervals, or tangent
bases are part of the declared matrix.

A separate one-vector calculation uses the first initial basis column,
$S^{-1}e_1$, the baseline numerical policy, and the same `0.25 s`
renormalisation interval. It checks the first QR column only and does not form
a second investigation.

### Cumulative quantities and predeclared criteria

All convergence decisions use

$$
\Lambda_i(T_n)=\frac{1}{T_n}
\sum_{k=1}^{n}\log |R_{ii}^{(k)}|.
$$

Per-cycle values remain diagnostics and are not treated as converged rates.
Components remain in fixed QR-column order; they are not sorted to make
comparisons look closer.

Absolute differences in `s^-1` are primary because relative errors become
ill-conditioned for neutral components. The primitive values are order one,
so the limits below demand approximately percent-scale numerical agreement and
five-percent-scale late duration stability without assuming any component is
nonzero.

Duration convergence requires all of:

1. maximum component change from `20→40 s` at most `0.10 s^-1`;
2. maximum component change from `40→80 s` at most `0.05 s^-1`; and
3. for every component, the range of cumulative values over `60–80 s` at most
   `0.05 s^-1`.

Numerical-policy convergence at `80 s` requires:

1. baseline/strict maximum component difference at most `0.01 s^-1`;
2. baseline/half-step maximum component difference at most `0.01 s^-1`;
3. baseline/short-QR and baseline/long-QR maximum component differences each
   at most `0.02 s^-1`; and
4. baseline one-vector cumulative rate within `0.01 s^-1` of the first QR
   component.

Every run must continue to pass the primitive QR/reconstruction checks, return
complete finite output, and keep normalized reference energy drift below
$10^{-7}$. Reference-path distances across policies are recorded but are not a
long-time acceptance condition: independently integrated chaotic references
may separate while a statistical spectrum estimate remains stable.

The whole spectrum is accepted as converged sufficiently for this controlled
reference case only if every duration, policy, one-vector, and numerical
validity check passes. If numerical-policy checks pass but either the late
duration change or final-quarter range exceeds `0.10 s^-1` (twice its limit),
the spectrum is classified **clearly not converged**. Smaller duration failures
are **unresolved at the tested durations**. Any failed numerical-policy or
validity check is **numerically unresolved**, regardless of duration trends.

### Hamiltonian diagnostics

For interpretation only, sort a copy of each final four-vector and report the
sum, outer-pair defect, inner-pair defect, and magnitudes of the two middle
values. These are theoretical asymptotic diagnostics, not finite-time
acceptance conditions and not target values to force.

## Convergence findings

### Duration behaviour

The baseline cumulative estimates in fixed QR-column order are:

| Duration | Cumulative four-component estimate / $\mathrm{s^{-1}}$ |
| ---: | --- |
| `20 s` | `(0.730611, 0.290286, -0.175815, -0.851214)` |
| `40 s` | `(0.861257, 0.148660, -0.113648, -0.911578)` |
| `80 s` | `(1.010631, 0.073345, -0.059582, -1.032261)` |

The maximum component change is `0.141626 s^-1` from `20→40 s` and
`0.149374 s^-1` from `40→80 s`, failing the respective `0.10` and `0.05`
limits. The largest cumulative-component range over `60–80 s` is
`0.092971 s^-1`, also above its `0.05` limit. The `40→80 s` change exceeds the
predeclared `0.10 s^-1` clear-nonconvergence diagnostic. Thus the baseline
duration evidence is not converged.

### Numerical refinements

Every full-matrix run completes with finite output and passes the inherited
energy and accepted QR-primitive checks. The final results are:

| Case | `80 s` cumulative estimate / $\mathrm{s^{-1}}$ | Maximum difference from baseline / $\mathrm{s^{-1}}$ | Limit |
| --- | --- | ---: | ---: |
| baseline | `(1.010631, 0.073345, -0.059582, -1.032261)` | — | — |
| strict tolerance | `(0.928799, 0.054264, -0.036095, -0.955069)` | `0.081832` | `0.01` |
| half step cap | `(0.864843, 0.049962, -0.040601, -0.875490)` | `0.156771` | `0.01` |
| `0.125 s` QR interval | `(0.861020, 0.074327, -0.053381, -0.884393)` | `0.149611` | `0.02` |
| `0.5 s` QR interval | `(0.918346, 0.068334, -0.060261, -0.929529)` | `0.102732` | `0.02` |

All four whole-spectrum comparisons fail their predeclared numerical limits.
The final Candidate-A distances between independently integrated reference
endpoints are `3.36–5.21`, confirming that the refined policies no longer
follow the same numerical shadow trajectory at `80 s`; those distances were
recorded rather than used as convergence criteria.

The first execution exposed a diagnostic-only bug in the short-QR case: the
global output check assumed the nominal `0.01 s` sampling interval divided
every QR interval exactly. It now derives the expected count from each actual
requested segment grid. A focused `0.125 s` regression test passes, and the
unchanged convergence matrix was rerun. This repair does not change the ODE,
QR map, accumulated growth, or comparison thresholds.

Across the final matrix, the largest QR orthonormality error is
$2.35\times10^{-15}$, the largest physical reconstruction relative error is
$8.05\times10^{-16}$, the smallest $R_{ii}$ is `0.04646`, and the largest
pre-QR condition number is `1095.55`. Maximum normalized reference energy
drift is $7.55\times10^{-10}$, well inside the $10^{-7}$ limit. The numerical
disagreement is therefore not accompanied by an obvious failure of the QR
primitive, tangent resolution guard, solver completion, or reference-energy
diagnostic.

### One-vector and Hamiltonian diagnostics

The conventional one-vector calculation is numerically valid and gives
`0.960877 s^-1`; it differs from the first baseline QR component by
`0.049754 s^-1`, failing the `0.01 s^-1` check. Because it integrates a
separate augmented system, its long-time reference shadow also need not match
the full-matrix baseline.

For the baseline, the interpretive spectrum sum remains small:
`-0.006131 s^-1` at `20 s` and `-0.007867 s^-1` at `80 s`. At `80 s`, the
sorted outer-pair defect is `-0.021630 s^-1`, the inner-pair defect is
`0.013763 s^-1`, and the middle magnitudes are `0.073345` and
`0.059582 s^-1`. These trends are qualitatively compatible with the expected
Hamiltonian asymptotic structure, but they are not acceptance evidence and do
not overcome the failed duration and policy comparisons.

### Convergence decision

Experiment 007 is **numerically unresolved at the tested durations and
refinements**. The baseline duration sequence meets the predeclared
clear-nonconvergence diagnostic, while every tolerance, step-cap, QR-interval,
and one-vector comparison fails its numerical agreement limit. Because the
classification hierarchy gives numerical-policy failure priority, the overall
result is unresolved rather than an accepted spectrum or a purely
duration-limited rejection.

The strongest supported statement is:

> The validated Euler–Lagrange tangent flow and Candidate-A-scaled QR primitive
> remain internally coherent and numerically valid, but the cumulative
> four-component estimates have not converged through `80 s` and remain
> materially dependent on the tested long-time numerical shadow path.

## Claim boundary

The four `80 s` vectors are diagnostic cumulative estimates, not accepted
Lyapunov spectra. Experiment 007 does not establish basis-initialization
independence, a maximal Lyapunov exponent, Hamiltonian/canonical agreement,
multiple-state robustness, or chaos classification. The single next question
is whether substantially longer, still predeclared Euler–Lagrange QR runs
cause the policy-separated cumulative spectra to approach one common
asymptotic vector or retain material separation.

Machine-readable evidence is generated under
`development/chaos_content/outputs/full_matrix_qr_tangent_dynamics/convergence/`.
`summary.json` holds the criteria, matrix, comparisons, decision, and claim
boundary; `cycles.json`/`cycles.csv` retain baseline per-cycle QR evidence;
`refinement_matrix.csv` records every final spectrum;
`refinement_timeseries.csv` records every refinement's cumulative path; and
`one_vector_cycles.json` records the independent first-column check.

## Reproduction commands

From the repository root:

```bash
MPLCONFIGDIR=/tmp/double-pendulum-mpl \
XDG_CACHE_HOME=/tmp/double-pendulum-cache \
PYTHONDONTWRITEBYTECODE=1 \
.venv/bin/python \
development/chaos_content/experiments/007_full_matrix_qr_tangent_dynamics/full_matrix_qr_tangent_dynamics.py \
--mode primitive \
--output-dir development/chaos_content/outputs/full_matrix_qr_tangent_dynamics/baseline \
--self-check
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
development/chaos_content/experiments/007_full_matrix_qr_tangent_dynamics/full_matrix_qr_tangent_dynamics.py \
--mode convergence \
--output-dir development/chaos_content/outputs/full_matrix_qr_tangent_dynamics/convergence \
--self-check
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
development/chaos_content/experiments/006_variational_dynamics_validation \
development/chaos_content/experiments/007_full_matrix_qr_tangent_dynamics
```
