import importlib

import numpy as np
import pytest

from app.serialization import build_canvas_motion_payload, validate_canvas_motion_payload
from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import (
    SIMPLE_DEFAULT_SOLVER_POLICY,
    SimulationResultState,
    DoublePendulumHamiltonian,
    DoublePendulumLagrangian,
    solver_failure_result,
)


SIMPLE_PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
INITIAL_CONDITIONS_DEGREES = [10.0, 20.0, 0.0, 0.0]
TIME_VECTOR = [0.0, 1.0, 20]


class FakeFailedOdeResult:
    def __init__(self, y0, t_eval):
        partial_t = np.asarray(t_eval[:2], dtype=float)
        self.t = partial_t
        self.y = np.column_stack([np.asarray(y0, dtype=float), np.asarray(y0, dtype=float) + 0.01])
        self.success = False
        self.status = -1
        self.message = "forced solver failure for contract test"
        self.nfev = 7
        self.njev = 0
        self.nlu = 0


def fake_failed_solve_ivp(system, t_span, y0, t_eval=None, **kwargs):
    return FakeFailedOdeResult(y0, t_eval)


@pytest.mark.parametrize(
    ("module_name", "model_class"),
    [
        ("src.double_pendulum.models.lagrangian", DoublePendulumLagrangian),
        ("src.double_pendulum.models.hamiltonian", DoublePendulumHamiltonian),
    ],
)
def test_failed_solve_preserves_metadata_and_is_not_render_safe(monkeypatch, module_name, model_class):
    model_module = importlib.import_module(module_name)
    monkeypatch.setattr(model_module, "solve_ivp", fake_failed_solve_ivp)

    pendulum = model_class(
        SIMPLE_PARAMETERS,
        INITIAL_CONDITIONS_DEGREES,
        TIME_VECTOR,
        model="simple",
        integrator=fake_failed_solve_ivp,
        solver_policy=SIMPLE_DEFAULT_SOLVER_POLICY,
    )

    metadata = pendulum.solver_metadata
    result = solver_failure_result("Solver failed.", metadata.message)

    assert result.state == SimulationResultState.SOLVER_FAILURE
    assert result.render_safe is False
    assert metadata.policy_name == "simple_default"
    assert metadata.method == "DOP853"
    assert metadata.rtol == 1e-6
    assert metadata.atol == 1e-8
    assert metadata.success is False
    assert metadata.status == -1
    assert metadata.message == "forced solver failure for contract test"
    assert metadata.nfev == 7
    assert metadata.requested_time_count == TIME_VECTOR[2]
    assert metadata.returned_time_count == 2
    assert metadata.returned_time_matches_requested is False
    assert pendulum.sol.shape == (2, 4)

    with pytest.raises(ValueError, match="requires successful solver metadata"):
        build_canvas_motion_payload(
            pendulum,
            run_id=901,
            status="success",
            model_type="simple",
            system_type="lagrangian",
        )

    failed_payload = build_canvas_motion_payload(
        None,
        run_id=902,
        status="failed",
        model_type="simple",
        system_type="lagrangian",
        failure_reason=SimulationResultState.SOLVER_FAILURE.value,
        solver_metadata=metadata.to_dict(),
        errors=[metadata.message],
    )
    assert validate_canvas_motion_payload(failed_payload) == []
    assert failed_payload["rendering"]["drawable"] is False
    assert failed_payload["failure_reason"] == "solver_failure"
    assert "time_s" not in failed_payload
