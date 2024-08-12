from dash import html
from layouts.layout_main import get_navbar, get_title_section, get_footer_section


def get_chaos_layout():
    return html.Div(
        className='chaos-layout',
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
                    get_title_section("Exploring Non-Linear Dynamics"),
                ]
            ),
            html.Div(
                className='chaos-content-container',
                children=[
                    html.H3("The Chaos section of the site is currently under development...",
                            className='chaos-text'),
                ]
            ),
            html.Div(
                className='footer',
                children=[
                    get_footer_section()
                ]
            )
        ]
    )
