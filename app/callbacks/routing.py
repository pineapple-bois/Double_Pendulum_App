from dash.dependencies import Input, Output

from app.pages.registry import get_layout_for_path


def register_routing_callbacks(app):
    @app.callback(
        Output("page-content", "children"),
        [Input("url", "pathname")],
    )
    def display_page(pathname):
        return get_layout_for_path(pathname)

    app.clientside_callback(
        """
        function(pathname) {
            if (pathname === '/simulation') {
                initializeHomePage();  // Call the JS function to reinitialize
            }
            return '';
        }
        """,
        Output("trigger-js", "data"),
        Input("url", "pathname"),
    )
