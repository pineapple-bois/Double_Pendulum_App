# Canonical Model Source Inventory

## Purpose and evidence labels

This inventory began by answering a narrow preparatory question: which
repository assets can support an independent canonical Hamiltonian cross-check
of Experiment 010? It now also records which claims Phase A independently
verified before any spectrum run.

The labels used below are epistemic:

1. **Accepted production/model convention** — current code and focused tests
   define or check the convention used by the application models.
2. **Exploratory convention** — executable sandbox material that may inform a
   fresh implementation but is not accepted merely because it runs.
3. **Requires independent verification** — a formula, derivative, coordinate
   map, or numerical policy that Experiment 011 must earn before using it for
   a spectrum comparison.
4. **Independently verified in Phase A** — checked by the predeclared
   Experiment 011 algebraic, finite-difference, or synchronized-flow tests.

No historic implementation is promoted by this document.

## Source map

| Asset | Exact source location | Current standing |
| --- | --- | --- |
| Canonical state names and solver-state label | `src/double_pendulum/models/initial_conditions.py:6-11` | Accepted production/model convention |
| Numerical velocity-to-momentum map and canonical initial state | `src/double_pendulum/models/initial_conditions.py:18-62` | Accepted production/model convention, with focused tests at `tests/numerical/test_initial_condition_conventions.py:87-106` |
| Simple-model Lagrangian | `src/double_pendulum/math/functions.py:41-105` | Production symbolic asset; expected form checked at `tests/unit/test_derivation_fidelity.py:19-33` |
| Symbolic canonical momenta | `src/double_pendulum/math/functions.py:403-419` | Production symbolic asset |
| Simple Hamiltonian | `src/double_pendulum/math/functions.py:422-447` | Production symbolic asset; exact form checked at `tests/unit/test_derivation_fidelity.py:36-52` |
| Hamilton equations | `src/double_pendulum/math/functions.py:450-489` | Production symbolic asset |
| Hamiltonian solver wrapper and state use | `src/double_pendulum/models/hamiltonian.py:25-33`, `36-44`, `59-120` | Accepted production/model convention |
| Production solver dispatch | `src/double_pendulum/models/hamiltonian.py:122-157` | Accepted production integration interface |
| Named simple-model solver policies | `src/double_pendulum/models/solver_policy.py:4-39`, `50-56` | Accepted production numerical convention |
| Short EL/Hamiltonian trajectory agreement | `tests/numerical/test_simple_formulation_agreement.py:46-100` | Accepted short regression evidence only |
| Hamiltonian energy reconstruction smoke test | `tests/numerical/test_energy_smoke.py:18-68`, `116-129` | Accepted test convention; not a production energy API |
| Self-contained Hamiltonian/Poincaré formulas | `development/chaos_content/experiments/foundations/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py:127-242` | Exploratory convention requiring independent verification |
| Poincaré solver convention | `development/chaos_content/experiments/foundations/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py:320-352` | Exploratory only |
| Poincaré experiment's own limitation statement | `development/chaos_content/experiments/foundations/001_hamiltonian_poincare/README.md:111-123` | Explicitly un-cross-validated prior work |
| Accepted EL target parameters and local chart constants | `development/chaos_content/experiments/foundations/006_variational_dynamics_validation/variational_dynamics_validation.py:47-63` | Existing accepted Lyapunov-strand fixture retained through Experiment 010 |
| Accepted EL spectrum target and uncertainty | `development/chaos_content/experiments/lyapunov_validation/010_independent_shadow_640s_compatibility/README.md`, “Ensemble estimate and uncertainty” | Accepted only within Experiment 010's declared ensemble |
| Experiment-local canonical state/tangent maps | `development/chaos_content/experiments/lyapunov_validation/011_hamiltonian_canonical_spectrum_crosscheck/canonical_spectrum_crosscheck.py`, `el_to_canonical`, `canonical_to_el`, `forward_tangent_map`, `inverse_tangent_map` | Independently verified in Phase A; not production code |
| Experiment-local canonical flow and Jacobian | same file, `CanonicalDynamics` | Derived from production $H$, independently checked in Phase A; not production code |
| Phase A evidence | ignored `development/chaos_content/outputs/hamiltonian_canonical_phase_a/baseline/{summary.json,jacobian_validation.json,manifest.json}` | Reproducible Experiment 011 evidence; no QR or spectrum |

