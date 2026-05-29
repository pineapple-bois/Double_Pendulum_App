# Simulation Workbench Inventory

Tier: Phase 6 / Tier 0
Date: 2026-05-29
Scope: inspection and documentation only

This inventory records the current state of the live `/simulation` workflow
before designing new Simulation Workbench outputs. It reflects the repository as
inspected on 2026-05-29 and treats `development/simulation_workbench/README.md`
as the Phase 6 manifesto.

No production Dash code, callbacks, model classes, plotting helpers, styles, or
tests were modified for this inventory.

## Files inspected

- `AGENTS.md`
- `README.md`
- `ROADMAP.md`
- `development/simulation_workbench/README.md`
- `pendulum_app.py`
- `app/pages/simulation.py`
- `app/components/simulation_controls.py`
- `app/components/graphs.py`
- `app/components/footer.py`
- `app/components/figure_style.py`
- `app/content/simulation.py`
- `app/callbacks/simulation.py`
- `app/callbacks/routing.py`
- `src/double_pendulum/models/lagrangian.py`
- `src/double_pendulum/models/hamiltonian.py`
- `src/double_pendulum/math/functions.py`
- `src/double_pendulum/plotting/helpers.py`
- `src/double_pendulum/validation/inputs.py`
- `src/double_pendulum/validation/dash.py`
- `tests/numerical/test_models.py`
- `tests/unit/test_derivation_fidelity.py`
- `tests/unit/test_validation.py`
- `tests/unit/test_components.py`
- `tests/unit/test_app_content.py`
- `tests/integration/test_app_import.py`
- `tests/integration/test_compatibility_imports.py`
- `assets/styles.css` for current layout/display behavior only

## 1. Current simulation page structure

The live `/simulation` route resolves through `app/pages/registry.py` to
`app/pages/simulation.py`. The route-level layout is defined by
`app/pages/simulation.py::layout()`. The main workspace is built by
`get_main_content()` with:

- `id="scroll-target"` on the `html.Main` workspace.
- `className="simulation-workspace"`.
- A primary grid container with `className="simulation-workspace-primary content-container"`.
- A left control rail from `build_simulation_controls()`.
- A main output area with `className="simulation-output-workspace"`.
- The simulation-specific footer from `get_footer_section_main()`, which owns
  the current run button.

Major layout regions:

- Shared page header from `get_header_section(current_path="/simulation")`.
- Body wrapper from `get_body_section()`.
- Simulation workspace main region.
- Left sidebar control rail with `className="side-bar"`.
- Output workspace containing animation/phase and time-graph sections.
- Footer wrapper containing the footer-anchored Run Simulation button and
  repository attribution.

Current control groups rendered:

- Information popup:
  - `info-popup`
  - `close-info-button`
  - `info-button`
- Model and system selection:
  - `model-type`
  - `system-type`
  - `g-label`
  - `param_g`
- Physical parameters:
  - `unity-parameters`
  - `lengths-label`
  - `param_l1`
  - `param_l2`
  - `masses-label`
  - `param_m1`
  - `param_m2`
  - `param_M1`
  - `param_M2`
- Initial conditions:
  - `init_cond_theta1`
  - `init_cond_theta2`
  - `init_cond_omega1`
  - `init_cond_omega2`
- Simulation interval:
  - `time_start`
  - `time_end`

Current defaults:

- `model-type`: `simple`
- `system-type`: `lagrangian`
- `param_g`: `9.81`
- `time_start`: `0`
- `time_end`: `20`
- Mass and length inputs have placeholders but no initial values until the user
  enters values or clicks `unity-parameters`.
- `param_M1` and `param_M2` are initially rendered with `style={"display": "none"}`.

Current empty/main workspace behavior:

- The animation/phase container is present in the layout but hidden by
  `style={"display": "none"}` on `animation-phase-container`.
- The time graph section and inner container are present but hidden by
  `style={"display": "none"}` on both `time-graph-section` and
  `time-graph-container`.
- Empty `dcc.Graph` components exist before a run for `pendulum-animation`,
  `phase-graph`, and `time-graph`.
- There is no explicit pre-run explanatory empty state in the output workspace.
  The page visually opens into controls plus an empty white output area.
- `error-message` is present inside the animation/phase loading region and is
  updated by validation callbacks.

Current footer Run Simulation behavior:

- The Run Simulation button is in `app/components/footer.py`, not inside the
  main control rail.
