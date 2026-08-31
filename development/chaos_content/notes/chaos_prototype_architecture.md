# Chaos Prototype Architecture Anchor

## Purpose

This document freezes the current architectural and pedagogical
direction for the next stage of the double-pendulum chaos work.

The project is deliberately changing mode from **experiments that answer
scientific questions** toward **purposeful scientific software that
embodies the answers already earned**.

The immediate destination is a small, isolated prototype whose first
pedagogical deliverable connects an intuitive physical measure of
trajectory separation to Lyapunov-style local stretching:

$$
\text{nearby pendulums}
\rightarrow
\text{Cartesian separation}
\rightarrow
\text{full-state separation}
\rightarrow
\text{local tangent stretching}
\rightarrow
\text{finite-time Lyapunov rate}.
$$

Experiments remain the forensic scientific record. Prototype code
becomes the clean implementation of the accepted scientific contracts.
It is not production code yet, but it should establish contracts that
can later be promoted or rewritten deliberately for production.

## 1. First pedagogical deliverable --- Sensitivity to Lyapunov

The first prototype should tell one coherent story.

A learner begins with two double pendulums whose initial conditions
differ by a tiny perturbation. The natural first question is: **how far
apart have the pendulums become?**

The prototype then introduces progressively more appropriate measures as
limitations of the previous measure become visible:

1.  two almost identical physical pendulums;
2.  Cartesian bob separation;
3.  recognition that physical separation is geometrically bounded;
4.  separation in the full dynamical state;
5.  recognition that two finite trajectories cease to represent an
    infinitesimal perturbation;
6.  tangent-space evolution;
7.  logarithmic local stretching;
8.  stretching accumulated per unit time;
9.  finite-time Lyapunov interpretation;
10. later, renormalisation and QR as the systematic extension.

The mathematics should appear because the learner encounters a
limitation, rather than because a Lyapunov exponent is presented
abstractly at the beginning.

## 2. Stage 1 --- Cartesian distance

For a reference trajectory and a nearby trajectory, begin with the
second-bob Cartesian distance

$$
d_{\mathrm{bob}}(t)
=
\left\|
\mathbf r'_2(t)-\mathbf r_2(t)
\right\|.
$$

This is an excellent first observable because its meaning is immediate.

For link lengths $l_1$ and $l_2$, however,

$$
d_{\mathrm{bob}}(t)\leq2(l_1+l_2).
$$

For unit links,

$$
d_{\mathrm{bob}}(t)\leq4.
$$

The boundedness is pedagogically useful. It lets the learner discover
that physical distance is useful for seeing sensitivity but cannot
measure continuing dynamical divergence indefinitely.

## 3. Stage 2 --- full-state distance

The Euler--Lagrange state is

$$
x=(\theta_1,\theta_2,\omega_1,\omega_2).
$$

Use local wrapped angular differences

