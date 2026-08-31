# 011 Hamiltonian/Canonical Spectrum Cross-Check

**Status: Phases A, B, and C accepted within their declared boundaries. The
canonical reference/tangent and pullback-QR primitives are validated, three
independent canonical shadows satisfy the frozen `640 s` compatibility
criteria, and their ensemble is descriptively compatible with Experiment
010's independent EL ensemble.**

## Research question (answered in Phase C)

> Does an independently formulated Hamiltonian/canonical tangent QR
> calculation reproduce the statistically compatible Euler–Lagrange spectrum
> estimate accepted by Experiment 010?

Experiment 010 accepted, within its declared one-initial-condition and three-
shadow protocol, the Euler–Lagrange ensemble mean

$$
(0.983276,\ 0.012274,\ -0.009941,\ -0.986532)\ \mathrm{s^{-1}},
$$

with conservative descriptive componentwise half-widths

$$
(0.023858,\ 0.006367,\ 0.008376,\ 0.024798)\ \mathrm{s^{-1}}.
$$

Those half-widths are not confidence intervals. They combine Experiment 010's
final ensemble spread and residual `560→640 s` settling. They were the
independent comparison evidence used by Phase C, not values fitted by
Experiment 011.

## Original scaffold purpose (historical)

The committed scaffold established source provenance and an implementation
boundary so Phase A could proceed without broad repository archaeology. The
detailed inventory, now extended with verified Phase A findings, is in
[`canonical_model_notes.md`](canonical_model_notes.md).

The repository already supplies:

- production canonical state and initial-condition conversion conventions;
- a production symbolic simple-model Hamiltonian;
- production symbolic Hamilton equations and a numerical solver wrapper;
- short EL/Hamiltonian formulation-agreement regression evidence; and
- a self-contained but explicitly exploratory Hamiltonian/Poincaré RHS and
  numeric energy evaluator.

At that scaffold boundary it did not supply a validated canonical flow
Jacobian/Hessian, canonical tangent evolution, canonical QR metric contract,
or long-time Hamiltonian spectrum evidence. Phases A--C subsequently supply
those staged experiment-local validations.

## Intended evidence sequence

The later executable experiment must proceed in this order:

```text
canonical state/formulation
  → EL ↔ canonical state equivalence
  → reference-flow equivalence
  → canonical tangent/Jacobian validation
  → canonical QR validation
  → eventual long-time spectrum comparison
```

| Stage | Evidence required before proceeding |
| --- | --- |
| Canonical state/formulation | Reproduce the production state order, Legendre map, Hamiltonian, parameters, and angular periodicity without copying exploratory code as authority. |
| EL ↔ canonical state equivalence | Validate forward and inverse state maps, including nonzero velocities and tangent-coordinate conversion. |
| Reference-flow equivalence | Show synchronized short canonical and EL reference trajectories agree after conversion under controlled solver policies. |
| Canonical tangent/Jacobian validation | Independently validate the canonical tangent operator with directional finite differences and periodicity/structural checks. |
| Canonical QR validation | Establish a dimensionally coherent metric, orthonormality, reconstruction, sign, and accumulation bookkeeping. |
| Long-time spectrum comparison | Only after all prior stages pass, compare a predeclared canonical ensemble with the Experiment 010 EL estimate and uncertainty boundary. |

Failure at any stage is a valid Experiment 011 outcome and stops the sequence.

## Current repository-supported formulation

The production canonical solver order is

$$
z=(\theta_1,\theta_2,p_{\theta_1},p_{\theta_2}),
$$

with $p=B(q)\dot q$ for the simple-model inertia matrix. Production constructs

$$
H(q,p)=\frac12p^{\mathsf T}B(q)^{-1}p+V(q)
$$

and forms

$$
\dot q=\frac{\partial H}{\partial p},
\qquad
\dot p=-\frac{\partial H}{\partial q}.
$$

Exact formulas, source locations, test evidence, and authority labels are
recorded in `canonical_model_notes.md`. This README does not promote the
exploratory Experiment 001 analytical RHS into accepted code.

## Original Python boundary (historical)

Before Phase A, `canonical_spectrum_crosscheck.py` contained only:

- static Experiment 010 target/provenance metadata;
- the canonical and EL state order contracts;
- a source-asset inventory;
- a small protocol describing eventual state conversion, energy, RHS, and
  Jacobian interfaces; and
- a `run_crosscheck()` placeholder that raises `NotImplementedError`.

That deliberate stop was first replaced by the Phase A implementation and
then by the Phase B and C QR paths described below. The current
`run_crosscheck()` entry point executes the frozen Phase C protocol; the
original refusal remains part of the scaffold history, not current behavior.

## Original unresolved choices

The scaffold required the later design to resolve, before long-time
computation:

1. how the canonical Jacobian is constructed and independently validated;
2. whether the tangent-coordinate map is derived analytically, symbolically,
   or by another controlled method;
3. the dimensionally coherent QR metric in canonical momentum coordinates;
4. whether that metric is a fixed canonical scaling or Candidate A pulled
   back through the state-dependent EL↔canonical tangent map;
5. how the initial tangent bases correspond across formulations;
6. the staged reference comparison and eventual numerical-shadow ensemble;
7. angle rebasing and $2\pi$ periodicity for canonical state, energy, RHS, and
   Jacobian;
8. the canonical numerical energy evaluator and normalization;
9. solver tolerance, `max_step`, restart, sampling, and QR-interval policies;
   and