- It has `id="submit-val"` and `className="button run-simulation-button"`.
- `submit-val.n_clicks` is the only input to the main simulation callback.
- The footer layout is still part of the simulation workflow, so moving or
  removing it later would require callback migration.

Existing graph/output containers and component IDs:

- `loading-animation-phase`: `dcc.Loading` wrapper for animation/phase and errors.
- `animation-phase-container`: hidden/shown style target containing:
  - `pendulum-animation`
  - `phase-graph`
- `time-graph-section`: hidden/shown style target for the time graph band.
- `time-graph-container`: hidden/shown style target containing:
  - `time-graph`
- `error-message`: validation/failure display target.

Callback-sensitive IDs to preserve unless intentionally migrated:

- Run and display:
  - `submit-val`
  - `time-graph`
  - `phase-graph`
  - `pendulum-animation`
  - `animation-phase-container`
  - `time-graph-container`
  - `time-graph-section`
  - `error-message`
- Controls:
  - `model-type`
  - `system-type`
  - `param_g`
  - `param_l1`
  - `param_l2`
  - `param_m1`
  - `param_m2`
  - `param_M1`
  - `param_M2`
  - `init_cond_theta1`
  - `init_cond_theta2`
  - `init_cond_omega1`
  - `init_cond_omega2`
  - `time_start`
  - `time_end`
  - `unity-parameters`
  - `info-popup`
  - `info-button`
  - `close-info-button`

Other app-shell IDs that matter to the route:

- `url`
- `page-content`
- `trigger-js`
- `update-state` exists in the top-level app layout but is not used by the
  simulation callbacks inspected in this pass.
- `scroll-target` is present in `/simulation`; assets include scroll behavior
  around the run button, but that JavaScript was not changed in this task.

## 2. Current callback flow

All simulation-specific callbacks are registered by
`app/callbacks/simulation.py::register_simulation_callbacks(app)`, which is
called from `pendulum_app.py` after app construction.

### Information popup callback

Responds to:

- `info-button.n_clicks`
- `close-info-button.n_clicks`

Consumes state:

- `info-popup.style`
- `info-button.n_clicks`

Updates:

- `info-popup.style`
- `info-button.children`
- `info-button.n_clicks`

Notes:

- Uses `dash.callback_context` to infer which button fired.
- The close button increments `info-button.n_clicks` to keep the toggle state
  aligned.

### Unity parameter callback

Responds to:

- `unity-parameters.n_clicks`

Updates:

- `param_l1.value`
- `param_l2.value`
- `param_m1.value`
- `param_m2.value`
- `param_M1.value`
- `param_M2.value`
- `param_g.value`

Behavior:

- After the button has been clicked, sets all lengths and masses to `1` and
  gravity to `9.81`.
- Before a click, returns `dash.no_update`.

### Model-parameter visibility callback

Responds to:

- `model-type.value`

Updates:

- `param_m1.style`
- `param_m2.style`
- `param_M1.style`
- `param_M2.style`

Behavior:

- `simple`: shows `param_m1` and `param_m2`; hides `param_M1` and `param_M2`.
- `compound`: hides `param_m1` and `param_m2`; shows `param_M1` and `param_M2`.

### Input-change clearing and validation callback

Responds to changes in all simulation inputs:

- `init_cond_theta1.value`
- `init_cond_theta2.value`
- `init_cond_omega1.value`
- `init_cond_omega2.value`
- `time_start.value`
- `time_end.value`
- `param_l1.value`
- `param_l2.value`
- `param_m1.value`
- `param_m2.value`
- `param_M1.value`
- `param_M2.value`
- `param_g.value`
- `model-type.value`
- `system-type.value`

Consumes state:

- `error-message.children`

Updates, all with `allow_duplicate=True`:

- `time-graph.figure`
- `phase-graph.figure`
- `pendulum-animation.figure`
- `animation-phase-container.style`
- `time-graph-container.style`
- `time-graph-section.style`
- `error-message.children`

Behavior:

- Calls `validate_inputs(...)`.
- If the validation message is unchanged, raises `PreventUpdate`.
- If invalid, clears all figures to empty `go.Figure()` instances, hides all
  graph containers, and displays validation errors.
- If valid, still returns empty figures and hidden graph containers. This means
  any edit after a successful run clears the visible outputs until the user
  clicks Run Simulation again.

Risk/coupling:

- This callback shares the same figure/style/error outputs as the run callback,
  using duplicate outputs.
- It validates `system-type` changes but does not use `system_type` directly.
- The "valid input" branch is intentionally or historically a clear-output
  branch, not a figure-generation branch.

