# 012 Initial-Condition Spectrum Robustness

**Status: protocol frozen, not executed. No Experiment 012 trajectory or
spectrum has been computed.**

## Question

> Across a small, predeclared design in zero-velocity configuration space,
> does independent Euler–Lagrange/canonical long-time spectrum agreement
> persist without retuning the accepted numerical protocol?

Experiment 012 is restricted to

$$
x_0=(\theta_1,\theta_2,0,0).
$$

It therefore tests robustness across a small subset of configuration space,
not robustness to initial angular velocity. That limitation is fixed, not an
unresolved design choice.

[Experiment 010](../010_independent_shadow_640s_compatibility/README.md)
accepted the Euler–Lagrange (EL) three-shadow result at
$(179^\circ,179^\circ,0,0)$, and
[Experiment 011](../011_hamiltonian_canonical_spectrum_crosscheck/README.md)
independently accepted canonical-shadow compatibility and descriptive
EL/canonical compatibility at the same physical initial condition. That point
is retained as a historical anchor. Its six accepted `640 s` integrations are
referenced rather than rerun, and it does not count as a new condition.

This document preregisters the additional conditions and decision logic. It
does not provide numerical evidence for them.

## Fixed inherited protocol

The following contract is inherited unchanged from Experiments 010–011 for
every new condition.

### Physical and tangent formulations

- Simple double pendulum with

  $$
  m_1=m_2=1\ \mathrm{kg},\qquad
  l_1=l_2=1\ \mathrm{m},\qquad
  g=9.81\ \mathrm{m\,s^{-2}}.
  $$

- EL state and independently validated tangent flow

  $$
  x=(\theta_1,\theta_2,\omega_1,\omega_2),
  \qquad
  \dot Y_{\mathrm{EL}}=J_{\mathrm{EL}}(x)Y_{\mathrm{EL}}.
  $$

- Canonical state and independently Hamiltonian-derived tangent flow

  $$
  z=(q_1,q_2,p_1,p_2),
  \qquad
  \dot Y_H=Df_H(z)Y_H.
  $$

- Candidate-A scaling

  $$
  S=\operatorname{diag}(1,1,T_c,T_c),
  \qquad
  T_c=\sqrt{\frac{1\ \mathrm m}{g}},
  \qquad
  \lVert\delta x\rVert_{\mathrm{EL}}=\lVert S\delta x\rVert_2.
  $$

- EL QR acts on $SY_{\mathrm{EL}}$. Canonical QR uses the accepted
  Candidate-A pullback

  $$
  A(z)=S\,D\Phi(z),
  $$

  with

  $$
  A(z_k)Y_{H,k}^-=Q_kR_k,
  \qquad
  Y_{H,k}^+=A(z_k)^{-1}Q_k.
  $$

- Corresponding initial bases

  $$
  Y_{\mathrm{EL},0}=S^{-1},
  \qquad
  Y_{H,0}=A(z_0)^{-1}.
  $$

- Deterministic positive-$R_{ii}$ QR signs, with no tangent-column sorting.
- QR cadence `0.25 s`.
- Solver-facing angular representatives remain locally rebased. Winding does
  not enter solver error control or tangent geometry.

### Numerical shadows and duration

Each formulation independently integrates three reference/tangent shadows:

| Shadow | `rtol` | `atol` | `max_step` |
| --- | ---: | ---: | ---: |
| baseline | `1e-9` | `1e-11` | `0.0099773571 s` |
| strict | `1e-11` | `1e-13` | `0.0099773571 s` |
| half step | `1e-9` | `1e-11` | `0.00498867855 s` |

Every run ends at `640 s`, with cumulative checkpoints at
`80/160/240/320/400/480/560/640 s`. The terminal comparison window is
`560–640 s`. EL and canonical trajectories, and the three policies within
each formulation, are independent numerical shadows; pointwise trajectory
correspondence after decorrelation is not required.

## What Experiment 012 must not retune

The following may not be changed per condition after any numerical outcome is
known:

- physical parameters or zero-velocity scope;
- solver tolerances or step caps;
- QR cadence, duration, or checkpoints;
- Candidate-A geometry or canonical pullback metric;
- tangent-basis initialization and correspondence;
- positive-diagonal sign convention or tangent-column order;
- numerical-validity thresholds;
- cumulative-settling thresholds;
- shadow-independence classification rule; or
- EL/canonical compatibility rule.

If execution exposes a genuine global defect, the protocol must be stopped,
revised explicitly for the complete selected set, and rerun without replacing
an inconvenient condition. It must not be repaired one condition at a time.

## Frozen initial-condition design

### Selection rule declared before the points

Use the principal periodic domain

$$
(\theta_1,\theta_2)\in[-\pi,\pi)\times[-\pi,\pi).
$$

