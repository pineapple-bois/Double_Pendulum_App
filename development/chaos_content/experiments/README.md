# Chronological Experiment Index

This directory contains Phase 10 mathematical experiments rewritten from clean
problem statements. Narrowly scoped teaching prototypes live separately under
`../prototypes/`; numerical experiments and exploratory interactions may inform
each other, but both remain sandbox work.

Numbered directory prefixes record **experiment chronology**: the order in
which questions were investigated in this sandbox. They do not record the
current Chaos teaching order, maturity, validity, acceptance, or importance. A
larger number is only a later address, not a stronger result.

The chronology intentionally preserves historical truth. Experiment 001 is the
Hamiltonian Poincare investigation because it happened first, even though the
current conceptual journey places Poincare sections after sensitivity and
Lyapunov analysis.

Rules for future code:

- Keep experiments self-contained inside `development/chaos_content/`.
- Do not copy legacy code wholesale from `development/chaos_branch/`.
- Do not import production callbacks, layouts, or assets.
- If production model code is used as read-only reference, document why in the
  experiment README or notes before running the experiment.
- Save generated outputs under the ignored `development/chaos_content/outputs/`
  tree and label them as exploratory.
- When an interaction prototype is introduced, state which assumption,
  observable, or learning question it is intended to explore. Do not imply that
  its numerical conventions are accepted merely because they make interaction
  possible.
- Do not present any metric, dataset, plot, or API as production-ready without
  mathematical fidelity review.
- Keep production promotion separate. Production code must not import an
  experiment or prototype from this directory.

## Directory Convention

Each numbered experiment should ordinarily own a `README.md` plus only the
implementation, tests, static plotting code, and local fixtures required to
reproduce that investigation. Its README is the authoritative working record
for its question, definition, minimal experiment, numerical validity, static
inspection, acceptance, findings, and next justified experiment.

Use a small human-readable status such as `exploratory`, `active`, `accepted
for limited claim`, `superseded`, or `deferred`. Do not infer status from the
directory number. Generated diagnostics do not belong in experiment source
directories unless a local README records a specific exception.

## Experiment Chronology

- `001_hamiltonian_poincare/` - the chronologically first executable Phase 10
  artifact: a minimal, self-contained simple-Hamiltonian Poincare-section
  experiment with explicit state, section, solver, and energy-drift
  conventions. Status: exploratory prior work.

- `002_initial_condition_sensitivity/` - fixed-pair and predeclared regime-selection
  evidence for how nearby trajectories evolve from different initial states.
  Its perturbation, duration, threshold, attribution ratio, and binary result
  labels are reproducible experimental choices rather than universal Stage 1
  conventions. Status: accepted for a limited close-over-this-interval claim;
  high-excitation threshold-crossing cases remain numerically unresolved. The
  teaching prototype under `../prototypes/initial_condition_sensitivity/` is a
  derived Experiment 002 interaction, not a third mathematical experiment.

- `003_lyapunov_distance_contract/` - compares two explicit, dimensionally
  coherent Euler–Lagrange/Cartesian full-state distances with the bounded
  second-bob display observable, including controlled perturbation, tolerance,
  sampling, and scaling checks. Status: accepted for distance-convention
  findings; no growth rate or exponent estimated.

- `004_finite_time_exponential_growth/` - audits whether the Experiment 003
  nearby-state growth contains a reproducible approximately exponential finite
  interval. Candidate A remains primary and Candidate B a robustness check;
  interval selection and provisional thresholds are predeclared. Lifted angles
  and signed revolutions are retained separately as global history diagnostics.
  Status: completed with a valid rejection—no defensible common interval under
  the predeclared rule; no Lyapunov exponent or renormalisation implemented.

- `005_renormalised_local_stretching/` - repeatedly restores the scaled
  Candidate-A perturbation magnitude while retaining its evolved direction and
  accumulating all signed cycle stretching. The uninterrupted reference and
  reset algorithmic shadow have distinct energy/history semantics. Status:
  completed with an accepted negative result—the baseline reset mechanism is
  valid, but accumulated rates do not stabilise robustly under the predeclared
  duration, magnitude, interval, and tolerance checks; no maximal Lyapunov
  exponent accepted.
