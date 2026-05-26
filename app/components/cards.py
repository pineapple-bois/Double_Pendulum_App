from dash import dcc, html

from app.content.home import LinkCopy, MarkdownCopy


def render_description_part(part):
    if isinstance(part, MarkdownCopy):
        return dcc.Markdown(part.text, mathjax=True, style={"display": "inline"})
    if isinstance(part, LinkCopy):
        return html.A(part.text, href=part.href, className="description-link", target="_blank")
    return part


def render_description_paragraph(parts):
    return html.P(
        [render_description_part(part) for part in parts],
        className="description-text",
    )


def render_model_card(card):
    return html.Div(
        className=card.card_class,
        children=[
            html.Div(
                className="image-description",
                children=[
                    html.H3(card.title, className="model-title"),
                    dcc.Markdown(card.markdown, mathjax=True, className="model-description"),
                ],
            ),
            html.Div(
                className="image-container",
                children=[
                    html.Img(src=card.image_src, className="model-image"),
                ],
            ),
        ],
    )

