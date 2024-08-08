# Math page layout
from dash import html
from dash import dcc
from layouts.layout_main import get_navbar, get_footer_section

# Math derivations
with open('assets/mathematics_lagrangian.txt', 'r') as file:
    lagrangian_section = file.read()

with open('assets/mathematics_hamiltonian.txt', 'r') as file:
    hamiltonian_section = file.read()


def get_lagrangian_layout():
    return html.Div(
        className='math-layout',
        children=[
            html.Div(
                className='header',
                children=[
                    get_navbar(),
                ]
            ),
            html.Div(
                className='body',
                children=[
                    html.Div(
                        className='markdown-latex-container',
                        children=[
                            dcc.Markdown(children=lagrangian_section, mathjax=True)
                        ]
                    ),
                ]
            ),
            html.Div(
                className='footer',
                children=[
                    get_footer_section()
                ]
            ),
        ]
    )


def get_hamiltonian_layout():
    return html.Div(
        className='math-layout',
        children=[
            html.Div(
                className='header',
                children=[
                    get_navbar(),
                ]
            ),
            html.Div(
                className='body',
                children=[
                    html.Div(
                        className='markdown-latex-container',
                        children=[
                            dcc.Markdown(children=hamiltonian_section, mathjax=True)
                        ]
                    ),
                ]
            ),
            html.Div(
                className='footer',
                children=[
                    get_footer_section()
                ]
            ),
        ]
    )
