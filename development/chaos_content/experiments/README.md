# Rewritten Experiments

This directory is reserved for future Phase 10 experiments rewritten from a
clean problem statement.

Rules for future code:

- Keep experiments self-contained inside `development/chaos_content/`.
- Do not copy legacy code wholesale from `development/chaos_branch/`.
- Do not import production callbacks, layouts, or assets.
- If production model code is used as read-only reference, document why in the
  experiment README or notes before running the experiment.
- Save generated outputs under a clearly named subdirectory and label them as
  exploratory.
- Do not present any metric, dataset, plot, or API as production-ready without
  mathematical fidelity review.

## Current Experiments

- `hamiltonian_poincare/` - a minimal, self-contained simple-Hamiltonian
  Poincare-section experiment with explicit state, section, solver, and
  energy-drift conventions.

