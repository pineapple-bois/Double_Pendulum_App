from dash import dcc, html

from app.content.home import (
    ATTRIBUTION_LABEL,
    EXPLORE_LINKS,
    FURTHER_READING,
    GITHUB_LOGO_SRC,
    HERO_IMAGE_SRC,
    HOME_CONTEXT_NOTE,
    HOME_INTRODUCTION,
    HOME_TITLE,
    REPOSITORY_URL,
)


def _explore_link(index, item):
    return dcc.Link(
        className="home-explore-link",
        href=item.href,
        children=[
            html.Span(f"{index}", className="home-explore-number"),
            html.Span(
                className="home-explore-copy",
                children=[
                    html.Span(item.title, className="home-explore-title"),
                    html.Span(item.description, className="home-explore-description"),
                ],
            ),
        ],
    )


def _reading_item(item):
    return html.Li(
        className="home-reading-item",
        children=[
            html.A(
                item.reference,
                href=item.href,
                className="home-reading-title",
                target="_blank",
                rel="noopener noreferrer",
            ),
            html.P(item.role, className="home-reading-role"),
        ],
    )


def _further_reading_section():
    return html.Section(
        className="home-further-reading",
        children=[
            html.H2("Further reading", className="home-further-reading-heading"),
            html.Ul(
                className="home-reading-list",
                children=[_reading_item(item) for item in FURTHER_READING],
            ),
        ],
    )


def _home_attribution():
    return html.A(
        className="home-attribution",
        href=REPOSITORY_URL,
        target="_blank",
        rel="noopener noreferrer",
        children=[
            html.Span(ATTRIBUTION_LABEL, className="home-attribution-label"),
            html.Img(src=GITHUB_LOGO_SRC, className="home-attribution-icon", alt="GitHub"),
        ],
    )


def layout():
    return html.Div(
        className="home-page",
        children=[
            html.Section(
                className="home-hero",
                style={"backgroundImage": f'url("{HERO_IMAGE_SRC}")'},
                children=[
                    html.Div(
                        className="home-hero-inner",
                        children=[
                            html.Div(
                                className="home-copy",
                                children=[
                                    html.H1(HOME_TITLE, className="home-hero-title"),
                                    html.P(HOME_INTRODUCTION, className="home-hero-description"),
                                    html.P(HOME_CONTEXT_NOTE, className="home-hero-note"),
                                ],
                            ),
                            html.Nav(
                                className="home-explore-panel",
                                children=[
                                    html.H2("Explore", className="home-explore-heading"),
                                    *[
                                        _explore_link(index, item)
                                        for index, item in enumerate(EXPLORE_LINKS, start=1)
                                    ],
                                ],
                            ),
                            html.Div(
                                className="home-lower-left",
                                children=[
                                    _further_reading_section(),
                                    _home_attribution(),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
