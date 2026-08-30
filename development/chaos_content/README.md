# Phase 10 Chaos Content Sandbox

This directory is the Phase 10 sandbox for new Chaos page discovery,
mathematical review, and rewritten experiments.

It is exploratory material only. Production app code must not import from this
directory, and this directory must not be used as a source of production
callbacks, layouts, assets, routes, metrics, plots, APIs, or datasets.

## Branch Boundary

Active Chaos-content development belongs on Phase 10 experimental branches only.
The current working branch is `phase10/chaos-experiments`.

Do not develop or promote material in this sandbox from unrelated feature
branches, including the parallel CSP/security development strand. This keeps
mathematical and numerical discovery isolated from production administration
work and reduces accidental coupling between the two efforts.

Future Phase 10 experiment branches may use the `phase10/...` namespace. Work
leaves this sandbox only through an explicit promotion decision after its
mathematical conventions, numerical behaviour, tests, and documentation have
been reviewed.

## Purpose

- Preserve Phase 10 discovery notes separately from the historic
  `development/chaos_branch/` work.
- Record what looked useful, stale, unsafe, or mathematically unproven in the
  historic branch.
- Provide a clean place for future rewritten chaos experiments.
- Keep all future experiments self-contained unless a read-only production
  reference is explicitly justified in the experiment notes.

## Experiment Chronology And Filesystem Addresses

Numbered directories under `experiments/` answer one question: **in what order
did we investigate these questions in this sandbox?** They do not encode the
current teaching sequence, maturity, validity, acceptance, or importance. A
larger number is a later address, not a stronger result.

The current chronology is:

| Address | Investigation | Current status |
| --- | --- | --- |
| `001_hamiltonian_poincare/` | The first executable Phase 10 experiment, retained as exploratory prior work. | Exploratory |
| `002_initial_condition_sensitivity/` | The nearby-trajectory gateway investigation and its regime-selection extension. | Accepted for a limited close-over-this-interval claim; high-excitation evidence unresolved |
| `003_lyapunov_distance_contract/` | Compare dimensionally coherent nearby-state distances before estimating growth rates. | Accepted for distance-convention findings; no exponent estimated |
| `004_finite_time_exponential_growth/` | Audit whether the controlled local divergence has a reproducible approximately exponential interval. | Completed with valid rejection: no defensible common interval under the predeclared rule |
| `005_renormalised_local_stretching/` | Test direction-preserving perturbation resets and convergence of accumulated local stretching. | Repaired iteration Outcome C: coordinate/step defects removed, but strict-tolerance and duration convergence still fail |
| `006_variational_dynamics_validation/` | Validate direct Euler–Lagrange tangent evolution against the finite-shadow local limit and repaired numerical policies. | Accepted for the limited short-time formulation claim; a long-time tangent-Lyapunov study is not included |

The living Lyapunov-strand status through Experiment 006 is maintained in
[`experiments/LYAPUNOV_STATUS.md`](experiments/LYAPUNOV_STATUS.md). The
historical finite-shadow audit remains in
[`experiments/LYAPUNOV_REVIEW.md`](experiments/LYAPUNOV_REVIEW.md).

This chronology intentionally differs from the Chaos journey below. Experiment
001 happened before that journey was formalised, so historical truth is
preserved rather than renumbered to imply a false sequence. Experiment 002 is
the accepted gateway investigation. Experiment 003 is next chronologically
because Lyapunov analysis now follows sensitivity conceptually.

### Numbered experiment directory convention

Each numbered experiment should ordinarily own a `README.md` and only the
implementation, tests, static plotting code, and experiment-local fixtures
needed to reproduce its investigation. The local README is the authoritative
working record for its question, definition, minimal experiment, numerical
validity, static inspection, acceptance, findings, and next experiment.

Use a short human-readable status such as `exploratory`, `active`, `accepted for
limited claim`, `superseded`, or `deferred`; do not infer status from the number.
Generated diagnostics belong under the ignored `outputs/` tree rather than in
experiment source directories unless a local README documents an exception.

## Chaos Journey Map

The sandbox follows a conceptual progression. Later stages depend on evidence
and conventions established by earlier stages; the existence of exploratory
code for a later stage does not imply that stage has been accepted.

The current teaching direction follows the question raised by the opening
interaction:

