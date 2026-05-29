# Tier 3 Roadmap — Animation, Interaction, and Renderer Strategy

Path: `development/simulation_workbench/tier_3/TIER_3_ROADMAP.md`

## Purpose

Tier 3 investigates the expensive and fragile parts of the future Simulation workspace:

- physical motion rendering;
- animation lifecycle;
- play, pause, reset, and scrub behavior;
- stale-state prevention;
- interaction between motion and plots;
- rendering payload and browser responsiveness;
- whether Plotly remains suitable for animation;
- whether a JS Canvas renderer should be considered, with Python retaining all mathematical authority.

Tier 3 is not a production redesign task.

Tier 3 is not a chaos task.

Tier 3 is not an energy-validation task.

Tier 3 should produce runnable, inspectable workbench experiments and clear renderer/interactivity decisions before anything is promoted into the production `/simulation` page.

## Core Doctrine

Animation is not accepted because it looks smooth.

Animation is accepted only if it:

- remains tied to the correct simulation result;
- can be cancelled or reset reliably;
- does not continue after the simulation result is superseded;
- has measured payload and rendering cost;
- exposes or preserves relevant numerical warnings;
- does not hide solver failure or stale state;
- has a maintainable implementation path.

The physical motion view is emotionally important, but it is also high risk because it can look authoritative even when the underlying state, renderer lifecycle, or numerical evidence is incomplete.

## Tier 3 Starting Point

Tier 1 established a baseline of numerical sanity for representative runs, solver metadata capture, and the accepted user-facing initial-condition convention.

Tier 2 established a coherent first-pass output composition:

- empty state;
- run summary;
- numerical diagnostics;
- physical motion or animation;
- time series;
- angular state projection;
- failure or invalid state.

Tier 3 now focuses specifically on whether the motion and interaction layer can be trusted, measured, and promoted.

## Known Bug To Investigate

There is a known Plotly animation lifecycle bug:

If a Plotly animation is playing, then the user changes model or simulation state, the old animation may continue for the remaining queued playback time before the new state fully takes over.

This is a trust issue.

Expected behavior:

- a new run cancels any old animation immediately;
- clear/reset cancels any old animation immediately;
- failure states do not allow old successful animations to keep playing;
- changed inputs either mark the output stale or prevent stale playback;
- no visual state should continue animating after its simulation result has been superseded.

Tier 3A starts here.

## Directory Structure

Use one directory per Tier 3 sub-tier.

Target structure:

development/simulation_workbench/tier_3/
- TIER_3_ROADMAP.md
- README.md
- tier_3a_animation_lifecycle/
  - README.md
  - TIER_3A_ANIMATION_LIFECYCLE.md
  - animation_lifecycle_preview.py
  - tier3a_results.json
- tier_3b_plotly_strategies/
  - README.md
  - TIER_3B_PLOTLY_STRATEGIES.md
  - plotly_strategy_preview.py
  - tier3b_results.json
- tier_3c_canvas_feasibility/
  - README.md
  - TIER_3C_CANVAS_FEASIBILITY.md
  - canvas_motion_preview.py
  - assets/
  - tier3c_results.json
- tier_3d_interaction_contract/
  - README.md
  - TIER_3D_INTERACTION_CONTRACT.md
  - interaction_contract_preview.py
  - tier3d_results.json
- tier_3e_renderer_decision/
  - README.md
  - TIER_3E_RENDERER_DECISION.md
  - PROMOTION_PLAN.md

The root Tier 3 directory is for the roadmap and index only.

Each sub-tier directory should contain its own scripts, reports, compact results, and README.

Do not allow Tier 3 root to become a dumping ground for experiment files.

## Shared Rules For All Tier 3 Work

All Tier 3 experiments must obey these rules:

- keep workbench experiments under `development/simulation_workbench/tier_3/`;
- do not redesign the production `/simulation` route;
- do not modify production callbacks unless a later promotion task explicitly allows it;
- do not change production component IDs;
- do not change model mathematics;
- do not change solver defaults;
- do not add energy diagnostics;
- do not add chaos diagnostics;
- do not add Poincare sections;
- do not save screenshots, large arrays, full Plotly JSON, or Plotly HTML dumps;
- keep generated JSON compact;
- document every known limitation;
- record metrics rather than relying on subjective impressions.

