# Math page layout
from dash import html
from dash import dcc
from layouts.layout_main import get_navbar, get_title_section, get_footer_section

# Math derivations
with open('assets/MarkdownScripts/mathematics_lagrangian.txt', 'r') as file:
    lagrangian_section = file.read()

with open('assets/MarkdownScripts/mathematics_hamiltonian.txt', 'r') as file:
    hamiltonian_section = file.read()

# References
lagrangian_references = [
    {'text': 'Massachusetts Institute of Technology: myPhysicsLab Double Pendulum',
     'href': 'https://web.mit.edu/jorloff/www/chaosTalk/double-pendulum/double-pendulum-en.html'},
    {'text': 'Double pendulum: Lagrangian formulation - Diego Assencio', 'href': 'https://dassencio.org/33'},
    {'text': 'Lagrangian Mechanics - Wikipedia', 'href': 'https://en.wikipedia.org/wiki/Lagrangian_mechanics'}
]

hamiltonian_references = [
    {'text': 'Massachusetts Institute of Technology: myPhysicsLab Double Pendulum',
     'href': 'https://web.mit.edu/jorloff/www/chaosTalk/double-pendulum/double-pendulum-en.html'},
    {'text': 'Double pendulum: Hamiltonian formulation - Diego Assencio', 'href': 'https://dassencio.org/46'},
    {'text': 'Prof. D. Garanin, City University of New York Graduate Centre: Exercises in Classical Mechanics 1, Hamiltonian formalism',
     'href': 'https://www.lehman.edu/faculty/dgaranin/Mechanics/ProblemSet-Fall-2006-4-Solution.pdf'},
    {'text': 'Hamiltonian Mechanics - Wikipedia', 'href': 'https://en.wikipedia.org/wiki/Hamiltonian_mechanics'}
]


def get_references_section(references):
    reference_links = [html.A(href=ref['href'], children=ref['text'], target='_blank') for ref in references]
    return html.Div(
        className='references-section',
        children=[
            html.Div(className="references-line"),
            html.H2('References', className='references-title'),
            html.Ul([html.Li(link) for link in reference_links])
        ]
    )


def get_lagrangian_layout():
    return html.Div(
        id="lagrangian-scroll-target",
        className='math-layout',
        children=[
            html.Div(
                className='header',
                children=[
                    get_navbar(current_path="/lagrangian"),
                ]
            ),
            html.Div(

                className='body',
                children=[
                    get_title_section("Lagrangian Derivation"),
                    html.Div(
                        className='math-sidebar',
                        children=[
                            html.Div(
                                className='markdown-latex-container',
                                children=[
                                    dcc.Markdown(children=lagrangian_section, mathjax=True)
                                ]
                            ),
                        ]
                    ),
                    get_references_section(lagrangian_references)
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
        id="hamiltonian-scroll-target",
        className='math-layout',
        children=[
            html.Div(
                className='header',
                children=[
                    get_navbar(current_path="/hamiltonian"),
                ]
            ),
            html.Div(
                className='body',
                children=[
                    get_title_section("Hamiltonian Derivation"),
                    html.Div(
                        className='math-sidebar',
                        children=[
                            html.Div(
                                className='markdown-latex-container',
                                children=[
                                    dcc.Markdown(children=hamiltonian_section, mathjax=True)
                                ]
                            ),
                        ]
                    ),
                    get_references_section(hamiltonian_references)
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