For each angular coordinate, divide the circle into three equal half-open
arcs,

$$
[-\pi,-\pi/3),\qquad[-\pi/3,\pi/3),\qquad[\pi/3,\pi),
$$

and take their midpoints

$$
a_0=-\frac{2\pi}{3},\qquad a_1=0,\qquad
a_2=\frac{2\pi}{3}.
$$

Pair these levels by the positive cyclic Latin shift

$$
(\theta_1,\theta_2)=(a_j,a_{j+1\pmod 3}),
\qquad j=0,1,2.
$$

This rule is geometric and deterministic. It was fixed before deriving the
individual pairs. It uses every angular level exactly once in each coordinate
without constructing a grid. It uses no trajectory, Lyapunov, flip,
Poincaré, sensitivity, solver-difficulty, or chaos-map information.

A geometry-first rule is preferable here to hand-picked energy strata:
analytical energy remains a useful description of the resulting coverage,
but choosing energy targets would add another arbitrary design axis. The
three-level cyclic design happens to span three distinct analytical energies;
that fact is an outcome of the geometric rule, not a criterion used to tune
it.

### Complete new condition list

The rule yields exactly three new physical initial conditions:

| ID | $\theta_1$ | $\theta_2$ | $\omega_1$ | $\omega_2$ |
| --- | ---: | ---: | ---: | ---: |
| A | $-120^\circ$ | $0^\circ$ | $0$ | $0$ |
| B | $0^\circ$ | $120^\circ$ | $0$ | $0$ |
| C | $120^\circ$ | $-120^\circ$ | $0$ | $0$ |

Equivalently,

$$
\begin{aligned}
x_{0,A}&=(-2\pi/3,0,0,0),\\
x_{0,B}&=(0,2\pi/3,0,0),\\
x_{0,C}&=(2\pi/3,-2\pi/3,0,0).
\end{aligned}
$$

The accepted $(179^\circ,179^\circ,0,0)$ case remains the reference anchor
and is neither a fourth new case nor part of the Experiment 012 compute load.

### Why three new cases

Three is the smallest defensible count for this rule:

- one new condition would be only another case study;
- two conditions would provide one contrast but cannot realize a balanced
  three-level cyclic design; and
- three conditions use all three levels once in each coordinate, distinguish
  the two coordinate roles, avoid symmetry duplicates, and supply low,
  intermediate, and high analytical initial energies without a grid survey.

The count is intentionally small because every new condition costs six
independent `640 s` reference/tangent integrations. It cannot estimate a
state-space distribution, establish representativeness, or support a global
classification. In particular, the design does not deliberately cover
equilibria, the full potential-energy range, nonzero velocities, or every
symmetry class.

### Analytical initial-energy coverage

For the accepted unshifted potential and zero initial velocities,

$$
H_0=V_0
=-(m_1+m_2)g l_1\cos\theta_1-m_2g l_2\cos\theta_2
=-g(2\cos\theta_1+\cos\theta_2).
$$

In the final equality the fixed unit mass and length are understood. Define
$E_*=1\ \mathrm{kg}\,g\,1\ \mathrm m=9.81\ \mathrm J$ to keep the exact
energy statements dimensionally explicit. The design then gives:

| ID | $H_0$ | Numerical value |
| --- | ---: | ---: |
| A | $0$ | $0\ \mathrm J$ |
| B | $-3E_*/2$ | $-14.715\ \mathrm J$ |
| C | $+3E_*/2$ | $+14.715\ \mathrm J$ |

For context, the zero-velocity configuration-space potential range is
$[-3E_*,+3E_*]=[-29.43,+29.43]\ \mathrm J$, while the established
$(179^\circ,179^\circ)$ anchor has

$$
H_0=-3E_*\cos179^\circ\approx29.425518\ \mathrm J.
$$

These values document coverage only. They do not predict or classify the
dynamics.

## Periodicity and symmetry treatment

The design counts physical states rather than coordinate representatives.

### Periodic equivalence

Independent integer shifts are coordinate equivalences:

$$
(\theta_1,\theta_2)
\sim(\theta_1+2\pi n_1,\theta_2+2\pi n_2),
\qquad n_1,n_2\in\mathbb Z.
$$

The half-open principal domain supplies one deterministic representative.
Periodic copies are never additional evidence.

### Exact global reflection

The simple model is invariant under the simultaneous reflection

$$
(\theta_1,\theta_2,\omega_1,\omega_2)
\mapsto(-\theta_1,-\theta_2,-\omega_1,-\omega_2).
$$

At zero velocity this reduces to
$(\theta_1,\theta_2)\mapsto(-\theta_1,-\theta_2)$. It preserves the
potential, the relative-angle inertia coupling, and Candidate-A geometry. In
canonical coordinates it also changes $(p_1,p_2)$ to $(-p_1,-p_2)$; the
selected initial momenta are zero.