If a sub-tier needs to touch production code to test a hypothesis, stop and write that as a future promotion task instead.

## Shared Metrics

Where relevant, each sub-tier should record:

- time to first useful visual;
- model construction time, if measured;
- output composition time;
- figure build time;
- callback latency, if applicable;
- Plotly JSON size;
- trace count;
- point count;
- frame count;
- browser responsiveness across repeated runs;
- stale-playback behavior;
- clear/reset behavior;
- rerun behavior;
- memory or responsiveness degradation observed manually;
- implementation complexity;
- production promotion risk.

Metrics should distinguish between:

- Python model/integration time;
- figure construction time;
- Dash callback time;
- browser playback/rendering behavior;
- subjective responsiveness observations.

## Technical Options Under Evaluation

Tier 3 should compare these options where useful:

### Plotly frames

Strengths:

- already exists;
- built-in animation controls;
- easy to integrate with existing figures.

Risks:

- frame payload can grow quickly;
- queued animation state may survive result replacement;
- cancellation/reset behavior may be hard to control;
- browser memory behavior may degrade over repeated runs.

### Reduced-frame Plotly animation

Strengths:

- lower payload;
- easy variation of current approach.

Risks:

- less smooth;
- may still inherit Plotly lifecycle problems.

### Plotly static motion view plus scrubber

Strengths:

- safer and more inspectable;
- less hidden playback state;
- user controls time explicitly;
- lower animation lifecycle risk.

Risks:

- less emotionally engaging;
- may feel less like a simulation.

### Plotly clientside trace update

Strengths:

- Python computes truth once;
- browser updates only visible motion state;
- may avoid full figure replacement.

Risks:

- custom JavaScript complexity;
- still tied to Plotly rendering behavior;
- lifecycle must still be designed carefully.

### Dash server interval

Strengths:

- simple Python-controlled mental model.

Risks:

- server roundtrips are likely wrong for smooth animation;
- latency may be unacceptable;
- unnecessary load for a simple two-bob renderer.

### JS Canvas renderer

Strengths:

- strong control over play, pause, reset, scrub, and cancellation;
- efficient for repeatedly drawing two rods and two bobs;
- smaller payload than Plotly frames may be possible;
- renderer state can be keyed by run ID or animation epoch;
- Python can retain all mathematical authority.

Risks:

- custom JavaScript maintenance;
- more complex Dash integration;
- testing and debugging burden;
- accessibility/export limitations;
- risk of divergence if the data contract is sloppy.

### Hybrid Plotly plus Canvas

Likely long-term candidate:

- Plotly for time series, projections, diagnostics, hover, zoom, and analytical views;
- Canvas for physical motion playback.

This should not be assumed. It must be earned by Tier 3 evidence.

## Python And JavaScript Responsibility Boundary

If Canvas or clientside rendering is explored, the responsibility boundary must be explicit.

Python owns:

- model construction;
- numerical integration;
- solver metadata;
- validation state;
- bob position arrays;
- time arrays;
- warnings;
- run identity;
- any future mathematical diagnostics.

JavaScript may own:

- drawing rods and bobs;
- drawing trails if supplied with approved data;
- play;
- pause;
- reset;
- scrub;
- frame stepping;
- speed control;
- cancelling stale animation when run identity changes.

JavaScript must not own:

- equations of motion;
- numerical integration;
- physical correctness;
- hidden state transformations;
- scientific claims.

## Tier 3A — Animation Lifecycle And Stale Playback

Directory:

development/simulation_workbench/tier_3/tier_3a_animation_lifecycle/

Goal:

Reproduce, document, and measure the current Plotly animation lifecycle problem.

Tier 3A should answer:

- can the stale-playback bug be reproduced reliably?
- when does old animation continue after state changes?
- what user actions trigger stale playback?
- can Plotly frames be cancelled or reset safely?
- does changing `uirevision`, graph key, figure identity, or frame content affect stale playback?
- does clear/reset stop old animation?
- does a failure-state preview stop old animation?
- is the current Plotly animation lifecycle safe enough to patch?

Required experiment states:

