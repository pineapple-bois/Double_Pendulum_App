# Chaos Page Context

## Purpose

This document captures the identity, educational architecture, reference projects, and design principles for the Double Pendulum Explorer's future chaos material.

It is not a page specification and it is not an implementation plan. Its purpose is to preserve the reasoning behind the page so that later content, interaction, visualisation, and numerical work can be judged against a coherent educational identity.

The central principle is:

> **The educational architecture should determine the interface, rather than the available numerical features determining the interface.**

The chaos experience should feel like a continuation of the existing derivation and simulation material, not like a separate expert dashboard attached to it.

---

## Existing educational identity

The Double Pendulum Explorer is already deliberately different from many interactive pendulum simulators.

The learner first encounters the mechanics through a derivation of the equations of motion from first principles. The simulation then turns the quantities from that derivation into explicit, controllable initial conditions and physical parameters.

The learner can choose quantities such as:

- $\theta_1$, $\theta_2$
- $\omega_1$, $\omega_2$
- masses and lengths
- gravitational acceleration
- formulation/model choices where appropriate

This is intentional.

The simulator is not primarily a sandbox in which the learner drags a bob somewhere and watches what happens. It preserves the connection between mathematical state and simulated state.

The current simulation also establishes an important visual grammar:

> **animation state ↔ mathematical representation**

The pendulum motion, angular-state projection, time-series plots, playback position, and highlighted points are different views of the same evolving state. The chaos material should extend this grammar.

---

## Core identity for the chaos material

The chaos page should not begin by presenting a catalogue of specialist diagnostics.

It should begin with phenomena and questions.

A conventional analysis interface might offer:

- phase portrait
- Poincaré section
- Lyapunov exponent
- FFT spectrum
- energy error
- numerical controls

These are useful instruments, but they are not themselves an educational sequence.

The Double Pendulum Explorer should instead lead with questions such as:

1. Is the system deterministic?
2. What happens when two initial states differ by an extremely small amount?
3. How can we measure their separation?
4. Does that separation initially grow exponentially?
5. How can motion be represented in phase space?
6. Can apparently complicated motion contain hidden structure?
7. How do we distinguish physical sensitivity from numerical error?
8. Once we understand the instruments, what can we discover by exploring freely?

The instrument should appear because the learner has developed a reason to need it.

A useful summary of the intended educational language is:

> **derive → simulate → observe → perturb → measure → represent → diagnose → explore**

A complementary content sequence is:

> **phenomenon → question → experiment → visual evidence → mathematical definition → numerical validation**

---

## The central pedagogical tension: deterministic chaos

The chaos material should begin with determinism rather than with the word "chaos."

Given the same equations, parameters, and initial state, the same deterministic model produces the same trajectory.

That provides the conceptual foundation for the surprising experiment that follows:

> What happens if the initial state is changed by an extremely small amount?

Because the existing simulator uses explicit numerical initial conditions, the perturbation can itself be explicit.

For example:

### Pendulum A

$$
\theta_1 = 0^\circ,\qquad \theta_2 = 120^\circ
$$

### Pendulum B

$$
\theta_1 = 0^\circ,\qquad \theta_2 = 120.001^\circ
$$

with the remaining initial conditions identical.

The interface can visually identify the single changed value. This is pedagogically stronger than creating two vaguely nearby states by dragging bobs.

Initially the trajectories may appear indistinguishable. Later they diverge.

The first lesson is therefore not a Lyapunov exponent. It is an observable fact:

> **A tiny difference in initial conditions can eventually produce substantially different trajectories, even though the governing system is deterministic.**

---

## Educational architecture

The following is a conceptual dependency graph rather than a requirement for seven literal pages.

### 1. Determinism

**Question:** Does the same initial state produce the same motion?

**Experience:** Run a trajectory, reset it, and replay the same state.

**Idea introduced:** deterministic evolution.

This establishes the apparent contradiction that makes deterministic chaos interesting.

---

### 2. Sensitivity to initial conditions

