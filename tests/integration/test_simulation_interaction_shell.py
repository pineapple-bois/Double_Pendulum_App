from pathlib import Path

from dash import dcc, html

from app.callbacks.simulation import build_input_change_result, build_simulation_run_result
from app.components.simulation_interaction import (
    CANVAS_PAYLOAD_STORE_ID,
    CANVAS_MOTION_VIEW_ID,
    CANVAS_PROJECTION_VIEW_ID,
    CANVAS_TIME_SERIES_VIEW_ID,
    CANVAS_WORKSPACE_ID,
    DISPLAY_OPTIONS_ID,
    FRAME_INDICATOR_ID,
    INTERACTION_SHELL_ID,
    PAUSE_BUTTON_ID,
    PLAYBACK_STATE_STORE_ID,
    PLAY_BUTTON_ID,
    RENDERER_SYNC_SIGNAL_ID,
    RESET_BUTTON_ID,
    RESULT_STATE_STORE_ID,
    RUN_SUMMARY_AREA_ID,
    SCRUBBER_ID,
    SOLVER_DIAGNOSTICS_AREA_ID,
    STATUS_MESSAGE_ID,
)
from app.pages.registry import get_layout_for_path
from app.serialization import build_canvas_motion_payload, validate_canvas_motion_payload
from tests.helpers import extract_dash_text


CALLBACK_SENSITIVE_IDS = {
    "submit-val",
    "scroll-target",
    "model-type",
    "system-type",
    "param_g",
    "param_l1",
    "param_l2",
    "param_m1",
    "param_m2",
    "param_M1",
    "param_M2",
    "init_cond_theta1",
    "init_cond_theta2",
    "init_cond_omega1",
    "init_cond_omega2",
    "time_start",
    "time_end",
    "unity-parameters",
    "info-popup",
    "info-button",
    "close-info-button",
}

LEGACY_PLOTLY_OUTPUT_IDS = {
    "animation-phase-container",
    "time-graph-container",
    "time-graph-section",
    "error-message",
    "pendulum-animation",
    "phase-graph",
    "time-graph",
    "loading-animation-phase",
}

SHELL_IDS = {
    CANVAS_PAYLOAD_STORE_ID,
    RESULT_STATE_STORE_ID,
    PLAYBACK_STATE_STORE_ID,
    INTERACTION_SHELL_ID,
    CANVAS_WORKSPACE_ID,
    STATUS_MESSAGE_ID,
    RUN_SUMMARY_AREA_ID,
    SOLVER_DIAGNOSTICS_AREA_ID,
    PLAY_BUTTON_ID,
    PAUSE_BUTTON_ID,
    RESET_BUTTON_ID,
    SCRUBBER_ID,
    DISPLAY_OPTIONS_ID,
    FRAME_INDICATOR_ID,
    CANVAS_MOTION_VIEW_ID,
    CANVAS_TIME_SERIES_VIEW_ID,
    CANVAS_PROJECTION_VIEW_ID,
    RENDERER_SYNC_SIGNAL_ID,
}


def collect_ids(component):
    ids = set()
    stack = [component]
    while stack:
        item = stack.pop()
        if item is None or isinstance(item, (str, int, float)):
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue
        component_id = getattr(item, "id", None)
        if component_id:
            ids.add(component_id)
        children = getattr(item, "children", None)
        if children is not None:
            stack.append(children)
    return ids


def collect_class_names(component):
    class_names = set()
    stack = [component]
    while stack:
        item = stack.pop()
        if item is None or isinstance(item, (str, int, float)):
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue
        class_name = getattr(item, "className", None)
        if class_name:
            class_names.update(str(class_name).split())
        children = getattr(item, "children", None)
        if children is not None:
            stack.append(children)
    return class_names


def find_by_id(component, target_id):
    stack = [component]
    while stack:
        item = stack.pop()
        if item is None or isinstance(item, (str, int, float)):
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue
        if getattr(item, "id", None) == target_id:
            return item
        children = getattr(item, "children", None)
        if children is not None:
            stack.append(children)
    return None


def text_from(component):
    return " ".join(extract_dash_text(component))


def callback_outputs(callback):
    outputs = callback.get("output") or []
    if isinstance(outputs, (list, tuple)):
        return outputs
    return [outputs]


