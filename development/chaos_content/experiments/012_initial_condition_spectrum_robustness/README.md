# 012 Initial-Condition Spectrum Robustness

**Status: scaffolded and not executed. No additional physical initial
conditions or numerical acceptance thresholds have been selected.**

## Question

> Across a small, predeclared set of additional physical initial conditions,
> does independent Euler–Lagrange/canonical long-time spectrum agreement
> persist without retuning the accepted numerical protocol?

[Experiment 010](../010_independent_shadow_640s_compatibility/README.md)
accepted a three-shadow Euler–Lagrange cumulative QR estimate at `640 s` for

$$
x_\mathrm{ref}=(179^\circ,179^\circ,0,0),
$$

and [Experiment 011](../011_hamiltonian_canonical_spectrum_crosscheck/README.md)
independently accepted internal canonical-shadow compatibility and descriptive
EL/canonical ensemble compatibility for that same physical state. This
establishes formulation independence only for one declared trajectory. It
does not show that either formulation's accepted protocol or resulting
spectrum generalises across physical initial conditions. The current claim
boundary is summarized in [`LYAPUNOV_STATUS.md`](../LYAPUNOV_STATUS.md).

Experiment 012 is intended to test that next boundary. This scaffold only
separates inherited commitments from unresolved design choices. It contains no
runner, selected case list, spectrum output, or acceptance result.

## Fixed inherited protocol

The following items are the starting contract supported by Experiments
010–011. A later design audit may identify a genuine global reason to revise
one, but none may be changed case-by-case after viewing an initial condition's
outcome.

### Physical model and formulations

- Simple double pendulum with

  $$
  m_1=m_2=1\ \mathrm{kg},\qquad
  l_1=l_2=1\ \mathrm{m},\qquad
  g=9.81\ \mathrm{m\,s^{-2}}.
  $$

- Euler–Lagrange state and independently validated tangent flow

  $$
  x=(\theta_1,\theta_2,\omega_1,\omega_2),
  \qquad
  \dot Y_\mathrm{EL}=J_\mathrm{EL}(x)Y_\mathrm{EL}.
  $$

- Canonical state, Hamiltonian reference flow, and independently derived
  tangent flow

  $$
  z=(q_1,q_2,p_1,p_2),
  \qquad
  \dot Y_H=Df_H(z)Y_H.
  $$

- The accepted EL↔canonical physical state and tangent maps from Experiment
  011. Long-time EL and canonical trajectories are independently integrated
  numerical shadows. For a chaotic case, they are not required to correspond
  pointwise after decorrelation.

### Tangent geometry and QR bookkeeping

Candidate A remains the shared comparison geometry:

$$
S=\operatorname{diag}(1,1,T_c,T_c),
\qquad
T_c=\sqrt{\frac{1\ \mathrm m}{g}},
\qquad
\lVert\delta x\rVert_\mathrm{EL}=\lVert S\delta x\rVert_2.
$$

The EL tangent matrix is evolved in physical EL coordinates and QR is applied
to $SY_\mathrm{EL}$. The canonical formulation retains Experiment 011's
state-dependent Candidate-A pullback

$$
A(z)=S\,D\Phi(z),
$$

with QR/reset

$$
A(z_k)Y_{H,k}^-=Q_kR_k,
\qquad
Y_{H,k}^+=A(z_k)^{-1}Q_k.
$$

The corresponding initial bases remain

$$
Y_{\mathrm{EL},0}=S^{-1},
\qquad
Y_{H,0}=A(z_0)^{-1},
$$

so both begin as the same Candidate-A-orthonormal physical basis. QR uses a
deterministic positive-$R_{ii}$ sign convention, and tangent columns are never
sorted during evolution.

### Numerical-shadow protocol

- DOP853 with the three deterministic policies used by Experiments 010–011:

  | Shadow | Tolerances | `max_step` |
  | --- | --- | ---: |
  | baseline | `rtol=1e-9`, `atol=1e-11` | `0.0099773571 s` |
  | strict | `rtol=1e-11`, `atol=1e-13` | `0.0099773571 s` |
  | half step | `rtol=1e-9`, `atol=1e-11` | `0.00498867855 s` |

- QR cadence `0.25 s`.
- Duration `640 s`, with cumulative checkpoints at
  `80/160/240/320/400/480/560/640 s` and the terminal `560–640 s` window.
