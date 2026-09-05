# S1 promotion validation

The existing S1 implementation passes this expanded, bounded validation on the
tested build. All **520 primary comparisons**, **240 renormalisation-prefix
checks**, and **5 additional outcome checks** agree with the trusted fast path.
The operational hybrid uses its verified fallback in 70 primary cases; S1 rejects
exactly those cases with identical max-step errors. No S1 correction was needed.

Warm same-process timing across 24 selected specifications confirms **12.22× at
T=5** and **12.70× at T=20** median speedup. This supports a guarded promotion
with the existing implementation and hybrid retained, as proposed below. It does
not establish portability to untested compilers, platforms or numerical policies.
No promotion, optimisation, production edit or field-generation run was performed.

## Scope, inputs and reproducibility

This investigation starts from `../../../PERFORMANCE_AUDIT.md` (S1),
`S1_SOLVER_BOUNDARY_PROFILE.md`, `S1_COMPILED_LOOP_PROTOTYPE.md`,
`s1_compiled_loop.py`, and the trusted Lyapunov implementation/tests. It validates
the existing compiled loop rather than redesigning it.

The new command and complete evidence are:

- `validate_s1_promotion.py`: deterministic case construction, explicit operational
  routing, numerical comparisons, prefix checks, failure checks and warm timing.
- `../evidence/s1/s1_promotion_validation.json`: every specification, outcome, comparison error,
  fallback route, final state/tangent, diagnostics, relation comparison, raw
  timing repetition, source hash and environment. Approximately 2.8 MB.
