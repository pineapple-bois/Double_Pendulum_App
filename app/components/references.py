from dash import html

from app.content.math import REFERENCES_TITLE


def get_references_section(references):
    reference_links = [
        html.A(href=ref.href, children=ref.text, target="_blank")
        for ref in references
    ]
    return html.Div(
        className="references-section",
        children=[
            html.Div(className="references-line"),
            html.H2(REFERENCES_TITLE, className="references-title"),
            html.Ul([html.Li(link) for link in reference_links]),
        ],
    )