The negative cyclic Latin shift is exactly the global-reflection image of the
positive-shift set. Selecting the positive orientation is therefore only a
representative convention. Running both would double-count equivalent
evidence.

### Transformations that are not duplicate evidence

- Time reversal changes the signs of angular velocities. On the fixed
  zero-velocity initial slice it maps an initial state to itself; it does not
  generate another case.
- Exchanging $\theta_1$ and $\theta_2$ is not a physical symmetry of the
  serial pendulum, even for equal masses and lengths. The potential weights
  the upper angle by $m_1+m_2$ and the lower angle by $m_2$, and the inertia
  matrix does not interchange its diagonal roles.
- Flipping only one angle is not generally a symmetry: it changes the
  relative-angle coupling from functions of $\theta_1-\theta_2$ to functions
  of $\theta_1+\theta_2$.
- Pairs that look symmetric, such as $\theta_1=\pm\theta_2$, are not declared
  equivalent unless related by periodicity or the exact global reflection.

The three selected cases are pairwise inequivalent under the periodic and
global-reflection relations above. Experiment 012 includes no separate
symmetry-check integration and does not count a symmetry image as an
independent robustness case.

## Frozen acceptance contract

The decision structure separates four questions for every selected initial
condition. A physical-regime label is never inferred from a failed numerical
criterion.

### A. Numerical validity

Numerical validity is independent of whether reference shadows decorrelate.
Every EL run must satisfy the established Experiment 010 limits:

- complete finite integration and globally monotonic cycle times;
- normalized energy drift at most `1e-7`;
- QR orthonormality, reconstruction, post-reset metric orthonormality, and
  cumulative/rate bookkeeping errors at most `1e-12`;
- every $R_{ii}$ finite, positive, and at least `1e-14`; and
- pre-QR scaled tangent-matrix condition number at most `1e12`.

Every canonical run must satisfy the corresponding Experiment 011 limits,
including:

- normalized Hamiltonian drift at most `1e-7`;
- QR, scaled/canonical/physical reconstruction, pullback orthonormality,
  reset-identity, and cumulative/rate bookkeeping errors at most `1e-12`;
- every $R_{ii}$ finite, positive, and at least `1e-14`;
- pre-QR pulled-back tangent-matrix condition number at most `1e12`;
- minimum singular value of $A(z)$ at least `1e-6`; and
- condition number of $A(z)$ at most `1e3`.

Failure is **numerically invalid**, not evidence of a regular or chaotic
physical regime.

### B. Cumulative-spectrum settling and policy stability

For EL and canonical results separately, inherit the absolute Experiment
010/011 limits unchanged. For every spectrum component:

- each shadow's change from `480→560 s` is at most `0.08 s^-1`;
- each shadow's change from `560→640 s` is at most `0.05 s^-1`;
- each shadow's component range over `560–640 s` is at most `0.05 s^-1`;
- the final three-policy component range is at most `0.05 s^-1`;
- the final three-policy sample standard deviation is at most `0.025 s^-1`;
- the ensemble-mean component change from `560→640 s` is at most
  `0.04 s^-1`; and
- the maximum three-policy component range at any terminal-window checkpoint
  is at most `0.07 s^-1`.

The per-component descriptive half-width remains

$$
w_i=\max\left(
s_i(640),
\frac{1}{2}\operatorname{range}_i(640),
\max_{r}\left|\lambda_{i,r}(640)-\lambda_{i,r}(560)\right|
\right).
$$

These are absolute numerical scales already accepted for the same physical
model, QR geometry, duration, and policies. No repository evidence justifies
manufacturing new values before execution. Absolute thresholds also avoid
ill-conditioned relative errors when a component is near zero.

The Experiment 010 requirement to reproduce an already stored `320 s` prefix
does not apply to a new physical condition because no accepted prefix exists.
All other same-concept thresholds are inherited.

### C. Shadow-independence status

This diagnostic describes the evidence supplied by the three numerical
policies; it is not a validity or chaos classifier. For each formulation,
measure all three pairwise Candidate-A reference-state separations and retain
the established material-separation scale $d_{\mathrm{EL}}=1$.

- **Early decorrelation:** all three pairs first cross $d_{\mathrm{EL}}=1$
  by `80 s`.
- **Terminal-window independence:** early decorrelation is not met, but all
  three pairs have crossed by `560 s`, before the complete terminal window.
- **Independence not demonstrated:** at least one pair has not crossed by
  `560 s`. A crossing only during `560–640 s` does not make the complete
  terminal window an independent-shadow comparison.

The condition's aggregate status is the weaker of the EL and canonical
statuses. The labels depend only on a predeclared physical distance and time,
not on the spectrum values. A non-decorrelating condition can pass A and B,
but its small between-policy spread is refinement agreement among nearby
shadows, not evidence from independent decorrelated samples. It must not be
post-hoc relabelled “regular.”