**Question:** What happens to nearby initial states?

**Experience:** Run two systems whose initial conditions differ by one explicitly controlled perturbation.

**New representation:** paired/overlaid trajectories.

The learner should know exactly:

- which quantity was perturbed;
- by how much;
- which quantities remained identical.

At first, avoid reducing the result to a single number.

Let the learner see the phenomenon.

---

### 3. Measuring divergence

**Question:** How far apart are the trajectories?

Once visual comparison becomes inadequate, introduce a separation measure:

$$
d(t)
$$

The separation plot should be synchronised with the animation. At a selected playback time, the corresponding pendulum states and point on the separation curve should be visible together.

This continues the existing interaction language of linking physical motion to mathematical representation.

The exact definition of distance is a mathematical/numerical question that must be treated carefully. The educational presentation should only expose a metric once its meaning and limitations are understood.

---

### 4. Exponential growth and Lyapunov ideas

**Question:** The trajectories separate, but how does that separation grow?

Begin with $d(t)$.

Then motivate a logarithmic view.

If, over an appropriate regime,

$$
d(t) \approx d_0 e^{\lambda t},
$$

then

$$
\log d(t) \approx \log d_0 + \lambda t.
$$

The slope now has a reason to exist.

Only after this relationship has been observed and motivated should the term **Lyapunov exponent** be introduced.

The learner should encounter the phenomenon before the statistic.

More sophisticated methods such as finite-time estimates, renormalisation, or the Benettin algorithm should answer problems the learner has already encountered rather than appearing as unexplained expert controls.

---

### 5. Phase space

**Question:** Can we represent motion without putting time on an axis?

The learner already understands quantities such as angle and angular velocity as functions of time.

Start from familiar representations such as:

$$
\theta_1(t),\qquad \omega_1(t).
$$

Then ask what happens if one is plotted against the other:

$$
(\theta_1,\omega_1).
$$

Synchronise a point on the phase portrait with the physical pendulum and time-series plots.

Only then name the representation:

> **phase portrait**

The current Angular State Projection provides a useful precedent for linking state-space representations to the animated system, although configuration-space and phase-space projections should remain conceptually distinct.

---

### 6. Poincaré sections and hidden structure

**Question:** Can complicated motion contain structure that is difficult to see in the full trajectory?

A Poincaré section should be constructed visibly rather than first presented as a finished scatter plot.

For example, choose a section such as

$$
\theta_1 = 0,\qquad \omega_1 > 0.
$$

Explain this operationally:

> Observe the system only when the first arm passes through a chosen angle in a chosen direction.

Each qualifying crossing can visibly add a point to the section.

The learner watches the dataset being created.

Only after several crossings should the term **Poincaré section** become central.

This makes the diagnostic a comprehensible sampling procedure rather than an unexplained cloud of points.

Comparisons between regular and chaotic motion can then emerge naturally from the resulting structure.

---

### 7. Numerical trust

**Question:** Is the observed behaviour physical, or could it be a numerical artefact?

Chaos makes this question especially important because genuine physical sensitivity and numerical error can both produce divergence.

Numerical validation should therefore become part of the physics education rather than remaining hidden implementation detail.

Possible ideas include:

- successful integration;
- finite-state checks;
- conservation of energy for the undamped conservative system;
- relative energy drift;
- sensitivity to solver tolerance;
- convergence under tighter numerical settings;
- reproducibility under an explicitly defined solver policy.

For example, introduce

$$
\frac{|E(t)-E_0|}{|E_0|}
$$

through the question:

> Before interpreting this as chaos, how do we know the numerical simulation itself remains trustworthy?

Avoid presenting an unexplained "PASS" badge as a substitute for understanding. Validation indicators can exist, but the learner should be able to discover what was checked and why.

---

### 8. Exploration

Once the learner has encountered and constructed the major instruments, a denser exploratory environment becomes appropriate.

An advanced view might eventually combine:

