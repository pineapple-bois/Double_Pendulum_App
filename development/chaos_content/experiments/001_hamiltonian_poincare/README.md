# 001 — Minimal Hamiltonian Poincare Experiment

**Status: exploratory prior work.** Chronologically this is the first executable
Phase 10 experiment; conceptually Poincare sections now occur after sensitivity
and Lyapunov analysis. The number records history, not acceptance or maturity.

This is the first executable Phase 10 chaos-content sandbox artifact. It is a
small, self-contained simple-double-pendulum Hamiltonian experiment for
extracting a Poincare section.

It is not production code and is not imported by the Dash app.

## What It Does

The experiment integrates one simple double-pendulum trajectory in canonical
Hamiltonian coordinates and extracts section points when the trajectory crosses
the angular section

```text
theta1 mod 2*pi = 0, with theta1 increasing.
```

At each accepted crossing it records:

- `time`;
- wrapped `theta2` in radians;
- canonical momentum `p_theta2`;
- total Hamiltonian energy at the interpolated crossing;
- relative energy drift at that crossing.

The plotted pair for the section is therefore:

```text
(theta2 wrapped to [-pi, pi), p_theta2)
```

This explicitly fixes the momentum-pairing ambiguity found in the historic
`development/chaos_branch/` work.

## Conventions

- Model: simple double pendulum only.
- State vector: `(theta1, theta2, p_theta1, p_theta2)`.
- Angles: radians, measured from the downward vertical, matching the app's
  existing simple-model convention.
- Momenta: canonical Hamiltonian momenta derived from `p = B(q) * qdot`.
- Energy: unshifted Hamiltonian `H = 0.5 * p.T * B(q)^-1 * p + V(q)`.
- Energy drift: `abs(H(t) - H0) / max(abs(H0), 1.0)`.
- Section event: `sin(theta1) = 0`.
- Crossing filter: accept only event states where `cos(theta1) > 0`,
  `theta1_dot > 0`, and `time >= discard_before`.
- Section condition after filtering: `theta1 mod 2*pi = 0` with increasing
  `theta1`.
- Interpolation: `solve_ivp` event root finding locates the crossing time and
  returns the event state from the solver's dense interpolation rather than
  linearly blending sampled states.
- Solver policy: `scipy.integrate.solve_ivp`, `method="DOP853"`,
  `rtol=1e-11`, `atol=1e-13`, with explicit `t_eval`.
- Failure handling: solver failure, non-finite state values, excessive energy
  drift, or no detected section points are reported explicitly. Failed runs do
  not produce padded points.

## How To Run

From the repository root:

Smoke-test run:

```bash
python development/chaos_content/experiments/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py
```

Run the built-in smoke check:

```bash
python development/chaos_content/experiments/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py --self-check
```

Write a small smoke-test output bundle:

```bash
python development/chaos_content/experiments/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py --output-dir development/chaos_content/outputs/smoke_run --plots
```

The default 30-second run is intentionally conservative for validation. Its
Poincare plot should be treated as a smoke test if it only produces a small
number of section points.

Write a longer diagnostic bundle for a structurally meaningful plot:

```bash
python development/chaos_content/experiments/001_hamiltonian_poincare/minimal_hamiltonian_poincare.py --t-stop 300 --sample-count 12001 --discard-before 30 --min-crossings-for-plot 100 --output-dir development/chaos_content/outputs/long_run --plots
```

With `--output-dir`, the experiment writes `manifest.json`, `summary.json`, and
`poincare_points.csv`. With `--plots`, it also writes:

- `poincare_section.png`;
- `energy_drift.png`;
- `theta_timeseries.png`.

Generated outputs are exploratory diagnostics, are ignored under
`development/chaos_content/outputs/`, and should not be committed unless a
future task explicitly asks for a tiny documented artifact.

The output manifest classifies a bundle as `smoke_test_output` when accepted
crossings are below `min_crossings_for_plot`, or `long_run_diagnostic` when the
threshold is met. The plot command also emits a warning for sparse smoke-test
plots.

## What Remains Unresolved

- This has not been cross-validated against a separate symbolic derivation or a
  published reference trajectory.
- Solver-method equivalence has not been checked.
- Tolerance sensitivity has not been studied beyond the single strict policy
  encoded here.
- The compound model is intentionally out of scope.
- Long-duration scientific validity is not established.
- The section convention may be pedagogically useful, but it has not yet been
  chosen as the production Chaos page convention.
- The current wrapped event/filter implementation should still be reviewed
  against an independent reference before production use.
