# Phase 10 Chaos Branch Discovery Report

Date: 2026-06-02

Scope: inspect `development/chaos_branch/` as historic reference material and
prepare a clean Phase 10 sandbox under `development/chaos_content/`.

## Executive Summary

The historic chaos branch contains useful exploratory ideas for a Chaos page,
especially Poincare return maps, initial-condition ensembles, resource-cost
tracking, and termination analysis. It should not be treated as trusted
implementation.

The dominant direction was data collation: generate large grids or ensembles of
Hamiltonian double-pendulum runs, store trajectory arrays or termination data,
then analyze and plot the resulting records. The work does not provide enough
mathematical fidelity evidence to promote any chaos metric, Poincare plot,
termination filter, dataset, or API into production.

No production routing, callbacks, layouts, app assets, or live UI were changed.
No legacy code was copied wholesale into this sandbox.

## What Was Found

The historic branch is about 10 MB and contains Python modules, notebooks, CSV
artifacts, images, backups, and an empty JSON output directory.

### Top-Level Files

| Path | Type | Notes |
| --- | --- | --- |
| `README.md` | project notes | Describes a Chaos page plan based on subclasses, JSON data, and possibly a PostgreSQL database. |
| `.gitattributes` | repo metadata | LF normalization only. |
| `MathFunctions.py` | symbolic mechanics code | Standalone symbolic helpers for Lagrangian and Hamiltonian systems. Duplicates/extends older model derivation logic. |
| `AnalysisFunctions.py` | resource-cost utility | Writes solver runtime, CPU, memory, and integration-step data to CSV. |
| `DoublePendulumSubclassData.py` | exploratory code | Builds trajectory dictionaries with angles, momenta, and positions; includes Poincare extraction. |
| `DoublePendulumSubclassMomenta.py` | exploratory code | Main fixed-angle Poincare-grid experiment using batches and `joblib`. |
| `DoublePendulumSubclassEnsemble.py` | exploratory code | Random/biased ensemble experiment with termination logging and Poincare extraction. |

### Model Copies

| Path | Type | Notes |
| --- | --- | --- |
| `PendulumModels/DoublePendulumLagrangian.py` | copied model code | Standalone Lagrangian class with plotting and Plotly animation helpers. |
| `PendulumModels/DoublePendulumHamiltonian.py` | copied model code | Standalone Hamiltonian class with plotting and Plotly animation helpers. |

These files appear to be older standalone model copies, not current production
architecture. They mix symbolic derivation, numerical solving, plotting, and
animation in one layer.

### Backups

| Path | Type | Notes |
| --- | --- | --- |
| `BackUps/DoublePendulumSubclass.py` | backup code | Older explorer implementation. |
| `BackUps/DoublePendulumSubclassEnergy.py` | backup code | Energy-focused variant. |
| `BackUps/DoublePendulumSubclassEnsemble.py` | backup code | Earlier ensemble variant. |
| `BackUps/DoublePendulumSubclassMomenta.py` | backup code | Earlier momenta/Poincare variant. |

These are historical snapshots. They should be treated as stale even relative
to the top-level chaos-branch code.

### Notebooks

| Path | Type | Notes |
| --- | --- | --- |
| `Notebooks/DevelopmentSubClass.ipynb` | exploratory notebook | Builds data dictionaries, converts NumPy arrays to JSON-serializable lists, writes JSON outputs, and tests plots. |
| `Notebooks/JSONTest.ipynb` | exploratory notebook | Reads expected JSON trajectory dictionaries into Pandas dataframes. |
| `Notebooks/PoincareSections.ipynb` | generated/exploratory notebook | Fixed-angle Poincare section experiments. Contains extensive embedded outputs. |
| `Notebooks/PoincareEnsemble.ipynb` | generated/exploratory notebook | Ensemble Poincare experiments with random/biased initial-condition sampling. Contains embedded outputs. |
| `Notebooks/DataAnalysisNBs/ResourceDataAnalysis.ipynb` | analysis notebook | Reads resource-cost CSVs and plots compute-cost summaries. |
| `Notebooks/DataAnalysisNBs/TerminationDataAnalysis.ipynb` | analysis notebook | Reads termination CSVs, extracts angles, visualizes termination times, and proposes heuristic exclusions. |

