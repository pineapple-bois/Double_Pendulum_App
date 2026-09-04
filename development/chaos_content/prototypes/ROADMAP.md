# Chaos Prototypes Roadmap

## Purpose

This roadmap stages the next development work under:

```text
development/chaos_content/prototypes/
```

The aim is to close the current pedagogical gap between:

```text
nearby deterministic trajectories diverge
        ↓
finite-time stretching / Lyapunov maps
```

The next scaffold should introduce physically legible event observables before adding more tangent-space machinery or higher map resolution.

The immediate priority is therefore:

```text
physical event
    ↓
event timescale
    ↓
thresholded outcome map
    ↓
finite-time sensitivity as a function of observation time
```

This is a roadmap, not an implementation specification. Existing prototype architecture and numerical contracts should be reused where justified, but no new abstraction should be introduced merely because it appears convenient.

> Complexity is earned by verification.

---

## Pedagogical objective

The learner should be able to distinguish the following ideas:

- large or complicated motion is not the same as chaos;
- a macroscopic event is not the same as local instability;
- an event time and a finite-time stretching rate answer different questions;
- finite-time sensitivity depends on the observation window;
- intricate state-space structure should first be attached to a physically interpretable outcome.

The first new observable should therefore be **time to first flip**.

The intended local narrative is:

```text
What happens?
    ↓
When does it happen?
    ↓
How does that outcome partition initial-condition space?
    ↓
How sensitive are nearby initial conditions over the same time scales?
```

---

# Immediate scaffold

The first implementation scaffold consists of Steps 1–3 below.

These steps should be treated as one small development strand, with a feasibility diagnosis against the existing codebase before implementation begins.

---

## Step 1 — Define the first-flip event contract

### Question

What precisely does "first flip" mean for the double pendulum, and how can it be detected in a way that is physically meaningful, numerically stable, and compatible with the existing trajectory/map machinery?

### Core requirement

The event definition must be based on an **unwrapped angular history**, not on an angle reduced modulo $2\pi$.

For each arm, retain or reconstruct a continuous angular coordinate

$$
\tilde\theta_i(t)
$$

and define a first complete revolution relative to the initial configuration using an explicit event rule.

A candidate form is

$$
\tau_{\mathrm{flip},i}
=
\inf\left\{
 t>0:
 \left|\tilde\theta_i(t)-\tilde\theta_i(0)\right|\ge 2\pi
\right\},
$$

with overall first-flip time

$$
\tau_{\mathrm{flip}}
=
\min_i \tau_{\mathrm{flip},i}.
$$

This formula is a candidate contract, not yet an accepted convention. Codex should inspect the existing model and integration conventions and report whether a better event definition is already supported or required.

### Contract questions to resolve

The feasibility diagnosis should explicitly answer:

- Are angular states currently integrated as naturally unbounded coordinates, wrapped coordinates, or wrapped only for presentation?
- Can first flip be detected directly from solver events, or would it currently require sampled-output reconstruction?
- Is event-root interpolation already available in the relevant generation code?
- Should the first flip be defined per arm and then reduced to the earliest event?
- How should simultaneous or near-simultaneous flips be represented?
- What numerical tolerance should define an accepted event crossing?
- What happens when no flip occurs before the observation horizon?
- Can the event be computed without storing full trajectories for map generation?
- Does the current batch/tiled map architecture already support event-valued observables and censored/no-event results?

### Validation requirements

Before any grid is generated, establish the event on a small set of named trajectories:

- one trajectory that clearly never flips over a short interval;
- one trajectory that clearly flips;
- one trajectory near a first-flip boundary;
- where practical, one case in which each arm flips first.

Checks should include:

- solver success;
- finite states;
- energy behaviour under the accepted model/solver policy;
- event residual at the detected crossing;
- stability of $\tau_{\mathrm{flip}}$ under modestly stricter tolerances;
- stability with respect to output sampling if event roots are not obtained directly from the integrator.

### Exit condition

A written and tested first-flip contract exists, with explicit failure/no-event semantics, and one deterministic command can reproduce a small diagnostic set.

---

## Step 2 — Generate a first-flip-time map

### Question

Across the established $(\theta_1(0),\theta_2(0))$ initial-condition slice, how long does it take before either arm completes its first full revolution?

### Dimensionless observable

Use the gravitational timescale

$$
t_g=\sqrt{\frac{\ell}{g}}
$$

as the base time unit, and map

$$
\hat\tau_{\mathrm{flip}}
=
\frac{\tau_{\mathrm{flip}}}{t_g}.
$$