## Accepted production/model conventions

### Canonical state

The production Hamiltonian solver state is

$$
z=(\theta_1,\theta_2,p_{\theta_1},p_{\theta_2}),
$$

in exactly that order. The constants are
`HAMILTONIAN_STATE_VARIABLE_NAMES` and
`HAMILTONIAN_SOLVER_STATE_CONVENTION = "angles_and_canonical_momenta"` at
`src/double_pendulum/models/initial_conditions.py:8-11`. Public initial
conditions remain ordered as
$(\theta_1,\theta_2,\omega_1,\omega_2)$ and are converted before the
Hamiltonian solver is called (`src/double_pendulum/models/hamiltonian.py:36-44`,
`74-89`).

Angles are radians inside solver states. Production user inputs are converted
componentwise from degrees/degrees per second to radians/radians per second at
`src/double_pendulum/models/initial_conditions.py:14-15`.

### Simple inertia matrix and canonical momenta

Let $q=(\theta_1,\theta_2)$, $\omega=\dot q$, and
$\Delta=\theta_1-\theta_2$. Production's simple-model conversion implements

$$
B(q)=
\begin{pmatrix}
(m_1+m_2)l_1^2 & m_2l_1l_2\cos\Delta\\
m_2l_1l_2\cos\Delta & m_2l_2^2
\end{pmatrix},
$$

$$
p=B(q)\omega,
$$

or explicitly

$$
p_{\theta_1}=(m_1+m_2)l_1^2\omega_1
+m_2l_1l_2\cos\Delta\,\omega_2,
$$

$$
p_{\theta_2}=m_2l_1l_2\cos\Delta\,\omega_1
+m_2l_2^2\omega_2.
$$

The numerical implementation is
`angular_velocities_to_canonical_momenta` at
`src/double_pendulum/models/initial_conditions.py:18-46`; its use in the
four-component initial solver state is at lines `49-62`. The same momentum
definition follows symbolically from $p_i=\partial L/\partial\omega_i$ in
`src/double_pendulum/math/functions.py:403-419`.

The inverse state map is mathematically

$$
\omega=B(q)^{-1}p.
$$

Production uses the equivalent derivatives $\partial H/\partial p$ in its
Hamilton equations. There is no named production `canonical_to_el` helper.
The matrix-solve implementation at
`development/chaos_content/experiments/foundations/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py:185-193`
and the test helper at `tests/numerical/test_energy_smoke.py:18-38` are useful
references, but Experiment 011 must validate its own inverse conversion.

### Hamiltonian

Production constructs

$$
H(q,p)=\frac12 p^{\mathsf T}B(q)^{-1}p+V(q),
$$

with unshifted potential

$$
V(q)=-(m_1+m_2)gl_1\cos\theta_1-m_2gl_2\cos\theta_2.
$$

The explicit simple-model expression checked by
`tests/unit/test_derivation_fidelity.py:36-52` is

$$
H=
\frac{
m_2l_2^2p_{\theta_1}^2
-2m_2l_1l_2\cos\Delta\,p_{\theta_1}p_{\theta_2}
+(m_1+m_2)l_1^2p_{\theta_2}^2
}{
2m_2l_1^2l_2^2\left(m_1+m_2\sin^2\Delta\right)
}
-(m_1+m_2)gl_1\cos\theta_1-m_2gl_2\cos\theta_2.
$$

The source expression is `compute_hamiltonian("simple")` at
`src/double_pendulum/math/functions.py:422-447`.

### Canonical equations

Production applies Hamilton's equations

$$
\dot q=\frac{\partial H}{\partial p},
\qquad
\dot p=-\frac{\partial H}{\partial q},
$$

at `src/double_pendulum/math/functions.py:450-472`, and exposes the four
right-hand sides in canonical state order through
`hamiltonian_system`/`hamiltonian_first_order_system` at
`src/double_pendulum/math/functions.py:475-489` and
`src/double_pendulum/models/hamiltonian.py:25-33`. The production model
substitutes parameters, lambdifies those expressions, and dispatches them in
state order at `src/double_pendulum/models/hamiltonian.py:92-120`.

