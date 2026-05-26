from dash import dcc, html

from app.content.home import HERO_IMAGE_SRC
from app.content.not_found import (
    NOT_FOUND_HAIKU_LINES,
    RETURN_HOME_LABEL,
    RETURN_SIMULATION_LABEL,
)
from app.content.routes import HOME_PAGE, SIMULATION_PAGE


def layout():
    return html.Div(
        className="not-found-page",
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
                                    html.Div(
                                        className="not-found-haiku",
                                        children=[
                                            html.P(line, className="not-found-haiku-line")
                                            for line in NOT_FOUND_HAIKU_LINES
                                        ],
                                    ),
                                    html.Div(
                                        className="not-found-actions",
                                        children=[
                                            dcc.Link(
                                                RETURN_HOME_LABEL,
                                                href=HOME_PAGE.path,
                                                className="not-found-link not-found-link-primary",
                                            ),
                                            dcc.Link(
                                                RETURN_SIMULATION_LABEL,
                                                href=SIMULATION_PAGE.path,
                                                className="not-found-link",
                                            ),
                                        ],
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
