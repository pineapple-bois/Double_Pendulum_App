# Experiment 020 — First-Flip Event Contract

## 1. Purpose

Experiment 020 will answer the following question:

> What precise physical event and numerical procedure provide a trustworthy reference measurement of the first completed link revolution for the equal-link simple double pendulum?

The experiment will establish a written, executable, and numerically validated contract for the observable called **first completed link revolution**, or **first flip** in shorter pedagogical language. It will cover the event definition, solver event surfaces, event identity, censoring, dimensionless time, numerical refinement, lift invariance, symmetry, grazing limitations, and near-simultaneous events.

This is a **physical-observable experiment**. It is not a Lyapunov, tangent-space, finite-time-stretching, state-space-map, persistence, rendering, or teaching-UI implementation. It may reuse the already validated physical Euler–Lagrange flow, but it must not couple the observable to Candidate-A distance, tangent/JVP evolution, QR renormalisation, or Lyapunov chart-rebasing conventions.

Successful completion and acceptance of Experiment 020 is the prerequisite for Steps 1–3 of [`development/chaos_content/prototypes/ROADMAP.md`](../../../prototypes/ROADMAP.md):

1. establish the first-flip event contract;
2. generate a dimensionless first-flip-time field; and
3. derive binary threshold fields from that same persisted time field.

Experiment 020 addresses only the first prerequisite.

## 2. Scientific contract

The simple Euler–Lagrange state is ordered as

$$
(\theta_1,\theta_2,\omega_1,\omega_2).
$$

For the continuous lifted solver angles $\theta_i(t)$, define displacement relative to the initial lifted state by

$$
\Delta_i(t)=\theta_i(t)-\theta_i(0).
$$

The candidate accepted definition is

$$
\tau_{\mathrm{flip}}
=
\inf
\left\{
t>0:
\max_{i\in\{1,2\}}
|\Delta_i(t)|
=
2\pi
\right\}.
$$

Equivalently, this is the first contact with the boundary of the open lifted-angle strip

$$
|\Delta_1(t)|<2\pi,
\qquad
|\Delta_2(t)|<2\pi.
$$

This definition matches the repository's simple-model coordinates. Both $\theta_1$ and $\theta_2$ are absolute link orientations measured from the downward vertical. The second-bob position is calculated as

$$
x_2=\ell_1\sin\theta_1+\ell_2\sin\theta_2,
\qquad
y_2=-\ell_1\cos\theta_1-\ell_2\cos\theta_2,
$$

so $\theta_2$ is not a relative elbow angle. Reaching $|\Delta_i|=2\pi$ therefore means that link $i$ has completed one net revolution relative to its initial orientation. Reversals before the completed revolution do not invalidate the event, but mere accumulated back-and-forth travel does not create one.

The observable does **not** mean:

- first passage through the upright orientation;
- accumulated angular path length of $2\pi$;
- wrapped angular difference;
- relative elbow rotation;
- arbitrary threshold crossing of an angle modulo $2\pi$.

The precise scientific description is **first completed link revolution**. **First flip** is the shorter pedagogical name.

## 3. Event surfaces

The reference calculation will use four smooth signed event surfaces:

$$
\phi_{i,s}(t)
=
s\Delta_i(t)-2\pi,
\qquad
i\in\{1,2\},
\quad
s\in\{-1,+1\}.
$$

For each surface, the intended `solve_ivp` semantics are:

- `terminal = True` for the primary early-terminating calculation;
- `direction = +1`, because $\phi_{i,s}$ enters the event region by increasing through zero;
- evaluation against the continuous lifted physical state, with no modulo reduction or chart rebasing;
- the earliest detected event determines the scalar first-flip time.

An event identity is the pair `(arm, direction)`, where `arm` is `1` or `2` and `direction` is `+1` or `-1`. Direction describes the sign of the completed lifted revolution, not the sign of a wrapped endpoint.

The scalar time remains unique when two or more surfaces reach zero simultaneously. Event attribution must therefore be able to contain multiple event identities. A convenience `winning_arm` or `winning_direction` value may be exposed only when the event is clearly unique.

