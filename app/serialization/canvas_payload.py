"""Canvas-ready simulation payload helpers.

The helpers in this module format already-computed Python simulation results
for browser rendering. They deliberately do not perform physics, integration,
Hamiltonian velocity reconstruction, energy diagnostics, or Dash callback work.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np


CANVAS_MOTION_PAYLOAD_SCHEMA_VERSION = "canvas_motion_payload.v1"
CANVAS_PAYLOAD_STATUSES = ("success", "stale", "failed", "cleared", "empty")
DRAWABLE_PAYLOAD_STATUSES = ("success", "stale")
NON_DRAWABLE_PAYLOAD_STATUSES = ("failed", "cleared", "empty")

DRAWABLE_ARRAY_FIELDS = (
    "time_s",
    "theta1_deg",
    "theta2_deg",
    "x1",
    "y1",
    "x2",
    "y2",
)
LAGRANGIAN_VELOCITY_ARRAY_FIELDS = ("omega1_deg_per_s", "omega2_deg_per_s")


def build_canvas_motion_payload(
    simulation_result: Any | None = None,
    *,
    run_id: int,
    status: str = "success",
    model_type: str | None = None,
    system_type: str | None = None,
    request_label: str | None = None,
    message: str | None = None,
    warnings: Iterable[str] | None = None,
    errors: Iterable[str] | None = None,
    solver_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable Canvas motion payload.

    ``simulation_result`` is expected to be a completed production model
    instance, such as ``DoublePendulumLagrangian`` or
    ``DoublePendulumHamiltonian``. For ``failed``, ``cleared``, and ``empty``
    states, pass ``simulation_result=None`` so no drawable arrays are emitted.
    """

    _validate_status(status)
    warnings_list = list(warnings or [])
    errors_list = list(errors or [])

    payload: dict[str, Any] = {
        "schema_version": CANVAS_MOTION_PAYLOAD_SCHEMA_VERSION,
        "run_id": int(run_id),
        "status": status,
        "model_type": model_type or getattr(simulation_result, "model", None),
        "system_type": system_type or _infer_system_type(simulation_result),
        "request_label": request_label,
        "sample_count": 0,
        "duration_s": 0.0,
        "time_units": {"time_s": "seconds"},
        "state_units": {},
        "position_units": "model_length_units",
        "user_initial_conditions": {},
        "internal_initial_state_summary": {},
        "solver_metadata": _solver_metadata_to_dict(simulation_result, solver_metadata),
        "warnings": warnings_list,
        "errors": errors_list,
        "message": message,
        "bounds": {},
        "rendering": {
            "drawable": status in DRAWABLE_PAYLOAD_STATUSES,
            "autoplay_allowed": status == "success",
            "stale": status == "stale",
        },
        "payload_size_bytes": 0,
    }

    if status in NON_DRAWABLE_PAYLOAD_STATUSES:
        return _set_payload_size(payload)

    if simulation_result is None:
        payload["errors"].append(f"{status} payload requires a simulation result.")
        payload["rendering"]["drawable"] = False
        payload["rendering"]["autoplay_allowed"] = False
        return _set_payload_size(payload)

    time_samples = _time_samples_for_solution(simulation_result)
    state = np.asarray(simulation_result.sol, dtype=float)
    positions = _precomputed_positions(simulation_result)
    theta1_deg = np.rad2deg(state[:, 0])
    theta2_deg = np.rad2deg(state[:, 1])

    payload.update(
        {
            "sample_count": int(len(time_samples)),
            "duration_s": _duration(time_samples),
            "time_s": _to_float_list(time_samples),
            "theta1_deg": _to_float_list(theta1_deg),
            "theta2_deg": _to_float_list(theta2_deg),
            "x1": _to_float_list(positions[0]),
            "y1": _to_float_list(positions[1]),
            "x2": _to_float_list(positions[2]),
            "y2": _to_float_list(positions[3]),
            "state_units": {
                "theta1_deg": "degrees",
                "theta2_deg": "degrees",
            },
            "user_initial_conditions": _user_initial_conditions(simulation_result),
            "internal_initial_state_summary": _internal_initial_state_summary(simulation_result),
            "parameters": _parameter_summary(simulation_result),
            "bounds": _position_bounds(positions),
        }
    )

    if _infer_system_type(simulation_result) == "lagrangian":
        payload["omega1_deg_per_s"] = _to_float_list(np.rad2deg(state[:, 2]))
        payload["omega2_deg_per_s"] = _to_float_list(np.rad2deg(state[:, 3]))
        payload["state_units"].update(
            {
                "omega1_deg_per_s": "degrees/second",
                "omega2_deg_per_s": "degrees/second",
            }
        )
    elif _infer_system_type(simulation_result) == "hamiltonian":
        payload["warnings"].append(
            "Hamiltonian angular velocity time series omitted; solver state uses canonical momenta."
        )

    return _set_payload_size(payload)