```text
deterministic evolution / sensitivity to initial conditions
                         ↓
how should distance between nearby trajectories be defined?
                         ↓
how quickly does that distance grow?
                         ↓
finite-time divergence
                         ↓
Lyapunov analysis
```

### 1. Sensitivity to initial conditions — the gateway

Begin with the learning question:

> How do two nearby initial states evolve, and how does the observed
> relationship depend on where the system starts?

Controlled pairs should keep their changed component and perturbation explicit,
then connect physical motion with a mathematical representation of separation.
The experience must not promise divergence. Remaining close over the visible
interval, separating gradually, separating rapidly, and developing
qualitatively different motion after an initially similar evolution are all
valid observations.

The first goal is descriptive rather than classificatory: build trustworthy
evidence of nearby-trajectory behaviour and learn which observations are useful
before attempting to assign a Lyapunov exponent or a general label of chaos.
No particular perturbation, separation threshold, duration, or binary
sensitivity label defines Stage 1.

### 2. Lyapunov analysis — formalise and quantify divergence

Build from the nearby-trajectory experiments toward a numerically defensible
notion of trajectory separation. Lyapunov analysis now follows sensitivity
directly because the opening interaction naturally asks both “what is the
distance between two trajectories?” and “at what rate does that distance
grow?” Begin with finite-time divergence and only introduce stronger Lyapunov
claims once the state-space metric, perturbation size, renormalisation,
convergence, and numerical sensitivity have been addressed.

### 3. Poincare sections — turn motion into geometry

Once nearby-trajectory behaviour and its distance conventions are understood,
sample the flow on a precisely defined section of phase space. Crossing
direction, coordinate conventions, interpolation, transient removal, solver
policy, and section residuals must all be explicit and testable.

The existing `experiments/001_hamiltonian_poincare/` work predates this journey
map. It is retained as useful exploratory prior work, not as evidence that
Stage 3 is complete. Moving it later changes development and teaching priority,
not its mathematical importance. Its assumptions and implementation should be
reviewed when this stage is reached.

### 4. Chaos maps — explore initial-state or parameter space

Only after an individual chaos diagnostic is trusted should it be evaluated
systematically across initial-condition or parameter space. Grids, ensembles,
classification maps, and expensive parameter sweeps therefore belong late in
the journey rather than at the start of discovery.

## Stage 1 Decision Record — Opening Interaction Candidate

### Decision and earned claim

The current initial-condition-sensitivity prototype is accepted as a **strong
candidate for the opening Chaos-page teaching interaction**, subject to small
mathematical and usability scaffolding and a separate production-promotion
review. This is a pedagogical acceptance decision, not production promotion or
acceptance of a general chaos diagnostic.

The interaction establishes the qualitative phenomenon needed at the opening:

- both trajectories evolve deterministically under the same equations,
  physical parameters, and numerical policy;
- their initial states are deliberately nearby and differ in one disclosed
  component;
- a very small second-angle perturbation can produce visibly different motion
  over time for the guided sensitive example; and
- a synchronized physical-separation trace accompanies the animation.

The descriptive claim is therefore that nearby deterministic beginnings can
evolve into visibly different motion, with the outcome depending on where the
system starts. The interaction does not establish exponential growth, measure
a Lyapunov exponent, or classify either a trajectory or the system as chaotic.
Its purpose is to demonstrate sensitivity and motivate a more formal question:
what should “distance between trajectories” mean?

### Minimal state and flow scaffold

The prototype uses the production simple-model Euler–Lagrange state convention,
not the Hamiltonian canonical-momentum convention:

$
\mathbf{x}(t)
=
\begin{pmatrix}
\theta_1(t) & \theta_2(t) & \omega_1(t) & \omega_2(t)
\end{pmatrix}^{\mathsf T}.
$

The production model's public initial-condition interface receives angles and
angular velocities in degrees and degrees per second, then converts them to
radians and radians per second for this solver state. The prototype exposes only
the angles and supplies zero angular velocities, so both pendulums are released
from rest:

$
\mathbf{x}_0
=
\begin{pmatrix}
\theta_{1,0} & \theta_{2,0} & 0 & 0
\end{pmatrix}^{\mathsf T},
\qquad
\mathbf{x}'_0
=
\mathbf{x}_0 + \delta\mathbf{x}_0,
$

with the disclosed nearby perturbation

