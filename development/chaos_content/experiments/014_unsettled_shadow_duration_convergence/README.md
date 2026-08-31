# 014 Unsettled-Shadow Duration Convergence

**Status: executed; only IC-1 settled under the frozen `1280 s` contract.**

## Question

> For the two Experiment 012 conditions whose decorrelated independent
> Euler–Lagrange shadows remained unsettled at 640 s, does increasing the
> averaging duration produce materially improved and ultimately compatible
> cumulative spectrum estimates under the unchanged numerical protocol?

This is a targeted, outcome-conditioned follow-up for IC-1 and IC-3. It is a
new from-zero ensemble because Experiment 012 did not retain restart arrays.
It is not a new unbiased initial-condition design, a canonical comparison, or
a universal spectrum claim.

## Frozen physical and numerical contract

Only these EL initial states are included:

```text
IC-1 = (-120 deg,    0 deg, 0, 0)
IC-3 = ( 120 deg, -120 deg, 0, 0)
```

The simple model retains `m1=m2=l1=l2=1` and `g=9.81`. The tangent matrix is
initialized as `Y0=S^-1`, evolved in physical EL coordinates, and QR-reset in
Candidate-A geometry every `0.25 s`. QR uses positive diagonals, fixed unsorted
columns, locally rebased angles, and no winding in the tangent geometry.

Each condition has exactly three independently integrated DOP853 shadows:

| Policy | `rtol` | `atol` | `max_step` |
| --- | ---: | ---: | ---: |
| baseline | `1e-9` | `1e-11` | `0.0099773571 s` |
| strict | `1e-11` | `1e-13` | `0.0099773571 s` |
| half-step | `1e-9` | `1e-11` | `0.00498867855 s` |

There are exactly `2 × 3 = 6` EL integrations, each from zero to `1280 s`,
for `7680` simulated formulation-seconds and `30,720` QR cycles. No canonical,
IC-2, historical-anchor, or replacement run is permitted.

## Duration and checkpoint contract

Cumulative fixed-column spectra are recorded at

```text
320, 480, 640, 800, 960, 1120, 1280 s.
```

These are new shadows, so their `320/480/640 s` values are structural time-
scale comparisons, not continuations or prefix-reproduction tests against
Experiment 012.

Every declared analysis checkpoint is also a restart-grade QR boundary using
the accepted Experiment 013 schema. A stopped execution resumes only from its
latest complete, integrity-checked checkpoint; it does not reconstruct state.

## Frozen numerical validity

Every run must satisfy the Experiment 012 EL limits:

- complete finite integration, all segments accepted, and all `5120` cycles
  accounted for;
- normalized energy drift at most `1e-7`;
- QR orthonormality, scaled/physical reconstruction, post-reset metric
  orthonormality, reset-map, cumulative-log, and spectrum bookkeeping errors
  at most `1e-12`;
- finite positive `R_ii >= 1e-14`; and
- pre-QR scaled tangent condition number at most `1e12`.

Restart metadata and array hashes must verify at every checkpoint. Numerical
invalidity is separate from a healthy but unsettled cumulative spectrum.

## Frozen settling definitions

Experiment 012's absolute limits are retained and mechanically moved to the
declared late checkpoints. For every component:

### Per shadow

- absolute change `960→1120 s <= 0.08 s^-1`;
- absolute change `1120→1280 s <= 0.05 s^-1`; and
- range across the cumulative values at `960/1120/1280 s <= 0.05 s^-1`.

### Three-shadow ensemble

- final component range at `1280 s <= 0.05 s^-1`;
- final sample standard deviation at `1280 s <= 0.025 s^-1`;
- ensemble-mean change `1120→1280 s <= 0.04 s^-1`; and
- maximum componentwise between-shadow range observed at any of
  `960/1120/1280 s <= 0.07 s^-1`.

The final descriptive half-width is

$$
w_i=\max\left(
s_i(1280),
\frac{1}{2}\operatorname{range}_i(1280),
\max_r|\lambda_{i,r}(1280)-\lambda_{i,r}(1120)|
\right).
$$

No relative criteria, power-law fits, or post-result threshold changes are
allowed.

## Descriptive spread trend

At every checkpoint report componentwise between-shadow range and sample SD,
plus their maxima. The observed sequence may be described as decreasing,
plateauing, or irregular/non-monotonic only as qualitative evidence. No trend
label is an acceptance criterion and no `T^-1/2` law is fitted.

