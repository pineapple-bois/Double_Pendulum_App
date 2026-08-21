# 003 Lyapunov Distance Contract

**Status: contract defined; implementation not started.**

This directory reserves the next chronological Chaos sandbox experiment. It
contains documentation only and does not implement finite-time exponents,
Lyapunov estimation, perturbation renormalisation, or a reusable Chaos API.

## Question

> What definition of distance between nearby double-pendulum states is
> mathematically appropriate for finite-time divergence and eventual Lyapunov
> analysis?

## Definition To Establish

The current Stage 1 teaching prototype displays second-bob Cartesian distance.
That physically intuitive, bounded observable is not automatically a norm on
the full dynamical state. This experiment must formalise the state-space object
before any divergence rate is estimated.

The investigation will consider, without yet deciding:

- the current Euler–Lagrange state
  $$(\theta_1,\theta_2,\omega_1,\omega_2)$$;
- wrapped angular differences and angular periodicity;
- the unlike dimensions of angles and angular velocities;
- nondimensionalisation or physically justified scaling;
- Cartesian, generalized-coordinate, and tangent-space representations;
- dependence of finite-time divergence values on the selected norm;
- infinitesimal perturbations versus the finite perturbation used in the
  teaching prototype;
- saturation of bounded physical-space distances; and
- eventual perturbation-renormalisation requirements.

## Experiment Boundary

No minimal executable experiment, numerical acceptance policy, or preferred
norm has yet been accepted. Those must be defined before implementation under
the sandbox's usual question, definition, numerical-validity, static-inspection,
acceptance, findings, and next-experiment discipline.

Experiment number 003 records chronology only. It is not a maturity level or an
epistemic ranking.