$
\delta\mathbf{x}_0
=
\begin{pmatrix}
0 & \delta\theta_{2,0} & 0 & 0
\end{pmatrix}^{\mathsf T}.
$

Under the same deterministic model, parameters, and numerical policy, the two
trajectories are represented schematically by

$
\mathbf{x}(t)=\Phi^t(\mathbf{x}_0),
\qquad
\mathbf{x}'(t)=\Phi^t(\mathbf{x}'_0).
$

This notation describes the present interaction only. It does not decide which
coordinates or norm should be used for Lyapunov analysis.

### Distance contract: display versus state space

For the opening interaction, the displayed separation is the Euclidean distance
between the two second-bob Cartesian positions:

$
d_{\mathrm{bob}}(t)
=
\left\lVert
\mathbf{r}_2(t)-\mathbf{r}'_2(t)
\right\rVert_2.
$

The pair shares the same pivot, link lengths, masses, gravity, solver policy,
and every initial-state component except the explicitly perturbed second angle.
Because each second bob lies within total reach $$l_1+l_2$$ of the common pivot,

$
0 \le d_{\mathrm{bob}}(t) \le 2(l_1+l_2).
$

The current teaching configuration uses $$l_1=l_2=1\,\mathrm{m}$$, so its maximum
possible displayed separation is $$4\,\mathrm{m}$$. This bound is geometric; it
does not define a sensitivity threshold.

Two distance concepts are now part of the project contract and must remain
distinct:

1. **Display/teaching distance:** second-bob Cartesian separation
   $$d_{\mathrm{bob}}(t)$$, chosen because it is intuitive, periodic in the
   angles through the Cartesian geometry, and directly visible in the animation.
2. **State-space distance:** a metric on the full dynamical state, still to be
   formalised before finite-time divergence or Lyapunov analysis can be
   interpreted defensibly.

The display distance is not the definitive state-space norm. In particular, it
omits angular-velocity information and saturates because the physical reach is
bounded.

### Remaining pre-promotion refinement

An optional usability refinement is a decade increment control for the
perturbation magnitude. It should make scales such as
$$10^{-1}, 10^{-2}, 10^{-3}, 10^{-4}, \ldots$$ degrees easy to explore without
awkward manual decimal entry. The precise UI treatment remains open. This is
useful scaffolding, not a blocker to accepting the conceptual interaction.

### Epistemic limitation: designed-case selection

The controlled experiments remain useful verification evidence, but their
initial states, perturbed component and magnitude, tolerances, durations, and
acceptance quantities were deliberately selected by the project. Agreement
across a handful of such manually chosen cases does not make those choices an
unbiased or representative sample of the double pendulum's behaviour.

The experiment therefore cannot bootstrap its own parameter choices into a
general sensitivity claim. Broader state/parameter sampling or other robustness
work may later address this self-referential selection bias, but it is not
required merely to justify the opening descriptive prototype. The same caveat
must remain visible when finite-time divergence or Lyapunov examples are later
selected.

## Lyapunov Strand — Distance Contract Result

Experiment 003 asked:

> **What definition of distance between nearby double-pendulum states is
> mathematically appropriate for finite-time divergence and eventual Lyapunov
> analysis?**

The investigation distinguishes the current second-bob display distance from
a full state-space perturbation norm. It addressed or explicitly deferred:

- the repository's actual dynamical state
  $$(\theta_1,\theta_2,\omega_1,\omega_2)$$ for the current Euler–Lagrange
  formulation, and the implications of other formulations;
- angular periodicity and wrapped angle differences;
- position coordinates versus angular-velocity or momentum components;
- the dimensional incompatibility of unlike coordinates;
- whether nondimensionalisation or physically justified scaling is required;
- whether Cartesian, generalized-coordinate, or tangent-space representations
  are preferable;
- how finite-time numerical values depend on the selected norm;
- infinitesimal perturbations versus the finite perturbation used by the
  teaching prototype;
- saturation of bounded physical-space distances; and
- whether perturbation renormalisation is required for a defensible Lyapunov
  algorithm.

The result retains one scaled Euler–Lagrange norm and one scaled Cartesian
full-state embedding as plausible, non-unique candidates. They give strongly
correlated local growth shapes but materially different finite-time values.
The bounded second-bob distance remains a display observable only, and the raw
mixed-units EL Euclidean norm is rejected.

