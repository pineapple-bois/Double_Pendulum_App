from dash import dcc, html


GRAPH_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["select2d", "lasso2d"]}


def get_graph_wrapper(title, graph_id, config=None, responsive=False):
    graph_kwargs = {
        "id": graph_id,
        "className": "responsive-graph",
    }
    if config is not None:
        graph_kwargs["config"] = config
    if responsive:
        graph_kwargs["responsive"] = True

    return html.Div(
        className="graph-wrapper",
        children=[
            html.Div(title, className="graph-title"),
            dcc.Graph(**graph_kwargs),
        ],
    )


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
                        children=[
                            get_graph_wrapper(trace_title, "pendulum-animation", config=GRAPH_CONFIG),
                            get_graph_wrapper(phase_title, "phase-graph", config=GRAPH_CONFIG),
                        ],
                    ),
                    html.Div(id="error-message", className="error-message"),
                ],
                className="delayed-spinner",
            ),
        ],
    )


def get_time_graph_section(title):
    return html.Div(
        id="time-graph-section",
        className="time-graph-section",
        children=[
            html.Div(
                id="time-graph-container",
                className="graph-container",
                children=[
                    html.Div(title, className="graph-title"),
                    dcc.Graph(id="time-graph", className="responsive-graph", responsive=True),
                ],
                style={"display": "none"},
            )
        ],
        style={"display": "none"},
    )

