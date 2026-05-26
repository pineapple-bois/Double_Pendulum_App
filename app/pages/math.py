from dash import dcc, html

from app.components.footer import get_footer_section
from app.components.references import get_references_section
from app.components.shell import get_body_section, get_footer_wrapper, get_header_section, get_title_section
from app.content.math import MATH_PAGES


def build_math_layout(page_content):
    return html.Div(
        id=page_content.scroll_target_id,
        className="math-layout",
        children=[
            get_header_section(current_path=page_content.path),
            get_body_section([
                get_title_section(page_content.title),
                html.Div(
                    className="math-sidebar",
                    children=[
                        html.Div(
                            className="markdown-latex-container",
                            children=[
                                dcc.Markdown(children=page_content.markdown, mathjax=True),
                            ],
                        ),
                    ],
                ),
                get_references_section(page_content.references),
            ]),
            get_footer_wrapper(get_footer_section()),
        ],
    )


def lagrangian_layout():
    return build_math_layout(MATH_PAGES["lagrangian"])


def hamiltonian_layout():
    return build_math_layout(MATH_PAGES["hamiltonian"])


def get_math_layout(page_content):
    return build_math_layout(page_content)


def get_lagrangian_layout():
    return lagrangian_layout()


def get_hamiltonian_layout():
    return hamiltonian_layout()