## Shadow independence

All three pairwise Candidate-A reference separations are sampled on the common
time grid. Record the first crossing of distance `1.0`. Decorrelation is
expected from Experiment 012 but is neither forced nor a numerical-validity
condition, and it does not classify the physical regime.

## Frozen outcomes

For each IC:

1. **numerically invalid** if any run fails the numerical contract;
2. **numerically valid but still unsettled at 1280 s** if validity passes but
   any frozen settling condition fails; or
3. **numerically valid, settled at 1280 s with demonstrated shadow
   independence** if validity and settling pass and every shadow pair crosses
   distance `1.0` by the start of the late window (`960 s`).

A settled case without demonstrated independence is reported separately and
does not receive the independent-shadow claim.

The experiment-level verdict is exactly one of: both settle; only IC-1
settles; only IC-3 settles; neither settles; or numerical invalidity. The two
conditions are never averaged together to hide a failure.

## Project-level decision rule

- If both settle, the method remains usable for these difficult conditions but
  may require substantially more than `640 s`.
- If either remains unsettled, asymptotic settling at every future map pixel
  is not a practical or justified map contract. Future map work should instead
  use a clearly labelled, predeclared fixed-horizon finite-time
  Lyapunov/stretching observable.

No map is implemented here.

## Claim boundary

For an accepted IC, the strongest claim is:

> Three independently integrated, decorrelated Euler–Lagrange numerical
> shadows produce compatible 1280 s cumulative QR spectrum estimates for this
> declared initial condition under the accepted protocol.

This is not an infinite-time spectrum, a canonical cross-check, a global
field, or a universal double-pendulum result.

## Findings

### Execution and one diagnostic repair

The pre-execution gate accepted the exact six-run workload. The first attempt
stopped after the IC-1 baseline `640→800 s` segment because a continued-run
bookkeeping check compared recursively stored cumulative logs with
`initial + cumsum(segment_logs)`. Those expressions change floating-point
association once the initial cumulative vector is nonzero. The observed log
discrepancy was `1.93e-12`, while the derived spectrum discrepancy was only
`2.66e-15 s^-1`; integration, energy, timing, QR, and every cycle were valid.

The Experiment 007 checker was corrected to replay the runner's actual
cycle-by-cycle addition order. This changes no integration, QR, or accumulation
mathematics. The affected partial output was preserved separately as
`invalidated_pre_replay_fix`, and all six preregistered runs were restarted
from zero with fresh source provenance. No threshold or scientific policy was
changed.

### Cumulative checkpoint spectra

All values below are fixed-column cumulative QR estimates in `s^-1`.

#### IC-1

| Time | baseline | strict | half-step |
| ---: | --- | --- | --- |
| 320 | `(0.883050, 0.025817, -0.019532, -0.889711)` | `(0.892939, 0.025538, -0.020962, -0.895779)` | `(0.956428, 0.021973, -0.018796, -0.959640)` |
| 480 | `(0.844436, 0.009511, -0.007526, -0.845936)` | `(0.900380, 0.017960, -0.016072, -0.901323)` | `(0.970463, 0.015263, -0.012163, -0.973789)` |
| 640 | `(0.869081, 0.012131, -0.008526, -0.872027)` | `(0.920552, 0.013284, -0.011793, -0.922134)` | `(0.957690, 0.010839, -0.008819, -0.959015)` |
| 800 | `(0.889369, 0.010117, -0.007586, -0.891287)` | `(0.903847, 0.011009, -0.009429, -0.904788)` | `(0.966041, 0.007687, -0.007040, -0.966854)` |
| 960 | `(0.919087, 0.006181, -0.005385, -0.919604)` | `(0.908894, 0.009803, -0.008480, -0.909822)` | `(0.948401, 0.006944, -0.006086, -0.948914)` |
| 1120 | `(0.924785, 0.005242, -0.003849, -0.925710)` | `(0.910024, 0.008513, -0.007449, -0.911204)` | `(0.949957, 0.006152, -0.005436, -0.950259)` |
| 1280 | `(0.934865, 0.004489, -0.003503, -0.935787)` | `(0.902596, 0.006613, -0.005780, -0.903485)` | `(0.930006, 0.005582, -0.004246, -0.930927)` |

