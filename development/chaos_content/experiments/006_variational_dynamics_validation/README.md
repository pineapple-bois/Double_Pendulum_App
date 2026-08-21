# 006 Variational Dynamics Validation

**Status: accepted for the limited short-time variational-dynamics validation
claim; no maximal Lyapunov exponent estimated.**

This experiment asks whether direct Euler–Lagrange tangent evolution reproduces
the short-time local perturbation dynamics established by Experiments 003–005
and converges materially better under the repaired Experiment 005 numerical
policies. It validates a formulation. It does not estimate or claim a maximal
Lyapunov exponent.

## Motivation and dependency boundary

Experiment 003 established dimensionally coherent nearby-state distances.
Experiment 004 found robust local growth but no defensible common
approximately exponential interval. Experiment 005 then accumulated repeated
finite-shadow stretching. Its repaired iteration removed winding-dependent
solver coordinates, unrestricted step size, and ill-conditioned reset
reconstruction, but retained a `10.77%` baseline/strict discrepancy at `80 s`
and failed duration convergence.

The historical Experiment 005 result and the independent
[`LYAPUNOV_REVIEW.md`](../LYAPUNOV_REVIEW.md) audit remain unchanged. This new
experiment isolates the next question: is finite-state subtraction itself the
limiting representation?

## Mathematical contract

The production simple-model Euler–Lagrange state and flow remain

$$
\mathbf{x}=(\theta_1,\theta_2,\omega_1,\omega_2),
\qquad
\frac{\mathrm{d}\mathbf{x}}{\mathrm{d}t}=\mathbf{f}(\mathbf{x}).
$$

The tangent vector evolves with the Jacobian of that same flow:

$$
\frac{\mathrm{d}\delta\mathbf{x}}{\mathrm{d}t}
=J(\mathbf{x})\delta\mathbf{x},
\qquad
J(\mathbf{x})=\frac{\partial\mathbf{f}}{\partial\mathbf{x}}.
$$

The reference case is unchanged:

$$
\mathbf{x}_0=(179^\circ,179^\circ,0,0),
\qquad
l_1=l_2=m_1=m_2=1,
\qquad
g=9.81
$$

in SI units. For continuity with the previous experiments,

$$
L_c=1\ \mathrm{m},
\qquad
T_c=\sqrt{\frac{L_c}{g}},
$$

and Candidate A remains the primary norm:

$$
\lVert\delta\mathbf{x}\rVert_{\mathrm{EL}}
=\left\lVert
(\delta\theta_1,\delta\theta_2,
T_c\delta\omega_1,T_c\delta\omega_2)
\right\rVert_2.
$$

The initial tangent is the controlled unit Candidate-A direction

$$
\delta\mathbf{x}_0=(0,1,0,0).
$$

Its unit magnitude is only a convenient linear scale. The direction is the
same pure-$\theta_2$ direction used previously; it is not privileged and is
not imposed again after $t=0$.

Tangent angular components are coordinate-basis components of an infinitesimal
vector. They are not finite angular displacements and are never wrapped. Only
finite reference/shadow subtraction uses the established wrapped difference.

## Jacobian construction and independent validation contract

The implementation differentiates, with SymPy, the exact parameter-substituted
first-order expressions returned by the production
`DoublePendulumLagrangian._compute_and_cache_equations("simple")` path. This
avoids maintaining a second hand-copied flow while keeping all new tangent
machinery inside the sandbox.

Symbolic provenance is not accepted as proof of correctness. At the baseline
initial state, three sampled baseline-trajectory states, and two nontrivial
velocity/branch states, five fixed directions are compared with the
independent forward directional difference

$$
\frac{\mathbf{f}(\mathbf{x}+h\mathbf{v})-\mathbf{f}(\mathbf{x})}{h}
$$

for $h\in\{10^{-2},10^{-3},\ldots,10^{-8}\}$. The predeclared assessment step
is $h=10^{-6}$; the range is retained to expose truncation and round-off rather
than to select the best result after inspection. Jacobian validation passes if
the maximum relative directional error at that fixed step is at most
$5\times10^{-5}$.

The flow, Jacobian, Cartesian observables, and energy are also checked under
independent positive and negative integer $2\pi$ shifts. The maximum absolute
flow/Jacobian discrepancy must be at most $10^{-9}$.

