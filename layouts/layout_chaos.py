from dash import html
from layouts.layout_main import get_navbar, get_title_section, get_footer_section


def get_chaos_layout():
    return html.Div(
        className='chaos-layout',
        children=[
            get_navbar(),
            get_title_section(),
            html.Div(
                className='chaos-content-container',
                children=[
                    html.H2("The Chaos section of the site is currently under development...", className='chaos-text'),
                ]
            ),
            get_footer_section()
        ]
    )
