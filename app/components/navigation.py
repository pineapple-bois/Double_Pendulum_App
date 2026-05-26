from dash import dcc, html

from app.content.routes import NAVIGATION_ITEMS


def get_navbar(current_path):
    return html.Div(
        className="navbar",
        children=[
            html.Div(
                children=[
                    dcc.Link(
                        page.label,
                        href=page.path,
                        className="nav-link",
                        style={
                            "background-color": "#76B083" if page.path == current_path else "#1E0B44",
                            "color": "white",
                        },
                    )
                    for page in NAVIGATION_ITEMS
                ],
                className="nav-links-container",
            )
        ],
    )