## Local finite-shadow comparison

The primary interval is fixed at `0–1.29 s`, the three-perturbation common local
prefix established by Experiments 003 and 004. Baseline finite shadows use

$$
\varepsilon\in\{10^{-4},10^{-5},10^{-6}\}
$$

in the same initial pure-$\theta_2$ direction. They are not reset. For each
magnitude, compare the normalized scaled finite difference

$$
\frac{1}{\varepsilon}
(\Delta\theta_1,\Delta\theta_2,
T_c\Delta\omega_1,T_c\Delta\omega_2)
$$

with the scaled tangent vector in norm and signed direction. Direction
alignment is the ordinary cosine $\mathbf{u}_{\rm shadow}\mathbin{\cdot}
\mathbf{u}_{\rm tangent}$; opposite directions are not treated as equivalent.

Local consistency passes only if:

- RMS log-norm error and RMS direction mismatch decrease successively from
  $10^{-4}$ to $10^{-5}$ to $10^{-6}$;
- the $10^{-6}$ maximum absolute log-norm error is at most `0.01`; and
- its minimum signed direction cosine is at least `0.999`.

These thresholds test the linearised limit without requiring exact equality
for a finite perturbation.

## Numerical policy and predeclared acceptance

The augmented eight-component reference/tangent system is solved with DOP853.
The baseline and strict policies remain those used by repaired Experiment 005:

| Policy | `rtol` | `atol` |
| --- | ---: | ---: |
| baseline | $10^{-9}$ | $10^{-11}$ |
| strict | $10^{-11}$ | $10^{-13}$ |

The baseline step cap is retained mechanically:

$$
h_{\max}=\min(T_c/32,0.25/25),
$$

with exactly one refinement $h_{\max}/2$. Every run uses the same `0.01 s`
requested output grid. The physical angular coordinates are deterministically
rebased to $(-\pi,\pi]$ at `0.25 s` chart boundaries. This is a physically
equivalent coordinate change whose tangent map is the identity; the tangent
components are left unchanged. Winding history is neither a solver coordinate
nor part of the tangent vector.

For policy comparison define

$$
d_{\rm tan}(t)=\lVert\delta\mathbf{x}(t)\rVert_{\rm EL},
\qquad
G(t)=\log\frac{d_{\rm tan}(t)}{d_{\rm tan}(0)},
$$

and, only as a descriptive finite-time diagnostic for $t>0$,

$$
\Lambda_{\rm tan}(t)=\frac{G(t)}{t}.
$$

Baseline/strict and baseline/half-step comparisons each pass only if:

- final $\Lambda_{\rm tan}$ relative difference is at most `1%`;
- maximum absolute $G(t)$ difference is at most $10^{-3}$;
- maximum normalized tangent-direction component difference is at most
  $10^{-3}$; and
- maximum Candidate-A reference-trajectory distance is at most $10^{-6}$.

The baseline/strict final-rate discrepancy must also be less than one fifth of
repaired Experiment 005's `10.767%` discrepancy. This is the predeclared
meaning of **materially improved tolerance convergence**.

Reference normalized energy drift must remain below $10^{-7}$, all requested
times and finite states must be returned, and all Jacobian/local-limit/policy
checks must pass for the experiment to be accepted.

## Required evidence

The output bundle will record:

- symbolic Jacobian provenance and directional finite-difference errors;
- periodicity checks for the flow and Jacobian;
- complete baseline, strict, and half-step tangent time series;
- all three finite-shadow norm and signed-direction comparisons;
- policy reference, tangent-norm, tangent-direction, log-growth, solver, and
  energy diagnostics;
- static plots exposing each comparison; and
- an explicit accepted/rejected status and claim boundary.

Candidate B is omitted. Its secondary role is already established and does not
help decide whether the tangent formulation reproduces the primary Candidate-A
local limit.

## Findings

All predeclared checks pass. The exact repository-derived symbolic Jacobian is
accepted against the independent directional finite differences: at the fixed
$h=10^{-6}$ assessment step, the largest relative error across six states and
five directions is $3.37\times10^{-6}$, below the $5\times10^{-5}$ limit. The
full recorded $h$ range shows the expected reduction and eventual round-off
floor rather than relying on a post-selected step.