### D. EL/canonical formulation compatibility

Compare EL and canonical estimates only for the same physical initial
condition and only after both formulations pass A and B. Inherit Experiment
011's symmetric descriptive rule unchanged. For every component:

1. the ensemble-mean envelopes overlap,

   $$
   |\mu_{H,i}-\mu_{\mathrm{EL},i}|\le w_{H,i}+w_{\mathrm{EL},i};
   $$

2. the terminal ensemble-mean displacement is at most `0.05 s^-1`;
3. the combined six-policy terminal range is at most `0.07 s^-1`;
4. the combined six-policy terminal sample standard deviation is at most
   `0.025 s^-1`; and
5. the absolute difference between the formulations' `560→640 s`
   ensemble-mean drifts is at most `0.04 s^-1`.

The widths and spreads are descriptive numerical evidence, not confidence
intervals or a formal hypothesis test. Shadow-independence status qualifies
the strength of the claim but does not change this same-IC formulation test.
Spectra from different physical initial conditions are not required to agree
with one another.

## Per-condition outcomes

Apply the following hierarchy without substituting or rerunning a condition:

1. **Numerically invalid:** A fails in either formulation. No spectrum or
   physical-regime inference is accepted.
2. **Numerically valid but unsettled at `640 s`:** A passes, but B fails in
   either formulation. The result is unresolved at the frozen duration;
   failure is not a “regular” label.
3. **Settled but cross-formulation incompatible:** A and B pass in both
   formulations, but D fails. This rejects formulation robustness for that
   condition under the declared protocol.
4. **Settled formulation agreement with decorrelated shadows:** A, B, and D
   pass and C reaches early or terminal-window decorrelation in both
   formulations. The result supports formulation agreement with meaningful
   independent-shadow evidence, with the timing category reported.
5. **Settled formulation agreement without demonstrated shadow
   independence:** A, B, and D pass, but C is not demonstrated in at least one
   formulation. The earned claim is limited to cumulative settling,
   numerical-policy stability, and EL/canonical agreement. It does not claim
   statistically compatible independent shadows, regularity, or chaos.

This hierarchy prevents a failed chaotic-case criterion from becoming a
post-hoc regular-case escape hatch while allowing valid non-decorrelating
calculations to be reported honestly.

## Experiment-level verdict logic

- **Full selected-set formulation robustness is accepted** only if all three
  new conditions pass A, B, and D.
- If all three also demonstrate C in both formulations by `560 s`, a stronger
  statement about independent-shadow formulation robustness is supported.
- If A, B, and D pass for all cases but one or more do not demonstrate C, the
  accepted claim is explicitly limited to policy-stable, settled
  cross-formulation agreement for the selected zero-velocity design.
- Any A failure makes the full-set result numerically unresolved; the case is
  not replaced.
- Any B failure makes robustness unresolved at `640 s`; the duration is not
  automatically extended.
- If A and B pass everywhere but D fails anywhere, formulation robustness
  across the complete selected set is rejected.

Genuine component differences between conditions are reported as physical
initial-condition dependence, not a protocol failure. A favorable condition
cannot average away another condition's failure.

## Exact future workload

The frozen execution contains:

$$
3\ \text{new conditions}
\times2\ \text{formulations}
\times3\ \text{numerical policies}
=18\ \text{integrations}.
$$

Each integration advances one reference state and one $4\times4$ tangent
matrix for `640 s` with `0.25 s` QR cadence. Therefore the planned total is:

- `11,520` simulated formulation-seconds;
- `46,080` QR cycles (`2,560` per integration); and
- `144` stored checkpoint spectrum vectors (`8` per integration).

The established anchor adds no new run. There are no pilot runs, adaptive
duration extensions, replacement conditions, symmetry duplicates, or
per-condition protocol variants in this workload.

## Claim boundary

This preregistration has selected cases and frozen a protocol, but has not
established:

- spectrum robustness across any new initial condition;
- robustness to nonzero initial angular velocities;
- that any selected condition is regular or chaotic;
- a global Lyapunov field, chaos map, or classifier;
- a universal double-pendulum spectrum;
- infinite-time convergence; or
- a production algorithm.

The selection rule is deliberately small and deterministic. Even a completely
accepted result would apply only to these three new zero-velocity conditions,
the historical anchor, the fixed physical model, and the declared numerical
protocol.

## Execution boundary

The four preregistration questions are resolved: selection rule, case count,
symmetry treatment, and regime-neutral acceptance semantics are frozen. No
scientific design question remains before implementation. The next bounded
task is to implement an experiment-local, resumable runner and execute exactly
the `18` preregistered integrations without changing this contract.

That task is not performed here.
