# Solver Contract Audit

Date: 2026-05-31

## Summary

Production already has a useful first layer of solver metadata and callback
gating: both model classes attach `solver_metadata`, and the Simulation
callback returns a non-drawable failed payload if SciPy reports
`success=False`.

The contract is not yet hard enough for a production solver-policy change. The
solver policy is still implicit in each model class through SciPy's default
`solve_ivp` behavior, policy fields such as `method`, `rtol`, `atol`, and
policy name are not first-class metadata, solver failure is folded into the
generic `failed` payload state, and the payload builder itself can still build
a drawable `success` payload from a model whose solver metadata reports
failure if a caller bypasses the callback guard.

Recommended direction: introduce central solver-policy definitions, normalize
solver metadata, add a model/callback result contract that distinguishes
`success`, `validation_error`, `solver_failure`, and `empty_or_cleared`, then
gate Canvas serialization on an explicit `render_safe` field before changing
the simple-model default to `dop853_moderate`.

## Files Inspected

Production code:

- `src/double_pendulum/models/lagrangian.py`
- `src/double_pendulum/models/hamiltonian.py`
- `src/double_pendulum/models/initial_conditions.py`
- `src/double_pendulum/models/metadata.py`
- `src/double_pendulum/validation/inputs.py`
- `app/callbacks/simulation.py`
- `app/serialization/canvas_payload.py`
- `app/components/simulation_controls.py`
- `app/serialization/__init__.py`
- `src/double_pendulum/models/__init__.py`

Production-facing documentation:

- `documentation/simulation-canvas/README.md`
- `documentation/simulation-canvas/canvas-integration-api.md`
- `documentation/simulation-canvas/callback-rendering-flow.md`
- `documentation/simulation-canvas/simulation-result-contract.md`

Tests:

- `tests/numerical/test_models.py`
- `tests/numerical/test_solver_metadata.py`
- `tests/numerical/test_initial_condition_conventions.py`
- `tests/numerical/test_canvas_payload.py`
- `tests/unit/test_validation.py`
- `tests/unit/test_derivation_fidelity.py`
- `tests/integration/test_simulation_interaction_shell.py`

## 1. Current Solver Policy

Current behavior:

- `DoublePendulumLagrangian.__init__` and `DoublePendulumHamiltonian.__init__`
  both default to `integrator=solve_ivp`.
- Both classes pass `**integrator_args` directly to `solve_ivp`.
- If no caller supplies `method`, `rtol`, or `atol`, SciPy defaults are used.
- `app/callbacks/simulation.py` currently instantiates both model classes
  without solver kwargs, so production Simulation runs use implicit SciPy
  defaults.
- The UI in `app/components/simulation_controls.py` exposes model type, system
  type, physical parameters, initial conditions, and duration. It does not
  expose solver policy.

Centralization:

- Solver policy is not centralised.
- The default policy is duplicated implicitly by the two model-class
  constructor signatures.
- Tests currently assert the integrator name is `solve_ivp`, but they do not
  assert an explicit method/tolerance policy.

Recommended home for candidate policies:

- Add a central production module such as
  `src/double_pendulum/models/solver_policy.py`.
- Keep the first policy surface small and explicit:

```python
@dataclass(frozen=True)
class SolverPolicy:
    name: str
    integrator: Callable
    method: str | None
    rtol: float | None
    atol: float | None
    role: str

    def solve_ivp_kwargs(self) -> dict[str, object]:
        ...
```

Candidate constants:

```text
simple_default:
  integrator = solve_ivp
  method = "DOP853"
  rtol = 1e-6
  atol = 1e-8

simple_reference:
  integrator = solve_ivp
  method = "DOP853"
  rtol = 1e-9
  atol = 1e-11

solve_ivp_default_baseline:
  integrator = solve_ivp
  method = None
  rtol = None
  atol = None
```

`solve_ivp_default_baseline` should remain a negative baseline/testing
reference, not the app-facing recommendation.

## 2. Current Solver Metadata

Current metadata lives in `src/double_pendulum/models/metadata.py` as
`SolverMetadata`. For `solve_ivp`, production retains:

- `integrator`
- `success`
- `status`
- `message`
- `nfev`
- `njev`
- `nlu`
- requested time count/start/end
- returned time count/start/end
- whether returned time exactly matches requested `t_eval`
- solution shape
- `solver_kwargs`

Current gaps:

- `method`, `rtol`, and `atol` are not top-level fields.
- The selected policy name is not captured.
- If no kwargs were supplied, `solver_kwargs` is `{}`, so the payload does not
  make SciPy defaults explicit.
- `summarise_canvas_payload(...)` only returns a compact solver summary and
  omits `message`, `nfev`, `method`, `rtol`, `atol`, and policy name.