def test_simulation_layout_adds_memory_scoped_stores_and_preserves_existing_ids():
    layout = get_layout_for_path("/simulation")
    ids = collect_ids(layout)

    assert CALLBACK_SENSITIVE_IDS <= ids
    assert SHELL_IDS <= ids
    assert LEGACY_PLOTLY_OUTPUT_IDS.isdisjoint(ids)

    canvas_store = find_by_id(layout, CANVAS_PAYLOAD_STORE_ID)
    result_store = find_by_id(layout, RESULT_STATE_STORE_ID)
    playback_store = find_by_id(layout, PLAYBACK_STATE_STORE_ID)

    assert isinstance(canvas_store, dcc.Store)
    assert canvas_store.storage_type == "memory"
    assert canvas_store.data["status"] == "empty"
    assert validate_canvas_motion_payload(canvas_store.data) == []
    assert result_store.storage_type == "memory"
    assert result_store.data["status"] == "empty"
    assert playback_store.storage_type == "memory"
    assert playback_store.data["playback_state"] == "idle"


def test_simulation_layout_includes_canvas_targets_and_local_controls():
    layout = get_layout_for_path("/simulation")
    classes = collect_class_names(layout)

    assert isinstance(find_by_id(layout, CANVAS_MOTION_VIEW_ID), html.Canvas)
    assert isinstance(find_by_id(layout, CANVAS_TIME_SERIES_VIEW_ID), html.Canvas)
    assert isinstance(find_by_id(layout, CANVAS_PROJECTION_VIEW_ID), html.Canvas)
    assert find_by_id(layout, FRAME_INDICATOR_ID) is not None
    assert {
        "canvas-panel-motion",
        "canvas-panel-projection",
        "canvas-panel-time",
        "playback-control-row",
        "simulation-detail-diagnostics",
    } <= classes

    scrubber = find_by_id(layout, SCRUBBER_ID)
    display_options = find_by_id(layout, DISPLAY_OPTIONS_ID)

    assert isinstance(scrubber, dcc.Input)
    assert scrubber.type == "range"
    assert scrubber.disabled is True
    assert isinstance(display_options, dcc.Checklist)
    assert display_options.value == ["axes", "grid"]
    assert {option["value"] for option in display_options.options} == {"axes", "grid"}
    assert all(option["disabled"] is True for option in display_options.options)


def test_submit_val_remains_registered_run_trigger():
    import pendulum_app

    submit_callbacks = [
        callback
        for callback in pendulum_app.app.callback_map.values()
        if any(item.get("id") == "submit-val" for item in callback.get("inputs", []))
    ]

    assert len(submit_callbacks) == 1
    callback = submit_callbacks[0]
    output_ids = {output.component_id for output in callback_outputs(callback)}
    assert CANVAS_PAYLOAD_STORE_ID in output_ids
    assert RESULT_STATE_STORE_ID in output_ids
    assert LEGACY_PLOTLY_OUTPUT_IDS.isdisjoint(output_ids)


def test_callbacks_do_not_target_retired_plotly_layout_components():
    import pendulum_app

    callback_output_ids = {
        output.component_id
        for callback in pendulum_app.app.callback_map.values()
        for output in callback_outputs(callback)
    }

    assert LEGACY_PLOTLY_OUTPUT_IDS.isdisjoint(callback_output_ids)


def test_renderer_store_sync_clientside_callback_is_registered():
    import pendulum_app

    renderer_callback = pendulum_app.app.callback_map[f"{RENDERER_SYNC_SIGNAL_ID}.children"]
    renderer_callback_config = [
        item
        for item in pendulum_app.app._callback_list
        if item.get("output") == f"{RENDERER_SYNC_SIGNAL_ID}.children"
    ][0]
    input_ids = {item["id"] for item in renderer_callback["inputs"]}

    assert {
        CANVAS_PAYLOAD_STORE_ID,
        RESULT_STATE_STORE_ID,
        PLAYBACK_STATE_STORE_ID,
    } <= input_ids
    assert "clientside_function" in renderer_callback_config


def test_successful_run_result_stores_valid_canvas_payload_without_plotly_generation():
    result = build_simulation_run_result(
        1,
        10.0,
        20.0,
        0.0,
        0.0,
        0.0,
        0.02,
        1.0,
        1.0,
        1.0,
        1.0,
        None,
        None,
        9.81,
        "simple",
        "lagrangian",
    )

    payload = result["canvas_payload"]
    assert validate_canvas_motion_payload(payload) == []
    assert payload["status"] == "success"
    assert payload["rendering"]["drawable"] is True
    assert result["result_state"]["status"] == "success"
    assert "animation_phase_children" not in result
    assert "time_graph_children" not in result
    assert "animation_phase_style" not in result

    summary_text = text_from(result["run_summary_children"])
    diagnostics_text = text_from(result["solver_diagnostics_children"])
    assert "State: success" in summary_text
    assert "Integrator: solve_ivp" in diagnostics_text
    assert "Payload validation passed." in diagnostics_text
    forbidden_text = f"{summary_text} {diagnostics_text}".lower()
    assert "energy" not in forbidden_text
    assert "chaos" not in forbidden_text


