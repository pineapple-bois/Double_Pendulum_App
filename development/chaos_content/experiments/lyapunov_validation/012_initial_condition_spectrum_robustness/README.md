# 012 Initial-Condition Spectrum Robustness

**Status: frozen protocol executed. All `18` runs are numerically valid, but
the full selected-set formulation-robustness question remains unresolved at
`640 s` because IC-1 and IC-3 fail the preregistered settling criteria.**

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

At the preregistration boundary that task had not been performed. The frozen
execution and its results are recorded below without changing the preceding
contract.

---

## Frozen execution result

### Pre-execution gate and workload

The gate accepted every preregistered check before the first long run. It
verified the three states and zero velocities, analytical energies in both
formulations, EL/canonical state and tangent-basis correspondence, the three
solver policies, duration, QR cadence, checkpoints, positive-diagonal signs,
fixed column order, exclusion of the historical anchor, decision-schema
separation, and the absence of per-condition overrides.

The older EL helper exposed an unrounded characteristic-time step cap
(`0.009977357137... s`) while this README froze the decimal values
`0.0099773571 s` and `0.00498867855 s`. The gate caught that difference before
execution. Both formulations were bound to the frozen README literals. This
was an implementation correction before evidence collection, not a protocol
change. No defect was found after execution began, and no run was repeated,
replaced, extended, or selectively retuned.

All `18` integrations completed:

- `11,520` simulated formulation-seconds;
- `46,080` QR cycles; and
- `144` checkpoint spectrum vectors.

The analytical initial energies were independently reproduced as `0`,
`-14.715`, and `+14.715 J` in both EL and canonical coordinates.

### Result overview

| Condition | Energy | Numerical validity | EL settling | Canonical settling | Shadow independence | Same-IC EL/canonical comparison | Preregistered category |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| IC-1 `(-120°,0°,0,0)` | `0 J` | passes | fails between-shadow spread | fails final spread | early decorrelation in both | not evaluable because settling fails | **numerically valid but unsettled at `640 s`** |
| IC-2 `(0°,120°,0,0)` | `-14.715 J` | passes | passes | passes | not demonstrated in either | passes | **settled formulation agreement without demonstrated shadow independence** |
| IC-3 `(120°,-120°,0,0)` | `+14.715 J` | passes | fails between-shadow spread | fails final/late spread | early decorrelation in both | not evaluable because settling fails | **numerically valid but unsettled at `640 s`** |

Thus the experiment-level verdict is
**full selected set unresolved at `640 s`**. The result is not a rejection of
EL/canonical equivalence: the frozen comparison is ineligible for IC-1 and
IC-3 because its preregistered settling prerequisite fails.

## IC-1 result: `(-120°,0°,0,0)`, `H_0=0 J`

All values in the checkpoint tables are cumulative fixed-column estimates in
`s^-1`, rounded to six decimals. Full precision is retained in the generated
evidence.

### IC-1 EL checkpoint spectra

| Shadow | `80 s` | `160 s` | `240 s` | `320 s` | `400 s` | `480 s` | `560 s` | `640 s` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | `(0.915443, 0.099539, -0.071881, -0.939768)` | `(0.914988, 0.045283, -0.039896, -0.916884)` | `(0.906337, 0.025281, -0.021820, -0.909394)` | `(0.883050, 0.025817, -0.019532, -0.889711)` | `(0.867813, 0.016921, -0.015126, -0.869532)` | `(0.844436, 0.009511, -0.007526, -0.845936)` | `(0.866825, 0.006858, -0.005293, -0.868627)` | `(0.869081, 0.012131, -0.008526, -0.872027)` |
| strict | `(0.937364, 0.089617, -0.072480, -0.953539)` | `(0.836523, 0.054678, -0.046430, -0.841770)` | `(0.866907, 0.035642, -0.027892, -0.872728)` | `(0.892939, 0.025538, -0.020962, -0.895779)` | `(0.895237, 0.022148, -0.019197, -0.897873)` | `(0.900380, 0.017960, -0.016072, -0.901323)` | `(0.909580, 0.016112, -0.013015, -0.912576)` | `(0.920552, 0.013284, -0.011793, -0.922134)` |
| half step | `(0.937813, 0.081078, -0.058594, -0.960196)` | `(0.946612, 0.039307, -0.035464, -0.948786)` | `(0.952364, 0.033361, -0.024943, -0.960652)` | `(0.956428, 0.021973, -0.018796, -0.959640)` | `(0.968541, 0.015911, -0.014037, -0.969063)` | `(0.970463, 0.015263, -0.012163, -0.973789)` | `(0.947421, 0.013037, -0.010478, -0.950170)` | `(0.957690, 0.010839, -0.008819, -0.959015)` |

