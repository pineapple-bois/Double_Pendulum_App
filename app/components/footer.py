from dash import dcc, html

from app.content.simulation import (
    FOOTER_COPYRIGHT,
    FOOTER_PREFIX,
    GITHUB_LOGO_SRC,
    REPOSITORY_LABEL,
    REPOSITORY_URL,
    RUN_SIMULATION_LABEL,
)

SITE_ATTRIBUTION_LABEL = "pineapple-bois"


def github_logo():
    return html.Img(
        src=GITHUB_LOGO_SRC,
        className="info-image",
        style={"width": "30px"},
    )


def get_common_footer(include_button=False, page_type="main"):
    if not include_button:
        return html.Footer(
            className="site-footer",
            children=[
                dcc.Link(
                    children=[
                        html.Span(SITE_ATTRIBUTION_LABEL, className="site-footer-label"),
                        html.Img(
                            src="/assets/Images/github-mark.png",
                            className="site-footer-icon",
                            alt="GitHub",
                        ),
                    ],
                    href=REPOSITORY_URL,
                    target="_blank",
                    className="site-footer-link",
                ),
            ],
        )

    children = []

    if include_button:
        children.append(
            html.Div(
                className="container-buttons run-simulation-group",
                children=[
                    html.Button(
                        RUN_SIMULATION_LABEL,
                        id="submit-val",
                        n_clicks=0,
                        className="button run-simulation-button",
                    ),
                ],
            )
        )

    children.append(
        html.Div(
            className="footer-text-box",
            children=[
                github_logo(),
                html.Div(
                    children=[
                        html.Span(FOOTER_PREFIX, className="info-text"),
                        dcc.Link(
                            REPOSITORY_LABEL,
                            href=REPOSITORY_URL,
                            target="_blank",
                            className="info-link",
                        ),
                        html.Div(FOOTER_COPYRIGHT, className="info-footer"),
                    ],
                ),
            ],
        )
    )

    footer_class = f"footer-bar {page_type}-page"

    return html.Div(
        className=footer_class,
        children=children,
    )


def get_footer_section_main():
    return get_common_footer(include_button=True, page_type="main")


def get_footer_section():
    return get_common_footer(include_button=False, page_type="other")
