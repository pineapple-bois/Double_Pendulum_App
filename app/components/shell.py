from dash import html

from app.components.navigation import get_navbar


def get_header_section(current_path):
    return html.Div(
        className="header",
        children=[
            get_navbar(current_path=current_path),
        ],
    )


def get_title_section(text):
    return html.Div(
        className="title-section",
        children=[
            html.H1(text, className="title-text"),
            html.Div(className="title-underline"),
        ],
    )


def get_body_section(children):
    return html.Div(
        className="body",
        children=children,
    )


def get_footer_wrapper(footer_content):
    return html.Div(
        className="footer",
        children=[
            footer_content,
        ],
    )

