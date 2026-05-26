from flask import Flask


def test_app_import_exposes_dash_app_without_starting_server():
    import pendulum_app

    assert pendulum_app.app.server is pendulum_app.server
    assert pendulum_app.app.title == "Double Pendulum Simulation - pineapple-bois"


def test_flask_server_is_available_for_gunicorn_style_import():
    import pendulum_app

    assert isinstance(pendulum_app.server, Flask)


def test_public_routes_return_layout_components():
    import pendulum_app

    for pathname in ["/", "/lagrangian", "/hamiltonian", "/chaos"]:
        layout = pendulum_app.display_page(pathname)
        assert layout is not None
        assert hasattr(layout, "children")