This derivative path is repository-supported. Experiment 011 still has to
validate the resulting numerical RHS independently against EL flow after
coordinate conversion; the existing trajectory comparison covers only short
fixtures (`tests/numerical/test_simple_formulation_agreement.py:46-100`).

### Parameters inherited by the Lyapunov strand

The retained simple-system fixture is

$$
m_1=m_2=1\ \mathrm{kg},\qquad
l_1=l_2=1\ \mathrm{m},\qquad
g=9.81\ \mathrm{m\,s^{-2}},
$$

with EL initial state

$$
(179^\circ,179^\circ,0,0).
$$

The values are defined at
`development/chaos_content/experiments/foundations/006_variational_dynamics_validation/variational_dynamics_validation.py:47-49`
and retained by Experiment 010. Because the angular velocities are zero, the
corresponding initial canonical momenta are both zero under the accepted map.
This special simplification must not replace validation of the nonzero-
velocity conversion along the trajectory.

### Energy evaluation

Production owns the symbolic Hamiltonian but does not expose a standalone
numeric Hamiltonian-energy method on `DoublePendulumHamiltonian`. Current
numeric conventions are split between:

- the test-only reconstruction of $\omega=B^{-1}p$ followed by $T+V$ at
  `tests/numerical/test_energy_smoke.py:18-68`; and
- the exploratory direct evaluation
  $\tfrac12p^{\mathsf T}B^{-1}p+V$ at
  `development/chaos_content/experiments/foundations/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py:171-182`.

Phase A supplies an experiment-local numeric evaluator derived from the
production symbolic $H$ and checks it independently against both the EL
mechanical energy and direct matrix evaluation. This does not create a new
production energy API.

### Solver conventions

Production uses `solve_ivp` with explicit sample times. The named simple
policies are DOP853 with `rtol=1e-6`, `atol=1e-8` (default) and DOP853 with
`rtol=1e-9`, `atol=1e-11` (reference) at
`src/double_pendulum/models/solver_policy.py:25-39`. Extra integrator arguments
override policy values through `merge_solver_policy_kwargs` at lines `50-56`.

Experiment 010's accepted ensemble instead uses its declared baseline
`1e-9/1e-11`, strict `1e-11/1e-13`, explicit baseline/half step caps, and
`0.25 s` QR cadence. Those are experiment policy, not production defaults.

## Exploratory Hamiltonian/Poincaré conventions

Experiment 001 independently writes down:

- the same canonical order and $B(q)$ (`minimal_hamiltonian_poincare.py:127-168`);
- the same matrix-form Hamiltonian and inverse velocity map (lines `171-193`);
- an explicit analytical numerical RHS (lines `196-230`);
- the same unit parameters as defaults (lines `33-41`); and
- strict DOP853 tolerances `1e-11/1e-13`, explicit `t_eval`, event root finding,
  and no explicit `max_step` (lines `44-54`, `320-352`).

Its physical initial condition is `(120°, -10°, 0, 0)`, not Experiment 010's
reference (`minimal_hamiltonian_poincare.py:57-64`). Its energy normalization
is $|H-H_0|/\max(|H_0|,1)$ (lines `239-242`), which differs from the
Lyapunov strand's fixed physical energy scale.

For later independent comparison, the explicit exploratory RHS at lines
`196-230` writes $\dot q=B^{-1}p$ and, with

$$
D=m_1+m_2\sin^2\Delta,
$$

$$
N=m_2l_2^2p_{\theta_1}^2
-2m_2l_1l_2\cos\Delta\,p_{\theta_1}p_{\theta_2}
+(m_1+m_2)l_1^2p_{\theta_2}^2,
$$

$$
N'=2m_2l_1l_2\sin\Delta\,p_{\theta_1}p_{\theta_2},
\qquad
D'=2m_2\sin\Delta\cos\Delta,
$$

uses

$$
K_\Delta=
\frac{N'D-ND'}{2m_2l_1^2l_2^2D^2}
$$

to compute

$$
\dot p_{\theta_1}
=-K_\Delta-(m_1+m_2)gl_1\sin\theta_1,
$$

