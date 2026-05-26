from dash import dcc, html

from app.content.routes import NAVIGATION_ITEMS, PAGES_BY_PATH


def get_navbar(current_path):
    current_page = PAGES_BY_PATH.get(current_path)
    subtitle = current_page.label if current_page else ""

    return html.Nav(
        className="site-nav",
        **{"aria-label": "Primary navigation"},
        children=[
            html.Div(
                className="site-brand-block",
                children=[
                    dcc.Link("Double Pendulum Explorer", href="/", className="site-brand"),
                    html.Span(subtitle, className="site-page-subtitle"),
                ],
            ),
            html.Details(
                className="site-nav-menu",
                children=[
                    html.Summary(
                        className="site-nav-toggle",
                        title="Open navigation",
                        children=[
                            html.Span(className="site-nav-toggle-bar"),
                            html.Span(className="site-nav-toggle-bar"),
                            html.Span(className="site-nav-toggle-bar"),
                        ],
                    ),
                    html.Div(
                        className="site-nav-panel",
                        children=[
                            dcc.Link(
                                page.label,
                                href=page.path,
                                className=(
                                    "site-nav-link site-nav-link-active"
                                    if page.path == current_path
                                    else "site-nav-link"
                                ),
                            )
                            for page in NAVIGATION_ITEMS
                        ],
                    ),
                ],
            ),
        ],
    )