- `tests/test_s1_promotion_validation.py`: checks that the validation harness rejects
  deliberately corrupted scientific quantities, diagnostics and counts.

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m development.chaos_content.prototypes.state_space_maps.investigations.performance.s1_history.validate_s1_promotion
```

That command produced the evidence JSON. It refuses to
overwrite a file. To reproduce, append
`--output /tmp/s1-promotion-rerun.json` using a new path. Default timing is seven
paired repetitions; the explicit equivalent is `--repetitions 7`.

Environment: Python 3.12.3, NumPy 2.5.2, SciPy 1.18.0, Numba 0.67.0,
macOS 15.7.9 ARM64, Apple Clang 17.0.0 (`clang-1700.6.4.2`). S1 compiler flags
remain `-O2 -ffp-contract=on -fPIC -shared`, without fast-math. Baseline Git HEAD
is `d27b4e6587c9ee82211e488505c87f9db7e12462`; the initial worktree was clean.
The JSON hashes the validator, recorded sample and unchanged S1/native sources.

## Deterministic validation-set construction

There are **104 named specifications, 103 distinct specifications**, each tested
at **T=1, 2, 5, 10 and 20**. The one duplicate is the recorded equilibrium also
included as a domain landmark. Cases are fixed before evaluating S1; none are
removed for disagreement, route failure or speed.

| Group | Cases | Construction |
| --- | ---: | --- |
| Recorded fast/fallback | 16 | All eight of each stratum in `../evidence/s1/route_stratified_16_cells.json`, including the original S1 cells |
| Periodic-domain landmarks | 25 | Cartesian combinations of `-pi`, `-pi/2`, `0`, `pi/2`, and `nextafter(pi,0)` |
| Domain coverage | 12 | First 12 base-2/base-3 radical-inverse pairs mapped into `[-pi,pi)` |
| Reflections | 12 | Simultaneous angle reflection of those 12 pairs, with the initial tangent also negated |
| Audited route boundaries | 4 | Exact nearby fast/fallback fixtures from `tests/lyapunov/test_hybrid.py` |
| Route neighbours | 8 | One 1024-grid angular increment to either side in theta1 of the first four recorded fallback cells |
| Existing oracle fixtures | 5 | All five degree pairs from `compiled_equivalence.py` |
| Periodic lifts | 6 | Equilibrium and original interior cell, lifted by `(1,0)`, `(0,-1)`, `(10,-10)` whole turns |
| Chart seams | 4 | Adjacent floating-point values outside ±pi and values `1e-12` inside, with theta2 `-0.7` |
| Nonzero velocities | 4 | Two rotating states plus their fully reflected states/tangents |
| Reset boundaries | 3 | Intervals `0.2`, `0.5`, `1.0` with otherwise unchanged policy |
| Endpoint sensitivity | 3 | Explicit max-step `0.005`, `0.01`, and one ULP above the default cap |
| Tangent/physical geometry | 2 | Mixed initial tangent; non-default physical parameters and characteristic length |

The 25 landmark combinations are individual diagnostic calls, not a generated
field. The case list includes quiet, unstable-equilibrium and strongly stretching
regions. Except where the group explicitly changes a specification, the original
equations, default parameters, zero velocities, tangent, solver tolerances,
sampling, renormalisation and validity limits are retained. Changes to case
specifications are validation probes, not changes to configuration defaults.
Exact coordinates and all non-default values are in the script and JSON.

## Trusted comparator and route semantics

Each primary specification runs:

1. `compiled_dop853.py::run_renormalized_tangent_compiled_dop853` for the trusted
   fast-path scientific record or rejection.
2. `s1_compiled_loop.py::run_compiled_loop` for the candidate record or rejection.
3. The unchanged `hybrid.py::evaluate_renormalized_tangent_hybrid` to identify the
   actual accepted operational route and status.

Successful trusted fast records are compared with S1's full scientific record.
The operational hybrid is also checked to return the same fast value and status.
If the fast path rejects, its failure is compared with S1's failure. All observed
primary failures are max-step failures, for which the **complete error string
must match**, including the observed and declared step sizes.

The hybrid separately replays the trusted native path to verify endpoint-only
cap excess before selecting `compiled_rhs_solve_ivp_fallback`. That fallback's
rate and diagnostics are recorded as the operational outcome, but are **not**
substituted as a scientific record for the rejected S1 call. This experiment does
not claim S1 replaces or is numerically identical to the solve_ivp route. There
are no unexplained candidate-success/operational-fallback mismatches.

## Numerical gates

`compiled_equivalence.py::compare_results` is reused unchanged at every horizon.
The same absolute gates apply at T=20; none are scaled upward to accept chaos.

| Quantity | Gate |
| --- | --- |
| Final finite-time rate difference | `<= 1e-8 /s` |
| Maximum per-cycle logarithmic growth difference | `<= 5e-8` |
| Final physical state, wrapped Candidate-A distance | `<= 1e-7` |
| Final tangent, unwrapped Candidate-A norm difference | `<= 1e-7` |
| Difference in maximum normalized energy drift | `<= 1e-8` |
| Numerical validity and issue tuples | Exact agreement |
| Energy and reset-norm validity gates | Original limits from each spec (`1e-7` and `1e-12` by default) |
| RHS and segment/cycle counts; cycle-end times | Exact agreement |
| Accumulated growth | Record maximum absolute cumulative-log difference; require prefix rate difference `<= 1e-8 /s` at every cycle end |
| Log/stretch and cumulative-sum bookkeeping | Existing test tolerance `2e-15`; positive finite stretches |
| Error outcomes | Same status/class; exact text for routing-sensitive max-step failures |

The prefix-rate check applies the existing rate gate to each cumulative growth
prefix divided by its time; it does not loosen the final or cycle-log gate.
The maximum reset-norm diagnostic is compared and its gate classification must
match. Prefix runs also compare final tangent directions at successive resets.

## Complete pass/fail summary

| Horizon | Primary cases | Full scientific comparisons passed | Matching fast rejections / operational fallbacks | Discrepancies |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 104 | 98 | 6 | 0 |
| 2 | 104 | 96 | 8 | 0 |
| 5 | 104 | 89 | 15 | 0 |
| 10 | 104 | 86 | 18 | 0 |
| 20 | 104 | 81 | 23 | 0 |
| Total | **520** | **450** | **70** | **0** |

All 450 returned fast records are valid. All operational fallback records are
explicitly recorded in JSON. The sample deliberately overrepresents fallback
and boundary regions; these counts are not estimates of domain-wide frequency.

Three fixed recorded fast cases, `(145,57)`, `(294,27)` and `(440,420)`, were also
run from their original initial conditions to **each of 80 successive 0.25-second
boundaries** through T=20. All **240** full prefix comparisons pass. This checks
accumulation, angle rebasing, segment counts and reset tangent directions across
the horizon, without adding an instrumentation path to S1. It is not a trace of
every accepted internal ODE step. The script instead scans up to three failing
inputs to the first failing prefix if future runs expose discrepancies.

Five further outcome checks pass:

- A `1e-20` energy limit produces the same `completed_invalid` status and issue.
- A `1e-20` norm limit at the one-segment fixture returns valid in both paths:
  its norm error is exactly zero. The JSON calls this fixture `norm_invalid`,
  but **it does not trigger invalidity**. Actual norm-gate rejection is covered
  by the existing S1 test at T=5, run below; the fixture name is not evidence.
- A `1e-7` max-step at T=0.25 exhausts the unchanged 100,000-step budget. Both
  raise `RuntimeError`; native status 22 corresponds to trusted solver code -2.
  S1 has a shorter error message and omits the trusted warning text. This is
  recorded and is not an endpoint failure eligible for solve_ivp fallback.
- Another solver (`RK45`) raises `ValueError` in both implementations.
- Non-finite input raises the same input-validation `ValueError` in both.

No S1 implementation/numerical discrepancy required minimisation or correction.
The different generic failure wording is an interface limitation to handle by
trusted replay in the proposed architecture, not evidence of accepted bad data.

### Worst numerical discrepancies

Across the 450 primary successful pairs and 240 prefix pairs:

| Quantity | Worst observed difference |
| --- | ---: |
| Final rate | 0 |
| Per-cycle logarithmic growth | 0 |
| Accumulated logarithmic growth | 0 |
| Prefix finite-time rates | 0 |
| Final physical state distance | 0 |
| Final tangent distance | 0 |
| Maximum reset-norm diagnostic | 0 |
| RHS counts, cycle counts and end times | Identical |
| Maximum energy-drift diagnostic | **`3.621522608435875e-16`**, recorded `(294,27)` at T=16.25 |

The small energy-diagnostic discrepancy is the already known scalar C versus
NumPy rounding difference. It is below the unchanged `1e-8` comparison gate.
Among primary S1 records, the largest normalized energy drift is
`3.3793091404412423e-10`; the largest reset-norm error is
`3.3306690738754696e-16`. Both remain below their original validity limits.

## Periodicity and reflection observations

S1 matches the trusted implementation separately for every reflected/lifted
input. All available relation-rate differences also match exactly between the
two implementations. This is distinct from requiring two mathematically related
floating-point inputs to produce identical long-time trajectories.

Two inherited discrepancies were isolated further with bounded diagnostic calls:

- **Reflection:** `halton_8` is `(-2.748893571891069, 2.443460952792061)`;
  its reflection negates both angles and the tangent. The initial physical RHS
  is exactly sign-reflected. After the first T=0.25 segment, the trusted rebased
  theta1 values have a signed residual of `4.440892098500626e-16`; velocities and
  tangents still match under reflection. At T=0.5 tangent residuals also reach
  that scale. This localises the first observed symmetry loss to the initial
  segment's angle rebasing, consistent with asymmetric rounding of the existing
  `remainder(theta+pi,2*pi)-pi` operation. At T=20 the reflected rate differs by
  `1.8598324095897567e-5 /s` in **both** implementations.
- **Angle lift:** adding `(20*pi,-20*pi)` to the `(-pi,-pi)` equilibrium gives
  `(59.690260418206066,-65.97344572538566)`. Before integration, the existing RHS
  already differs in its two physical accelerations by
  `(-1.0693483178684613e-13, 9.611028079708429e-14)` due to finite-precision angle
  construction/trigonometry. The unstable equilibrium amplifies that perturbation.
  The lifted-minus-base rate difference is zero at T=1 and T=2, about
  `-1.20965e-5 /s` at T=5, `-2.38101 /s` at T=10 and `-4.05377 /s` at T=20,
  again identically in S1 and the trusted path.

The five-horizon relation measurements are in JSON. The short initial-RHS and
T=0.25/0.5 probes above were console inspections using the same case constructor
and trusted runner. These are inherited floating-point input/trajectory effects,
not grounds to relax S1's comparison gates. Promotion must not add input
canonicalisation, reflection reuse or lift-based result caching.

## Explicit fallback inventory

The following are all primary specifications for which the operational hybrid
selected its verified solve_ivp fallback. Other specifications stay fast at all
five horizons. Names resolve to exact specifications in JSON.

| Case | Fallback horizons |
| --- | --- |
| recorded_0_12 | 5, 10, 20 |
| recorded_171_983 | 1, 2, 5, 10, 20 |
| recorded_270_470 | 1, 2, 5, 10, 20 |
| recorded_389_47 | 5, 10, 20 |
| recorded_635_171 | 2, 5, 10, 20 |
| recorded_754_204 | 5, 10, 20 |
| recorded_878_958 | 20 |
| recorded_852_826 | 1, 2, 5, 10, 20 |
| recorded_1023_958 | 2, 5, 10, 20 |
| audited_boundary_0 | 5, 10, 20 |
| audited_boundary_1 | 20 |
| audited_boundary_2 | 5, 10, 20 |
| neighbor_1_-1 | 1, 2, 5, 10, 20 |
| neighbor_1_1 | 20 |
| neighbor_2_-1 | 1, 2, 5, 10, 20 |
| neighbor_2_1 | 1, 2, 5, 10, 20 |
| oracle_fixture_0 | 20 |
| oracle_fixture_3 | 20 |
| oracle_fixture_4 | 10, 20 |
| velocity_1 | 5, 10, 20 |
| velocity_reflection_1 | 5, 10, 20 |
| interval_0.2 | 10, 20 |
| cap_0.005 | 10, 20 |

T=5 route labels do not predict T=20 eligibility: even existing oracle fixtures
can encounter a later endpoint cap excess. S1 must preserve that runtime gate.

## Performance confirmation

The script selects up to 24 specifications round-robin across the defined groups,
requiring only **trusted completed-valid fast success at both T=5 and T=20**.
Selection does not filter on S1 accuracy or speed. It includes boundary neighbours,
oracle cases, reflections, lifts, nonzero velocities and non-default policies.

Both complete evaluators are warmed before timing in the same process. Seven
paired repetitions alternate evaluator order and reverse case order. Timing
includes setup, result construction and the common evaluator adapter. JIT and C
compilation are excluded. No profiler or tests ran concurrently with timing.
The aggregate is the median of per-cell ratios of median wall times.

| Horizon | Cells | Median speedup | Minimum | Maximum |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 24 | **12.216×** | 10.332× | 13.873× |
| 20 | 24 | **12.702×** | 11.038× | 14.741× |

Every measured specification improves by more than 10×. Per-cell medians follow;
all individual repetitions are in JSON.

| Case | T=5 trusted/S1 ms | Speedup | T=20 trusted/S1 ms | Speedup |
| --- | ---: | ---: | ---: | ---: |
| recorded_0_0 | 6.250 / 0.457 | 13.67× | 24.849 / 1.686 | 14.74× |
| domain_0_0 | 6.337 / 0.458 | 13.83× | 24.810 / 1.693 | 14.65× |
| halton_1 | 6.342 / 0.502 | 12.63× | 25.042 / 1.863 | 13.44× |
| reflection_1 | 6.373 / 0.500 | 12.74× | 25.128 / 1.833 | 13.71× |
| audited_boundary_3 | 7.163 / 0.610 | 11.74× | 27.519 / 2.218 | 12.41× |
| neighbor_0_-1 | 6.783 / 0.573 | 11.85× | 26.591 / 2.108 | 12.61× |
| oracle_fixture_1 | 7.025 / 0.575 | 12.22× | 28.548 / 2.319 | 12.31× |
| lift_recorded_0_0_0 | 6.304 / 0.454 | 13.87× | 24.992 / 1.731 | 14.44× |
| seam_0 | 6.786 / 0.561 | 12.10× | 26.627 / 2.091 | 12.74× |
| velocity_0 | 6.505 / 0.533 | 12.21× | 26.062 / 2.035 | 12.81× |
| interval_0.5 | 6.017 / 0.554 | 10.86× | 24.155 / 2.084 | 11.59× |
| cap_0.01 | 6.574 / 0.547 | 12.02× | 26.635 / 2.103 | 12.67× |
| mixed_tangent | 6.773 / 0.562 | 12.06× | 27.203 / 2.179 | 12.49× |
| nondefault_physics | 6.172 / 0.469 | 13.16× | 24.076 / 1.726 | 13.95× |
| recorded_145_57 | 6.696 / 0.539 | 12.43× | 27.036 / 2.174 | 12.44× |
| domain_0_1 | 6.825 / 0.559 | 12.22× | 27.197 / 2.156 | 12.62× |
| halton_2 | 6.972 / 0.574 | 12.15× | 26.254 / 2.118 | 12.40× |
| reflection_2 | 6.980 / 0.563 | 12.40× | 26.800 / 2.076 | 12.91× |
| neighbor_0_1 | 6.881 / 0.585 | 11.77× | 27.803 / 2.253 | 12.34× |
| oracle_fixture_2 | 6.886 / 0.573 | 12.01× | 27.355 / 2.211 | 12.37× |
| lift_recorded_0_0_1 | 6.309 / 0.464 | 13.58× | 24.938 / 1.720 | 14.50× |
| seam_1 | 6.768 / 0.553 | 12.24× | 26.790 / 2.080 | 12.88× |
| velocity_reflection_0 | 6.509 / 0.537 | 12.11× | 25.979 / 2.029 | 12.81× |
| interval_1.0 | 5.699 / 0.552 | 10.33× | 23.027 / 2.086 | 11.04× |

These are successful single-cell timings. They do not measure fallback cost,
worker cold starts, pools, IPC, persistence or field throughput. The duplicate
equilibrium remains visible; it does not conceal a regression in any other cell.

## Tests and repository checks

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m pytest -q -p no:cacheprovider \
  development/chaos_content/prototypes/state_space_maps/tests/lyapunov/test_reference.py \
  development/chaos_content/prototypes/state_space_maps/tests/lyapunov/test_compiled.py \
  development/chaos_content/prototypes/state_space_maps/tests/lyapunov/test_compiled_dop853.py \
  development/chaos_content/prototypes/state_space_maps/tests/lyapunov/test_hybrid.py \
  development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_history/tests/test_s1_compiled_loop.py
```

