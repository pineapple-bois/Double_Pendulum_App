from dash import html
from dash import dcc
from layouts.layout_main import get_navbar, get_footer_section


def get_404_layout():
    return html.Div(
        className='not-found-layout',
        children=[
            get_navbar(),
            html.Div(
                className='not-found-content-container',
                children=[
                    html.H1("404: Page Not Found 🍍", className='custom-text'),
                    html.P("Sorry, the page you are looking for does not exist.", className='custom-text'),
                    dcc.Link("Return to Home Page", href="/", className="nav-link")
                ]
            ),
            get_footer_section()
        ]
    )
