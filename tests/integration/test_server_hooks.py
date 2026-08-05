import importlib

from flask import Flask

import app.config
from app.server_hooks import configure_server


def build_server(monkeypatch, force_https):
    monkeypatch.setattr(app.config, "FORCE_HTTPS", force_https)

    server = Flask(__name__)

    @server.route("/")
    @server.route("/example/path")
    def index():
        return "ok"

    configure_server(server)
    return server


def test_unset_force_https_env_does_not_redirect(monkeypatch):
    monkeypatch.delenv("FORCE_HTTPS", raising=False)
    importlib.reload(app.config)
    server = build_server(monkeypatch, force_https=app.config.FORCE_HTTPS)

    response = server.test_client().get("/example/path?alpha=1")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_http_request_does_not_redirect_when_force_https_is_disabled(monkeypatch):
    server = build_server(monkeypatch, force_https=False)

    response = server.test_client().get("/example/path?alpha=1")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_http_request_redirects_to_https_when_force_https_is_enabled(monkeypatch):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path?alpha=1&beta=two",
        base_url="http://example.test",
    )

    assert response.status_code == 301
    assert response.headers["Location"] == (
        "https://example.test/example/path?alpha=1&beta=two"
    )


def test_forwarded_https_request_does_not_redirect(monkeypatch):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path?alpha=1",
        base_url="http://example.test",
        headers={"X-Forwarded-Proto": "https"},
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_secure_request_does_not_redirect(monkeypatch):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path?alpha=1",
        base_url="https://example.test",
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_robots_txt_is_served_as_plain_text(monkeypatch):
    server = build_server(monkeypatch, force_https=False)

    response = server.test_client().get("/robots.txt")

    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    assert response.get_data(as_text=True) == (
        "User-agent: AhrefsBot\n"
        "Disallow: /\n"
        "\n"
        "User-agent: *\n"
        "Allow: /\n"
    )


def test_security_headers_are_added_to_responses(monkeypatch):
    server = build_server(monkeypatch, force_https=False)

    response = server.test_client().get("/example/path")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
