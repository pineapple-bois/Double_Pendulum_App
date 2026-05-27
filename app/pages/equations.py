from dash import html

from app.components.derivation import (
    render_branch_card,
    render_derivation_section,
    render_markdown,
    render_model_summary,
)
from app.components.footer import get_footer_section
from app.components.references import get_references_section
from app.components.shell import get_body_section, get_footer_wrapper, get_header_section
from app.content.equations import (
    BRANCH_CARDS,
    DERIVATION_SECTIONS,
    EQUATIONS_REFERENCES,
    INTRODUCTION_PARAGRAPHS,
    MECHANICAL_MODEL_LEAD,
    MODEL_SUMMARIES,
)
from app.content.routes import EQUATIONS_PAGE


def _hero_section():
    return html.Section(
        className="equations-hero",
        children=[
            html.Div(
                className="equations-hero-copy",
                children=[
                    html.P("Classical mechanics derivation", className="equations-eyebrow"),
                    html.H1(EQUATIONS_PAGE.title, className="equations-hero-title"),
                    *[
                        render_markdown(paragraph, "equations-hero-text")
                        for paragraph in INTRODUCTION_PARAGRAPHS
                    ],
                ],
            ),
        ],
    )


def _mechanical_model_section():
    return html.Section(
        className="equations-model-section",
        children=[
            html.Div(
                className="equations-section-heading",
                children=[
                    html.P("Mechanical model", className="equations-eyebrow"),
                    html.H2("What physical system is being modelled?", className="equations-section-title"),
                    html.P(MECHANICAL_MODEL_LEAD, className="equations-section-lead"),
                ],
            ),
            html.Div(
                className="equations-model-grid",
                children=[render_model_summary(card) for card in MODEL_SUMMARIES],
            ),
        ],
    )


def _branching_section():
    return html.Section(
        className="equations-branching",
        children=[
            html.Div(
                className="equations-section-heading",
                children=[
                    html.P("Two routes", className="equations-eyebrow"),
                    html.H2("From one Lagrangian to two formulations", className="equations-section-title"),
                    html.P(
                        (
                            "The derivation shares a single energy trunk before splitting into "
                            "two useful descriptions of the same motion."
                        ),
                        className="equations-section-lead",
                    ),
                ],
            ),
            html.Div(
                className="equations-branch-grid",
                children=[render_branch_card(card) for card in BRANCH_CARDS],
            ),
        ],
    )


def layout():
    return html.Div(
        className="equations-layout",
        children=[
            get_header_section(current_path=EQUATIONS_PAGE.path),
            get_body_section(
                [
                    html.Main(
                        className="equations-page",
                        children=[
                            _hero_section(),
                            _mechanical_model_section(),
                            render_derivation_section(DERIVATION_SECTIONS[0]),
                            _branching_section(),
                            *[
                                render_derivation_section(section)
                                for section in DERIVATION_SECTIONS[1:]
                            ],
                            get_references_section(EQUATIONS_REFERENCES),
                        ],
                    ),
                ]
            ),
            get_footer_wrapper(get_footer_section()),
        ],
    )


def get_equations_layout():
    return layout()
