# Chaos Prototype Architecture Anchor

## Purpose

This document records the evolving architectural and pedagogical
direction of the double-pendulum chaos work. Its earlier sections preserve
the reasoning that guided the first prototype; later sections record the
stronger boundaries earned by the validated reference observable, 1-D sweep,
and 2-D reference grid.

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

A possible isolated structure considered before implementation was:

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

This structure was deliberately provisional. The completed prototype did not
need the proposed `chaos_core/` package tree. The implementation instead grew
as one cohesive Lyapunov strand, and only after repeated sweep/grid evaluation
demonstrated cross-observable pressure was one shared state-space-field module
earned. This is an example of the intended rule: the architecture follows
verified use rather than a speculative target tree.

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

The bounded 1-D and 2-D prototype workloads have now exercised the first part
of this route. A validated `9 x 9` reference field retained ordered axes,
scalar values, per-cell validity, numerical diagnostics, persistence, and
rendering provenance. Runtime scaled approximately linearly with cell count.
That evidence now justifies separating observable evaluation from domain
sampling; it does not yet justify implementing the later high-resolution
layers.

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

The completed reference grid earned the reference-versus-compiled question.
The first Numba augmented-RHS path has now passed bounded pointwise
equivalence, but that does not replace the reference path. The NumPy/SciPy
implementation remains the scientific oracle. A compiled evaluator must keep
passing explicit pointwise and field-level equivalence tests before performance
comparisons can affect execution architecture.

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

# 19. Historical immediate software milestone

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

That milestone is now complete. The Lyapunov strand progressed from the local
teaching reference through a one-vector fixed-horizon observable, a bounded
1-D sweep, and a bounded 2-D reference grid. The provisional label
“Prototype 001” was not adopted as a self-contained mini-project; the code
instead remains a growing Lyapunov scientific strand with shared machinery
extracted only where repeated use has earned it.

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

# 22. Architecture earned by the reference sweep and grid

The completed Lyapunov strand supplied evidence that was unavailable when the
earlier map architecture was deliberately deferred:

- a trusted single-condition NumPy/SciPy reference calculation;
- a fixed-horizon scalar observable with explicit numerical validity;
- a bounded 1-D sampling strategy;
- a bounded rectangular 2-D sampling strategy;
- an authoritative saved scalar field and a separately rendered heatmap;
- measured approximately linear repeated-evaluation cost.

The first 2-D implementation also exposed a concrete defect: a rectangular
grid cell was represented by wrapping a coordinate-specific 1-D
`Theta1SweepSample`, and the grid was executed as a collection of theta1
sweeps. That was useful scaffolding, but it confused two peer sampling
strategies with a scientific hierarchy.

The smallest earned correction is now:

``` text
scientific observable specification
        |
        v
observable-specific evaluator
        |
        v
coordinate-neutral scalar evaluation outcome
        |
        +-------------------+
        |                   |
        v                   v
explicit-axis        explicit-axis
  1-D sampling       rectangular 2-D sampling
```

The shared outcome records a value, validity state, lightweight diagnostics,
elapsed evaluation time, evaluator identity, and bounded numerical-error
details. The same small module supplies named ordered axes and reference
line/rectangle sampling records. Rectangle arrays use explicit y rows and x
columns. None of these types knows whether the scalar is tangent stretching,
first-flip time, flip count, or another future observable. Scientific
specification, coordinate-to-state substitution, and diagnostic types remain
owned by the observable.

The outcome vocabulary is deliberately small: completed-valid,
completed-invalid, and execution-error. Sampling catches no exceptions. Each
observable adapter may translate only its explicitly bounded numerical
failures into execution-error data; programming and specification defects must
propagate.

This boundary is implemented minimally in
`development/chaos_content/prototypes/state_space_fields.py`. The Lyapunov
strand owns an adapter from its rich reference result to that neutral outcome.
No inheritance hierarchy, plugin registry, or generic N-dimensional runner is
needed.

# 23. Reference and compiled evaluator boundary

Sampling must depend on an observable evaluator contract, not directly on one
integration implementation:

``` text
observable specification
         |
         +-------------------------+
         |                         |
         v                         v
NumPy/SciPy reference       validated compiled evaluator
         |                         |
         +---- equivalence tests --+
                       |
                       v
             shared sampling strategies
```

The current NumPy/SciPy path remains authoritative. Its equations, Jacobian,
Candidate-A geometry, renormalisation semantics, signed logarithmic
accumulation, horizon, and validity policy must not be changed merely to ease
compilation.

A compiled implementation may use a different internal representation, but it
must accept the same scientific specification in all relevant respects and
produce an equivalent scalar evaluation outcome. The first Numba path meets
that requirement over its declared pointwise validation set. Bounded compiled
field evaluation is the next separate apparatus test before compiled execution
is used for larger field generation.

Wall-clock duration is provenance, not part of scientific equivalence. A
compiled path may have a one-time compilation or setup cost. The equivalence
task should report that cost separately from warmed per-evaluation timing so a
cold first call cannot be confused with steady field throughput.

# 24. Periodic angular-domain and resolution contract

The physical angular configuration space is periodic. A full angular axis uses
the canonical half-open representation

$$
[-\pi,\pi).
$$

For $N$ samples, coordinates are

$$
\theta_k
=
-\pi+\frac{2\pi k}{N},
\qquad
k=0,\ldots,N-1.
$$