10. a predeclared comparison rule that separates finite-time coordinate/metric
    transients from disagreement with Experiment 010.

No acceptance thresholds are invented in this scaffold.

## Accepted versus exploratory inputs

| Category | May be treated as current convention | Must be independently verified before scientific use |
| --- | --- | --- |
| Production model | Canonical state order; simple inertia/momentum map; symbolic Hamiltonian; Hamilton-equation construction; named solver policies | Numerical canonical RHS equivalence over the Experiment 010 reference; inverse and tangent maps; canonical Jacobian/Hessian; long-time validity |
| Experiment 001 Poincaré work | Evidence that a self-contained numerical formulation and energy diagnostic are feasible | Its explicit RHS, energy implementation, unrestricted-step solver protocol, event conventions, and unrelated initial condition |
| Experiment 010 | EL target mean, descriptive half-widths, physical case, Candidate-A result boundary | Any claim that the canonical finite-time QR geometry must reproduce individual EL QR columns pointwise |

## Scaffold claim boundary (historical)

Before Phase A, Experiment 011 established only that the repository contained
enough source material to design an independent canonical formulation, subject
to the documented validation and metric choices.

At that scaffold boundary no Hamiltonian tangent vector or matrix had been
evolved. The current boundary is recorded under **Phase A result** below. The
Experiment 010 vector remains solely an EL comparison target.

## Reproduction commands

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
development/chaos_content/experiments/011_hamiltonian_canonical_spectrum_crosscheck/test_canonical_spectrum_crosscheck.py
```

This focused test now exercises the Phase A primitive. The deterministic
numerical self-check and machine-readable evidence are generated with:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
development/chaos_content/experiments/011_hamiltonian_canonical_spectrum_crosscheck/canonical_spectrum_crosscheck.py \
--self-check
```

Outputs are written beneath the ignored
`development/chaos_content/outputs/hamiltonian_canonical_phase_a/baseline/`
directory.

