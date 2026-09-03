# 003 Euler–Lagrange Nearby-State Distance Investigation

**Status: accepted for distance-convention findings; no exponent estimated.**

This chronological experiment is the first numerical investigation in the
Lyapunov strand. It interrogates definitions of nearby-state distance. It does
not estimate a finite-time growth rate, fit a slope, calculate a Lyapunov
exponent, renormalise a perturbation, integrate tangent equations, compare
formulations, or classify a trajectory.

## Question

> For one controlled pair of nearby Euler–Lagrange double-pendulum
> trajectories, how do several defensible state-distance conventions behave
> during the local-divergence regime, and which remain plausible foundations
> for later Lyapunov analysis?

The objective is controlled falsification and convention testing, not selection
of the norm with the straightest-looking log trace.

## Mathematical definitions

The experiment uses the production simple-model Euler–Lagrange solver state

$$
\mathbf{x}=(\theta_1,\theta_2,\omega_1,\omega_2).
$$

For the reference and nearby states, respectively,

$$
\mathbf{x}'_0=\mathbf{x}_0+\delta\mathbf{x}_0,
\qquad
\delta\mathbf{x}_0=(0,\varepsilon,0,0).
$$

The second-angle direction is a manually controlled reference direction. It is
not a privileged Lyapunov direction, and this experiment cannot generalise from
it to other perturbation directions.

Angles are not subtracted naively. The raw perturbation representation is

$$
\delta\mathbf{x}(t)=
(\Delta\theta_1,\Delta\theta_2,\Delta\omega_1,\Delta\omega_2),
$$

where