The notebooks are useful evidence of exploratory thinking, but many outputs are
embedded and the code references changing module names and relative paths.

### Data Artifacts

| Path | Rows | Notes |
| --- | ---: | --- |
| `Notebooks/AnalysisData/simulation_data_simple_1.csv` | 720 | Runtime/CPU/memory/step-count records for simple-model runs. |
| `Notebooks/AnalysisData/simulation_data_compound_1.csv` | 720 | Runtime/CPU/memory/step-count records for compound-model runs. |
| `Notebooks/termination_data/raw_termination_data.csv` | 372 | Early-termination records. |
| `Notebooks/termination_data/raw_termination_data_two.csv` | 1793 | Early-termination records. |
| `Notebooks/termination_data/raw_termination_data_three.csv` | 256 | Early-termination records. |
| `Notebooks/termination_data/older_data/*.csv` | 443-472 each | Older termination records. |

All termination CSVs inspected recorded `Large deviation` as the termination
reason. These are not validated chaos datasets.

### Images

| Path | Type | Notes |
| --- | --- | --- |
| `Images/Models_Joint_White.png` | reference image | Duplicate/reference pendulum model image. |
| `Images/SimpleReturn.png` | generated output | Historic simple-model return-map image. |
| `Images/CompoundReturn.png` | generated output | Historic compound-model return-map image. |

The generated images are output evidence only. They are not proof of
mathematical correctness.

### Empty Output Directory

`JSONdata/` exists but was empty during this inspection. Notebook code expects
`simple_data.json` and `compound_data.json`, so historic JSON outputs were
either never generated in this copy, intentionally excluded, or removed.

## Useful Ideas

- A Chaos page could teach initial-condition sensitivity through carefully
  scoped Poincare sections and ensemble comparisons.
- The separation between fixed-angle sweeps and random/biased ensembles is a
  useful research distinction.
- Resource-cost and termination data can inform interactive limits, but only
  after the numerical problem definition is validated.
- The notebooks contain useful questions about solver tolerance, runtime, and
  noise accumulation.
- A future sandbox experiment could begin with a small, deterministic,
  self-contained Poincare extraction routine and a known reference trajectory.

## Unsafe, Stale, Or Unclear Material

- The historic README explicitly proposes precomputing and hosting large
  trajectory data in a database so the app can query slices instead of deriving
  and integrating on demand. That is a data-delivery architecture, not a
  mathematical validation strategy.
- JSON trajectory collation stores angles, momenta, and positions without an
  attached solver contract, energy-drift audit, event definition, schema
  version, or fidelity threshold.
- Several modules duplicate older pendulum model implementations and plotting
  helpers instead of using the current production architecture.
- Notebook code refers to older module names and call signatures, including
  names not present in the inspected tree.
- Resource analysis appends CSVs using relative paths such as `AnalysisData`,
  which would depend on the current working directory.
- Termination analysis converts observed termination patterns into heuristic
  angle exclusions. Those filters optimize computation, but they are not
  mathematically justified as chaos-domain boundaries.
- Early termination uses a "large deviation" angle threshold that changed in
  comments and code. One implementation comments "Allow 15 loops" while the
  code uses `2 * (2 * np.pi)`.
- Failed or terminated runs may be padded with zeros or left as uninitialized
  array rows, which can pollute later Poincare extraction and plotting.
- Some code casts Poincare points to `float32`, reducing precision without a
  stated error budget.
- Several methods print status/debug output directly and combine simulation,
  analysis, plotting, and persistence in one class.

## Mathematical And Numerical Fidelity Concerns

These areas require review before any production use:

- Hamiltonian state convention: confirm that trajectory columns are always
  `(theta1, theta2, p_theta1, p_theta2)` and that labels/plots use the
  corresponding conjugate momentum.
- Poincare section definition: define the section, crossing direction,
  interpolation method, accepted state variables, and whether crossings through
  zero must be direction-filtered.
- Momentum pairing: some code appears to mix crossing variables and plotted
  momentum variables. For example, ensemble extraction for a `theta1` crossing
  sets the other variable to `theta2` but uses `p_theta1` as the stored
  momentum, while the plot labels imply `p_theta2`.
- Fixed-angle naming: in `DoublePendulumSubclassMomenta.py`, `fixed_angle`
  describes the initial-condition grid, but section detection is performed on
  the other angle. That must be clarified before reuse.
- Mechanical-energy bounds: energy is inferred from maximum potential energy
  over a chosen angle range, rounded to two decimals in one implementation, and
  used as a plotting/filter label. This is not a validated energy contract.
- Solver policy: notebook experiments use tolerances such as `rtol=1e-6` and
  `atol=1e-9` or `1e-8`, sometimes with default solver methods. There is no
  solver-equivalence or tolerance-sensitivity record for chaos diagnostics.
- Event handling: termination by large angle deviation is a computational
  control, not a physical or mathematical conclusion.
- Data completeness: padded zeros, missing failures, embedded notebook output,
  and empty JSON outputs make the artifacts unsuitable as reference datasets.
- Compound model assumptions: compound potential-energy formulas and momenta
  must be cross-checked against current production derivation tests before use.

## UX And Pedagogical Assumptions

- The historic work assumes Poincare return maps are the primary Chaos page
  artifact.
- It assumes precomputed data/database access may be preferable to live
  simulation for interactivity.
- It assumes noisy plots can be improved by longer runs, smaller step size, or
  tighter tolerances, but does not separate visual density from mathematical
  validity.
- It assumes early-termination exclusion zones can make the UX tractable, but
  those zones are derived from observed compute behavior rather than a teaching
  model.
- It assumes `theta_i` angle grids in degrees are intuitive for users, while
  internal data uses radians and canonical momenta.

## What Was Rewritten Into This Sandbox

No executable legacy code was rewritten in this task.

The reusable output of this task is documentation-only:

- this discovery report;
- a legacy inventory;
- a mathematical fidelity question list;
- scaffold directories for future rewritten experiments and references.

This was intentional because the task is discovery and sandboxing only. Any
future code should be written from a clean problem statement instead of copied
from the historic branch.

## What Was Deliberately Not Promoted

- No `/chaos` production routing changes.
- No `app/pages/`, `app/callbacks/`, `src/double_pendulum/`, or
  `assets/styles.css` changes.
- No production imports from `development/chaos_branch/` or
  `development/chaos_content/`.
- No live UI updates.
- No production tests, because no production behavior changed.
- No legacy Poincare image, dataset, metric, solver policy, JSON schema, or
  database architecture was promoted as production-ready.

## Recommended Next Phase 10 Step

Start with a written Chaos page problem statement before implementing UI or
metrics.

Recommended first follow-up:

1. Define the teaching goal for the new Chaos page: qualitative sensitivity,
   Poincare sections, Lyapunov exponents, solver/numerical caution, or a
   sequence that introduces them gradually.
2. Define a minimal mathematical contract for one artifact, preferably a small
   deterministic Poincare-section experiment:
   - model scope: simple Hamiltonian only at first;
   - state convention;
   - section equation and crossing direction;
   - interpolation method;
   - solver method and tolerances;
   - accepted error checks, including energy drift;
   - output schema.
3. Implement that artifact as a self-contained sandbox experiment in
   `development/chaos_content/experiments/`.
4. Validate it against analytic expectations where possible and against a
   high-accuracy reference run where analytic checks are unavailable.
5. Only after the mathematical artifact is reviewed, decide whether it belongs
   in production code, tracked tests, or durable documentation.