- physical trajectory;
- nearby trajectory comparison;
- separation;
- phase portrait;
- Poincaré section;
- Lyapunov estimate;
- energy/numerical diagnostics;
- parameter controls.

The important difference is that the learner has **earned the dashboard**.

None of the panels is mysterious because each instrument has previously been introduced through a question and an experiment.

---

## Progressive disclosure

The page should support increasing levels of sophistication without forcing all users to confront everything at once.

One possible conceptual layering is:

### Observe

See the phenomenon.

Examples:

- deterministic replay;
- nearby trajectories;
- visible divergence.

### Measure

Quantify what was observed.

Examples:

- $d(t)$;
- logarithmic separation;
- growth rate;
- phase-space representation.

### Verify

Interrogate whether the measurement is robust.

Examples:

- perturbation-size dependence;
- fit/convergence behaviour;
- solver tolerance;
- energy drift;
- numerical consistency.

This allows the first encounter to remain approachable while preserving a route into serious numerical dynamics.

---

## Reference projects

These projects are useful references, but none should be copied wholesale. Each represents a different balance between simulation, exploration, analysis, and education.

### MyPhysicsLab — Double Pendulum

Interactive site:

https://www.myphysicslab.com/pendulum/double-pendulum-en.html

**What it does well**

- Makes the physical pendulum immediate and tangible.
- Encourages direct manipulation and experimentation.
- Provides a low barrier to simply seeing the system move.
- Exposes physical and numerical controls in a compact simulation environment.
- Keeps the simulated object itself central.

**What we want to do differently**

The Double Pendulum Explorer deliberately preserves explicit mathematical initial conditions rather than making dragging the primary way of defining a state.

A learner should be able to say:

$$
\theta_2 = 120^\circ
$$

rather than "I dragged the second bob somewhere around here."

This matters especially for chaos, where the difference between $120^\circ$ and $120.001^\circ$ may be the experiment.

The goal is therefore not merely direct manipulation but a transparent connection between the mathematical state introduced in the derivation and the state used by the simulator.

---

### Elliot Jung — Pendulum Lab

Repository:

https://github.com/elliotjung/pendulum-lab

Interactive application:

https://elliotjung.github.io/pendulum-lab/

**What it does well**

- Presents an ambitious browser-based nonlinear-dynamics laboratory.
- Treats the double pendulum as more than an animation.
- Brings together physical simulation and advanced analysis.
- Demonstrates that phase-space analysis, Poincaré sections, Lyapunov analysis, spectra, numerical diagnostics, presets, and rich exploration can coexist in an interactive environment.
- Has a visually polished, research-instrument/workbench identity.
- Provides useful inspiration for what a mature exploratory environment can eventually contain.

**What we want to do differently**

The information density is high. A learner can encounter energy error, a Benettin Lyapunov estimate, a phase portrait, a Poincaré section, a frequency spectrum, physical parameters, numerical controls, ensemble controls, and integrity diagnostics at the same time.

For an experienced nonlinear-dynamics user this can be powerful. For a learner, the immediate questions are:

- Which plot should I look at?
- Why does it matter?
- Where did these points come from?
- What does this number mean?
- Which controls are relevant to the question I am asking?

The Double Pendulum Explorer should therefore borrow the **ambition and instrumentation**, but not the assumption that all instruments should be presented simultaneously.

Instead:

> **The question comes first.**

A Poincaré section should be motivated and constructed.

A Lyapunov exponent should emerge from observed trajectory separation.

An energy diagnostic should answer a question about numerical trust.

The eventual expert/workbench experience can be dense because the learner already understands the instruments.

---

### sihooleebd / emergence

Repository:

https://github.com/sihooleebd/emergence

**What it contributes as a reference**

This project explores sensitivity to initial conditions through large-scale visual structure, including flip-time/fractal-style mappings across initial-condition space.

It is useful inspiration for a later question:

> What happens when we stop comparing only two initial states and explore a whole region of initial-condition space?

**What we want to preserve**

