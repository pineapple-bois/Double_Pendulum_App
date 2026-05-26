from dash import html

from app.components.cards import render_description_paragraph, render_model_card
from app.components.footer import get_footer_section_main
from app.components.graphs import get_animation_phase_section as get_animation_phase_graphs
from app.components.graphs import get_time_graph_section as get_time_graph
from app.components.shell import get_body_section, get_footer_wrapper, get_header_section, get_title_section
from app.components.simulation_controls import build_simulation_controls
from app.content.home import (
    DESCRIPTION_PARAGRAPHS,
    MODEL_CARDS,
    PHASE_PORTRAIT_TITLE,
    TIME_GRAPH_TITLE,
    TRACE_ANIMATION_TITLE,
)
from app.content.routes import HOME_PAGE


def get_description_images_section():
    return html.Div(
        className="description-images-section",
        children=[
            html.Div(
                className="description",
                children=[
                    render_description_paragraph(paragraph)
                    for paragraph in DESCRIPTION_PARAGRAPHS
                ],
            ),
            html.Div(
                className="models-container",
                children=[
                    render_model_card(card) for card in MODEL_CARDS
                ],
            ),
        ],
    )


def get_animation_phase_section():
    return get_animation_phase_graphs(TRACE_ANIMATION_TITLE, PHASE_PORTRAIT_TITLE)


def get_time_graph_section():
    return get_time_graph(TIME_GRAPH_TITLE)


def get_main_content():
    return html.Div(
        className="main-layout",
        children=[
            html.Div(
                id="scroll-target",
                className="content-container",
                children=[
                    build_simulation_controls(),
                    get_animation_phase_section(),
                ],
            ),
            get_time_graph_section(),
        ],
    )


def layout():
    return html.Div(
        className="main-layout",
        children=[
            get_header_section(current_path=HOME_PAGE.path),
            get_body_section([
                get_title_section(HOME_PAGE.title),
                get_description_images_section(),
                get_main_content(),
            ]),
            get_footer_wrapper(get_footer_section_main()),
        ],
    )


def get_main_layout():
    return layout()

