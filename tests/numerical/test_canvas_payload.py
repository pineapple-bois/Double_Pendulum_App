import json

import numpy as np
import pytest

from app.serialization import (
    CANVAS_MOTION_PAYLOAD_SCHEMA_VERSION,
    build_canvas_motion_payload,
    estimate_canvas_payload_size,
    summarise_canvas_payload,
    validate_canvas_motion_payload,
)
from src.double_pendulum.math.functions import M1, M2, g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumHamiltonian, DoublePendulumLagrangian


SIMPLE_PARAMETERS = {l1: 1.0, l2: 1.0, m1: 1.0, m2: 1.0, g: 9.81}
COMPOUND_PARAMETERS = {l1: 1.0, l2: 1.0, M1: 1.0, M2: 1.0, g: 9.81}
TIME_VECTOR = [0.0, 0.05, 4]

REPRESENTATIVE_CASES = (
    (
        "simple",
        "lagrangian",
        DoublePendulumLagrangian,
        SIMPLE_PARAMETERS,
        [10.0, 20.0, 0.0, 0.0],
    ),
    (
        "simple",
        "hamiltonian",
        DoublePendulumHamiltonian,
        SIMPLE_PARAMETERS,
        [45.0, -30.0, 10.0, -5.0],
    ),
    (
        "compound",
        "lagrangian",
        DoublePendulumLagrangian,
        COMPOUND_PARAMETERS,
        [35.0, -25.0, 8.0, -3.0],
    ),
    (
        "compound",
        "hamiltonian",
        DoublePendulumHamiltonian,
        COMPOUND_PARAMETERS,
        [45.0, -30.0, 10.0, -5.0],
    ),
)


def _build_pendulum(model_type, model_class, parameters, initial_conditions, time_vector=TIME_VECTOR):
    return model_class(parameters, initial_conditions, time_vector, model=model_type)


@pytest.mark.parametrize(
    ("model_type", "system_type", "model_class", "parameters", "initial_conditions"),
    REPRESENTATIVE_CASES,
)
def test_success_payload_schema_units_arrays_and_solver_metadata(
    model_type,
    system_type,
    model_class,
    parameters,
    initial_conditions,
):
    pendulum = _build_pendulum(model_type, model_class, parameters, initial_conditions)
    payload = build_canvas_motion_payload(
        pendulum,
        run_id=101,
        status="success",
        model_type=model_type,
        system_type=system_type,
        request_label=f"{model_type} {system_type}",
    )

    assert validate_canvas_motion_payload(payload) == []
    assert payload["schema_version"] == CANVAS_MOTION_PAYLOAD_SCHEMA_VERSION
    assert payload["status"] == "success"
    assert payload["rendering"]["drawable"] is True
    assert payload["rendering"]["autoplay_allowed"] is True
    assert payload["sample_count"] == TIME_VECTOR[2]
    assert payload["time_s"][0] == TIME_VECTOR[0]
    assert payload["time_s"][-1] == TIME_VECTOR[1]
    assert payload["duration_s"] == pytest.approx(TIME_VECTOR[1] - TIME_VECTOR[0])

    for field in ("time_s", "theta1_deg", "theta2_deg", "x1", "y1", "x2", "y2"):
        assert len(payload[field]) == payload["sample_count"]
        assert np.all(np.isfinite(payload[field]))

    assert payload["time_units"] == {"time_s": "seconds"}
    assert payload["state_units"]["theta1_deg"] == "degrees"
    assert payload["state_units"]["theta2_deg"] == "degrees"
    assert payload["position_units"] == "model_length_units"
    assert payload["user_initial_conditions"] == {
        "theta1_deg": initial_conditions[0],
        "theta2_deg": initial_conditions[1],
        "omega1_deg_per_s": initial_conditions[2],
        "omega2_deg_per_s": initial_conditions[3],
    }

    solver_metadata = payload["solver_metadata"]
    assert solver_metadata["integrator"] == "solve_ivp"
    assert solver_metadata["success"] is True
    assert solver_metadata["status"] == 0
    assert solver_metadata["message"]
    assert solver_metadata["requested_time_count"] == TIME_VECTOR[2]
    assert solver_metadata["returned_time_count"] == TIME_VECTOR[2]
    assert solver_metadata["solution_shape"] == [TIME_VECTOR[2], 4]

    json.dumps(payload, allow_nan=False)
    assert estimate_canvas_payload_size(payload) > 0
    assert payload["payload_size_bytes"] > 0


def test_lagrangian_payload_includes_audited_angular_velocity_arrays():
    pendulum = _build_pendulum(
        "simple",
        DoublePendulumLagrangian,
        SIMPLE_PARAMETERS,
        [45.0, -30.0, 10.0, -5.0],
    )
    payload = build_canvas_motion_payload(
        pendulum,
        run_id=102,
        model_type="simple",
        system_type="lagrangian",
    )

    assert validate_canvas_motion_payload(payload) == []
    assert "omega1_deg_per_s" in payload
    assert "omega2_deg_per_s" in payload
    assert payload["state_units"]["omega1_deg_per_s"] == "degrees/second"
    assert payload["state_units"]["omega2_deg_per_s"] == "degrees/second"
    assert len(payload["omega1_deg_per_s"]) == payload["sample_count"]
    assert len(payload["omega2_deg_per_s"]) == payload["sample_count"]