No fixed tie tolerance is accepted by this plan. A numerical tie tolerance, if one is ultimately used, must be justified from the event-time and state-refinement evidence produced by Experiment 020.

## 4. Observation horizon and censoring

Every run must declare a finite observation horizon $T_{\max}>0$.

If no first-flip event is observed by that horizon, the physical information is right-censored:

$$
\tau_{\mathrm{flip}}>T_{\max}.
$$

The required language is:

> no flip observed by $T_{\max}$

It must never be reported as:

> this trajectory never flips

Censoring is a valid physical observation and must remain distinct from:

- solver failure;
- invalid or nonfinite integration state;
- failed numerical validation, such as unacceptable energy or convergence evidence;
- incomplete computation.

The experiment must define an explicit result state for an observed event and an explicit result state for right-censoring. It must not encode censoring as numerical failure, NaN, or an invalid event time.

Experiment 020 must also investigate the exact-horizon edge case $\tau_{\mathrm{flip}}=T_{\max}$ and recommend a precise convention for later capped scalar fields. That recommendation must be compatible with the roadmap's strict binary predicate $\tau_{\mathrm{flip}}<T_k$ and must state whether an explicit event-observed mask would be needed to preserve the distinction at the cap. No HDF5 or map schema is to be changed here.

## 5. Dimensionless time

For the current equal-link baseline, define

$$
t_g
=
\sqrt{\frac{\ell_{\mathrm{ref}}}{g}},
$$

with

$$
\ell_{\mathrm{ref}}
=
\ell_1
=
\ell_2.
$$

Then define

$$
\widehat{\tau}_{\mathrm{flip}}
=
\frac{\tau_{\mathrm{flip}}}{t_g}.
$$

This convention is unambiguous for the current baseline because `PendulumParameters` uses equal link lengths, with $\ell_1=\ell_2=1\,\mathrm{m}$ and $g=9.81\,\mathrm{m\,s^{-2}}$ by default. The tangent-space `characteristic_length` used elsewhere must not define $\ell_{\mathrm{ref}}$ implicitly; it is conceptually separate even though it has the same numerical value in the current baseline.

No unequal-link convention will be proposed or accepted in Experiment 020. For $\ell_1\ne\ell_2$, the choice among the first link, second link, total reach, or another reference length is a separate scientific decision.

Candidate pedagogical classes such as

$$
1,\;10,\;10^2,\;10^3,\ldots
$$

in units of $t_g$ are future derived-view candidates. They are not part of the event-contract acceptance criteria.

The feasibility diagnosis found that the class below $1\,t_g$ appears to be empty for the zero-initial-velocity, equal-unit initial-condition grid, with an energy-bound argument supporting that finding. Experiment 020 should record this as planning evidence rather than use it to select display bins. The eventual bins and $T_{\max}$ must be chosen from a coarse pilot field and its observed event-time/censoring distribution, not from aesthetic preference.

## 6. Reference implementation shape

The smallest intended experiment-level API is conceptually:

```python
first_flip_time(
    initial_state,
    parameters,
    solver_spec,
    observation_horizon,
)
```

The implementation may use a small experiment-specific specification and result dataclass where that improves validation and serialization. It must not create a generic event framework or a prototype-wide observable hierarchy.

The result must expose, at minimum:

- event observed versus right-censored;
- dimensional event time when observed;
- dimensionless event time when observed;
- unique winning arm and direction when numerically resolved;
- all tied or numerically indistinguishable event identities;
- whether event attribution is unique, tied, or unresolved;
- solver success and message;
- solver method, tolerances, and effective maximum step;
- integration endpoint and declared observation horizon;
- number of RHS evaluations and available step/output counts;
- physical state at the event when observed;
- each relevant event-surface residual at the reported event time;
- angular velocity of the triggering arm or arms at the event;
- initial, maximum observed, and event-time energy diagnostics;
- sufficient timing and numerical provenance to reproduce the run.

For a censored result, dimensional and dimensionless event times and event identities should be absent rather than replaced with a fabricated cap value. A capped scalar is a later map adapter concern. Solver failure and failed numerical validation must be expressible without masquerading as censoring.

