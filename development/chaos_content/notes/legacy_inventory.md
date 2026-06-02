# Historic Chaos Branch Inventory

Source inspected: `development/chaos_branch/`

This inventory classifies the historic branch by role. It is descriptive, not
an endorsement of correctness.

## Code

- `MathFunctions.py`
  - Symbolic mechanics helpers for simple and compound Lagrangian/Hamiltonian
    systems.
  - Includes energy, moment of inertia, Euler-Lagrange, matrix isolation, and
    Hamiltonian helpers.
  - Needs review before reuse; at least one helper appears stale because
    `derive_canonical_momenta()` assigns the tuple returned by
    `form_lagrangian()` to `L`.

- `AnalysisFunctions.py`
  - Runtime, CPU, memory, integration-step, and tolerance CSV logging.
  - Uses relative output directory `AnalysisData`.
  - Useful conceptually for future cost profiling, but not production-ready.

- `DoublePendulumSubclassData.py`
  - Builds all-angle trajectory dictionaries with `theta1`, `theta2`, `p1`,
    `p2`, `x1`, `y1`, `x2`, and `y2`.
  - Performs Poincare extraction after data collation.
  - Strongly data-collation-driven.

- `DoublePendulumSubclassMomenta.py`
  - Fixed-angle Poincare grid experiments.
  - Uses batch processing and `joblib`.
  - Contains useful Poincare-section intent but ambiguous variable/momentum
    pairing.

- `DoublePendulumSubclassEnsemble.py`
  - Biased/random ensemble experiments.
  - Uses potential-energy filtering to select candidate initial conditions.
  - Logs early termination to CSV and uses large-angle events as compute
    controls.

- `PendulumModels/*.py`
  - Older standalone model copies with plotting and Plotly animation.
  - Should not be imported by new sandbox work.

- `BackUps/*.py`
  - Older snapshots of exploratory subclasses.
  - Treat as stale historical evidence only.

## Content And Data

- `README.md`
  - Historic plan for Chaos page development.
  - Emphasizes subclassing, JSON collation, and eventual database-backed data
    slicing.

- `Notebooks/AnalysisData/*.csv`
  - Solver/resource-cost records for simple and compound models.

- `Notebooks/termination_data/*.csv`
  - Early-termination records produced during ensemble experimentation.

- `JSONdata/`
  - Empty during inspection. Notebooks refer to JSON files that were not
    present.

## Generated Or Exploratory Output

- `Notebooks/*.ipynb`
  - Exploratory notebooks with embedded outputs.
  - Useful as process evidence, not trusted implementation.

- `Images/SimpleReturn.png`
  - Generated simple-model Poincare/return-map style output.

- `Images/CompoundReturn.png`
  - Generated compound-model Poincare/return-map style output.

- `Images/Models_Joint_White.png`
  - Reference model image, likely duplicated from app assets.

## Implicit Assumptions To Revisit

- Dense data collation can substitute for live mathematical computation.
- Poincare plots can be treated as reliable if they look visually plausible.
- Solver tolerance tightening controls chaos-plot noise without a separate
  fidelity contract.
- Early termination patterns can justify excluding angle combinations.
- Maximum potential energy over an angle range is an adequate mechanical-energy
  bound for plot labeling and filtering.
- Random/biased ensembles can be pedagogically meaningful before the section
  and state conventions are fixed.