$$
\dot p_{\theta_2}
=K_\Delta-m_2gl_2\sin\theta_2.
$$

These expressions appear consistent with differentiating the recorded
Hamiltonian, but that is a mathematical observation, not accepted Experiment
011 evidence. A later task should compare them symbolically and numerically
with the production-derived RHS rather than adopt them verbatim.

Most importantly, the Experiment 001 README says the formulation has not been
cross-validated against a separate symbolic derivation or reference trajectory
and has not received solver-equivalence or tolerance study
(`development/chaos_content/experiments/foundations/001_hamiltonian_poincare/README.md:111-123`). Its explicit RHS is therefore a
valuable independent comparison candidate, not code to copy as accepted truth.

## Existing derivatives, Jacobians, and Hessians

Repository search finds no implemented canonical flow Jacobian or Hamiltonian
Hessian in production or Experiment 001. Production differentiates $H$ once
to form Hamilton's equations; it does not form

$$
J_H(z)=\frac{\partial f_H}{\partial z}
$$

or $\nabla^2H$. Experiment 006's validated Jacobian is for the EL state and
must not be relabelled as a canonical Jacobian.

Phase A resolves this experiment-local gap without changing production. It
constructs independent canonical symbols, substitutes the accepted parameters
into production's $H$, forms $f_H=J_s\nabla H$, and differentiates that flow to
obtain $D f_H=J_s\nabla^2H$ in `CanonicalDynamics`. The construction does not
transform Experiment 006's EL Jacobian. Directional finite differences and the
Hamiltonian-matrix identity independently validate the result over the fixed
test set.

## Scaffold-era validation requirements

The scaffold listed the following mathematically motivated requirements. Phase
A has now satisfied all five over its declared representative states and
`0–1.29 s` interval; they are not claims about long-time QR.

1. **Full state equivalence.** Validate both directions
   $(q,\omega)\leftrightarrow(q,p)$ at representative nonzero velocities and
   at independent positive/negative $2\pi$ angle shifts.
2. **Tangent-coordinate equivalence.** Differentiating $p=B(q)\omega$ suggests

   $$
   \delta p=B(q)\,\delta\omega
   +\left[\mathrm{D}B(q)[\delta q]\right]\omega.
   $$

   This state-dependent tangent map is not implemented or tested in the
   repository and must be verified independently.
3. **Reference-flow equivalence.** Compare short, synchronized EL and
   canonical references after state conversion before chaotic shadow
   decorrelation makes pointwise comparison meaningless.
4. **Canonical tangent operator.** Validate every implemented Jacobian through
   independent directional finite differences and $2\pi$ periodicity tests.
5. **Hamiltonian structural identity.** Symplectic/Hamiltonian identities may
   be useful checks, but are not substitutes for RHS/Jacobian validation.

## Scaffold-era choices affecting the future comparison

- **Canonical QR geometry.** Raw Euclidean QR in
  $(\theta_1,\theta_2,p_{\theta_1},p_{\theta_2})$ mixes units. A future contract
  must choose and justify either a dimensionally scaled canonical metric or
  the state-dependent pullback of Candidate A through the tangent coordinate
  map. Candidate A cannot simply be copied onto momentum components.
- **Tangent-basis correspondence.** Decide whether the initial canonical basis
  is the differential image of Experiment 010's EL basis or an independently
  scaled canonical basis, and define what comparison each choice supports.
- **Finite-time comparison rule.** Asymptotic exponents should be invariant
  under a regular bounded coordinate change, while finite-time QR columns and
  estimates can differ. The later acceptance rule must distinguish coordinate
  transients from disagreement beyond Experiment 010's descriptive envelope.
- **Reference ensemble.** Decide whether to mirror all three Experiment 010
  policies, first validate a common EL/canonical reference, or stage those
  tests sequentially. No choice is made here.
- **Angle chart handling.** Establish canonical angle rebasing and verify that
  $p$, $H$, the RHS, and the Jacobian are invariant under independent integer
  $2\pi$ shifts. Do not let lifted winding enter solver error control.
- **Energy diagnostic.** Choose a common normalization and derive a numeric
  canonical energy evaluator from the accepted symbolic source.