## 7. Existing repository components to reuse

### Production simple model

Consult and preserve the coordinate and equation conventions in:

```text
src/double_pendulum/models/lagrangian.py
```

`DoublePendulumLagrangian` supplies the production symbolic equations and confirms through its position calculation that both angular coordinates are absolute link orientations. Its physical `solve_ivp` path leaves angles unwrapped.

Do not use `DoublePendulumLagrangian._solve_ode` as the event interface. It returns sampled solution arrays and metadata but does not preserve `t_events`, `y_events`, or the dense interpolant needed by this experiment.

### Validated Euler–Lagrange reference

Reuse or directly consult these definitions in:

```text
development/chaos_content/prototypes/state_space_maps/src/lyapunov/reference.py
```

- `PendulumParameters` for the simple point-mass parameter contract;
- `EulerLagrangeState` for state order and finite-value validation;
- `SolverSpec` for the existing DOP853 baseline of `rtol=1e-9` and `atol=1e-11`;
- `EulerLagrangeDynamics.flow` as the validated four-state physical RHS;
- `simple_energy` and the existing energy scale for diagnostics.

`EulerLagrangeDynamics` is reusable because its physical flow is built from the production simple Lagrangian equations. Its package location does not make the first-flip observable a Lyapunov observable.

The segmented Lyapunov trajectory driver must **not** be used as the event engine. `_rebase_reference_angles` maps the first two state components back to a principal branch at segment boundaries and therefore destroys the global winding information required by $\Delta_i(t)$. `_solve_segment` also returns sampled segment arrays rather than an event result.

Tangent evolution, JVPs, Candidate-A distance, finite shadows, QR decomposition, renormalisation, Lyapunov rates, the hybrid evaluator, and the eight-state compiled tangent RHS are not part of Experiment 020.

### SciPy event precedent

Consult:

```text
development/chaos_content/experiments/foundations/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py
```

Its `solve_ivp(events=...)` use demonstrates repository-local handling of `t_events`, `y_events`, event-state energy checks, explicit solver failure, and deterministic evidence. Its Hamiltonian canonical state and Poincaré section semantics are not reusable first-flip definitions.

### Lifted-angle/revolution precedent

Consult:

```text
development/chaos_content/experiments/foundations/004_finite_time_exponential_growth/finite_time_exponential_growth.py
```

Its `lifted_angle_history` and `revolution_history` establish the conceptual distinction between wrapped state-space distance and global winding history. Its sampled `numpy.unwrap` reconstruction and first sampled crossing are diagnostics only; they must not replace continuous solver event detection for the reference first-flip time.

## 8. Experiment implementation files

The subsequent implementation task should create only the minimal local experiment files:

```text
development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/
├── PLAN.md
├── README.md
├── first_flip_event_contract.py
└── test_first_flip_event_contract.py
```

`README.md` will become the authoritative experiment report and status record. `first_flip_event_contract.py` will own the reference evaluator, named-case harness, deterministic command-line entry point, and concise evidence formatting. The test module will own deterministic contract and refinement tests.

A small reproducible evidence bundle may optionally be written beneath:

```text
development/chaos_content/experiments/outputs/020/
```

if it materially improves review. Such output should follow the ignored experiment-output convention and should be limited to a concise machine-readable summary or table. Plots, large trajectories, grids, and committed generated data are unnecessary.

The implementation task may add a concise Experiment 020 entry to `development/chaos_content/experiments/README.md` to register the new physical-observables strand. The following existing areas are expected to remain unchanged:

- `src/double_pendulum/` production code;
- `app/` and all teaching UI code;
- `development/chaos_content/prototypes/state_space_maps/src/generation/`;
- `development/chaos_content/prototypes/state_space_maps/src/lyapunov/`;
- state-space-map runners, renderers, HDF5 schema, and persisted map outputs;
- the compound-pendulum implementation.

## 9. Named trajectory suite

The implementation must establish a small named suite by verifying candidate initial conditions numerically and then freezing the accepted cases in the experiment. Initial conditions must not be declared authoritative merely because they appeared in an exploratory feasibility probe.

The minimum suite is:

| Named role | Evidence required |
| --- | --- |
| Stable downward equilibrium | Robust right-censored/no-event result; solver reaches $T_{\max}$ with finite state and stable energy. |
| Arm 1, positive | Earliest event identity `(1, +1)`. |
| Arm 1, negative | Earliest event identity `(1, -1)`. |
| Arm 2, positive | Earliest event identity `(2, +1)`. |
| Arm 2, negative | Earliest event identity `(2, -1)`. |
| Reflection pair | Equal event times, same arm, and reversed direction under the accepted reflection symmetry. |
| Near-horizon case | A converged event time that can be bracketed by observation horizons to test event/censor boundary semantics. |
| Near-simultaneous candidate | Two surfaces approach the earliest time closely enough to exercise attribution diagnostics, if a bounded deterministic search finds one. |
| Near-grazing candidate | Small event-surface derivative at contact, if a bounded deterministic search finds one. |

Candidate discovery must remain small and deterministic. A bounded list or coarse candidate sweep is acceptable; a state-space map is not. Once a candidate is selected, the README must record its state, why it was selected, and whether it passed refinement. Near-simultaneous and near-grazing searches may legitimately report that no trustworthy physical example was found, provided the search and limitation are explicit and the associated result-classification logic is still tested where practical.

The exact upward equilibrium must not be the principal no-event case. It is mathematically stationary but numerically and physically unstable. The stable downward equilibrium is the robust censoring reference.

## 10. Numerical validation matrix

For each representative event trajectory, compare at least the following policies while keeping the same physical initial condition and observation horizon:

| Policy | Required change |
| --- | --- |
| Baseline | Existing DOP853 `SolverSpec` tolerances and a recorded physical maximum-step policy. |
| Stricter tolerances | Reduce both relative and absolute tolerances by a declared factor. |
| Reduced maximum step | Reduce the baseline maximum step, normally by a factor of two. |
| Adaptive comparison | Omit the imposed maximum-step cap where meaningful and let DOP853 choose steps from its error controller. |

The starting capped-step candidate is the existing gravitational-scale policy $t_g/32$, but Experiment 020 must record the effective value and validate it rather than treating its prior Lyapunov use as first-flip evidence.

For each policy comparison, examine:

- event-time convergence in seconds and in units of $t_g$;
- event identity and unique/tied/unresolved classification;
- event-surface residuals;
- physical state agreement at the event;
- angular velocity at the triggering surface;
- absolute and normalized energy error;
- solver success, integration endpoint, and RHS evaluations;
- maximum accepted angular increment where accepted solver states make it available.

For selected event trajectories, independently check the reported root by one of the following:

- a nonterminal dense-output run followed by an explicit local bracket and scalar root solve;
- a stricter reference trajectory whose dense interpolant brackets the same surface;
- an equivalent local refinement that does not simply reread `t_events` as its own check.

The check must verify both time and state at the root. It must also determine whether more than one crossing could plausibly have occurred inside an accepted step.

PLAN.md deliberately sets no acceptance tolerances for event-time differences, state differences, residuals, tie classification, or crossing velocity. The experiment must derive and document defensible thresholds from the observed convergence scales and numerical resolution. It must not choose a gate after inspecting only the case it is intended to accept.

## 11. Symmetry and lift-invariance checks

### Lift invariance

For integers $k_1$ and $k_2$, compare physically equivalent lifted initial states

$$
(\theta_1,\theta_2,\omega_1,\omega_2)
$$

and

$$
(\theta_1+2k_1\pi,\theta_2+2k_2\pi,\omega_1,\omega_2).
$$

Because the physical equations are periodic and each event displacement is measured relative to its own initial lift, the expected results are:

- equal elapsed first-flip times within the convergence-derived tolerance;
- identical observed/censored status;
- identical arm and direction attribution;
- identical angular velocities and physical energy diagnostics;
- event states differing only by the imposed $2k_i\pi$ angular offsets.

Test shifts of each angular coordinate separately and at least one combined shift. This check guards directly against accidental use of wrapped absolute angles as event surfaces.

### Reflection symmetry