$$
\Delta\theta_i=
\operatorname{wrap}_{(-\pi,\pi]}(\theta'_i-\theta_i),
$$

and $\Delta\omega_i=\omega'_i-\omega_i$.

Angles and angular velocities should not simply be mixed in an unscaled
Euclidean norm. The accepted Candidate-A convention uses

$$
T_c=\sqrt{\frac{L_c}{g}}
$$

and

$$
d_{\mathrm{state}}
=
\left\|
\begin{pmatrix}
\Delta\theta_1\\
\Delta\theta_2\\
T_c\Delta\omega_1\\
T_c\Delta\omega_2
\end{pmatrix}
\right\|_2,
$$

with

$$
S=\operatorname{diag}(1,1,T_c,T_c).
$$

This convention should be named explicitly in software rather than
buried as anonymous scaling factors. It is a validated working geometry,
not a uniquely ordained state-space distance.

## 4. Stage 3 --- why finite trajectory separation is not enough

Once initially nearby chaotic trajectories become macroscopically
separated,

$$
x'(t)-x(t)
$$

no longer represents an infinitesimal perturbation attached to the
reference trajectory.

That motivates the next question: **how can we continue measuring the
local instability of one reference trajectory after the second
trajectory has wandered away?**

Instead of following one finite perturbation forever, follow an
infinitesimal tangent perturbation governed by

$$
\dot{\delta x}=J(x)\delta x,
$$

where

$$
J(x)=\frac{\partial f}{\partial x}.
$$

This is the conceptual transition from trajectory separation to local
stretching of the flow.

## 5. Stage 4 --- tangent stretching

Track the Candidate-A-scaled norm of a tangent perturbation. Introduce
logarithmic growth as

$$
G(t)
=
\log
\frac{\|\delta x(t)\|}
     {\|\delta x(0)\|}.
$$

The teaching progression becomes

$$
\text{Cartesian distance}
\rightarrow
\text{full-state distance}
\rightarrow
\text{local infinitesimal distance}
\rightarrow
\text{logarithmic stretching}
\rightarrow
\text{stretching per unit time}.
$$

A finite-time rate follows naturally:

$$
\lambda_T
=
\frac{1}{T}
\log
\frac{\|\delta x(T)\|}
     {\|\delta x(0)\|}.
$$

Initially this should be presented as a finite-time stretching or
Lyapunov diagnostic, within the claim boundaries established by the
experiments.

## 6. Stage 5 --- renormalisation and QR

The absolute magnitude of a tangent perturbation is not the important
quantity; accumulated stretching is.

This motivates

$$
\text{evolve}
\rightarrow
\text{measure stretch}
\rightarrow
\text{renormalise}
\rightarrow
\text{evolve}
\rightarrow\cdots
$$

and, for stretch factors $r_k$,

$$
\lambda_T=\frac1T\sum_k\log r_k.
$$

A single tangent vector can introduce the idea. Later, four tangent
vectors can be evolved simultaneously and QR decomposition can maintain
an orthonormal basis while accumulating stretching in multiple
directions.

Thus full-spectrum QR becomes an extension of an already-understood
concept rather than the learner's first encounter with Lyapunov
analysis.

# 7. Prototype architecture

A possible isolated structure is:

``` text
development/chaos_content/
    prototype/
        chaos_core/
            model.py
            state.py
            trajectory.py
            perturbation.py
            observables.py
            tangent.py
            lyapunov.py
            results.py
        demos/
            sensitivity_to_lyapunov.py
        tests/
```

This is intentionally not production code. Its purpose is to discover
and validate a clean scientific API that can later be promoted,
rewritten, optimized, or incorporated into production.

## 8. Prefer small data types and pure functions

Do not begin with a general `DoublePendulumChaosSimulator`,
`ChaosEngine`, `ChaosAnalyzer`, or `SimulationManager`.

Prefer small semantic data structures:

``` python
@dataclass(frozen=True)
class PendulumParameters:
    m1: float
    m2: float
    l1: float
    l2: float
    g: float
```

``` python
@dataclass(frozen=True)
class ELState:
    theta1: float
    theta2: float
    omega1: float
    omega2: float
```

Numerical integration can still use NumPy arrays internally.

> **Dataclasses define semantic boundaries; arrays remain efficient
> numerical representations.**

Prefer pure numerical functions such as:

``` python
rhs(state, params)
cartesian_position(state, params)
cartesian_distance(a, b, params)
candidate_a_distance(a, b, params)
jacobian(state, params)
integrate(...)
finite_time_lyapunov(...)
```

These will be easier to validate, test, compile, batch, and eventually
adapt for high-resolution map generation.

# 9. Separate specification, calculation, and result

Use the architectural flow

$$
\text{specification}
\rightarrow
\text{calculation}
\rightarrow
\text{result}.
$$

Avoid mutable objects that simultaneously configure, execute, store,
analyse, and render simulations.

For example:

``` python
@dataclass(frozen=True)
class SimulationSpec:
    params: PendulumParameters
    initial_state: ELState
    duration: float
    sampling_dt: float
    solver: SolverSpec
```

and

``` python
@dataclass
class Trajectory:
    time: ndarray
    state: ndarray
```

The specification says what should be calculated. The scientific kernel
performs it. The result records what was calculated. Observables and
presentation consume the result.

# 10. `TrajectoryPair` as a pedagogical result

The first lesson concerns one reference trajectory and one nearby
trajectory, so a result structure such as this may be useful:

``` python
@dataclass
class TrajectoryPair:
    time: ndarray
    reference_state: ndarray
    perturbed_state: ndarray
    reference_xy: ndarray
    perturbed_xy: ndarray
    cartesian_distance: ndarray
    state_distance: ndarray
```

It may also carry perturbation, parameters, and solver metadata.

`TrajectoryPair` should represent a result, not become an object
containing all simulation logic.

# 11. Explicit observables

Preserve the conceptual distinction between:

``` text
Physical observables
    Cartesian bob distance
    First-flip time
    Flip count

State-space observables
    Candidate-A state distance

Tangent observables
    Tangent norm
    Log stretch
    Finite-time Lyapunov rate
```

This does not require an inheritance hierarchy. Explicit functions and
result types are preferable initially:

``` python
cartesian_distance(...)
candidate_a_distance(...)
tangent_norm(...)
log_stretch(...)
finite_time_lyapunov(...)
```

The conceptual hierarchy matters more than Python inheritance.

# 12. A small metric object may be justified

One abstraction that may genuinely deserve a class is the state-space
metric:

``` python
metric = CandidateAMetric.from_parameters(params)
```

with operations such as:

``` python
metric.distance(x1, x2)
metric.scale_tangent(delta_x)
metric.scaling_matrix()
```

It has one coherent responsibility: defining the accepted local geometry
used to compare states and tangent perturbations.

# 13. Tangent and Lyapunov result structures

A simple pedagogical tangent result might be:

``` python
@dataclass
class TangentTrace:
    time: ndarray
    norm: ndarray
    log_norm: ndarray
```

A later result might resemble:

``` python
@dataclass
class LyapunovResult:
    time: ndarray
    cumulative_log_growth: ndarray
    finite_time_rate: ndarray
```

The exact structures should be earned through prototype use rather than
frozen prematurely.

# 14. Two computational APIs

## Teaching-level API

``` python
simulate_nearby_pair(...)
cartesian_separation(...)
state_separation(...)
tangent_stretching(...)
finite_time_lyapunov(...)
```

This API is consumed by demonstrations, plots, notebooks, and eventually
UI components. It exposes concepts rather than numerical implementation
details.

## Scientific kernel API

``` python
el_rhs(...)
el_jacobian(...)
integrate_reference(...)
integrate_reference_and_tangent(...)
qr_step(...)
qr_spectrum(...)
```

This layer embodies the mathematics and numerical contracts established
by the experiments.

The teaching API should compose the scientific kernel rather than
duplicate its mathematics.

# 15. First prototype experience

The first purposeful prototype should synchronize four views:

``` text
Double-pendulum motion
        |
        +--- Cartesian bob separation
        |
        +--- Candidate-A state separation
        |
        +--- tangent log stretching
        |
        +--- finite-time Lyapunov estimate
```

The key requirement is that the learner can see **why each new quantity
is introduced**.

The pedagogical questions are:

1.  **Are two almost identical pendulums still close together?** ---
    Cartesian distance.
2.  **Why does that distance stop telling us how much divergence has
    accumulated?** --- expose its geometric bound.
3.  **Can we compare their complete dynamical states instead?** ---
    introduce the dimensionally coherent state metric.
4.  **What happens once the trajectories are no longer nearby?** ---
    finite trajectory difference ceases to represent local instability.
5.  **Can we keep an infinitesimal perturbation attached to one
    trajectory?** --- tangent dynamics.
6.  **How rapidly does that perturbation stretch?** --- logarithmic
    growth and finite-time rate.
7.  **How do we measure this for long periods without enormous
    perturbations?** --- renormalisation.
8.  **Can we measure stretching in every independent direction?** --- QR
    and the Lyapunov spectrum.

This is the pedagogical spine.

# 16. Route toward high-resolution maps

The same architecture should lead naturally toward:

``` text
validated NumPy reference implementation
        ↓
compiled/JIT numerical kernel
        ↓
batch initial-condition evaluator
        ↓
tiled evaluator
        ↓
persistent scalar-field dataset
        ↓
map renderer
        ↓
teaching UI
```

Ideally the map layer asks for an observable at an initial condition:

``` python
value = observable(initial_state)
```

and eventually:

``` python
values = evaluate_grid(initial_conditions)
```

Possible map observables include:

``` text
bob distance after a fixed time
first-flip time
flip count
finite-time stretching
finite-time Lyapunov diagnostic
```

These can share the same initial-condition representation and form
increasingly sophisticated views of the same state-space slice.

# 17. Do not optimize prematurely

Do not initially design the prototype around Numba, multiprocessing, GPU
execution, 12,000 × 12,000 maps, tile schedulers, databases, production
caches, or UI frameworks.

The preferred sequence is

$$
\text{clear reference implementation}
\rightarrow
\text{validation}
\rightarrow
\text{compiled equivalent}
\rightarrow
\text{large-scale evaluation}.
$$

Performance work must not silently redefine the mathematics. A future
compiled kernel should be validated against the clean reference
implementation before becoming the map engine.

# 18. Relationship to production

The prototype should establish durable contracts rather than simply
being copied wholesale into production:

-   parameter representation;
-   state representation;
-   angle conventions;
-   state metric;
-   trajectory representation;
-   perturbation specification;
-   observable definitions;
-   tangent evolution;
-   Lyapunov result semantics;
-   numerical provenance;
-   validation fixtures.

Once these contracts are stable, production code can be designed
deliberately around them.

The prototype acts as a **scientific reference implementation and
architectural proving ground**.

# 19. Immediate software milestone

After the remaining long-time convergence question is closed, begin a
new development strand:

> **Prototype 001 --- Sensitivity to Lyapunov**

Use one reference initial condition and one nearby initial condition to
demonstrate

$$
\boxed{
\text{physical separation}
\rightarrow
\text{state separation}
\rightarrow
\text{tangent stretching}
\rightarrow
\text{finite-time Lyapunov rate}
}
$$

Before substantial implementation, inspect the accepted experimental
machinery and design the minimum `chaos_core` API and data model needed
to express this story.

Do not allow the directory structure or abstractions of the experiments
to become the architecture by accident.

# 20. Architectural principles to preserve

1.  **Experiments are evidence; prototype code is implementation.**
2.  **Complexity is earned by verification.**
3.  **The pedagogy should motivate each abstraction through a limitation
    of the previous one.**
4.  **Prefer explicit scientific concepts over generic software
    abstractions.**
5.  **Prefer small data structures and pure functions over large mutable
    simulator classes.**
6.  **Separate specification, calculation, result, observable, and
    presentation.**
7.  **Make conventions such as Candidate-A geometry visible in the
    API.**
8.  **Keep physical, state-space, and tangent observables conceptually
    distinct.**
9.  **Maintain a clean NumPy reference implementation before
    optimizing.**
10. **Validate future compiled kernels against the reference
    implementation.**
11. **Keep map computation independent of rendering and teaching UI.**
12. **Promote stable contracts into production deliberately rather than
    treating prototype code as production by default.**

# 21. Destination

The longer-term destination is a defensible teaching system in which the
learner moves through increasingly sophisticated descriptions of
double-pendulum chaos:

$$
\text{sensitivity}
\rightarrow
\text{physical consequence}
\rightarrow
\text{state-space separation}
\rightarrow
\text{local stretching}
\rightarrow
\text{Lyapunov analysis}
\rightarrow
\text{Poincaré/state-space structure}
\rightarrow
\text{high-resolution chaos maps}.
$$

The purpose of the next software phase is to make that progression
concrete.

The first step is not to build everything.

It is to build one small prototype in which the path from **Cartesian
distance to Lyapunov stretching feels inevitable**.
