from dash import html

from app.components.footer import get_footer_section
from app.components.shell import get_body_section, get_footer_wrapper, get_header_section
from app.content.chaos import CHAOS_UNDER_DEVELOPMENT_TEXT
from app.content.home import HERO_IMAGE_SRC
from app.content.routes import CHAOS_PAGE


def layout():
    return html.Div(
        className="main-layout chaos-layout",
        children=[
            get_header_section(current_path=CHAOS_PAGE.path),
            get_body_section(
                [
                    html.Section(
                        className="home-hero chaos-hero",
                        style={"backgroundImage": f'url("{HERO_IMAGE_SRC}")'},
                        children=[
                            html.Div(
                                className="chaos-hero-inner",
                                children=[
                                    html.H1(
                                        CHAOS_UNDER_DEVELOPMENT_TEXT,
                                        className="chaos-placeholder-title",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ]
            ),
            get_footer_wrapper(get_footer_section()),
        ],
    )


def get_chaos_layout():
    return layout()
