# Sensitivity to Lyapunov — mathematical storyboard

This is the mathematical companion to the strand's first rendered figure. The
executable writes that deliverable under `../outputs/`; explanation belongs
here rather than in terminal narration.

## The learning question

Begin with one physical double pendulum and a second whose initial condition is
almost identical. The reference Euler--Lagrange state is

$$
x=(\theta_1,\theta_2,\omega_1,\omega_2),
$$

and the nearby trajectory starts at

$$
x'_0=x_0+\Delta x_0.
$$

For the executable story,

$$
x_0=(179^\circ,179^\circ,0,0),
\qquad
\Delta x_0=(0,10^{-6},0,0),
$$

where the finite angular perturbation is in radians. The two systems share the
same simple-model parameters and numerical policy.

The question is not initially “what is the Lyapunov exponent?” It is the more
concrete question: **do the two physical pendulums remain close?** Each later
object is introduced because the preceding object has a specific limitation.

## 1. Physical trajectories and second-bob distance

For link lengths $l_1$ and $l_2$, the second bob has position

$$
\mathbf r_2(x)=
\begin{pmatrix}
l_1\sin\theta_1+l_2\sin\theta_2\\
-l_1\cos\theta_1-l_2\cos\theta_2
\end{pmatrix}.
$$

The most immediate separation is therefore

