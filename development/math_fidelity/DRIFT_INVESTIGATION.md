# Simple-Model Drift Investigation

Date: 2026-05-31

## Purpose

This investigation keeps `development/math_fidelity/` as a reproducible
evidence lab for checking whether observed simple-model
Lagrangian/Hamiltonian drift is primarily solver-driven,
state-mapping/formulation-driven, or something else.

This pass did not change production app behavior, UI, callbacks, Canvas
payloads, or roadmap content.

## Source Snapshot

The probes import a diagnostic source snapshot from:

```text
development/math_fidelity/snapshots/simple_model_source/
```

The copied files are listed in:

```text
development/math_fidelity/snapshots/SNAPSHOT_MANIFEST.md
```

The snapshot contains the current production math/model helpers needed to run
simple Lagrangian and Hamiltonian integrations. The copied files were not
modified after copying; relative imports allowed the package to run as
`double_pendulum_snapshot`.

## How To Rerun

From the repository root:

```bash
.venv/bin/python development/math_fidelity/probes/investigate_simple_drift.py
```

The script writes:

- `development/math_fidelity/logs/simple_drift_results.csv`
- `development/math_fidelity/logs/simple_drift_results.json`
- `development/math_fidelity/logs/simple_drift_mapping_checks.csv`
- `development/math_fidelity/logs/simple_drift_mapping_checks.json`
- `development/math_fidelity/logs/timeseries/*.csv`
- `development/math_fidelity/logs/timeseries/simple_drift_timeseries_long.csv`
- `development/math_fidelity/reports/simple_drift_summary.md`

Generated logs are the source of truth. The notebook should read those logs
rather than rerun simulations by default.

## Cases Tested

| Case | Initial state `[theta1, theta2, omega1, omega2]` | Parameters | Duration | Samples |
| --- | --- | --- | ---: | ---: |
| `low_energy_small_angles` | `[5, 7, 0, 0]` | `l1=1`, `l2=1`, `m1=1`, `m2=1`, `g=9.81` | 4 s | 800 |
| `screenshot_like_simple_start` | `[0, 60, 0, 0]` | `l1=1`, `l2=1`, `m1=1`, `m2=1`, `g=9.81` | 4 s | 800 |
| `nonzero_velocity_spirograph` | `[90, 0, 572.95, -458.37]` | `l1=1`, `l2=1.5`, `m1=3`, `m2=1`, `g=9.81` | 1 s | 400 |
| `higher_energy_wide_swing` | `[120, -120, 120, -90]` | `l1=1`, `l2=1`, `m1=1`, `m2=1`, `g=9.81` | 2 s | 600 |

Angles are degrees. Angular velocities are degrees per second.

## Solver Configurations

| Solver config | Method | rtol | atol |
| --- | --- | ---: | ---: |
| `solve_ivp_default` | SciPy default `solve_ivp` method/tolerances | default | default |
| `rk45_strict` | `RK45` | `1e-8` | `1e-10` |
| `dop853_moderate` | `DOP853` | `1e-6` | `1e-8` |
| `dop853_strict` | `DOP853` | `1e-9` | `1e-11` |
| `dop853_reference` | `DOP853` | `1e-11` | `1e-13` |

All comparisons use the same `t_eval` grid for the Lagrangian and Hamiltonian
run in a pair.

## Refreshed Row Counts

The refreshed run includes five solver configurations across four cases:

- Run-level rows: 20
- Hamiltonian mapping checks: 20
- Per-run time-series CSV files: 20
- Combined long-format time-series rows: 13,000

## Summary Table