For the zero-initial-velocity equal-parameter model, compare an initial state with its sign reflection

$$
(\theta_1,\theta_2,0,0)
\mapsto
(-\theta_1,-\theta_2,0,0).
$$

The expected transformation is:

- equal elapsed first-flip time;
- same winning arm or arms;
- every event direction reversed;
- reflected angular and angular-velocity event state;
- matching energy and solver-validity conclusions within numerical resolution.

Interchanging arms is **not** an assumed symmetry. Even at equal masses and lengths, the first link supports both masses and the second does not.

## 12. Grazing-event policy

The mathematical contract is first contact with $|\Delta_i|=2\pi$. A practical event detector usually discovers a sign-changing crossing. These statements are not automatically equivalent for a tangential contact.

For a signed event surface,

$$
\frac{\mathrm{d}\phi_{i,s}}{\mathrm{d}t}
=
s\omega_i.
$$

The experiment must therefore record the triggering arm's angular velocity at every detected event. Events whose crossing velocity is small relative to the numerical/refinement evidence must be flagged rather than silently treated as routine transversal crossings. No fixed “near zero” threshold is specified in advance; the report must state how the flag scale was chosen.

For every suspected grazing case:

- inspect the relevant surface on a local dense-output interval;
- reduce the maximum step and tighten tolerances;
- determine whether the surface changes sign, merely touches zero, or remains numerically unresolved;
- report whether the primary terminal-event run would have detected the same contact.

If true grazing contact cannot be robustly demonstrated or detected, Experiment 020 may certify the implementation only for transversal first-flip events. It must retain first contact as the scientific definition and record grazing detection as an explicit limitation. It must not silently redefine first flip as only a sign-changing crossing.

## 13. Near-simultaneous-event policy

The experiment must investigate cases in which two or more event surfaces approach zero at nearly the same earliest time.

It must not adopt a hand-picked tie tolerance. Instead, it must:

- compare candidate root times under the numerical refinement matrix;
- inspect all four event-surface residuals at and around the earliest root;
- use a short continuation or nonterminal diagnostic run where terminal stopping hides another nearby root;
- compare event states and crossing velocities;
- derive any numerical indistinguishability scale from the stable refinement envelope.

The final experiment result must classify attribution as one of:

- **clearly unique first event** — one surface is separated from every other candidate beyond numerical uncertainty;
- **numerically resolved simultaneous/tied event** — multiple identities agree within a justified resolution and remain tied under refinement;
- **unresolved near-tie** — available evidence cannot order the candidate events reliably.

An unresolved attribution must not be collapsed to the event-list order returned by SciPy. The scalar earliest time may still be reportable if it is itself converged, but the unresolved identity must remain explicit.

## 14. Censoring validation

The stable downward equilibrium must provide at least one robust censored case. The solver must:

- succeed and reach $T_{\max}$;
- report no event;
- retain finite physical states;
- retain acceptable energy behavior;
- remain censored under stricter tolerances and reduced maximum step.

At least one converged event trajectory must be run with horizons on both sides of its refined event time. This should establish that:

- a horizon below the event produces a successful censored result;
- a horizon beyond the event produces the same converged event;
- numerical failure is never interpreted as censoring;
- behavior at a horizon numerically coincident with the root is explicitly classified.

The experiment must recommend a precise later convention for the exact-horizon case. It should evaluate the compatibility of these facts:

- the physical event exists at $\tau_{\mathrm{flip}}$;
- the roadmap's binary observable uses the strict predicate $\tau_{\mathrm{flip}}<T_k$;
- a capped scalar alone cannot distinguish an event exactly at the cap from right-censoring unless the boundary convention deliberately makes them equivalent;
- an explicit event-observed mask would preserve that distinction if required.

This section produces a recommendation only. Persistence code and schemas remain unchanged.

## 15. Energy diagnostic

Reuse `simple_energy` from the validated reference module. For state $(\theta_1,\theta_2,\omega_1,\omega_2)$ and simple point-mass parameters, the conserved energy is

