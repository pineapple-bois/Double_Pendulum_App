# Tier 1 Result Contract Prototype

Tier: Phase 6 / Simulation Workbench Tier 1
Status: planning/prototype contract, not production implementation

This document sketches the fields a future `SimulationResult` should expose
before new Simulation page outputs are accepted. Field status labels mean:

- **available today**: accessible directly from the current callback or model
  instance.
- **available but not cleanly packaged**: inferable today, but scattered across
  callback logic, model attributes, or implicit conventions.
- **missing today**: not retained or computed by current code.
- **unsafe/needs mathematical audit**: present or inferable, but not safe to
  use for scientific claims until conventions/formulas are audited.

## Request

| Field | Purpose | Status | Current source / note |
| --- | --- | --- | --- |
| `model_type` | Selects simple point-mass or compound rod model. | available today | `model-type` callback state and `pendulum.model`. |
| `system_type` | Selects Lagrangian or Hamiltonian formulation. | available today | `system-type` callback state. |
| `gravity` | Acceleration due to gravity. | available today | `param_g`, passed as SymPy key `g`. |
| `lengths` | Rod lengths `l1`, `l2`. | available today | `param_l1`, `param_l2`, passed in `parameters`. |
| `masses` | Active simple masses `m1`, `m2` or compound masses `M1`, `M2`. | available today | Callback chooses symbols based on `model_type`. |
| `initial_conditions_ui` | Values entered by the UI. | available today | Callback receives `[theta1, theta2, omega1, omega2]` before model construction. |
| `initial_conditions_internal` | Values used by solver. | available today | `pendulum.initial_conditions` after `np.deg2rad(...)`. |
| `state_variable_names` | Names and order of state columns. | available but not cleanly packaged | Lagrangian is `[theta1, theta2, omega1, omega2]`; Hamiltonian is `[theta1, theta2, p_theta_1, p_theta_2]`. |
| `state_units` | Units for each state column. | unsafe/needs mathematical audit | Angle columns are radians internally. Lagrangian velocity columns appear converted from deg/s to rad/s. Hamiltonian momentum slots are not audited. |
| `time_start` | Requested start time. | available today | `time_start` callback state. |
| `time_end` | Requested end time. | available today | `time_end` callback state. |
| `requested_sample_count` | Number of requested time samples. | available but not cleanly packaged | Callback computes `int((time_end - time_start) * 200)`. |
| `sample_rate_rule` | Current UI sampling rule. | available but not cleanly packaged | Hardcoded callback rule: 200 samples per second. |
| `solver_method` | Integration method. | available today | Tier 1b stores the integrator name in `pendulum.solver_metadata.integrator`. |
| `solver_settings` | Tolerances, max step, dense output, and other integrator arguments. | available but not cleanly packaged | Tier 1b stores explicit constructor kwargs in `solver_metadata.solver_kwargs`; effective SciPy defaults are still not expanded. |

## Status

| Field | Purpose | Status | Current source / note |
| --- | --- | --- | --- |
| `validation_status` | Whether request passed input validation. | available but not cleanly packaged | `validate_inputs(...)` returns Dash HTML or `None`; not attached to a result. |
| `solver_success` | Whether solver reports success. | available today | Tier 1b stores `solve_ivp.success`; `odeint` metadata leaves this as `None`. |
| `solver_status` | Solver status code. | available today | Tier 1b stores `solve_ivp.status`; `odeint` metadata leaves this as `None`. |
| `solver_message` | Human-readable solver message. | available today | Tier 1b stores `solve_ivp.message`; `odeint` metadata leaves this as `None`. |
| `warnings` | Nonfatal issues or convention warnings. | missing today | Needed for Hamiltonian convention and future numerical warnings. |
| `errors` | Controlled validation, solver, or rendering failure state. | missing today | Validation errors exist separately; solver/render errors are not captured as result data. |
| `runtime_duration` | Time spent constructing/integrating/deriving figures. | missing today | Tier 1 script measures this externally; production code does not. |
| `solver_metadata_available` | Explicit flag for solver metadata retention. | available today | Model instances expose `pendulum.solver_metadata`. |

## Data

| Field | Purpose | Status | Current source / note |
| --- | --- | --- | --- |
| `time_samples` | Time array used for output. | available today | `pendulum.time`. |
| `solver_time_samples` | Raw time samples returned by the solver. | available today | Tier 1b stores these separately as `pendulum.solver_time`. |
| `state_array` | Solver state array. | available today | `pendulum.sol`, expected shape `(sample_count, 4)`. |
| `bob_positions` | `x1`, `y1`, `x2`, `y2` arrays. | available but not cleanly packaged | `pendulum.precomputed_positions` after `precompute_positions()`. |
| `energy_arrays` | Kinetic, potential, total energy over time. | missing today | Symbolic expressions exist, but runtime energy arrays are not implemented. |
| `energy_arrays_safe` | Whether energy arrays are valid for claims. | unsafe/needs mathematical audit | Needs state convention and formula audit for each model/system pair. |
| `figure_inputs.time_series` | Data used by time graph. | available but not cleanly packaged | `time_samples`, `state[:, 0]`, `state[:, 1]`. |
| `figure_inputs.theta_theta_projection` | Data used by current theta-theta projection. | available but not cleanly packaged | `state[:, 0]`, `state[:, 1]`; not a validated full phase portrait. |
| `figure_inputs.animation` | Data used by animation. | available but not cleanly packaged | `bob_positions`; path traces use full position arrays. |
| `state_projections` | Named projections such as theta-theta, theta-omega, or momentum views. | missing today | Only theta-theta projection is currently produced, and only as a model plotting method. |

