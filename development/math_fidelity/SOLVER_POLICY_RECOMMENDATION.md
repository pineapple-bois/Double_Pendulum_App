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

Provisional recommendation: `dop853_moderate` is now the leading simple-model
production-default candidate for the next hardening phase. It collapses
Lagrangian/Hamiltonian drift by roughly `1.4e2x` to `3.3e4x` compared with
default `solve_ivp` in the refreshed drift investigation, while the app-like
benchmark shows lower local runtime than strict policies.

Provisional recommendation: retain `dop853_strict` as the high-fidelity and
diagnostic candidate. It produces tighter drift and energy behavior than
`dop853_moderate`, and remains locally affordable in the tested simple-model
app-like benchmark.

Unresolved evidence gap: compound-model behavior, production payload schema,
browser/rendering cost, and production callback failure contracts have not been
hardened yet.

## 1. Default `solve_ivp` Acceptability

High-confidence finding: default `solve_ivp` is risky for production
simple-model runs.

Evidence:

- The drift investigation shows default `solve_ivp` reaches up to about
  `9.53e-2` radians Lagrangian/Hamiltonian angular drift in the screenshot-like
  short simple case.
- The same drift case drops to about `2.87e-6` radians under
  `dop853_moderate`.
- The solver-cost benchmark showed default `solve_ivp` failed the 60-second
  `nonzero_velocity_spirograph` case for both formulations.
- The app-like benchmark reproduced that same default-solver failure for both
  formulations.
- Default energy drift is far worse than explicit tolerance policies.

Provisional recommendation: do not rely on bare default `solve_ivp` for
app-facing simple-model simulations once production code is ready for a solver
policy change.

## 2. DOP853 Moderate As Likely Production Default Candidate

Provisional recommendation: use `dop853_moderate`
(`method="DOP853"`, `rtol=1e-6`, `atol=1e-8`) as the leading candidate for the
first production solver-policy hardening pass.

Evidence:

- Refreshed drift logs show maximum angular drift in the `1e-6` to `3e-6`
  radian range across all four short simple cases.
- Default-to-moderate drift reduction ranges from about `1.43e2x` to
  `3.32e4x`.
- App-like 60-second, 200 Hz median total runtime was about `0.180s`
  Lagrangian and `0.205s` Hamiltonian.
- Solver-cost and app-like benchmarks both show DOP853 policies completing the
  longer nonzero-velocity case where default `solve_ivp` failed.

High-confidence finding: `dop853_moderate` is no longer an unresolved drift
gap. It has direct Lagrangian/Hamiltonian drift evidence and remains a strong
latency/fidelity compromise candidate.

Unresolved evidence gap: production callback behavior, production Canvas-schema
payload size, and browser/rendering cost still need measurement before this can
become an implemented production default.

## 3. DOP853 Strict As High-Fidelity Candidate

Provisional recommendation: retain `dop853_strict`
(`method="DOP853"`, `rtol=1e-9`, `atol=1e-11`) as a high-fidelity and
diagnostic candidate.

Evidence:

- Refreshed drift logs show maximum angular drift around `1e-9` to `1e-8`
  radians for `dop853_strict`.
- The app-like benchmark shows 60-second, 200 Hz median total runtime around
  `0.325s` Lagrangian and `0.375s` Hamiltonian.
- The worst tested 60-second strict DOP853 app-like row was about `0.659s`.

Interpretation: `dop853_strict` appears affordable enough locally to remain in
the policy discussion, but the extra accuracy may not be necessary as the
default app-facing policy if `dop853_moderate` passes production contract tests.

## 4. RK45 Strict Status

Provisional recommendation: keep `rk45_strict` as a fallback and comparison
candidate, not the leading candidate.

Evidence:

- It strongly improves drift over default behavior.
- It remains familiar and conservative.
- Runtime evidence does not show a decisive advantage over DOP853 policies.
- DOP853 moderate is faster than RK45 strict in the app-like 60-second median
  results while still reducing drift to the micro-radian scale.

## 5. Shared Lagrangian And Hamiltonian Policy

Provisional recommendation: use the same candidate policy for simple
Lagrangian and simple Hamiltonian paths unless targeted production tests show a
formulation-specific failure.

Evidence:

- Both formulations benefit from explicit tolerances.
- Both formulations failed the same default 60-second nonzero-velocity case.
- Both formulations remain locally affordable under DOP853 policies.
- The baseline and refreshed drift probes do not point to a simple Hamiltonian
  state-mapping defect.

Unresolved evidence gap: long-duration chaotic runs may expose
formulation-specific behavior. Measure that before declaring the shared policy
final.

## 6. Hamiltonian As Future Chaos Backbone

Provisional recommendation: keep Hamiltonian as a strong candidate for the
future chaos-investigation backbone, but do not make that architectural shift in
this pass.

Rationale:

- Hamiltonian state has the right conceptual relationship to energy and phase
  space, provided canonical momenta are handled explicitly.
- The baseline review found that the simple Hamiltonian path appears to convert
  user angular velocities to canonical momenta correctly.
- The refreshed drift evidence does not point to a Hamiltonian state-mapping
  error in the simple model.

Unresolved evidence gap: a Hamiltonian-first chaos workflow needs dedicated
tests for canonical-momentum mapping, omega reconstruction for diagnostics,
energy behavior, solver failure status, and long-duration sensitivity.

## 7. Production Tests To Add Before Solver Changes

Recommended production tests before changing solver settings:

- Simple Lagrangian/Hamiltonian agreement tests under `dop853_moderate` for
  benign and sensitive initial states.
- A comparison test or diagnostic fixture for `dop853_strict` as the
  high-fidelity reference candidate.
- Hamiltonian initial-state mapping tests verifying angular velocity to
  canonical momentum conversion.
- Hamiltonian diagnostic omega-reconstruction tests, if angular-velocity output
  remains user-facing.
- Solver metadata tests asserting success/status/message/method/tolerances and
  `nfev` are captured.
- Failure-contract tests for a known hard input where default policy failed or
  where the selected policy cannot complete.
- Energy drift smoke tests with clear tolerance bands for short deterministic
  runs.
- Payload shape and finite-value tests for callback outputs.
- Regression tests for default UI inputs and the screenshot-like `[0, 60, 0, 0]`
  case.

## 8. Solver Failure Contract

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

## 9. Remaining Evidence Gaps

Unresolved evidence gap: compound model. None of this should be generalized to
compound pendulum behavior until compound equations, state mapping, solver
runtime, and energy diagnostics have their own evidence pass.

Unresolved evidence gap: browser/rendering cost. The app-like benchmark
measures diagnostic payload construction and JSON serialization, but not Dash
callback overhead, browser transfer, browser parse time, or Canvas rendering.

Unresolved evidence gap: production payload schema. The diagnostic app-like
payload is intentionally close to app needs, but it is not the production Canvas
schema.

Unresolved evidence gap: long-duration chaos behavior. The drift investigation
uses short focused runs; longer chaotic runs need explicit scientific and UX
failure criteria.