The next earned question is whether a reproducible approximately exponential
local interval can be defined without contamination from transients, norm
choice, or saturation. Experiment 003 does not fit that interval or estimate a
growth rate or exponent.

## Lyapunov Strand — Finite-Time Growth Result

Experiment 004 tested that earned question using Candidate A as the primary EL
distance and Candidate B as a required robustness comparison. Its locality
rule, primary `0.32–1.12 s` interval, eleven-window audit, endpoint movements,
moving-slope width, and provisional thresholds were fixed before numerical
interpretation.

The three perturbation magnitudes collapse closely through the common local
prefix, and tolerance, sampling, and energy checks pass. However, Candidate A
fails the predeclared log-linearity and residual checks, endpoint rates vary by
more than the allowed amount, and the fixed $L_c=2\ \mathrm{m}$ comparison
fails its linearity check. Candidate B shows qualitatively compatible local
growth but a materially different finite-window rate. No audit interval is
promoted in place of the failed primary interval.

The completed result is therefore a valid rejection: **no defensible common
approximately exponential interval was identified under the predeclared
rule**. A recorded finite-window rate is descriptive only and is not a
Lyapunov exponent.

Experiment 004 also preserves lifted angles and signed accumulated revolutions
as global history diagnostics. They remain separate from wrapped local angular
differences and do not enter either full-state norm, locality, interval
selection, or acceptance. In the baseline run the trajectories first differ
by one accumulated revolution only much later than the local prefix.

Because the finite approximately exponential interval was not established,
Experiment 004 did not itself earn an exponent claim. Experiment 005 was
subsequently authorised as a direct falsification test of whether repeated
local resets could overcome the rejected finite-window instability.

## Lyapunov Strand — Renormalised Local Stretching Result

Experiment 005 implements direction-preserving Candidate-A resets and retains
signed contraction in the accumulated logarithmic sum. Its original run
rejected convergence, but an independent audit found winding-dependent solver
error control, unrestricted step size, and lifted-coordinate reconstruction
loss. That historical bundle is preserved.

The repaired second iteration keeps solver-facing cycle-boundary angles in a
principal local chart, accumulates winding separately, and applies
$h_{\max}=\min(T_c/32,\tau_r/25)$ plus one half-step check. All magnitude and
interval runs now complete: the old $10^{-6}$ and `0.125 s` failures do not
survive, and the half-step rate differs by only `0.0912%`.

Status remains negative as Outcome C. The repaired `20/40/80 s` rates are
`0.756750`, `0.839863`, and `0.903459 s^-1`; the strict-tolerance result is
`0.806183 s^-1`, a failing `10.767%` difference. The finite-shadow method is
therefore still numerically unresolved, no maximal Lyapunov exponent is
accepted, and further finite-shadow tuning is not justified by this result.

## Internal Structure

- `DISCOVERY_REPORT.md` - Phase 10 discovery report for
  `development/chaos_branch/`.
- `notes/` - inventories, fidelity questions, and design/research notes.
- `experiments/` - chronologically numbered, self-contained sandbox
  investigations. No legacy code should be copied here wholesale.
- `prototypes/` - self-contained exploratory interactions used to expose UX,
  observable, and numerical questions before production promotion.
- `outputs/` - ignored, reproducible sandbox diagnostics generated by explicit
  CLI commands.
- `references/` - curated reference notes and links that may inform future
  experiments.

## Reuse Policy

Historic code from `development/chaos_branch/` may only be reused after it is
rewritten into this sandbox. Rewritten code must be self-contained inside
`development/chaos_content/` and must not depend on production app callbacks,
layouts, or assets unless the dependency is explicitly documented as read-only
reference material.

Nothing in this sandbox is production-ready unless a later Phase 10 task
promotes it deliberately with mathematical fidelity review, tests, and
production documentation.

## Experimental Method

New work begins with a precise question and minimal evidence, but discovery is
not required to move through a one-way pipeline. Numerical and interaction
work can inform each other:

```text
phenomenon
    ↓
minimal numerical evidence
    ↓
static inspection
    ↓
exploratory interaction prototype
    ↘
      observable definition ↔ numerical validation ↔ pedagogical design
              ↖_______________________________________________|
```

**Define precisely.** State the question before implementing the experiment.
Record the mathematical quantity being investigated, coordinate conventions,
initial conditions, perturbation or event rule, numerical policy, and what
would count as failure. Mark choices as established, provisional, or unresolved
rather than allowing an early test configuration to become a general contract.

