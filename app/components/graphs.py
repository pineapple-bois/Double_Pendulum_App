from dash import dcc, html


GRAPH_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["select2d", "lasso2d"]}


def _graph_instance_id(graph_id, instance_id=None):
    if instance_id is None:
        return graph_id
    return f"{graph_id}-{instance_id}"


def get_graph_wrapper(title, graph_id, config=None, responsive=False, figure=None, instance_id=None):
    graph_kwargs = {
        "id": _graph_instance_id(graph_id, instance_id),
        "className": "responsive-graph",
    }
    if config is not None:
        graph_kwargs["config"] = config
    if responsive:
        graph_kwargs["responsive"] = True
    if figure is not None:
        graph_kwargs["figure"] = figure

    return html.Div(
        className="graph-wrapper",
        children=[
            html.Div(title, className="graph-title"),
            dcc.Graph(**graph_kwargs),
        ],
    )


def get_animation_phase_children(trace_title, phase_title, animation_figure=None, phase_figure=None, instance_id=None):
    return [
        get_graph_wrapper(
            trace_title,
            "pendulum-animation",
            config=GRAPH_CONFIG,
            figure=animation_figure,
            instance_id=instance_id,
        ),
        get_graph_wrapper(
            phase_title,
            "phase-graph",
            config=GRAPH_CONFIG,
            figure=phase_figure,
            instance_id=instance_id,
        ),
    ]


def get_animation_phase_section(trace_title, phase_title):
    return html.Div(
        className="graph-section",
        children=[
            dcc.Loading(
                id="loading-animation-phase",
                type="cube",
                children=[
                    html.Div(
                        id="animation-phase-container",
                        className="above-graph-container",
                        style={"display": "none"},
                        children=get_animation_phase_children(trace_title, phase_title),
                    ),
                    html.Div(id="error-message", className="error-message"),
                ],
                className="delayed-spinner",
            ),
        ],
    )


def get_time_graph_children(title, figure=None, instance_id=None):
    graph_kwargs = {
        "id": _graph_instance_id("time-graph", instance_id),
        "className": "responsive-graph",
        "responsive": True,
    }
    if figure is not None:
        graph_kwargs["figure"] = figure
    return [
        html.Div(title, className="graph-title"),
        dcc.Graph(**graph_kwargs),
    ]


def get_time_graph_section(title):
    return html.Div(
        id="time-graph-section",
        className="time-graph-section",
        children=[
            html.Div(
                id="time-graph-container",
                className="graph-container",
                children=get_time_graph_children(title),
                style={"display": "none"},
            )
        ],
        style={"display": "none"},
    )