### IC-1 canonical checkpoint spectra

| Shadow | `80 s` | `160 s` | `240 s` | `320 s` | `400 s` | `480 s` | `560 s` | `640 s` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | `(0.935608, 0.081468, -0.065019, -0.946363)` | `(1.006546, 0.045463, -0.038573, -1.013410)` | `(0.946922, 0.029663, -0.026063, -0.950384)` | `(0.970662, 0.023345, -0.020381, -0.973579)` | `(0.955365, 0.015471, -0.010640, -0.959129)` | `(0.944716, 0.010704, -0.006959, -0.948588)` | `(0.943398, 0.010807, -0.007878, -0.945466)` | `(0.956213, 0.008385, -0.006963, -0.957843)` |
| strict | `(0.794816, 0.115227, -0.096042, -0.811498)` | `(0.833777, 0.051202, -0.043404, -0.838250)` | `(0.832395, 0.037193, -0.029292, -0.839564)` | `(0.872950, 0.026270, -0.021481, -0.876297)` | `(0.877239, 0.019475, -0.017213, -0.879012)` | `(0.897845, 0.019748, -0.016269, -0.901552)` | `(0.915771, 0.014587, -0.011786, -0.918434)` | `(0.902737, 0.013914, -0.012127, -0.904732)` |
| half step | `(0.934708, 0.049511, -0.035848, -0.949429)` | `(0.923372, 0.044958, -0.039777, -0.929100)` | `(0.914794, 0.025990, -0.022445, -0.918697)` | `(0.871664, 0.026117, -0.021997, -0.875464)` | `(0.883855, 0.019664, -0.017327, -0.885464)` | `(0.885379, 0.018360, -0.015661, -0.888009)` | `(0.903038, 0.013951, -0.011593, -0.904779)` | `(0.916822, 0.011781, -0.010466, -0.917550)` |

### IC-1 settling and formulation evidence

All six individual shadows pass the `480→560`, `560→640`, and per-shadow
late-range limits:

| Formulation/shadow | `480→560` maximum | `560→640` maximum | `560–640` maximum range |
| --- | ---: | ---: | ---: |
| EL baseline | `0.022692` | `0.005272` | `0.021380` |
| EL strict | `0.011253` | `0.010972` | `0.015367` |
| EL half step | `0.023620` | `0.010269` | `0.018809` |
| canonical baseline | `0.003122` | `0.012815` | `0.018069` |
| canonical strict | `0.017926` | `0.013702` | `0.020663` |
| canonical half step | `0.017659` | `0.013783` | `0.017532` |

The ensemble criteria fail:

| Formulation | Final maximum range (`≤0.05`) | Final maximum sample SD (`≤0.025`) | Late maximum range (`≤0.07`) | Mean drift (`≤0.04`) |
| --- | ---: | ---: | ---: | ---: |
| EL | `0.088609` fail | `0.044497` fail | `0.100478` fail | `0.007833` pass |
| canonical | `0.053476` fail | `0.027718` fail | `0.055273` pass | `0.004521` pass |

The `640 s` EL mean and descriptive half-width are

$$
(0.915774,0.012085,-0.009713,-0.917725)
\pm(0.044497,0.005272,0.003233,0.043661)\ \mathrm{s^{-1}},
$$

and the canonical values are

$$
(0.925257,0.011360,-0.009852,-0.926708)
\pm(0.027718,0.002788,0.002636,0.027715)\ \mathrm{s^{-1}}.
$$

All EL reference pairs first cross distance `1` at
`32.26/32.38/32.58 s`; canonical pairs cross at
`29.27/29.27/32.40 s`. Both formulations therefore have **early
decorrelation**.

The mean displacement (`0.009483 s^-1` maximum), envelope overlap, and late-
drift difference (`0.003452 s^-1` maximum) are descriptively small, but the
combined-six range (`0.088609`) and sample SD (`0.033560 s^-1`) exceed their
limits. More importantly, the frozen comparison prerequisite fails because
both formulation ensembles are not settled. The cross-formulation verdict is
therefore **not evaluable**, not incompatible.

