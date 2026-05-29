from dash import html

from app.components.footer import get_footer_section
from app.components.shell import get_body_section, get_footer_wrapper, get_header_section
from app.components.simulation_interaction import build_simulation_interaction_shell
from app.components.simulation_controls import build_simulation_controls
from app.content.routes import SIMULATION_PAGE


def get_main_content():
    return html.Main(
        id="scroll-target",
        className="simulation-workspace",
        children=[
            html.Div(
                className="simulation-workspace-primary content-container",
                children=[
                    build_simulation_controls(),
                    html.Div(
                        className="simulation-output-workspace",
                        children=[
                            build_simulation_interaction_shell(),
                        ],
                    ),
                ],
            ),
        ],
    )


def layout():
    return html.Div(
        className="main-layout simulation-layout",
        children=[
            get_header_section(current_path=SIMULATION_PAGE.path),
            get_body_section([
                get_main_content(),
            ]),
            get_footer_wrapper(get_footer_section()),
        ],
    )


def get_simulation_layout():
    return layout()
