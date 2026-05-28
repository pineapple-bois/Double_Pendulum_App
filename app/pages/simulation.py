from dash import html

from app.components.footer import get_footer_section_main
from app.components.graphs import get_animation_phase_section as get_animation_phase_graphs
from app.components.graphs import get_time_graph_section as get_time_graph
from app.components.shell import get_body_section, get_footer_wrapper, get_header_section
from app.components.simulation_controls import build_simulation_controls
from app.content.routes import SIMULATION_PAGE
from app.content.simulation import (
    PHASE_PORTRAIT_TITLE,
    TIME_GRAPH_TITLE,
    TRACE_ANIMATION_TITLE,
)


def get_animation_phase_section():
    return get_animation_phase_graphs(TRACE_ANIMATION_TITLE, PHASE_PORTRAIT_TITLE)


def get_time_graph_section():
    return get_time_graph(TIME_GRAPH_TITLE)


def get_main_content():
    return html.Main(
        id="scroll-target",
        className="simulation-workspace",
        children=[
            html.Div(
                className="simulation-workspace-primary content-container",
                children=[
                    build_simulation_controls(),
                    html.Div(
                        className="simulation-output-workspace",
                        children=[
                            get_animation_phase_section(),
                            get_time_graph_section(),
                        ],
                    ),
                ],
            ),
        ],
    )


def layout():
    return html.Div(
        className="main-layout simulation-layout",
        children=[
            get_header_section(current_path=SIMULATION_PAGE.path),
            get_body_section([
                get_main_content(),
            ]),
            get_footer_wrapper(get_footer_section_main()),
        ],
    )


def get_simulation_layout():
    return layout()