- play animation, then rerun same request;
- play animation, then switch model type;
- play animation, then switch system type;
- play animation, then switch initial-condition preset;
- play animation, then clear/reset;
- play animation, then trigger a failure/invalid preview;
- rapidly repeat runs.

Deliverables:

- `README.md`
- `animation_lifecycle_preview.py`
- `TIER_3A_ANIMATION_LIFECYCLE.md`
- `tier3a_results.json`

Acceptance criteria:

- the known stale-playback bug is either reproduced or explicitly not reproduced with notes;
- observed lifecycle behavior is documented;
- candidate mitigation strategies are listed;
- metrics are recorded compactly;
- no production code is changed;
- Tier 3A recommends whether to proceed to Plotly strategy comparison, Canvas feasibility, or both.

## Tier 3B — Plotly Animation Strategy Comparison

Directory:

development/simulation_workbench/tier_3/tier_3b_plotly_strategies/

Goal:

Compare Plotly-based strategies for physical motion display.

Tier 3B should test:

- current Plotly frames;
- reduced-frame Plotly frames;
- static physical view plus scrubber;
- selected-frame updates;
- clientside Plotly trace update if feasible without excessive complexity.

Tier 3B should answer:

- which Plotly strategy has the smallest safe payload?
- which strategy gives the clearest user interaction?
- which strategy cancels or resets most reliably?
- does any Plotly strategy avoid stale queued playback?
- does Plotly remain credible for production motion rendering?
- what frame count or sample count appears reasonable?

Suggested test cases:

- short run;
- moderate run;
- larger sample count;
- simple Lagrangian;
- compound Hamiltonian;
- at least one nonzero angular-velocity preset.

Deliverables:

- `README.md`
- `plotly_strategy_preview.py`
- `TIER_3B_PLOTLY_STRATEGIES.md`
- `tier3b_results.json`

Acceptance criteria:

- at least two Plotly strategies are compared;
- build time, JSON size, trace count, point count, and frame count are recorded;
- cancellation/reset behavior is observed;
- repeated-run behavior is observed;
- recommendation is made on whether Plotly should remain a production candidate for physical motion.

## Tier 3C — Canvas Feasibility Spike

Directory:

development/simulation_workbench/tier_3/tier_3c_canvas_feasibility/

Goal:

Test whether a JS Canvas renderer is a better fit for physical motion playback, while Python remains the sole source of mathematical truth.

Tier 3C should answer:

- can Python-generated bob positions drive a simple Canvas renderer?
- can Canvas provide reliable play, pause, reset, and scrub behavior?
- can Canvas cancel stale playback when run identity changes?
- is the payload smaller or lifecycle cleaner than Plotly frames?
- does Canvas reduce browser responsiveness issues?
- what integration and maintenance costs would Canvas introduce?

Minimum Canvas behavior:

- draw two rods and two bobs;
- use Python-computed position arrays;
- support play;
- support pause;
- support reset;
- support scrub or frame selection;
- visibly stop old playback when a new run ID appears;
- display basic runtime/rendering state.

Canvas must not compute equations or integrate trajectories.

Deliverables:

- `README.md`
- `canvas_motion_preview.py`
- `assets/`, if needed for workbench-only JavaScript
- `TIER_3C_CANVAS_FEASIBILITY.md`
- `tier3c_results.json`

Acceptance criteria:

- Canvas renders Python-computed positions;
- play/pause/reset/scrub behavior is demonstrated or limitations are documented;
- stale-run cancellation is tested;
- payload and responsiveness are compared against Plotly evidence;
- maintenance risks are documented;
- recommendation is made on whether Canvas should become a production candidate.

## Tier 3D — Interaction Contract And State Synchronisation

Directory:

development/simulation_workbench/tier_3/tier_3d_interaction_contract/

Goal:

Define the interaction lifecycle for the future Simulation workspace.

Tier 3D should answer:

- what happens when a new run starts?
- what happens when a run completes?
- what happens when a run fails?
- what happens when inputs change after a successful run?
- what happens when the user clears outputs?
- what happens when the animation is playing during any of the above?
- should outputs be marked stale when inputs change?
- should plots preserve zoom or reset after rerun?
- should animation time sync with time-series hover or cursor state?
- should scrubbing update a state readout?
- should comparison runs exist in the same interaction model or be deferred?

