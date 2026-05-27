from dash import html

from app.components.derivation import (
    render_branch_card,
    render_derivation_section,
    render_markdown,
    render_model_summary,
)
from app.components.footer import get_footer_section
from app.components.shell import get_body_section, get_footer_wrapper, get_header_section
from app.content.equations import (
    BRANCH_CARDS,
    DERIVATION_SECTIONS,
    INTRODUCTION_PARAGRAPHS,
    MECHANICAL_MODEL_LEAD,
    MODEL_SUMMARIES,
)
from app.content.routes import EQUATIONS_PAGE


OVERVIEW_BRANCH = "overview"
EULER_LAGRANGE_BRANCH = "euler_lagrange"
HAMILTONIAN_BRANCH = "hamiltonian"

BRANCH_SECTIONS = {
    EULER_LAGRANGE_BRANCH: DERIVATION_SECTIONS[1],
    HAMILTONIAN_BRANCH: DERIVATION_SECTIONS[2],
}


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


def _branching_section(selected_branch):
    return html.Section(
        id="equations-branch",
        className="equations-branching",
        children=[
            html.Div(
                className="equations-section-heading",
                children=[
                    html.P("Two formulations", className="equations-eyebrow"),
                    html.H2("From one Lagrangian to two formulations", className="equations-section-title"),
                    html.P(
                        (
                            "Choose one formulation to mount below. The shared trunk above remains "
                            "in place, and only the selected branch is added to the page."
                        ),
                        className="equations-section-lead",
                    ),
                ],
            ),
            html.Div(
                className="equations-branch-grid",
                children=[
                    render_branch_card(card, is_active=card.branch_key == selected_branch)
                    for card in BRANCH_CARDS
                ],
            ),
        ],
    )


def _selected_branch_section(selected_branch):
    section = BRANCH_SECTIONS.get(selected_branch)
    if section is None:
        return []
    return [render_derivation_section(section)]


def layout(selected_branch=OVERVIEW_BRANCH):
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
                            _branching_section(selected_branch),
                            html.Div(
                                id="equations-branch-output",
                                className="equations-branch-output",
                                children=_selected_branch_section(selected_branch),
                            ),
                        ],
                    ),
                ]
            ),
            get_footer_wrapper(get_footer_section()),
        ],
    )


def get_equations_layout():
    return layout(OVERVIEW_BRANCH)


def get_euler_lagrange_layout():
    return layout(EULER_LAGRANGE_BRANCH)


def get_hamiltonian_layout():
    return layout(HAMILTONIAN_BRANCH)
