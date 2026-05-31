from dataclasses import dataclass


@dataclass(frozen=True)
class SolverPolicy:
    """Explicit solve_ivp policy for production and diagnostic model runs."""

    name: str
    method: str | None
    rtol: float | None
    atol: float | None
    role: str

    def solve_ivp_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {}
        if self.method is not None:
            kwargs["method"] = self.method
        if self.rtol is not None:
            kwargs["rtol"] = self.rtol
        if self.atol is not None:
            kwargs["atol"] = self.atol
        return kwargs


SIMPLE_DEFAULT_SOLVER_POLICY = SolverPolicy(
    name="simple_default",
    method="DOP853",
    rtol=1e-6,
    atol=1e-8,
    role="leading app-facing simple-model candidate",
)

SIMPLE_REFERENCE_SOLVER_POLICY = SolverPolicy(
    name="simple_reference",
    method="DOP853",
    rtol=1e-9,
    atol=1e-11,
    role="high-fidelity simple-model reference",
)

SOLVE_IVP_DEFAULT_BASELINE_POLICY = SolverPolicy(
    name="solve_ivp_default_baseline",
    method=None,
    rtol=None,
    atol=None,
    role="baseline/testing reference; not the app-facing default candidate",
)


def merge_solver_policy_kwargs(
    solver_policy: SolverPolicy | None,
    integrator_args: dict[str, object],
) -> dict[str, object]:
    kwargs = solver_policy.solve_ivp_kwargs() if solver_policy is not None else {}
    kwargs.update(integrator_args)
    return kwargs