**Run minimally.** Start with the smallest experiment capable of answering the
question: one model, one or two named initial conditions, and an integration
short enough to inspect. Do not begin with grids, ensembles, long sweeps, or
performance optimisation.

**Verify numerically.** Solver success alone is not acceptance. Check relevant
invariants, finite values, residuals, event/interpolation accuracy, and
sensitivity to tolerances or resolution where the experiment requires it.
Failed numerical criteria should reject an individual run under its declared
policy rather than merely annotate it. That does not automatically make the
initial condition pedagogically useless or settle whether a teaching observable
is robust under a better policy.

**Inspect statically.** Matplotlib diagnostics are the baseline for exposing
correctness, failure, structure, and numerical artefacts. A visually interesting
result is not evidence of its own validity.

**Prototype interactions deliberately.** A self-contained sandbox interaction
prototype may follow minimal numerical evidence before every mathematical or
pedagogical convention is final. Its purpose must be to explore interaction
design, expose assumptions, generate better questions, or discover which
observables help a learner. It is not an accepted numerical model, production
feature, or substitute for static and machine-readable evidence.

**Increase complexity for a reason.** Longer integrations, additional initial
conditions, different energy regimes, ensembles, and parameter sweeps require a
question justified by earlier evidence or prototype feedback. More complexity
does not confer more validity.

> Complexity must answer an evidence-backed or explicitly exploratory question;
> neither makes it production-ready.

## Experiment Contract

Each experiment should record, either in a local README or an equivalent small
experiment note:

- **Question** — what are we trying to establish?
- **Definition** — what mathematical quantity or event is being measured?
- **Minimal experiment** — what is the smallest run that can answer it?
- **Numerical validity** — how could the result be wrong, and how will that be
  detected?
- **Convention status** — which choices are established, provisional, or
  unresolved?
- **Static inspection** — which figures expose the result and its failure
  modes?
- **Observable robustness** — does the intended conclusion survive an
  appropriate numerical comparison even if pointwise trajectories eventually
  differ?
- **Prototype purpose** — when interaction is involved, what assumption or
  learning question is it intended to test?
- **Acceptance** — what evidence supports a particular claim or permits
  production promotion?
- **Findings** — what was actually observed?
- **Next experiment** — what additional complexity has now been justified?

These questions must keep four judgements distinct:

- whether an individual integration is numerically valid under its declared
  policy;
- whether a nominal trajectory is pointwise resolved over a stated interval;
- whether the observable used for a teaching claim is robust;
- whether an interaction is useful for learning or for discovering the next
  experimental question.

An exploratory prototype can be useful while one or more mathematical choices
remain unresolved. Production promotion is still a separate, later activity:

```text
reviewed mathematical and numerical contract
                  +
reviewed pedagogical evidence and production architecture
                  ↓
          explicit promotion decision
                  ↓
         production teaching surface
```

Nothing should move into production merely because an experiment or sandbox
prototype is useful or visually compelling. Production code must not import
from this sandbox.

## Executable Sandbox Artifacts

- `prototypes/initial_condition_sensitivity/` is the exploratory Dash teaching
  surface derived from Experiment 002. It remains separate from the numbered
  mathematical experiment to avoid coupling prototype UI assets to the
  experiment source. The interaction compares one nearby pair that stays close
  with one that separates, then lets the learner choose an initial state,
  disclose one small nearby change, and compare synchronized motion in
  superimposed or side-by-side views. Launch it from the repository root with:

  ```bash
  uv run python development/chaos_content/prototypes/initial_condition_sensitivity/app.py
  ```

  It is a sandbox UX/numerical-observable probe, not an accepted production
  teaching surface or chaos classifier. Its local README owns the provisional
  controls, numerical policy, limitations, and run instructions.

  Prototype use also raises a later map question: **What structure appears when
  sensitivity is measured across the `(theta1, theta2)` initial-angle plane?**
  That remains a Stage 4 direction rather than the immediate next task. It is
  not a prescribed sweep or an accepted claim that any observed boundary is
  fractal; its observable, classification, resolution, colour mapping, and
  numerical validation policy all remain unresolved.