def validate_canvas_motion_payload(payload: dict[str, Any]) -> list[str]:
    """Return schema, unit, shape, finite-value, and status problems."""

    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a dictionary."]

    _validate_common_fields(payload, problems)
    status = payload.get("status")
    system_type = payload.get("system_type")

    if _contains_energy_key(payload):
        problems.append("payload must not include energy diagnostics.")

    if status in DRAWABLE_PAYLOAD_STATUSES:
        _validate_drawable_payload(payload, problems)
    elif status in NON_DRAWABLE_PAYLOAD_STATUSES:
        _validate_non_drawable_payload(payload, problems)

    if status == "stale" and payload.get("rendering", {}).get("autoplay_allowed") is not False:
        problems.append("stale payload must explicitly disable autoplay.")

    if system_type == "hamiltonian":
        _validate_hamiltonian_label_safety(payload, problems)

    return problems


def estimate_canvas_payload_size(payload: dict[str, Any]) -> int:
    """Return a compact JSON size estimate in bytes."""

    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True, allow_nan=False)
    return len(encoded.encode("utf-8"))


def _set_payload_size(payload: dict[str, Any]) -> dict[str, Any]:
    """Set payload_size_bytes to a stable compact JSON byte estimate."""

    for _ in range(4):
        size_bytes = estimate_canvas_payload_size(payload)
        if payload.get("payload_size_bytes") == size_bytes:
            return payload
        payload["payload_size_bytes"] = size_bytes
    return payload


