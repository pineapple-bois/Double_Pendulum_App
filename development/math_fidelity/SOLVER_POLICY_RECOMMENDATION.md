# Solver Policy Recommendation

Date: 2026-05-31

This note synthesizes the Phase 8 evidence currently captured in:

- `BASELINE_REVIEW.md`
- `DRIFT_INVESTIGATION.md`
- `SOLVER_COST_BENCHMARK.md`
- `APP_LIKE_COST_BENCHMARK.md`

It is an evidence note, not a production change request.

## Executive Summary

High-confidence finding: default `solve_ivp` should not remain the unqualified
production policy for simple-model runs. It can produce visible
Lagrangian/Hamiltonian drift under default tolerances, and it failed the
60-second nonzero-velocity simple case in both solver-cost and app-like
benchmarks.

Provisional recommendation: keep `rk45_strict`, `dop853_moderate`, and
`dop853_strict` as candidate simple-model production policies. The strongest
candidate set is:

- `dop853_moderate` as the likely latency/accuracy compromise candidate.
- `dop853_strict` as the high-fidelity candidate, still apparently affordable
  for tested simple-model app-like runs.
- `rk45_strict` as a conservative fallback candidate because it is familiar and
  performed well, though it was not consistently cheaper than DOP853.

Unresolved evidence gap: compound-model behavior and production callback
contract behavior have not been tested in this evidence lab.

## 1. Default `solve_ivp` Acceptability

High-confidence finding: default `solve_ivp` is risky for production
simple-model runs.

Evidence:

- The drift investigation showed that simple Lagrangian/Hamiltonian angular
  disagreement collapses when tolerances tighten.
- The solver-cost benchmark showed default `solve_ivp` failed the 60-second
  `nonzero_velocity_spirograph` case for both formulations.
- The app-like benchmark reproduced that same default-solver failure for both
  formulations.
- Default 60-second energy drift was far worse than explicit tolerance policies.

Provisional recommendation: do not rely on bare default `solve_ivp` for
app-facing simple-model simulations once production code is ready for a solver
policy change.

## 2. Plausible Simple-Model Solver Policies

Provisional recommendation: consider these candidates for simple-model
production evaluation:

| Candidate | Why it remains plausible | Concern |
| --- | --- | --- |
| `dop853_moderate` | Good runtime profile; energy drift close to moderate RK45; higher-order method. | Needs direct production-schema and callback tests. |
| `dop853_strict` | Strongest fidelity profile in the evidence gathered so far; still sub-second for tested 60-second app-like simple runs. | More expensive; should be checked against UX latency targets. |
| `rk45_strict` | Strong fidelity improvement over defaults; familiar SciPy default-family method. | Not always cheaper than DOP853 and sometimes slower than DOP853 moderate. |

High-confidence finding: any production policy should set explicit `method`,
`rtol`, and `atol` instead of relying on SciPy defaults.

## 3. DOP853 Strict Affordability

Provisional recommendation: keep `dop853_strict` as a live candidate.

Evidence:

- In the app-like benchmark, 60-second, 200 Hz median total runtimes were about
  0.325s for Lagrangian and 0.375s for Hamiltonian.
- The worst tested 60-second DOP853 strict app-like row was about 0.659s.
- JSON serialization and diagnostic payload preparation were small compared
  with model construction and solve time.

Unresolved evidence gap: these timings exclude Dash callback overhead, network
transfer, browser parsing, Canvas rendering, and production payload schema
differences.

## 4. DOP853 Moderate As A Compromise

Provisional recommendation: `dop853_moderate` may be the best first production
candidate to compare against `dop853_strict`.

Evidence:

- App-like 60-second median total runtime was about 0.180s for Lagrangian and
  0.205s for Hamiltonian.
- Solver-cost energy drift was close to `rk45_moderate` and dramatically better
  than default behavior.
- It avoids the bare default policy while preserving a lower latency profile
  than strict policies.

Unresolved evidence gap: the existing drift investigation did not include
`dop853_moderate` in the Lagrangian/Hamiltonian agreement comparison. Add that
before finalizing a production default.

## 5. Separate Lagrangian And Hamiltonian Policies

Provisional recommendation: use the same candidate policy for Lagrangian and
Hamiltonian simple paths unless a targeted follow-up shows a formulation-specific
failure.

Evidence:

- Both formulations benefited from explicit tolerances.
- Both formulations failed the same default 60-second nonzero-velocity case.
- App-like DOP853 strict and DOP853 moderate costs were similar enough that
  separate policy complexity is not yet justified.

Unresolved evidence gap: longer chaotic runs may expose formulation-specific
behavior. That should be measured before declaring one shared policy final.

## 6. Hamiltonian As Future Chaos Backbone

Provisional recommendation: keep Hamiltonian as a strong candidate for the
future chaos-investigation backbone, but do not make that architectural shift in
this pass.

Rationale:

- Hamiltonian state has the right conceptual relationship to energy and phase
  space, provided canonical momenta are handled explicitly.
- The baseline review found that the simple Hamiltonian path appears to convert
  user angular velocities to canonical momenta correctly.
- The evidence does not currently point to a Hamiltonian state-mapping defect in
  the simple model.

Unresolved evidence gap: a Hamiltonian-first chaos workflow needs dedicated
tests for canonical-momentum mapping, omega reconstruction for diagnostics,
energy behavior, and long-duration sensitivity.

## 7. Evidence Needed Before Production Changes

Before changing production solver settings, gather or add:

- Drift comparisons that include `dop853_moderate`.
- Production-schema app-like payload size measurements, not only diagnostic
  payload measurements.
- Callback-level behavior when a solver returns failure status.
- Browser-side timing for JSON parse and Canvas rendering at 60 seconds and
  200 Hz.
- Compound-model solver evidence.
- A long-duration simple-model sensitivity pass with explicit failure criteria.

## 8. Production Tests To Add First

Recommended production tests before solver-policy changes:

- Simple Lagrangian/Hamiltonian agreement tests under the selected policy for
  benign and sensitive initial states.
- Hamiltonian initial-state mapping tests verifying angular velocity to
  canonical momentum conversion.
- Hamiltonian diagnostic omega-reconstruction tests, if angular-velocity output
  remains user-facing.
- Solver metadata tests asserting success/status/message are captured.
- Failure-contract tests for a known hard input where the solver cannot complete.
- Energy drift smoke tests with clear tolerance bands for short deterministic
  runs.
- Payload shape and finite-value tests for callback outputs.
- Regression tests for default UI inputs and the screenshot-like `[0, 60, 0, 0]`
  case.

## 9. Solver Failure Contract

High-confidence finding: solver failure must be represented explicitly in the
callback/result contract before stricter solver policy work is considered done.

Recommended contract direction:

- Include solver success as a first-class boolean.
- Include solver status, message, method, `rtol`, `atol`, and `nfev`.
- Preserve partial returned sample count when available.
- Avoid silently rendering failed trajectories as if they were complete.
- Surface a user-facing validation or simulation warning when solver failure
  occurs.
- Keep diagnostic metadata available for tests and future numerical audits.

Unresolved evidence gap: the current production callback contract has not been
audited in this pass, because production callback changes are intentionally out
of scope.