**IC-1 category: numerically valid but unsettled at `640 s`.**

## IC-2 result: `(0°,120°,0,0)`, `H_0=-14.715 J`

### IC-2 EL checkpoint spectra

| Shadow | `80 s` | `160 s` | `240 s` | `320 s` | `400 s` | `480 s` | `560 s` | `640 s` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | `(0.022514, 0.026690, -0.006165, -0.044698)` | `(0.010671, 0.018884, -0.000870, -0.029028)` | `(0.012794, 0.010406, -0.001453, -0.019713)` | `(0.009117, 0.007407, -0.000673, -0.016006)` | `(0.008522, 0.005266, -0.000225, -0.013534)` | `(0.006652, 0.005720, 0.000145, -0.011358)` | `(0.005759, 0.004834, -0.000223, -0.010491)` | `(0.005435, 0.004595, -0.001513, -0.008724)` |
| strict | `(0.022514, 0.026690, -0.006165, -0.044698)` | `(0.010671, 0.018884, -0.000870, -0.029028)` | `(0.012794, 0.010406, -0.001453, -0.019713)` | `(0.009117, 0.007407, -0.000673, -0.016006)` | `(0.008522, 0.005266, -0.000225, -0.013534)` | `(0.006652, 0.005720, 0.000145, -0.011358)` | `(0.005759, 0.004834, -0.000223, -0.010491)` | `(0.005435, 0.004595, -0.001513, -0.008724)` |
| half step | `(0.022514, 0.026690, -0.006165, -0.044698)` | `(0.010671, 0.018884, -0.000870, -0.029028)` | `(0.012794, 0.010406, -0.001453, -0.019713)` | `(0.009117, 0.007407, -0.000673, -0.016006)` | `(0.008522, 0.005266, -0.000225, -0.013534)` | `(0.006652, 0.005720, 0.000145, -0.011358)` | `(0.005759, 0.004834, -0.000223, -0.010491)` | `(0.005435, 0.004595, -0.001513, -0.008724)` |

### IC-2 canonical checkpoint spectra

The three canonical vectors also agree to more digits than shown here; their
full-precision differences remain in the evidence bundle.

| Shadow | `80 s` | `160 s` | `240 s` | `320 s` | `400 s` | `480 s` | `560 s` | `640 s` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | `(0.022514, 0.026690, -0.006165, -0.044698)` | `(0.010671, 0.018884, -0.000870, -0.029028)` | `(0.012794, 0.010406, -0.001453, -0.019713)` | `(0.009117, 0.007407, -0.000673, -0.016006)` | `(0.008522, 0.005266, -0.000225, -0.013534)` | `(0.006652, 0.005720, 0.000145, -0.011358)` | `(0.005759, 0.004834, -0.000223, -0.010491)` | `(0.005435, 0.004595, -0.001513, -0.008724)` |
| strict | `(0.022514, 0.026690, -0.006165, -0.044698)` | `(0.010671, 0.018884, -0.000870, -0.029028)` | `(0.012794, 0.010406, -0.001453, -0.019713)` | `(0.009117, 0.007407, -0.000673, -0.016006)` | `(0.008522, 0.005266, -0.000225, -0.013534)` | `(0.006652, 0.005720, 0.000145, -0.011358)` | `(0.005759, 0.004834, -0.000223, -0.010491)` | `(0.005435, 0.004595, -0.001513, -0.008724)` |
| half step | `(0.022514, 0.026690, -0.006165, -0.044698)` | `(0.010671, 0.018884, -0.000870, -0.029028)` | `(0.012794, 0.010406, -0.001453, -0.019713)` | `(0.009117, 0.007407, -0.000673, -0.016006)` | `(0.008522, 0.005266, -0.000225, -0.013534)` | `(0.006652, 0.005720, 0.000145, -0.011358)` | `(0.005759, 0.004834, -0.000223, -0.010491)` | `(0.005435, 0.004595, -0.001513, -0.008724)` |

### IC-2 settling and formulation evidence

