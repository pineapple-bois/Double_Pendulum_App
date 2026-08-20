# Rewritten Experiments

This directory contains Phase 10 experiments and narrowly scoped interaction
prototypes rewritten from clean problem statements. Numerical experiments and
exploratory interactions may inform each other, but both remain sandbox work.

Rules for future code:

- Keep experiments self-contained inside `development/chaos_content/`.
- Do not copy legacy code wholesale from `development/chaos_branch/`.
- Do not import production callbacks, layouts, or assets.
- If production model code is used as read-only reference, document why in the
  experiment README or notes before running the experiment.
- Save generated outputs under a clearly named subdirectory and label them as
  exploratory.
- When an interaction prototype is introduced, state which assumption,
  observable, or learning question it is intended to explore. Do not imply that
  its numerical conventions are accepted merely because they make interaction
  possible.
- Do not present any metric, dataset, plot, or API as production-ready without
  mathematical fidelity review.
- Keep production promotion separate. Production code must not import an
  experiment or prototype from this directory.

## Current Experiments

- `initial_condition_sensitivity/` - fixed-pair and predeclared regime-selection
  evidence for how nearby trajectories evolve from different initial states.
  Its perturbation, duration, threshold, attribution ratio, and binary result
  labels are reproducible experimental choices rather than universal Stage 1
  conventions. High-excitation threshold-crossing cases remain numerically
  unresolved.

- `hamiltonian_poincare/` - a minimal, self-contained simple-Hamiltonian
  Poincare-section experiment with explicit state, section, solver, and
  energy-drift conventions.