- The visual power of parameter/initial-condition maps.
- The ability to reveal large-scale structure emerging from deterministic dynamics.
- The sense of discovery created by exploring a field of initial states rather than a single trajectory.

**What we want to do differently**

Such maps should come after the learner understands why sensitivity to initial conditions matters and what is actually being measured.

A beautiful fractal should not be used as self-evident proof of chaos.

The quantity mapped, event definition, numerical stopping rule, and interpretation should be explicit.

---

### josmarcristello / Double-Pendulum-Simulation

Repository:

https://github.com/josmarcristello/Double-Pendulum-Simulation

**What it contributes as a reference**

This project is relevant because it treats the double pendulum as a numerical experiment rather than only a visual animation, including investigation of initial conditions and numerical methods.

**What we want to preserve**

- Interest in numerical method dependence.
- Parameter and initial-condition exploration.
- The idea that computational choices themselves are worth investigating.

**What we want to do differently**

Numerical-method comparisons should be introduced through an educational question rather than simply exposed as additional controls.

For example:

> If chaotic trajectories are extremely sensitive, how do we know changing the solver is not changing our physical conclusion?

That turns numerical analysis into part of the conceptual story.

---

### dynamicslab / MultiArm-Pendulum

Repository:

https://github.com/dynamicslab/MultiArm-Pendulum

**What it contributes as a reference**

This sits closer to the research/reproducibility end of the spectrum and is useful as a reminder that chaotic pendulum systems can also be physical experimental systems, benchmark datasets, and objects of system identification/control research.

**Why it matters here**

The Double Pendulum Explorer is not trying to become a research-data platform, but it should retain respect for the distinction between:

- visually plausible behaviour;
- numerically supported behaviour;
- experimentally validated behaviour.

This helps keep educational simplification from becoming scientific overstatement.

---

## Positioning among related projects

A useful spectrum is:

```text
visual toy
    ↓
interactive physics simulator
    ↓
educational chaos explorer
    ↓
numerical experimentation environment
    ↓
research / reproducibility platform
```

The Double Pendulum Explorer should deliberately occupy the **educational chaos explorer** position while allowing motivated learners to look downward into the numerical machinery.

Its distinguishing characteristic should not be that it contains the most diagnostics.

It should be that it makes sophisticated diagnostics understandable.

---

## Design principles

### 1. Questions before instruments

Do not begin a section because a plot is available.

Begin because there is a question worth answering.

---

### 2. Phenomenon before terminology

Let the learner see nearby trajectories diverge before introducing "sensitive dependence on initial conditions."

Let the learner see approximately linear growth in log separation before introducing a Lyapunov exponent.

Let the learner watch crossings generate points before naming a Poincaré section.

---

### 3. Construct representations rather than merely reveal them

Whenever possible, show where plotted data comes from.

A point on a graph should correspond to something observable in the simulated state.

---

### 4. Preserve explicit state

The mathematical initial condition is part of the experiment.

Perturbations should be inspectable, reproducible, and precisely specified.

---

### 5. Synchronise physical and mathematical views

Use shared playback state, highlighted points, cursors, crossing events, or other visual links to show that animations and plots describe the same system.

---

### 6. Progressive disclosure over permanent complexity

Advanced controls and diagnostics can exist without dominating the first encounter.

Complexity should become available as the learner develops the conceptual tools to use it.

---

### 7. Numerical trust is part of the lesson

Do not hide all numerical analysis behind a badge.

Teach why validation matters, especially in a chaotic system.

---

### 8. Avoid visual evidence being mistaken for mathematical proof

Complicated trails, divergence, fractal images, or irregular spectra can motivate investigation but should not automatically be labelled proof of chaos.

Claims should match the diagnostic actually performed.

---

### 9. Do not reduce chaos to a single number

A Lyapunov exponent is powerful, but the educational objective is understanding the phenomenon, measurement, assumptions, and limitations—not merely producing $\lambda_{\max}$.

---

### 10. Exploration should be earned, not forbidden