- Each policy independently integrates its own reference and tangent system in
  each formulation. A common reference would answer a different numerical
  question.
- Solver-facing angles remain locally rebased; winding is not part of solver
  error control or tangent geometry.
- Per-run validity retains finite complete integration, normalized
  energy/Hamiltonian drift, metric-factor singular-value and condition
  monitoring, QR and pullback orthonormality, scaled/canonical/physical
  reconstruction, reset identity, positive finite $R_{ii}$, finite log
  accumulation, exact cumulative bookkeeping, and deterministic policy
  provenance.

The numerical values and provenance are recorded in the Experiment 010 and
011 READMEs. This scaffold does not reproduce their accepted outputs as new
evidence.

## What Experiment 012 must not retune

After the physical initial-condition set is frozen, none of the following may
be adjusted for a particular case because its spectrum, convergence, or
formulation comparison is inconvenient:

- solver tolerances;
- `max_step` values;
- QR cadence;
- Candidate-A or pullback metric;
- EL/canonical tangent-basis correspondence;
- QR sign convention or tangent-column order;
- duration or checkpoint placement;
- physical masses, lengths, or gravity; or
- the two-level compatibility decision architecture.

The later design task must decide globally whether the exact numerical
thresholds from Experiments 010–011 remain scientifically meaningful across
qualitatively different trajectories. If a threshold or other inherited item
requires revision, the replacement must be justified and frozen for the whole
selected set before any long run. An initial condition may not be replaced,
and a threshold may not be relaxed, because that case fails.

## Initial-condition selection problem

Selection bias is the central methodological risk. The additional conditions
must be chosen without using their observed finite-time or long-time Lyapunov
behavior, solver compatibility, phase portrait, animation, or apparent
regularity. Otherwise Experiment 012 would test only cases already known to
support the protocol and could not provide honest robustness evidence.

No state-space scan, spectrum pilot, chaos classification, or visually guided
map inspection belongs in the selection step. Existing historical runs are a
contamination risk, not evidence for which points to choose.

Candidate selection principles for the later design audit are:

| Candidate principle | Scientific advantage | Risk or hidden selection bias |
| --- | --- | --- |
| Geometrically defined angle points in a predeclared periodic domain | Simple, reproducible, and independent of dynamical outcomes; can expose angular-coordinate and symmetry coverage directly. | Domain boundaries, axes, corners, and spacing may overrepresent special configurations; choosing the domain after seeing prior plots would contaminate the design. |
| Analytically energy-stratified configurations | Separates a deliberate range of physical energy scales and makes energy coverage explicit before integration. | Equal-energy states need not represent equivalent dynamics; choosing favorable energy bands from prior behavior is outcome selection, and angle-only zero-velocity states restrict which energy strata are reachable. |
| Symmetry-related plus symmetry-breaking configurations | Can distinguish implementation/formulation symmetry checks from genuinely different physical geometry. | Symmetry images may be dynamically redundant and must not be counted as independent evidence of generality; hand-picking the symmetry-breaking case can reintroduce bias. |
| A small deterministic design in $(\theta_1,\theta_2)$ with $\omega_1=\omega_2=0$ | Controls velocity as a factor, keeps the Legendre map simple, and yields an auditable finite design. | It tests only the zero-velocity slice; grid origin, orientation, and resolution can encode hidden preferences, and too many points would turn the experiment into a state-space survey. |
| Retain $(179^\circ,179^\circ,0,0)$ as an established reference anchor | Provides provenance and a direct check that the accepted protocol is reproduced unchanged. | It is not an additional condition and contributes no evidence of generality; counting it in the new-case total would overstate coverage. |

These are candidate design rules, not a shortlist of physical states. The
later design pass must choose one coherent rule or a justified combination and
derive the complete set from it before observing any new spectrum.

## Contamination and bias controls

The later design should record, before choosing cases, which historical angle
sets, plots, animations, solver failures, or qualitative labels are already
known to the project. In particular:

- prior Chaos experiments and teaching examples were deliberately designed
  cases, not an unbiased sampling frame;
- choosing points that look chaotic or regular in an existing map would make
  the test circular;
- preliminary spectrum runs, even short ones, can reveal enough behavior to
  bias inclusion or exclusion;