If the model has unequal lengths or the existing parameter contract makes a single $\ell$ ambiguous, Codex should report that explicitly rather than silently choosing a convention.

### Presentation target

The first pedagogical rendering should favour **logarithmic timescale bins** rather than a smooth continuous colour scale.

Candidate classes are:

$$
\hat\tau_{\mathrm{flip}} < 1,
$$

$$
1 \le \hat\tau_{\mathrm{flip}} < 10,
$$

$$
10 \le \hat\tau_{\mathrm{flip}} < 10^2,
$$

$$
10^2 \le \hat\tau_{\mathrm{flip}} < 10^3,
$$

and so on, plus an explicit

```text
no flip observed by T_max
```

class.

The exact binning and maximum integration horizon should be treated as experiment parameters, not hard-coded scientific truth.

### Scientific intent

This map should answer a directly legible physical question:

> Starting from this initial configuration, on what dynamical timescale does the first complete revolution occur?

The goal is not yet to classify chaos.

The map should reveal whether state-space is partitioned into broad no-flip regions, short-time flip regions, long-delay regions, and intricate boundaries between them.

### Computational questions for feasibility diagnosis

Codex should inspect the existing generation machinery and report:

- whether the current grid evaluator can terminate trajectories early after the first event;
- whether event time can be stored as a scalar field with a no-event sentinel/mask;
- whether current tile persistence supports masks or categorical metadata;
- whether the first-flip calculation can share the same initial-condition specification as the existing finite-time stretching maps;
- expected wall cost at 512² for candidate $T_{\max}/t_g$ values;
- whether a coarse pilot grid should precede 512² in order to choose a useful horizon;
- whether the current renderer supports discrete/categorical colourmaps and a separate no-event class.

### Minimal progression

Do not begin with a very long 512² integration merely to populate the highest decade.

Prefer:

```text
small named trajectories
    ↓
coarse pilot map
    ↓
choose informative T_max and bins
    ↓
512² map
```

### Exit condition

A reproducible map dataset exists for $\hat\tau_{\mathrm{flip}}$, with explicit event/no-event semantics, numerical provenance, and a static binned rendering whose meaning is physically interpretable without introducing Lyapunov theory.

---

## Step 3 — Derive binary flip-threshold maps

### Question

For a chosen observation horizon, which initial conditions have experienced a first flip and which have not?

### Observable

Binary maps should be derived from the first-flip-time dataset rather than recomputed independently whenever possible.

For threshold $T_k$, define

$$
F_k(x_0)
=
\mathbf{1}
\left[
\tau_{\mathrm{flip}}(x_0) < T_k
\right].
$$

Natural dimensionless thresholds are

$$
T_k = 10^k\sqrt{\frac{\ell}{g}},
\qquad k=0,1,2,3,\ldots
$$

subject to the model/time-scale convention accepted in Step 2.

### Pedagogical role

The binary map should make the geometry of event boundaries visually unmistakable.

It asks:

> By this physically meaningful time horizon, has a complete revolution occurred?

A sequence of thresholds should show how the flip-accessible region expands and how increasingly fine boundaries emerge as the observation horizon increases.

This is intended to prepare the learner for the later question:

> Why are these outcome boundaries so sensitive to initial conditions?

That question will motivate comparison with finite-time stretching maps.

### Rendering target

Produce a small threshold series from the same scalar dataset, for example:

```text
T/t_g = 1
T/t_g = 10
T/t_g = 100
T/t_g = 1000
```

Only thresholds actually supported by the chosen $T_{\max}$ should be rendered.

A threshold above the integration horizon must never be implied from censored data.

### Exit condition

One accepted first-flip-time dataset can reproducibly generate a family of binary threshold maps without rerunning dynamics, and the distinction between "not flipped by threshold" and "not known beyond T_max" is explicit.

---

# Feasibility diagnosis for Codex

Before implementing Steps 1–3, inspect the existing code under at least:

```text
development/chaos_content/prototypes/state_space_maps/src/generation/
development/chaos_content/prototypes/state_space_maps/src/lyapunov/
```

and any directly relevant prototype/model/solver code required to understand established conventions.

The diagnosis should **report before coding**.

Use the following shape.

## 1. Existing capability inventory

Identify what already exists for:

- model/state representation;
- angle wrapping/unwrapping conventions;
- solver configuration;
- event detection/root interpolation;
- per-initial-condition early termination;
- batch and tiled evaluation;
- scalar-field result representation;
- masks / missing / censored values;
- persistence and provenance;
- discrete rendering;
- reusable initial-condition grid specifications.

