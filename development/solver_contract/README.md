# Solver Contract Planning

Date: 2026-05-31

This directory is a Phase 8 planning area for production solver-policy
hardening and solver-failure handling. It is documentation and audit evidence
only. It does not change production solver behavior, Canvas rendering, callback
flow, UI styling, compound-model math, or the roadmap.

## Index

- [Solver Contract Audit](SOLVER_CONTRACT_AUDIT.md)
- [Implementation Plan](IMPLEMENTATION_PLAN.md)
- [UX Performance Inspection Checklist](UX_PERFORMANCE_INSPECTION.md)

## Purpose

The simple-model evidence lab in `development/math_fidelity/` shows that bare
default `solve_ivp` is risky for app-facing simple-model runs. Before changing
production solver settings, production code needs a clear contract for:

- solver policy selection;
- solver metadata capture;
- validation errors versus solver failures;
- callback-safe result states;
- Canvas payload render-safety gating;
- tests that make failed or partial trajectories impossible to render as
  successful output.

## Evidence Relationship

This planning area builds on local evidence from:

- `development/math_fidelity/SOLVER_POLICY_RECOMMENDATION.md`
- `development/math_fidelity/DRIFT_INVESTIGATION.md`
- `development/math_fidelity/SOLVER_COST_BENCHMARK.md`
- `development/math_fidelity/APP_LIKE_COST_BENCHMARK.md`

The current leading simple-model production-default candidate is:

```text
simple_default: method="DOP853", rtol=1e-6, atol=1e-8
```

The current high-fidelity/reference candidate is:

```text
simple_reference: method="DOP853", rtol=1e-9, atol=1e-11
```

Those policies are recommendations only until the production contract and tests
described here are implemented.

## Non-Goals

This planning pass does not:

- change production solver policy;
- change Canvas payload code;
- change simulation callbacks;
- change app UI or styling;
- change compound-model math;
- implement Hamiltonian chaos tooling;
- rewrite `ROADMAP.md`;
- add production tests.
