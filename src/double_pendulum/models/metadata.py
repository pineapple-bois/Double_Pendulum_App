from dataclasses import dataclass

import numpy as np


def _integrator_name(integrator):
    return getattr(integrator, "__name__", str(integrator))


def _serializable_solver_kwargs(solver_kwargs):
    return {str(key): repr(value) for key, value in solver_kwargs.items()}


def _solver_value(solver_kwargs, solver_policy, key):
    if key in solver_kwargs:
        return solver_kwargs[key]
    if solver_policy is not None:
        return getattr(solver_policy, key, None)
    return None


def _time_endpoint(values, index):
    if values is None or len(values) == 0:
        return None
    return float(values[index])


@dataclass(frozen=True)
class SolverMetadata:
    policy_name: str | None
    integrator: str
    method: str | None
    rtol: float | None
    atol: float | None
    success: bool | None
    status: int | None
    message: str | None
    nfev: int | None
    njev: int | None
    nlu: int | None
    requested_time_count: int
    returned_time_count: int | None
    requested_time_start: float | None
    requested_time_end: float | None
    returned_time_start: float | None
    returned_time_end: float | None
    returned_time_matches_requested: bool | None
    solution_shape: tuple[int, ...]
    solver_kwargs: dict[str, str]

    @classmethod
    def from_solve_ivp(cls, integrator, ode_result, requested_time, solution, solver_kwargs, solver_policy=None):
        returned_time = getattr(ode_result, "t", None)
        returned_time_matches_requested = None
        if returned_time is not None:
            returned_time_matches_requested = (
                len(returned_time) == len(requested_time)
                and np.allclose(returned_time, requested_time, rtol=0, atol=0)
            )

        return cls(
            policy_name=getattr(solver_policy, "name", None),
            integrator=_integrator_name(integrator),
            method=_solver_value(solver_kwargs, solver_policy, "method"),
            rtol=_solver_value(solver_kwargs, solver_policy, "rtol"),
            atol=_solver_value(solver_kwargs, solver_policy, "atol"),
            success=bool(getattr(ode_result, "success", False)),
            status=getattr(ode_result, "status", None),
            message=getattr(ode_result, "message", None),
            nfev=getattr(ode_result, "nfev", None),
            njev=getattr(ode_result, "njev", None),
            nlu=getattr(ode_result, "nlu", None),
            requested_time_count=len(requested_time),
            returned_time_count=len(returned_time) if returned_time is not None else None,
            requested_time_start=_time_endpoint(requested_time, 0),
            requested_time_end=_time_endpoint(requested_time, -1),
            returned_time_start=_time_endpoint(returned_time, 0),
            returned_time_end=_time_endpoint(returned_time, -1),
            returned_time_matches_requested=returned_time_matches_requested,
            solution_shape=tuple(solution.shape),
            solver_kwargs=_serializable_solver_kwargs(solver_kwargs),
        )

    @classmethod
    def from_odeint(cls, integrator, requested_time, solution, solver_kwargs, solver_policy=None):
        return cls(
            policy_name=getattr(solver_policy, "name", None),
            integrator=_integrator_name(integrator),
            method=_solver_value(solver_kwargs, solver_policy, "method"),
            rtol=_solver_value(solver_kwargs, solver_policy, "rtol"),
            atol=_solver_value(solver_kwargs, solver_policy, "atol"),
            success=None,
            status=None,
            message=None,
            nfev=None,
            njev=None,
            nlu=None,
            requested_time_count=len(requested_time),
            returned_time_count=solution.shape[0],
            requested_time_start=_time_endpoint(requested_time, 0),
            requested_time_end=_time_endpoint(requested_time, -1),
            returned_time_start=_time_endpoint(requested_time, 0),
            returned_time_end=_time_endpoint(requested_time, -1),
            returned_time_matches_requested=solution.shape[0] == len(requested_time),
            solution_shape=tuple(solution.shape),
            solver_kwargs=_serializable_solver_kwargs(solver_kwargs),
        )

    def to_dict(self):
        return {
            "policy_name": self.policy_name,
            "integrator": self.integrator,
            "method": self.method,
            "rtol": self.rtol,
            "atol": self.atol,
            "success": self.success,
            "status": self.status,
            "message": self.message,
            "nfev": self.nfev,
            "njev": self.njev,
            "nlu": self.nlu,
            "requested_time_count": self.requested_time_count,
            "returned_time_count": self.returned_time_count,
            "requested_time_start": self.requested_time_start,
            "requested_time_end": self.requested_time_end,
            "returned_time_start": self.returned_time_start,
            "returned_time_end": self.returned_time_end,
            "returned_time_matches_requested": self.returned_time_matches_requested,
            "solution_shape": list(self.solution_shape),
            "solver_kwargs": dict(self.solver_kwargs),
        }
