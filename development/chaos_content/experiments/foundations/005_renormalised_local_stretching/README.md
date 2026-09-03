# 005 Renormalised Local Stretching

**Status: repaired second numerical iteration completed; Outcome C — all
declared runs are numerically valid and max-step refinement is stable, but the
accumulated rate remains tolerance-sensitive and is not accepted.**

This experiment asks whether repeated perturbation renormalisation can retain a
numerically resolvable local perturbation and produce a more stable accumulated
finite-time stretching rate than the unrenormalised rate rejected by Experiment
004. It does not calculate or claim an accepted maximal Lyapunov exponent.

## Chronology

1. The original Experiment 005 contract introduced direction-preserving
   Candidate-A resets, signed growth accumulation, and the `20→40→80 s`
   duration ladder.
2. The original run showed that the reset algebra worked mechanically and that
   the direction evolved, but rejected rate convergence. Its `80 s` baseline
   and strict values were `1.039931` and `0.788167 s^-1`; the $10^{-6}$ and
   `0.125 s` cases were rejected.
3. The independent [`LYAPUNOV_REVIEW.md`](../../LYAPUNOV_REVIEW.md) audit found
   that this rejection was not trustworthy as evidence against the
   finite-shadow method. Lifted solver coordinates made relative error control
   winding-dependent, no `max_step` was set, and lifted reset reconstruction
   lost avoidable precision.
4. The repaired second iteration retains the mathematical contract and
   thresholds, but uses local angular coordinates, separate winding history,
   and one predeclared step cap plus its half-step refinement.
5. The repaired result is Outcome C. Coordinate/reconstruction and short-cycle
   energy failures disappear, while the strict-tolerance comparison still
   differs materially. The method remains numerically unresolved.

The original ignored evidence bundle remains at
`outputs/renormalised_local_stretching/baseline`; the repaired bundle is at
`outputs/renormalised_local_stretching/repaired`.

## Prior evidence and question

Experiment 003 established two dimensionally coherent nearby-state distances.
Experiment 004 then found strong perturbation collapse, substantial local
growth, compatible qualitative Candidate-A/Candidate-B behaviour, and sound
solver, sampling, and energy diagnostics. It nevertheless rejected an
approximately exponential interval under its predeclared rule because the
Candidate-A trace was curved, endpoint-sensitive, and scale-dependent.

No Experiment 004 threshold is changed or retrospectively revisited here. The
new question is:

> Can repeated renormalisation keep a nearby perturbation inside the
> empirically supported local regime while preserving its evolving direction,
> and does accumulated logarithmic stretching become more stable than the
> rejected unrenormalised finite-window rate?

A valid result is that the accumulated rate does not stabilise robustly.

## State, reference case, and working norm

The primary representation remains the simple-model Euler–Lagrange state

$$
\mathbf{x}=(\theta_1,\theta_2,\omega_1,\omega_2).
$$

The uninterrupted reference trajectory begins at

$$
\mathbf{x}_0=(179^\circ,179^\circ,0,0),
$$

with $l_1=l_2=m_1=m_2=1$ in SI units and $g=9.81\ \mathrm{m\,s^{-2}}$.
The initial nearby state uses the controlled direction

$$
\delta\mathbf{x}_0=(0,\varepsilon,0,0).
$$

This is a manually selected initial direction, not a privileged Lyapunov
direction. After evolution starts, it is never imposed again.

