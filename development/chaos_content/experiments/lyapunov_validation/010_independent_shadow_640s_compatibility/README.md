# 010 Independent-Shadow Compatibility at 640 Seconds

**Status: accepted at `640 s`; all predeclared continuation, settling,
between-shadow compatibility, and numerical-validity criteria pass.**

## Research question

> Does extending the same three independently integrated chaotic shadows from
> `320 s` to `640 s` bring late-window fluctuation and between-shadow spread
> below the predeclared statistical compatibility limits?

Experiment 009 was unresolved rather than incompatible. All checkpoint-drift
criteria passed and spread contracted strongly from `80` to `320 s`, but late
outer-component ranges and final/late ensemble spread remained marginally
above their limits. Experiment 010 performs exactly the one duration extension
that result earned.

## Unchanged continuation design

The following Experiment 009 choices are unchanged:

- physical initial state $(179^\circ,179^\circ,0,0)$;
- validated Euler–Lagrange flow and Jacobian;
- Candidate-A tangent geometry;
- physical-coordinate `4x4` tangent matrix;
- positive-diagonal Candidate-A-scaled QR every `0.25 s`;
- local angular rebasing and signed logarithmic accumulation; and
- the same three deterministic numerical-shadow policies:

| Shadow | DOP853 tolerances | `max_step` |
| --- | --- | ---: |
| baseline | `rtol=1e-9`, `atol=1e-11` | `0.0099773571 s` |
| strict | `rtol=1e-11`, `atol=1e-13` | `0.0099773571 s` |
| half step | `rtol=1e-9`, `atol=1e-11` | `0.0049886786 s` |

Each reference+tangent system is independently integrated once from `0` to
`640 s`. No common reference, extra shadow, altered QR cadence, or adaptive
duration extension is introduced.

## Continuation checkpoints

Record cumulative estimates at

$$
320,\ 400,\ 480,\ 560,\ 640\ \mathrm{s}.
$$

The new convergence decision uses `480→560 s`, `560→640 s`, and the
`560–640 s` late window. These preserve Experiment 009's exact `80 s`
checkpoint and late-window widths. Only their placement moves to the end of
the longer run; no threshold is relaxed by duration scaling.

The `320 s` prefix of every run must reproduce Experiment 009's committed
checkpoint vector within $10^{-12}\ \mathrm{s^{-1}}$. This verifies that
Experiment 010 is an exact continuation rather than a changed experiment.

## Retained compatibility criteria

Statistical compatibility at `640 s` requires all of:

1. every run passes the inherited solver, energy, QR, conditioning,
   reconstruction, and accumulation guards;
2. every shadow pair retains the already established decorrelation condition
   of crossing Candidate-A distance `1.0` by `80 s`;
3. every `320 s` prefix matches Experiment 009 within $10^{-12}$;
4. for every shadow, maximum component change is at most `0.08 s^-1` from
   `480→560 s` and at most `0.05 s^-1` from `560→640 s`;
5. every shadow/component cumulative range over `560–640 s` is at most
   `0.05 s^-1`;
6. at `640 s`, every between-shadow component range is at most `0.05 s^-1`
   and sample standard deviation at most `0.025 s^-1`;
7. maximum ensemble-mean component change from `560→640 s` is at most
   `0.04 s^-1`; and
8. maximum between-shadow component range anywhere over `560–640 s` is at
   most `0.07 s^-1`.

These are Experiment 009's limits applied to an identically sized terminal
window. Pointwise reference agreement remains irrelevant after decorrelation.

## Contraction and outcome rules

Compare the `640 s` spread with Experiment 009's documented values:

- `320 s` final maximum range: `0.0572795 s^-1`;
- `240–320 s` maximum between-shadow range: `0.0966596 s^-1`.

Classify the result as:

1. **Accepted statistical compatibility at `640 s`** if every compatibility
   criterion passes.
2. **Unresolved but continuing contraction** if acceptance fails, numerical
   validity/prefix/decorrelation pass, both final and late-window maximum
   ranges are smaller than their Experiment 009 counterparts, and no relevant
   drift/spread exceeds `0.10 s^-1`.
3. **Rejected for plateau or material worsening** if validity passes but a
   still-failing final or late-window spread does not contract relative to its
   Experiment 009 value, or any relevant drift/spread exceeds `0.10 s^-1`.
4. **Numerically unresolved** if solver/QR validity, prefix reproduction, or
   decorrelation fails.

These outcome rules were fixed before inspecting `640 s` output. No further
duration is implied automatically by an unresolved result.

## Ensemble estimate and uncertainty

