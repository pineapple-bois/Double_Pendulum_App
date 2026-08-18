import tomllib
from pathlib import Path

import pytest
from flask import Flask

from app.content.routes import APP_TITLE, PUBLIC_ROUTE_ITEMS
from app.pages.registry import get_layout_for_path


def test_app_import_exposes_dash_app_without_starting_server():
    import pendulum_app

    assert pendulum_app.app.server is pendulum_app.server
    assert pendulum_app.app.title == APP_TITLE


def test_app_owns_global_styles_without_bootstrap_or_external_webfont():
    import pendulum_app

    project_root = Path(__file__).resolve().parents[2]
    with (project_root / "pyproject.toml").open("rb") as project_file:
        project_dependencies = tomllib.load(project_file)["project"]["dependencies"]

    assert pendulum_app.app.config.external_stylesheets == []
    assert not any(
        "dash-bootstrap-components" in dependency.lower()
        for dependency in project_dependencies
    )

    response = pendulum_app.server.test_client().get(
        "/", base_url="https://double-pendulum.test"
    )
    index = response.get_data(as_text=True)

    assert "bootstrap" not in index.lower()
    assert "fonts.googleapis.com" not in index
    assert "Red+Hat+Display" not in index


def test_flask_server_is_available_for_gunicorn_import():
    import pendulum_app

    assert isinstance(pendulum_app.server, Flask)


def test_public_routes_return_layout_components():
    import pendulum_app

    for pathname in ["/", "/simulation", "/equations", "/lagrangian", "/hamiltonian", "/chaos"]:
        layout = get_layout_for_path(pathname)
        assert layout is not None
        assert hasattr(layout, "children")


@pytest.fixture
def client():
    import pendulum_app

    return pendulum_app.server.test_client()


@pytest.mark.parametrize("pathname", [page.path for page in PUBLIC_ROUTE_ITEMS])
def test_public_http_routes_return_dash_shell(client, pathname):
    response = client.get(pathname, base_url="https://double-pendulum.test")

    assert response.status_code == 200
    assert response.mimetype == "text/html"


@pytest.mark.parametrize(
    "pathname",
    [
        "/.env",
        "/shell.php",
        "/wp-login.php",
        "/wordpress/wp-includes/wlwmanifest.xml",
        "/api/private",
        "/missing.js",
    ],
)
def test_probe_and_non_navigation_paths_return_plain_404(client, pathname):
    response = client.get(pathname, base_url="https://double-pendulum.test")

    assert response.status_code == 404
    assert response.mimetype == "text/plain"
    assert response.get_data(as_text=True) == "Not Found\n"


def test_unknown_navigation_returns_custom_404_dash_shell(client):
    pathname = "/definitely-not-a-route"
    response = client.get(pathname, base_url="https://double-pendulum.test")

    assert response.status_code == 404
    assert response.mimetype == "text/html"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Double Pendulum Simulation - Explore Non-Linear Dynamics" in response.get_data(
        as_text=True
    )

    callback = client.post(
        "/_dash-update-component",
        base_url="https://double-pendulum.test",
        json={
            "output": "page-content.children",
            "outputs": {"id": "page-content", "property": "children"},
            "inputs": [{"id": "url", "property": "pathname", "value": pathname}],
            "changedPropIds": ["url.pathname"],
            "state": [],
        },
    )

    assert callback.status_code == 200
    callback_body = callback.get_data(as_text=True)
    assert "Path not found" in callback_body
    assert "not-found-message" in callback_body
    assert "double_pend_hero1_green.png" in callback_body
    assert "Return home" in callback_body


@pytest.mark.parametrize("pathname", ["/_dash-layout", "/_dash-dependencies"])
def test_dash_framework_get_endpoints_remain_available(client, pathname):
    response = client.get(pathname, base_url="https://double-pendulum.test")

    assert response.status_code == 200
    assert response.mimetype == "application/json"


def test_dash_callback_post_remains_available(client):
    response = client.post(
        "/_dash-update-component",
        base_url="https://double-pendulum.test",
        json={
            "output": "page-content.children",
            "outputs": {"id": "page-content", "property": "children"},
            "inputs": [{"id": "url", "property": "pathname", "value": "/"}],
            "changedPropIds": ["url.pathname"],
            "state": [],
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "application/json"


def test_dash_asset_remains_available(client):
    response = client.get(
        "/assets/styles.css",
        base_url="https://double-pendulum.test",
    )

    assert response.status_code == 200
    assert response.mimetype == "text/css"


def test_application_responses_include_security_headers(client):
    response = client.get("/", base_url="https://double-pendulum.test")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