| Formulation/shadow | `480→560` maximum | `560→640` maximum | `560–640` maximum range |
| --- | ---: | ---: | ---: |
| EL baseline | `0.000893` | `0.001767` | `0.003029` |
| EL strict | `0.000893` | `0.001767` | `0.003029` |
| EL half step | `0.000893` | `0.001767` | `0.003029` |
| canonical baseline | `0.000893` | `0.001767` | `0.003029` |
| canonical strict | `0.000893` | `0.001767` | `0.003029` |
| canonical half step | `0.000893` | `0.001767` | `0.003029` |

The largest EL final range, final sample SD, late-window range, and mean drift
are respectively `3.49e-10`, `1.88e-10`, `4.55e-10`, and
`0.001767 s^-1`. Canonical values are `4.50e-11`, `2.56e-11`, `2.60e-10`,
and `0.001767 s^-1`. All settling limits pass.

The `640 s` EL estimate is

$$
(0.0054345813,0.0045950056,-0.0015129348,-0.0087237409)
\pm(0.000324452,0.000239288,0.001290433,0.001766949)\ \mathrm{s^{-1}},
$$

and the canonical estimate is

$$
(0.0054345814,0.0045950056,-0.0015129347,-0.0087237410)
\pm(0.000324452,0.000239288,0.001290433,0.001766949)\ \mathrm{s^{-1}}.
$$

No reference pair reaches Candidate-A distance `1` in either formulation.
Maximum pair distances are only `1.18e-8` for EL and `6.53e-8` for canonical.
The status is therefore **independence not demonstrated**. This does not fail
validity or settling, but the three policy paths cannot be described as an
independent-shadow ensemble.

The EL/canonical rule passes every check. Maximum mean displacement is
`1.38e-10 s^-1`, maximum combined-six range `3.70e-10 s^-1`, maximum combined
sample SD `1.41e-10 s^-1`, and maximum late-drift difference
`2.16e-11 s^-1`; all descriptive envelopes overlap.

**IC-2 category: settled formulation agreement without demonstrated shadow
independence.** This is not a regular/non-chaotic classification.

## IC-3 result: `(120°,-120°,0,0)`, `H_0=+14.715 J`

### IC-3 EL checkpoint spectra

| Shadow | `80 s` | `160 s` | `240 s` | `320 s` | `400 s` | `480 s` | `560 s` | `640 s` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | `(1.112640, 0.033933, -0.027195, -1.115159)` | `(1.264114, 0.026734, -0.027130, -1.264219)` | `(1.289430, 0.021234, -0.020379, -1.289117)` | `(1.359153, 0.015794, -0.017732, -1.355480)` | `(1.346931, 0.013120, -0.012595, -1.346981)` | `(1.372349, 0.012397, -0.011110, -1.373791)` | `(1.363426, 0.009636, -0.009178, -1.363750)` | `(1.387218, 0.007514, -0.007928, -1.386391)` |
| strict | `(1.394836, 0.076654, -0.077539, -1.387036)` | `(1.445842, 0.032334, -0.033686, -1.444687)` | `(1.428954, 0.020711, -0.023127, -1.424207)` | `(1.399195, 0.017800, -0.018692, -1.396977)` | `(1.418494, 0.013553, -0.012581, -1.418837)` | `(1.417509, 0.014716, -0.014382, -1.416720)` | `(1.387871, 0.013131, -0.013565, -1.387638)` | `(1.385982, 0.008782, -0.009799, -1.385027)` |
| half step | `(1.565527, 0.027558, -0.027467, -1.564012)` | `(1.559978, 0.015964, -0.012907, -1.560992)` | `(1.516801, 0.016829, -0.014338, -1.516974)` | `(1.499052, 0.014014, -0.016052, -1.497323)` | `(1.537156, 0.009000, -0.009925, -1.535121)` | `(1.524839, 0.009809, -0.010646, -1.524252)` | `(1.514682, 0.009362, -0.010072, -1.513891)` | `(1.496606, 0.010051, -0.010323, -1.496330)` |

### IC-3 canonical checkpoint spectra