At each checkpoint, report componentwise mean, sample standard deviation, and
range across the three deterministic shadows. Define a conservative
descriptive `640 s` uncertainty half-width for each component as the maximum
of:

- final sample standard deviation;
- half the final between-shadow range; and
- the largest absolute `560→640 s` change among the three shadows.

This envelope incorporates both ensemble spread and residual late settling.
It is not a confidence interval and does not represent uncertainty across all
initial conditions or numerical shadows. It becomes the stated uncertainty of
the strongest numerical spectrum estimate only if compatibility is accepted.

## Hamiltonian diagnostics

Report total sum, outer-pair sum, inner-pair sum, and neutral-middle magnitudes
for each checkpoint and the final ensemble mean. These remain supporting
asymptotic diagnostics and cannot override the compatibility decision.

## Claim boundary

Acceptance can establish one statistically compatible `640 s` numerical
spectrum estimate for three decorrelated deterministic Euler–Lagrange shadows
of the declared initial condition and Candidate-A protocol. It cannot establish
universality across physical initial conditions, norms, formulations, all
numerical shadows, or durations; it is not yet an independent canonical
cross-check or a general chaos classification.

## Results

### Exact continuation and reference decorrelation

Each `640 s` run contains `2560` QR cycles. At `320 s`, all twelve cumulative
components reproduce the committed Experiment 009 values exactly at stored
double precision; the maximum observed discrepancy is `0.0 s^-1`, against the
predeclared $10^{-12}\ \mathrm{s^{-1}}$ limit.

The reference shadows retain the Experiment 009 decorrelation evidence. The
baseline/strict and baseline/half-step pairs first cross Candidate-A distance
`1.0` at `35.67 s`; strict/half-step first crosses at `40.00 s`. All pass the
`80 s` deadline. Their later pointwise distances are not compatibility tests.

### Checkpoint spectra

The cumulative fixed-column estimates are:

| Shadow | `320 s` | `400 s` | `480 s` | `560 s` | `640 s` |
| --- | --- | --- | --- | --- | --- |
| baseline | `(0.990570, 0.010103, -0.007600, -0.995203)` | `(0.959678, 0.009226, -0.004903, -0.965348)` | `(0.976770, 0.012185, -0.008978, -0.981276)` | `(0.970949, 0.008732, -0.005886, -0.974721)` | `(0.977896, 0.010175, -0.007329, -0.981494)` |
| strict | `(0.950365, 0.012889, -0.009378, -0.955531)` | `(0.965021, 0.009921, -0.006517, -0.969339)` | `(0.959137, 0.004434, -0.002237, -0.962492)` | `(0.953796, 0.003869, -0.002601, -0.956260)` | `(0.977654, 0.009207, -0.006746, -0.981058)` |
| half step | `(1.005588, 0.014313, -0.008049, -1.012810)` | `(1.000703, 0.010607, -0.005761, -1.005597)` | `(1.020560, 0.009822, -0.007882, -1.023924)` | `(0.990655, 0.011072, -0.007372, -0.994402)` | `(0.994277, 0.017439, -0.015748, -0.997045)` |

All entries have units $\mathrm{s^{-1}}$. They are numerical estimates under
the declared protocol, not universal properties of the double pendulum.

### Within-shadow settling

| Shadow | Maximum `480→560 s` change | Maximum `560→640 s` change | Maximum cumulative range over `560–640 s` | Result |
| --- | ---: | ---: | ---: | --- |
| baseline | `0.006554` | `0.006947` | `0.019525` | passes |
| strict | `0.006232` | `0.024798` | `0.032468` | passes |
| half step | `0.029905` | `0.008376` | `0.022404` | passes |

Thus every run remains below the inherited `0.08`, `0.05`, and `0.05 s^-1`
limits. Compared with Experiment 009's `240–320 s` late ranges, the maxima
contract from `0.077852` to `0.019525 s^-1` for baseline, `0.052580` to
`0.032468 s^-1` for strict, and `0.046117` to `0.022404 s^-1` for half step.

### Between-shadow compatibility

| Diagnostic | `320 s` / `240–320 s` | `640 s` / `560–640 s` | Limit | Result |
| --- | ---: | ---: | ---: | --- |
| maximum final component range | `0.057279` | `0.016622` | `0.05` | passes at `640 s` |
| maximum final sample standard deviation | `0.029339` | `0.009528` | `0.025` | passes at `640 s` |
| maximum late-window between-shadow range | `0.096660` | `0.050120` | `0.07` | passes at `640 s` |
| maximum terminal ensemble-mean change | `0.014582` | `0.011475` | `0.04` | passes |