### Main Run Simulation callback

Responds to:

- `submit-val.n_clicks`

Consumes state:

- `init_cond_theta1.value`
- `init_cond_theta2.value`
- `init_cond_omega1.value`
- `init_cond_omega2.value`
- `time_start.value`
- `time_end.value`
- `param_l1.value`
- `param_l2.value`
- `param_m1.value`
- `param_m2.value`
- `param_M1.value`
- `param_M2.value`
- `param_g.value`
- `model-type.value`
- `system-type.value`

Updates:

- `time-graph.figure`
- `phase-graph.figure`
- `pendulum-animation.figure`
- `animation-phase-container.style`
- `time-graph-container.style`
- `time-graph-section.style`
- `error-message.children`

Behavior before first run:

- If `n_clicks <= 0`, returns three empty `go.Figure()` objects, hides the graph
  containers, and clears the error message.

Behavior on run:

1. Builds `initial_conditions` as
   `[theta1, theta2, omega1, omega2]` from UI values.
2. Calls `validate_inputs(...)`.
3. If invalid, leaves figures as `no_update`, hides graph containers, and
   displays validation output.
4. Computes `time_steps = int((time_end - time_start) * 200)`.
5. Builds `time_vector = [time_start, time_end, time_steps]`.
6. Selects mass symbols based on `model-type`:
   - `simple`: `{m1: param_m1, m2: param_m2}`
   - otherwise: `{M1: param_M1, M2: param_M2}`
7. Combines lengths, gravity, and masses into a SymPy-keyed `parameters` dict.
8. Selects model class based on `system-type`:
   - `lagrangian`: `DoublePendulumLagrangian(...)`
   - otherwise: `DoublePendulumHamiltonian(...)`
9. Builds the time graph by calling `pendulum.time_graph()`, converting the
   Matplotlib figure to Plotly with `plotly.tools.mpl_to_plotly`, applying
   margins and `mpl_layout`, then closing the Matplotlib figure.
10. Builds the phase graph the same way with `pendulum.phase_path()`, fixed
    width/height `600`, `mpl_layout`, and Matplotlib close.
11. Calls `pendulum.precompute_positions()`.
12. Builds the animation with
    `pendulum.animate_pendulum(trace=True, fig_width=600, fig_height=600, static=True)`.
13. Shows `animation-phase-container` with `display: flex`, `time-graph-container`
    with `display: block`, `time-graph-section` with `display: flex`, and clears
    `error-message`.

Where simulation results are generated:

- Numerical model instances are created inside the Dash callback.
- `DoublePendulumLagrangian.__init__` and `DoublePendulumHamiltonian.__init__`
  immediately derive/load equations, lambdify equations, and integrate.
- The callback does not retain a structured result object. It only receives the
  model instance long enough to build figures.

Where figures/animations are built:

- Time graph: model class method `time_graph()`, Matplotlib, converted in
  callback.
- Phase graph: model class method `phase_path()`, Matplotlib, converted in
  callback.
- Animation: model class method `animate_pendulum()`, Plotly directly.
- Shared helper `src/double_pendulum/plotting/helpers.py::generate_pendulum_figures`
  exists, but the live callback does not use it for the current three-output
  run path.
- Shared `app/components/figure_style.py::mpl_layout` is applied to converted
  time and phase figures.

Callback coupling that makes future redesign risky:

- Output IDs are tightly coupled to both callbacks.
- The run trigger lives in the footer, away from the control component that
  owns most input IDs.
- Figure generation, model construction, validation handling, display-style
  changes, and error-state handling all live in one Dash callback.
- `suppress_callback_exceptions=True` in `pendulum_app.py` can hide some missing
  ID mistakes until runtime.
- The model class methods combine numerical data and plotting concerns.
- The main callback treats any non-`lagrangian` `system-type` as Hamiltonian.
- The current Hamiltonian UI state convention is known to be unsettled because
  the UI labels angular velocities but the Hamiltonian equations use canonical
  momenta.

## 3. Current model and numerical pipeline

Relevant classes:

- `src/double_pendulum/models/lagrangian.py::DoublePendulumLagrangian`
- `src/double_pendulum/models/hamiltonian.py::DoublePendulumHamiltonian`

Relevant symbolic helpers:

- `form_lagrangian(model)`
- `euler_lagrange_system(...)`
- `simplify_system(...)`
- `first_order_system(...)`
- `compute_hamiltonian(model)`
- `hamiltonian_system(model)`
- `hamiltonian_first_order_system(model)`

Model type handling:

- The UI exposes `model-type` values `simple` and `compound`.
- The callback selects different mass symbols based on `model-type`.
- The Lagrangian class uses `add_equations(model)` through a class-level cache.
- The Hamiltonian class uses `hamiltonian_first_order_system(model)` through a
  class-level cache.
- `form_lagrangian` and `compute_hamiltonian` both branch on `simple` versus
  `compound`.

System type handling:

- The UI exposes `system-type` values `lagrangian` and `hamiltonian`.
- The callback constructs `DoublePendulumLagrangian` only when
  `system_type == "lagrangian"`; any other value constructs
  `DoublePendulumHamiltonian`.
- No factory or shared simulator interface exists yet.

Gravity handling:

- Gravity is selected through `param_g`, a dropdown of fixed planetary values.
- Validation bounds gravity between Pluto and Jupiter values:
  `0.696 <= g <= 23.15`.
- The callback passes gravity as SymPy symbol `g` in the parameter dictionary.
- Gravity label/copy treats the value as acceleration due to gravity in
  meters per second squared.

Parameter handling:

- Simple model parameters:
  - `l1`
  - `l2`
  - `m1`
  - `m2`
  - `g`
- Compound model parameters:
  - `l1`
  - `l2`
  - `M1`
  - `M2`
  - `g`
- `unity-parameters` fills all mass and length fields, including hidden fields,
  with `1` and gravity with `9.81`.
- Validation checks only the active mass pair for the selected model type.
- Parameters are passed as a SymPy-keyed dict, not a typed or serializable data
  object.

Initial condition handling:

- UI labels the four values as angles and angular velocities:
  `[theta1, theta2, omega1, omega2]`.
- Validation requires numeric values, angles between `-180` and `180` degrees,
  and angular velocities within `+/-1000` degrees per second.
- Both model classes apply `np.deg2rad(initial_conditions)` to all four entries.
- For Lagrangian, the state is `[theta1, theta2, omega1, omega2]` in radians.
- For Hamiltonian, the state is `[theta1, theta2, p_theta_1, p_theta_2]`, but
  the current app passes the same UI-shaped values and applies `deg2rad` to the
  momentum slots. Existing tests explicitly preserve that contract without
  asserting that it is physically final.

Solver and integration path:

- Both model classes default to `scipy.integrate.solve_ivp`.
- Both classes also accept `odeint` and arbitrary `**integrator_args`.
- The UI does not expose solver method, tolerances, max step, dense output, or
  failure behavior.
- `self.time = np.linspace(time_start, time_end, time_steps)`.
- For `solve_ivp`, the classes call:
  - `solve_ivp(lambda t, y: self._system(y, t), t_span, self.initial_conditions, t_eval=self.time, **integrator_args)`
  - then store only `sol.y.T`.
- The returned SciPy `OdeResult` metadata is discarded. Success/failure status,
  solver message, step counts, function evaluation counts, and event metadata
  are not retained.
- For `odeint`, only the returned solution array is retained.

Where arrays are produced:

- `self.time`: one-dimensional NumPy array generated in model `__init__`.
- `self.sol`: two-dimensional NumPy array generated by `_solve_ode`.
  Current expected shape is `(time_steps, 4)`.
- `self.precomputed_positions`: two-dimensional NumPy array with shape
  `(4, time_steps)` after `precompute_positions()`.
- Position arrays are produced from the first two state columns only:
  - `x_1 = l1 * sin(theta_1)`
  - `y_1 = -l1 * cos(theta_1)`
  - `x_2 = x_1 + l2 * sin(theta_2)`
  - `y_2 = y_1 - l2 * cos(theta_2)`

Metadata currently retained:

- `initial_conditions`, after conversion with `np.deg2rad`.
- `time` samples.
- `parameters` dict, keyed by SymPy symbols.
- `model` string.
- `matrix`, the symbolic matrix equation.
- Lambdified equation functions.
- `sol` array.
- `precomputed_positions`, only after explicitly computed.

Metadata currently lost or not cleanly packaged:

- Original input values in degrees and user-facing units.
- Time interval request as entered by the user.
- Time sample rate rule (`200` samples per second) except as implicit callback
  logic.
- Solver method name as a serializable value.
- Solver tolerances and other integrator settings unless inferred externally.
- `solve_ivp` success flag, status, message, `nfev`, `njev`, `nlu`, and
  returned time array before transposition.
- Runtime duration.
- Validation warnings/errors alongside the result.
- State variable semantics, especially Hamiltonian momentum versus UI angular
  velocity.
