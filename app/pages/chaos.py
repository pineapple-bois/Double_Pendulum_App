from dash import html

from app.components.footer import get_footer_section
from app.components.shell import get_footer_wrapper, get_header_section, get_title_section
from app.content.chaos import CHAOS_PAGE_TITLE, CHAOS_UNDER_DEVELOPMENT_TEXT
from app.content.routes import CHAOS_PAGE


def layout():
    return html.Div(
        className="chaos-layout",
        children=[
            get_header_section(current_path=CHAOS_PAGE.path),
            get_title_section(CHAOS_PAGE_TITLE),
            html.Div(
                className="chaos-content-container",
                children=[
                    html.H3(CHAOS_UNDER_DEVELOPMENT_TEXT, className="chaos-text"),
                ],
            ),
            get_footer_wrapper(get_footer_section()),
        ],
    )


def get_chaos_layout():
    return layout()