## 2. Gaps

For each of Steps 1–3, state the smallest missing capability.

Distinguish between:

- missing mathematics/contract;
- missing reference implementation;
- missing compiled/batch implementation;
- missing persistence semantics;
- missing rendering support.

## 3. Reuse assessment

For each relevant existing component, classify it as:

```text
reuse as-is
reuse with a small extension
reference only
not suitable
```

Give a short reason.

Do not broaden into general refactoring.

## 4. Proposed minimum change set

List the smallest files/modules that would need to change or be added to support Steps 1–3.

Prefer explicit scientific concepts such as:

```text
first_flip_time(...)
```

over generic event-framework abstractions unless the existing architecture already provides a justified reusable contract.

## 5. Numerical risks

Call out at least:

- wrapped-angle false events;
- missed crossings from sampled trajectories;
- event-root accuracy;
- very long no-flip integrations;
- sensitivity of near-boundary event times;
- ambiguity in the choice of gravitational timescale;
- overflow or inappropriate sentinel handling for no-event cells;
- accidental confusion between "no event by T_max" and "never flips".

## 6. Cost estimate

Give a rough feasibility estimate for:

- named single-trajectory validation;
- a coarse pilot grid;
- a 512² map for representative candidate horizons.

Use existing observed map-generation costs where relevant, but do not assume first-flip maps have the same cost profile as fixed-horizon Lyapunov calculations: early event termination may make them substantially cheaper in some regions, while long-lived no-flip cells may dominate total cost.

## 7. Recommendation and stop condition

Conclude with one of:

```text
feasible with existing machinery
feasible with a small scoped extension
requires a new numerical primitive before map work
blocked by an unresolved mathematical convention
```

Then propose only the **next justified task**.

Do not implement the whole roadmap as part of the diagnosis.

---

# Next scaffold after Steps 1–3

These items are intentionally **not** part of the first implementation request, but they define where the narrative goes next.

## Step 4 — Finite-time stretching as a function of observation window

Using the existing one-vector finite-time stretching observable, generate a modest-resolution series such as

$$
\Lambda^{(1)}_T(x_0)
$$

for several values of $T/t_g$.

The important question is not higher spatial resolution. It is:

> Which structures appear, persist, sharpen, move, or disappear as the finite-time observation window changes?

512² is expected to be adequate for this narrative unless evidence shows otherwise.

## Step 5 — Compare physical-event geometry with sensitivity geometry

Compare:

$$
\tau_{\mathrm{flip}}(x_0)
$$

and

$$
\Lambda^{(1)}_T(x_0).
$$

Look specifically for:

- high stretching near sharp first-flip boundaries;
- rapid flips without especially high stretching;
- high stretching without flips inside the same time horizon;
- persistent low-sensitivity regions;
- changes in these relationships as $T$ increases.

The pedagogical distinction to establish is:

```text
large motion ≠ chaos
macroscopic event ≠ local instability
```

## Step 6 — Compound-model comparison

Only after the simple model's first-flip observable is understood should the same physical observable be evaluated for the compound/physical double-pendulum model.

The first question should be qualitative:

> Which features of the first-flip geometry survive a more realistic mass distribution?

Do not begin by porting or duplicating tangent/Lyapunov machinery for the compound model.

Use the physical event observable as the lowest-cost and most interpretable model comparison first.

---

# Architectural constraints

The roadmap should preserve the existing prototype principles:

- experiments are evidence; prototype code is implementation;
- separate specification, calculation, result, observable, persistence, and rendering;
- keep physical observables distinct from state-space and tangent observables;
- keep map computation independent of teaching UI;
- maintain a clear reference implementation before optimizing;
- validate compiled/batched kernels against the reference behaviour;
- make angle conventions and event semantics explicit;
- do not let map infrastructure silently redefine the mathematics;
- no production promotion is implied by successful prototype results.

The first-flip observable belongs to the **physical observable** layer. It should not be coupled to Candidate-A state distance or Lyapunov conventions merely because those modules already exist.

---

# Current decision

The immediate development request is limited to:

```text
1. first-flip event contract
2. dimensionless first-flip-time map
3. binary threshold maps derived from the same data
```

The first action is a **Codex feasibility diagnosis against the existing prototype codebase**.

No broad refactor, production integration, compound-model implementation, or additional Lyapunov development should be undertaken until that diagnosis is reviewed.