## Diagnostics

| Field | Purpose | Status | Current source / note |
| --- | --- | --- | --- |
| `output_shape_check` | Verify `time` and `state` shapes. | available but not cleanly packaged | Existing tests cover some shapes; Tier 1 script records all four baseline cases. |
| `finite_value_check` | Verify finite time/state values. | available but not cleanly packaged | Existing tests cover model state; Tier 1 script records time, state, and positions. |
| `monotonic_time_check` | Verify time samples increase. | available but not cleanly packaged | Easy to compute from `pendulum.time`; not currently stored. |
| `initial_condition_consistency_check` | Verify first state row matches internal initial conditions. | available but not cleanly packaged | Existing tests cover simple cases; Tier 1 script covers all baseline cases. |
| `deterministic_repeat_run_check` | Verify repeated construction produces same state. | available but not cleanly packaged | Tier 1 script computes this externally. |
| `position_shape_check` | Verify position array shape. | available but not cleanly packaged | Tier 1 script records `(4, sample_count)` after precompute. |
| `position_finite_value_check` | Verify finite position values. | available but not cleanly packaged | Tier 1 script records this externally. |
| `energy_drift` | Quantify total-energy drift. | missing today | Future evidence gate; unsafe until energy formulas/state conventions are audited. |
| `solver_metrics` | `nfev`, `njev`, `nlu`, raw returned samples. | available today | Tier 1b stores `solve_ivp` counters and `solver_time`; `odeint` counter fields remain `None`. |

## Rendering Metrics

| Field | Purpose | Status | Current source / note |
| --- | --- | --- | --- |
| `time_graph_build_time` | Time to build current time graph and Plotly conversion. | available but not cleanly packaged | Tier 1 script measures externally. |
| `phase_projection_build_time` | Time to build current theta-theta projection and Plotly conversion. | available but not cleanly packaged | Tier 1 script measures externally. |
| `animation_build_time` | Time to build current animation figure. | available but not cleanly packaged | Tier 1 script measures externally. |
| `trace_count` | Number of Plotly traces. | available but not cleanly packaged | Tier 1 script records for current figures. |
| `animation_frame_count` | Number of Plotly animation frames. | available but not cleanly packaged | Current method uses every tenth sample. |
| `plotly_json_size` | Approximate payload-size proxy. | available but not cleanly packaged | Tier 1 script uses `len(fig.to_json())`; full JSON is not saved. |
| `point_count` | Approximate rendered point count across traces/frames. | available but not cleanly packaged | Tier 1 script records a compact summary. |

## Hamiltonian Convention Warning

The current UI labels the final two initial-condition inputs as angular
velocities. The Hamiltonian model state, however, is
`[theta1, theta2, p_theta_1, p_theta_2]`, where the final two slots are
canonical momenta. The current code passes the UI-shaped values into the
Hamiltonian class and applies `np.deg2rad(...)` to all four entries.

Existing tests preserve that behavior, but they do not prove that the
Hamiltonian run is physically initialized from angular velocities correctly.
Tier 1C completed the first convention audit and confirmed the mismatch for
nonzero UI-labelled angular velocities. Until a velocity-to-momentum conversion
path is implemented and tested, Hamiltonian visual outputs should be treated as
behavior-preserving and exploratory, not as strong physical evidence.

## Minimum Future Contract Shape

```text
SimulationResult
  request
    model_type
    system_type
    parameters
      gravity
      lengths
      masses
    initial_conditions
      ui_values
      internal_values
      state_variable_names
      state_units
    time
      start
      end
      requested_sample_count
      sample_rate_rule
    solver
      method
      settings
  status
    validation_status
    solver_success
    solver_status
    solver_message
    warnings
    errors
    runtime_duration
    solver_metadata_available
  data
    time_samples
    state_array
    bob_positions
    energy_arrays
    figure_inputs
    state_projections
  diagnostics
    output_shape_check
    finite_value_check
    monotonic_time_check
    initial_condition_consistency_check
    deterministic_repeat_run_check
    position_shape_check
    position_finite_value_check
    energy_drift
    solver_metrics
  rendering_metrics
    figure_build_time
    trace_count
    frame_count
    point_count
    plotly_json_size
```

The contract should keep "available" and "trusted" separate. A field can exist
today and still be unsafe for scientific claims.
