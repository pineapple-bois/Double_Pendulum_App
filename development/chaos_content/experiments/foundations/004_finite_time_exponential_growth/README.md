# 004 Finite-Time Approximately Exponential Growth Investigation

**Status: completed; no defensible common approximately exponential interval
identified under the predeclared rule.**

This experiment asks whether the controlled nearby-state divergence accepted by
Experiment 003 contains a reproducible finite interval that can defensibly be
described as approximately exponential. It does not calculate a Lyapunov
exponent, renormalise a perturbation, integrate tangent dynamics, establish an
asymptotic limit, or classify a trajectory.

## Question

> Does the controlled Euler–Lagrange nearby-state divergence contain a
> reproducible finite interval over which sufficiently small perturbations grow
> approximately exponentially?

This is distinct from the stronger question “What is the Lyapunov exponent?”
Experiment 004 does not answer that question.

## Experiment 003 boundary

Experiment 003 established that dimensionally coherent full-state distances can
be constructed and evaluated robustly enough to support this investigation. It
did not establish a linear interval in log separation, exponential divergence,
a finite-time or maximal Lyapunov exponent, renormalisation, asymptotic
convergence, coordinate-independent rates, representative state-space
behaviour, or a regular/chaotic classification.

The unchanged reference state is

$$
\mathbf{x}_0=(179^\circ,179^\circ,0,0),
$$

and the controlled perturbations remain

$$
\delta\mathbf{x}_0=(0,\varepsilon,0,0),
\qquad
\varepsilon\in\{10^{-4},10^{-5},10^{-6}\}\ \mathrm{rad}.
$$

The $10^{-5}\ \mathrm{rad}$ case is the baseline. The second-angle direction is
manual and is not a privileged stretching or Lyapunov direction.

## Working distances

The Euler–Lagrange state remains

$$
\mathbf{x}=(\theta_1,\theta_2,\omega_1,\omega_2),
$$

with