The goal is not to keep the interface permanently simple.

A rich laboratory/workbench view is desirable once the constituent instruments have been taught.

The final experience can support both:

- guided investigation;
- free exploration.

---

## Candidate content/interaction ideas

These are ideas to explore rather than commitments.

- Deterministic replay of exactly the same initial condition.
- Side-by-side or overlaid nearby trajectories.
- Explicit "change only this parameter" perturbation controls.
- A visual annotation showing the magnitude of the initial perturbation.
- Separation $d(t)$ synchronised with the animation.
- Toggle or transition from $d(t)$ to $\log d(t)$.
- Visual slope interpretation before introducing a Lyapunov estimate.
- Multiple perturbation sizes for convergence/comparison.
- Time-series-to-phase-space animated transformation.
- A phase-space point synchronised with pendulum motion.
- A Poincaré section that visibly acquires one point per qualifying crossing.
- Comparison of regular and chaotic Poincaré structures.
- Energy drift introduced through "Can we trust this simulation?"
- Solver-tolerance experiments framed as scientific questions.
- Later initial-condition/parameter maps inspired by fractal/flip-time explorations.
- Presets chosen for pedagogical contrast rather than merely visual drama.
- An eventual advanced "Explore" or "Workbench" mode containing multiple learned diagnostics.

---

## Content-writing implications

When writing the chaos page, avoid opening with formal definitions or a list of diagnostics.

Prefer a pattern such as:

1. establish something the learner already understands;
2. pose a question;
3. run a controlled experiment;
4. let the learner observe the result;
5. introduce a representation that helps answer the question;
6. name the mathematical concept;
7. explain its limitations;
8. where appropriate, validate it numerically;
9. invite another experiment.

The prose should repeatedly connect equations, controls, animation, and plots.

A diagnostic should never feel as though it arrived from a separate analytics package.

---

## What this page is not

The chaos page is not intended to be:

- a collection of impressive chaotic trails;
- an expert dashboard presented without explanation;
- a catalogue of nonlinear-dynamics terminology;
- a one-click "calculate chaos" tool;
- a claim that visual complexity alone demonstrates chaos;
- a research platform disguised as an introductory educational page;
- a simplified toy that hides every numerical assumption.

It should occupy the space between those extremes.

---

## Working identity

The clearest current statement of identity is:

> **An educational chaos laboratory in which learners build the instruments they later use to explore.**

Or, more explicitly:

> The Double Pendulum Explorer begins with mechanics derived from first principles, turns those mathematical quantities into explicit simulations, and then uses controlled numerical experiments to build an understanding of deterministic chaos. Advanced tools such as trajectory separation, phase portraits, Poincaré sections, Lyapunov analysis, and numerical diagnostics are introduced as answers to questions rather than presented as unexplained instrumentation.

The eventual goal is not simply for the learner to see chaos.

It is for them to understand **how we know what we are seeing**.


----

## Coda: Why the Hamiltonian Matters

So far, the Euler–Lagrange and Hamiltonian formulations have largely been presented as two routes to the same physical motion.

That equivalence is important.

Given the same physical system and initial conditions, both formulations describe the same double pendulum. In the simulator, switching between Euler–Lagrange and Hamiltonian mechanics should therefore not produce a visibly different physical trajectory merely because the formulation has changed.

This establishes an important principle:

> **The physics has not changed. Our description of it has.**

The chaos material provides an opportunity to explain why that change of description is useful.

### From equations of motion to a space of possible motion

The Euler–Lagrange formulation naturally supports the first part of the project's educational story:

> Given the geometry, masses, constraints, and initial conditions, what motion follows?

Starting from

$$
L(q,\dot q,t)=T-V,
$$

the Euler–Lagrange equations

$$
\frac{d}{dt}\frac{\partial L}{\partial\dot q_i}
-\frac{\partial L}{\partial q_i}
=0
$$

produce the equations governing that motion.

The Hamiltonian formulation reorganises the same mechanics around a different mathematical object:

