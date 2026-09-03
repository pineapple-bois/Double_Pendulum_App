# 008 Common-Reference QR Isolation

**Status: accepted for the limited diagnostic claim that numerical reference-
shadow divergence is the primary observed source of Experiment 007's policy
separation.**

## Research question

> Is the material long-time separation between Experiment 007 refinement
> cases primarily caused by divergence of the numerical reference shadow, or
> does tangent/QR propagation itself remain materially sensitive when driven
> by a common reference history?

This experiment isolates a source of numerical separation. It does not seek a
long-time asymptotic spectrum and does not reconsider the validated Jacobian,
Candidate-A geometry, or QR primitive unless their reuse exposes a concrete
defect.

## Retained mathematical contract

The physical state, tangent matrix, and Candidate-A scaling remain

$$
x=(\theta_1,\theta_2,\omega_1,\omega_2),
\qquad
\dot{Y}=J(x)Y,
$$

$$
S=\operatorname{diag}(1,1,T_c,T_c),
\qquad
\lVert\delta x\rVert_{\mathrm{EL}}=\lVert S\delta x\rVert_2.
$$

Experiment 008 imports Experiment 007's accepted initial basis, scaled QR map,
positive-diagonal sign convention, and accumulation rule. It imports the
validated Euler–Lagrange flow and Jacobian through that dependency. The
physical reference initial state remains
$(179^\circ,179^\circ,0,0)$.

## Isolation strategy

### One common reference driver

Construct one reference-only Euler–Lagrange history over `80 s`. Its fixed
construction policy is:

- DOP853 with `rtol=1e-11`, `atol=1e-13`;
- `max_step=0.0049886786 s`, the Experiment 007 half-step cap;
- deterministic `0.125 s` reference segments;
- dense output within each segment; and
- canonical angular rebasing to $(-\pi,\pi]$ only between reference segments.

The segment grid is independent of every tangent QR interval. A tangent RHS
query at time $t$ evaluates the same stored piecewise-dense reference history
and then applies the validated $J(x(t))$. Changing tangent tolerance,
`max_step`, or QR interval cannot alter or restart the reference solution.

This deliberately replaces a jointly adaptive reference+tangent solve with a
nonautonomous tangent solve driven by an interpolant. The result diagnoses the
declared common numerical history; it does not prove invariance to the choice
of reference history.

### Interpolation and reference control

Dense interpolation is not assumed exact. For every `0.125 s` reference
segment, independently integrate the same segment-start state with DOP853,
`rtol=1e-12`, `atol=1e-14`, and half the common-driver step cap. Compare the
common dense solution and this local refined solution at the segment midpoint
and endpoint using wrapped Candidate-A state distance.

This is a local interpolation/integration defect check: the companion is
restarted from the common segment state so chaotic global shadow divergence
cannot accumulate inside the validation measure. It does not claim that a
separately accumulated refined `80 s` reference would remain close.

Reference construction is valid only if:

1. every common and local-refinement segment succeeds with finite output;
2. the maximum local Candidate-A discrepancy is at most $10^{-8}$;
3. normalized reference energy drift remains at most $10^{-7}$; and
4. stored reference times and segment selection are deterministic and complete.

## Compact tangent/QR matrix

All cases use the identical common reference driver and the Experiment 007
initial tangent basis. Only tangent integration and QR policy change:

| Case | Tangent tolerances | Tangent `max_step` | QR interval |
| --- | --- | ---: | ---: |
| baseline | `rtol=1e-9`, `atol=1e-11` | `0.0099773571 s` | `0.25 s` |
| strict tangent | `rtol=1e-11`, `atol=1e-13` | baseline | `0.25 s` |
| half tangent step | baseline | `0.0049886786 s` | `0.25 s` |
| short QR interval | baseline | baseline | `0.125 s` |
| long QR interval | baseline | baseline | `0.5 s` |

No additional duration, reference trajectory, tangent basis, solver policy, or
QR interval is part of the declared matrix.

Every tangent run must pass the existing Experiment 007 QR, reconstruction,
conditioning, finite-accumulation, solver-completion, and bookkeeping guards.
The common reference itself supplies the shared energy-validity check.

## Predeclared diagnostic criteria

Compare cumulative estimates in fixed QR-column order at `80 s` and at all
common `0.5 s` boundaries over `60–80 s`. Per-cycle QR growth is not an
acceptance quantity.

Retain Experiment 007's absolute limits:

- strict tangent versus baseline: `0.01 s^-1`;
- half tangent step versus baseline: `0.01 s^-1`;
- either QR-interval variant versus baseline: `0.02 s^-1`.

For context, Experiment 007's corresponding final maximum differences with
independently integrated references were respectively `0.081832`, `0.156771`,
`0.149611`, and `0.102732 s^-1`. Define the separation ratio as the new maximum
component difference divided by that documented Experiment 007 value.

Classify the diagnostic as follows:

1. **Reference-shadow divergence is the primary observed source** if all
   reference and tangent validity checks pass, every final and late-window
   common-reference difference meets its absolute limit, and every final
   separation ratio is at most `0.25`.
2. **Material tangent/QR-policy dependence remains** if validity passes and at
   least one comparison both exceeds its absolute limit and retains at least
   `0.50` of its Experiment 007 separation at `80 s` or across the late window.
