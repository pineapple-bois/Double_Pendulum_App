# 011 Hamiltonian/Canonical Spectrum Cross-Check

**Status: scaffolded/in preparation. No Hamiltonian tangent dynamics, QR run,
or spectrum comparison has been implemented.**

## Eventual research question

> Does an independently formulated Hamiltonian/canonical tangent QR
> calculation reproduce the statistically compatible Euler–Lagrange spectrum
> estimate accepted by Experiment 010?

Experiment 010 accepted, within its declared one-initial-condition and three-
shadow protocol, the Euler–Lagrange ensemble mean

$$
(0.983276,\ 0.012274,\ -0.009941,\ -0.986532)\ \mathrm{s^{-1}},
$$

with conservative descriptive componentwise half-widths

$$
(0.023858,\ 0.006367,\ 0.008376,\ 0.024798)\ \mathrm{s^{-1}}.
$$

Those half-widths are not confidence intervals. They combine Experiment 010's
final ensemble spread and residual `560→640 s` settling. They are a future
comparison target, not an Experiment 011 result.

## Purpose of this scaffold

This task establishes source provenance and an implementation boundary so a
later high-effort task can design the cross-check without broad repository
archaeology. The detailed inventory is in
[`canonical_model_notes.md`](canonical_model_notes.md).

The repository already supplies:

- production canonical state and initial-condition conversion conventions;
- a production symbolic simple-model Hamiltonian;
- production symbolic Hamilton equations and a numerical solver wrapper;
- short EL/Hamiltonian formulation-agreement regression evidence; and
- a self-contained but explicitly exploratory Hamiltonian/Poincaré RHS and
  numeric energy evaluator.

It does not yet supply a validated canonical flow Jacobian/Hessian, canonical
tangent evolution, canonical QR metric contract, or long-time Hamiltonian
spectrum evidence.

## Intended evidence sequence

The later executable experiment must proceed in this order:

```text
canonical state/formulation
  → EL ↔ canonical state equivalence
  → reference-flow equivalence
  → canonical tangent/Jacobian validation
  → canonical QR validation
  → eventual long-time spectrum comparison
```

| Stage | Evidence required before proceeding |
| --- | --- |
| Canonical state/formulation | Reproduce the production state order, Legendre map, Hamiltonian, parameters, and angular periodicity without copying exploratory code as authority. |
| EL ↔ canonical state equivalence | Validate forward and inverse state maps, including nonzero velocities and tangent-coordinate conversion. |
| Reference-flow equivalence | Show synchronized short canonical and EL reference trajectories agree after conversion under controlled solver policies. |
| Canonical tangent/Jacobian validation | Independently validate the canonical tangent operator with directional finite differences and periodicity/structural checks. |
| Canonical QR validation | Establish a dimensionally coherent metric, orthonormality, reconstruction, sign, and accumulation bookkeeping. |
| Long-time spectrum comparison | Only after all prior stages pass, compare a predeclared canonical ensemble with the Experiment 010 EL estimate and uncertainty boundary. |

Failure at any stage is a valid Experiment 011 outcome and stops the sequence.

## Current repository-supported formulation

The production canonical solver order is

$$
z=(\theta_1,\theta_2,p_{\theta_1},p_{\theta_2}),
$$

with $p=B(q)\dot q$ for the simple-model inertia matrix. Production constructs

$$
H(q,p)=\frac12p^{\mathsf T}B(q)^{-1}p+V(q)
$$

and forms

$$
\dot q=\frac{\partial H}{\partial p},
\qquad
\dot p=-\frac{\partial H}{\partial q}.
$$

Exact formulas, source locations, test evidence, and authority labels are
recorded in `canonical_model_notes.md`. This README does not promote the
exploratory Experiment 001 analytical RHS into accepted code.

## Intended Python boundary

`canonical_spectrum_crosscheck.py` contains only:

- static Experiment 010 target/provenance metadata;
- the canonical and EL state order contracts;
- a source-asset inventory;
- a small protocol describing eventual state conversion, energy, RHS, and
  Jacobian interfaces; and
- a `run_crosscheck()` placeholder that raises `NotImplementedError`.

It performs no symbolic derivation or numerical integration. The local tests
verify only this scaffold and source-path inventory.

## Explicit unresolved choices

The later design must resolve, before long-time computation:

1. how the canonical Jacobian is constructed and independently validated;
2. whether the tangent-coordinate map is derived analytically, symbolically,
   or by another controlled method;
3. the dimensionally coherent QR metric in canonical momentum coordinates;
4. whether that metric is a fixed canonical scaling or Candidate A pulled
   back through the state-dependent EL↔canonical tangent map;
5. how the initial tangent bases correspond across formulations;
6. the staged reference comparison and eventual numerical-shadow ensemble;
7. angle rebasing and $2\pi$ periodicity for canonical state, energy, RHS, and
   Jacobian;
8. the canonical numerical energy evaluator and normalization;
9. solver tolerance, `max_step`, restart, sampling, and QR-interval policies;
   and
10. a predeclared comparison rule that separates finite-time coordinate/metric
    transients from disagreement with Experiment 010.

No acceptance thresholds are invented in this scaffold.

## Accepted versus exploratory inputs

| Category | May be treated as current convention | Must be independently verified before scientific use |
| --- | --- | --- |
| Production model | Canonical state order; simple inertia/momentum map; symbolic Hamiltonian; Hamilton-equation construction; named solver policies | Numerical canonical RHS equivalence over the Experiment 010 reference; inverse and tangent maps; canonical Jacobian/Hessian; long-time validity |
| Experiment 001 Poincaré work | Evidence that a self-contained numerical formulation and energy diagnostic are feasible | Its explicit RHS, energy implementation, unrestricted-step solver protocol, event conventions, and unrelated initial condition |
| Experiment 010 | EL target mean, descriptive half-widths, physical case, Candidate-A result boundary | Any claim that the canonical finite-time QR geometry must reproduce individual EL QR columns pointwise |

## Claim boundary

Experiment 011 currently establishes only that the repository contains enough
source material to design an independent canonical formulation, subject to the
documented validation and metric choices.

No Hamiltonian tangent vector or matrix has been evolved. No canonical
Jacobian, QR primitive, finite-time spectrum, long-time spectrum, maximal
Lyapunov exponent, or EL/Hamiltonian agreement has been computed or accepted.
The Experiment 010 vector remains solely an EL comparison target.

## Lightweight scaffold check

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
development/chaos_content/experiments/011_hamiltonian_canonical_spectrum_crosscheck/test_canonical_spectrum_crosscheck.py
```

This command imports metadata and checks source paths only. It does not derive
equations or run a solver.
