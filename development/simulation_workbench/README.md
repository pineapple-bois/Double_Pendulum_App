# Simulation Manifesto and Workbench

This directory governs Phase 6: the evidence-led redesign of the live
`/simulation` page.

The simulation page is the product surface. This workbench is not a detached
sandbox outside the app, and it is not another Phase 5 styling pass. Phase 5D.1
cleared the old documentation-style introduction from `/simulation`; Phase 6
now decides what deserves to occupy that workspace.

The purpose of this workbench is to answer, with evidence:

- what should the Simulation page show?
- how should the Simulation page behave before, during, and after a run?
- what numerical evidence is required before an output can be trusted?
- what rendering and callback costs are acceptable?
- which ideas should be accepted, rejected, deferred, or promoted?

## File structure

The workbench root is the manifesto and index area. Tier-specific artifacts
belong in tier directories so the evidence trail can scale without turning this
directory into a flat archive.

Current structure:

```text
development/simulation_workbench/
├── README.md
├── tier_0/
│   └── INVENTORY.md
├── tier_1/
│   ├── README.md
│   ├── TIER_1_RESULT_CONTRACT.md
│   ├── TIER_1_NUMERICAL_BASELINE.md
│   ├── TIER_1B_SOLVER_METADATA.md
│   ├── TIER_1C_HAMILTONIAN_CONVENTION.md
│   ├── TIER_1D_OPTION_1_HAMILTONIAN_CONVERSION.md
│   ├── TIER_1_CLOSEOUT.md
│   ├── tier1_baseline.py
│   ├── tier1_baseline_results.json
│   ├── tier1c_hamiltonian_convention.py
│   └── tier1c_hamiltonian_convention_results.json
├── tier_2/
│   ├── README.md
│   ├── TIER_2_OUTPUT_COMPOSITION.md
│   ├── OUTPUT_DECISIONS.md
│   ├── workspace_preview_app.py
│   ├── output_composition.py
│   ├── tier2_metrics.py
│   └── tier2_preview_results.json
├── tier_3/
    ├── README.md
    ├── TIER_3_ROADMAP.md
    ├── tier_3a_animation_lifecycle/
    ├── tier_3b_plotly_strategies/
    ├── tier_3c_canvas_feasibility/
    ├── tier_3d_interaction_contract/
    └── tier_3e_renderer_decision/
└── tier_4_production_promotion/
    ├── README.md
    ├── TIER_4_PROMOTION_CLEANUP.md
    ├── ACCEPTED_DECISIONS.md
    ├── API_TIGHTENING_REQUIREMENTS.md
    ├── PRODUCTION_TASK_A_PAYLOAD_API.md
    ├── PRODUCTION_TASK_B_CANVAS_INTEGRATION.md
    ├── PRODUCTION_TEST_PLAN.md
    └── ROLLBACK_AND_DEFERRED_WORK.md
```

File-management rule: new notes, scripts, and compact evidence files should
live under the directory for their tier, such as `tier_1/` or `tier_2/`. Keep
only cross-tier manifesto, index, and operating-rule material at the workbench
root.

## Core manifesto

`/simulation` is the core interactive instrument of the app.

It is not a documentation page. It is not a gallery of attractive plots. It is
not a dumping ground for every historical graph the app once rendered.

A simulation output earns its place only if it improves at least one of:

- interpretability;
- numerical trust;
- interaction quality;
- rendering performance;
- maintainability.

Visual appeal is not enough. A plot, animation, diagnostic, or interaction must
answer a useful question and must state the numerical and performance evidence
needed to trust it.

## Relationship to the app

This workbench may directly shape the live `/simulation` page once a tier is
accepted. The separation here is not product separation; it is decision and
evidence separation.

Until a tier is accepted:

- keep exploratory code and notes easy to identify;
- document assumptions and known failures;
- avoid silently changing unrelated app behavior;
- do not make production app code depend on unstable workbench modules;
- preserve existing callback-bound component IDs unless the task explicitly
  updates all dependent layout and callback references together.

When a tier is accepted, write a promotion plan. Promotion is the documented
step where a workbench decision becomes part of the default `/simulation`
experience.

## Working rules

Before editing, read:

- `AGENTS.md`;
- `README.md`;
- `ROADMAP.md`;
- this file.

For every workbench task:

- check `git status --short` before editing;
- keep changes scoped to the named tier or promotion task;
- document what was inspected;
- document what was changed;
- document metrics gathered, even when the result is inconclusive;
- run the relevant tests;
- for UI-facing work, perform a browser smoke check when practical;
- make unknowns explicit rather than smoothing over them.

## Tier model

Tiers are independent enough to review on their own. A later tier may depend on
an accepted earlier decision, but it should not silently inherit assumptions
from an unaccepted experiment.

### Tier 0: Manifesto and inventory

Goal: establish the facts before designing outputs.

Inspect and document:

- current `/simulation` layout;
- control groups and component IDs;
- callback inputs, outputs, states, and callback-bound IDs;
- current graph/output targets;
- current plotting helpers;
- current `DoublePendulum` model classes;
- validation paths;
- existing tests;
- known numerical evidence gaps;
- known rendering/performance risks.

Expected artifacts:

- `tier_0/INVENTORY.md`;
- a list of callback/component IDs that must be preserved or intentionally
  migrated;
- a list of existing outputs and whether they are accepted, provisional,
  historical, or unknown.

### Tier 1: Numerical trust baseline and result contract foundations

Goal: define what a simulation run must expose before deciding what to render.