Independent integer-turn shifts produce maximum absolute differences of
$7.75\times10^{-13}$ in the EL flow and $6.61\times10^{-13}$ in the Jacobian.
The corresponding maxima are $4.06\times10^{-14}$ for Cartesian observables
and $1.95\times10^{-13}$ for energy. The local angular chart is therefore
supported by the implemented dynamics and derived quantities.

### Finite-shadow limit

The finite-shadow results approach the direct tangent trace by approximately
one decimal order per perturbation decade:

| $\varepsilon$ | RMS log-norm error | Maximum log-norm error | RMS direction mismatch | Minimum signed cosine |
| ---: | ---: | ---: | ---: | ---: |
| $10^{-4}$ | $3.423\times10^{-3}$ | $6.293\times10^{-3}$ | $1.504\times10^{-6}$ | `0.9999955193` |
| $10^{-5}$ | $3.437\times10^{-4}$ | $6.324\times10^{-4}$ | $1.523\times10^{-8}$ | `0.9999999546` |
| $10^{-6}$ | $3.439\times10^{-5}$ | $6.328\times10^{-5}$ | $1.525\times10^{-10}$ | `0.9999999995` |

Both the norm and signed direction converge monotonically toward the tangent
solution over the full established `1.29 s` local prefix. This reproduces the
local finite-shadow dynamics without fitting a common exponential interval.

### Numerical convergence

The baseline tangent norm grows from `1` to `100.1778405750`, giving
$G(1.29)=4.6069470122$ and the descriptive
$\Lambda_{\rm tan}(1.29)=3.5712767537\ \mathrm{s^{-1}}$. These quantities are
finite-time diagnostics for the selected initial direction, not an exponent.

Baseline and strict tolerances give the same final value to recorded precision;
their maximum log-growth difference is `0`, maximum reference Candidate-A
distance is $1.11\times10^{-18}$, and maximum direction-component difference
is $1.39\times10^{-17}$. Both policies require `2049` RHS evaluations because
the common explicit step cap is active. This is accepted evidence of policy
agreement **within this declared short-time, capped protocol**, not evidence
that tolerances are irrelevant in a future long-time calculation.

Halving `max_step` changes the final descriptive rate by
$3.49\times10^{-14}$ relatively. The maximum log-growth difference is
$1.99\times10^{-13}$, maximum direction-component difference
$8.62\times10^{-14}$, and maximum reference distance
$1.81\times10^{-13}$. The refined solve uses `3585` RHS evaluations.

The maximum baseline reference energy drift is $8.45\times10^{-16}$, and all
requested states and solver segments are complete and finite. The accepted
baseline/strict discrepancy is therefore materially below repaired Experiment
005's long-time finite-shadow `10.767%` discrepancy, with the important
qualification that Experiment 006 validates only the prior short local regime.

### Decision

The experiment is accepted for its limited formulation-validation claim. It
supports direct tangent evolution as a trustworthy representation of local
perturbation growth and earns a separate long-time tangent-Lyapunov convergence
experiment. It does not establish that such a future experiment will converge.

## Acceptance boundary and stronger claims excluded

The strongest accepted claim is:

> Direct variational evolution of the Euler–Lagrange tangent vector reproduces
> the finite-shadow local dynamics in the small-perturbation limit and is
> materially more numerically stable under solver refinement than repeated
> finite-shadow subtraction.

Acceptance would earn a separate long-time tangent-Lyapunov convergence
experiment. This experiment does not implement tangent renormalisation, fit a
single exponential interval, estimate a maximal Lyapunov exponent, classify
the trajectory or system as chaotic, introduce new initial conditions, compare
Hamiltonian dynamics, or support the full Lyapunov spectrum.

## Reproduction commands

From the repository root:

```bash
MPLCONFIGDIR=/tmp/double-pendulum-mpl \
XDG_CACHE_HOME=/tmp/double-pendulum-cache \
PYTHONDONTWRITEBYTECODE=1 \
.venv/bin/python \
development/chaos_content/experiments/006_variational_dynamics_validation/variational_dynamics_validation.py \
--output-dir development/chaos_content/outputs/variational_dynamics_validation/baseline \
--self-check
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
development/chaos_content/experiments/006_variational_dynamics_validation
```