$$
H(q,p).
$$

For the double pendulum, an instantaneous state can be represented using the canonical variables

$$
(\theta_1,\theta_2,p_1,p_2).
$$

Hamilton's equations,

$$
\dot q_i=\frac{\partial H}{\partial p_i},
\qquad
\dot p_i=-\frac{\partial H}{\partial q_i},
$$

then describe a flow through this four-dimensional phase space.

This changes the question we are naturally encouraged to ask.

Instead of only asking:

> **What does this initial state do?**

we can begin asking:

> **What is the structure of the space containing all possible states and trajectories?**

This is where the Hamiltonian formulation becomes especially valuable to the later dynamical-systems material.

### Energy organises phase space

For the conservative double pendulum, fixing the Hamiltonian to a particular energy,

$$
H(\theta_1,\theta_2,p_1,p_2)=E,
$$

restricts the states accessible to a trajectory.

The trajectory does not wander arbitrarily throughout four-dimensional phase space. It remains on a constant-energy hypersurface.

This gives the project a natural reason to return to the Hamiltonian after the simulator:

> **Until now, we used the Hamiltonian to generate the motion. We can now use it to investigate which motions are possible.**

This is an important transition in the educational architecture.

The Hamiltonian ceases to be merely an alternative way of obtaining equations already derived with Euler–Lagrange mechanics. It becomes an object that helps organise and investigate the dynamics.

### From one trajectory to a space of trajectories

The existing simulator is intentionally concerned with precise initial states.

A learner chooses quantities such as

$$
\theta_1,\quad\theta_2,\quad\omega_1,\quad\omega_2
$$

and observes the resulting motion.

The chaos material can progressively change the learner's unit of thought:

```text
ONE STATE
What does this system do?
    ↓
ONE PAIR OF NEARBY STATES
How sensitive is the motion?
    ↓
ONE ENERGY SURFACE
What kinds of motion are available at the same energy?
    ↓
A FAMILY OF INITIAL STATES
Where do different behaviours occur?
    ↓
GLOBAL STRUCTURE
What patterns, boundaries, islands and chaotic regions emerge?
```

Parameter sweeps provide the bridge between thinking about individual trajectories and thinking about a space of possible trajectories.

### Fixed-energy parameter sweeps

A particularly important class of numerical experiment should therefore investigate families of initial conditions constrained by

$$
H(\theta_1,\theta_2,p_1,p_2)=E.
$$

The educational question is not simply:

> What happens when we vary some parameters?

It is more specifically:

> **At this particular total energy, what range of dynamical behaviour exists?**

or:

> **How many different kinds of motion can share the same energy?**

A fixed-energy sweep can systematically construct admissible initial states, integrate their trajectories, measure a clearly defined outcome, and map the resulting structure.

Conceptually:

```text
choose an energy E
        ↓
construct states satisfying H = E
        ↓
sample the admissible state space
        ↓
integrate each initial state
        ↓
measure a defined dynamical quantity
        ↓
map the result
```

Possible measured quantities might eventually include rotation or flip behaviour, first-event times, finite-time divergence measures, trajectory classifications, or other rigorously defined observables.

The diagnostic must determine the interpretation of the map. A visually complicated map should not automatically be labelled a "chaos map."

### Why dimensional reduction becomes necessary

The Hamiltonian description also gives a pedagogical reason for projections, sections, and maps to exist.

The full phase space of the double pendulum has four dimensions:

$$
(\theta_1,\theta_2,p_1,p_2).
$$

We cannot directly display that space on a two-dimensional screen.

Conservation of energy restricts the motion to

$$
H=E,
$$

giving a three-dimensional constant-energy hypersurface within that phase space.

A further section condition can reduce the object again. Schematically, imposing something such as

$$
\theta_1=0
$$

together with an appropriate direction condition produces a two-dimensional section that can actually be visualised.

This provides a natural route toward Poincaré sections.