| Case | Solver | Max theta diff (rad) | Max position diff | Lag energy drift | Ham energy drift | nfev L/H |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `low_energy_small_angles` | default | `2.056e-4` | `1.589e-4` | `9.832e-5` | `1.007e-4` | 92/86 |
| `low_energy_small_angles` | RK45 strict | `3.266e-10` | `4.636e-10` | `3.537e-9` | `3.823e-9` | 722/722 |
| `low_energy_small_angles` | DOP853 moderate | `1.434e-6` | `1.003e-6` | `3.791e-7` | `5.435e-7` | 209/209 |
| `low_energy_small_angles` | DOP853 strict | `8.675e-10` | `6.038e-10` | `4.222e-10` | `4.813e-10` | 521/416 |
| `low_energy_small_angles` | DOP853 reference | `1.019e-11` | `6.228e-12` | `4.192e-12` | `4.288e-12` | 788/701 |
| `screenshot_like_simple_start` | default | `9.528e-2` | `6.453e-2` | `3.106e-1` | `3.941e-2` | 242/248 |
| `screenshot_like_simple_start` | RK45 strict | `2.432e-8` | `1.465e-8` | `2.291e-7` | `1.940e-7` | 1622/1562 |
| `screenshot_like_simple_start` | DOP853 moderate | `2.870e-6` | `1.913e-6` | `1.721e-5` | `5.026e-6` | 1010/830 |
| `screenshot_like_simple_start` | DOP853 strict | `1.430e-9` | `8.700e-10` | `8.101e-9` | `1.101e-8` | 2045/1727 |
| `screenshot_like_simple_start` | DOP853 reference | `1.612e-11` | `9.557e-12` | `1.220e-10` | `1.270e-10` | 3482/2723 |
| `nonzero_velocity_spirograph` | default | `3.551e-2` | `3.529e-2` | `9.455` | `3.067` | 116/116 |
| `nonzero_velocity_spirograph` | RK45 strict | `2.178e-7` | `3.109e-7` | `6.588e-5` | `1.868e-5` | 722/734 |
| `nonzero_velocity_spirograph` | DOP853 moderate | `1.933e-6` | `1.868e-6` | `2.332e-4` | `1.056e-3` | 593/404 |
| `nonzero_velocity_spirograph` | DOP853 strict | `2.638e-9` | `4.020e-9` | `5.171e-7` | `7.306e-7` | 1172/971 |
| `nonzero_velocity_spirograph` | DOP853 reference | `5.505e-11` | `7.169e-11` | `6.350e-9` | `1.873e-8` | 1925/1568 |
| `higher_energy_wide_swing` | default | `5.959e-2` | `5.568e-2` | `1.456` | `1.015` | 128/98 |
| `higher_energy_wide_swing` | RK45 strict | `1.614e-7` | `1.250e-7` | `3.386e-6` | `2.390e-6` | 836/704 |
| `higher_energy_wide_swing` | DOP853 moderate | `2.646e-6` | `2.694e-6` | `1.821e-4` | `4.611e-5` | 500/413 |
| `higher_energy_wide_swing` | DOP853 strict | `1.132e-8` | `1.277e-8` | `1.637e-7` | `1.961e-7` | 1052/752 |
| `higher_energy_wide_swing` | DOP853 reference | `1.913e-10` | `1.500e-10` | `2.086e-9` | `1.473e-9` | 1754/1298 |

The full generated table is also available at:

```text
development/math_fidelity/reports/simple_drift_summary.md
```

## DOP853 Moderate Findings

High-confidence finding: `dop853_moderate` collapses
Lagrangian/Hamiltonian angular drift compared with default `solve_ivp` in all
four short drift cases.

Default-to-moderate angular-drift reduction:

| Case | Default / DOP853 moderate |
| --- | ---: |
| `low_energy_small_angles` | `1.43e2x` |
| `screenshot_like_simple_start` | `3.32e4x` |
| `nonzero_velocity_spirograph` | `1.84e4x` |
| `higher_energy_wide_swing` | `2.25e4x` |

Provisional interpretation: `dop853_moderate` is strong enough to remain the
leading latency/fidelity compromise candidate for app-facing simple-model use.
It is not as close to the reference trajectory as `dop853_strict`, but its
maximum angular drift stayed in the `1e-6` to `3e-6` radian range for these
short cases, while default drift reached `1e-4` to `1e-1` radians.

Unresolved evidence gap: final production default selection still needs
production-schema payload checks, callback failure-contract tests, browser
rendering cost, and compound-model evidence.

## Strict And Reference Comparison