Candidate A is the primary working norm. Angular components use
$\operatorname{wrap}_{(-\pi,\pi]}(\theta'_i-\theta_i)$ and velocity components
use ordinary differences. With

$$
L_c=1\ \mathrm{m},
\qquad
T_c=\sqrt{\frac{L_c}{g}}=0.3192754284\ \mathrm{s},
$$

define the dimensionless scaled perturbation

$$
\mathbf{q}
=
(\Delta\theta_1,\Delta\theta_2,
T_c\Delta\omega_1,T_c\Delta\omega_2),
\qquad
d_A=\lVert\mathbf{q}\rVert_2.
$$

$L_c=1\ \mathrm{m}$ is retained for continuity, not asserted to be invariant
or uniquely correct.

## Direction-preserving reset map

Immediately before reset $k$, compute

$$
\mathbf{q}_k^-=
(\Delta\theta_{1,k}^-,\Delta\theta_{2,k}^-,
T_c\Delta\omega_{1,k}^-,T_c\Delta\omega_{2,k}^-),
\qquad
d_k^-=\lVert\mathbf{q}_k^-\rVert_2,
$$

and the evolved dimensionless direction

$$
\mathbf{u}_k=\frac{\mathbf{q}_k^-}{d_k^-}.
$$

For target Candidate-A magnitude $\varepsilon$, the post-reset scaled
perturbation is

$$
\mathbf{q}_k^+=\varepsilon\mathbf{u}_k.
$$

It is mapped back to physical EL components by

$$
\delta\mathbf{x}_k^+
=
\left(
\varepsilon u_{k,1},
\varepsilon u_{k,2},
\frac{\varepsilon u_{k,3}}{T_c},
\frac{\varepsilon u_{k,4}}{T_c}
\right),
$$

and the new algorithmic shadow state is

$$
\mathbf{x}_k^{\prime +}=\mathbf{x}_k+\delta\mathbf{x}_k^+.
$$

The physical reference state is not changed. In the repaired iteration its
angles are first canonicalised deterministically to $(-\pi,\pi]$; the reset is
constructed around that local representative and the resulting shadow angles
are canonicalised again. Tests verify the reset norm and direction across the
$-\pi/\pi$ branch and from synthetic million-turn representatives, including
at $\varepsilon=10^{-6}$.

The baseline is $\varepsilon=10^{-5}$ in Candidate-A norm. Initially this also
equals a $10^{-5}$ rad pure $\theta_2$ increment. After the first reset it is
the norm of a four-component scaled perturbation, not an angular increment.

## Reference and shadow semantics

For each repaired run, the reference remains one uninterrupted **physical**
trajectory: it is never perturbed or dynamically reset. Its coordinate chart
is rebased at each cycle boundary and DOP853 is restarted from the physically
equivalent principal-angle state. This prevents solver error control from
depending on accumulated winding while preserving exact cycle timing.

The nearby comparison is an algorithmic shadow: each segment evolves under the
same EL equations and numerical policy, but its endpoint is deliberately
reconstructed around the current reference state. It is therefore not one
uninterrupted physical trajectory.

## Cycle accumulation

For constant reset interval $\tau_r$, cycle $k$ covers
$t_{k-1}\rightarrow t_k$, with $t_k=k\tau_r$ computed from the integer cycle
index rather than repeated floating-point addition. The denominator is the
achieved Candidate-A reset magnitude at the previous boundary, including the
initial perturbation for the first cycle:

$$
g_k=\frac{d_k^-}{d_{k-1}^+},
\qquad
\ell_k=\log g_k.
$$

No negative $\ell_k$ is clipped. Contraction cycles with $g_k<1$ remain in

$$
S_N=\sum_{k=1}^{N}\ell_k,
\qquad
\Lambda_N=\frac{S_N}{t_N}.
$$

$\Lambda_N$ is called the **accumulated renormalised stretching rate** or
**cumulative finite-time rate**. It is not denoted $\lambda_{\max}$ and is not
an accepted Lyapunov exponent.

## Predeclared reset and duration policy

Experiment 004's three-perturbation common local prefix extended through
`1.29 s`. The baseline reset interval is fixed at

$$
\tau_r=0.25\ \mathrm{s},
$$

which is about $0.78T_c$ and less than one fifth of that observed local prefix.
It is chosen to reset comfortably before the prior finite perturbations lost
locality, not because it produces a smooth rate.

The controlled interval comparison is

$$
\tau_r\in\{0.125,0.25,0.5\}\ \mathrm{s}.
$$

Even the longest is below 40% of the observed prefix. These values will not be
optimised or supplemented after viewing the result.

Duration increases are staged:

```text
20 s -> inspect numerical/cycle validity
40 s -> inspect duration change
80 s -> run final convergence and robustness audit only if earlier stages pass
```

Failure at a stage stops interpretation; failed cycles are never skipped.

## Robustness cases

Only after the baseline algorithm passes cycle validity, the final-duration
audit compares:

- reset magnitudes $10^{-4}$, $10^{-5}$, and $10^{-6}$ in Candidate-A norm;
- reset intervals `0.125`, `0.25`, and `0.5 s`;
- DOP853 baseline tolerances against `rtol=1e-11`, `atol=1e-13`;
- a true Candidate-A-renormalised run using fixed $L_c=2\ \mathrm{m}$; and
- Candidate B measured along the Candidate-A-renormalised shadow segments.

The Candidate-B diagnostic uses each segment's actual Candidate-B post-reset
and pre-reset distances to accumulate its own signed log ratios. Candidate B
does **not** define these resets, so this is only a representation check along
the Candidate-A algorithmic shadow. It cannot establish Candidate-B-reset or
norm-independent convergence.

## Numerical policy and validity

The baseline retains DOP853 with `rtol=1e-9`, `atol=1e-11`. Every reference
and shadow solve now receives the predeclared bound

$$
h_{\max}=\min(T_c/32,\tau_r/25)=0.0099773571\ \mathrm{s}.
$$

This provides at least 32 permitted steps per characteristic time and 25 per
baseline reset interval. The only step-control comparison uses
$h_{\max}/2=0.0049886786\ \mathrm{s}$; neither value was selected from a rate
result. Reference energy is evaluated across the uninterrupted physical
trajectory. Nearby energy is evaluated within each segment relative to that
segment's own post-reset start. The audit found that this definition was
already correct, so the `1e-7` criterion and formula were not changed. Reset energy
jumps are recorded separately as deliberate algorithmic changes and are not
mislabelled as numerical drift.

Every cycle requires:

1. reference and shadow boundary states to be finite;
2. shadow segment solver success and complete requested output;
3. finite positive pre-reset Candidate-A and Candidate-B magnitudes;
4. $d_k^-\le10^{-2}$, retained as the empirical local guard rather than a
   universal constant;
5. achieved reset magnitude relative error at most `1e-8`;
6. maximum component error between pre- and post-reset scaled directions at
   most `1e-8`;
7. reconstructed wrapped perturbation matching the requested physical reset
   vector to absolute tolerance `1e-12`;
8. finite $g_k$, $\ell_k$, $S_N$, and $\Lambda_N$;
9. within-segment normalized energy drift at most `1e-7`.

The uninterrupted reference maximum normalized energy drift must also be at
most `1e-7`. A failed cycle rejects the entire run explicitly.

### Pre-interpretation representability calibration

The first algorithm dry run used `1e-10` reset-relative and unit-direction
component tolerances. It stopped at cycle 17 with a direction discrepancy only
slightly above `1e-10`, while the corresponding absolute scaled reset-vector
error was around machine precision and all dynamics, locality, solver, and
energy checks passed. Subtracting a $10^{-5}$ perturbation from growing
unwrapped EL angle representatives cannot support that fixed relative threshold
uniformly over long runs. Before interpreting any stretching result, both
relative/component tolerances were therefore replaced by `1e-8`. This remains
a tight $O(10^{-13})$ absolute scaled-vector check at the baseline reset size
and is applied unchanged to every subsequent run. The failed dry run is not
used as dynamical evidence.

## Predeclared convergence diagnostics

These provisional thresholds are fixed before baseline interpretation. They
are experiment-local falsification rules, not a universal definition of
convergence. Success requires all of the following at `80 s`:

1. all baseline and robustness runs pass numerical and cycle validity;
2. the baseline final-rate relative change is at most `10%` from `20→40 s`
   and at most `5%` from `40→80 s`;
3. the range of baseline cumulative rates over the final 25% of the `80 s`
   run is at most `5%` of the magnitude of its final value;
4. independently averaged signed cycle stretching over `40–60 s` and
   `60–80 s` differs by at most `10%`;
5. the final full-history rate differs by at most `5%` from the rate formed
   after excluding the predeclared first `2 s`; this is a diagnostic only—the
   primary rate always includes every cycle;
6. the three reset-magnitude final rates have relative spread at most `5%`;
7. the three reset-interval final rates have relative spread at most `10%`;
8. the strict-tolerance final rate differs from baseline by at most `1%`; and
9. the true $L_c=2\ \mathrm{m}$ renormalised final rate differs from the
   $L_c=1\ \mathrm{m}$ value by at most `5%`; and
10. the $h_{\max}/2$ final rate differs from baseline by at most `1%`.

Relative comparisons use the baseline or median magnitude as explicitly
recorded. A near-zero denominator makes the relevant diagnostic invalid rather
than automatically passing. Monotonic convergence and constant $\ell_k$ are
not required. No $R^2$ fit is used.

The `5–10%` stability limits are provisional but intentionally demand a clear
improvement over Experiment 004's `16.8%` endpoint sensitivity. Raw values are
always retained beside pass/fail results.

## Initial-direction transient

The full-history cumulative rate includes the manually chosen initial
$\theta_2$ direction. A secondary fixed `2 s` exclusion diagnostic asks whether
that initial choice still materially affects the final average. It cannot
replace the full result and will not be adjusted after inspection. Cumulative
curves at `20`, `40`, and `80 s` expose progressively longer histories without
inventing a burn-in from a visually favourable plot.

## Local angles and separate winding history

Wrapped angular differences remain part of local Candidate A. Solver-facing
reference and shadow states start every cycle in $(-\pi,\pi]$. At `0.01 s`
diagnostic samples, wrapped angular increments are accumulated into a separate
continuous reference history. That history handles positive and negative
turns, reversals, multiple turns, and principal-branch crossings; it is never
fed to DOP853, Candidate A, reset reconstruction, or acceptance. The repeatedly
reset shadow still has no natural global winding history.

## Required evidence and figures

Per-cycle JSON/CSV evidence records cycle timing, reference boundary states,
pre-reset shadow state, wrapped and scaled perturbations, pre/post magnitudes,
direction, growth factor, signed log stretching, cumulative sum/rate, Candidate
B diagnostics, solver status, checks, segment energy drift, and reset energy
change. The summary records all physical, solver, scale, duration, robustness,
convergence, timing, and claim-boundary metadata.

Deterministic figures show:

1. signed cycle $\ell_k$ values, including contractions;
2. cumulative $\Lambda_N$ versus time for staged durations;
3. pre- and post-reset magnitude verification;
4. evolution of all four scaled Candidate-A direction components;
5. reset-magnitude robustness;
6. reset-interval robustness;
7. reference/segment energy and numerical validity; and
8. fixed scaling, tolerance, and Candidate-B representation comparisons;
9. baseline/strict cycle, cumulative-rate, direction, and max-step diagnostics;
10. bounded local angles beside separately accumulated winding history.

No plot can override a failed numerical check.

## Original completed evidence and findings (first iteration)

### Observation — the baseline reset algorithm works locally

The baseline completed all `320` cycles through `80 s`. Every accepted reset
preserved the evolved scaled EL direction and restored the Candidate-A norm to
$10^{-5}$. The largest pre-reset norm was `1.65142e-4`, more than sixty times
below the retained $10^{-2}$ local ceiling. Maximum reset-relative error was
`6.01e-10` and maximum unit-direction component error was `8.17e-10`, both
inside the calibrated `1e-8` limits.

The scaled direction develops substantial contributions from all four EL
components and changes sign and orientation throughout the run. The algorithm
therefore evolves and preserves direction rather than repeatedly imposing the
initial $\theta_2$ direction.

Interpretation: repeated Candidate-A renormalisation is mechanically and
numerically viable for the baseline magnitude and interval. This establishes
an algorithmic local-stretching process, not convergence of its average.

### Observation — cycle stretching fluctuates and includes contraction

The baseline has `221` expanding and `99` contracting cycles. Signed cycle
contributions span

$$
-1.69834\le\ell_k\le2.80422.
$$

No contraction is clipped or omitted. The positive accumulated result arises
from the complete signed sum.

Interpretation: constant cycle stretching is neither observed nor required.
The relevant question remains whether these fluctuations average stably.

### Observation — duration convergence fails

The full-history baseline accumulated rates are:

| Duration | $\Lambda_N$ / $\mathrm{s}^{-1}$ |
| ---: | ---: |
| `20 s` | `0.756196` |
| `40 s` | `0.859560` |
| `80 s` | `1.039931` |

The relative changes are `12.03%` from `20→40 s` and `17.34%` from
`40→80 s`, failing the predeclared `10%` and `5%` limits. The cumulative-rate
range over the final quarter is `26.61%` of the final value. Independently
averaged block rates are `0.798642 s^-1` over `40–60 s` and
`1.641967 s^-1` over `60–80 s`, a `51.36%` difference.

Excluding the fixed first `2 s` changes the final value by `4.21%`, which passes
its secondary diagnostic. The dominant instability is therefore not explained
only by the manually chosen initial direction.

Interpretation: the cumulative average is smoother than individual cycle
stretching, but it is still drifting materially at `80 s`. The experiment does
not find robust settling with time.

### Observation — reset-magnitude robustness is incomplete

The accepted $10^{-4}$ and $10^{-5}$ runs give `1.038558` and
`1.039931 s^-1`, respectively, which is strong agreement. The $10^{-6}$ run is
explicitly rejected at `45.0 s`: its reconstructed unit-direction error reaches
`1.34e-8`, beyond the declared `1e-8` resolvability limit. Its partial rate is
retained only as `last_valid_cumulative_rate`, not treated as an `80 s` result.

Interpretation: two magnitudes support local scaling compatibility, but the
required three-magnitude spread is undefined because the smallest reset is no
longer reliably resolvable. The magnitude-robustness criterion fails rather
than silently dropping that case.

### Observation — reset-interval robustness is incomplete

The accepted `0.25 s` and `0.5 s` runs give `1.039931` and
`1.041071 s^-1`, strong agreement. The `0.125 s` run is explicitly rejected at
`18.25 s` when its within-segment normalized energy drift reaches
`2.27e-6`, above the `1e-7` limit. No failed cycle is skipped and no partial
rate is promoted to an `80 s` result.

Interpretation: the two valid intervals are compatible, but the complete
predeclared interval comparison fails numerical validity and cannot support an
interval-robust conclusion.

### Observation — scaling, representation, and tolerance

A true Candidate-A-renormalised run with $L_c=2\ \mathrm{m}$ gives
`1.043472 s^-1`, only `0.341%` from the baseline and inside the provisional
`5%` scaling check. This particular long-time accumulated result is much less
sensitive to the declared scaling change than the short-time trace shape in
Experiment 004.

Candidate B measured along the Candidate-A-reset shadow gives
`1.041027 s^-1`, qualitatively and numerically close to Candidate A. Candidate
B did not define the resets, so this is not a Candidate-B-renormalised or
norm-independent result.

The stricter-tolerance Candidate-A run gives `0.788167 s^-1`, differing from
baseline by `24.21%` and failing the `1%` tolerance criterion. Its much smaller
energy errors do not rescue agreement: over this long horizon the two numerical
policies follow materially different reference histories.

Interpretation: scale and limited Candidate-B checks are encouraging, but the
large tolerance dependence is independently sufficient to reject promotion.

### Observation — energy semantics and numerical validity

The accepted baseline uninterrupted reference has maximum normalized energy
drift `9.11e-8`, inside the `1e-7` limit. Its shadow segments have maximum
within-segment drift `5.71e-8`. Reset-induced energy changes are recorded
separately; they are deliberate consequences of reconstructing the algorithmic
shadow and are not reported as global physical-trajectory drift.

The reference winding history remains a legitimate uninterrupted trajectory
diagnostic. No cumulative winding count is assigned physical-trajectory meaning
to the repeatedly reset shadow.

### Accepted negative result

Accepted finding: repeated Candidate-A renormalisation can preserve a small,
direction-evolving local perturbation for the baseline and can accumulate both
stretching and contraction without saturation.

Rejected hypothesis: the accumulated renormalised stretching rate does not
stabilise robustly under all declared duration, reset-magnitude, reset-interval,
and tolerance checks. The values above are experiment-local finite-time
diagnostics, not a maximal Lyapunov exponent.

Unresolved choices include the EL norm, characteristic scale, reference state,
initial direction, reset magnitude, reset interval, duration, representability
floor, energy threshold, and solver policy. The evidence does not earn the
stronger maximal-Lyapunov validation experiment described below.

## Independent audit and repaired second iteration

### Repairs applied

The second iteration maps the audit findings narrowly to three code paths:

- `canonicalize_state_angles`, `integrate_rebased_reference`, and
  `reconstruct_shadow_state` keep cycle-boundary reference/shadow angles in
  $(-\pi,\pi]$ while `accumulate_lifted_angles` owns winding history outside
  the solver state;
- `solve_segment` requires an explicit `max_step`, records it with actual
  `nfev`/`njev`/`nlu` statistics, and is called with the same cap for reference
  and shadow; and
- achieved reset norm/direction are recovered around the local reference
  chart, avoiding subtraction from large lifted representatives.

The EL RHS, Cartesian state, and energy were tested under independent positive
and negative integer $2\pi$ shifts before using rebasing. The physical model,
initial state, Candidate-A norm, initial direction, reset map, signed
accumulation, duration ladder, tolerances, and original acceptance thresholds
were not changed. The segment energy definition was not changed because the
audit verified that it already used the segment's own post-reset initial
energy.

### Repaired baseline and duration convergence

All `320` baseline cycles complete and remain local. The repaired rates are:

| Duration | $\Lambda_N$ / $\mathrm{s}^{-1}$ | Relative change |
| ---: | ---: | ---: |
| `20 s` | `0.756750` | — |
| `40 s` | `0.839863` | `9.896%` (passes `10%`) |
| `80 s` | `0.903459` | `7.039%` (fails `5%`) |

The final-quarter cumulative-rate range is `9.817%` of the final value and
fails its `5%` limit. The `40–60 s` and `60–80 s` block rates are `0.923574`
and `1.010534 s^-1`, a passing `8.605%` difference. Excluding the first `2 s`
changes the rate by `5.233%`, just beyond the unchanged `5%` criterion. These
failures are retained; no duration was added to average them away.

The repaired baseline contains `215` expanding and `105` contracting cycles,
with $-1.48444\le\ell_k\le1.62763$. Its largest pre-reset Candidate-A norm is
`5.09177e-5`. Maximum reset-relative and direction-component errors are
`6.26e-11` and `6.36e-11`. Maximum reference and shadow-segment normalized
energy drifts are `4.11e-9` and `2.64e-9`, respectively.

### Repaired tolerance and step-control findings

At the baseline cap, the strict-tolerance rate is `0.806183 s^-1`, `10.767%`
below the baseline value and still outside the unchanged `1%` limit. This is
smaller than the original `24.21%` discrepancy but remains material. Both
runs use identical physical initial state, reset magnitude and interval,
rebasing, cap, cycle times, and accumulation; each complete tolerance policy
integrates its own reference.

The first baseline/strict cycle-log difference above `0.1` occurs at `27.0 s`;
the first direction-component difference above `0.1` occurs at `29.25 s`; and
the cumulative rates first differ by more than `1%` at `29.75 s`. Their
reference Candidate-A distance crosses `0.01` at `21.68 s`, `0.1` at `25.9 s`,
and `1` at `29.7 s`. The maximum direction-component difference is `1.8014`,
the maximum cumulative-rate relative difference is `17.619%`, and the final
rates do not reconverge within `1%`. Evolved direction divergence therefore
coincides with later cycle-stretching divergence, rather than a reset back to
the initial $\theta_2$ direction.

The sole half-step run gives `0.904282 s^-1`, only `0.0912%` from baseline and
passes the predeclared `1%` step-refinement check. Thus unrestricted step size
was a real original contaminant, but further reducing the repaired cap does
not explain the remaining tolerance discrepancy.

### Repaired magnitude, interval, scale, and representation findings

- Reset magnitudes $10^{-4}$, $10^{-5}$, and $10^{-6}$ give `0.901479`,
  `0.903459`, and `0.903646 s^-1`, a passing `0.240%` spread. The $10^{-6}$
  run completes all cycles; its maximum reset-relative and direction-component
  errors are `6.20e-10` and `6.42e-10`, with no failure time. The old `45 s`
  rejection was primarily a lifted-coordinate conditioning artifact.
- Reset intervals `0.125`, `0.25`, and `0.5 s` give `0.838355`, `0.903459`,
  and `0.879541 s^-1`, a passing `7.402%` spread. The `0.125 s` run completes;
  its maximum segment energy drift is `3.72e-9`. The old `18.25 s` rejection
  does not survive the explicit step/local-coordinate policy.
- The true $L_c=2\ \mathrm{m}$ run gives `0.905297 s^-1`, a passing `0.203%`
  difference from baseline.
- Candidate B measured along Candidate-A resets gives `0.910543 s^-1`, a
  `0.784%` observational difference. It still does not define the resets and
  is not a Candidate-B convergence result.

Local stored reference angles remain within `3.141585 rad`; continuous angles
inside one integration segment reach at most `5.411470 rad` before the next
rebase, rather than growing to the original tens or hundreds of radians.
Separate winding bookkeeping continues across branch crossings and records the
history without entering the norm or solver error scale.

### Outcome C — repaired method remains numerically unresolved

All required runs now pass cycle, reconstruction, locality, solver, and energy
validity. Magnitude, interval, scale, and max-step refinement checks pass. The
coordinate-conditioned $10^{-6}$ and `0.125 s` failures are repaired.

The experiment is still rejected because the strict-tolerance difference is
`10.767%`, the `40→80 s` duration change is `7.039%`, the final-quarter range
is `9.817%`, and the initial-transient comparison is `5.233%`. The original
headline values and causes are superseded, but its core claim boundary
survives: Experiment 005 still has not produced a robustly converged
accumulated stretching rate and still does not establish a maximal Lyapunov
exponent. Under the task's interpretation hierarchy this is **Outcome C**, not
an invitation to tune more finite-shadow parameters.

## Reproduction

The repaired final bundle is reproduced with:

```bash
UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run python development/chaos_content/experiments/foundations/005_renormalised_local_stretching/renormalised_local_stretching.py --max-duration 80 --self-check --output-dir development/chaos_content/outputs/renormalised_local_stretching/repaired --plots
```

Generated evidence is ignored and reproducible. `summary.json` owns the final
decision and claim boundary; `cycles.json` and `cycles.csv` preserve every
accepted and rejected cycle. `policy_comparison.csv` exposes corresponding
baseline/strict cycle logs, rates, directions, and half-step rates;
`winding_history.csv` separates bounded local angles from lifted history. The
original `baseline` bundle is intentionally not overwritten.

## Claim boundary and next question

The strongest possible success claim is:

> For this controlled EL reference trajectory and initial direction, repeated
> Candidate-A renormalisation preserves a numerically resolvable local
> perturbation and yields an accumulated logarithmic stretching rate that
> becomes substantially more stable with time and survives the declared reset,
> tolerance, and scaling comparisons.

This acceptance boundary was not met. The repaired max-step result is stable,
but independently integrated baseline/strict policies select different
long-time reference and reset-direction histories and fail the `1%` rate
criterion. Further finite-shadow parameter tuning is not justified by this
experiment. Tangent/variational dynamics is now a justified next mathematical
formulation because it would remove finite-state subtraction and repeated
shadow reconstruction, but it is not implemented here and would require a
separately validated EL-flow Jacobian.

The reference trajectory, initial direction, reset magnitude, reset interval,
scale, duration ladder, numerical policy, and thresholds remain manually
selected. Success cannot generalise this trajectory across phase space.

No Experiment 006, additional initial condition, longer duration, or tangent
dynamics is part of this repaired Experiment 005 iteration.