- excluding a selected case because it converges slowly would select for
  numerically easy trajectories rather than test protocol robustness;
- periodic or symmetry-equivalent states can be accidentally counted twice;
- changing an angle domain, energy band, grid offset, or case count after
  observing results is post-selection; and
- compute cost may constrain the predeclared design, but it cannot justify
  substituting a more favorable condition after execution begins.

Model-domain validity checks that reveal no Lyapunov outcome may be permitted
by the later contract, but their role and replacement rule must be declared in
advance.

## Scope question: what counts as “additional”?

The repository does not yet predeclare answers to these questions:

1. Should Experiment 012 vary only $(\theta_1,\theta_2)$ while keeping
   $\omega_1=\omega_2=0$, or should the design cover nonzero velocities?
2. Should physical energy be held approximately fixed to isolate geometry, or
   deliberately varied as part of the robustness claim?
3. Which symmetry-related states are exact physical equivalents, useful
   implementation controls, or genuinely additional evidence?
4. How many additional conditions provide a meaningful small robustness test
   without becoming a state-space survey?
5. Should the established $(179^\circ,179^\circ,0,0)$ case be rerun only as a
   provenance control, or referenced from Experiments 010–011?
6. Do clearly regular or non-chaotic regimes belong in the same experiment,
   or do they require a separate interpretation and convergence contract?

The last question matters because Experiment 010's requirement that chaotic
numerical shadows decorrelate by `80 s` is not automatically appropriate for
a regular trajectory. Failure to decorrelate could be the physically correct
behavior rather than a numerical-invalidity signal. Conversely, three nearly
identical numerical shadows do not provide the same between-shadow evidence
as three decorrelated chaotic shadows. The later design must resolve this
without using a candidate's observed spectrum to choose the rule.

## Future acceptance structure

The likely structure has two levels for every selected physical condition:

1. **Within-formulation validity and compatibility:** independently assess the
   baseline, strict, and half-step EL ensemble, and separately the three-shadow
   canonical ensemble, including long-time cumulative settling and all local
   numerical guards.
2. **Cross-formulation compatibility:** only after both formulations are
   interpretable, compare their EL and canonical ensemble estimates with a
   symmetric, predeclared descriptive rule based on both formulations'
   observed numerical variability.

That architecture is inherited. The precise thresholds are not frozen here.
Reusing Experiment 011's absolute limits may be defensible, but qualitatively
different spectra—especially values near zero—may expose different absolute
versus relative error behavior. The later design must decide this globally
before long integrations and must not engineer thresholds around pilot output.

Across the selected set, reporting must distinguish:

- **protocol or numerical-validity failure:** integration, energy,
  conditioning, reconstruction, or bookkeeping is invalid;
- **lack of within-formulation convergence:** a valid EL or canonical ensemble
  does not meet the predeclared settling/compatibility rule;
- **cross-formulation incompatibility:** both formulations are internally
  interpretable but fail the symmetric comparison rule;
- **physical initial-condition dependence:** both formulations agree for a
  condition, but its compatible spectrum differs from another condition's;
  this is a scientific result, not a protocol failure; and
- **regular/non-decorrelating behavior:** an outcome whose numerical and
  inferential meaning must follow the globally predeclared regular-case rule,
  not a post hoc chaos label.

The experiment-level decision must also state whether robustness requires all
selected conditions to pass, permits separately classified outcomes, or is
only descriptive. That choice remains for the Extra-High design pass.

## Claim boundary

This scaffold establishes only that the next investigation has a coherent
question, an inherited numerical foundation, and an explicit selection-bias
gate. Experiment 012 has not established:

- robustness across initial conditions;
- a global Lyapunov field;
- a chaos map;
- a universal spectrum;
- a regular/chaotic classifier;
- a production algorithm; or
- any new cumulative spectrum value.

No Experiment 012 numerical evidence exists yet, and no candidate selection
principle above has been accepted as the final design.

## Next design task

> Predeclare a small physical initial-condition set and acceptance contract
> using a selection rule that does not depend on observed Lyapunov outcomes.

That Extra-High task must resolve the scope questions, document contamination
risks, derive the complete condition set without exploratory spectrum runs,
and freeze one globally applicable interpretation/acceptance contract before
any long integration begins.
