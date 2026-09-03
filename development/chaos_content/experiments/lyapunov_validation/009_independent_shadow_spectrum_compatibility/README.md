# 009 Independent-Shadow Spectrum Compatibility

**Status: unresolved at `320 s`; compatibility improves substantially but
late-window fluctuation and between-shadow spread remain marginally above the
predeclared limits.**

## Research question

> After independently integrated Euler–Lagrange reference trajectories have
> decorrelated, do their cumulative QR spectrum estimates approach
> statistically compatible long-time values?

Experiment 008 showed that the tangent tolerance, tangent step cap, and QR
cadence differences tested in Experiment 007 collapse by several orders of
magnitude on a common reference history. Experiment 009 therefore restores
independently integrated reference+tangent systems and asks whether cumulative
statistics reconcile even though their chaotic reference paths do not.

This is a compact deterministic shadow ensemble, not a parameter sweep or a
formal probabilistic sample of all trajectories.

## Retained contract

Each run reuses Experiment 007's validated system:

$$
\dot{x}=f(x),
\qquad
\dot{Y}=J(x)Y,
$$

$$
S=\operatorname{diag}(1,1,T_c,T_c),
\qquad
SY^-=QR,
\qquad
Y^+=S^{-1}Q.
$$

The physical initial condition, initial Candidate-A-orthonormal tangent basis,
positive-diagonal QR convention, `0.25 s` QR interval, signed logarithmic
accumulation, angular rebasing, and numerical validity guards remain unchanged.
No common reference interpolant is used.

## Shadow ensemble

Integrate exactly three deterministic numerical shadows from the same physical
initial state:

| Shadow | DOP853 tolerances | `max_step` | QR interval |
| --- | --- | ---: | ---: |
| baseline | `rtol=1e-9`, `atol=1e-11` | `0.0099773571 s` | `0.25 s` |
| strict | `rtol=1e-11`, `atol=1e-13` | `0.0099773571 s` | `0.25 s` |
| half step | `rtol=1e-9`, `atol=1e-11` | `0.0049886786 s` | `0.25 s` |

These are the smallest subset that reproduces Experiment 007's main
independent-reference separation while holding QR cadence fixed. They are not
random seeds and do not establish an invariant-measure ensemble.

Each shadow runs once to `320 s`, four times Experiment 007's horizon. One
continuous run supplies cumulative checkpoints at

$$
80,\ 160,\ 240,\ 320\ \mathrm{s}.
$$

No adaptive duration extension is permitted in this experiment.

## Decorrelation diagnostic

At the shared `0.01 s` reference samples, compute wrapped Candidate-A distance
for every shadow pair. A pair is operationally decorrelated after first
crossing distance `1.0`; all three pairs must cross by `80 s` for the ensemble
interpretation to be valid.

Subsequent pointwise distance is descriptive only. Chaotic references are not
required to stay separated or to approach one another, and pointwise reference
distance is not a spectrum-convergence criterion.

## Summary statistics

For each cumulative component and each shadow, record:

- checkpoint values at `80/160/240/320 s`;
- absolute change from `160→240 s` and `240→320 s`;
- the range of the cumulative estimate over `240–320 s`.

Across shadows, record at every checkpoint:

- the componentwise ensemble mean;
- sample standard deviation;
- maximum-minus-minimum range.

Also record the maximum between-shadow component range over the full
`240–320 s` window. These descriptive statistics distinguish residual
within-shadow drift from disagreement among decorrelated shadows; three
deterministic runs do not justify confidence intervals or population-level
claims.

## Predeclared acceptance criteria

The long-time cumulative estimates are **statistically compatible within this
declared numerical-shadow ensemble** only if all of the following hold:

1. every run passes Experiment 007's solver, energy, QR, conditioning,
   reconstruction, and accumulation checks;
2. every reference-shadow pair crosses Candidate-A distance `1.0` no later
   than `80 s`;
3. for every shadow, the maximum component change is at most `0.08 s^-1` from
   `160→240 s` and at most `0.05 s^-1` from `240→320 s`;
4. for every shadow and component, the cumulative range over `240–320 s` is at
   most `0.05 s^-1`;