**63 passed in 10.05s.** These retain independent symbolic/RHS/JVP checks,
existing solver-oracle fixtures, routing/fallback protections and the original S1
tests, including an actually triggered norm-invalid outcome at T=5. Some existing
unit tests use tiny grid fixtures; no operational field-generation runner ran.

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/double-pendulum-mpl \
.venv/bin/python -m pytest -q -p no:cacheprovider \
  development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_history/tests/test_s1_promotion_validation.py
```

**12 passed in 1.55s.** These establish that comparison gates reject deliberately
changed rates, cumulative/cycle logs, final states/tangents, energy/norm
diagnostics, validity and RHS/cycle counts. The case constructor is also exercised
at every required horizon. Total tests run: **75 passed**.

Final checks verify benchmark source hashes and that changes are limited to new
validation artifacts. S1, its native sources, production evaluators, defaults,
fallback, persistence, rendering and multiprocessing remain unchanged.

## Limitations

- This establishes implementation equivalence on a bounded sample, not accuracy
  of arbitrary long-horizon Lyapunov results or an independent convergence proof.
  T>20, arbitrary non-default parameters and domain-wide coverage are not established.
- Exact agreement is build-dependent. The earlier prototype's failed
  contraction-disabled build remains a warning against assuming DOP853-name
  equivalence. Linux/x86, other Clang versions, SciPy versions and BLAS/Numba
  combinations were not tested here.
- Energy-diagnostic rounding is not bitwise identical. Inputs precisely at a
  validity threshold and arbitrary user-specified thresholds need additional
  guard tests before expanding eligibility beyond the standard field policy.
- Python exceptions/build failures, native crashes and memory-safety faults are
  different categories. This task exercises numerical step exhaustion and
  input rejection, not sanitizer coverage or exhaustive native fault injection.
- Prefix runs expose reset outputs, not every internal stage or accepted-step
  trace. Cold build/JIT cost, deployment packaging, process lifecycle and sustained
  field performance remain integration checks.

## Proposed promotion architecture — no integration performed

Keep the change local to the operational Lyapunov fast-evaluator selection.

1. **Eligibility before S1.** Initially allow the standard zero-velocity periodic
   angle field policy: unit lengths/masses, gravity 9.81, characteristic length 1,
   initial tangent `(1,0,0,0)`, DOP853 `rtol=1e-9`, `atol=1e-11`, resolved default
   max-step, reset interval 0.25, sampling 0.01, standard validity limits, and
   T in `{1,2,5,10,20}`. Require finite inputs in the existing periodic chart;
   do not rebase inputs as part of eligibility. Other specifications continue
   through the existing hybrid. Broader probes here are supporting evidence,
   not an obligation to expand the first promotion's scope.
2. **Validated native build.** Move the native implementation into the operational
   package only in the future integration change; production code must not import
   this investigation. Package/version the native library and retain its license.
   Load lazily with an explicit supported-build check. An unavailable or unvalidated
   build selects the existing hybrid. Initially the allowlist contains only the
   tested platform/toolchain combination; any intended deployment platform must
   pass this suite before eligibility is enabled there.
3. **Entry point.** Add S1 as the first eligible attempt at the current hybrid's
   fast-selection boundary, using the existing scalar result/diagnostic contract.
   Keep `compiled_dop853.py` intact as the comparison oracle and recovery path.
   Accept valid S1 results only under the unchanged scientific gates. Before
   accepting borderline energy diagnostics, replay through the trusted path;
   define and test this conservative guard from the existing diagnostic comparison
   tolerance rather than ignoring a threshold-sensitive status difference.
4. **Recovery and errors.** On a candidate numerical failure, obtain the authoritative
   outcome by running the original hybrid. It alone verifies endpoint-snap excess
   and decides whether to use the existing compiled-RHS solve_ivp fallback. Do not
   make all S1 failures eligible for solve_ivp and do not make the current verifier
   trust an S1 error string. This also preserves public error wording for generic
   native failures. Ineligible/build-unavailable cases go directly to the old
   hybrid. Programming/specification errors propagate; do not broadly swallow them.
   Invalid completed results need the same existing status semantics, with trusted
   replay for diagnostic-boundary ambiguity rather than automatic solver fallback.
5. **Provenance.** Give S1 a distinct accepted implementation ID, for example
   `s1_native_dop853_v1`; never label an S1 result as the legacy implementation.
   Record source digest, native build identity, SciPy/DOP source version, compiler
   and contraction flags, NumPy/Numba versions and actual accepted route. Recovery
   must retain the original accepted-route ID and separately identify the attempted
   S1/recovery reason. Preserve scientific spec identity and checksum/resume
   contracts; provenance changes require their existing integration tests.
6. **Tests gating the actual change.** Require these 520 cases, 240 prefixes,
   failure checks and 75 tests on every eligible build, without changing gates.
   Add isolated adapter tests for eligibility, unavailable build, generic native
   failure, endpoint rejection, invalid/borderline diagnostics and programming
   errors. Require exact accepted route/status comparisons against the old hybrid.
   Then run existing field-adapter, operational-runner and tiny persistence/resume
   tests for the integration and provenance change; no large field is necessary
   to validate the adapter. Confirm worker-safe build/load and cleanup and repeat
   the warmed benchmark without modifying the solver to improve its score.

This preserves the trusted mechanisms for all unsupported or rejected cases and
does not require any change to equations, tolerances, endpoint policy, fallback
verification, sampling, rendering or scheduling.

## Files changed and git status

Only four new validation artifacts were added, all under this investigation:
`validate_s1_promotion.py`, `tests/test_s1_promotion_validation.py`,
`../evidence/s1/s1_promotion_validation.json`, and this report.

```text
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/S1_PROMOTION_VALIDATION.md
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/s1_promotion_validation.json
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/test_s1_promotion_validation.py
?? development/chaos_content/prototypes/state_space_maps/investigations/performance/validate_s1_promotion.py
```

## Decision

PROMOTE — evidence supports integrating S1 as the operational fast path, while retaining the existing trusted/fallback mechanisms.