The endpoint $+\pi$ is excluded because it represents the same physical angle
as $-\pi$. Including both would duplicate a row or column and distort periodic
field semantics.

Use `samples`, `samples_per_axis`, and `resolution`, not the ambiguous term
“steps”. A periodic two-angle domain declares independent resolutions:

``` python
PeriodicAngularDomain(theta1_samples=32, theta2_samples=48)
PeriodicAngularDomain.square(samples_per_axis=32)
```

The human-facing resolution order is
`(theta1_samples, theta2_samples)`. A scalar field stored with theta2 rows and
theta1 columns has array shape
`(theta2_samples, theta1_samples)` and convention

``` text
values[theta2_index, theta1_index].
```

Thus `32 x 32` and a future `12000 x 12000` identify the same mathematical
domain with different discretisations. The current bounded degree-based grid
is preserved for its validated reference fixtures; it can also be constructed
from the canonical periodic domain without introducing the duplicate endpoint.

# 25. Cross-observable state-space-field direction

Observable definition and domain sampling are separate responsibilities.
Finite-time tangent stretching is the first consumer, not the definition of a
state-space field.

Future first-flip-time or flip-count observables may reuse the neutral outcome,
periodic domain, status vocabulary, array orientation, and later execution or
storage layers where their own scientific contracts permit. They should not
reuse Lyapunov specifications, diagnostics, or tangent machinery.

The intended direction is now:

``` text
scientific contracts and reference evaluators
        |
        v
validated compiled equivalents
        |
        v
domains and sampling strategies
        |
        v
tile planning and execution
        |
        v
persistent numerical fields
        |
        v
renderers
        |
        v
possible production derivatives
```

Only the reference-evaluator, neutral-outcome, bounded-sampling, small JSON
field, and renderer portions exist today. The remaining boxes are direction,
not implemented architecture.

# 26. Numerical fields and rendering

The persisted numerical scalar field is the authoritative scientific artifact.
It must retain explicit axes, value/status arrays, observable and numerical
provenance, and enough validity information to interpret missing or rejected
values.

PNG, PDF, TIFF, or other visual outputs are derivatives. Changing a colormap,
normalisation, label, or output format must not require recomputing the
dynamics. Renderers consume persisted numerical fields; evaluators do not
depend on renderers.

The current small JSON artifact demonstrates this separation for reference
grids. JSON is not proposed as the format for large maps.

# 27. Persistent storage direction

Large scalar fields will require chunked persistent storage, but selecting or
implementing that backend is premature in the current reference pass.

For local scientific storage, HDF5 is the leading candidate because it offers
mature multidimensional arrays, chunking, compression, metadata, and local
tooling. This is not a frozen choice. Zarr remains a viable alternative if
later execution becomes naturally distributed, chunk-object-oriented, or
object-store based.

The eventual storage boundary must keep observable evaluators independent of
the backend. Neither HDF5 nor Zarr belongs inside the scientific calculation.
No dependency on either format should be introduced until a concrete storage
prototype and comparison are in scope.

# 28. Large-field and tile-oriented execution direction

A possible destination of approximately

$$
12000\times12000=144{,}000{,}000
$$

initial conditions changes execution and storage constraints, but it does not
change the mathematical domain or observable definition.

Execution at that scale is expected to become tile-oriented so later machinery
can support:

- bounded memory;
- resumability;
- progress accounting;
- retries and failure isolation;
- parallel execution;
- tile-level validation and provenance;
- rendering independently from persisted fields.

No tile planner or executor is implemented yet. The present reference grids
appropriately retain rich Python objects per evaluation for inspection. A
144-million-cell field must not. Large storage will instead require compact,
aligned value and status arrays plus aggregate or tile-level diagnostics and
provenance.

# 29. Scientific storage and production delivery

Scientific storage and production delivery are separate problems. Scientific
work may need axes, scalar values, statuses, provenance, and diagnostic data.
Production may ultimately consume only generated visual assets derived from
that field.

Interactive delivery of underlying scalar data remains possible, but it is not
currently a requirement. Production APIs, asset formats, caching, and UI
integration should therefore not dictate scientific field storage prematurely.

# 30. Current boundary and next earned question

The architecture now includes a first validated compiled equivalent of the
finite-time tangent observable. It compiles the explicit Euler--Lagrange flow
and exact Jacobian-vector product with Numba, then reuses the reference SciPy
DOP853 integration, Candidate-A renormalisation, diagnostics, and result
driver. A mechanically declared five-condition center-plus-corners set agrees
pointwise with the NumPy/SymPy/SciPy oracle inside predeclared tolerances, and
the compiled evaluator composes with the existing rectangular sampler.

This is evidence for the evaluator seam, not yet for a final large-field
engine. The architecture currently stops at pointwise compiled-RHS evaluation,
small reference sampling, JSON field persistence, and diagnostic rendering.
It deliberately does not include:

- a wholly compiled integrator or batch kernel;
- batch or tile executors;
- multiprocessing or GPU execution;
- HDF5 or Zarr storage;
- resumable large-map orchestration;
- additional observables;
- production integration.

The next earned task is a bounded compiled batch/grid apparatus test. It
should measure how much Python/SciPy per-cell orchestration remains visible and
whether a compiled integration/batch boundary is needed before designing tile
execution. Tiling remains a later seam: pointwise speedup alone does not yet
earn scheduling, resumability, or persistent chunk-storage machinery.