`dop853_strict` remains the strongest app-facing high-fidelity candidate in
this drift probe. Its maximum angular drift stayed near `1e-9` to `1e-8`
radians, and the tighter DOP853 reference reduced drift further to about
`1e-11` to `1e-10` radians.

`rk45_strict` also performs well, with maximum angular drift around `1e-10` to
`2e-7` radians across these cases. It remains a viable fallback candidate, but
the runtime evidence does not show a decisive cost advantage over DOP853
policies.

## State-Mapping Evidence

The probe explicitly checks the Hamiltonian initial-state mapping:

1. Take user state `[theta1, theta2, omega1, omega2]`.
2. Let `DoublePendulumHamiltonian` convert the velocity entries to canonical
   momenta.
3. Reconstruct angular velocities using `B(theta)^-1 p`.
4. Compare reconstructed angular velocities to user angular velocities after
   degree-to-radian conversion.

The maximum reconstruction error was `0.0` for the zero/nonzero cases except
for the high-energy case, where it was `4.44e-16`, consistent with floating
point roundoff.

No evidence from this probe points to a Hamiltonian initialization state-mapping
defect.

## Energy Drift Observations

The probe computes simple point-mass energy as:

```text
T = 1/2 * (m1 + m2) * l1^2 * omega1^2
    + 1/2 * m2 * l2^2 * omega2^2
    + m2 * l1 * l2 * omega1 * omega2 * cos(theta1 - theta2)

V = -(m1 + m2) * g * l1 * cos(theta1)
    - m2 * g * l2 * cos(theta2)
```

For Hamiltonian runs, the probe reconstructs `omega` from canonical momenta
before computing energy. It does not treat momenta as angular velocities.

Energy drift follows the same broad solver-policy pattern as trajectory drift.
Default runs can have large drift, especially in nonzero-velocity and
higher-energy cases. `dop853_moderate` sharply improves energy behavior over
default runs, but `dop853_strict` and the reference policy remain much tighter.

For `dop853_moderate`, the median maximum energy drift across the four cases
was about `9.97e-5` for Lagrangian and `2.56e-5` for Hamiltonian. The largest
moderate-DOP853 energy drift was the Hamiltonian nonzero-velocity case at about
`1.06e-3`.

## Solver Failure Observations

In this short drift probe, no solver configuration failed for any of the four
cases. The longer 60-second solver-cost and app-like benchmarks remain the
evidence that default `solve_ivp` can fail on the nonzero-velocity simple case,
while explicit RK45/DOP853 policies complete.

## Time-Series Logs

Notebook-ready time-series logs are available under:

```text
development/math_fidelity/logs/timeseries/
```

The combined long-format CSV is:

```text
development/math_fidelity/logs/timeseries/simple_drift_timeseries_long.csv
```

It has one row per sample per run and includes:

- case name;
- solver config, solver method, `rtol`, `atol`;
- time `t`;
- Lagrangian and Hamiltonian `theta1`, `theta2`;
- absolute theta differences;
- row-level maximum angular difference;
- second-bob position values and differences;
- row-level maximum bob-position component difference;
- Lagrangian and Hamiltonian energy;
- signed, absolute, and relative energy drift.

## Limitations

- This pass covers only the simple point-mass model.
- It does not validate or repair the compound model.
- It uses short, focused drift durations to keep the evidence fast to
  regenerate.
- It does not introduce production tests or production energy diagnostics.
- It does not prove long-duration scientific fidelity.
- It does not measure production callback, browser, or Canvas rendering cost.

## Recommended Next Actions

1. Use `dop853_moderate` as the leading simple-model production-default
   candidate for the next production hardening discussion.
2. Retain `dop853_strict` as a high-fidelity and diagnostic candidate.
3. Add production tests for solver success metadata, finite outputs, energy
   drift envelopes, Hamiltonian state mapping, and Lagrangian/Hamiltonian
   agreement before changing production solver settings.
4. Harden the callback/result contract so solver failure cannot be silently
   rendered as a complete simulation.
5. Run a compound-model evidence pass before generalizing the simple-model
   policy.