- The diagnostics UI shows integrator, success/status, requested/returned
  counts, and sample match, but not method/tolerances/function evaluations.

Recommended capture point:

- Keep low-level SciPy metadata in `SolverMetadata`.
- Extend it or wrap it so normalized policy fields are first-class:
  `policy_name`, `method`, `rtol`, `atol`, and possibly `sample_rate_hz`.
- Introduce a higher-level simulation result object for callback decisions
  instead of making callbacks infer render safety from model instances.

Preferred shape:

```python
@dataclass(frozen=True)
class SimulationRunResult:
    state: SimulationResultState
    model_type: str
    formulation: str
    user_message: str
    debug_message: str | None
    render_safe: bool
    payload_safe: bool
    solver_metadata: SolverMetadata | None
    simulation: DoublePendulumLagrangian | DoublePendulumHamiltonian | None
```

The model instance may still own `sol`, `solver_time`, and
`solver_metadata`, but callback and payload code should consume the result
contract, not assume every constructed model is drawable.

## 3. Current Failure Behavior

Validation failure:

- `validate_inputs(...)` runs before model construction.
- A validation error returns `_failed_result(...)`.
- The resulting Canvas payload has `status="failed"`, no drawable arrays,
  `sample_count=0`, and `rendering.drawable=False`.

Model setup exception:

- Exceptions during model construction are caught by
  `build_simulation_run_result(...)`.
- The callback returns `_failed_result(...)` with a setup-failure message and
  no drawable arrays.

Solver failure:

- Both model classes call `solve_ivp(...)`, then set `self.sol` from
  `ode_result.y.T` regardless of `ode_result.success`.
- `SolverMetadata.from_solve_ivp(...)` records `success`, `status`, `message`,
  returned sample count, and solution shape.
- `build_simulation_run_result(...)` checks `solver_metadata.success is False`
  immediately after construction and returns `_failed_result(...)` before
  precomputing positions or building a success payload.

Payload behavior:

- `build_canvas_motion_payload(...)` knows which payload statuses are drawable.
- `failed`, `cleared`, and `empty` payloads omit drawable arrays.
- `validate_canvas_motion_payload(...)` enforces non-drawable-array rules for
  non-drawable statuses.
- However, the payload builder and payload validator do not currently reject a
  drawable `success` payload solely because embedded solver metadata says
  `success=False`. Today that protection is callback-level, not boundary-level.

Stale data behavior:

- When inputs change after a successful run, `mark_canvas_payload_stale(...)`
  keeps the previous arrays but changes `status` to `stale`, disables autoplay,
  and marks the result stale.
- If changed inputs are invalid, the callback returns a failed non-drawable
  payload instead of leaving the old success arrays active.

Current risk:

- The normal callback path avoids silently rendering known solver failures.
- A direct caller of `build_canvas_motion_payload(...)` can still produce a
  drawable `success` payload from a failed/partial model unless the proposed
  contract or payload validation closes that gap.
- Solver failure is not distinct from validation failure in the status enum;
  both become `failed` with different messages/errors.

## 4. Proposed Solver Contract

The production contract should distinguish at least:

| State | Meaning | Render safe |
| --- | --- | --- |
| `success` | Validation passed, solver succeeded, returned trajectory is complete enough for the requested payload, payload validation passed. | Yes |
| `validation_error` | User input validation failed before solver execution. | No |
| `solver_failure` | Solver ran or setup began but did not produce an accepted complete trajectory. | No by default |
| `empty_or_cleared` | No active run, or output was deliberately cleared. | No |

The existing `stale` state should remain distinct in the Canvas payload layer:
it is drawable for inspection, but it is not a current successful result and
autoplay stays disabled.

Required contract fields:

- `state`: enum/string such as `success`, `validation_error`,
  `solver_failure`, `empty_or_cleared`, or `stale_success`.
- `user_message`: concise message safe for the run-status area.
- `debug_message`: solver/setup detail for diagnostics and tests.
- `solver_success`: boolean or `None` when solver did not run.
- `solver_status`: SciPy status code or `None`.
- `solver_message`: SciPy message or setup message.
- `solver_integrator`: currently `solve_ivp` or `odeint`.
- `solver_policy_name`: for example `simple_default`.
- `solver_method`: for example `DOP853`.
- `rtol` and `atol`: explicit values or explicit `None` for baseline/default.
- `nfev`, `njev`, `nlu`: where available.
- `requested_sample_count` and `returned_sample_count`.
- `requested_time_interval` and `returned_time_interval`.
- `returned_time_matches_requested`.
- `model_type`: `simple` or `compound`.
- `formulation`: `lagrangian` or `hamiltonian`.
- `render_safe`: whether any drawable arrays may be serialized/rendered.
- `payload_safe`: whether the Canvas payload builder accepted the result.

