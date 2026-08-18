from dash import dcc, html

from app.content.home import HERO_IMAGE_SRC
from app.content.not_found import (
    NOT_FOUND_HAIKU_LINES,
    NOT_FOUND_TITLE,
    RETURN_HOME_LABEL,
)
from app.content.routes import HOME_PAGE


def _message_children():
    children = [NOT_FOUND_TITLE]
    for line in NOT_FOUND_HAIKU_LINES:
        children.extend([html.Br(), line])
    return children


def layout():
    return html.Div(
        className="home-page not-found-page",
        children=[
            html.Section(
                className="home-hero not-found-hero",
                style={"backgroundImage": f'url("{HERO_IMAGE_SRC}")'},
                children=[
                    html.Div(
                        className="home-hero-inner not-found-hero-inner",
                        children=[
                            html.Div(
                                className="not-found-panel",
                                children=[
                                    html.H1(
                                        className="not-found-message",
                                        children=_message_children(),
                                    ),
                                    dcc.Link(
                                        RETURN_HOME_LABEL,
                                        href=HOME_PAGE.path,
                                        className="not-found-home-link",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def get_404_layout():
    return layout()
