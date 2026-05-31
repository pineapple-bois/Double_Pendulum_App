# Solver Cost Benchmark

Date: 2026-05-31

## Purpose

This benchmark measures the runtime cost of candidate `solve_ivp` solver
policies for the simple double-pendulum model. It is Phase 8 diagnostic
evidence only. It does not change production behavior and does not import live
production source.

The central question is how expensive it appears to move from the current
default `solve_ivp` behavior to explicit higher-accuracy policies such as
stricter RK45 or DOP853.

## Benchmark Design

Script:

```bash
.venv/bin/python development/math_fidelity/probes/benchmark_solver_cost.py
```

The script imports from:

```text
development/math_fidelity/snapshots/simple_model_source/
```

It warms the simple Lagrangian and Hamiltonian symbolic-equation caches before
timing so that measured rows focus on solver/runtime behavior rather than
one-time symbolic equation construction.

Rows are written to:

- `development/math_fidelity/logs/solver_cost_benchmark.csv`
- `development/math_fidelity/logs/solver_cost_benchmark.json`

Each row summarizes repeated runs for one case, formulation, duration, and
solver policy. Logged fields include sample count, sample rate, repeat count,
minimum/median/maximum runtime, function evaluations, solver success/status,
energy drift, initial conditions, physical parameters, and notes.

## Cases Tested

| Case | Initial user state | Parameters | Purpose |
| --- | --- | --- | --- |
| `low_energy_small_angles` | `[5, 7, 0, 0]` | `l1=l2=m1=m2=1`, `g=9.81` | Benign low-energy baseline. |
| `screenshot_like_simple_start` | `[0, 60, 0, 0]` | `l1=l2=m1=m2=1`, `g=9.81` | Screenshot-like simple case from drift notes. |
| `nonzero_velocity_spirograph` | `[90, 0, 572.95, -458.37]` | `l1=1`, `l2=1.5`, `m1=3`, `m2=1`, `g=9.81` | Fast nonzero angular-velocity case. |
| `higher_energy_wide_swing` | `[120, -120, 120, -90]` | `l1=l2=m1=m2=1`, `g=9.81` | Higher-energy, more sensitive case. |

Both simple formulations were benchmarked:

- `lagrangian`
- `hamiltonian`

Durations:

- 5 seconds
- 10 seconds
- 30 seconds
- 60 seconds

All runs use the app-relevant 200 Hz sample policy. The 60-second rows therefore
request 12,000 time samples.

## Solver Configurations

| Solver config | Method | rtol | atol | Role |
| --- | --- | ---: | ---: | --- |
| `solve_ivp_default` | default `solve_ivp` | default | default | Current/default behavior. |
| `rk45_moderate` | RK45 | `1e-6` | `1e-8` | Moderate tolerance candidate. |
| `rk45_strict` | RK45 | `1e-8` | `1e-10` | Strict tolerance candidate. |
| `dop853_moderate` | DOP853 | `1e-6` | `1e-8` | Moderate higher-order candidate. |
| `dop853_strict` | DOP853 | `1e-9` | `1e-11` | Strict higher-order candidate. |

Repeat counts were 3 for 5s and 10s runs, and 2 for 30s and 60s runs to keep
the pass reasonably fast while preserving the app-relevant 60-second maximum.

## Headline Runtime Findings

The benchmark generated 160 summary rows.

Median runtime across all durations and cases:

| Formulation | Default | RK45 moderate | RK45 strict | DOP853 moderate | DOP853 strict |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lagrangian | 0.02679s | 0.04319s | 0.07134s | 0.04092s | 0.06771s |
| Hamiltonian | 0.03886s | 0.05955s | 0.09590s | 0.05745s | 0.08313s |

For app-relevant 60-second, 200 Hz runs:

| Formulation | Default median | RK45 strict median | DOP853 strict median | DOP853 strict max |
| --- | ---: | ---: | ---: | ---: |
| Lagrangian | 0.05156s | 0.24628s | 0.29836s | 0.55970s |
| Hamiltonian | 0.07258s | 0.30253s | 0.31669s | 0.62037s |

These timings are local-machine measurements, not production guarantees. They
do suggest that strict DOP853 is materially more expensive than default
behavior, but still sub-second for the simple-model cases tested here.

## DOP853 Versus RK45 Cost Observations

For 60-second rows, DOP853 strict was not uniformly much slower than RK45
strict. The per-case DOP853-strict/RK45-strict runtime ratios were:

| Formulation | Case | Ratio |
| --- | --- | ---: |
| Lagrangian | `higher_energy_wide_swing` | 1.31x |
| Lagrangian | `low_energy_small_angles` | 0.68x |
| Lagrangian | `nonzero_velocity_spirograph` | 1.42x |
| Lagrangian | `screenshot_like_simple_start` | 1.08x |
| Hamiltonian | `higher_energy_wide_swing` | 1.18x |
| Hamiltonian | `low_energy_small_angles` | 0.62x |
| Hamiltonian | `nonzero_velocity_spirograph` | 1.26x |
| Hamiltonian | `screenshot_like_simple_start` | 0.91x |

This supports treating DOP853 as a plausible production-policy candidate for
the simple model, especially if the next decision is between strict RK45 and
strict DOP853 rather than between default tolerances and strict DOP853.

## Energy Drift Observations

Energy drift fell sharply when explicit tolerances were supplied.

Across 60-second rows, median maximum absolute energy drift was:

| Solver config | Median max energy drift | Worst max energy drift |
| --- | ---: | ---: |
| `solve_ivp_default` | `1.825e+01` | `6.887e+12` |
| `rk45_moderate` | `1.883e-03` | `1.113e-01` |
| `rk45_strict` | `8.783e-06` | `3.398e-04` |
| `dop853_moderate` | `1.803e-03` | `1.090e-01` |
| `dop853_strict` | `6.745e-07` | `3.418e-04` |

The extreme default worst case came from the 60-second
`nonzero_velocity_spirograph` run. In that case, default `solve_ivp` failed for
both Lagrangian and Hamiltonian formulations with:

```text
Required step size is less than spacing between numbers.
```

The explicit RK45 and DOP853 tolerance policies completed that case.

## Limitations

- The benchmark covers simple-model source only.
- It uses the diagnostic snapshot, not live `src/`.
- It measures local wall-clock runtime, so absolute timings will vary by
  machine, Python build, and installed SciPy version.
- Symbolic equation cache warmup is excluded from timed rows.
- 30-second and 60-second rows use 2 repeats rather than 3.
- The benchmark logs energy drift for each formulation, but it does not compute
  angular drift against a per-row tight reference. Use the drift investigation
  logs for Lagrangian/Hamiltonian agreement.
- Compound-model behavior is out of scope.

## Recommended Next Actions

1. Use `development/math_fidelity/explore_drift_evidence.ipynb` to compare the
   benchmark logs alongside the drift logs.
2. Treat default `solve_ivp` as risky for at least some app-relevant 60-second
   simple-model inputs.
3. Compare `rk45_strict`, `dop853_moderate`, and `dop853_strict` against UX
   latency targets before changing production solver policy.
4. If production policy changes are considered, add targeted numerical tests
   before editing the production classes.
5. Run a second pass for compound models before generalizing any simple-model
   solver-policy conclusion.