@pytest.mark.parametrize(
    ("model_type", "parameters"),
    [
        ("simple", SIMPLE_PARAMETERS),
        ("compound", COMPOUND_PARAMETERS),
    ],
)
def test_hamiltonian_payload_keeps_momentum_labels_and_omits_velocity_series(model_type, parameters):
    pendulum = _build_pendulum(
        model_type,
        DoublePendulumHamiltonian,
        parameters,
        [45.0, -30.0, 10.0, -5.0],
    )
    payload = build_canvas_motion_payload(
        pendulum,
        run_id=103,
        model_type=model_type,
        system_type="hamiltonian",
    )

    assert validate_canvas_motion_payload(payload) == []
    assert payload["user_initial_conditions"]["omega1_deg_per_s"] == 10.0
    assert payload["user_initial_conditions"]["omega2_deg_per_s"] == -5.0
    assert "omega1_deg_per_s" not in payload
    assert "omega2_deg_per_s" not in payload
    assert "omega1_deg_per_s" not in payload["state_units"]
    assert "omega2_deg_per_s" not in payload["state_units"]

    internal_summary = payload["internal_initial_state_summary"]
    assert internal_summary["state_convention"] == "angles_and_canonical_momenta"
    assert internal_summary["state_variable_names"] == ["theta1", "theta2", "p_theta_1", "p_theta_2"]
    assert internal_summary["units"]["p_theta_1"] == "canonical_momentum_internal_units"
    assert internal_summary["units"]["p_theta_2"] == "canonical_momentum_internal_units"
    assert "canonical momenta" in payload["warnings"][0]


def test_stale_payload_is_drawable_but_distinguishable_from_success():
    pendulum = _build_pendulum("simple", DoublePendulumLagrangian, SIMPLE_PARAMETERS, [10.0, 20.0, 0.0, 0.0])

    success_payload = build_canvas_motion_payload(
        pendulum,
        run_id=201,
        status="success",
        model_type="simple",
        system_type="lagrangian",
    )
    stale_payload = build_canvas_motion_payload(
        pendulum,
        run_id=201,
        status="stale",
        model_type="simple",
        system_type="lagrangian",
        message="Settings changed - rerun to update.",
    )

    assert validate_canvas_motion_payload(success_payload) == []
    assert validate_canvas_motion_payload(stale_payload) == []
    assert success_payload["status"] == "success"
    assert stale_payload["status"] == "stale"
    assert success_payload["rendering"]["autoplay_allowed"] is True
    assert stale_payload["rendering"]["autoplay_allowed"] is False
    assert stale_payload["rendering"]["stale"] is True
    assert stale_payload["time_s"] == success_payload["time_s"]


@pytest.mark.parametrize("status", ["failed", "cleared", "empty"])
def test_non_drawable_status_payloads_do_not_contain_success_arrays(status):
    payload = build_canvas_motion_payload(
        None,
        run_id=301,
        status=status,
        model_type="simple",
        system_type="lagrangian",
        message=f"{status} state",
        errors=["controlled state"] if status == "failed" else None,
    )

    assert validate_canvas_motion_payload(payload) == []
    assert payload["status"] == status
    assert payload["sample_count"] == 0
    assert payload["rendering"]["drawable"] is False
    assert payload["rendering"]["autoplay_allowed"] is False
    for field in ("time_s", "theta1_deg", "theta2_deg", "x1", "y1", "x2", "y2"):
        assert field not in payload
    assert "omega1_deg_per_s" not in payload
    assert "omega2_deg_per_s" not in payload


def test_payload_validation_rejects_bad_lengths_nonfinite_values_and_energy_keys():
    pendulum = _build_pendulum("simple", DoublePendulumLagrangian, SIMPLE_PARAMETERS, [10.0, 20.0, 0.0, 0.0])
    payload = build_canvas_motion_payload(
        pendulum,
        run_id=401,
        model_type="simple",
        system_type="lagrangian",
    )

    payload["theta1_deg"] = payload["theta1_deg"][:-1]
    payload["x1"][0] = float("nan")
    payload["energy_total"] = [1.0]

    problems = validate_canvas_motion_payload(payload)
    assert "theta1_deg length must equal sample_count." in problems
    assert "x1 must contain only finite values." in problems
    assert "payload must not include energy diagnostics." in problems


def test_longer_sample_payload_summary_is_compact_and_size_aware():
    pendulum = _build_pendulum(
        "simple",
        DoublePendulumLagrangian,
        SIMPLE_PARAMETERS,
        [20.0, -10.0, 4.0, -2.0],
        time_vector=[0.0, 0.5, 100],
    )
    payload = build_canvas_motion_payload(
        pendulum,
        run_id=501,
        model_type="simple",
        system_type="lagrangian",
        request_label="longer sample summary case",
    )
    summary = summarise_canvas_payload(payload)

    assert validate_canvas_motion_payload(payload) == []
    assert summary["sample_count"] == 100
    assert summary["payload_size_bytes"] == payload["payload_size_bytes"]
    assert summary["estimated_size_bytes"] == estimate_canvas_payload_size(payload)
    assert summary["drawable"] is True
    assert summary["drawable_fields"] == [
        "time_s",
        "theta1_deg",
        "theta2_deg",
        "x1",
        "y1",
        "x2",
        "y2",
        "omega1_deg_per_s",
        "omega2_deg_per_s",
    ]
    assert "time_s" not in summary
    assert "theta1_deg" not in summary
    assert "x1" not in summary
