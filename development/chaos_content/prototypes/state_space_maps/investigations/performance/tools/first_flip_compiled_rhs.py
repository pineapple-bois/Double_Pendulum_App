"""Investigation-only compiled physical RHS for the first-flip reference.

Only the four-state Euler--Lagrange RHS is compiled. The operational
``first_flip_time`` function continues to own solve_ivp, its four terminal
events, root finding, diagnostics, statuses, and censoring semantics.
"""

from __future__ import annotations

from ....src.first_flip.compiled import (
    compiled_physical_rhs,
    compiled_rhs,
    first_flip_time_compiled as _first_flip_time_compiled,
    initialize_compiled_rhs,
)
from ....src.first_flip.reference import FirstFlipResult
from ....src.lyapunov.reference import EulerLagrangeState, PendulumParameters, SolverSpec


PROTOTYPE_IDENTITY = "investigation_first_flip_numba_4state_rhs_v1"


def warm_compiled_rhs(parameters: PendulumParameters) -> None:
    """Exclude one-time Numba compilation from warm repeated cell timings."""

    initialize_compiled_rhs(parameters)


def first_flip_time_compiled_rhs(
    initial_state: EulerLagrangeState | tuple[float, float, float, float],
    parameters: PendulumParameters | None = None,
    solver_spec: SolverSpec | None = None,
    observation_horizon: float = 5.0,
) -> FirstFlipResult:
    """Run the exact operational event contract with only its RHS replaced."""

    fixed_parameters = parameters or PendulumParameters()
    return _first_flip_time_compiled(
        initial_state,
        parameters=fixed_parameters,
        solver_spec=solver_spec,
        observation_horizon=observation_horizon,
    )