- Energy arrays and drift diagnostics.

## 4. Current visual/output logic

### Animation

Built by:

- `DoublePendulumLagrangian.animate_pendulum(...)`
- `DoublePendulumHamiltonian.animate_pendulum(...)`

Live callback path:

- Calls `pendulum.precompute_positions()`.
- Calls `pendulum.animate_pendulum(trace=True, fig_width=600, fig_height=600, static=True)`.

Data consumed:

- `precomputed_positions`: `x_1`, `y_1`, `x_2`, `y_2`.
- Lengths via position calculation before animation.
- First two state columns indirectly, through position calculation.

Current behavior:

- Plotly figure with initial pendulum trace.
- Optional full path traces for bob 1 and bob 2 when `trace=True`.
- Frames are added every `10` samples.
- A Play button is embedded in Plotly `updatemenus`.
- `static=True` disables zoom/pan and hides legend.
- Uses fixed `600 x 600` dimensions in the live callback.

Trust/reuse status:

- Callback-safe in the current path if `precompute_positions()` was called.
- Reusable as a model method, but it mixes data, style, animation, and
  interaction policy inside the model class.
- Untested at the Plotly figure/frame level.
- Performance risk is unmeasured. Frame count scales with time interval and the
  hardcoded `200` samples per second rule, reduced by frame step `10`.
- Axis extent is based on realized trajectory extrema rather than the full
  reachable length envelope; this may be visually tight for some runs but needs
  product review before changing.

### Time-series plot

Built by:

- `DoublePendulumLagrangian.time_graph()`
- `DoublePendulumHamiltonian.time_graph()`

Live callback path:

- Builds a Matplotlib figure.
- Plots `self.sol[:, 0]` and `self.sol[:, 1]` converted to degrees.
- Converts the Matplotlib figure to Plotly with `plotly.tools.mpl_to_plotly`.
- Applies responsive margins and shared `mpl_layout`.
- Closes the Matplotlib figure.

Data consumed:

- `self.time`.
- First two state columns, interpreted as angular displacement.

Current behavior:

- Shows `theta1` and `theta2` over time.
- Does not show angular velocities or momenta.
- Does not show solver status, numerical error, or energy drift.

Trust/reuse status:

- Callback-safe in current usage.
- Basic array shape and finite values are tested indirectly for model output,
  but figure structure is not tested.
- Reusable only as a model method or through Matplotlib conversion. It is not a
  clean data-to-figure helper.
- Trusted only as a basic visual projection of state columns 0 and 1, assuming
  state conventions are correct.

### Phase-style/state projection plot

Built by:

- `DoublePendulumLagrangian.phase_path()`
- `DoublePendulumHamiltonian.phase_path()`

Live callback path:

- Builds a Matplotlib figure.
- Plots `rad2deg(self.sol[:, 0])` against `rad2deg(self.sol[:, 1])`.
- Converts to Plotly.
- Applies fixed `600 x 600` dimensions and `mpl_layout`.
- Closes the Matplotlib figure.

Data consumed:

- First two state columns only.

Current behavior:

- Labeled as "Phase Portrait".
- Actually plots `theta1` versus `theta2`; it is a coordinate-space projection,
  not a full phase portrait with angle and conjugate velocity/momentum axes.

Trust/reuse status:

- Callback-safe in current usage.
- Useful as a state projection, but the current title may overstate what it is.
- Untested at figure level.
- Reusable only through model methods and Matplotlib conversion.
- Needs pedagogical review before being treated as a validated phase-space
  diagnostic.

### Position traces

Built by:

- `_calculate_positions()`
- `precompute_positions()`
- `animate_pendulum(trace=True, ...)`

Data consumed:

- `self.sol[:, 0]`, `self.sol[:, 1]`, `l1`, and `l2`.

Current behavior:

- Position arrays are not separately exposed to the callback.
- Path traces are included inside the animation figure for both bobs.
- No standalone position-over-time plot exists.

Trust/reuse status:

- Basic dimensions and finite values are tested for simple Lagrangian and
  Hamiltonian models.
- Initial vertical position is tested for the simple Lagrangian model.
- Compound position interpretation may need review because compound-model
  derivation uses rod centers of mass in the Lagrangian, while visualization
  still draws endpoint geometry from full lengths.

### Energy plots or diagnostics

Current status:

- No live energy plot exists.
- No energy arrays are computed by the model classes.
- Symbolic Lagrangian and Hamiltonian energy expressions exist in
  `src/double_pendulum/math/functions.py`, but runtime energy diagnostics are
  not exposed.