#### IC-3

| Time | baseline | strict | half-step |
| ---: | --- | --- | --- |
| 320 | `(1.359153, 0.015794, -0.017732, -1.355480)` | `(1.399195, 0.017800, -0.018692, -1.396977)` | `(1.499052, 0.014014, -0.016052, -1.497323)` |
| 480 | `(1.372349, 0.012397, -0.011110, -1.373791)` | `(1.417509, 0.014716, -0.014382, -1.416720)` | `(1.524839, 0.009809, -0.010646, -1.524252)` |
| 640 | `(1.387218, 0.007514, -0.007928, -1.386391)` | `(1.385982, 0.008782, -0.009799, -1.385027)` | `(1.496606, 0.010051, -0.010323, -1.496330)` |
| 800 | `(1.412911, 0.007886, -0.006643, -1.413634)` | `(1.369567, 0.008278, -0.008088, -1.369239)` | `(1.493796, 0.008582, -0.008079, -1.494012)` |
| 960 | `(1.413894, 0.008536, -0.008574, -1.413861)` | `(1.373007, 0.007626, -0.007599, -1.373019)` | `(1.486030, 0.006158, -0.006589, -1.485519)` |
| 1120 | `(1.420717, 0.006357, -0.006920, -1.419768)` | `(1.379191, 0.005523, -0.005852, -1.378977)` | `(1.474743, 0.005429, -0.005731, -1.474276)` |
| 1280 | `(1.417283, 0.006405, -0.005761, -1.417632)` | `(1.387764, 0.005728, -0.005179, -1.388167)` | `(1.476707, 0.005641, -0.005400, -1.477051)` |

### Spread evolution

The table gives componentwise three-shadow ranges and sample standard
deviations in `s^-1`. `max` is the largest component at that checkpoint.

#### IC-1

| Time | component range | max range | component sample SD | max SD |
| ---: | --- | ---: | --- | ---: |
| 320 | `(0.073378, 0.003845, 0.002166, 0.069929)` | `0.073378` | `(0.039818, 0.002143, 0.001101, 0.038741)` | `0.039818` |
| 480 | `(0.126027, 0.008449, 0.008546, 0.127854)` | `0.127854` | `(0.063145, 0.004316, 0.004278, 0.064117)` | `0.064117` |
| 640 | `(0.088609, 0.002446, 0.003267, 0.086987)` | `0.088609` | `(0.044497, 0.001224, 0.001807, 0.043661)` | `0.044497` |
| 800 | `(0.076673, 0.003322, 0.002389, 0.075567)` | `0.076673` | `(0.040736, 0.001720, 0.001252, 0.040301)` | `0.040736` |
| 960 | `(0.039506, 0.003622, 0.003095, 0.039092)` | `0.039506` | `(0.020510, 0.001910, 0.001623, 0.020343)` | `0.020510` |
| 1120 | `(0.039933, 0.003270, 0.003600, 0.039055)` | `0.039933` | `(0.020191, 0.001688, 0.001804, 0.019741)` | `0.020191` |
| 1280 | `(0.032269, 0.002124, 0.002277, 0.032302)` | `0.032302` | `(0.017398, 0.001062, 0.001161, 0.017417)` | `0.017417` |

The early spread is non-monotonic, but from `480 s` onward its maximum range
contracts from `0.127854` to `0.032302 s^-1`, with a small `960→1120 s`
plateau before further contraction.

#### IC-3

| Time | component range | max range | component sample SD | max SD |
| ---: | --- | ---: | --- | ---: |
| 320 | `(0.139899, 0.003787, 0.002640, 0.141843)` | `0.141843` | `(0.072049, 0.001894, 0.001336, 0.072928)` | `0.072928` |
| 480 | `(0.152489, 0.004907, 0.003737, 0.150461)` | `0.152489` | `(0.078328, 0.002455, 0.002036, 0.077508)` | `0.078328` |
| 640 | `(0.110624, 0.002537, 0.002395, 0.111303)` | `0.111303` | `(0.063515, 0.001268, 0.001259, 0.063871)` | `0.063871` |
| 800 | `(0.124229, 0.000696, 0.001444, 0.124773)` | `0.124773` | `(0.063053, 0.000349, 0.000831, 0.063245)` | `0.063245` |
| 960 | `(0.113023, 0.002378, 0.001985, 0.112500)` | `0.113023` | `(0.057227, 0.001200, 0.000993, 0.056949)` | `0.057227` |
| 1120 | `(0.095552, 0.000928, 0.001189, 0.095299)` | `0.095552` | `(0.047912, 0.000511, 0.000655, 0.047814)` | `0.047912` |
| 1280 | `(0.088943, 0.000764, 0.000582, 0.088884)` | `0.088943` | `(0.045302, 0.000418, 0.000294, 0.045275)` | `0.045302` |

