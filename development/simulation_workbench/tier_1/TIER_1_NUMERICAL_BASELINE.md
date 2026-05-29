# Tier 1 Numerical Baseline

Tier: Phase 6 / Simulation Workbench Tier 1
Date: 2026-05-29
Source script: `development/simulation_workbench/tier_1/tier1_baseline.py`
Compact results: `development/simulation_workbench/tier_1/tier1_baseline_results.json`

## Summary

This Tier 1 pass measured what the current model classes produce for a small
representative matrix of simulations. It did not redesign the live
`/simulation` page, alter callbacks, change model classes, add outputs, or
claim physical correctness beyond the evidence gathered here.

The original Tier 1 baseline confirmed that the current classes can construct
four representative runs, produce finite state arrays with expected shapes,
precompute finite position arrays, and rebuild the same state arrays
deterministically for the same request on this machine. It also identified an
important absence: solver metadata was discarded.

Tier 1b updated the model layer to retain compact solver metadata. Tier 1D then
implemented the accepted Hamiltonian input convention: UI requests remain
`theta1`, `theta2`, `omega1`, `omega2`, and Hamiltonian model construction
converts angular velocities to canonical momenta before solving. The compact
JSON was regenerated after those changes.

The timings below are local measurements from one script run. Model
construction timings include equation cache lookup or derivation, lambdification,
and numerical integration because the current constructors do all of that work
together.

## Case Matrix

Shared request:

- Gravity: `9.81`
- Lengths: `l1=1.0`, `l2=1.0`
- Masses: `m1=1.0`, `m2=1.0` for simple cases; `M1=1.0`, `M2=1.0` for compound cases
- Initial conditions in current UI convention: `[45.0, -30.0, 0.0, 0.0]` degrees
- Time interval: `0.0` to `5.0` seconds
- Sample-rate rule: `200 samples per second`
- Requested sample count: `1000`
- Numerical tolerance for consistency checks: `1e-10`

| Case | Model type | System type | Model class | State variable names |
| --- | --- | --- | --- | --- |
| `simple_lagrangian` | simple | lagrangian | `DoublePendulumLagrangian` | `theta1`, `theta2`, `omega1`, `omega2` |
| `simple_hamiltonian` | simple | hamiltonian | `DoublePendulumHamiltonian` | `theta1`, `theta2`, `p_theta_1`, `p_theta_2` |
| `compound_lagrangian` | compound | lagrangian | `DoublePendulumLagrangian` | `theta1`, `theta2`, `omega1`, `omega2` |
| `compound_hamiltonian` | compound | hamiltonian | `DoublePendulumHamiltonian` | `theta1`, `theta2`, `p_theta_1`, `p_theta_2` |

## Evidence Table

All four cases completed construction and passed the core baseline checks.

| Case | Constructed | Shapes | Finite values | Monotonic time | Initial-condition match | Repeat deterministic | Positions | Warnings | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `simple_lagrangian` | yes | time `(1000,)`, state `(1000, 4)` | time/state yes | yes | yes, max diff `0.0` | yes, max diff `0.0` | `(4, 1000)`, finite yes | none | none |
| `simple_hamiltonian` | yes | time `(1000,)`, state `(1000, 4)` | time/state yes | yes | yes, max diff `0.0` | yes, max diff `0.0` | `(4, 1000)`, finite yes | converted Hamiltonian state | none |
| `compound_lagrangian` | yes | time `(1000,)`, state `(1000, 4)` | time/state yes | yes | yes, max diff `0.0` | yes, max diff `0.0` | `(4, 1000)`, finite yes | none | none |
| `compound_hamiltonian` | yes | time `(1000,)`, state `(1000, 4)` | time/state yes | yes | yes, max diff `0.0` | yes, max diff `0.0` | `(4, 1000)`, finite yes | converted Hamiltonian state | none |

Additional numerical maxima:

| Case | Max abs state value | Max abs position value |
| --- | ---: | ---: |
| `simple_lagrangian` | `5.202783` | `1.998306` |
| `simple_hamiltonian` | `3.578247` | `1.998833` |
| `compound_lagrangian` | `2.993768` | `1.999793` |
| `compound_hamiltonian` | `1.928708` | `1.999873` |

## Timing And Rendering Metrics

Timings are seconds. Plotly JSON sizes are approximate payload-size proxies from
`len(fig.to_json())`; the full plot JSON was not saved.

| Case | First construct/integrate | Repeat construct/integrate | Position precompute | Time graph build | Theta-theta projection build | Animation build |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `simple_lagrangian` | `2.1065` | `0.0204` | `0.000025` | `0.0828` | `0.0405` | `0.0283` |
| `simple_hamiltonian` | `0.3713` | `0.0323` | `0.000021` | `0.0836` | `0.0368` | `0.0210` |
| `compound_lagrangian` | `2.1831` | `0.0190` | `0.000022` | `0.0450` | `0.0816` | `0.0208` |
| `compound_hamiltonian` | `0.3681` | `0.0307` | `0.000022` | `0.0420` | `0.0364` | `0.0212` |

Rendering summary:

| Case | Time graph traces / points / JSON bytes | Projection traces / points / JSON bytes | Animation traces / frames / points / JSON bytes |
| --- | --- | --- | --- |
| `simple_lagrangian` | `2 / 2000 / 83089` | `1 / 1000 / 45622` | `3 / 100 / 2303 / 80219` |
| `simple_hamiltonian` | `2 / 2000 / 83082` | `1 / 1000 / 45614` | `3 / 100 / 2303 / 80269` |
| `compound_lagrangian` | `2 / 2000 / 83142` | `1 / 1000 / 45675` | `3 / 100 / 2303 / 81076` |
| `compound_hamiltonian` | `2 / 2000 / 83132` | `1 / 1000 / 45665` | `3 / 100 / 2303 / 80857` |