$$
\begin{aligned}
E={}&
\frac{1}{2}(m_1+m_2)\ell_1^2\omega_1^2
+\frac{1}{2}m_2\ell_2^2\omega_2^2 \\
&+m_2\ell_1\ell_2\omega_1\omega_2
\cos(\theta_1-\theta_2) \\
&-(m_1+m_2)g\ell_1\cos\theta_1
-m_2g\ell_2\cos\theta_2.
\end{aligned}
$$

Where normalized drift is useful, retain the repository's parameter scale

$$
E_{\mathrm{scale}}
=
g\left[(m_1+m_2)\ell_1+m_2\ell_2\right]
$$

and evaluate

$$
\delta_E(t)
=
\frac{|E(t)-E(0)|}{E_{\mathrm{scale}}}.
$$

Energy must be evaluated:

- at the initial state;
- over accepted or requested diagnostic states where practical;
- at the detected event state;
- at $T_{\max}$ for censored trajectories.

Energy is a diagnostic, not a demand that adaptive DOP853 behave symplectically. The experiment should use it to identify obviously unreliable integrations, compare solver policies, and qualify long-duration evidence. It must derive an experiment-level energy gate from convergence evidence rather than importing the Lyapunov field's existing gate without review.

## 16. Performance observations

Correctness has priority over throughput in Experiment 020. Nevertheless, named-trajectory runs should record enough execution evidence to plan the later coarse field.

Capture where practical:

- elapsed wall time;
- requested and actual integration endpoint;
- RHS evaluation count;
- accepted or diagnostic output-point count where meaningful;
- event versus censored status;
- whether early termination occurred;
- solver policy and effective maximum step.

Report early-event and full-horizon censored costs separately. Do not extrapolate them into a 512² estimate and do not treat a small warm timing as a throughput benchmark.

Do not optimize prematurely. Experiment 020 should use the validated four-state physical reference flow. It must not introduce compiled physical-only machinery unless reference performance makes the contract experiment itself impractical. If a later pilot needs a compiled four-state RHS, that work must be separately justified and validated against `EulerLagrangeDynamics.flow`; it must not reuse tangent/JVP computation merely because a compiled eight-state evaluator already exists.

## 17. Acceptance criteria

Experiment 020 is accepted only if all of the following are satisfied or, where explicitly allowed, bounded as an honest documented limitation:

1. The event definition is documented and matches repository coordinate semantics.
2. Lifted physical angles are used without Lyapunov rebasing.
3. All four arm/direction event identities are demonstrated.
4. Event times converge under solver refinement for representative cases.
5. Event-surface residuals are numerically small, stable, and interpreted against the refinement evidence.
6. Energy behavior is documented for event and censored runs.
7. Lift invariance under $\theta_i(0)\mapsto\theta_i(0)+2k\pi$ is demonstrated.
8. The declared reflection-symmetry checks pass, and no unsupported arm-exchange symmetry is claimed.
9. Censoring is represented distinctly from numerical failure or invalidity.
10. Near-horizon behavior and the exact-horizon semantic choice are tested and documented.
11. Grazing limitations are investigated and explicitly documented; transversal-only certification is acceptable only when stated clearly.
12. Near-simultaneous-event handling is investigated and explicitly documented, including unresolved attribution where applicable.
13. The experiment produces enough evidence to accept, reject, or conditionally accept `first_flip_time(...)` for promotion into `state_space_maps`.
14. Existing repository tests remain passing.
15. The worktree contains no unrelated modifications.
16. One deterministic command reproduces the named diagnostic summary, and focused tests reproduce the contract checks.

The README verdict must be `ACCEPT`, `CONDITIONALLY ACCEPT`, or `REJECT`, with claim boundaries. A visually plausible trajectory or isolated successful event is not acceptance evidence.

## 18. Non-goals

Experiment 020 does not:

- generate state-space maps;
- run 512² calculations;
- choose final pedagogical colour bins;
- modify HDF5 or any persistence schema;
- build binary maps;
- add a renderer;
- modify Lyapunov algorithms;
- build a generic event abstraction;
- modify the production application;
- address the compound pendulum;
- resolve unequal-link nondimensionalisation;
- integrate with teaching UI;
- promote code into the state-space-map prototype;
- introduce compiled or batch integration without a separately earned need.