$$
\Delta\theta_i=
\operatorname{wrap}_{(-\pi,\pi]}(\theta'_i-\theta_i),
\qquad
\Delta\omega_i=\omega'_i-\omega_i.
$$

The implementation maps both $-\pi$ and $+\pi$ differences to $+\pi$, making
the branch convention deterministic. Experiment-local tests cover the branch
endpoints and physically identical states represented on opposite sides of the
angular boundary.

## Candidate distance conventions

### Candidate A — nondimensional generalized-coordinate full state

For characteristic time $T_c$,

$$
\delta\widetilde{\mathbf{x}}=
(\Delta\theta_1,\Delta\theta_2,
T_c\Delta\omega_1,T_c\Delta\omega_2),
$$

and

$$
d_{\mathrm{EL}}(t)=
\left\lVert\delta\widetilde{\mathbf{x}}(t)\right\rVert_2.
$$

This is dimensionless and includes all four EL state components. It depends on
the selected mechanical time scale.

### Candidate B — nondimensional Cartesian full state

Each EL state is mapped locally to the explicitly ordered vector

$$
\mathbf{z}=(x_1,y_1,x_2,y_2,
\dot{x}_1,\dot{y}_1,\dot{x}_2,\dot{y}_2),
$$

using

$$
\begin{aligned}
x_1&=l_1\sin\theta_1,&
y_1&=-l_1\cos\theta_1,\\
x_2&=x_1+l_2\sin\theta_2,&
y_2&=y_1-l_2\cos\theta_2,\\
\dot{x}_1&=l_1\omega_1\cos\theta_1,&
\dot{y}_1&=l_1\omega_1\sin\theta_1,\\
\dot{x}_2&=\dot{x}_1+l_2\omega_2\cos\theta_2,&
\dot{y}_2&=\dot{y}_1+l_2\omega_2\sin\theta_2.
\end{aligned}
$$

The distance is

$$
d_{\mathrm{Cartesian}}(t)=
\left\lVert
\left(
\frac{\Delta\mathbf{r}}{L_c},
\frac{T_c\Delta\mathbf{v}}{L_c}
\right)
\right\rVert_2,
$$

with both bobs included. It is dimensionless, uses physical positions and
velocities, and avoids an explicit angular branch cut. The eight Cartesian
components obey the pendulum's geometric constraints; they are an embedding of
the EL state, not eight independent phase-space coordinates and not a canonical
Hamiltonian state.

### Candidate C — second-bob display observable

The sensitivity prototype's dimensional observable is retained as

$$
d_{\mathrm{bob}}(t)=
\left\lVert\mathbf{r}'_2(t)-\mathbf{r}_2(t)\right\rVert_2.
$$

It remains a physical teaching/display quantity, not a candidate full-state
Lyapunov norm. It omits velocity differences and is bounded by

$$
0\le d_{\mathrm{bob}}(t)\le2(l_1+l_2)=4\ \mathrm{m}
$$

for this experiment.

### Rejected mixed-units baseline

The raw quantity

$$
\sqrt{\Delta\theta_1^2+\Delta\theta_2^2+
\Delta\omega_1^2+\Delta\omega_2^2}
$$

is dimensionally inadmissible. It was rejected before execution and not
implemented; adding it would only disguise the arbitrary relative weighting of
angles and angular velocities.

## Scaling conventions

The baseline uses

$$
L_c=1\ \mathrm{m},
\qquad
T_c=\sqrt{\frac{L_c}{g}}
=0.3192754284\ \mathrm{s}.
$$

The actual simple-model parameters are $l_1=l_2=1\ \mathrm{m}$, so one metre is
the common physical link length rather than an arbitrary numeric constant. It
also makes the initial values of Candidates A and B directly comparable for
the selected second-angle perturbation.

This is an experimental convention, not a universal rule. A controlled
Candidate A comparison uses $L_c=l_1+l_2=2\ \mathrm{m}$, the total reach, and
therefore $T_c=\sqrt{2/g}$. Unequal links would require an explicit decision
between a particular link, an average, a total reach, an energy-derived scale,
or another mechanically justified convention. No such general rule is claimed.

## Reference state and perturbation

The baseline reference state is

$$
\mathbf{x}_0=(179^\circ,179^\circ,0,0)
=(3.1241393611,3.1241393611,0,0)
$$

in solver units. It is the predeclared `near_inverted_release` case from
Experiment 002 and the guided separating case in the sensitivity prototype.
It was reused so this investigation changes the distance question rather than
searching for a new visually dramatic trajectory. Experiment 002 found this
case promising but numerically unresolved under its moderate production
policy; its strict-policy trajectories did pass their energy check.

The baseline perturbation is

$$
\varepsilon=10^{-5}\ \mathrm{rad}
=5.72957795\times10^{-4}\ ^\circ.
$$

This is slightly smaller than the prototype's $0.001^\circ$ display
perturbation, explicitly configured in radians, well above floating-point
resolution, and small relative to the angular scale. Its suitability is tested
rather than assumed through the adjacent $10^{-4}$ and $10^{-6}$ rad
comparisons.

## Numerical policy

Every member of the baseline pair uses the sensitivity prototype's trusted
strict Euler–Lagrange policy:

```text
model        = simple point-mass Euler–Lagrange
l1,l2,m1,m2 = 1 in SI units
g            = 9.81 m/s^2
method       = DOP853
rtol         = 1e-9
atol         = 1e-11
interval     = [0, 20] s
output       = 2001 samples, 0.01 s interval, 100 Hz
```

The two trajectories use identical parameters, integration policy, duration,
and output grid. The energy diagnostic is the Experiment 002 simple-model
mechanical energy, with drift

$$
\frac{|E(t)-E(0)|}{E_{\mathrm{scale}}},
\qquad
E_{\mathrm{scale}}=
g\left((m_1+m_2)l_1+m_2l_2\right)=29.43\ \mathrm{J}.
$$

Each trajectory must remain below the inherited strict-run limit $10^{-7}$.
The declared local-distance interval is the contiguous prefix before Candidate
A first exceeds $10^{-2}$; later returns below that threshold are not folded
back into the local interval.

## Baseline run

All baseline integrations and distance checks passed. Initial distances were

| Quantity | Measured initial value |
| --- | ---: |
| $d_{\mathrm{EL}}(0)$ | `9.99999999962e-6` |
| $d_{\mathrm{Cartesian}}(0)$ | `9.99999999958e-6` |
| $d_{\mathrm{bob}}(0)$ | `9.99999999958e-6 m` |

Candidate A first reached $10d(0)$ at `0.47 s` and $100d(0)$ at `1.29 s`.
Candidate B reached those levels at `0.56 s` and `1.02 s`. Candidate A stayed
below the predeclared $10^{-2}$ local-distance ceiling through the `1.70 s`
sample and exceeded it immediately afterward.

Over the full 20 seconds, Candidate A reached `7.52433`, Candidate B reached
`6.67686`, and the second-bob observable reached `3.94940 m`. These late maxima
are finite-separation diagnostics outside the declared local regime; they are
not evidence for a local growth law.

## Numerical checks

The machine-readable acceptance record verifies:

- solver success, complete requested output, expected `(sample_count, 4)`
  state shape, and finite state values for every trajectory;
- requested versus realised perturbation vector agreement within `2e-12`;
- deterministic wrapped differences in $(-\pi,\pi]$;
- finite, non-negative distances and analytically expected initial values;
- the $4\ \mathrm{m}$ second-bob bound;
- explicit log validity masks, with no zero/invalid baseline log samples and no
  clipping before logarithms;
- independent energy drift below $10^{-7}$ for every trajectory; and
- explicit rejection summaries if any integration or derived check fails.

The baseline maximum normalized energy drifts were `3.40294e-8` for the
reference and `1.38896e-8` for the nearby trajectory. Across every controlled
run, the largest drift remained `3.40294e-8`. The stricter-policy drifts were
`2.96345e-10` and `3.47245e-10`.

The wrapping unit checks pass. Within the contiguous local interval, maximum
sample-to-sample changes in $(\Delta\theta_1,\Delta\theta_2)$ were only
`(1.14003e-4, 1.92497e-4) rad`. Over the full nonlinear trace, the components
show branch changes of `6.21752` and `6.24338 rad`, close to $2\pi$. Those late
jumps are a real limitation of component-wise wrapped coordinates, not hidden
solver failure. They occur after the perturbation is no longer local.

## Static diagnostics

The reproducible output bundle contains:

1. `01_component_perturbations.png` — full and local views of
   $\Delta\theta_1$, $\Delta\theta_2$, $T_c\Delta\omega_1$, and
   $T_c\Delta\omega_2$;
2. `02_candidate_distance_comparison.png` — the dimensionless full-state
   candidates together and the dimensional bob observable on a separate axis;
3. `03_normalized_separation.png` — $d(t)/d(0)$ for Candidates A and B;
4. `04_log_normalized_separation.png` — log-normalized candidates with no fit,
   regression line, or reported rate;
5. `05_second_bob_saturation.png` — the display observable and its $4\ \mathrm{m}$
   geometric maximum;
6. `06_energy_validity.png` — independent drift for both trajectories and the
   rejection limit; and
7. `07_controlled_comparisons.png` — perturbation, tolerance, sampling, and
   Candidate A scaling comparisons.

The component diagnostic shows that the perturbation rapidly spreads from the
manually changed second angle into both angle and both velocity components.
At the end of the contiguous local interval, the wrapped-angle component norm
is `0.00332975` while the scaled-velocity component norm is `0.00779032`.
Velocities therefore cannot be omitted merely because the initial perturbation
has zero velocity components.

## Controlled comparisons

These are one-at-a-time checks around the baseline, not a parameter sweep.

### Perturbation magnitude

The same pair and strict policy were run with
$\varepsilon\in\{10^{-4},10^{-5},10^{-6}\}\ \mathrm{rad}$. Through the common
contiguous local interval ending at `1.29 s`, the maximum spread among Candidate
A log-normalized traces was `0.00623007`, below the provisional `0.1` agreement
limit. This is a ratio difference of about `0.6%`, not exact identity.

**Observation:** the early normalized response is stable over two adjacent
decades, and the smallest perturbation is not visibly overtaken by solver noise.

**Interpretation:** this supports a finite local regime for the selected state
and direction. It does not establish direction independence or an asymptotic
limit.

### Solver tolerance

The baseline was repeated with DOP853, `rtol=1e-11`, and `atol=1e-13`. Over the
baseline contiguous local interval, the maximum Candidate A log-normalized
difference was `1.92147e-7`.

**Observation:** the early trace is materially unchanged by the stricter
policy, while energy drift falls by roughly two orders of magnitude.

**Interpretation:** the observed local divergence is not dominated by the
baseline solver tolerance under this comparison.

### Output sampling

Output was increased from 100 Hz (`2001` samples) to 200 Hz (`4001` samples)
without changing the integration tolerances. At the shared output times, the
maximum absolute difference was exactly `0.0` for Candidate A, Candidate B, and
the second-bob distance.

**Interpretation:** features in the recorded traces are not output-sampling
artefacts at these two resolutions. This does not make the adaptive internal
solver steps fixed or identical to the output grid.

### Characteristic scaling

Candidate A was recomputed with $L_c=2\ \mathrm{m}$ and
$T_c=\sqrt{2/g}$. Over the baseline local interval, its log-normalized trace
differed from the $L_c=1\ \mathrm{m}$ convention by as much as `0.306383`, a
ratio factor of about `1.36`.

**Observation:** the qualitative growth shape remains recognizable, but finite
values change appreciably when velocity components receive a different
mechanical scale.

**Interpretation:** scaling cannot be dismissed as asymptotically irrelevant in
this finite-time experiment. The one-metre choice remains provisional.

## Findings

### Observations

- Candidates A and B both show prompt growth from the same nearby pair. Their
  local log-normalized traces have correlation `0.987402`.
- Their timings and amplitudes are not interchangeable: local 10x/100x crossing
  times differ, and the maximum local log-ratio difference is `0.756992`, a
  factor of about `2.13` in normalized distance.
- The perturbation spreads into all EL components; velocity differences become
  dynamically important.
- The two full-state candidates remain finite after the local interval, but
  their later values describe finite nonlinear separation rather than a
  tangent/local perturbation.
- The second-bob observable reaches 90% of its geometric maximum at `19.24 s`
  and a maximum of `3.94940 m`. Its bounded geometry visibly suppresses its
  usefulness as a local-divergence measure.
- Wrapped angular component traces have unavoidable branch-cut jumps once the
  states become macroscopically separated. No such discontinuity appears in the
  declared local interval; the Cartesian embedding supplies a useful check on
  this coordinate effect.
- The log traces rise strongly in the early interval, but already contain norm-
  dependent timing and curvature. No slope was fitted and no stable
  exponential interval is claimed by this experiment.

### Interpretation

The evidence supports a credible **local-divergence regime** for this one
manually selected trajectory, direction, and scale: both full-state candidates
grow by two orders of magnitude while the perturbation remains below the local
distance ceiling, the three perturbation magnitudes agree closely after
normalization, and the result survives stricter tolerance and denser output.

This is enough to retain both full-state candidates for a later finite-time
growth-rate investigation. It is not enough to say that a reproducible
approximately exponential interval has been identified. Candidate-dependent
oscillations, finite values, and interval choices must be addressed explicitly
in that next experiment.

## Accepted conventions

- The primary state remains the Euler–Lagrange
  $(\theta_1,\theta_2,\omega_1,\omega_2)$ state.
- Angular differences use the deterministic $(-\pi,\pi]$ wrapping convention;
  velocity differences remain ordinary differences.
- Candidate A is retained as a plausible, dimensionally coherent EL full-state
  norm under an explicit mechanical time scale.
- Candidate B is retained as a plausible, physically interpretable full-state
  comparison embedding under the same length/time scales.
- Normalized and log-normalized separation may be emitted as diagnostics only
  where the initial and current distance are positive; invalid logs are
  reported, not silently clipped.
- Full-state and display distances remain separate concepts.

These acceptances are local to the experiment. They do not select one unique
norm or promote code into production.

## Rejected conventions

- The mixed-units raw EL Euclidean norm is rejected and unimplemented.
- Second-bob Cartesian distance is rejected as a full-state Lyapunov norm. It
  remains accepted only as a bounded physical display observable.
- A norm is not preferred because its log plot looks more linear.

## Unresolved questions

- Whether $L_c=1\ \mathrm{m}$ is the best scaling, especially for unequal link
  lengths or other physical parameter sets.
- Whether Candidate A's angular branch convention causes practical ambiguity
  near antipodal differences before a future renormalisation policy intervenes.
- How the Cartesian embedding's redundant constrained components should be
  weighted relative to generalized coordinates.
- Which perturbation directions give comparable local behaviour.
- How a local interval should be selected without using an attractive-looking
  trace after the fact.
- Whether a finite-time rate is robust to norm, transient removal, interval,
  tolerance, and perturbation size.
- Whether later Hamiltonian/canonical-coordinate calculations agree after
  appropriate scaling. That is a future formulation-robustness check; no
  Hamiltonian trajectory or metric is implemented here.

## Self-selection limitation

Every central choice remains manual: reference trajectory, second-angle
direction, perturbation magnitude, $L_c$, 20-second duration, local ceiling,
and the stricter tolerance comparison. The perturbation decades and alternate
length are controlled checks around those choices, not representative sampling
of phase space.

The experiment therefore retains the sensitivity strand's self-referential
selection bias. Its successful result cannot be used to claim general chaotic
behaviour, typical divergence, or that the selected state is representative.

## Reproduce

Run the experiment-local mathematical tests:

```bash
uv run pytest development/chaos_content/experiments/foundations/003_lyapunov_distance_contract/test_lyapunov_distance_investigation.py
```

Run the deterministic numerical self-check:

```bash
uv run python development/chaos_content/experiments/foundations/003_lyapunov_distance_contract/lyapunov_distance_investigation.py --self-check
```

Write the ignored machine-readable and static evidence bundle:

```bash
uv run python development/chaos_content/experiments/foundations/003_lyapunov_distance_contract/lyapunov_distance_investigation.py --output-dir development/chaos_content/experiments/outputs/003/baseline --plots
```

The bundle contains `manifest.json`, `summary.json`,
`distance_timeseries.csv`, and the seven PNG diagnostics listed above. Blank log
CSV cells mean that the positive-distance precondition failed; no clipping is
used in the machine-readable result.

## Next justified experiment

The evidence earns the next question, but does not answer it:

> Is there a reproducible interval in which sufficiently small perturbations
> exhibit approximately exponential growth, and how should a finite-time growth
> rate be defined without contaminating it by transient behaviour, norm choice,
> or saturation?

That next experiment may investigate finite-time growth-rate estimation. It
must not treat the current `0–1.70 s` distance-defined interval as prevalidated,
and it must not promote a positive fitted slope to a Lyapunov exponent. No part
of that experiment is implemented here.