$$
d_{\mathrm{bob}}(t)
=
\left\|
\mathbf r_2\bigl(x'(t)\bigr)-\mathbf r_2\bigl(x(t)\bigr)
\right\|_2.
$$

This is dimensional, periodic in both angles, and visually meaningful: it is
the distance in metres between the two end bobs.

Its limitation follows from the geometry. Each second bob remains within
$l_1+l_2$ of the pivot, so the triangle inequality gives

$$
d_{\mathrm{bob}}(t)\leq 2(l_1+l_2).
$$

For the unit-link story,

$$
d_{\mathrm{bob}}(t)\leq4\ \mathrm{m}.
$$

Thus $d_{\mathrm{bob}}$ can show that motions become visibly different, but it
cannot record unbounded accumulated dynamical stretching. It also observes
position only: two states can share similar bob positions while having
different angular velocities.

## 2. Finite full-state separation in Candidate-A geometry

To compare complete Euler--Lagrange states, first define a periodic finite
angular subtraction. For $i\in\{1,2\}$,

$$
\Delta\theta_i
=
\operatorname{wrap}_{(-\pi,\pi]}(\theta'_i-\theta_i),
\qquad
\Delta\omega_i=\omega'_i-\omega_i.
$$

The branch convention is deterministic: an exact $-\pi$ result is represented
as $+\pi$. Only finite angular differences are wrapped. Solver trajectories are
not reduced before integration.

Angles are dimensionless while angular velocities have units of inverse time,
so an unscaled Euclidean mixture would not be a dimensionally coherent working
distance. Candidate A introduces

$$
T_c=\sqrt{\frac{L_c}{g}},
\qquad
S=\operatorname{diag}(1,1,T_c,T_c),
$$

and the finite full-state distance

$$
d_{\mathrm{EL}}(t)
=
\left\|
S
\begin{pmatrix}
\Delta\theta_1(t)\\
\Delta\theta_2(t)\\
\Delta\omega_1(t)\\
\Delta\omega_2(t)
\end{pmatrix}
\right\|_2.
$$

The prototype retains the experimentally validated convention
$L_c=1\ \mathrm{m}$. Candidate A is a named working geometry, not a uniquely
correct norm.

This object improves on bob distance because it sees the whole physical state
and scales its unlike components explicitly. Its limitation is different: it
still subtracts two **finite trajectories**. Once $d_{\mathrm{EL}}$ is no
longer small, $x'(t)-x(t)$ is a chord between separate histories rather than a
local perturbation attached to $x(t)$. Wrapping keeps finite angular
subtraction physically local at branch boundaries; it does not make a
macroscopic shadow infinitesimal.

For that reason, the workflow exposes Candidate-A finite separation only with
an explicit local mask. In the declared story the mask is

$$
d_{\mathrm{EL}}(t)\leq10^{-2}.
$$

This is an inherited validation ceiling for the prototype interval, not a
universal definition of locality.

## 3. The local limit and tangent dynamics

Let the physical flow be

$$
\frac{\mathrm{d}x}{\mathrm{d}t}=f(x).
$$

For an infinitesimal perturbation $\delta x$ attached to the reference
trajectory, linearising the flow gives

$$
\frac{\mathrm{d}}{\mathrm{d}t}\delta x
=J(x)\,\delta x,
\qquad
J(x)=\frac{\partial f}{\partial x}.
$$

The reference and tangent are integrated together:

$$
\frac{\mathrm{d}}{\mathrm{d}t}
\begin{pmatrix}x\\\delta x\end{pmatrix}
=
\begin{pmatrix}f(x)\\J(x)\delta x\end{pmatrix}.
$$

The prototype differentiates the actual parameter-substituted production
Euler--Lagrange flow symbolically. This ensures the reference and tangent
equations describe the same vector field; directional finite differences and
trusted short-time trajectories then test that construction independently.

The finite perturbation and initial tangent share a direction. If

$$
\varepsilon=\|S\Delta x_0\|_2,
$$

then the unit Candidate-A initial tangent is

$$
\delta x_0=\frac{\Delta x_0}{\varepsilon},
\qquad
\|S\delta x_0\|_2=1.
$$

The bridge from finite separation to the derivative of the flow is visible in
the local limit

$$
\frac{S\bigl(x'(t)-x(t)\bigr)}{\varepsilon}
\longrightarrow
S\delta x(t)
\quad\text{as}\quad\varepsilon\to0,
$$

with wrapped differences used on the finite left-hand side. Norm agreement is
not enough by itself, so the prototype also exposes the signed direction
cosine between the scaled finite difference and scaled tangent.

Tangent angular components on the right-hand side are coordinate-basis vector
components, not finite angles. They are **never wrapped**. During piecewise
integration the physical reference angles may be rebased by integer turns for
numerical hygiene, while every tangent component is preserved unchanged.

## 4. Tangent norm and logarithmic stretch

The Candidate-A tangent magnitude is

$$
N(t)=\|S\delta x(t)\|_2.
$$

Raw tangent magnitude depends on the arbitrary scale chosen for
$\delta x_0$. A ratio removes that scale, and a logarithm turns multiplicative
stretching into additive growth:

$$
G(t)
=
\log\frac{N(t)}{N(0)}.
$$

Positive $G$ means net stretching over the interval; negative $G$ means net
contraction. $G$ can rise and fall. No assumption of one constant exponential
slope is built into this definition, which matters because Experiment 004 did
not establish a common approximately exponential window under its declared
rule.

## 5. A finite-time stretching-rate diagnostic

For $t>0$, accumulated logarithmic stretch per unit time is

$$
\Lambda(t)
=
\frac{G(t)}{t}
=
\frac{1}{t}
\log\frac{\|S\delta x(t)\|_2}{\|S\delta x(0)\|_2}.
$$

At $t=0$ this ratio is undefined; the implementation records `NaN` instead of
inventing a value. At the endpoint $T=1.29\ \mathrm{s}$, $\Lambda(T)$ is
clearly labelled a **finite-time stretching-rate diagnostic** (or finite-time
Lyapunov diagnostic).

An asymptotic Lyapunov exponent would require an additional limit and the
associated convergence evidence:

$$
\lambda
=
\lim_{T\to\infty}
\frac{1}{T}
\log\frac{\|S\delta x(T)\|_2}{\|S\delta x(0)\|_2}.
$$

This prototype neither takes nor claims that limit. It performs no repeated
renormalisation and no QR evolution. Experiments 007–014 explain why a
long-time finite value must not be silently promoted to an asymptotic
exponent.

## What the complete story establishes

For one declared state, perturbation direction, metric, and validated local
interval, the learner can see all of the following at the same sample times:

1. two nearby physical trajectories;
2. their bounded second-bob distance $d_{\mathrm{bob}}(t)$;
3. their local finite full-state distance $d_{\mathrm{EL}}(t)$;
4. the directly integrated unwrapped tangent $\delta x(t)$;
5. its Candidate-A magnitude $N(t)$ and logarithmic stretch $G(t)$;
6. the finite-time diagnostic $\Lambda(t)$.

The strongest supported interpretation is local and directional: the direct
tangent reproduces the small finite-shadow limit and quantifies finite-time
stretching along this reference trajectory. It is not a universal statement
about the double pendulum, an asymptotic exponent, a full spectrum, or a chaos
map.
