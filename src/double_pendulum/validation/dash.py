from dash import html

from .inputs import validate_input_sections


def validate_inputs(
    initial_conditions_list,
    time_start,
    time_end,
    model_type,
    param_l1,
    param_l2,
    param_m1,
    param_m2,
    param_M1,
    param_M2,
    param_g,
):
    sections = validate_input_sections(
        initial_conditions_list,
        time_start,
        time_end,
        model_type,
        param_l1,
        param_l2,
        param_m1,
        param_m2,
        param_M1,
        param_M2,
        param_g,
    )

    error_list = []
    for section in sections:
        error_list.append(section.title)
        error_list.append(html.Br())
        error_list.extend([html.Div(error) for error in section.messages])
        for _ in range(section.trailing_breaks):
            error_list.append(html.Br())

    return html.Div(error_list) if error_list else None