def summarise_canvas_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return compact diagnostics without large arrays."""

    drawable_fields = [field for field in (*DRAWABLE_ARRAY_FIELDS, *LAGRANGIAN_VELOCITY_ARRAY_FIELDS) if field in payload]
    solver_metadata = payload.get("solver_metadata") or {}
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "status": payload.get("status"),
        "model_type": payload.get("model_type"),
        "system_type": payload.get("system_type"),
        "sample_count": payload.get("sample_count"),
        "duration_s": payload.get("duration_s"),
        "payload_size_bytes": payload.get("payload_size_bytes"),
        "estimated_size_bytes": estimate_canvas_payload_size(payload),
        "drawable": payload.get("status") in DRAWABLE_PAYLOAD_STATUSES and bool(drawable_fields),
        "drawable_fields": drawable_fields,
        "state_units": dict(payload.get("state_units") or {}),
        "position_units": payload.get("position_units"),
        "bounds": dict(payload.get("bounds") or {}),
        "solver": {
            "integrator": solver_metadata.get("integrator"),
            "success": solver_metadata.get("success"),
            "status": solver_metadata.get("status"),
            "requested_time_count": solver_metadata.get("requested_time_count"),
            "returned_time_count": solver_metadata.get("returned_time_count"),
            "returned_time_matches_requested": solver_metadata.get("returned_time_matches_requested"),
        },
        "warnings": list(payload.get("warnings") or []),
        "message": payload.get("message"),
    }


def _validate_status(status: str) -> None:
    if status not in CANVAS_PAYLOAD_STATUSES:
        raise ValueError(f"Unsupported Canvas payload status: {status!r}")


def _infer_system_type(simulation_result: Any | None) -> str | None:
    if simulation_result is None:
        return None
    convention = getattr(simulation_result, "solver_state_convention", "")
    if "canonical_momenta" in convention:
        return "hamiltonian"
    if "angular_velocities" in convention:
        return "lagrangian"
    return None


def _solver_metadata_to_dict(
    simulation_result: Any | None,
    solver_metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if solver_metadata is not None:
        return dict(solver_metadata)
    metadata = getattr(simulation_result, "solver_metadata", None)
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()
    return dict(metadata)


def _time_samples_for_solution(simulation_result: Any) -> np.ndarray:
    state = np.asarray(simulation_result.sol)
    solver_time = getattr(simulation_result, "solver_time", None)
    if solver_time is not None and len(solver_time) == state.shape[0]:
        return np.asarray(solver_time, dtype=float)
    return np.asarray(simulation_result.time, dtype=float)


def _precomputed_positions(simulation_result: Any) -> np.ndarray:
    positions = getattr(simulation_result, "precomputed_positions", None)
    if positions is None:
        simulation_result.precompute_positions()
        positions = simulation_result.precomputed_positions
    return np.asarray(positions, dtype=float)


def _to_float_list(values: Iterable[Any]) -> list[float]:
    return [float(value) for value in values]


def _duration(time_samples: np.ndarray) -> float:
    if len(time_samples) < 2:
        return 0.0
    return float(time_samples[-1] - time_samples[0])


def _user_initial_conditions(simulation_result: Any) -> dict[str, float]:
    values = getattr(simulation_result, "user_initial_conditions_degrees", [])
    values = _to_float_list(values)
    if len(values) != 4:
        return {}
    return {
        "theta1_deg": values[0],
        "theta2_deg": values[1],
        "omega1_deg_per_s": values[2],
        "omega2_deg_per_s": values[3],
    }


def _internal_initial_state_summary(simulation_result: Any) -> dict[str, Any]:
    names = list(getattr(simulation_result, "solver_state_variable_names", []))
    values = _to_float_list(getattr(simulation_result, "initial_conditions", []))
    return {
        "state_convention": getattr(simulation_result, "solver_state_convention", None),
        "state_variable_names": names,
        "values": values,
        "units": _internal_state_units(names),
        "initial_condition_conversion": getattr(simulation_result, "initial_condition_conversion", None),
    }


def _internal_state_units(names: list[str]) -> dict[str, str]:
    units: dict[str, str] = {}
    for name in names:
        if name.startswith("theta"):
            units[name] = "radians"
        elif name.startswith("omega"):
            units[name] = "radians/second"
        elif name.startswith("p_theta"):
            units[name] = "canonical_momentum_internal_units"
        else:
            units[name] = "internal_units"
    return units


def _parameter_summary(simulation_result: Any) -> dict[str, Any]:
    parameters = getattr(simulation_result, "parameters", {})
    values = {str(symbol): float(value) for symbol, value in parameters.items()}
    return {
        "values": values,
        "length_units": "model_length_units",
        "mass_units": "model_mass_units",
        "gravity_units": "model_length_units/second^2",
    }


def _position_bounds(positions: np.ndarray) -> dict[str, float]:
    x_values = np.concatenate([positions[0], positions[2]])
    y_values = np.concatenate([positions[1], positions[3]])
    max_abs_extent = max(float(np.max(np.abs(x_values))), float(np.max(np.abs(y_values))))
    return {
        "min_x": float(np.min(x_values)),
        "max_x": float(np.max(x_values)),
        "min_y": float(np.min(y_values)),
        "max_y": float(np.max(y_values)),
        "max_abs_extent": max_abs_extent,
    }


def _validate_common_fields(payload: dict[str, Any], problems: list[str]) -> None:
    required_fields = (
        "schema_version",
        "run_id",
        "status",
        "model_type",
        "system_type",
        "sample_count",
        "duration_s",
        "time_units",
        "state_units",
        "position_units",
        "solver_metadata",
        "warnings",
        "bounds",
        "rendering",
        "payload_size_bytes",
    )
    for field in required_fields:
        if field not in payload:
            problems.append(f"missing required field: {field}.")

    if payload.get("schema_version") != CANVAS_MOTION_PAYLOAD_SCHEMA_VERSION:
        problems.append("schema_version must be canvas_motion_payload.v1.")
    if payload.get("status") not in CANVAS_PAYLOAD_STATUSES:
        problems.append(f"status must be one of {CANVAS_PAYLOAD_STATUSES}.")
    if not isinstance(payload.get("payload_size_bytes"), int) or payload.get("payload_size_bytes", 0) <= 0:
        problems.append("payload_size_bytes must be a positive integer.")


def _validate_drawable_payload(payload: dict[str, Any], problems: list[str]) -> None:
    sample_count = payload.get("sample_count")
    if not isinstance(sample_count, int) or sample_count <= 0:
        problems.append("drawable payload must have a positive integer sample_count.")
        sample_count = None

    required_drawable = (*DRAWABLE_ARRAY_FIELDS,)
    for field in required_drawable:
        if field not in payload:
            problems.append(f"drawable payload missing array field: {field}.")
        else:
            _validate_array_field(payload, field, sample_count, problems)

    if payload.get("system_type") == "lagrangian":
        for field in LAGRANGIAN_VELOCITY_ARRAY_FIELDS:
            if field not in payload:
                problems.append(f"Lagrangian drawable payload missing angular velocity field: {field}.")
            else:
                _validate_array_field(payload, field, sample_count, problems)

    time_values = np.asarray(payload.get("time_s", []), dtype=float)
    if len(time_values) > 1 and not np.all(np.diff(time_values) > 0):
        problems.append("time_s must be strictly increasing.")
    if len(time_values) > 1:
        expected_duration = float(time_values[-1] - time_values[0])
        if not np.isclose(float(payload.get("duration_s", 0.0)), expected_duration):
            problems.append("duration_s must match the time_s endpoints.")

    _validate_units(payload, problems)
    _validate_solver_metadata(payload, problems)
    _validate_initial_state(payload, problems)


def _validate_array_field(
    payload: dict[str, Any],
    field: str,
    sample_count: int | None,
    problems: list[str],
) -> None:
    values = payload.get(field)
    if not isinstance(values, list):
        problems.append(f"{field} must be a JSON list.")
        return
    if sample_count is not None and len(values) != sample_count:
        problems.append(f"{field} length must equal sample_count.")
    try:
        array = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        problems.append(f"{field} must contain numeric values.")
        return
    if not np.all(np.isfinite(array)):
        problems.append(f"{field} must contain only finite values.")


def _validate_units(payload: dict[str, Any], problems: list[str]) -> None:
    time_units = payload.get("time_units") or {}
    state_units = payload.get("state_units") or {}
    if time_units.get("time_s") != "seconds":
        problems.append("time_s unit must be seconds.")
    for field in ("theta1_deg", "theta2_deg"):
        if state_units.get(field) != "degrees":
            problems.append(f"{field} unit must be degrees.")
    if payload.get("system_type") == "lagrangian":
        for field in LAGRANGIAN_VELOCITY_ARRAY_FIELDS:
            if state_units.get(field) != "degrees/second":
                problems.append(f"{field} unit must be degrees/second.")
    if not payload.get("position_units"):
        problems.append("position_units must be explicit.")
    user_initial_conditions = payload.get("user_initial_conditions") or {}
    for field in ("theta1_deg", "theta2_deg", "omega1_deg_per_s", "omega2_deg_per_s"):
        if field not in user_initial_conditions:
            problems.append(f"user_initial_conditions missing explicit field: {field}.")


def _validate_solver_metadata(payload: dict[str, Any], problems: list[str]) -> None:
    metadata = payload.get("solver_metadata") or {}
    for field in (
        "integrator",
        "success",
        "status",
        "message",
        "requested_time_count",
        "returned_time_count",
        "solution_shape",
    ):
        if field not in metadata:
            problems.append(f"solver_metadata missing field: {field}.")


def _validate_initial_state(payload: dict[str, Any], problems: list[str]) -> None:
    summary = payload.get("internal_initial_state_summary") or {}
    for field in ("state_convention", "state_variable_names", "values", "units", "initial_condition_conversion"):
        if field not in summary:
            problems.append(f"internal_initial_state_summary missing field: {field}.")
    values = summary.get("values") or []
    names = summary.get("state_variable_names") or []
    if len(values) != len(names):
        problems.append("internal initial-state names and values must have matching lengths.")
    units = summary.get("units") or {}
    for name in names:
        if name not in units:
            problems.append(f"internal initial-state unit missing for {name}.")


def _validate_non_drawable_payload(payload: dict[str, Any], problems: list[str]) -> None:
    for field in (*DRAWABLE_ARRAY_FIELDS, *LAGRANGIAN_VELOCITY_ARRAY_FIELDS):
        if field in payload:
            problems.append(f"{payload.get('status')} payload must not contain drawable array field: {field}.")
    if payload.get("sample_count") not in (0, None):
        problems.append(f"{payload.get('status')} payload must not advertise drawable samples.")
    rendering = payload.get("rendering") or {}
    if rendering.get("drawable") is not False:
        problems.append(f"{payload.get('status')} payload must explicitly set rendering.drawable false.")
    if rendering.get("autoplay_allowed") is not False:
        problems.append(f"{payload.get('status')} payload must explicitly disable autoplay.")


def _validate_hamiltonian_label_safety(payload: dict[str, Any], problems: list[str]) -> None:
    for field in LAGRANGIAN_VELOCITY_ARRAY_FIELDS:
        if field in payload:
            problems.append("Hamiltonian payload must not serialize canonical momenta as angular velocities.")

    state_units = payload.get("state_units") or {}
    for field in LAGRANGIAN_VELOCITY_ARRAY_FIELDS:
        if field in state_units:
            problems.append("Hamiltonian payload must not expose angular velocity time-series units.")

    summary = payload.get("internal_initial_state_summary") or {}
    names = summary.get("state_variable_names") or []
    if any(name.startswith("omega") for name in names):
        problems.append("Hamiltonian internal state must use canonical momentum labels, not omega labels.")


def _contains_energy_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if "energy" in str(key).lower():
                return True
            if _contains_energy_key(nested):
                return True
    elif isinstance(value, list | tuple):
        return any(_contains_energy_key(item) for item in value)
    return False
