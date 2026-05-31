# App-Like Cost Benchmark

Date: 2026-05-31

## Purpose

This benchmark estimates simple-model simulation cost in a shape closer to what
the app needs after a user requests a run. It measures model construction and
solve cost, bob-position reconstruction, diagnostic Canvas-like payload
preparation, JSON serialization time, and serialized payload size.

This is Phase 8 evidence only. It does not import or change production app,
callback, or Canvas payload code.

## Design

Script:

```bash
.venv/bin/python development/math_fidelity/probes/benchmark_app_like_cost.py
```

The script imports only from the diagnostic source snapshot:

```text
development/math_fidelity/snapshots/simple_model_source/
```

It prepares a diagnostic payload with per-sample time, angular state, and bob
positions. This is intentionally a close evidence-layer equivalent, not the
production Canvas schema.

Logs:

- `development/math_fidelity/logs/app_like_cost_benchmark.csv`
- `development/math_fidelity/logs/app_like_cost_benchmark.json`

## Cases Tested

| Case | Initial user state | Parameters |
| --- | --- | --- |
| `low_energy_small_angles` | `[5, 7, 0, 0]` | `l1=l2=m1=m2=1`, `g=9.81` |
| `screenshot_like_simple_start` | `[0, 60, 0, 0]` | `l1=l2=m1=m2=1`, `g=9.81` |
| `nonzero_velocity_spirograph` | `[90, 0, 572.95, -458.37]` | `l1=1`, `l2=1.5`, `m1=3`, `m2=1`, `g=9.81` |
| `higher_energy_wide_swing` | `[120, -120, 120, -90]` | `l1=l2=m1=m2=1`, `g=9.81` |

Both simple formulations were tested:

- `lagrangian`
- `hamiltonian`

Durations and sampling:

- 10 seconds at 200 Hz
- 30 seconds at 200 Hz
- 60 seconds at 200 Hz

## Solver Policies Tested

| Solver config | Method | rtol | atol | Role |
| --- | --- | ---: | ---: | --- |
| `solve_ivp_default` | default `solve_ivp` | default | default | Negative baseline-risk policy. |
| `rk45_strict` | RK45 | `1e-8` | `1e-10` | Strict RK45 candidate. |
| `dop853_moderate` | DOP853 | `1e-6` | `1e-8` | Moderate DOP853 candidate. |
| `dop853_strict` | DOP853 | `1e-9` | `1e-11` | Strict DOP853 candidate. |

Repeat counts were 3 for 10-second rows and 2 for 30-second and 60-second rows.

## Timing Categories

Measured categories:

- `model_construction_and_solve_time_s`
- `position_reconstruction_time_s`
- `payload_preparation_time_s`
- `json_serialization_time_s`
- `total_runtime_s`

Current snapshot class design performs parameter substitution, lambdify setup,
and solving inside class construction. Exact solve time is therefore not cleanly
separated in this pass. The benchmark logs that limitation in each row.

## Headline Findings For 60-Second, 200 Hz Runs

Median total app-like runtime across cases:

| Formulation | Default | RK45 strict | DOP853 moderate | DOP853 strict |
| --- | ---: | ---: | ---: | ---: |
| Lagrangian | 0.09886s | 0.28217s | 0.18029s | 0.32524s |
| Hamiltonian | 0.11036s | 0.33168s | 0.20479s | 0.37451s |

Maximum total app-like runtime across 60-second rows:

| Formulation | Default | RK45 strict | DOP853 moderate | DOP853 strict |
| --- | ---: | ---: | ---: | ---: |
| Lagrangian | 0.84876s | 0.43221s | 0.34986s | 0.61016s |
| Hamiltonian | 0.96882s | 0.54920s | 0.32248s | 0.65949s |

The default maximums are not reassuring: both came from failed 60-second
`nonzero_velocity_spirograph` runs.

## Payload-Size Observations

For 60-second, 200 Hz runs, the diagnostic payload contains 12,000 rows when the
solver reaches the requested grid.

Median serialized JSON payload size was about 2.17 MB across solver policies:

| Solver config | Median JSON payload bytes | Max JSON payload bytes |
| --- | ---: | ---: |
| `solve_ivp_default` | 2,167,930 | 2,213,102 |
| `rk45_strict` | 2,166,829 | 2,212,968 |
| `dop853_moderate` | 2,167,395 | 2,213,199 |
| `dop853_strict` | 2,167,677 | 2,213,305 |

For 60-second rows, median JSON serialization time was about 0.033 seconds.
Median diagnostic payload preparation time was about 0.008 seconds. Position
reconstruction was negligible at roughly 0.0002 seconds.

## DOP853 Strict App-Like Affordability

DOP853 strict remains a plausible simple-model production candidate from a
local cost perspective. It was materially more expensive than default behavior,
but the 60-second app-like medians remained under 0.4 seconds for both
formulations, and the worst 60-second strict DOP853 row was about 0.66 seconds.

The per-case 60-second DOP853-strict/RK45-strict total-runtime ratios were:

| Formulation | Case | Ratio |
| --- | --- | ---: |
| Lagrangian | `higher_energy_wide_swing` | 1.24x |
| Lagrangian | `low_energy_small_angles` | 0.77x |
| Lagrangian | `nonzero_velocity_spirograph` | 1.41x |
| Lagrangian | `screenshot_like_simple_start` | 1.05x |
| Hamiltonian | `higher_energy_wide_swing` | 1.28x |
| Hamiltonian | `low_energy_small_angles` | 0.70x |
| Hamiltonian | `nonzero_velocity_spirograph` | 1.20x |
| Hamiltonian | `screenshot_like_simple_start` | 0.96x |

## Default Solver Failure

The default `solve_ivp` baseline failed for the 60-second
`nonzero_velocity_spirograph` case in both formulations with:

```text
Required step size is less than spacing between numbers.
```

This matches the solver-cost benchmark and strengthens the conclusion that
default `solve_ivp` is a risky app-facing simple-model policy for longer or
higher-energy inputs.

## Limitations

- This benchmark is simple-model only.
- It imports the diagnostic source snapshot, not live `src/`.
- It prepares a diagnostic Canvas-like payload, not the production Canvas
  schema.
- Exact solve time is not separated from model construction because the current
  class constructor performs both.
- The benchmark measures local wall-clock time; absolute timings are machine
  and environment dependent.
- It does not test Dash callback overhead, browser transfer time, rendering
  cost, or production JSON schema size.
- Compound-model behavior remains out of scope.

## Recommended Next Checks

1. Compare this diagnostic payload size with the production Canvas payload
   schema before changing callback behavior.
2. Add production numerical tests around solver success, finite outputs, energy
   drift, and Lagrangian/Hamiltonian agreement before changing solver settings.
3. Add callback-level contract tests for solver failure representation before
   exposing stricter solver policy in production.
4. Run a compound-model evidence pass before generalizing the simple-model
   solver policy.
