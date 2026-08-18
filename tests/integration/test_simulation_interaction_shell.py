from pathlib import Path

from dash import dcc, html, no_update

from app.callbacks.simulation import (
    build_input_change_result,
    build_simulation_run_result,
    selected_initial_state_preset_update,
    selected_initial_state_preset_values,
)
from app.components.simulation_controls import (
    INITIAL_STATE_PRESET_APPLY_STORE_ID,
    INITIAL_STATE_PRESET_ID,
    INTEGRATOR_POLICY_DEFAULT,
    INTEGRATOR_POLICY_ID,
    INTEGRATOR_POLICY_OPTIONS,
    RUN_VALIDATION_MESSAGE_ID,
)
from app.components.simulation_interaction import (
    CANVAS_PAYLOAD_STORE_ID,
    CANVAS_MOTION_VIEW_ID,
    CANVAS_PROJECTION_VIEW_ID,
    CANVAS_TIME_SERIES_VIEW_ID,
    CANVAS_WORKSPACE_ID,
    DIAGNOSTICS_CONTENT_ID,
    DIAGNOSTICS_TOGGLE_ID,
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
    SELECTED_STATE_READOUT_ID,
    SOLVER_DIAGNOSTICS_AREA_ID,
    STATUS_MESSAGE_ID,
)
from app.pages.registry import get_layout_for_path
from app.serialization import build_canvas_motion_payload, validate_canvas_motion_payload
from src.double_pendulum.models import SimulationResultState
from tests.helpers import extract_dash_text


