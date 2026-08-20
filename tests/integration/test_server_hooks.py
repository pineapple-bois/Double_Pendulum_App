import importlib

import pytest
from flask import Flask

import app.config
from app.server_hooks import configure_server


def build_server(monkeypatch, force_https):
    monkeypatch.setattr(app.config, "FORCE_HTTPS", force_https)
    monkeypatch.setattr(
        app.config,
        "TRUSTED_HOSTS",
        app.config.PRODUCTION_TRUSTED_HOSTS if force_https else None,
    )

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
        base_url="http://double-pendulum.net",
    )

    assert response.status_code == 301
    assert response.headers["Location"] == (
        "https://double-pendulum.net/example/path?alpha=1&beta=two"
    )


def test_forwarded_https_request_does_not_redirect(monkeypatch):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path?alpha=1",
        base_url="http://double-pendulum.net",
        headers={"X-Forwarded-Proto": "https"},
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_secure_request_does_not_redirect(monkeypatch):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path?alpha=1",
        base_url="https://double-pendulum.net",
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


@pytest.mark.parametrize("hostname", app.config.PRODUCTION_TRUSTED_HOSTS)
def test_production_hosts_are_accepted(monkeypatch, hostname):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path",
        base_url=f"https://{hostname}",
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_untrusted_host_is_rejected_in_production_mode(monkeypatch):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path",
        base_url="https://hostile.example",
    )

    assert response.status_code == 400


def test_untrusted_http_host_is_rejected_instead_of_redirected(monkeypatch):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path",
        base_url="http://hostile.example",
    )

    assert response.status_code == 400
    assert "Location" not in response.headers


@pytest.mark.parametrize(
    "base_url",
    ["http://localhost:8050", "http://127.0.0.1:8050"],
)
def test_local_development_hosts_remain_available(monkeypatch, base_url):
    server = build_server(monkeypatch, force_https=False)

    response = server.test_client().get("/example/path", base_url=base_url)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_first_forwarded_protocol_value_preserves_existing_behavior(monkeypatch):
    server = build_server(monkeypatch, force_https=True)
    client = server.test_client()

    forwarded_https = client.get(
        "/example/path",
        base_url="http://double-pendulum.net",
        headers={"X-Forwarded-Proto": "https, http"},
    )
    forwarded_http = client.get(
        "/example/path",
        base_url="http://double-pendulum.net",
        headers={"X-Forwarded-Proto": "http, https"},
    )

    assert forwarded_https.status_code == 200
    assert forwarded_http.status_code == 301
    assert forwarded_http.headers["Location"] == (
        "https://double-pendulum.net/example/path"
    )


def test_secure_request_ignores_conflicting_forwarded_http_value(monkeypatch):
    server = build_server(monkeypatch, force_https=True)

    response = server.test_client().get(
        "/example/path",
        base_url="https://double-pendulum.net",
        headers={"X-Forwarded-Proto": "http"},
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
    assert response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