3. **Isolation numerically unresolved** if reference/interpolation validity
   fails or the evidence lies between those two boundaries.

These thresholds distinguish near-collapse from a merely smaller discrepancy.
They were fixed before interpreting the full diagnostic.

## Claim boundary

Acceptance can identify the dominant observed source of Experiment 007's
policy separation under one common, validated numerical reference history. It
cannot establish a converged Lyapunov spectrum, prove independence from the
reference history, choose an asymptotic duration, validate a canonical or
Hamiltonian formulation, or classify chaos.

## Results

### Common-reference validity

The `80 s` reference history contains `640` fixed `0.125 s` segments. Every
common and local-refinement solve succeeds. The maximum wrapped Candidate-A
difference between the common dense solution and the tighter, half-step local
companion is

$$
1.115\times10^{-11},
$$

well inside the predeclared $10^{-8}$ limit. Maximum normalized reference
energy drift is $2.210\times10^{-11}$, inside the inherited $10^{-7}$ limit.
The common construction uses `252713` RHS evaluations; the independent local
validation uses `396800`.

These results support the piecewise-dense history as a sufficiently resolved
common driver for this diagnostic. They do not show that another independently
accumulated `80 s` reference would follow the same chaotic shadow.

### Tangent/QR comparison

The baseline common-reference cumulative diagnostic at `80 s` is

$$
(0.855142775,\ 0.068817519,\ -0.048982863,\ -0.880814441)
\ \mathrm{s^{-1}}.
$$

The policy comparisons are:

| Case | `80 s` cumulative diagnostic / $\mathrm{s^{-1}}$ | Final maximum difference / $\mathrm{s^{-1}}$ | `60–80 s` maximum | Ratio to Experiment 007 separation |
| --- | --- | ---: | ---: | ---: |
| strict tangent | `(0.855142774, 0.068816884, -0.048982226, -0.880814442)` | $6.365\times10^{-7}$ | $7.223\times10^{-7}$ | $7.78\times10^{-6}$ |
| half tangent step | `(0.855142774, 0.068816961, -0.048982303, -0.880814442)` | $5.598\times10^{-7}$ | $6.355\times10^{-7}$ | $3.57\times10^{-6}$ |
| `0.125 s` QR interval | `(0.855142775, 0.068817486, -0.048982829, -0.880814442)` | $3.320\times10^{-8}$ | $3.737\times10^{-8}$ | $2.22\times10^{-7}$ |
| `0.5 s` QR interval | `(0.855142774, 0.068817579, -0.048982923, -0.880814441)` | $6.018\times10^{-8}$ | $6.799\times10^{-8}$ | $5.86\times10^{-7}$ |

All final and late-window values are many orders below their `0.01` or
`0.02 s^-1` absolute limits. Every final separation ratio is far below the
predeclared `0.25` collapse boundary; none approaches the `0.50` material-
remainder boundary.

### QR and tangent numerical validity

All five tangent runs complete with finite, independently recomputable
accumulation. Across the matrix:

| Diagnostic | Extremum |
| --- | ---: |
| maximum QR orthonormality error | $2.18\times10^{-15}$ |
| maximum physical reconstruction relative error | $7.59\times10^{-16}$ |
| minimum positive $R_{ii}$ | `0.0340` |
| maximum pre-QR condition number | `5576.49` |

The long-interval condition number remains far inside Experiment 007's broad
$10^{12}$ pathology guard. No solver, QR, reconstruction, conditioning,
reference interpolation, energy, or bookkeeping failure contaminates the
comparison.

## Verdict

Experiment 008 accepts outcome 1:

> Tangent/QR policy differences largely collapse on a common reference
> history.

Under the declared Euler–Lagrange reference history, Experiment 007's material
policy separation falls from `0.082–0.157 s^-1` to at most
$6.365\times10^{-7}\ \mathrm{s^{-1}}$ at `80 s`. Divergence of independently
integrated numerical reference shadows is therefore the **primary observed
source** of the Experiment 007 separation. This does not prove that tangent or
QR errors are identically zero, nor that the common-reference diagnostic
vector is an asymptotic Lyapunov spectrum.

The single next scientific question is:

> Do substantially longer independently integrated Euler–Lagrange QR runs
> yield cumulative spectra that statistically reconcile after their reference
> shadows decorrelate?

That future work must distinguish convergence of cumulative statistics from
pointwise agreement of chaotic reference paths. Experiment 008 does not begin
it.

## Evidence and reproduction

Generated evidence belongs under
`development/chaos_content/outputs/common_reference_qr_isolation/baseline/`.
It includes `summary.json`, all local reference-validation segments,
reference and cumulative time series, the final comparison matrix, baseline
QR cycles, static diagnostics, and a checksum manifest.

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
development/chaos_content/experiments/lyapunov_validation/008_common_reference_qr_isolation/common_reference_qr_isolation.py \
--output-dir development/chaos_content/outputs/common_reference_qr_isolation/baseline \
--self-check
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
development/chaos_content/experiments/foundations/006_variational_dynamics_validation \
development/chaos_content/experiments/lyapunov_validation/007_full_matrix_qr_tangent_dynamics \
development/chaos_content/experiments/lyapunov_validation/008_common_reference_qr_isolation
```