5. at `320 s`, every component's between-shadow range is at most `0.05 s^-1`
   and sample standard deviation is at most `0.025 s^-1`;
6. the maximum ensemble-mean component change from `240→320 s` is at most
   `0.04 s^-1`; and
7. the maximum between-shadow component range anywhere over `240–320 s` is at
   most `0.07 s^-1`.

Absolute limits are used because relative differences are ill-conditioned for
the expected neutral components. The bounds require late cumulative agreement
without requiring identical local QR growth or pointwise reference shadows.

Classify the result as:

1. **Accepted statistical compatibility** if every criterion passes.
2. **Clearly incompatible at the tested horizon** if numerical validity and
   decorrelation pass but any `240→320 s` within-shadow change, final between-
   shadow range, or late-window between-shadow range exceeds `0.10 s^-1`.
3. **Unresolved at `320 s`** for intermediate failures or if validity or
   decorrelation is not established.

These criteria were fixed before inspecting the `320 s` results.

## Hamiltonian diagnostics

For each checkpoint and shadow, sort a copy of the four-vector and report total
sum, outer-pair sum, inner-pair sum, and middle-component magnitudes. Trends
toward pairing, neutral components, and zero total sum support interpretation
only. They cannot override failed compatibility criteria.

## Claim boundary

Acceptance may establish compatibility of cumulative QR estimates across
three decorrelated deterministic numerical shadows of one Euler–Lagrange
initial condition under the declared `320 s` protocol. It cannot establish
all-shadow or all-duration convergence, physical-initial-condition robustness,
norm independence, a canonical/Hamiltonian cross-check, a formal invariant-
measure result, or chaos classification.

## Results

### Reference-shadow decorrelation

All three reference pairs cross the Candidate-A distance `1.0` threshold well
before the `80 s` deadline:

| Pair | First crossing | Median distance after `80 s` | Final distance |
| --- | ---: | ---: | ---: |
| baseline / strict | `35.67 s` | `4.150` | `2.631` |
| baseline / half step | `35.67 s` | `3.956` | `3.638` |
| strict / half step | `40.00 s` | `4.062` | `2.889` |

The ensemble therefore satisfies the operational decorrelation prerequisite.
The pointwise distances remain descriptive and do not enter the compatibility
decision.

### Cumulative checkpoint spectra

The fixed-column cumulative estimates are:

| Shadow | `80 s` | `160 s` | `240 s` | `320 s` |
| --- | --- | --- | --- | --- |
| baseline | `(1.010631, 0.073345, -0.059582, -1.032261)` | `(0.998728, 0.033130, -0.019477, -1.012409)` | `(1.030264, 0.019628, -0.011315, -1.039392)` | `(0.990570, 0.010103, -0.007600, -0.995203)` |
| strict | `(0.928799, 0.054264, -0.036095, -0.955069)` | `(0.965212, 0.025177, -0.022415, -0.969254)` | `(0.975424, 0.022848, -0.015753, -0.984815)` | `(0.950365, 0.012889, -0.009378, -0.955531)` |
| half step | `(0.864843, 0.049962, -0.040601, -0.875490)` | `(0.993348, 0.024326, -0.015219, -1.006612)` | `(0.973364, 0.022755, -0.015374, -0.983084)` | `(1.005588, 0.014313, -0.008049, -1.012810)` |

These remain finite-time diagnostic vectors. Their increasing agreement does
not by itself make any one vector a converged Lyapunov spectrum.

### Within-shadow settling

| Shadow | Maximum `160→240 s` change | Maximum `240→320 s` change | Maximum cumulative range over `240–320 s` | Within-shadow result |
| --- | ---: | ---: | ---: | --- |
| baseline | `0.031536` | `0.044189` | `0.077852` | fails late-range limit |
| strict | `0.015561` | `0.029285` | `0.052580` | fails late-range limit narrowly |
| half step | `0.023528` | `0.032225` | `0.046117` | passes |

Every checkpoint-change criterion passes. The baseline and strict cumulative
outer components nevertheless explore ranges above the predeclared
`0.05 s^-1` late-window limit. Neither exceeds the `0.10 s^-1` clear-
incompatibility boundary.

