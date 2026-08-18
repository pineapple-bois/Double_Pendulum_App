import dash
from dash import html, dcc
from app import config
from app.callbacks.equations import register_equations_callbacks
from app.callbacks.routing import register_routing_callbacks
from app.callbacks.simulation import register_simulation_callbacks
from app.content.routes import APP_TITLE, HOME_PAGE
from app.pages.registry import get_layout_for_path
from app.server_hooks import configure_server


app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,  # May not be warned about genuine mistakes like typos in component IDs
    external_scripts=[
        # ... (other scripts if any)
        'https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.0/es5/tex-mml-chtml.js'
    ]
)
server = app.server
configure_server(server, dash_index_renderer=app.index)


# App set up
app.title = APP_TITLE
app.index_string = open('assets/custom-header.html', 'r').read()
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),  # Tracks the url
    dcc.Store(id='update-state', data={'clear': False, 'update': False}),
    html.Div(id='page-content', children=get_layout_for_path(HOME_PAGE.path)),  # Set initial content
    dcc.Store(id='trigger-js')  # Hidden div to trigger JS
])


register_routing_callbacks(app)
register_simulation_callbacks(app)
register_equations_callbacks(app)


if __name__ == '__main__':
    app.run(debug=config.DASH_DEBUG)