The animation frame count is `100` because the current animation method uses
every tenth sample from the `1000` requested samples.

## Tier 1b Solver Metadata Addendum

The regenerated baseline confirms that all four representative `solve_ivp`
cases now expose compact solver metadata:

| Case | Solver success | Status | Returned/requested samples | Returned time matches requested | `nfev` | `njev` | `nlu` | Metadata solution shape |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| `simple_lagrangian` | true | `0` | `1000 / 1000` | true | `290` | `0` | `0` | `(1000, 4)` |
| `simple_hamiltonian` | true | `0` | `1000 / 1000` | true | `296` | `0` | `0` | `(1000, 4)` |
| `compound_lagrangian` | true | `0` | `1000 / 1000` | true | `224` | `0` | `0` | `(1000, 4)` |
| `compound_hamiltonian` | true | `0` | `1000 / 1000` | true | `170` | `0` | `0` | `(1000, 4)` |

The model instances also retain `solver_time`; in these baseline cases it
matches the requested `pendulum.time` samples exactly.

## Hamiltonian Convention Note

The UI supplies four initial-condition values labelled as
`theta1`, `theta2`, `omega1`, and `omega2`. The Hamiltonian model state is
`theta1`, `theta2`, `p_theta_1`, and `p_theta_2`, where the final two values are
canonical momenta.

Tier 1C confirmed that directly passing nonzero UI-labelled angular velocities
into Hamiltonian momentum slots was not acceptable. Tier 1D implemented Option
1: Hamiltonian construction now converts UI angular velocities to canonical
momenta before solving. Model instances expose both the user-facing initial
conditions and the internal solver state.

The baseline request still uses zero angular velocities, so it proves the
standard array and rendering checks for the accepted path. Nonzero conversion
evidence lives in `TIER_1D_OPTION_1_HAMILTONIAN_CONVERSION.md` and
`tier1c_hamiltonian_convention_results.json`.

## Energy Diagnostics Note

No live runtime energy arrays currently exist. Symbolic energy-related
expressions exist in the math layer, including Lagrangian and Hamiltonian
expressions, but the model instances do not expose kinetic, potential, total
energy, or energy drift arrays.

Energy drift should become a future evidence gate because the app describes the
system as conservative. However, energy diagnostics should not be added casually
until the state conventions and formulas are audited for each model/system
combination, especially the Hamiltonian momentum convention and the compound
model geometry.

## Historical Missing Metadata Note

The original Tier 1 baseline found that model classes called `solve_ivp`, then
stored only `sol.y.T` as `pendulum.sol`. At that point, the following solver
metadata was not retained:

- solver success
- solver status
- solver message
- `nfev`
- `njev`
- `nlu`
- raw returned time samples from `OdeResult.t`

Tier 1b resolved this specific gap for the current `solve_ivp` path by adding
`pendulum.solver_metadata` and `pendulum.solver_time`. This matters because
future Simulation page diagnostics need to distinguish a valid completed
simulation from a solver failure, a partial solution, a slow/expensive run, or a
rendering problem.

## Interpretation

What this baseline supports:

- The four representative current model paths construct successfully on this
  machine for a 5-second, 1000-sample request.
- The four representative `solve_ivp` paths now report solver success and
  return the requested time samples.
- Time arrays have the expected shape, finite values, correct endpoints, and
  strictly increasing samples.
- State arrays have expected shape and finite values.
- The first state row matches the model's internal initial conditions for all
  four baseline cases.
- The user-facing initial-condition convention and internal solver-state
  convention are now separately recorded on model instances.
- Repeat construction with the same request produces identical state arrays
  within `1e-10` for all four baseline cases.
- Position precompute produces finite `(4, 1000)` arrays for all four baseline
  cases.
- Current graph and animation methods can produce compactly measured Plotly
  figures without saving large artifacts.

What this baseline does not support:

- It does not validate physical correctness of the equations.
- It does not validate energy conservation or energy drift.
- The zero-velocity baseline does not by itself validate Hamiltonian
  angular-velocity to canonical-momentum conversion; Tier 1D adds nonzero tests
  and compact evidence for that.
- It does not validate the current theta-theta projection as a full phase
  portrait.
- It does not test solver tolerances, alternative methods, stiff/failure
  regimes, chaotic divergence, or long-duration performance.
- It does not make the live UI consume solver metadata yet.
- It does not prove browser responsiveness or memory behavior under repeated
  UI runs.

Outputs that remain visually plausible but scientifically under-evidenced:

- The animation can look smooth while solver status and energy drift remain
  unknown.
- The theta-theta projection can look like a phase portrait, but it is only a
  two-angle state projection in the current implementation.
- Hamiltonian runs now use converted internal momenta, but energy diagnostics
  and deeper trajectory validation remain under-evidenced.

## Recommended Next Task

Recommended next task: Tier 2 first output-composition experiments.

Reason:

The result contract and baseline now show that the array plumbing is sane for
representative cases, Tier 1b captures solver metadata, and Tier 1D implements
the accepted Hamiltonian input convention. Tier 2 can begin output-composition
experiments, but energy diagnostics and stronger physical validation remain out
of scope until separately audited.

Do not implement new Simulation page visuals until that convention is resolved
or explicitly scoped out of the accepted output.
