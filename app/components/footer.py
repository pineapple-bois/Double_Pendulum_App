from dash import dcc, html

from app.content.simulation import REPOSITORY_URL

SITE_ATTRIBUTION_LABEL = "pineapple-bois"


def get_footer_section():
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