- Tests explicitly mention energy conservation and trajectory regression as
  known gaps.

Trust/reuse status:

- Not available for production output yet.
- Feasible later, but requires a clear state convention, especially for the
  Hamiltonian path.

### Textual diagnostics

Current status:

- Validation errors are rendered to `error-message` through
  `validate_inputs(...)`.
- No successful-run summary is shown.
- No solver success/failure message is shown.
- No runtime, sample count, solver method, tolerance, or drift information is
  shown.

Trust/reuse status:

- Validation rendering is tested.
- Solver/runtime diagnostics are missing.

### Error/failure display

Current status:

- Input validation errors are displayed as Dash HTML under `error-message`.
- Invalid inputs hide the graph containers.
- Solver failures are not separately handled because the model classes discard
  `solve_ivp` status and the callback does not catch integration exceptions
  around model construction or plotting.
- A failed model construction or plotting step would likely surface as a server
  error rather than a controlled simulation failure state.

Trust/reuse status:

- Validation failure path exists and is partially tested at validation/component
  level.
- Numerical failure display is not trusted because it is not represented.

## 5. Current tests and evidence

Relevant model initialization and numerical tests:

- `tests/numerical/test_models.py`
  - Instantiates Lagrangian and Hamiltonian classes for simple and compound
    models.
  - Verifies `pendulum.sol.shape == (time_steps, 4)`.
  - Verifies `pendulum.time.shape == (time_steps,)`.
  - Verifies finite values in `pendulum.sol`.
  - Verifies first solution row matches `np.deg2rad(initial_conditions)` for
    simple Lagrangian and simple Hamiltonian.
  - Verifies `precomputed_positions.shape == (4, time_steps)` and finite
    values for simple Lagrangian and simple Hamiltonian.
  - Verifies one static vertical initial-condition position for simple
    Lagrangian.

Relevant symbolic/equation tests:

- `tests/unit/test_derivation_fidelity.py`
  - Checks simple-model Lagrangian against an expected kinetic-minus-potential
    expression.
  - Checks simple-model Hamiltonian against an expected mass-matrix and
    potential-energy expression.
  - Comments identify compound-model fidelity, energy conservation, trajectory
    regression, and Hamiltonian runtime state/input convention as known gaps.

Relevant validation tests:

- `tests/unit/test_validation.py`
  - Covers valid inputs and rendered Dash validation messages.
  - Covers invalid/missing time intervals, length bounds, mass bounds, gravity
    bounds, initial angle bounds, angular velocity bounds, and invalid value
    types.
  - Validation is foundational and input-focused, not a numerical quality test.

Relevant callback/layout/component tests:

- `tests/unit/test_components.py`
  - Asserts simulation controls include callback-bound IDs.
  - Asserts graph components and footer components can be built.
  - Asserts `mpl_layout` is available and has expected basic properties.
- `tests/unit/test_app_content.py`
  - Asserts `/simulation` opens directly into the workspace.
  - Asserts old intro/model-card content is absent from the live layout.
  - Asserts key IDs exist in the simulation layout:
    `scroll-target`, `submit-val`, `model-type`, `system-type`, `param_g`,
    `unity-parameters`, `pendulum-animation`, `phase-graph`, and `time-graph`.
  - Asserts simulation callback registration is importable.
- `tests/integration/test_app_import.py`
  - Imports `pendulum_app` without starting a server.
  - Verifies the Flask `server` object.
  - Verifies public routes return layout components.
- `tests/integration/test_compatibility_imports.py`
  - Verifies source-package helper/model imports remain available.

Evidence gaps:

- No direct tests for the main run callback's output tuple, display-style
  changes, validation branch, or successful graph generation.
- No tests for `clear_graphs_on_input_change` behavior despite duplicate output
  coupling.
- No browser smoke evidence in this Tier 0 pass.
- No Plotly figure contract tests for time graph, phase projection, animation
  traces, frames, layout, or JSON size.
- No tests for animation requiring `precompute_positions()`.
- No tests for compound-model precomputed position dimensions.
- No tests for solver failure handling.
- No tests retaining or asserting `solve_ivp` metadata.
- No deterministic repeat-run checks.
- No monotonic time checks.
- No sample-count checks for the callback's `200` samples per second rule.
- No energy conservation, energy drift, or Hamiltonian value checks.
- No trajectory regression fixtures.
- No Lagrangian/Hamiltonian comparison under a clearly audited common state
  convention.