### Between-shadow compatibility

| Checkpoint | Maximum component range | Maximum sample standard deviation |
| ---: | ---: | ---: |
| `80 s` | `0.156771` | `0.078389` |
| `160 s` | `0.043154` | `0.023422` |
| `240 s` | `0.056900` | `0.032273` |
| `320 s` | `0.057279` | `0.029339` |

The spread contracts markedly from `80 s`, but the `320 s` range and sample
standard deviation remain above their `0.05` and `0.025 s^-1` limits. The
maximum between-shadow range anywhere over `240–320 s` is `0.096660 s^-1`,
above its `0.07` acceptance limit but below the `0.10` clear-incompatibility
boundary.

The ensemble-mean vector changes by at most `0.014582 s^-1` from `240→320 s`,
comfortably passing its `0.04` limit. Thus the unresolved evidence is localized
to residual outer-component path fluctuation and spread rather than systematic
drift of the ensemble mean.

### Hamiltonian supporting diagnostics

At `320 s`, the ensemble mean is

$$
(0.982175,\ 0.012435,\ -0.008342,\ -0.987848)
\ \mathrm{s^{-1}}.
$$

Its total sum is `-0.001581 s^-1`, outer-pair sum is `-0.005673 s^-1`, and
inner-pair sum is `0.004093 s^-1`. The two middle magnitudes are `0.012435`
and `0.008342 s^-1`. These trends support, but do not establish, the expected
Hamiltonian asymptotic structure and do not override the failed compatibility
criteria.

### Numerical validity

All three `320 s`, `1280`-cycle runs pass the inherited numerical guards.
Across the ensemble:

| Diagnostic | Extremum |
| --- | ---: |
| maximum normalized reference-energy drift | $1.54\times10^{-9}$ |
| maximum QR orthonormality error | $2.66\times10^{-15}$ |
| maximum physical reconstruction relative error | $9.54\times10^{-16}$ |
| minimum positive $R_{ii}$ | `0.0847` |
| maximum pre-QR condition number | `708.53` |

No solver, energy, QR, conditioning, reconstruction, or bookkeeping pathology
invalidates the statistical comparison.

## Verdict

Experiment 009 accepts outcome 3: **statistical compatibility remains
unresolved at `320 s`**.

The evidence is neither accepted nor clearly incompatible. All decorrelation,
numerical-validity, checkpoint-drift, and ensemble-mean-drift checks pass, and
the between-shadow spread is much smaller than at `80 s`. However, two late
within-shadow ranges, the final ensemble range/standard deviation, and the
late-window ensemble range remain marginally above their acceptance limits.

The strongest supported statement is:

> The three independently integrated, decorrelated numerical shadows become
> substantially more compatible from `80` to `320 s` and pass every
> checkpoint-drift criterion, but residual late-window fluctuation and
> between-shadow spread remain too large for the predeclared statistical-
> compatibility claim.

The single next scientific question is:

> Does one predeclared extension of the same three-shadow ensemble to `640 s`
> reduce outer-exponent late-window drift and between-shadow spread below the
> compatibility limits?

Experiment 009 does not perform that extension.

## Evidence and reproduction

Generated evidence belongs under
`development/chaos_content/outputs/independent_shadow_spectrum_compatibility/baseline/`.
It records the summary, checkpoint vectors, full cumulative paths, pairwise
reference distances, reduced cycle evidence, static diagnostics, and checksum
manifest.

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
development/chaos_content/experiments/lyapunov_validation/009_independent_shadow_spectrum_compatibility/independent_shadow_spectrum_compatibility.py \
--output-dir development/chaos_content/outputs/independent_shadow_spectrum_compatibility/baseline \
--self-check
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
development/chaos_content/experiments/foundations/006_variational_dynamics_validation \
development/chaos_content/experiments/lyapunov_validation/007_full_matrix_qr_tangent_dynamics \
development/chaos_content/experiments/lyapunov_validation/008_common_reference_qr_isolation \
development/chaos_content/experiments/lyapunov_validation/009_independent_shadow_spectrum_compatibility
```