CALLBACK_SENSITIVE_IDS = {
    "submit-val",
    RUN_VALIDATION_MESSAGE_ID,
    "scroll-target",
    "model-type",
    "system-type",
    INTEGRATOR_POLICY_ID,
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
    INITIAL_STATE_PRESET_ID,
    INITIAL_STATE_PRESET_APPLY_STORE_ID,
    "time_start",
    "time_end",
    "unity-parameters",
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
    SELECTED_STATE_READOUT_ID,
    DISPLAY_OPTIONS_ID,
    FRAME_INDICATOR_ID,
    CANVAS_MOTION_VIEW_ID,
    CANVAS_TIME_SERIES_VIEW_ID,
    CANVAS_PROJECTION_VIEW_ID,
    RENDERER_SYNC_SIGNAL_ID,
    DIAGNOSTICS_TOGGLE_ID,
    DIAGNOSTICS_CONTENT_ID,
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


def find_by_class(component, target_class):
    stack = [component]
    while stack:
        item = stack.pop()
        if item is None or isinstance(item, (str, int, float)):
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue
        class_name = getattr(item, "className", None)
        if class_name and target_class in str(class_name).split():
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
    classes = collect_class_names(layout)

    assert CALLBACK_SENSITIVE_IDS <= ids
    assert SHELL_IDS <= ids
    assert LEGACY_PLOTLY_OUTPUT_IDS.isdisjoint(ids)
    assert {"info-popup", "info-button", "close-info-button"}.isdisjoint(ids)
    assert "container-buttons" not in classes

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


def test_route_sequence_remounts_simulation_with_fresh_memory_state():
    first_simulation_layout = get_layout_for_path("/simulation")
    equations_layout = get_layout_for_path("/equations")
    second_simulation_layout = get_layout_for_path("/simulation")

    first_ids = collect_ids(first_simulation_layout)
    second_ids = collect_ids(second_simulation_layout)
    assert CALLBACK_SENSITIVE_IDS <= first_ids
    assert CALLBACK_SENSITIVE_IDS <= second_ids
    assert SHELL_IDS <= first_ids
    assert SHELL_IDS <= second_ids
    assert equations_layout is not None
    assert find_by_id(equations_layout, CANVAS_PAYLOAD_STORE_ID) is None

    first_canvas_store = find_by_id(first_simulation_layout, CANVAS_PAYLOAD_STORE_ID)
    second_canvas_store = find_by_id(second_simulation_layout, CANVAS_PAYLOAD_STORE_ID)
    first_result_store = find_by_id(first_simulation_layout, RESULT_STATE_STORE_ID)
    second_result_store = find_by_id(second_simulation_layout, RESULT_STATE_STORE_ID)
    first_integrator_policy = find_by_id(first_simulation_layout, INTEGRATOR_POLICY_ID)
    second_integrator_policy = find_by_id(second_simulation_layout, INTEGRATOR_POLICY_ID)

    assert first_canvas_store is not second_canvas_store
    assert first_canvas_store.data["status"] == "empty"
    assert first_canvas_store.data["run_id"] == 0
    assert second_canvas_store.data["status"] == "empty"
    assert second_canvas_store.data["run_id"] == 0
    assert first_result_store.data["status"] == "empty"
    assert second_result_store.data["status"] == "empty"
    assert first_integrator_policy.value == INTEGRATOR_POLICY_DEFAULT
    assert second_integrator_policy.value == INTEGRATOR_POLICY_DEFAULT


def test_simulation_layout_includes_canvas_targets_and_local_controls():
    layout = get_layout_for_path("/simulation")
    classes = collect_class_names(layout)

    assert isinstance(find_by_id(layout, CANVAS_MOTION_VIEW_ID), html.Canvas)
    assert isinstance(find_by_id(layout, CANVAS_TIME_SERIES_VIEW_ID), html.Canvas)
    assert isinstance(find_by_id(layout, CANVAS_PROJECTION_VIEW_ID), html.Canvas)
    frame_indicator = find_by_id(layout, FRAME_INDICATOR_ID)
    assert frame_indicator is not None
    assert "t =" in text_from(frame_indicator)
    assert "Frame" not in text_from(frame_indicator)
    diagnostics_toggle = find_by_id(layout, DIAGNOSTICS_TOGGLE_ID)
    assert isinstance(diagnostics_toggle, html.Div)
    assert "simulation-hidden-runtime-targets" in diagnostics_toggle.className
    assert "Show diagnostics" not in text_from(diagnostics_toggle)
    diagnostics_content = find_by_id(layout, DIAGNOSTICS_CONTENT_ID)
    assert diagnostics_content is not None
    assert find_by_id(diagnostics_content, SELECTED_STATE_READOUT_ID) is not None
    playback_strip = find_by_class(layout, "simulation-playback-strip")
    run_dock = find_by_class(layout, "simulation-run-dock")
    hidden_runtime_targets = find_by_class(run_dock, "simulation-hidden-runtime-targets")
    assert find_by_id(playback_strip, DIAGNOSTICS_TOGGLE_ID) is None
    assert find_by_id(playback_strip, DIAGNOSTICS_CONTENT_ID) is None
    assert find_by_id(playback_strip, STATUS_MESSAGE_ID) is None
    assert find_by_id(run_dock, DIAGNOSTICS_TOGGLE_ID) is diagnostics_toggle
    assert find_by_id(run_dock, DIAGNOSTICS_CONTENT_ID) is diagnostics_content
    assert hidden_runtime_targets is not None
    assert find_by_id(hidden_runtime_targets, STATUS_MESSAGE_ID) is not None
    assert "Show diagnostics" not in text_from(run_dock)
    assert "Run and inspect the simulation" not in text_from(playback_strip)
    assert "Choose the system configuration" not in text_from(playback_strip)
    assert "Use playback, guide toggles, and the time slider" not in text_from(playback_strip)
    assert {
        "canvas-panel-motion",
        "canvas-panel-projection",
        "canvas-panel-time",
        "simulation-control-centre",
        "simulation-control-centre-title",
        "simulation-playback-strip",
        "simulation-playback-header",
        "playback-panel-controls-row",
        "canvas-time-selector",
        "playback-control-row",
        "playback-header-controls",
        "playback-header-display",
        "selected-state-diagnostics-area",
        "simulation-diagnostics-toggle",
        "simulation-detail-diagnostics",
        "simulation-hidden-runtime-targets",
        "initial-state-input-grid",
        "initial-state-input-column",
        "initial-state-heading-row",
        "initial-state-help",
        "initial-state-help-summary",
        "initial-state-help-panel",
        "initial-state-preset-hidden",
        "binary-choice",
        "model-system-choice",
        "system-type-choice",
        "quiet-gravity-dropdown",
        "integrator-policy-hidden",
        "simulation-config-column",
        "simulation-config-system-column",
        "simulation-config-state-column",
        "simulation-run-dock",
        "parameter-stepper",
        "parameter-stepper-button",
        "parameter-stepper-input",
    } <= classes
    assert "init-cond-split" not in classes
    assert "initial-state-slider-stack" not in classes
    assert "initial-state-slider-section" not in classes
    assert "simulation-output-control-layout" not in classes
    assert "time-cap-copy" not in classes

    scrubber = find_by_id(layout, SCRUBBER_ID)
    display_options = find_by_id(layout, DISPLAY_OPTIONS_ID)
    time_selector = find_by_class(layout, "canvas-time-selector")
    control_centre = find_by_class(layout, "simulation-control-centre")
    playback_display = find_by_class(layout, "playback-header-display")
    system_column = find_by_class(layout, "simulation-config-system-column")
    state_column = find_by_class(layout, "simulation-config-state-column")
    initial_state_grid = find_by_class(layout, "initial-state-input-grid")
    initial_state_help = find_by_class(layout, "initial-state-help")
    initial_state_preset_hidden = find_by_class(layout, "initial-state-preset-hidden")
    initial_state_preset = find_by_id(layout, INITIAL_STATE_PRESET_ID)
    angle_column = find_by_class(layout, "angle-input-column")
    velocity_column = find_by_class(layout, "velocity-input-column")
    theta1_input = find_by_id(layout, "init_cond_theta1")
    theta2_input = find_by_id(layout, "init_cond_theta2")
    omega1_input = find_by_id(layout, "init_cond_omega1")
    omega2_input = find_by_id(layout, "init_cond_omega2")
    model_type = find_by_id(layout, "model-type")
    system_type = find_by_id(layout, "system-type")
    integrator_policy = find_by_id(layout, INTEGRATOR_POLICY_ID)
    param_l1 = find_by_id(layout, "param_l1")
    param_l2 = find_by_id(layout, "param_l2")
    param_m1 = find_by_id(layout, "param_m1")
    param_m2 = find_by_id(layout, "param_m2")
    param_M1 = find_by_id(layout, "param_M1")
    param_M2 = find_by_id(layout, "param_M2")
    param_m1_control = find_by_id(layout, "param_m1-control")
    param_M1_control = find_by_id(layout, "param_M1-control")
    time_start_input = find_by_id(layout, "time_start")
    time_end_slider = find_by_id(layout, "time_end")
    run_validation = find_by_id(layout, RUN_VALIDATION_MESSAGE_ID)
    preset_apply_store = find_by_id(layout, INITIAL_STATE_PRESET_APPLY_STORE_ID)

    assert isinstance(scrubber, dcc.Input)
    assert scrubber.type == "range"
    assert scrubber.disabled is True
    assert isinstance(preset_apply_store, dcc.Store)
    assert preset_apply_store.storage_type == "memory"
    assert find_by_id(system_column, "model-type") is model_type
    assert find_by_id(system_column, "param_l1") is param_l1
    assert find_by_id(state_column, "init_cond_theta1") is theta1_input
    assert find_by_id(state_column, "time_end") is time_end_slider
    assert find_by_id(system_column, "init_cond_theta1") is None
    assert find_by_id(state_column, "param_l1") is None
    assert find_by_id(time_selector, SCRUBBER_ID) is not None
    assert "Control Centre" in text_from(control_centre)
    assert find_by_class(control_centre, "simulation-playback-strip") is playback_strip
    assert find_by_class(control_centre, "canvas-time-selector") is time_selector
    assert find_by_id(playback_display, DISPLAY_OPTIONS_ID) is not None
    assert find_by_id(playback_strip, FRAME_INDICATOR_ID) is not None
    assert isinstance(initial_state_help, html.Details)
    assert initial_state_help.open is False
    assert "The four initial state values define the starting configuration." in text_from(initial_state_help)
    assert "Positive angles rotate counterclockwise" in text_from(initial_state_help)
    assert "Example state" not in text_from(find_by_class(layout, "initial-conditions-group"))
    assert "Choose a preset" not in text_from(find_by_class(layout, "initial-conditions-group"))
    assert find_by_id(initial_state_preset_hidden, INITIAL_STATE_PRESET_ID) is initial_state_preset
    assert isinstance(initial_state_preset, dcc.Dropdown)
    assert initial_state_preset.clearable is True
    assert initial_state_preset.searchable is False
    assert {option["value"] for option in initial_state_preset.options} == {
        "simple-start",
        "quasi-periodic",
        "wide-swing",
        "spirograph-like",
    }
    assert getattr(initial_state_grid, "children", None) == [angle_column, velocity_column]
    assert find_by_id(angle_column, "init_cond_theta1") is not None
    assert find_by_id(angle_column, "init_cond_theta2") is not None
    assert find_by_id(velocity_column, "init_cond_omega1") is not None
    assert find_by_id(velocity_column, "init_cond_omega2") is not None
    assert isinstance(model_type, dcc.RadioItems)
    assert {option["value"] for option in model_type.options} == {"simple", "compound"}
    assert model_type.labelClassName == "system-button"
    assert model_type.inputClassName == "system-button-input"
    assert isinstance(system_type, dcc.RadioItems)
    assert {option["value"] for option in system_type.options} == {"lagrangian", "hamiltonian"}
    assert {option["label"] for option in system_type.options} == {"Euler-Lagrange", "Hamiltonian"}
    assert system_type.labelClassName == "system-button"
    assert system_type.inputClassName == "system-button-input"
    assert isinstance(integrator_policy, dcc.Dropdown)
    assert integrator_policy.value == INTEGRATOR_POLICY_DEFAULT
    assert integrator_policy.clearable is False
    assert integrator_policy.searchable is False
    assert integrator_policy.options == list(INTEGRATOR_POLICY_OPTIONS)
    assert {option["value"] for option in integrator_policy.options} == {
        "simple_default",
        "simple_reference",
        "solve_ivp_default_baseline",
    }
    assert "Integrator policy" not in text_from(find_by_class(layout, "model-system-group"))
    assert "System" not in text_from(find_by_class(layout, "model-system-group"))
    assert "Gravity" not in text_from(find_by_class(layout, "model-system-group"))
    assert param_m1_control.style is None
    assert param_M1_control.style == {"display": "none"}
    assert find_by_id(layout, "param_l1-decrement") is not None
    assert find_by_id(layout, "param_l1-increment") is not None
    assert find_by_id(layout, "param_m1-decrement") is not None
    assert find_by_id(layout, "param_m1-increment") is not None
    expected_placeholders = (
        (param_l1, "Length 1"),
        (param_l2, "Length 2"),
        (param_m1, "Mass 1"),
        (param_m2, "Mass 2"),
        (param_M1, "Mass 1"),
        (param_M2, "Mass 2"),
    )
    for parameter_input, placeholder in expected_placeholders:
        assert isinstance(parameter_input, dcc.Input)
        assert parameter_input.type == "text"
        assert parameter_input.inputMode == "numeric"
        assert parameter_input.readOnly is True
        assert parameter_input.placeholder == placeholder
        assert parameter_input.min == 1
        assert parameter_input.max == 10
        assert parameter_input.step == 1
    assert isinstance(theta1_input, dcc.Input)
    assert theta1_input.type == "number"
    assert theta1_input.min == -180
    assert theta1_input.max == 180
    assert theta1_input.step == 1
    assert theta1_input.value == 0
    assert isinstance(theta2_input, dcc.Input)
    assert theta2_input.type == "number"
    assert theta2_input.min == -180
    assert theta2_input.max == 180
    assert theta2_input.step == 1
    assert isinstance(omega1_input, dcc.Input)
    assert omega1_input.type == "number"
    assert omega1_input.min == -1000
    assert omega1_input.max == 1000
    assert omega1_input.step == 1
    assert omega1_input.value == 0
    assert isinstance(omega2_input, dcc.Input)
    assert omega2_input.type == "number"
    assert omega2_input.min == -1000
    assert omega2_input.max == 1000
    assert isinstance(time_start_input, dcc.Input)
    assert time_start_input.value == 0
    assert time_start_input.style == {"display": "none"}
    assert isinstance(time_end_slider, dcc.Slider)
    assert time_end_slider.min == 1
    assert time_end_slider.max == 60
    assert time_end_slider.step == 1
    assert time_end_slider.value == 20
    assert set(time_end_slider.marks) == {10, 20, 30, 40, 50, 60}
    assert run_validation is not None
    assert "Ready" in text_from(run_validation)
    assert isinstance(display_options, dcc.Checklist)
    assert display_options.value == ["axes", "grid"]
    assert {option["value"] for option in display_options.options} == {"axes", "grid"}
    assert all(option["disabled"] is True for option in display_options.options)


def test_initial_state_preset_values_update_only_initial_conditions():
    assert selected_initial_state_preset_values("simple-start") == (0, 60, 0, 0)
    assert selected_initial_state_preset_values("quasi-periodic") == (45, 45, 0, 0)
    assert selected_initial_state_preset_values("wide-swing") == (0, 120, 0, 0)
    assert selected_initial_state_preset_values("spirograph-like") == (90, 0, 572.95, -458.37)

    cleared = selected_initial_state_preset_values(None)
    assert all(value is no_update for value in cleared)

    assert selected_initial_state_preset_update("wide-swing") == (
        0,
        120,
        0,
        0,
        {"preset": "wide-swing", "values": [0, 120, 0, 0]},
    )
    cleared_update = selected_initial_state_preset_update(None)
    assert all(value is no_update for value in cleared_update)


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
    assert RUN_VALIDATION_MESSAGE_ID in output_ids
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
    assert result["result_state"]["failure_reason"] is None
    assert result["result_state"]["render_safe"] is True
    assert "simulation-run-validation-success" in result["run_validation_className"]
    assert "Success" in text_from(result["run_validation_children"])
    assert "animation_phase_children" not in result
    assert "time_graph_children" not in result
    assert "animation_phase_style" not in result

    summary_text = text_from(result["run_summary_children"])
    diagnostics_text = text_from(result["solver_diagnostics_children"])
    assert "State: success" in summary_text
    assert payload["solver_metadata"]["policy_name"] == "simple_default"
    assert payload["solver_metadata"]["method"] == "DOP853"
    assert payload["solver_metadata"]["rtol"] == 1e-6
    assert payload["solver_metadata"]["atol"] == 1e-8
    assert "Policy: simple_default" in diagnostics_text
    assert "Integrator: solve_ivp" in diagnostics_text
    assert "Method: DOP853" in diagnostics_text
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
    assert payload["failure_reason"] == SimulationResultState.VALIDATION_ERROR.value
    assert payload["rendering"]["drawable"] is False
    assert result["result_state"]["status"] == "failed"
    assert result["result_state"]["failure_reason"] == SimulationResultState.VALIDATION_ERROR.value
    assert result["result_state"]["render_safe"] is False
    assert "simulation-run-validation-invalid" in result["run_validation_className"]
    assert "requires a numerical value" in text_from(result["run_validation_children"])
    diagnostics_text = text_from(result["solver_diagnostics_children"])
    assert "Solver was not run for this state." in diagnostics_text
    assert "Policy:" not in diagnostics_text
    assert "Payload validation passed." not in diagnostics_text
    assert result["playback_state"]["playback_state"] == "cancelled"
    assert "time_s" not in payload
    assert "theta1_deg" not in payload


def test_simple_policy_selector_values_are_reflected_in_solver_metadata():
    expected = {
        "simple_default": ("simple_default", "DOP853", 1e-6, 1e-8),
        "simple_reference": ("simple_reference", "DOP853", 1e-9, 1e-11),
        "solve_ivp_default_baseline": ("solve_ivp_default_baseline", None, None, None),
        "unknown-policy": ("simple_default", "DOP853", 1e-6, 1e-8),
        None: ("simple_default", "DOP853", 1e-6, 1e-8),
    }

    for selected_value, (policy_name, method, rtol, atol) in expected.items():
        result = build_simulation_run_result(
            11,
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
            integrator_policy_value=selected_value,
        )
        metadata = result["canvas_payload"]["solver_metadata"]
        assert result["canvas_payload"]["status"] == "success"
        assert metadata["policy_name"] == policy_name
        assert metadata["method"] == method
        assert metadata["rtol"] == rtol
        assert metadata["atol"] == atol


def test_simple_hamiltonian_receives_selected_integrator_policy():
    result = build_simulation_run_result(
        12,
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
        "hamiltonian",
        integrator_policy_value="simple_reference",
    )

    metadata = result["canvas_payload"]["solver_metadata"]
    assert result["canvas_payload"]["status"] == "success"
    assert metadata["policy_name"] == "simple_reference"
    assert metadata["method"] == "DOP853"
    assert metadata["rtol"] == 1e-9
    assert metadata["atol"] == 1e-11


def test_compound_runs_do_not_claim_simple_solver_policy_validation():
    result = build_simulation_run_result(
        13,
        10.0,
        20.0,
        0.0,
        0.0,
        0.0,
        0.02,
        1.0,
        1.0,
        None,
        None,
        1.0,
        1.0,
        9.81,
        "compound",
        "lagrangian",
        integrator_policy_value="simple_reference",
    )

    metadata = result["canvas_payload"]["solver_metadata"]
    assert result["canvas_payload"]["status"] == "success"
    assert metadata["policy_name"] is None
    assert metadata["method"] is None
    assert metadata["rtol"] is None
    assert metadata["atol"] is None


def test_solver_failure_stores_failed_non_drawable_payload(monkeypatch):
    class FailedSolverMetadata:
        def __init__(self, solver_policy):
            self.policy_name = solver_policy.name
            self.method = solver_policy.method
            self.rtol = solver_policy.rtol
            self.atol = solver_policy.atol

        success = False
        message = "forced callback solver failure"

        def to_dict(self):
            return {
                "policy_name": self.policy_name,
                "integrator": "solve_ivp",
                "method": self.method,
                "rtol": self.rtol,
                "atol": self.atol,
                "success": False,
                "status": -1,
                "message": self.message,
                "nfev": 7,
                "njev": 0,
                "nlu": 0,
                "requested_time_count": 4,
                "returned_time_count": 2,
                "requested_time_start": 0.0,
                "requested_time_end": 0.02,
                "returned_time_start": 0.0,
                "returned_time_end": 0.01,
                "returned_time_matches_requested": False,
                "solution_shape": [2, 4],
                "solver_kwargs": {"method": "'DOP853'", "rtol": "1e-06", "atol": "1e-08"},
            }

    class FailedPendulum:
        def __init__(self, *args, **kwargs):
            self.solver_metadata = FailedSolverMetadata(kwargs["solver_policy"])

    monkeypatch.setattr("app.callbacks.simulation.DoublePendulumLagrangian", FailedPendulum)

    result = build_simulation_run_result(
        22,
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
        integrator_policy_value="solve_ivp_default_baseline",
    )

    payload = result["canvas_payload"]
    assert validate_canvas_motion_payload(payload) == []
    assert payload["status"] == "failed"
    assert payload["failure_reason"] == SimulationResultState.SOLVER_FAILURE.value
    assert payload["rendering"]["drawable"] is False
    assert payload["solver_metadata"]["policy_name"] == "solve_ivp_default_baseline"
    assert payload["solver_metadata"]["method"] is None
    assert payload["solver_metadata"]["success"] is False
    assert payload["solver_metadata"]["message"] == "forced callback solver failure"
    assert result["result_state"]["status"] == "failed"
    assert result["result_state"]["failure_reason"] == SimulationResultState.SOLVER_FAILURE.value
    assert result["result_state"]["render_safe"] is False
    assert "simulation-run-validation-failed" in result["run_validation_className"]
    diagnostics_text = text_from(result["solver_diagnostics_children"])
    assert "Policy: solve_ivp_default_baseline" in diagnostics_text
    assert "Solver success: False" in diagnostics_text
    assert "Policy: simple_default" not in diagnostics_text
    assert "Payload validation passed." not in diagnostics_text
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
    assert "simulation-run-validation-stale" in stale_result["run_validation_className"]
    assert "Stale inputs" in text_from(stale_result["run_validation_children"])
    assert stale_result["playback_state"]["playback_state"] == "cancelled"
    assert "Settings changed" in text_from(stale_result["status_children"])
    diagnostics_text = text_from(stale_result["solver_diagnostics_children"])
    assert "Diagnostics are stale and describe the previous successful run." in diagnostics_text
    assert "Rerun to refresh solver metadata for the current controls." in diagnostics_text
    assert "Policy: simple_default" in diagnostics_text
    assert "Previous payload validation passed before inputs changed." in diagnostics_text
    assert "Payload validation passed." not in diagnostics_text


def test_integrator_policy_change_marks_diagnostics_stale_until_rerun():
    success_result = build_simulation_run_result(
        6,
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
        integrator_policy_value="simple_default",
    )
    stale_result = build_input_change_result(
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
        success_result["canvas_payload"],
        integrator_policy_value="simple_reference",
        current_playback_state=success_result["playback_state"],
    )
    rerun_result = build_simulation_run_result(
        7,
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
        integrator_policy_value="simple_reference",
    )

    stale_diagnostics = text_from(stale_result["solver_diagnostics_children"])
    rerun_diagnostics = text_from(rerun_result["solver_diagnostics_children"])
    assert stale_result["canvas_payload"]["status"] == "stale"
    assert "Diagnostics are stale" in stale_diagnostics
    assert "Policy: simple_default" in stale_diagnostics
    assert "Policy: simple_reference" not in stale_diagnostics
    assert rerun_result["canvas_payload"]["status"] == "success"
    assert "Diagnostics are stale" not in rerun_diagnostics
    assert "Policy: simple_reference" in rerun_diagnostics
    assert "Policy: simple_default" not in rerun_diagnostics


def test_validation_error_after_success_does_not_reuse_success_diagnostics():
    success_result = build_simulation_run_result(
        8,
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
        integrator_policy_value="simple_reference",
    )
    invalid_result = build_input_change_result(
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
        success_result["canvas_payload"],
        integrator_policy_value="simple_reference",
        current_playback_state=success_result["playback_state"],
    )

    diagnostics_text = text_from(invalid_result["solver_diagnostics_children"])
    assert invalid_result["canvas_payload"]["status"] == "failed"
    assert invalid_result["result_state"]["render_safe"] is False
    assert "Solver was not run for this state." in diagnostics_text
    assert "Policy: simple_reference" not in diagnostics_text
    assert "Payload validation passed." not in diagnostics_text


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
    assert "function resetRouteScopedState()" in source
    assert "rendererState.minimumRunId = 0" in source
    assert "rendererState.boundShell !== shell" in source
    assert INTEGRATOR_POLICY_ID in source
    assert CANVAS_MOTION_VIEW_ID in source
    assert CANVAS_TIME_SERIES_VIEW_ID in source
    assert CANVAS_PROJECTION_VIEW_ID in source
    assert PLAY_BUTTON_ID in source
    assert SCRUBBER_ID in source
    assert FRAME_INDICATOR_ID in source
    assert "submit-val" in source
    assert "PLOTLY_FRAME_SAMPLE_STEP" in source
    assert "frameForTime" in source
    assert "squarePlotArea" in source
    assert "motionMapper" in source
    assert "drawMotionTrace" in source
    assert "drawPlotTickLabels" in source
    assert "θ₁ (deg)" in source
    assert "θ₂ (deg)" in source
    assert "t = \" + currentTime" in source
    assert "formatNumber(payload.time_s[frame], 1)" in source
    assert "formatNumber(payload.time_s[payload.sample_count - 1], 1)" in source
    assert "PALETTE" in source

    lowered = source.lower()
    assert "energy" not in lowered
    assert "chaos" not in lowered
    assert "comparison" not in lowered
    assert "p_theta" not in lowered
    assert "localstorage" not in lowered
    assert "sessionstorage" not in lowered
    assert "fetch(" not in lowered
    assert "xmlhttprequest" not in lowered


def test_route_clientside_callback_guards_renderer_and_scroll_globals():
    source = Path("app/callbacks/routing.py").read_text(encoding="utf-8")

    assert "typeof initializeHomePage === 'function'" in source
    assert "window.DoublePendulumCanvasRenderer" in source
    assert "typeof window.DoublePendulumCanvasRenderer.init === 'function'" in source