$$
\Delta\theta_i=
\operatorname{wrap}_{(-\pi,\pi]}(\theta'_i-\theta_i),
\qquad
\Delta\omega_i=\omega'_i-\omega_i.
$$

### Primary working convention — Candidate A

$$
d_{\mathrm{EL}}(t)=
\left\lVert
(\Delta\theta_1,\Delta\theta_2,
T_c\Delta\omega_1,T_c\Delta\omega_2)
\right\rVert_2.
$$

Candidate A is primary because it operates directly on the current EL state,
contains all four state components, handles angular topology explicitly, is
dimensionally coherent under a declared scale, and passed Experiment 003's
numerical checks. This is a working convention, not a unique or
coordinate-invariant norm.

### Robustness convention — Candidate B

$$
d_{\mathrm{Cartesian}}(t)=
\left\lVert
\left(
\frac{\Delta\mathbf r}{L_c},
\frac{T_c\Delta\mathbf v}{L_c}
\right)
\right\rVert_2,
$$

using both bob positions and velocities. Candidate B remains a required
robustness comparison. Its constrained Cartesian components are not treated as
independent canonical coordinates, and its finite-time rate need not equal
Candidate A's.

Second-bob distance is excluded from growth-rate estimation because it omits
velocity components and saturates geometrically. It remains a teaching/display
observable only.

## Lifted angular-history diagnostic

The wrapped angular differences above remain the angular components of
Candidate A. Separately, each sampled physical angle is lifted to a continuous
history $\Theta_i(t)$ by unwrapping consecutive samples. Every required run
verifies that each raw EL angle advances by less than $\pi$ between output
samples, so the sampled unwrapping convention is unambiguous. Define

$$
R_i(t)=\frac{\Theta_i(t)-\Theta_i(0)}{2\pi},
$$

and, between the nearby and reference histories,

$$
\Delta\Theta_i(t)=\Theta'_i(t)-\Theta_i(t),
\qquad
\Delta R_i(t)=R'_i(t)-R_i(t).
$$

$R_i$ is a continuous signed accumulated-revolution quantity. It preserves
reversals rather than rounding an endpoint angle. The precisely recorded
one-revolution marker is the first output sample at which
$|\Delta R_i|\ge1$; no integer endpoint count is substituted for the signed
history.

These quantities are global history observables, not state-space distances.
Two histories may differ by a full revolution while having nearly identical
instantaneous wrapped angles. Conversely, wrapped angular separation measures
local configuration without recording the path taken. Neither $\Theta_i$ nor
$R_i$ enters Candidate A, Candidate B, the locality rule, interval selection,
or any acceptance threshold.

## Scaling convention and caveat

For continuity with Experiment 003,

$$
L_c=1\ \mathrm{m},
\qquad
T_c=\sqrt{\frac{L_c}{g}}=0.3192754284\ \mathrm{s}.
$$

The one-metre length is the common link length for $l_1=l_2=1\ \mathrm{m}$.
Candidate A will also be recomputed with the fixed alternative
$L_c=2\ \mathrm{m}$ and $T_c=\sqrt{2/g}$. The alternative is the total reach,
not a scale selected to improve linearity. Experiment 003 already showed
material finite-time scaling dependence, so no reported finite-window rate is
a coordinate-free invariant.

## Quantities

For every perturbation magnitude and full-state candidate,

$$
y(t)=\log\frac{d(t)}{d(0)}.
$$

Logs are defined only for positive finite distances. Zero or invalid distances
are reported and reject the affected diagnostic; they are not clipped.

The adopted finite-window logarithmic growth rate is

$$
\Lambda(t_a,t_b)=
\frac{y(t_b)-y(t_a)}{t_b-t_a}.
$$

$\Lambda(t_a,t_b)$ is a descriptive endpoint rate with units
$\mathrm{s}^{-1}$. It is not denoted $\lambda$, is not a maximal Lyapunov
exponent, and is not an asymptotic quantity.

For log-linearity diagnostics only, ordinary least squares will fit

$$
y(t)=\alpha+\widehat\beta t+r(t)
$$

on each declared interval. The fit records $\widehat\beta$, $R^2$, root-mean-
square residual, and maximum absolute residual. The fitted slope is not allowed
to replace $\Lambda$ or to choose an interval.

## Numerical policy

The baseline policy is unchanged from Experiment 003:

```text
model        = simple point-mass Euler–Lagrange
state        = (theta1, theta2, omega1, omega2)
l1,l2,m1,m2 = 1 in SI units
g            = 9.81 m/s^2
method       = DOP853
rtol         = 1e-9
atol         = 1e-11
interval     = [0, 20] s
output       = 2001 samples, 0.01 s interval, 100 Hz
energy limit = 1e-7 normalized drift per trajectory
```

The stricter comparison remains DOP853 with `rtol=1e-11`, `atol=1e-13`.
The sampling comparison remains 4001 samples at 200 Hz with unchanged solver
tolerances. Both members of every pair use identical numerical policy.

## Locality rule

Locality is determined independently of regression quality. A time sample is
in the common local regime only while every Candidate-A perturbation satisfies
both of these conditions on one contiguous prefix:

1. $d_{\mathrm{EL},\varepsilon}(t)\le10^{-2}$ for all three perturbations;
2. the instantaneous perturbation-collapse spread

   $$
   \max_\varepsilon y_\varepsilon(t)
   -\min_\varepsilon y_\varepsilon(t)\le0.1.
   $$

The $10^{-2}$ ceiling and `0.1` log-spread limit are inherited provisional
Experiment 003 policies. The ceiling is retained as a conservative macroscopic-
separation guard; collapse supplies the stronger evidence that
$d_\varepsilon(t)\propto\varepsilon$. Neither value is a universal physical
boundary. The common local regime ends at the first violation, and later
returns are excluded.

## Predeclared interval rule

No interval may be selected by maximizing $R^2$, minimizing residuals, or
inspecting a plot.

The primary candidate interval is mechanically anchored before execution:

$$
t_a=T_c,
\qquad
t_b=3.5T_c.
$$

Endpoints are rounded to the nearest baseline output sample, giving the
predeclared `0.32–1.12 s` interval. This allows one characteristic time for the
manual coordinate perturbation to begin aligning with the evolving local
stretching directions, while still testing a duration greater than $2T_c$.
That transient hypothesis is testable and is not permission to move $t_a$ after
inspection.

The inference-rule audit records every valid combination of

$$
t_a\in\{0,0.5T_c,T_c,1.5T_c\},
\qquad
t_b\in\{3T_c,3.5T_c,4T_c\},
$$

rounded to the output grid and restricted to durations of at least $2T_c$.
These windows expose transient and endpoint dependence. They cannot substitute
for the primary interval if it fails.

Endpoint sensitivity uses the eight neighbouring endpoint combinations formed
from

$$
t_a\pm0.10\ \mathrm{s},
\qquad
t_b\pm0.10\ \mathrm{s},
$$

including one- and two-endpoint movements and excluding the unchanged pair.
Every neighbour remains subject to locality and duration checks. Invalid
neighbours remain visibly rejected.

## Local slope diagnostic

A centered ordinary-least-squares window of fixed width `0.20 s` is moved over
the common local regime. No smoothing, weighting, polynomial order beyond one,
or bandwidth optimisation is used. The windowed slope is plotted and recorded
to expose variation; the primary acceptance decision uses the independently
declared endpoint-sensitivity test below rather than selecting a flat-looking
part of this curve.

## Provisional thresholds fixed before execution

These thresholds are deliberately simple and are not derived by inspecting
which values make this baseline pass. They are experiment-local decision aids,
not universal definitions of exponential growth.

The predeclared primary interval is accepted only if all conditions hold:

1. **Duration/growth:** duration is at least $2T_c$ and Candidate A's baseline
   log growth across the interval is at least `2.0` (a factor $e^2$), keeping
   the inference away from numerical-noise-scale changes.
2. **Locality/collapse:** the entire interval lies in the common local regime;
   Candidate A's maximum log-trace spread is at most `0.1`.
3. **Candidate A log-linearity:** for all three perturbations, $R^2\ge0.98$
   and maximum absolute residual is at most `0.25`.
4. **Perturbation rate agreement:** the relative spread of the three Candidate
   A endpoint rates, `(max-min)/abs(median)`, is at most `0.05`.
5. **Endpoint stability:** every numerically valid, local endpoint neighbour's
   baseline Candidate A rate differs from the primary rate by at most `10%`.
6. **Candidate B robustness:** all three Candidate B rates are positive,
   Candidate B has $R^2\ge0.95$, its collapse spread is at most `0.15`, and its
   median rate differs from Candidate A's median by at most `30%`.
7. **Tolerance robustness:** the stricter-policy baseline Candidate A rate
   differs by at most `1%`.
8. **Sampling robustness:** the 200 Hz baseline Candidate A rate differs by at
   most `0.5%` at its own sampled endpoints.
9. **Scaling robustness:** the fixed $L_c=2\ \mathrm{m}$ Candidate A trace has a
   positive rate and $R^2\ge0.95$ over the same interval. Its numerical rate is
   reported but is not required to match the $L_c=1\ \mathrm{m}$ value.
10. **Numerical validity:** all required trajectories pass solver, completeness,
    finiteness, initial-perturbation, distance, and energy checks.

The `0.98`/`0.95` linearity thresholds demand strong but not perfect affine
agreement. Residual thresholds prevent a high $R^2$ caused only by a large
vertical range. The `5%`, `10%`, `1%`, and `0.5%` rate limits distinguish
perturbation/endpoint/numerical questions. Candidate B's looser `30%` rate limit
acknowledges the finite-time norm dependence already measured in Experiment
003. All values remain provisional and raw diagnostics are retained even when a
threshold fails.

## Candidate interval audit

For every predeclared audit interval, the machine-readable table will record:

- requested and realised endpoints and duration;
- locality and numerical status;
- endpoint $\Lambda$ and fitted $\widehat\beta$ for each perturbation;
- $R^2$, RMSE, and maximum absolute residual;
- perturbation-rate and log-collapse spreads;
- Candidate A/B and $L_c=1/2\ \mathrm{m}$ comparisons; and
- rejection reasons.

No “best interval” is returned. The primary interval owns the acceptance
decision; the table audits how fragile that decision is.

## Numerical rejection

A run is rejected if integration fails, requested output is incomplete or
misaligned, state/distance/energy values are non-finite, the requested initial
perturbation is not realised, a distance is non-positive where a logarithm is
required, or normalized energy drift exceeds $10^{-7}$. A failed run cannot be
rescued by a visually attractive plot or fit.

## Required outputs

The ignored output bundle will contain structured JSON/CSV evidence and at
least these deterministic Matplotlib diagnostics:

1. perturbation-collapse log traces with the common local and primary interval;
2. the fixed-width local slope diagnostic versus time;
3. the full candidate-interval audit without a highlighted “best” window;
4. Candidate A versus Candidate B growth behaviour;
5. fixed $L_c=1$ versus $L_c=2\ \mathrm{m}$ scaling sensitivity; and
6. solver/energy numerical validity; and
7. reference/nearby signed revolution histories for both pendulums, with
   $\Delta R_1$ and $\Delta R_2$ in a separate panel.

The summary JSON must include the model, parameters, state, perturbation
direction and magnitudes, metrics, scales, solver/output policy, every candidate
interval, rates, residuals, endpoint sensitivity, metric/scaling comparisons,
energy drift, acceptance/rejection reasons, and an explicit `claim_boundary`.

## Acceptance claim

If every predeclared condition passes, the strongest permitted claim is:

> For this controlled reference trajectory and perturbation direction,
> sufficiently small nearby states exhibit a reproducible finite interval of
> approximately exponential full-state separation under the declared EL
> distance convention, with qualitatively compatible behaviour under the
> Cartesian full-state representation.

The experiment may report $\Lambda(t_a,t_b)$ for the declared interval. It must
not call that number a Lyapunov exponent or generalise beyond this state,
direction, metric, scale, and interval.

A fully valid alternative outcome is that no defensible common exponential-
growth interval was identified.

## Completed evidence and findings

### Observation — locality and perturbation collapse

The three Candidate-A traces for $10^{-4}$, $10^{-5}$, and $10^{-6}$ rad
remain in the declared common local prefix through `1.29 s`; the first failure
at `1.30 s` is the provisional $d_{\mathrm{EL}}\le10^{-2}$ ceiling, not
perturbation-collapse disagreement. The maximum three-trace log spread within
that prefix is `0.006230`, well below the provisional `0.1` limit. The primary
`0.32–1.12 s` interval is therefore local under the predeclared rule.

Interpretation: these perturbations give strong evidence for a shared finite-
perturbation local regime. This does not by itself make the growth exponential.

### Observation — primary interval and interval audit

Across the primary interval, Candidate A's endpoint rates for the three
perturbations are `3.71577`, `3.72245`, and `3.72312 s^-1`, with relative
spread `0.001973`. The baseline log growth is `2.97796`. Nevertheless,
Candidate A has $R^2=0.94040$ for the baseline, below `0.98`, and maximum
absolute residual `0.53684`, above `0.25`. Its fixed `0.20 s` local fitted
slope changes substantially across the interval rather than forming a stable
plateau.

The endpoint-neighbour audit reaches a maximum admissible relative rate change
of `0.16803`, exceeding the predeclared `0.10` limit. All eleven declared audit
intervals are retained and all fail at least one core check. Some earlier
windows have visually strong $R^2$ values—for example `0.00–0.96 s` has
minimum Candidate-A $R^2=0.99399$—but still fail the independently fixed
residual limit and cannot replace the primary interval.

Interpretation: the distance grows strongly and the perturbations collapse,
but the rate changes too much in time to support the requested approximately
exponential description under this inference rule. A visually attractive
sub-interval would be post-hoc selection.

### Observation — metric and scaling sensitivity

Candidate B supports the same qualitative rising local-growth episode and is
more affine over the primary interval ($R^2=0.99144$ for the baseline). Its
median endpoint rate is `4.73833 s^-1`, versus Candidate A's `3.72245 s^-1`, a
relative difference of `0.27291`. Candidate B's perturbation-collapse spread
is `0.004681`.

With the fixed alternative $L_c=2\ \mathrm{m}$ scaling, Candidate A's baseline
endpoint rate is `3.48039 s^-1`, but $R^2=0.91320`; this fails the predeclared
scaling-robustness linearity check. The scale was not tuned.

Interpretation: Candidates A and B agree that a reproducible local growth
episode exists, but they do not support a common stable exponential-rate claim.
The meaningful norm/scaling dependence anticipated by Experiment 003 remains
visible.

### Observation — numerical validity

All required integrations, finiteness, initial-perturbation, positive-distance,
log-validity, energy, and lifted-history checks pass. The baseline reference
maximum normalized energy drift is `3.40294e-8`; nearby baseline drifts are
between `1.38896e-8` and `2.55471e-8`, below the `1e-7` limit. Tightening the
solver changes the baseline Candidate-A endpoint rate by only
`1.95e-9` relative; doubling output density changes it by `0` at the shared
endpoints.

Interpretation: the rejection is inferential, not a solver, energy, or output-
sampling failure.

### Observation — winding histories

For the $10^{-5}$ rad baseline at `20 s`, the reference signed revolution
totals are `(1.40980, 11.35114)` and the nearby totals are
`(3.69653, 13.80293)`, giving final differences
`(2.28672, 2.45179)` revolutions. The first sampled
$|\Delta R_i|\ge1$ markers occur at `17.43 s` and `17.48 s` for pendulums one
and two. Both are far after the primary candidate interval and the common local
prefix. For $10^{-4}$ rad they occur at `11.35 s` and `14.45 s`; for
$10^{-6}$ rad neither occurs by `20 s`.

Interpretation: differing winding histories are a late, macroscopic history
effect in these runs. They do not motivate a new locality threshold and do not
change the interval decision. Wrapped angular differences describe local
separation on the physical angular state space; lifted angles and revolution
counts are retained separately as global history observables and potential
later teaching metrics.

### Accepted and rejected claims

Accepted observation: sufficiently small perturbations show reproducible,
numerically robust local full-state growth for this manually selected
trajectory and direction, and Candidates A and B tell a qualitatively
compatible growth story.

Rejected claim: no defensible common approximately exponential interval was
identified under the predeclared policy. The descriptive primary-window value
$\Lambda(0.32,1.12)=3.72245\ \mathrm{s}^{-1}$ for baseline Candidate A is
retained as an audited finite-window number only. It is not accepted as an
exponential rate and is not a Lyapunov exponent.

Unresolved choices include the locality ceilings, transient policy, primary
interval anchoring, residual and endpoint thresholds, moving-window width,
norm, characteristic scaling, trajectory, perturbation direction, and finite
duration. The evidence does not earn Experiment 005 renormalisation. A new
contract would first need to justify how a stable growth interval can be tested
without adapting the rule to this rejected trace.

## Reproduction

From the repository root:

```bash
UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run pytest development/chaos_content/experiments/foundations/004_finite_time_exponential_growth/test_finite_time_exponential_growth.py -q
UV_CACHE_DIR=/tmp/double-pendulum-uv-cache uv run python development/chaos_content/experiments/foundations/004_finite_time_exponential_growth/finite_time_exponential_growth.py --self-check --output-dir development/chaos_content/experiments/outputs/004/baseline --plots
```

The output directory is ignored. `summary.json` and `manifest.json` preserve
the rejection and claim boundary; `interval_audit.json`/`.csv`,
`growth_timeseries.csv`, and `local_slopes.csv` preserve the reconstructible
diagnostics behind it.

## Self-selection limitation

The reference trajectory, perturbation direction and magnitudes, characteristic
scale, duration, solver comparisons, locality rules, primary interval, audit
grid, window width, and thresholds are all manually designed. Mechanically
anchoring and predeclaring them prevents one form of post-hoc selection; it does
not make the case representative of phase space or the policy universal.

## Teaching significance — deferred

If accepted, a future teaching surface may show

$$
d(t)\approx d_0e^{\Lambda t},
\qquad
\log[d(t)/d_0]\approx\Lambda t
$$

over one explicitly finite interval, then explain why the straight region ends
when perturbations leave the local regime and physical observables saturate.
No UI is implemented here.

## Next question — document only

Only if this experiment accepts a finite approximately exponential interval
would the next question be how to keep perturbations local long enough to
accumulate a defensible instability rate. A later Experiment 005 might examine
renormalisation magnitude, interval, direction evolution, accumulated
stretching, and duration convergence. Experiment 004 does not implement any of
that work.
