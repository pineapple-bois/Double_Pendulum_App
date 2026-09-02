## noah-lowry/double-pendulum — JAX/Diffrax state-space map implementation

**Repository:**  [noah-lowry/double-pendulum - GitHub](https://github.com/noah-lowry/double-pendulum?utm_source=chatgpt.com)  
**License:** MIT

### Why this reference is interesting

This repository is substantially simpler and has different scientific goals,
but it demonstrates an interesting alternative architecture for computing
large double-pendulum state-space maps.

Rather than treating every initial condition as an independently orchestrated
Python task, it expresses the calculation through JAX and Diffrax so that
evaluation across many initial conditions can be transformed into compiled,
batched array computation.

The broad execution model is:

    construct theta1/theta2 grid
        ↓
    scalar dynamical calculation
        ↓
    JAX vectorisation across initial conditions
        ↓
    bounded row batching
        ↓
    Diffrax/JAX compiled execution
        ↓
    large numerical field

The implementation uses nested `jax.vmap` / `jax.lax.map`-style execution and a
Diffrax `Dopri8` integrator. This is conceptually different from the current
project architecture:

    trusted scalar evaluator
        ↓
    independent-cell execution policy
        ↓
    rectangular work units
        ↓
    persistence/resume
        ↓
    authoritative scalar field

### Main implementation lesson

The most relevant idea is **compiled batch evaluation across independent
initial conditions**.

The repository demonstrates that independence between cells does not
necessarily imply one Python-level task or solver invocation per cell. The
array structure can instead be exposed to a compiler/runtime, allowing many
independent trajectories to be evaluated through a batched numerical boundary.

This suggests a possible future investigation for this project:

> Can the already validated finite-time renormalised tangent observable be
> expressed as a genuinely batched compiled calculation over many initial
> conditions while remaining equivalent to the existing scientific oracle?

JAX/Diffrax is one possible implementation technology, but this reference does
not establish that it is the correct choice. A Numba/custom compiled batch
boundary or another approach could implement the same architectural idea.

### Scientific differences

The repository's Lyapunov calculation should **not** be treated as a scientific
reference for this project.

Its approach uses separation between two independently evolved nearby
trajectories, based primarily on angular separation, rather than the validated
renormalised tangent observable used here.

Notable differences include:

- no Candidate-A full-state metric;
- no angular-velocity contribution to the perturbation norm;
- no repeated tangent renormalisation;
- no tangent/JVP evolution;
- independently evolved nearby trajectories;
- perturbation scale coupled to map resolution;
- a simpler finite-shadow/log-separation interpretation.

These differences make the implementation suitable as an architectural
reference, but not as a replacement for the project's established Lyapunov
contract.

### Periodic-domain difference

The reference constructs its angular grid using an inclusive `linspace` from
`-pi` to `+pi`.

For periodic angular coordinates this includes two representations of the same
physical boundary state.

The current project's canonical

    [-pi, pi)

half-open convention remains preferable for authoritative state-space fields.

### Relationship to the current map pipeline

This reference does **not** invalidate the execution/tile/persistence work
already being developed.

A future architecture could instead separate *what constitutes work* from
*how its cells are numerically evaluated*:

    rectangular work unit
            │
            ▼
    collection of initial states
            │
       ┌────┴────┐
       ▼         ▼
    process     compiled
    workers     batch evaluator
       │         │
       └────┬────┘
            ▼
       same tile result
            │
            ▼
       persistence

The tile boundary therefore remains useful even if the numerical execution
strategy is later replaced.

### Relevance to the 12000 × 12000 destination

The reference is especially notable because it targets a `12000 × 12000`
state-space calculation while remaining comparatively small in implementation.

Its simplicity comes partly from delegating vectorisation and batching to
JAX/Diffrax and partly from having a much narrower scientific/data-management
contract. It does not demonstrate the same requirements around numerical
oracle equivalence, per-cell status semantics, failure isolation, deterministic
retry, provenance, persistence, or authoritative restartable fields.

### Takeaway

Keep this repository as an **implementation/architecture reference rather than
a scientific reference**.

The particularly valuable idea is:

> A scalar observable does not necessarily require scalar Python
> orchestration. Independent initial conditions may be evaluated through a
> compiled batch boundary.

Do not interrupt the current tile/persistence sequence to adopt this approach.
If later throughput evidence shows that Python/process-level scalar execution
has reached its useful ceiling, this repository provides a useful precedent
for a dedicated **compiled batch-evaluator experiment**.