Candidate result-contract fields:

- model type;
- system/formulation type;
- gravity setting;
- masses and lengths;
- initial angles and angular velocities or momenta, as appropriate;
- time interval and sample settings;
- solver method and tolerances;
- solver success/failure status;
- runtime and integration metadata;
- time array;
- state arrays;
- position arrays;
- energy arrays where validated;
- warnings and validation flags.

Initial evidence baseline:

- output shape checks;
- finite-value checks;
- monotonic time checks;
- deterministic repeat-run checks;
- initial-condition consistency checks;
- solver status and failure reporting;
- energy or drift checks where the formula and regime are appropriate;
- Lagrangian/Hamiltonian comparison only where the state definitions make the
  comparison meaningful.

Expected artifacts:

- result-contract notes or prototype object;
- numerical baseline report;
- explicit list of quantities that are trusted, untrusted, or not yet audited.

Tier 1 also established the accepted user-facing initial-condition convention:
`theta1`, `theta2`, `omega1`, `omega2`. Hamiltonian simulations convert those
angular velocities to canonical momenta before solving.

### Tier 2: First output composition preview

Goal: test a coherent post-run Simulation workspace, not isolated eye-candy.

Candidate outputs may include:

- physical motion or animation;
- time-series views;
- state/output projections;
- run summary;
- numerical diagnostics;
- useful empty state before the first run;
- validation/failure state after invalid input or solver failure.

Each candidate must answer:

- what question does this output answer?
- what data does it require?
- what could mislead the user?
- what numerical evidence is required?
- what rendering/callback cost does it introduce?
- should it be accepted, rejected, deferred, or revised?

### Tier 3: Animation, Canvas renderer, interaction lifecycle, and renderer decision

Goal: measure expensive or fragile interaction ideas before accepting them.

Candidate experiments may include:

- animation frame strategy;
- play/pause/reset;
- scrubber behavior;
- compare/clear/rerun behavior;
- clientside update paths if Dash/Plotly redraws are too expensive.

Record:

- time to first useful visual;
- figure-build time;
- callback latency;
- Plotly JSON size;
- trace count;
- point count;
- frame count;
- responsiveness across repeated runs;
- any browser or memory degradation observed.

Accepted Tier 3 direction:

- Canvas is the preferred production candidate for physical motion and synced
  selected-time inspection.
- Python owns all mathematical and numerical truth.
- JavaScript owns rendering and playback/inspection state only.
- Plotly remains available as fallback or richer future analytical inspection.
- Reduced-frame Plotly animation should not be promoted as the main UX.
- The Tier 3D event matrix is the lifecycle authority.

### Moved out of this workbench: comparison and chaos bridge

The previous Tier 4 comparison/chaos bridge is cancelled from this workbench
sequence and moved to a future development branch to be defined later.

The idea remains valuable, but it introduces distinct scientific and
pedagogical questions:

- side-by-side runs;
- perturbation controls;
- separation-over-time diagnostics;
- tolerance or solver-method comparison;
- energy-drift comparison;
- bridges to future chaos modules.

These are not prerequisites for promoting the accepted Canvas renderer
direction.

### Tier 4: Production promotion package, API hardening plan, and final workbench cleanup

Goal: turn accepted workbench decisions into maintainable production behavior.

The Tier 4 promotion package should state:

- what user problem the accepted tier solves;
- which files will change;
- which component IDs and callbacks are affected;
- which code remains workbench-only;
- which code moves into `app/` or `src/double_pendulum/`;
- which tests must be added or updated;
- which browser smoke checks are required;
- which numerical assumptions are trusted;
- which limitations remain documented;
- how to roll back or defer if the promoted path fails.

Tier 4 splits the production implementation into two tasks:

- Production Task A: Python Canvas payload API and tests.
- Production Task B: Canvas renderer integration into `/simulation`.

## Candidate output decision record

Use this shape for each proposed output or interaction:

```markdown
## Candidate: <name>

Question answered:

Required data:

Numerical assumptions:

Rendering/callback risks:

User-experience risks:

Metrics to gather:

Evidence gathered:

Decision:
Accepted / rejected / deferred / revise.

Promotion notes:
```

## Evidence metrics

Prefer measured evidence over subjective impressions.

Numerical evidence:

- shape and finite-value behavior;
- initial-condition consistency;
- deterministic repeatability;
- solver status;
- tolerance sensitivity;
- energy or drift behavior where appropriate;
- representative trajectory sanity checks;
- documented failure modes.

Rendering evidence:

- integration time;
- figure-build time;
- callback latency;
- Plotly payload size;
- trace count;
- point count;
- animation frame count;
- time to first useful visual;
- responsiveness after repeated runs.

Interpretability evidence:

- the output answers a clear user question;
- the output is understandable in the Simulation page context;
- limitations are visible or documented;
- the output does not overclaim what the numerics or projection can show.

Maintainability evidence:

- code ownership is clear;
- dependencies are justified;
- callback complexity is contained;
- tests cover promoted behavior;
- production code does not import unstable workbench modules.

## Current recommended next tasks

Tier 0 through Tier 3 now provide the evidence trail for Canvas promotion.

The next production work should follow Tier 4:

1. Implement Production Task A: Python Canvas payload API and tests.
2. Implement Production Task B: Canvas renderer integration into `/simulation`
   using the tested payload API and Tier 3D lifecycle contract.

Comparison and chaos bridge work is intentionally deferred to a future
development branch. It should not block the Canvas renderer promotion path.