- No performance baseline for integration time, callback latency, figure-build
  time, frame count, trace count, or Plotly JSON size.
- No memory/responsiveness evidence for repeated simulations.

## 6. Initial SimulationResult contract sketch

This is a planning sketch only. It should not be read as an implementation
request.

### Data that already exists

These fields are currently available on model instances or in the callback:

- `model_type`: current `model-type` value, `simple` or `compound`.
- `system_type`: current `system-type` value, `lagrangian` or `hamiltonian`.
- `gravity`: current `param_g` value.
- `lengths`: `param_l1`, `param_l2`.
- `masses`: active simple masses `param_m1`, `param_m2` or active compound
  masses `param_M1`, `param_M2`.
- `initial_conditions_degrees`: callback has the original UI values before
  model construction.
- `initial_conditions_radians`: model stores `self.initial_conditions` after
  `np.deg2rad(...)`.
- `time_start`: callback has the original value.
- `time_end`: callback has the original value.
- `time_steps`: callback computes this from `int((time_end - time_start) * 200)`.
- `time_samples`: model stores `self.time`.
- `state`: model stores `self.sol`.
- `symbolic_matrix`: model stores `self.matrix`.
- `parameters`: model stores the SymPy-keyed parameter dict.
- `bob_positions`: available after `precompute_positions()`.

### Data that exists but is not cleanly packaged

These fields can be inferred or captured today, but are not bundled into a
stable result object:

- `sample_rate_rule`: the callback hardcodes `200` samples per second.
- `active_mass_symbols`: selected by the callback from `model_type`.
- `state_columns`: known by convention:
  - Lagrangian: `[theta1, theta2, omega1, omega2]`.
  - Hamiltonian: `[theta1, theta2, p_theta_1, p_theta_2]`.
- `state_units`: angles are radians internally; Lagrangian angular velocities
  appear to be radians per second after `deg2rad`; Hamiltonian momentum units
  need audit.
- `figure_inputs`: time graph and phase projection consume only state columns
  `0` and `1`; animation consumes positions derived from those columns.
- `validation_errors`: available before result creation through
  `validate_inputs(...)`, but not attached to a result.
- `display_status`: callback decides hidden/visible styles, but this is UI
  state rather than simulation data.

### Data that would need to be added later

These fields are not currently retained or computed:

- `solver_method`: serializable method name, defaulting to `solve_ivp`.
- `solver_settings`: tolerances, max step, dense output, integration method,
  and other solver arguments.
- `solver_success`: `solve_ivp.success`.
- `solver_status`: `solve_ivp.status`.
- `solver_message`: `solve_ivp.message`.
- `solver_metrics`: `nfev`, `njev`, `nlu`, and any method-specific counters.
- `returned_time_samples`: raw `OdeResult.t`, distinct from requested
  `t_eval`.
- `runtime_seconds`: measured construction/integration/figure timing.
- `equation_cache_hit`: whether symbolic equations came from cache.
- `energy`: kinetic, potential, total energy arrays where formulas and state
  conventions have been validated.
- `energy_drift`: absolute and relative drift summaries.
- `warnings`: nonfatal numerical or convention warnings.
- `errors`: controlled simulation or solver failure errors.
- `figure_metrics`: trace count, frame count, point count, and Plotly JSON size
  if the result contract is used to support rendering evidence.

### Data whose meaning needs verification

These fields require mathematical or numerical audit before they can be trusted
as teaching outputs:

- Hamiltonian initial condition slots:
  - UI labels values as angular velocities.
  - Hamiltonian equations use canonical momenta.
  - Current tests preserve the existing pass-through convention but do not
    validate it as physically correct.
- Hamiltonian state columns 2 and 3:
  - Need units and interpretation verified before plotting or diagnostics.
- Compound visualization positions:
  - Compound derivation uses distributed rods/centers of mass, while animation
    draws endpoint geometry with full lengths.
- The current "Phase Portrait":
  - It plots `theta1` versus `theta2`; whether that should be labeled phase
    portrait, configuration projection, or another term needs product and math
    review.
- Energy formulas:
  - Symbolic expressions exist, but runtime energy arrays and drift metrics
    need a tested convention for both formulations and both model types.

### Possible contract shape