The final component ranges are

$$
(0.016622,\ 0.008233,\ 0.009002,\ 0.015988)\ \mathrm{s^{-1}},
$$

and the corresponding sample standard deviations are

$$
(0.009528,\ 0.004500,\ 0.005038,\ 0.009107)\ \mathrm{s^{-1}}.
$$

The maximum final range contracts by about `71%` from `320` to `640 s`; the
maximum matched-width late-window range contracts by about `48%`. Spread is
not monotonic at every intermediate checkpoint—for example, the maximum range
is `0.061432 s^-1` at `480 s`—but the predeclared decision concerns cumulative
settling and the terminal `560–640 s` window, not monotonic pointwise decay.

### Ensemble estimate and uncertainty

The accepted three-shadow ensemble mean at `640 s` is

$$
(0.983276,\ 0.012274,\ -0.009941,\ -0.986532)\ \mathrm{s^{-1}}.
$$

Applying the predeclared descriptive envelope gives componentwise half-widths

$$
(0.023858,\ 0.006367,\ 0.008376,\ 0.024798)\ \mathrm{s^{-1}}.
$$

Accordingly, the strongest conservative numerical summary is the ensemble
mean above with those componentwise descriptive half-widths. These widths are
the maxima of final sample standard deviation, half final range, and largest
per-shadow `560→640 s` change. They are not confidence intervals.

### Hamiltonian supporting diagnostics

For the `640 s` ensemble mean, the total sum is `-0.000924 s^-1`, the outer-
pair sum is `-0.003257 s^-1`, and the inner-pair sum is `0.002333 s^-1`. The
middle magnitudes are `0.012274` and `0.009941 s^-1`. The approximate pairing,
small middle components, and small total sum are consistent with the expected
asymptotic Hamiltonian structure, but remain supporting evidence only.

### Numerical validity

All three integrations and all `7680` aggregate cycles pass the inherited
solver, energy, QR, conditioning, reconstruction, and accumulation guards:

| Diagnostic | Ensemble extremum |
| --- | ---: |
| maximum normalized reference-energy drift | $3.42\times10^{-9}$ |
| maximum QR orthonormality error | $2.68\times10^{-15}$ |
| maximum physical reconstruction relative error | $1.12\times10^{-15}$ |
| minimum positive $R_{ii}$ | `0.0539` |
| maximum pre-QR condition number | `708.53` |

No new numerical pathology was observed.

## Verdict

Experiment 010 accepts outcome 1: **statistical compatibility at `640 s`**.
All predeclared within-shadow, final-ensemble, late-window, decorrelation,
exact-continuation, and numerical-validity conditions pass. The previously
unresolved Experiment 009 spread therefore continues to contract and falls
below the retained limits without changing the ensemble or QR protocol.

The strongest earned claim is:

> Three independently integrated, decorrelated Euler–Lagrange numerical
> shadows produce statistically compatible `640 s` cumulative four-component
> QR spectrum estimates under the declared Candidate-A protocol.

This is a defensible long-time numerical spectrum estimate for the one tested
initial condition and three numerical-shadow policies. It is not a universal
spectrum for the double pendulum, a result across physical initial conditions,
or an independent validation of the Euler–Lagrange formulation itself.

The single next scientific question is:

> Does an independently formulated Hamiltonian/canonical tangent QR
> calculation reproduce the statistically compatible Euler–Lagrange spectrum
> estimate?

Experiment 010 does not begin that cross-check.

## Evidence and reproduction

Generated evidence belongs under
`development/chaos_content/outputs/independent_shadow_640s_compatibility/baseline/`.
It includes the machine-readable summary, checkpoint vectors, cumulative
paths, pairwise reference distances, reduced cycle evidence, static plots, and
checksum manifest.

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
development/chaos_content/experiments/lyapunov_validation/010_independent_shadow_640s_compatibility/independent_shadow_640s_compatibility.py \
--output-dir development/chaos_content/outputs/independent_shadow_640s_compatibility/baseline \
--self-check
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
development/chaos_content/experiments/foundations/006_variational_dynamics_validation \
development/chaos_content/experiments/lyapunov_validation/007_full_matrix_qr_tangent_dynamics \
development/chaos_content/experiments/lyapunov_validation/008_common_reference_qr_isolation \
development/chaos_content/experiments/lyapunov_validation/009_independent_shadow_spectrum_compatibility \
development/chaos_content/experiments/lyapunov_validation/010_independent_shadow_640s_compatibility
```
