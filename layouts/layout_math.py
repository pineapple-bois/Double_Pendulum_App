# Math page layout
from dash import html
from dash import dcc
from layouts.layout_main_refactor import get_navbar, get_title_section, get_footer_section

# Math derivations
with open('assets/mathematics_lagrangian.txt', 'r') as file:
    lagrangian_section = file.read()

with open('assets/mathematics_hamiltonian.txt', 'r') as file:
    hamiltonian_section = file.read()


def get_lagrangian_layout():
    return html.Div(
        className='math-layout',
        children=[
            get_navbar(),
            get_title_section(),
            html.Div(
                className='markdown-latex-container',
                children=[
                    dcc.Markdown(children=lagrangian_section, mathjax=True)
                ]
            ),
            get_footer_section()
        ]
    )


def get_hamiltonian_layout():
    return html.Div(
        className='math-layout',
        children=[
            get_navbar(),
            get_title_section(),
            html.Div(
                className='markdown-latex-container',
                children=[
                    dcc.Markdown(children=hamiltonian_section, mathjax=True)
                ]
            ),
            get_footer_section()
        ]
    )