- **Solver protocol.** Retain or explicitly justify Experiment 010's
  tolerances, step caps, cycle boundaries, and restart semantics. Experiment
  001's unrestricted-step event run is not a substitute.
- **Derivative construction.** Analytic/symbolic Hessian, automatic
  differentiation, or a controlled numerical Jacobian remain open until one
  is selected and independently validated.

## Potential blockers

No repository evidence blocks an independent canonical formulation in
principle: the state, Legendre map, Hamiltonian, and Hamilton equations exist.
The material gaps are validation work, not missing physical definitions.

The scaffold identified the absent canonical Jacobian/Hessian and canonical QR
metric as its highest-risk gaps. Phase A resolves the first and recommends a
controlled metric contract for testing, but it does not validate QR. A
long-time canonical spectrum run therefore remains premature.

## Phase A independently verified results

### State and energy

The production state order, inertia matrix, forward Legendre map, Hamiltonian,
parameters, and Hamilton-equation order in the earlier inventory were
confirmed; no scaffold formula required correction. The experiment-local
inverse map is $\omega=B(q)^{-1}p$. State round trips and tangent-map inverse
products have maximum absolute error `4.44e-16`; directional finite
differences of the forward state map have maximum relative error `4.46e-10`.
The production forward momentum helper agrees exactly at all four
representative states.

The canonical initial state for the established physical case is
$(179^\circ,179^\circ,0,0)$, with its angular entries converted to radians.
Canonical $H$, EL mechanical energy, and direct
$\tfrac12p^{\mathsf T}B^{-1}p+V$ agree within `1.21e-16` after normalization.

### Flow, periodicity, and tangent operator

Independent integer $2\pi$ shifts change canonical energy, flow, and Jacobian
by at most `4.11e-14`. At the refined solver policy, the synchronized
canonical reference converted to EL coordinates stays within `6.04e-15` in
Candidate-A distance of the EL reference; the baseline maximum is `2.76e-14`.
The two canonical policies differ by at most `8.55e-14`. Maximum normalized
energy drift is `1.45e-15`.

Across four fixed states and three fixed trajectory samples, three directions
per state, the maximum central-difference Jacobian error at $h=10^{-6}$ is
`1.01e-9` relative. The maximum
$\lVert Df_H^{\mathsf T}J_s+J_sDf_H\rVert_\infty$ residual is numerically zero.
The full $h=10^{-2}\ldots10^{-8}$ records expose the expected truncation-to-
roundoff transition in `jacobian_validation.json`.

For the refined pure-$\theta_2$ tangent, the canonical vector mapped back to
EL coordinates agrees with direct EL tangent evolution to `1.42e-14` in
relative Candidate-A norm and log growth, `2.84e-14` in scaled direction
components, with minimum signed cosine `0.9999999999999996`.

### Chosen future QR convention

**Chosen experimental convention:** for the primary formulation comparison,
pull Candidate A back through $\Phi:z\mapsto x$:

$$
G_z(z)=C(z)^{\mathsf T}S^{\mathsf T}S C(z),
\qquad C(z)=\mathrm{D}\Phi(z),
$$

using factor $A(z)=SC(z)$. A future reset would evaluate
$A(z_k)Y_k^-=Q_kR_k$ and set $Y_k^+=A(z_k)^{-1}Q_k$. This removes a metric
change as a confound while retaining an independently Hamiltonian-derived
flow and tangent operator. The tested factor has maximum condition number
`12.40`, minimum absolute determinant `0.05097`, and reconstruction error
`4.44e-16` over Phase A.

**Remaining convention:** a fixed dimensionless canonical scaling is also
mathematically defensible and should yield the same asymptotic exponents when
the coordinate/norm change stays regular and bounded, but finite-time QR
columns and estimates are metric-dependent. It is not the primary comparison
because its characteristic momentum scales are conventional. No metric has
been chosen to imitate the Experiment 010 numbers.

### Current blocker and next gate

At the Phase A boundary, no ambiguity or inconsistency blocked the canonical
state transformation, reference flow, or tangent primitive. The remaining gate
was a tested full-matrix canonical QR primitive in the pullback geometry.
Phase B now resolves that gate as recorded below. Neither phase supplies a
long-time Hamiltonian spectrum.