The Phase B self-check is:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
development/chaos_content/experiments/011_hamiltonian_canonical_spectrum_crosscheck/canonical_spectrum_crosscheck.py \
--phase b --self-check
```

Its evidence is written beneath the ignored
`development/chaos_content/outputs/hamiltonian_canonical_phase_b/short_qr/`
directory.

## Phase A validation contract

This section was added before the first Phase A numerical run. It extends the
scaffold without changing the eventual long-time question.

### Formulation policy

Phase A will construct the experiment-local canonical Hamiltonian directly
from production's symbolic `compute_hamiltonian("simple")`, substitute the
accepted physical parameters, and derive

$$
f_H(z)=J_s\nabla H(z),
\qquad
D f_H(z)=\frac{\partial f_H}{\partial z},
$$

by symbolic differentiation in canonical variables. It will not transform or
reuse the EL Jacobian. The symbolic canonical Jacobian will be checked by
central directional finite differences of the canonical flow.

The accepted physical case remains

$$
m_1=m_2=1\ \mathrm{kg},\quad
l_1=l_2=1\ \mathrm{m},\quad
g=9.81\ \mathrm{m\,s^{-2}},
$$

$$
x_0=(179^\circ,179^\circ,0,0).
$$

### Compact validation set

State, energy, periodicity, and Jacobian checks use the initial state plus
three fixed nonzero-velocity states spanning moderate, wide-angle, and branch-
adjacent representatives. Jacobian checks add three states sampled from the
accepted reference interval. Fixed deterministic directions are used; no
state or finite-difference step is selected after viewing an error.

Reference and tangent comparisons cover `0–1.29 s` at `0.01 s` output spacing,
the local interval already validated by Experiment 006. Two matched EL and
canonical policies are used:

| Policy | DOP853 tolerances | `max_step` |
| --- | --- | ---: |
| baseline | `rtol=1e-9`, `atol=1e-11` | `0.0099773571 s` |
| refined | `rtol=1e-11`, `atol=1e-13` | `0.0049886786 s` |

Both formulations receive identical requested sample times and policy within
each comparison. Phase A performs no solver-method or duration sweep.

### Predeclared acceptance limits

The canonical primitive is accepted only if all of the following pass:

1. EL→canonical→EL and canonical→EL→canonical state round trips have maximum
   absolute component error at most $10^{-12}$.
2. Forward/inverse tangent-map products have maximum absolute error at most
   $10^{-12}$, and directional finite differences of the state map have
   relative error at most $5\times10^{-6}$.
3. Canonical $H$ and EL mechanical energy differ by at most $10^{-12}$ after
   normalization by the established energy scale; the physical initial state
   and zero momenta agree within $10^{-14}$.
4. Independent integer $2\pi$ shifts of either angle change canonical energy,
   flow, or Jacobian by at most $10^{-9}$ in absolute value.
5. At central-difference step $h=10^{-6}$, every tested canonical Jacobian-
   vector product has relative error at most $5\times10^{-5}$. The maximum
   Hamiltonian-matrix residual
   $\lVert J_H^{\mathsf T}J_s+J_sJ_H\rVert_\infty$ is at most $10^{-10}$.
6. Baseline EL/canonical reference separation never exceeds
   $10^{-7}$ in Candidate-A norm; refined separation never exceeds
   $2\times10^{-8}$. Both policies must integrate successfully with finite
   states.
7. Each reference run's maximum normalized energy drift is at most $10^{-7}$,
   and the baseline/refined canonical references differ by at most $10^{-6}$
   in Candidate-A norm.
8. For the refined pure-$\theta_2$ tangent comparison, mapping the canonical
   tangent back to EL coordinates yields maximum relative Candidate-A norm
   error, absolute log-growth error, and scaled direction-component error each
   at most $10^{-6}$; signed direction cosine must remain at least
   $1-10^{-10}$.
9. The Candidate-A pullback factor through the canonical→EL tangent map remains
   finite and nonsingular over the reference interval, with inverse/reset-map
   reconstruction error at most $10^{-12}$.

The state and energy tolerances target algebraic floating-point agreement.
The periodicity and Jacobian limits match or tighten the validated Experiment
006 checks. The flow/tangent limits are materially above expected roundoff but
well below the local perturbation and solver-policy differences that previous
experiments treated as meaningful. No threshold will be relaxed after the
run.

### Phase A outcomes

The result is classified as accepted below. Acceptance earns a separate,
predeclared canonical QR primitive and short-time metric-equivalence test. It
does not authorize a `640 s` Hamiltonian spectrum run.

## Canonical state and tangent contract

Phase A confirms the production canonical order

$$
z=(q_1,q_2,p_1,p_2)=(\theta_1,\theta_2,p_{\theta_1},p_{\theta_2}),
$$

and uses the simple-model inertia matrix $B(q)$ and Legendre map

$$
p=B(q)\omega,
\qquad
\omega=B(q)^{-1}p.
$$

The experiment imports the production symbolic $H(q,p)$, replaces the
time-dependent production symbols with independent canonical state symbols,
substitutes the accepted parameters, and constructs

$$
f_H(z)=J_s\nabla H(z),
\qquad
D f_H(z)=J_s\nabla^2H(z).
$$

This derivative path does not transform or reuse Experiment 006's EL
Jacobian. The EL flow and Jacobian enter only as the independent physical-
coordinate comparison.

The forward tangent-coordinate map is the differential of the Legendre map:

$$
\delta z=
\begin{pmatrix}
I&0\\
\mathrm{D}_q[B(q)\omega]&B(q)
\end{pmatrix}
\delta x,
$$

and its inverse is evaluated by the inverse-function theorem at the same
physical state.

## Phase A result

**Verdict: accepted canonical reference-flow and tangent primitive.** Every
predeclared criterion passed over the fixed `0–1.29 s` comparison. No
criterion was changed after the run.

| Validation | Strongest observed discrepancy | Predeclared limit |
| --- | ---: | ---: |
| EL/canonical state round trips | `4.44e-16` absolute | `1e-12` |
| Tangent-map inverse | `4.44e-16` absolute | `1e-12` |
| State-map directional finite difference | `4.46e-10` relative | `5e-6` |
| EL/canonical or matrix-form energy | `1.21e-16` normalized | `1e-12` |
| Independent $2\pi$ shifts: $H$, flow, Jacobian | `4.11e-14` maximum | `1e-9` |
| Canonical Jacobian directional finite difference at $h=10^{-6}$ | `1.01e-9` relative | `5e-5` |
| Hamiltonian-matrix identity residual | exactly `0.0` numerically | `1e-10` |
| Baseline EL/canonical reference separation | `2.76e-14` Candidate A | `1e-7` |
| Refined EL/canonical reference separation | `6.04e-15` Candidate A | `2e-8` |
| Canonical baseline/refined separation | `8.55e-14` Candidate A | `1e-6` |
| Maximum normalized reference-energy drift | `1.45e-15` | `1e-7` |
| Mapped tangent norm | `1.42e-14` relative | `1e-6` |
| Mapped tangent log growth | `1.42e-14` absolute | `1e-6` |
| Mapped tangent direction components | `2.84e-14` absolute | `1e-6` |
| Minimum signed tangent-direction cosine | `0.9999999999999996` | $1-10^{-10}$ |

The four production Hamilton equations also simplify symbolically to the four
components of $J_s\nabla H$ in the declared state order. The zero-momentum
canonical initial state is exactly

$$
(179^\circ,179^\circ,0,0),
$$

with angular entries interpreted in radians by the solver. The nonzero-
velocity representatives establish that the result is not relying on the
special zero-momentum initial condition.

Both formulations used synchronized output times. The baseline run used
DOP853 at `rtol=1e-9`, `atol=1e-11`, `max_step=0.0099773571 s`; the refined
run used `1e-11`, `1e-13`, and half that step cap. All integrations completed
with finite states. The agreement is therefore well inside the declared
formulation-error boundary and remains stable under the one predeclared solver
refinement.

## Canonical QR metric analysis

Let $\Phi:z\mapsto x$ be the canonical-to-EL state map and

$$
C(z)=\mathrm{D}\Phi(z),
\qquad
A(z)=S C(z).
$$

The recommended metric for the eventual formulation cross-check is the
state-dependent pullback of Candidate A,

$$
\lVert\delta z\rVert_{\mathrm{pullback}}
=\lVert A(z)\delta z\rVert_2.
$$

For a future canonical tangent matrix $Y$, the corresponding reset candidate
is

$$
A(z_k)Y_k^-=Q_kR_k,
\qquad
Y_k^+=A(z_k)^{-1}Q_k.
$$

This keeps the physical tangent geometry identical to Experiment 010 while
leaving the canonical reference and tangent equations independently derived.
Over the Phase A reference the factor remains nonsingular, has maximum
condition number `12.40`, minimum absolute determinant `0.05097`, and inverse
reconstruction error `4.44e-16`.

A fixed dimensionless canonical metric is also possible. One defensible scale
uses characteristic momenta

$$
P_{1c}=\frac{(m_1+m_2)l_1^2}{T_c},
\qquad
P_{2c}=\frac{m_2l_2^2}{T_c},
$$

which are `6.26418` and `3.13209 kg m² s⁻¹` for this fixture. That choice is
conventional, however, and would add a finite-time metric transient to the
formulation comparison. A regular bounded change of norm should leave
asymptotic exponents invariant, but finite-time QR columns and component
estimates need not match. The pullback metric is therefore recommended as the
primary controlled comparison; a fixed canonical metric is at most a later
sensitivity check, not a tuning device.

## Current claim boundary and next question

Experiment 011 Phase A establishes that the repository-supported simple-model
Hamiltonian, Legendre map, canonical reference flow, and independently
Hamiltonian-derived tangent operator reproduce the accepted EL physical flow
and local tangent dynamics over the declared validation interval under both
tested solver policies.

It does **not** establish a canonical QR primitive, a finite-time canonical
spectrum, a long-time Hamiltonian spectrum, agreement with Experiment 010's
four values, or a maximal Lyapunov exponent.

The single next question is:

> Does full-matrix canonical tangent evolution with QR in the Candidate-A
> pullback metric have internally correct orthonormality, reconstruction, sign,
> and accumulation bookkeeping, while reproducing the corresponding short-time
> EL QR calculation?

Only an accepted answer to that question would make a predeclared long-time
canonical spectrum comparison defensible.

## Phase B validation contract

This contract was recorded before the first Phase B numerical run. Phase A's
canonical flow, Jacobian, state map, tangent map, and Candidate-A pullback are
fixed inputs; Phase B does not rederive them.

### Question and controlled protocol

Phase B asks:

> Does full-matrix canonical tangent evolution with QR in the Candidate-A
> pullback metric have internally correct orthonormality, reconstruction, sign,
> and accumulation bookkeeping, while reproducing the corresponding short-time
> Euler–Lagrange QR calculation?

The deterministic primary run is deliberately limited to `1.25 s`, five
`0.25 s` QR cycles, and `0.01 s` diagnostic sampling. This stays inside Phase
A's accepted `0–1.29 s` EL/canonical comparison interval while exercising the
same QR cadence as Experiment 007. No duration or cadence sweep is included.

Two matched formulation pairs are predeclared:

| Pair | DOP853 tolerances | `max_step` |
| --- | --- | ---: |
| baseline | `rtol=1e-9`, `atol=1e-11` | `0.0099773571 s` |
| refined | `rtol=1e-11`, `atol=1e-13` | `0.00498867855 s` |

Within each pair, the EL and canonical calculations use identical physical
initial state, QR boundaries, sample times, tolerance, and step cap. One exact
repeat of the canonical baseline is used only as a determinism check.

### Basis correspondence and reset

With $C(z)=\mathrm{D}\Phi(z)$ and $A(z)=SC(z)$, initialize

$$
Y_{\mathrm{EL},0}=S^{-1},
\qquad
Y_{H,0}=A(z_0)^{-1}.
$$

Then

$$
S Y_{\mathrm{EL},0}=A(z_0)Y_{H,0}=I,
\qquad
Y_{\mathrm{EL},0}=C(z_0)Y_{H,0}.
$$

At every canonical QR event, Phase B recomputes $A(z_k)$ from that event's
canonical reference state, then applies

$$
A(z_k)Y_{H,k}^-=Q_kR_k,
\qquad
Y_{H,k}^+=A(z_k)^{-1}Q_k.
$$

The reference angles are locally rebased after each segment. Canonical momenta
and tangent columns are unchanged by the integer-$2\pi$ chart transition,
whose derivative is the identity. Lifted winding is not introduced.

Both formulations use Experiment 007's deterministic QR convention: after
NumPy QR, corresponding columns of $Q$ and rows of $R$ are flipped so every
$R_{ii}$ is positive. Columns are never sorted.

### Predeclared internal limits

Every canonical cycle must satisfy:

1. successful complete finite reference/tangent integration and normalized
   Hamiltonian drift at most $10^{-7}$;
2. finite $A(z_k)$, minimum singular value at least $10^{-6}$, and condition
   number at most $10^3$;
3. pre-QR scaled tangent condition number at most $10^{12}$;
4. $Q$ orthonormality, pullback-metric post-reset orthonormality, and reset-map
   errors at most $10^{-12}$;
5. scaled and canonical-coordinate reconstruction relative errors at most
   $10^{-12}$;
6. finite positive $R_{ii}\ge10^{-14}$ and finite logarithms; and
7. independently recomputed cumulative logs and diagnostic rates agreeing
   with stored values to $10^{-12}$.

The exact canonical repeat must reproduce cycle logs, cumulative logs, final
diagnostic values, and final physical reference state to $10^{-12}$.

### Predeclared cross-formulation limits

At synchronized events, after applying $C(z)$ and $A(z)$, each baseline and
refined EL/canonical pair must satisfy:

- maximum reference separation: `1e-7` Candidate A for baseline and `2e-8`
  for refined;
- pre-QR scaled and mapped physical tangent-matrix relative differences at
  most `2e-6`;
- positive-diagonal $Q$ component and post-reset mapped-basis differences at
  most `2e-6`;
- relative $R_{ii}$ and absolute per-cycle log differences at most `2e-6`;
- cumulative-log difference at most `1e-5`; and
- final four-component diagnostic-vector difference at most
  `1e-5 s^-1`.

These are formulation-equivalence limits, not Lyapunov convergence limits.
They are anchored to Phase A's `1e-6` full tangent-coordinate comparison and
allow five-cycle accumulation without relaxing Experiment 007's internal
machine-precision QR requirements.

### Predeclared numerical-refinement limits

For both formulations separately, baseline/refined comparison must keep the
maximum reference distance at most `1e-6`, maximum cycle-log difference at
most `1e-4`, maximum cumulative-log difference at most `5e-4`, and final
diagnostic-vector difference at most `5e-4 s^-1`. The two matched
cross-formulation comparisons must also pass the tighter limits above. This
compact refinement distinguishes a formulation/QR discrepancy from ordinary
short-run solver error; it is not a convergence study.

### Phase B claim boundary

Acceptance establishes only an internally coherent canonical pullback-QR
primitive and short-time equivalence with the corresponding EL QR calculation.
It does not establish a long-time canonical spectrum, agreement with the
Experiment 010 `640 s` estimate, statistical compatibility across canonical
shadows, or a maximal Lyapunov exponent.

## Phase B result

**Verdict: accepted canonical pullback-QR primitive and short-time EL
equivalence.** Every predeclared internal, cross-formulation, refinement, and
exact-repeat check passes. No Phase B threshold was changed after execution.

### Internal pullback-QR validity

At each event the implementation evaluates the current
$C(z_k)=\mathrm{D}\Phi(z_k)$ and $A(z_k)=SC(z_k)$; no constant-factor shortcut
is used. It then performs positive-diagonal QR on $A(z_k)Y_{H,k}^-$ and solves
the current linear system for $Y_{H,k}^+$. Across both policies, the limiting
internal diagnostics are:

| Diagnostic | Observed bound | Predeclared limit |
| --- | ---: | ---: |
| Maximum $\kappa_2(A)$ | `12.1003` | `1e3` |
| Minimum singular value of $A$ | `0.121953` | `1e-6` minimum |
| Maximum $\kappa_2(A Y_H^-)$ | `26.6229` | `1e12` |
| $Q^{\mathsf T}Q-I$ infinity norm | `1.27e-15` | `1e-12` |
| Scaled $A Y_H^- - QR$ relative error | `3.54e-16` | `1e-12` |
| Canonical $Y_H^- - Y_H^+R$ relative error | `5.23e-16` | `1e-12` |
| Mapped physical reconstruction relative error | `4.93e-16` | `1e-12` |
| Post-reset pullback orthonormality error | `4.61e-15` | `1e-12` |
| Reset identity $A Y_H^+-Q$ error | `5.62e-16` | `1e-12` |
| Minimum positive $R_{ii}$ | `0.227361` | `1e-14` minimum |
| Cumulative-log/rate bookkeeping error | exactly `0.0` | `1e-12` |
| Maximum normalized Hamiltonian drift | `7.24e-16` | `1e-7` |

All five segments complete with finite reference and tangent states. Every
$R_{ii}$ is positive after the paired sign resolution, every log is finite,
and no column sorting occurs. The canonical baseline exact repeat has zero
recorded difference in cycle logs, cumulative logs, diagnostic vectors, and
the final physical reference state.

### EL/canonical cycle correspondence

The corresponding EL calculation is Experiment 007's accepted QR primitive,
restricted to the same five cycles. Canonical tangent matrices are compared
only after applying $C(z)$ or $A(z)$ as appropriate.

| Maximum discrepancy over five cycles | Baseline | Refined | Declared bound |
| --- | ---: | ---: | ---: |
| Reference Candidate-A distance | `1.76e-15` | `1.78e-13` | `1e-7` / `2e-8` |
| Pre-QR scaled relative difference | `2.79e-15` | `1.75e-13` | `2e-6` |
| Mapped physical pre-QR relative difference | `3.08e-15` | `2.38e-13` | `2e-6` |
| Positive-diagonal $Q$ component difference | `2.38e-15` | `1.11e-13` | `2e-6` |
| Relative $R_{ii}$ difference | `3.56e-15` | `1.85e-13` | `2e-6` |
| Per-cycle log difference | `3.55e-15` | `1.85e-13` | `2e-6` |
| Cumulative-log difference | `4.44e-15` | `2.42e-13` | `1e-5` |
| Final diagnostic-vector difference | `3.11e-15 s^-1` | `1.50e-13 s^-1` | `1e-5 s^-1` |

The baseline cumulative log vectors at `1.25 s` are

$$
L_{\mathrm{EL}}=
(4.906391904210701, 3.164484293856641,
-2.327408630581164, -6.375856172102764),
$$

$$
L_H=
(4.906391904210698, 3.164484293856640,
-2.327408630581165, -6.375856172102762).
$$

Dividing by the elapsed `1.25 s` gives the short diagnostic vectors

$$
\Lambda_{\mathrm{EL}}=
(3.925113523368561, 2.531587435085313,
-1.861926904464931, -5.100684937682211) \mathrm{s^{-1}},
$$

$$
\Lambda_H=
(3.925113523368558, 2.531587435085312,
-1.861926904464932, -5.100684937682209) \mathrm{s^{-1}}.
$$

These column-ordered values are neither sorted nor interpreted as a converged
spectrum. Their short duration makes them especially unsuitable as estimates
of the Experiment 010 result.

### Compact numerical refinement

The baseline-to-refined final diagnostic change is `1.16e-13 s^-1` for EL and
`3.73e-14 s^-1` for canonical, against the predeclared `5e-4 s^-1` limit.
Maximum cycle-log changes are `1.43e-13` and `4.05e-14`; maximum cumulative-log
changes are `1.86e-13` and `5.95e-14`. Baseline/refined reference distances
remain at most `1.36e-13` for EL and `4.34e-14` for canonical. Thus the observed
cross-formulation agreement is not hiding a discrepancy at the selected
solver resolution.

### Phase B claim boundary and next question

Phase B establishes that full-matrix evolution under the independently
Hamiltonian-derived canonical tangent operator admits internally coherent QR
in the state-dependent Candidate-A pullback metric. With corresponding initial
bases and deterministic signs, it reproduces the accepted EL QR calculation
cycle-by-cycle over `0–1.25 s` under both tested policies.

It does **not** establish a long-time canonical Lyapunov spectrum, agreement
with Experiment 010 at `640 s`, statistical compatibility across independently
diverging canonical shadows, or a maximal Lyapunov exponent.

The single next scientific question is:

> Under a predeclared long-time canonical shadow/refinement protocol, do
> cumulative pullback-QR estimates become statistically compatible with one
> another and with Experiment 010's accepted Euler–Lagrange ensemble estimate?

That question is now methodologically earned but is not run in Phase B.

## Phase C long-time validation contract

**This contract was frozen before the first long-time canonical run.** Phase
C takes the accepted Phase A Hamiltonian flow/Jacobian and the accepted Phase
B pullback-QR primitive as fixed inputs. It does not alter the state map,
metric, tangent basis, QR signs, column order, physical initial condition, or
QR cadence in response to the result.

### Questions

Phase C separates two decisions:

1. Do three independently integrated canonical numerical shadows satisfy the
   established long-time within-shadow and between-shadow compatibility
   limits?
2. If so, is their terminal ensemble descriptively compatible with the
   independently obtained Experiment 010 Euler--Lagrange ensemble under a
   separately declared symmetric rule?

Long-time pointwise agreement between EL and canonical reference trajectories
is neither expected nor tested.

### Frozen canonical ensemble

All three runs start from

$$
(	heta_1,	heta_2,omega_1,omega_2)
=(179^\circ,179^\circ,0,0)
$$

after conversion to $z=(q_1,q_2,p_1,p_2)$. They independently evolve the
canonical reference and tangent matrix for `640 s`, apply positive-diagonal
pullback QR every `0.25 s`, and retain cumulative fixed-column estimates at

$$
80, 160, 240, 320, 400, 480, 560, 640\ \mathrm{s}.
$$

The numerical policies exactly mirror Experiments 009--010:

| Shadow | DOP853 tolerances | `max_step` |
| --- | --- | ---: |
| baseline | `rtol=1e-9`, `atol=1e-11` | `0.0099773571 s` |
| strict | `rtol=1e-11`, `atol=1e-13` | `0.0099773571 s` |
| half step | `rtol=1e-9`, `atol=1e-11` | `0.00498867855 s` |

Each QR boundary is already an integration restart, so saving a completed
`80 s` block and resuming from its post-QR reference, tangent basis, and
cumulative log vector does not add a new restart or change the numerical
semantics. Canonical angles are rebased to the principal chart only at the
existing QR boundaries. The chart-transition derivative is the identity;
momenta and tangent columns are not changed, and winding is not accumulated in
solver state or tangent geometry.

### A. Predeclared canonical internal-compatibility criteria

Phase C moves Experiment 010's terminal-window logic to the canonical
ensemble without changing any threshold. Acceptance requires all of:

1. all three runs pass the Phase B solver, Hamiltonian-drift, pullback-factor,
   QR, reconstruction, diagonal, and cumulative-bookkeeping guards through all
   `2560` cycles;
2. all three pairwise reference distances cross Candidate-A distance `1.0` by
   `80 s`, establishing that the comparison is among decorrelated numerical
   shadows rather than duplicate trajectories;
3. for each shadow, the largest component change is at most `0.08 s^-1` from
   `480→560 s` and `0.05 s^-1` from `560→640 s`;
4. for each shadow and component, the cumulative range anywhere over
   `560–640 s` is at most `0.05 s^-1`;
5. at `640 s`, every between-shadow component range is at most `0.05 s^-1`
   and every sample standard deviation is at most `0.025 s^-1`;
6. the largest component change in the ensemble mean from `560→640 s` is at
   most `0.04 s^-1`; and
7. the largest between-shadow component range anywhere over `560–640 s` is at
   most `0.07 s^-1`.

There is no Experiment 010-style `320 s` prefix-reproduction condition:
Phase C is the first canonical long-time run, so no prior canonical prefix
exists to reproduce. Omitting an inapplicable provenance check does not change
any settling, spread, decorrelation, or numerical-validity threshold.

If numerical validity or decorrelation fails, canonical compatibility is
numerically unresolved. If every condition passes it is accepted. Otherwise,
Phase C reports internal incompatibility/unresolved settling at `640 s`; it
does not tune or extend the run.

The canonical descriptive component half-width is computed exactly as in
Experiment 010: the componentwise maximum of final sample standard deviation,
half the final range, and the largest absolute per-shadow `560→640 s` change.
It is not a confidence interval.

### B. Predeclared EL/canonical compatibility criterion

The cross-formulation comparison is evaluated only if both the committed EL
ensemble and the new canonical ensemble pass their own internal criteria. Let
$\mu_F$, $s_F$, $r_F$, and $w_F$ be formulation $F$'s `640 s` ensemble mean,
three-shadow sample standard deviation, component range, and descriptive
half-width, respectively, for $F\in\{\mathrm{EL},H\}$. Let
$d_F=\mu_F(640)-\mu_F(560)$.

Descriptive compatibility requires, component by component:

1. overlapping descriptive envelopes,
   $|\mu_H-\mu_{\mathrm{EL}}|\le w_H+w_{\mathrm{EL}}$;
2. absolute terminal mean displacement no larger than `0.05 s^-1`;
3. the range of the combined six terminal shadow values no larger than
   `0.07 s^-1`;
4. the sample standard deviation of those six values no larger than
   `0.025 s^-1`; and
5. $|d_H-d_{\mathrm{EL}}|\le0.04\ \mathrm{s^{-1}}$.

This rule is symmetric between formulations, uses both observed
within/between-shadow scales, and retains Experiment 010's already accepted
absolute numerical scales. The envelope condition does not treat Experiment
010's half-widths as confidence intervals, while the absolute and combined-
ensemble guards prevent broad descriptive envelopes from manufacturing
agreement. This is a finite deterministic numerical compatibility rule, not a
formal hypothesis test for six random samples.

Failure of this rule is a cross-formulation incompatibility finding, not a
numerical failure unless a numerical-validity guard also fails. If the
canonical ensemble is not internally accepted, the cross-formulation result
is reported as unresolved rather than forcing a comparison.

### Numerical evidence and claim boundary

Every run records checkpoint and per-cycle cumulative spectra, reference
samples for decorrelation, policy provenance, solver statistics, normalized
Hamiltonian drift, extrema of $A(z)$ conditioning and singular values, QR and
pullback orthonormality, scaled/canonical/physical reconstruction, reset
identity, positive $R$ diagonals, and cumulative-log bookkeeping. Total sum,
outer-pair sum, inner-pair sum, and middle-component magnitudes are supporting
Hamiltonian diagnostics only.

Even if both questions pass, Phase C can establish only a compatible `640 s`
canonical/EL cumulative pullback-QR estimate for this physical initial
condition and declared deterministic shadow policies. It cannot establish an
infinite-time theorem, exact finite-time Hamiltonian pairing, universality
over initial conditions or parameters, or a production chaos-classification
algorithm.

## Phase C result

**Verdict: both questions accepted.** No criterion above was changed after the
canonical calculation began.

1. The independently integrated canonical shadows satisfy every predeclared
   numerical-validity, decorrelation, within-shadow, terminal-spread, and
   late-window criterion at `640 s`.
2. The accepted canonical ensemble satisfies every part of the separate
   predeclared descriptive compatibility rule against Experiment 010's EL
   ensemble.

### Canonical checkpoint spectra

Each run contains `2560` canonical QR cycles. All values below are cumulative
fixed-column estimates in $\mathrm{s^{-1}}$; columns were never sorted during
evolution.

| Shadow | `80 s` | `160 s` | `240 s` | `320 s` |
| --- | --- | --- | --- | --- |
| baseline | `(0.778751, 0.067455, -0.051256, -0.795208)` | `(0.870062, 0.023100, -0.018239, -0.879127)` | `(0.867066, 0.016117, -0.013803, -0.872247)` | `(0.901208, 0.016693, -0.013165, -0.906852)` |
| strict | `(0.909591, 0.085215, -0.059277, -0.940765)` | `(1.051828, 0.025767, -0.018523, -1.063323)` | `(0.986515, 0.013790, -0.012101, -0.990201)` | `(0.991682, 0.020752, -0.014079, -1.000507)` |
| half step | `(0.929239, 0.067795, -0.054115, -0.945707)` | `(0.912911, 0.024394, -0.021695, -0.919170)` | `(0.984191, 0.017100, -0.008520, -0.993589)` | `(1.000706, 0.015425, -0.011416, -1.006628)` |

| Shadow | `400 s` | `480 s` | `560 s` | `640 s` |
| --- | --- | --- | --- | --- |
| baseline | `(0.927647, 0.009801, -0.005747, -0.932782)` | `(0.961196, 0.009450, -0.007567, -0.963086)` | `(0.984387, 0.010794, -0.008017, -0.988363)` | `(0.992088, 0.007241, -0.006017, -0.994396)` |
| strict | `(0.997561, 0.014510, -0.010242, -1.003486)` | `(0.986324, 0.012867, -0.008469, -0.990884)` | `(0.959373, 0.006287, -0.005090, -0.961148)` | `(0.964389, 0.004151, -0.002613, -0.966619)` |
| half step | `(1.015772, 0.011861, -0.009502, -1.018214)` | `(1.017975, 0.009707, -0.008143, -1.019715)` | `(1.001571, 0.010463, -0.007482, -1.005539)` | `(1.004592, 0.010870, -0.007980, -1.008107)` |

The reference pairs cross Candidate-A distance `1.0` at `34.82`, `34.83`,
and `37.96 s`, all before the declared `80 s` deadline. Their later
pointwise separation is expected and is not a spectrum-agreement test.

### Canonical internal compatibility

| Shadow | Maximum `480→560 s` change | Maximum `560→640 s` change | Maximum range over `560–640 s` | Result |
| --- | ---: | ---: | ---: | --- |
| baseline | `0.025277` | `0.007701` | `0.023147` | passes |
| strict | `0.029736` | `0.005471` | `0.014944` | passes |
| half step | `0.016403` | `0.003021` | `0.020287` | passes |

The final component ranges are

$$
(0.040202, 0.006719, 0.005366, 0.041488)\ \mathrm{s^{-1}},
$$

and the final sample standard deviations are

$$
(0.020574, 0.003363, 0.002715, 0.021138)\ \mathrm{s^{-1}}.
$$

Both are within the inherited `0.05` and `0.025 s^-1` limits. The maximum
ensemble-mean `560→640 s` change is `0.005246 s^-1`, and the maximum
between-shadow range anywhere over that late window is `0.056842 s^-1`, below
the `0.04` and `0.07 s^-1` limits respectively.

The accepted canonical ensemble mean is

$$
(0.987023, 0.007421, -0.005537, -0.989707)\ \mathrm{s^{-1}},
$$

with the Experiment 010-style descriptive half-width

$$
(0.020574, 0.003553, 0.002715, 0.021138)\ \mathrm{s^{-1}}.
$$

These widths remain descriptive numerical envelopes, not confidence
intervals.

### EL/canonical ensemble comparison

The componentwise absolute displacement between the canonical and EL `640 s`
ensemble means is

$$
(0.003748, 0.004853, 0.004404, 0.003175)\ \mathrm{s^{-1}}.
$$

The corresponding sums of descriptive half-widths are

$$
(0.044432, 0.009920, 0.011092, 0.045936)\ \mathrm{s^{-1}}.
$$

Thus all four descriptive envelopes overlap; the largest displacement-to-
envelope-sum ratio is `0.489`. The combined six-shadow component ranges are

$$
(0.040202, 0.013288, 0.013135, 0.041488)\ \mathrm{s^{-1}},
$$

and the combined sample standard deviations are

$$
(0.014486, 0.004437, 0.004350, 0.014660)\ \mathrm{s^{-1}}.
$$

Their maxima pass the declared `0.07` and `0.025 s^-1` guards. The maximum
componentwise difference between the two formulations' ensemble-mean
`560→640 s` drift vectors is `0.006714 s^-1`, below `0.04 s^-1`. The result is
therefore accepted descriptive numerical compatibility, not a formal
six-sample statistical inference.

### Numerical and Hamiltonian diagnostics

All `7680` aggregate canonical cycles complete with finite reference/tangent
states and positive finite $R_{ii}$. The limiting inherited guards are:

| Diagnostic | Observed extremum | Limit |
| --- | ---: | ---: |
| normalized Hamiltonian drift | `7.61e-10` | `1e-7` |
| $\kappa_2(A)$ | `81.20` | `1e3` |
| minimum singular value of $A$ | `0.06333` | `1e-6` minimum |
| pre-QR condition number | `687.47` | `1e12` |
| minimum positive $R_{ii}$ | `0.06350` | `1e-14` minimum |
| $Q$ orthonormality error | `2.57e-15` | `1e-12` |
| canonical reconstruction error | `4.17e-15` | `1e-12` |
| physical reconstruction error | `1.07e-15` | `1e-12` |
| post-reset pullback orthonormality error | `1.29e-14` | `1e-12` |
| cumulative-log/rate bookkeeping | exactly `0.0` | `1e-12` |

For the canonical ensemble mean, the spectrum sum is `-0.000800 s^-1`, the
outer-pair sum is `-0.002684 s^-1`, the inner-pair sum is `0.001884 s^-1`,
and the middle magnitudes are `0.007421` and `0.005537 s^-1`. These approach
the expected Hamiltonian structure but remain supporting finite-time
diagnostics, not acceptance targets.

### Phase C claim boundary and next question

The strongest earned claim is:

> Independently integrated, decorrelated canonical Hamiltonian shadows
> produce statistically compatible `640 s` cumulative pullback-QR spectrum
> estimates, and the resulting canonical ensemble is descriptively compatible
> with the independently obtained Euler--Lagrange ensemble under the
> predeclared rule.

This supplies independent formulation-level support for the numerical
spectrum estimate under the one declared physical initial condition and
protocol. It does not prove an infinite-time limit, establish a universal
double-pendulum spectrum, or validate a chaos map or classification over
initial-condition space.

The single next scientific question is:

> Across a small, predeclared set of additional physical initial conditions,
> does independent EL/canonical spectrum agreement persist without retuning
> the accepted numerical protocol?

Phase C does not begin that investigation.

### Phase C evidence and reproduction

The ignored machine-readable bundle is written to

```text
development/chaos_content/outputs/hamiltonian_canonical_phase_c/640s_ensemble/
```

It contains `summary.json`, all eight checkpoint vectors, the complete
cumulative time series, reduced per-cycle QR/validity evidence, pairwise
reference-distance histories, and a SHA-256 manifest. Reproduce the frozen run
and its non-outcome-dependent consistency self-check with:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  development/chaos_content/experiments/011_hamiltonian_canonical_spectrum_crosscheck/canonical_spectrum_crosscheck.py \
  --phase c \
  --self-check \
  --output-dir development/chaos_content/outputs/hamiltonian_canonical_phase_c/640s_ensemble
```