They need not appear as mysterious specialist scatter plots. They can arise from a concrete problem:

> **Our dynamics live in a space we cannot directly see. How can we construct a lower-dimensional view without throwing away all of its structure?**

This also provides an opportunity to distinguish several objects that can otherwise look superficially similar:

- a **projection** displays selected coordinates while suppressing others;
- an **initial-condition or parameter map** associates members of a family of simulations with measured outcomes;
- a **Poincaré section** records repeated intersections of dynamical trajectories with a precisely defined surface.

The archived exploratory work can inform all three, but these objects should be defined carefully rather than grouped together because they produce compelling scatter plots.

### Precomputed experiments are part of the architecture

High-quality parameter sweeps and long-time chaos diagnostics may be too computationally expensive for good browser UX.

This should not force the numerical experiments to become less rigorous merely so they can run interactively.

Instead:

> **Interactivity belongs in the investigation, not necessarily in the computation.**

The project can maintain a separate computational workflow:

```text
simulation engine
        ↓
experiment / sweep infrastructure
        ↓
validated numerical datasets
        ↓
publication-quality artefacts
        ↓
educational presentation
```

This follows the same principle already used for high-resolution static bifurcation diagrams.

Expensive sweeps can be generated offline at appropriate numerical resolution and then presented as static or precomputed computational artefacts.

The surrounding educational experience can remain interactive.

A learner might:

- zoom into a high-resolution sweep;
- inspect the initial conditions represented by a point;
- compare neighbouring states;
- select representative trajectories;
- move between several precomputed energy levels;
- inspect the quantity used to classify or colour the map;
- reveal numerical methodology and validation information.

There is no requirement that the browser reproduce the expensive computation responsible for the figure.

### Static does not mean pedagogically inert

A high-resolution static figure can sometimes communicate more than a compromised live calculation.

The important distinction is between **computational interactivity** and **educational interactivity**.

A parameter sweep may have taken minutes or hours to generate while the resulting page still lets the learner interrogate:

> What was varied?

> What remained fixed?

> Why are these states comparable?

> What does each point represent?

> What quantity was measured?

> What happens if I select two neighbouring states?

> How do we know the observed structure is numerically trustworthy?

The computation can therefore remain offline while the reasoning remains interactive.

### The formulations are not competitors

The later material should avoid implying that Euler–Lagrange mechanics is a basic formulation while Hamiltonian mechanics is the formulation required for chaos.

They are equivalent formulations of the same mechanics, organised around different mathematical structures and useful perspectives.

The educational distinction is better expressed as a change in the question being asked.

Earlier:

> **Given this physical system and initial state, what motion follows?**

Later:

> **How is the space of possible dynamical states organised?**

The Hamiltonian formulation provides particularly natural language for the second question through canonical phase space, Hamiltonian flow, conserved energy surfaces, and the geometric structure of dynamics.

The formulation selector in the simulator therefore establishes something that becomes important later.

The learner switches from Euler–Lagrange to Hamiltonian mechanics and sees the same pendulum motion.

That is not a disappointing lack of difference.

It demonstrates:

> **Equivalent formulations can describe the same physical trajectory while revealing different mathematical structures.**

The chaos material is where the learner begins to exploit those structures.

### Closing the loop

This creates a longer conceptual arc across the project:

$$
\boxed{\text{Derive the mechanics}}
\longrightarrow
\boxed{\text{Simulate a state}}
\longrightarrow
\boxed{\text{Compare nearby states}}
\longrightarrow
\boxed{\text{Explore phase space}}
\longrightarrow
\boxed{\text{Map families of trajectories}}
$$

The Hamiltonian forms a bridge between simulation and dynamical structure.

The fixed-energy parameter sweep is therefore more than another chaos visualisation. It answers a question created much earlier in the project:

> **Why did we derive a Hamiltonian if Euler–Lagrange mechanics already gave us the motion?**

Because eventually we are no longer interested only in calculating **a motion**.

We want to understand the structure of **the space of possible motion**.
