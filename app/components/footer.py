from dash import html

from app.content.simulation import REPOSITORY_URL

SITE_ATTRIBUTION_LABEL = "pineapple-bois 2026"


def get_footer_section():
    return html.Footer(
        className="site-footer",
        children=[
            html.Span(SITE_ATTRIBUTION_LABEL, className="site-footer-label"),
            html.A(
                children=html.Img(
                    src="/assets/Images/github-mark.png",
                    className="site-footer-icon",
                    alt="GitHub",
                ),
                href=REPOSITORY_URL,
                target="_blank",
                rel="noopener noreferrer",
                className="site-footer-link",
                **{"aria-label": "GitHub repository"},
            ),
        ],
    )