| Shadow | `80 s` | `160 s` | `240 s` | `320 s` | `400 s` | `480 s` | `560 s` | `640 s` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | `(1.438241, 0.053866, -0.053734, -1.433550)` | `(1.484106, 0.032982, -0.035233, -1.478390)` | `(1.445235, 0.025877, -0.027680, -1.443934)` | `(1.469438, 0.019411, -0.019214, -1.469884)` | `(1.440272, 0.014676, -0.014599, -1.440058)` | `(1.422515, 0.012251, -0.013270, -1.421574)` | `(1.432021, 0.011851, -0.011097, -1.432609)` | `(1.432544, 0.011386, -0.011245, -1.432254)` |
| strict | `(1.480048, 0.065594, -0.062465, -1.484738)` | `(1.363507, 0.026858, -0.029041, -1.362122)` | `(1.414515, 0.026992, -0.025858, -1.415796)` | `(1.407709, 0.017467, -0.017236, -1.406204)` | `(1.432784, 0.015342, -0.015870, -1.432175)` | `(1.434366, 0.013676, -0.012654, -1.435480)` | `(1.424769, 0.014420, -0.013815, -1.425504)` | `(1.434846, 0.011143, -0.011637, -1.434463)` |
| half step | `(1.432772, 0.049340, -0.055629, -1.423267)` | `(1.432782, 0.019371, -0.019275, -1.430500)` | `(1.432172, 0.018284, -0.014568, -1.434343)` | `(1.426290, 0.025223, -0.024640, -1.427139)` | `(1.394712, 0.018958, -0.017969, -1.395192)` | `(1.397704, 0.016880, -0.017901, -1.396493)` | `(1.364227, 0.017481, -0.017568, -1.363162)` | `(1.373277, 0.015426, -0.015374, -1.373339)` |

### IC-3 settling and formulation evidence

| Formulation/shadow | `480→560` maximum | `560→640` maximum | `560–640` maximum range |
| --- | ---: | ---: | ---: |
| EL baseline | `0.010041` | `0.023792` | `0.027474` |
| EL strict | `0.029638` | `0.004350` | `0.017983` |
| EL half step | `0.010362` | `0.018076` | `0.032477` |
| canonical baseline | `0.011035` | `0.000523` | `0.015440` |
| canonical strict | `0.009976` | `0.010077` | `0.017264` |
| canonical half step | `0.033478` | `0.010177` | `0.013148` |

All individual-shadow settling limits pass, but ensemble spread does not:

| Formulation | Final maximum range (`≤0.05`) | Final maximum sample SD (`≤0.025`) | Late maximum range (`≤0.07`) | Mean drift (`≤0.04`) |
| --- | ---: | ---: | ---: | ---: |
| EL | `0.111303` fail | `0.063871` fail | `0.151256` fail | `0.001928` pass |
| canonical | `0.061569` fail | `0.034901` fail | `0.073141` fail | `0.006550` pass |

The `640 s` EL mean and descriptive half-width are

$$
(1.423269,0.008782,-0.009350,-1.422583)
\pm(0.063515,0.004350,0.003766,0.063871)\ \mathrm{s^{-1}},
$$

and the canonical values are

$$
(1.413556,0.012652,-0.012752,-1.413352)
\pm(0.034901,0.003277,0.002279,0.034670)\ \mathrm{s^{-1}}.
$$

EL reference pairs first cross distance `1` at
`16.17/16.19/18.14 s`; canonical pairs cross at
`17.69/17.93/18.26 s`. Both formulations have **early decorrelation**.

Mean displacement (`0.009713 s^-1` maximum), envelope overlap, and late-drift
difference (`0.005437 s^-1` maximum) pass their descriptive guards. Combined-
six range (`0.123329`) and sample SD (`0.046240 s^-1`) do not. Because the
settling prerequisite fails, the cross-formulation verdict is **not
evaluable**, not incompatible.

**IC-3 category: numerically valid but unsettled at `640 s`.**

## Numerical-validity extrema

Every individual run and every QR cycle passes the frozen validity contract.
The limiting extrema by condition and formulation are:

| Condition/formulation | Energy drift | Maximum $Q$ error | Maximum physical reconstruction | Minimum $R_{ii}$ | Maximum pre-QR condition | Maximum $\kappa_2(A)$ | Minimum $\sigma_{\min}(A)$ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| IC-1 EL | `9.64e-11` | `2.39e-15` | `1.03e-15` | `0.1498` | `57.08` | — | — |
| IC-1 canonical | `9.17e-10` | `2.75e-15` | `9.18e-16` | `0.1558` | `59.71` | `43.14` | `0.08630` |
| IC-2 EL | `1.38e-11` | `2.45e-15` | `8.83e-16` | `0.3272` | `6.02` | — | — |
| IC-2 canonical | `5.88e-11` | `2.68e-15` | `1.07e-15` | `0.3272` | `6.02` | `23.05` | `0.11232` |
| IC-3 EL | `1.20e-9` | `2.35e-15` | `8.95e-16` | `0.09952` | `225.21` | — | — |
| IC-3 canonical | `3.97e-10` | `2.32e-15` | `1.11e-15` | `0.07726` | `242.33` | `63.27` | `0.07222` |

Across all runs, post-reset metric/pullback orthonormality is at most
`8.60e-15`, canonical-coordinate reconstruction at most `3.56e-15`, reset
error at most `1.16e-15`, and cumulative/rate bookkeeping error exactly zero.
These are comfortably inside the frozen limits. The unsettled verdicts are
scientific spread findings, not numerical-invalidity outcomes.

## Supporting Hamiltonian-structure diagnostics

| Condition/formulation | Spectrum sum | Outer-pair sum | Inner-pair sum | Middle magnitudes |
| --- | ---: | ---: | ---: | --- |
| IC-1 EL | `0.000421` | `-0.001951` | `0.002372` | `(0.012085,0.009713)` |
| IC-1 canonical | `0.000057` | `-0.001451` | `0.001508` | `(0.011360,0.009852)` |
| IC-2 EL | `-0.000207` | `-0.003289` | `0.003082` | `(0.004595,0.001513)` |
| IC-2 canonical | `-0.000207` | `-0.003289` | `0.003082` | `(0.004595,0.001513)` |
| IC-3 EL | `0.000118` | `0.000686` | `-0.000568` | `(0.008782,0.009350)` |
| IC-3 canonical | `0.000104` | `0.000204` | `-0.000100` | `(0.012652,0.012752)` |

These diagnostics are consistent with approximate finite-time Hamiltonian
structure but do not override the frozen settling decisions.

## Experiment-level verdict and claim boundary

**Verdict: full selected-set formulation robustness remains unresolved at
`640 s`.**

The strongest earned claim is:

> All `18` EL and canonical tangent-QR runs for the three preregistered
> zero-velocity conditions are numerically valid under the unchanged
> protocol. IC-2 supplies settled, policy-stable EL/canonical formulation
> agreement without demonstrated shadow independence. IC-1 and IC-3 supply
> early-decorrelated but still-unsettled ensembles, so the full selected-set
> cross-formulation robustness claim is not yet evaluable.

The visibly different cumulative vectors across IC-1, IC-2, and IC-3 are
allowed physical initial-condition dependence; the experiment does not test
equality between different conditions. IC-2's non-decorrelation is not a
regular/non-chaotic label, and IC-1/IC-3's positive leading components are not
a global chaos classification.

The single next scientific question suggested by this evidence is:

> Under a separately preregistered duration continuation of the unchanged
> IC-1 and IC-3 numerical shadows, do their between-shadow cumulative-spectrum
> spreads fall below the existing settling limits, or remain materially
> unresolved?

This experiment does not launch that continuation.

## Evidence and reproduction

The ignored evidence tree is:

```text
development/chaos_content/outputs/
  initial_condition_spectrum_robustness/frozen_640s/
```

It contains the accepted pre-execution gate, frozen configuration, overall
and per-condition summaries, per-formulation ensemble analyses, all per-run
checkpoint and cycle histories, pairwise reference-distance histories, and a
SHA-256 manifest covering `72` evidence files. Reproduce the frozen run with:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  development/chaos_content/experiments/lyapunov_validation/012_initial_condition_spectrum_robustness/initial_condition_spectrum_robustness.py \
  --self-check \
  --output-dir development/chaos_content/outputs/initial_condition_spectrum_robustness/frozen_640s
```

The focused tests are:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  development/chaos_content/experiments/lyapunov_validation/007_full_matrix_qr_tangent_dynamics \
  development/chaos_content/experiments/lyapunov_validation/010_independent_shadow_640s_compatibility \
  development/chaos_content/experiments/lyapunov_validation/011_hamiltonian_canonical_spectrum_crosscheck \
  development/chaos_content/experiments/lyapunov_validation/012_initial_condition_spectrum_robustness
```