Tier 3D should introduce or specify:

- run identity;
- animation epoch;
- stale output state;
- active run state;
- failure state;
- cleared state;
- selected time/frame state;
- reset behavior.

Deliverables:

- `README.md`
- `interaction_contract_preview.py`
- `TIER_3D_INTERACTION_CONTRACT.md`
- `tier3d_results.json`

Acceptance criteria:

- lifecycle states are explicitly documented;
- expected behavior is defined for run, rerun, clear, failure, input change, play, pause, reset, and scrub;
- stale-state prevention is specified;
- sync behavior between motion and plots is accepted, revised, deferred, or rejected;
- nearby-initial-condition comparison is either scoped carefully or deferred;
- no production callback changes are made.

## Tier 3E — Renderer Decision And Promotion Plan

Directory:

development/simulation_workbench/tier_3/tier_3e_renderer_decision/

Goal:

Close Tier 3 by recommending the renderer and interaction strategy for production promotion.

Tier 3E should synthesize evidence from Tier 3A through Tier 3D.

Possible decisions:

- keep and patch Plotly frames;
- use reduced Plotly frames;
- use Plotly static view plus scrubber;
- use Plotly clientside trace updates;
- use Canvas for physical motion and Plotly for analytical plots;
- defer animation promotion and ship static motion first;
- reject an approach due to lifecycle, payload, or maintenance risk.

Deliverables:

- `README.md`
- `TIER_3E_RENDERER_DECISION.md`
- `PROMOTION_PLAN.md`

The renderer decision should include:

- recommended renderer;
- rejected alternatives;
- evidence summary;
- lifecycle behavior;
- payload summary;
- responsiveness summary;
- implementation complexity;
- testing requirements;
- production risks;
- required callback/state changes;
- required CSS/layout changes;
- whether the solution is ready for production promotion.

The promotion plan should include:

- files likely to change;
- component IDs likely to be needed;
- callback changes likely to be needed;
- tests that must be added;
- manual browser checks required;
- rollback plan;
- known limitations;
- user-facing language requirements.

Acceptance criteria:

- Tier 3 evidence is synthesized;
- a clear renderer recommendation exists;
- production promotion is either recommended, deferred, or rejected;
- next implementation task is scoped;
- unresolved risks are documented honestly.

## Suggested Sequencing

Tier 3 should proceed in this order:

1. Tier 3A — Animation lifecycle and stale playback.
2. Tier 3B — Plotly strategy comparison.
3. Tier 3C — Canvas feasibility spike.
4. Tier 3D — Interaction contract.
5. Tier 3E — Renderer decision and promotion plan.

Tier 3A should happen first because the known stale-playback bug may change how Plotly strategies are evaluated.

Tier 3C should not be skipped if Tier 3A or Tier 3B confirms that Plotly lifecycle control is fragile.

Tier 3D should wait until renderer capabilities are better understood.

Tier 3E should not begin until at least Tier 3A and either Tier 3B or Tier 3C have produced evidence.

## What Is Out Of Scope For Tier 3

Tier 3 should not attempt:

- energy validation;
- energy drift plots;
- Lyapunov exponents;
- Poincare sections;
- chaos teaching modules;
- nearby-initial-condition comparison as a default feature;
- final production layout polish;
- full `/simulation` route migration;
- full browser performance automation;
- long-duration scientific validation.

Nearby-initial-condition comparison may be discussed in Tier 3D, but should probably remain deferred unless the renderer architecture makes it safe and cheap.

## Tier 3 Closeout Requirements

Tier 3 is complete only when:

- the stale animation lifecycle issue has been investigated;
- Plotly animation strategies have been measured or explicitly rejected;
- Canvas feasibility has been tested or explicitly deferred with justification;
- the motion interaction lifecycle has been specified;
- a renderer decision exists;
- a production promotion plan exists;
- unresolved risks are documented;
- no accepted decision relies only on visual appeal.

The final Tier 3 closeout should state:

- what renderer strategy is recommended;
- what interaction model is recommended;
- what should be promoted to production;
- what should remain workbench-only;
- what must be tested before promotion;
- what remains unknown.