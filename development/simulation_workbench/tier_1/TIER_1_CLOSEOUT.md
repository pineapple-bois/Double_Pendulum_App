# Tier 1 Closeout

Tier: Phase 6 / Simulation Workbench Tier 1
Date: 2026-05-29

## Status

Tier 1 is ready to hand off to Tier 2 output-composition experiments, with
clear limits.

Tier 2 may design candidate Simulation page outputs using the current animation,
time-series, theta-theta projection, solver metadata, and normalized initial
condition convention. Tier 2 should still avoid energy diagnostics and stronger
scientific claims until those receive their own evidence work.

## What Tier 1 Now Proves

Tier 1 supports these claims for the representative baseline cases:

- simple and compound Lagrangian runs construct successfully;
- simple and compound Hamiltonian runs construct successfully;
- time arrays have expected shape, finite values, correct endpoints, and
  monotonic increasing samples;
- state arrays have expected shape and finite values;
- first state rows match internal solver initial states;
- repeated runs are deterministic within the baseline tolerance;
- position precompute returns finite `(4, sample_count)` arrays;
- current animation, time graph, and theta-theta projection methods still build;
- `solve_ivp` metadata is retained compactly;
- the user-facing initial-condition convention is now
  `[theta1, theta2, omega1, omega2]` for both formulations;
- Hamiltonian construction converts UI angular velocities to canonical momenta
  before solving;
- nonzero angular-velocity tests cover simple and compound Hamiltonian
  conversion.

## What Tier 1 Does Not Prove

Tier 1 does not prove:

- full physical correctness of every symbolic equation;
- energy conservation or acceptable energy drift;
- long-duration numerical stability;
- tolerance sensitivity;
- solver-method equivalence;
- chaotic divergence behavior;
- browser memory behavior under repeated runs;
- that the theta-theta projection is a full phase portrait;
- that any new Simulation page output composition is accepted.

## Solver Metadata Change

Tier 1b added compact metadata capture to model instances:

- `solver_metadata`
- `solver_time`

For `solve_ivp`, the metadata includes success, status, message, function
evaluation counts, requested and returned time counts, returned-time matching,
solution shape, and explicit solver kwargs. The full SciPy `OdeResult` is not
stored.

This closes the original Tier 1 gap where the app could render plausible
figures without retaining solver success evidence.

## Hamiltonian Conversion Change

Tier 1C identified that the old behavior was ambiguous for nonzero angular
velocities. Tier 1D implements the accepted convention:

```text
UI request: [theta1, theta2, omega1, omega2]
Hamiltonian solver state: [theta1, theta2, p_theta_1, p_theta_2]
```

Model instances now distinguish:

- user-facing initial conditions in degrees and degrees per second;
- user-facing initial conditions converted to radians and radians per second;
- internal solver state;
- solver-state variable names;
- solver-state convention;
- initial-condition conversion rule.

## Nonzero Evidence

The important nonzero request was:

```text
[45.0, -30.0, 10.0, -5.0]
```

After Tier 1D, both simple and compound Hamiltonian cases report that the
internal momentum tail matches the canonical momenta computed from the
user-facing angular velocities. The compact script evidence records zero max
absolute difference for both nonzero cases.

## Remaining Blockers

Energy diagnostics remain blocked. Runtime energy arrays do not exist, and
energy drift should not be promoted until formulas, state conventions, and
expected regimes are audited for each model/system combination.

Deeper physical validation also remains blocked. The Tier 1 evidence is strong
enough to support output-composition experiments, but not strong enough to make
scientific claims about conservation, chaos metrics, or formulation equivalence
beyond the tested initial-condition conversion.

## Tier 2 Handoff

Tier 2 should focus on the first coherent post-run Simulation workspace. It can
use:

- current animation output;
- current time-series output;
- current theta-theta projection, labelled carefully as a projection;
- solver metadata;
- user-facing and internal initial-condition records;
- warnings or diagnostics only where backed by Tier 1 evidence.

Tier 2 should not add energy plots, chaos diagnostics, or strong validation
language without a new evidence task.