## 19. Expected experiment outputs

The completed implementation should leave behind:

- a focused `README.md` stating the question, contract, method, reproducible commands, evidence, limitations, and verdict;
- `first_flip_event_contract.py` containing the experiment-specific reference evaluator and deterministic named-case harness;
- `test_first_flip_event_contract.py` containing deterministic contract, symmetry, lift, censoring, and refinement tests;
- a concise named-trajectory/refinement table in the README or a small reproducible summary artifact;
- explicit accepted, rejected, conditional, or open conclusions for:
  - event definition;
  - event detection and root accuracy;
  - censoring and exact-horizon semantics;
  - unique, tied, and unresolved event attribution;
  - grazing detection limitations;
  - dimensionless equal-link scaling;
  - readiness for map promotion.

The named-trajectory evidence table should include at least: initial state, parameters, $T_{\max}$, solver policy, observed/censored state, dimensional and dimensionless event times, event identities, maximum event residual, event crossing velocity, energy drift, RHS evaluations, wall time, and changes under refinement.

Follow the neighbouring experiment convention of one deterministic CLI command and one focused pytest command. Suitable command shapes are:

```bash
uv run python development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/first_flip_event_contract.py --self-check
```

```bash
uv run pytest development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/test_first_flip_event_contract.py -q
```

The implementation may refine the CLI flags, but the README must record the final exact commands. Any generated output belongs under the ignored `development/chaos_content/experiments/outputs/020/` tree and must be reproducible from the documented command.

## 20. Promotion gate

Promotion into a location such as

```text
development/chaos_content/prototypes/state_space_maps/src/first_flip/
```

is allowed only if Experiment 020 establishes a trustworthy reference contract and its README verdict explicitly authorizes promotion within documented limitations.

After successful acceptance, the next prototype task may be narrowly scoped to:

- promote the validated first-flip primitive without changing its scientific semantics;
- build a scalar-field adapter on the existing periodic grid;
- perform a small coarse pilot rather than a 512² production-scale calculation;
- use pilot evidence to select useful $T_{\max}$ and dimensionless bins;
- determine whether the existing capped-scalar HDF5 semantics are sufficient or whether an explicit event-observed mask is scientifically justified.

That future prototype work is not part of Experiment 020. Failure or conditional acceptance of the event contract must stop automatic promotion and identify the next smallest unresolved numerical task.

## 21. Implementation task handoff

## Next Codex task

```text
Implement Experiment 020 exactly within
development/chaos_content/experiments/physical_observables/020_first_flip_event_contract/
according to PLAN.md.

Create the experiment-local README.md, first_flip_event_contract.py, and
test_first_flip_event_contract.py. Reuse the validated simple Euler–Lagrange
physical flow, parameter/state/solver contracts, and energy expression identified
in PLAN.md. Implement the four signed terminal solve_ivp event surfaces using the
continuous lifted physical angles. Do not use the segmented/rebased Lyapunov driver
or any tangent, JVP, QR, map, persistence, renderer, production-app, or teaching-UI
machinery.

Establish and freeze the named trajectory suite only after verifying each candidate.
Run the solver-refinement, independent-root, lift-invariance, reflection-symmetry,
censoring, near-horizon, grazing, and near-simultaneous investigations required by
PLAN.md. Derive numerical acceptance tolerances from the recorded convergence
evidence rather than choosing them arbitrarily. Record timing and solver-work data
only to inform the later pilot; do not optimize or extrapolate to 512².

Run the focused Experiment 020 tests and the relevant existing repository tests.
Update the experiment-local README.md with reproducible commands, the named-case and
refinement evidence, explicit limitations, and an ACCEPT, CONDITIONALLY ACCEPT, or
REJECT verdict. Optionally register Experiment 020 in the experiment archive index
and write a small reproducible ignored summary under experiments/outputs/020/ if it
materially improves review.

Stop after the Experiment 020 evidence and verdict. Do not promote the evaluator into
state_space_maps, generate a field, modify HDF5, add a renderer, choose final bins,
or begin Steps 2–3.
```