```text
SimulationResult
  request
    model_type
    system_type
    parameters
      lengths
      masses
      gravity
    initial_conditions
      raw_degrees
      internal_values
      state_variable_names
      state_units
    time
      start
      end
      requested_steps
      sample_rate_rule
    solver
      method
      settings
  status
    validation_errors
    solver_success
    solver_status
    solver_message
    warnings
    runtime_seconds
  data
    time_samples
    state
    positions
    energy
  diagnostics
    finite_values
    monotonic_time
    initial_condition_match
    energy_drift
    solver_metrics
  metadata
    symbolic_matrix
    equation_cache_key
    source_model_class
```

## 7. Risks and unknowns

Numerical trust gaps:

- Current tests prove basic shape and finite values, not correctness.
- Energy conservation is described in project copy, but no runtime energy drift
  evidence exists.
- Solver failure metadata is discarded.
- Default solver tolerances are implicit.
- No trajectory regression fixtures exist.
- No deterministic repeat-run checks exist.
- Hamiltonian state/input convention is explicitly unsettled.

Unclear conventions:

- UI velocity labels versus Hamiltonian momentum variables.
- Degrees-to-radians conversion is applied to every state entry in both systems.
- "Phase Portrait" currently means `theta1` versus `theta2`, not a full
  phase-space plot.
- Compound model visualization may not communicate distributed rod mass or
  center-of-mass assumptions.

Callback fragility:

- Duplicate outputs are shared by input-change clearing and run callbacks.
- Output visibility is controlled by callback-returned style dicts.
- The run button is footer-owned, while most input IDs live in the sidebar.
- Future layout changes must preserve or deliberately migrate callback-bound
  IDs.
- `suppress_callback_exceptions=True` reduces early warning for missing IDs.

Plotting reuse risks:

- Time and phase plots are methods on model classes and use Matplotlib before
  conversion to Plotly.
- Animation is also a model method and contains rendering, trace, frame, and UI
  play-button decisions.
- The live callback duplicates figure assembly logic instead of using the
  existing `generate_pendulum_figures` helper.
- Plotly conversion from Matplotlib may constrain future interactivity and
  testing.

Output IDs that constrain layout changes:

- `animation-phase-container`, `time-graph-container`, and
  `time-graph-section` are style outputs, not just passive wrappers.
- `time-graph`, `phase-graph`, and `pendulum-animation` are figure outputs.
- `error-message` sits inside the animation/phase loading region, so moving
  diagnostics elsewhere requires callback updates.

Performance risks:

- Time steps scale linearly as `200 * (time_end - time_start)`.
- Maximum validated duration is 120 seconds, implying up to 24,000 requested
  samples.
- Animation frames use every tenth sample, implying up to about 2,400 frames at
  the maximum interval.
- Full path traces in the animation include all position samples.
- Figure-build time, callback latency, and JSON payload size are unmeasured.
- Symbolic equation derivation is cached by model type, but first-run cost and
  cache behavior are not measured.

Missing diagnostics:

- No solver success/failure status.
- No runtime duration.
- No sample count shown to the user.
- No energy/drift diagnostic.
- No warning when Hamiltonian inputs are being interpreted as momenta.
- No controlled display for solver or plotting exceptions.

Areas where the app may look convincing without evidence:

- Smooth animation may imply numerical trust even though solver status and
  energy drift are hidden.
- The "Phase Portrait" label may imply a richer phase-space diagnostic than the
  plotted coordinate projection supports.
- Hamiltonian runs may appear equivalent to Lagrangian runs despite unresolved
  state convention questions.
- Compound runs may animate with simple endpoint geometry without explaining
  distributed-mass interpretation.

## 8. Recommended next Tier 1 task

Recommended next task:

Create the Phase 6 / Tier 1 numerical evidence baseline and result-contract
prototype without changing the live `/simulation` page.

Suggested Tier 1 scope:

- Define a small internal `SimulationResult` or result-contract note/prototype
  under `development/simulation_workbench/`.
- Run representative simple and compound, Lagrangian and Hamiltonian cases
  through the current model classes.
- Record baseline checks for:
  - output shape
  - finite values
  - monotonic time
  - deterministic repeat runs
  - initial-condition consistency
  - position dimensions and finite values
  - solver metadata that is currently lost
- Audit and document the Hamiltonian initial-condition convention before using
  Hamiltonian outputs for claims beyond current behavior preservation.
- Add measured evidence for at least one baseline run:
  - integration/runtime duration
  - generated sample count
  - animation frame count
  - trace count
  - approximate Plotly JSON size
- Do not design or promote new visuals until this evidence baseline exists.

Tier 1 should focus on the simulation contract and numerical trust floor first.
New visuals can wait until the app knows exactly what a run produced, whether
the solver succeeded, and what claims the state arrays can support.