Acceptance criteria for `success`:

- validation passed;
- model construction did not raise;
- solver metadata exists for `solve_ivp`;
- `solver_metadata.success is True`;
- returned sample count equals requested sample count;
- returned times match requested `t_eval` or an explicitly documented
  interpolation/resampling path has been applied;
- state arrays are finite;
- positions are finite and match sample count;
- payload validation passes.

Acceptance criteria for `solver_failure`:

- do not serialize drawable arrays by default;
- preserve solver metadata and partial returned counts for diagnostics;
- cancel playback;
- clear active success/autoplay state;
- show a user-facing simulation failure message distinct from validation
  failure;
- make details available in diagnostics/tests.

## 5. Proposed Solver Policies

Provisional simple-model policies from `development/math_fidelity/`:

| Policy | Method | rtol | atol | Role |
| --- | --- | ---: | ---: | --- |
| `simple_default` | `DOP853` | `1e-6` | `1e-8` | Leading app-facing simple-model candidate. |
| `simple_reference` | `DOP853` | `1e-9` | `1e-11` | High-fidelity/reference candidate. |
| `solve_ivp_default_baseline` | SciPy default | default | default | Negative baseline/testing reference. |

Recommendation:

- Use the same `simple_default` policy for simple Lagrangian and simple
  Hamiltonian unless production tests find a formulation-specific failure.
- Do not generalize this policy to compound models until compound evidence is
  collected.
- Keep policy selection out of the UI initially unless product scope changes.

## 6. Production Tests To Add

Concrete tests are detailed in `IMPLEMENTATION_PLAN.md`. The minimum coverage
before changing production solver settings should include:

- simple Lagrangian/Hamiltonian agreement under `simple_default`;
- `simple_reference` comparison or diagnostic fixture;
- Hamiltonian angular-velocity to canonical-momentum mapping;
- Hamiltonian momentum-to-angular-velocity reconstruction if exposed;
- short deterministic energy drift smoke tests;
- solver metadata captured on successful solves, including policy fields;
- solver failure metadata captured on failed solves;
- failed solver result is not render-safe;
- callback returns or clears safe failure state instead of stale success data;
- Canvas payload serialization rejects or omits failed/incomplete results;
- screenshot-like `[0, 60, 0, 0]` completes under selected policy;
- nonzero-velocity spirograph case completes under selected policy or reports
  failure cleanly.

## 7. Implementation Sequencing

Recommended sequence is documented in `IMPLEMENTATION_PLAN.md`. In short:

1. Introduce solver policy constants/config.
2. Normalize solver metadata with policy fields.
3. Add result-state/result-wrapper contract tests.
4. Add solver success metadata tests.
5. Add solver failure tests.
6. Gate Canvas payload creation on `render_safe`.
7. Update callback result handling and diagnostics.
8. Change simple-model production default to `simple_default`.
9. Update production documentation.
10. Run full tests and targeted Simulation smoke checks.

## 8. Explicit Non-Goals

This pass does not:

- change production solver policy;
- change Canvas rendering;
- change UI or styling;
- change compound-model math;
- implement Hamiltonian chaos tooling;
- rewrite `ROADMAP.md`;
- add production tests.

## 9. Relationship To Evidence Lab

This audit depends on local Phase 8 evidence:

- `development/math_fidelity/SOLVER_POLICY_RECOMMENDATION.md`
- `development/math_fidelity/DRIFT_INVESTIGATION.md`
- `development/math_fidelity/SOLVER_COST_BENCHMARK.md`
- `development/math_fidelity/APP_LIKE_COST_BENCHMARK.md`

Relevant evidence conclusions:

- Default `solve_ivp` is a high-confidence risk for app-facing simple-model
  runs.
- `dop853_moderate` collapsed simple Lagrangian/Hamiltonian drift compared
  with default behavior and is the leading simple-model default candidate.
- `dop853_strict` remains the high-fidelity/reference candidate.
- Default `solve_ivp` failed the 60-second nonzero-velocity simple case in the
  solver-cost and app-like benchmarks.
- Compound-model behavior, browser/rendering cost, and production payload
  schema effects remain unresolved evidence gaps.

## Current Uncertainties

- Whether `dop853_moderate` remains sufficient for compound models.
- Whether production Canvas payload size and browser rendering cost remain
  acceptable at 60 seconds and 200 Hz after contract hardening.
- Whether `returned_time_matches_requested` should be a hard success
  requirement for all accepted payloads or whether a tested interpolation path
  should exist.
- Whether `odeint` should remain supported as a production integrator option or
  be treated as a legacy/testing path with partial metadata.
- Whether the result contract should be a new dataclass returned by model
  factories or a callback-level dictionary first. A dataclass is the cleaner
  long-term shape, but a dictionary may be a smaller migration step.