- `experiments/002_initial_condition_sensitivity/` investigates how nearby
  simple-model trajectories evolve from different regions of initial-state
  space. Its current `theta2 += 0.001 deg`, 20-second, and `d_tip = 0.1`
  conventions are experimental scaffolding, not universal definitions of
  sensitivity. The original fixed pair remains a numerically accepted
  close-over-this-interval observation. A predeclared six-regime comparison is
  **provisionally useful (Outcome C)**: two high-excitation pairs cross the
  provisional threshold under both recorded policies, but their production-
  principal runs fail the energy bound and the observable has not yet been
  validated across a suitable tolerance hierarchy. Reproduce the comparison
  with:

  ```bash
  uv run python development/chaos_content/experiments/002_initial_condition_sensitivity/regime_selection_comparison.py --output-dir development/chaos_content/outputs/initial_condition_sensitivity/regime_selection --plots
  ```

  No high-excitation case has yet passed the recorded experiment contract, and
  this does not establish that 20 seconds is generally adequate or inadequate.
  Observable-focused numerical validation of those cases remains unresolved,
  but the next mathematical strand is to define an appropriate state-space
  distance rather than lengthen a run or make a chaos claim. The experiment-
  local README owns the detailed conventions, results, methodology
  reassessment, and limitations.

- `experiments/003_lyapunov_distance_contract/` compares a scaled
  Euler–Lagrange full-state norm, a scaled Cartesian full-state embedding, and
  the bounded second-bob display observable for one controlled nearby pair.
  Both full-state candidates remain plausible despite material finite-time
  differences; perturbation, tolerance, sampling, and scaling checks are
  recorded without fitting a growth rate or exponent. Reproduce its ignored
  evidence bundle with:

  ```bash
  uv run python development/chaos_content/experiments/003_lyapunov_distance_contract/lyapunov_distance_investigation.py --output-dir development/chaos_content/outputs/lyapunov_distance_contract/baseline --plots
  ```

  The experiment-local README owns the accepted, rejected, and unresolved
  conventions and the self-selection limitation.

- `experiments/004_finite_time_exponential_growth/` audits a predeclared
  finite growth interval without selecting a visually straight segment. It
  records perturbation collapse, Candidate A/B and scaling dependence, moving
  slopes, endpoint sensitivity, numerical validity, and separate winding-
  history diagnostics. The result is a valid rejection, not an exponent.
  Reproduce its ignored evidence bundle with:

  ```bash
  uv run python development/chaos_content/experiments/004_finite_time_exponential_growth/finite_time_exponential_growth.py --self-check --output-dir development/chaos_content/outputs/finite_time_exponential_growth/baseline --plots
  ```

  The experiment-local README owns the predeclared inference contract, exact
  findings, rejected stronger claims, and unresolved choices.

- `experiments/005_renormalised_local_stretching/` is the first repeated-reset
  investigation. It preserves the evolved Candidate-A direction, records every
  signed cycle contribution, and now keeps local solver coordinates separate
  from reference winding history under an explicit max-step policy. The
  repaired result is Outcome C, not a Lyapunov exponent. Reproduce the repaired
  ignored evidence with:

  ```bash
  uv run python development/chaos_content/experiments/005_renormalised_local_stretching/renormalised_local_stretching.py --max-duration 80 --self-check --output-dir development/chaos_content/outputs/renormalised_local_stretching/repaired --plots
  ```

  The experiment-local README preserves the original rejection, independent
  audit, repaired evidence, explicit robustness rejections, and claim boundary.

- `experiments/001_hamiltonian_poincare/` contains the first minimal executable
  Phase 10 experiment: a self-contained simple-Hamiltonian Poincare-section
  workflow with explicit state, section, interpolation, solver, and
  energy-drift policies.

This experiment is currently treated as exploratory prior work for Stage 3 of
the journey map. Keep it runnable and inspectable, but do not let its existence
skip the Stage 1 sensitivity work or imply that its mathematical and numerical
policies have already passed final acceptance.

Run it from the repository root:

```bash
python development/chaos_content/experiments/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py
```

Write a local diagnostic bundle:

```bash
python development/chaos_content/experiments/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py --output-dir development/chaos_content/outputs/smoke_run --plots
```

Write a longer diagnostic bundle with more section points:

```bash
python development/chaos_content/experiments/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py --t-stop 300 --sample-count 12001 --discard-before 30 --min-crossings-for-plot 100 --output-dir development/chaos_content/outputs/long_run --plots
```

Generated output bundles are ignored by git and are not production assets.