## Phase B pullback-QR result

### State-dependent metric bookkeeping

**Independently verified in Phase B:** at each QR event, evaluating

$$
A(z_k)=S\,\mathrm{D}\Phi(z_k)
$$

at the current canonical reference and applying

$$
A(z_k)Y_{H,k}^-=Q_kR_k,
\qquad
Y_{H,k}^+=A(z_k)^{-1}Q_k
$$

simultaneously enforces

$$
(Y_{H,k}^+)^{\mathsf T}A(z_k)^{\mathsf T}A(z_k)Y_{H,k}^+=I,
$$

$$
A(z_k)Y_{H,k}^-=Q_kR_k,
\qquad
Y_{H,k}^-=Y_{H,k}^+R_k.
$$

Mapping the last identity with $C(z_k)=\mathrm{D}\Phi(z_k)$ also reconstructs
the same pre-reset matrix in physical EL tangent coordinates. The state
dependence is therefore explicit in both factorization and reset; Experiment
007's constant-$S$ reset is not silently reused for canonical coordinates.

Over the fixed five-cycle Phase B run, the largest pullback-factor condition
number is `12.1003`, its minimum singular value is `0.121953`, and the largest
pre-QR scaled-basis condition number is `26.6229`. Maximum $Q$ orthonormality,
scaled reconstruction, canonical reconstruction, physical reconstruction,
pullback orthonormality, and reset-identity errors range from `3.54e-16` to
`4.61e-15`. All are below the predeclared `1e-12` limits.

### Coordinate-equivalent QR factors

**Independently verified in Phase B:** initialize

$$
Y_{\mathrm{EL},0}=S^{-1},
\qquad
Y_{H,0}=A(z_0)^{-1}.
$$

Then $Y_{\mathrm{EL}}=C(z)Y_H$ and
$SY_{\mathrm{EL}}=A(z)Y_H$ remain numerically consistent through every
synchronized QR event over `0–1.25 s`. With a positive-$R_{ii}$ convention and
no column sorting, the baseline and refined EL/canonical calculations agree in
pre-QR scaled matrices, $Q$, $R_{ii}$, cycle logs, cumulative logs, and final
diagnostic vectors. The largest refined per-cycle log difference is
`1.85e-13`; the largest refined cumulative-log difference is `2.42e-13`; the
final diagnostic-vector difference is `1.50e-13 s^-1`.

This agreement is a coordinate-equivalence result under the shared pullback
metric, not independent long-time spectrum evidence. It shows that the chosen
metric removes finite-time coordinate geometry as a confound for the declared
comparison. A fixed dimensionless canonical metric remains a different,
conventional sensitivity question and was not substituted into Phase B.

### Remaining gate

The canonical state, flow, Jacobian, full tangent matrix, and pullback-QR
primitive are now locally validated. The remaining scientific question is
long-time statistical compatibility across independently integrated canonical
shadows and comparison with the accepted Experiment 010 EL ensemble. No such
integration or Hamiltonian spectrum is present in Experiment 011 Phases A–B.

## Phase C long-time pullback-metric evidence

**Independently verified in Phase C:** the same state-dependent factor

$$
A(z)=S\,\mathrm{D}\Phi(z)
$$

remains finite and nonsingular across three independently integrated
`640 s` canonical reference histories and `7680` aggregate QR events. The
largest observed $\kappa_2(A)$ is `81.1977`, the minimum singular value is
`0.0633315`, and the largest pre-QR scaled-basis condition number is `687.475`.
The maximum post-reset pullback-orthonormality error is `1.29e-14`; the maximum
canonical and mapped-physical reconstruction errors are `4.17e-15` and
`1.07e-15` respectively. Thus no long-time singularity or conditioning failure
of the accepted pullback metric is observed under this specific physical
initial condition and numerical protocol.

This is a reusable numerical fact about the tested pullback construction, not
a proof that $A(z)$ is globally well-conditioned throughout canonical state
space. Phase C's spectrum and formulation-compatibility conclusions remain in
the Experiment 011 README rather than this mathematical inventory.