def test_validation_failure_stores_failed_non_drawable_payload():
    result = build_simulation_run_result(
        2,
        10.0,
        20.0,
        0.0,
        0.0,
        0.0,
        0.02,
        None,
        1.0,
        1.0,
        1.0,
        None,
        None,
        9.81,
        "simple",
        "lagrangian",
    )

    payload = result["canvas_payload"]
    assert validate_canvas_motion_payload(payload) == []
    assert payload["status"] == "failed"
    assert payload["rendering"]["drawable"] is False
    assert result["result_state"]["status"] == "failed"
    assert result["playback_state"]["playback_state"] == "cancelled"
    assert "time_s" not in payload
    assert "theta1_deg" not in payload


def test_input_change_marks_success_payload_stale_without_recomputing_physics():
    success_result = build_simulation_run_result(
        3,
        10.0,
        20.0,
        0.0,
        0.0,
        0.0,
        0.02,
        1.0,
        1.0,
        1.0,
        1.0,
        None,
        None,
        9.81,
        "simple",
        "lagrangian",
    )

    stale_result = build_input_change_result(
        12.0,
        20.0,
        0.0,
        0.0,
        0.0,
        0.02,
        1.0,
        1.0,
        1.0,
        1.0,
        None,
        None,
        9.81,
        "simple",
        "lagrangian",
        success_result["canvas_payload"],
        current_playback_state=success_result["playback_state"],
    )

    payload = stale_result["canvas_payload"]
    assert validate_canvas_motion_payload(payload) == []
    assert payload["status"] == "stale"
    assert payload["rendering"]["drawable"] is True
    assert payload["rendering"]["autoplay_allowed"] is False
    assert stale_result["result_state"]["status"] == "stale"
    assert stale_result["playback_state"]["playback_state"] == "cancelled"
    assert "Settings changed" in text_from(stale_result["status_children"])


def test_empty_and_cleared_payload_states_are_non_drawable():
    empty_payload = build_canvas_motion_payload(None, run_id=0, status="empty", message="No run yet.")
    cleared_payload = build_canvas_motion_payload(None, run_id=4, status="cleared", message="Output cleared.")

    for payload in (empty_payload, cleared_payload):
        assert validate_canvas_motion_payload(payload) == []
        assert payload["rendering"]["drawable"] is False
        assert payload["sample_count"] == 0
        assert "time_s" not in payload
        assert "theta1_deg" not in payload


def test_hamiltonian_run_payload_does_not_expose_momenta_as_angular_velocity_series():
    result = build_simulation_run_result(
        5,
        45.0,
        -30.0,
        10.0,
        -5.0,
        0.0,
        0.02,
        1.0,
        1.0,
        1.0,
        1.0,
        None,
        None,
        9.81,
        "simple",
        "hamiltonian",
    )

    payload = result["canvas_payload"]
    assert validate_canvas_motion_payload(payload) == []
    assert payload["status"] == "success"
    assert "omega1_deg_per_s" not in payload
    assert "omega2_deg_per_s" not in payload
    assert payload["internal_initial_state_summary"]["state_variable_names"] == [
        "theta1",
        "theta2",
        "p_theta_1",
        "p_theta_2",
    ]


def test_renderer_asset_exists_and_stays_within_task_c_boundaries():
    asset_path = Path("assets/simulation-canvas-renderer.js")
    assert asset_path.exists()

    source = asset_path.read_text(encoding="utf-8")
    assert "DoublePendulumCanvasRenderer" in source
    assert "requestAnimationFrame" in source
    assert CANVAS_MOTION_VIEW_ID in source
    assert CANVAS_TIME_SERIES_VIEW_ID in source
    assert CANVAS_PROJECTION_VIEW_ID in source
    assert PLAY_BUTTON_ID in source
    assert SCRUBBER_ID in source
    assert FRAME_INDICATOR_ID in source
    assert "submit-val" in source
    assert "PLOTLY_FRAME_SAMPLE_STEP" in source
    assert "frameForTime" in source

    lowered = source.lower()
    assert "energy" not in lowered
    assert "chaos" not in lowered
    assert "comparison" not in lowered
    assert "p_theta" not in lowered
    assert "localstorage" not in lowered
    assert "sessionstorage" not in lowered
    assert "fetch(" not in lowered
    assert "xmlhttprequest" not in lowered