IC-3 also contracts after its `480 s` maximum, but remains well above the
frozen outer-component range and SD limits at `1280 s`; its evolution is
therefore continuing contraction, not accepted settling.

### Frozen settling decisions

For IC-1, all per-shadow late checks pass. Maximum `960→1120 s` changes are
`0.006106`, `0.001382`, and `0.001556 s^-1` for baseline, strict, and
half-step; maximum `1120→1280 s` changes are `0.010081`, `0.007720`, and
`0.019951 s^-1`. The final mean is

```text
(0.922489, 0.005561, -0.004509, -0.923400) s^-1
```

with final range
`(0.032269, 0.002124, 0.002277, 0.032302) s^-1`, sample SD
`(0.017398, 0.001062, 0.001161, 0.017417) s^-1`, and descriptive half-width
`(0.019951, 0.001899, 0.001669, 0.019332) s^-1`. The maximum ensemble-mean
`1120→1280 s` change is `0.005766 s^-1`; every frozen ensemble check passes.

For IC-3, all three individual shadows pass their late movement checks. Their
maximum `1120→1280 s` changes are `0.003434`, `0.009190`, and
`0.002774 s^-1`. The final mean is

```text
(1.427251, 0.005925, -0.005447, -1.427617) s^-1
```

but the final outer-component range is `0.088943 s^-1` against `0.05`, the
maximum final SD is `0.045302 s^-1` against `0.025`, and the maximum late-
checkpoint range is `0.113023 s^-1` against `0.07`. The ensemble-mean drift
passes at `0.003276 s^-1`. IC-3 therefore fails ensemble compatibility, not
individual cumulative movement or numerical validity.

### Independence, validity, and structure

All pairs crossed Candidate-A reference distance `1.0`: IC-1 at `32.26`,
`32.38`, and `32.58 s`; IC-3 at `16.17`, `16.19`, and `18.14 s`.

All `30,720` QR cycles and all segments are accepted. Across all six runs, the
largest normalized energy drift is `2.612e-9`, the largest QR/reset/
reconstruction error is `2.769e-15`, the minimum positive `R_ii` is
`0.07870`, and the maximum pre-QR condition number is `229.32`. Cumulative-log
and spectrum bookkeeping errors are zero under exact replay. All `42`
restart checkpoints load with matching policy and provenance and are covered
by the evidence manifest.

At `1280 s`, the IC-1 mean has total sum `1.41e-4 s^-1`, outer-pair sum
`-9.11e-4 s^-1`, and inner-pair sum `1.05e-3 s^-1`. IC-3 has total sum
`1.12e-4 s^-1`, outer-pair sum `-3.65e-4 s^-1`, and inner-pair sum
`4.78e-4 s^-1`. These are supporting finite-time Hamiltonian diagnostics,
not acceptance criteria.

## Verdict and project implication

- **IC-1:** numerically valid, settled at `1280 s`, with demonstrated shadow
  independence.
- **IC-3:** numerically valid but still unsettled at `1280 s`, despite
  demonstrated shadow independence and healthy per-shadow late movement.
- **Experiment:** only IC-1 settles under the frozen contract.

IC-1 earns the narrow independent-shadow claim stated above. IC-3 does not
earn a compatible `1280 s` ensemble estimate. Because at least one difficult
condition remains unsettled after the targeted duration extension, requiring
an asymptotically settled spectrum at every future map pixel is neither
practical nor scientifically justified by this evidence. Future teaching/map
work should use a clearly labelled, predeclared fixed-horizon finite-time
Lyapunov/stretching observable rather than present every pixel as an
asymptotic exponent.

The long-time settling investigation stops here unless a genuine numerical
defect is later found. No canonical follow-up, duration extension, convergence
law, or map has been run in Experiment 014.
