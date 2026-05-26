from dash import dcc, html

from app.components.footer import get_footer_section
from app.components.shell import get_footer_wrapper, get_header_section
from app.content.not_found import NOT_FOUND_MESSAGE, NOT_FOUND_TITLE, RETURN_HOME_LABEL
from app.content.routes import HOME_PAGE


def layout():
    return html.Div(
        className="not-found-layout",
        children=[
            get_header_section(current_path=""),
            html.Div(
                className="not-found-content-container",
                children=[
                    html.H1(NOT_FOUND_TITLE, className="custom-text"),
                    html.P(NOT_FOUND_MESSAGE, className="custom-text"),
                    dcc.Link(RETURN_HOME_LABEL, href=HOME_PAGE.path, className="nav-link"),
                ],
            ),
            get_footer_wrapper(get_footer_section()),
        ],
    )


def get_404_layout():
    return layout()

