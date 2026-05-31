# Simple-Model Drift Investigation

Date: 2026-05-31

## Purpose

This investigation turns `development/math_fidelity/` into a reproducible
evidence lab for checking whether observed simple-model Lagrangian/Hamiltonian
drift is primarily solver-driven, state-mapping/formulation-driven, or
something else.

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

## How to Rerun

From the repository root:

```bash
.venv/bin/python development/math_fidelity/probes/investigate_simple_drift.py
```

The script writes:

- compact run logs:
  `development/math_fidelity/logs/simple_drift_results.csv`
- compact run logs as JSON:
  `development/math_fidelity/logs/simple_drift_results.json`
- Hamiltonian state-mapping checks:
  `development/math_fidelity/logs/simple_drift_mapping_checks.csv`
- Hamiltonian state-mapping checks as JSON:
  `development/math_fidelity/logs/simple_drift_mapping_checks.json`
- per-run time-series CSVs:
  `development/math_fidelity/logs/timeseries/*.csv`
- combined long-format time-series CSV:
  `development/math_fidelity/logs/timeseries/simple_drift_timeseries_long.csv`
- markdown summary table:
  `development/math_fidelity/reports/simple_drift_summary.md`

## Notebook Readiness

Future notebooks should read the generated logs by default rather than rerun
the simulations. The preferred notebook entry point is:

```python
import pandas as pd

runs = pd.read_csv("development/math_fidelity/logs/simple_drift_results.csv")
timeseries = pd.read_csv(
    "development/math_fidelity/logs/timeseries/simple_drift_timeseries_long.csv"
)
```

Rerun `investigate_simple_drift.py` only when intentionally refreshing the
evidence after a model, solver, or probe change.

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
| `dop853_strict` | `DOP853` | `1e-9` | `1e-11` |
| `dop853_reference` | `DOP853` | `1e-11` | `1e-13` |

All comparisons use the same `t_eval` grid for the Lagrangian and Hamiltonian
run in a pair.

## Summary Table

| Case | Solver | Max theta diff (rad) | Max position diff | Lag energy drift | Ham energy drift |
| --- | --- | ---: | ---: | ---: | ---: |
| `low_energy_small_angles` | default | `2.056e-4` | `1.589e-4` | `9.832e-5` | `1.007e-4` |
| `low_energy_small_angles` | RK45 strict | `3.266e-10` | `4.636e-10` | `3.537e-9` | `3.823e-9` |
| `low_energy_small_angles` | DOP853 strict | `8.675e-10` | `6.038e-10` | `4.222e-10` | `4.813e-10` |
| `low_energy_small_angles` | DOP853 reference | `1.019e-11` | `6.228e-12` | `4.192e-12` | `4.288e-12` |
| `screenshot_like_simple_start` | default | `9.528e-2` | `6.453e-2` | `3.106e-1` | `3.941e-2` |
| `screenshot_like_simple_start` | RK45 strict | `2.432e-8` | `1.465e-8` | `2.291e-7` | `1.940e-7` |
| `screenshot_like_simple_start` | DOP853 strict | `1.430e-9` | `8.700e-10` | `8.101e-9` | `1.101e-8` |
| `screenshot_like_simple_start` | DOP853 reference | `1.612e-11` | `9.557e-12` | `1.220e-10` | `1.270e-10` |
| `nonzero_velocity_spirograph` | default | `3.551e-2` | `3.529e-2` | `9.455` | `3.067` |
| `nonzero_velocity_spirograph` | RK45 strict | `2.178e-7` | `3.109e-7` | `6.588e-5` | `1.868e-5` |
| `nonzero_velocity_spirograph` | DOP853 strict | `2.638e-9` | `4.020e-9` | `5.171e-7` | `7.306e-7` |
| `nonzero_velocity_spirograph` | DOP853 reference | `5.505e-11` | `7.169e-11` | `6.350e-9` | `1.873e-8` |
| `higher_energy_wide_swing` | default | `5.959e-2` | `5.568e-2` | `1.456` | `1.015` |
| `higher_energy_wide_swing` | RK45 strict | `1.614e-7` | `1.250e-7` | `3.386e-6` | `2.390e-6` |
| `higher_energy_wide_swing` | DOP853 strict | `1.132e-8` | `1.277e-8` | `1.637e-7` | `1.961e-7` |
| `higher_energy_wide_swing` | DOP853 reference | `1.913e-10` | `1.500e-10` | `2.086e-9` | `1.473e-9` |

The full generated table is also available at:

```text
development/math_fidelity/reports/simple_drift_summary.md
```

## Does Drift Decrease With Tighter Tolerances?

Yes. Across all four cases, Lagrangian/Hamiltonian angular-coordinate drift
drops by many orders of magnitude as tolerances tighten.

The most striking case is `screenshot_like_simple_start`: default `solve_ivp`
reaches about `9.5e-2` radians maximum angular difference over four seconds,
while `DOP853` with `rtol=1e-11`, `atol=1e-13` reduces that to about
`1.6e-11` radians.

The nonzero-velocity and higher-energy cases show the same pattern. Default
solver energy drift is comparatively large; strict and reference runs reduce
both energy drift and Lagrangian/Hamiltonian trajectory disagreement.

Current evidence therefore points strongly toward solver behavior/tolerance
sensitivity as the cause of the observed simple-model Lagrangian/Hamiltonian
drift, not a simple state-mapping or sign-convention error.

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

Energy drift follows the same broad tolerance pattern as trajectory drift.
Default runs can have large drift, especially in nonzero-velocity and
higher-energy cases. Strict and reference runs reduce energy drift by many
orders of magnitude.

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

Per-run CSVs are also written with names like:

```text
development/math_fidelity/logs/timeseries/screenshot_like_simple_start__dop853_reference.csv
```

## Limitations

- This pass covers only the simple point-mass model.
- It does not validate or repair the compound model.
- It uses short, focused durations to keep the evidence fast to regenerate.
- It does not introduce production tests or production energy diagnostics.
- It does not prove long-duration scientific fidelity.
- It does not tune app defaults; it only demonstrates the effect of solver
  configuration in the evidence lab.

## Recommended Next Actions

1. Promote a small subset of this probe into focused Phase 8 tests after the
   expected tolerances and runtime budget are agreed.
2. Decide whether production simple simulations should expose solver tolerance
   controls or use stricter backend defaults.
3. Add a production-safe Hamiltonian velocity reconstruction helper if
   Hamiltonian angular-velocity diagnostics are needed.
4. Add energy drift diagnostics behind a deliberate result contract, not by
   sneaking energy fields into the existing Canvas payload.
5. Keep notebooks log-driven: load CSV/JSON evidence first, and rerun probes
   only when refreshing evidence intentionally.
