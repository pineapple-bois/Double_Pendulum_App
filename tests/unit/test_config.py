import importlib

import app.config


def reload_config(monkeypatch, *, force_https=None, dash_debug=None):
    if force_https is None:
        monkeypatch.delenv("FORCE_HTTPS", raising=False)
    else:
        monkeypatch.setenv("FORCE_HTTPS", force_https)

    if dash_debug is None:
        monkeypatch.delenv("DASH_DEBUG", raising=False)
    else:
        monkeypatch.setenv("DASH_DEBUG", dash_debug)

    return importlib.reload(app.config)


def test_force_https_defaults_to_false(monkeypatch):
    config = reload_config(monkeypatch)

    assert config.FORCE_HTTPS is False


def test_force_https_truthy_values(monkeypatch):
    for value in ["1", "true", "TRUE", "yes", "Yes", "on", "ON"]:
        config = reload_config(monkeypatch, force_https=value)

        assert config.FORCE_HTTPS is True


def test_force_https_falsey_values(monkeypatch):
    for value in ["", "0", "false", "no", "off", "anything-else"]:
        config = reload_config(monkeypatch, force_https=value)

        assert config.FORCE_HTTPS is False


def test_dash_debug_defaults_to_false(monkeypatch):
    config = reload_config(monkeypatch)

    assert config.DASH_DEBUG is False


def test_dash_debug_truthy_values(monkeypatch):
    for value in ["1", "true", "TRUE", "yes", "Yes", "on", "ON"]:
        config = reload_config(monkeypatch, dash_debug=value)

        assert config.DASH_DEBUG is True


def test_dash_debug_falsey_values(monkeypatch):
    for value in ["", "0", "false", "no", "off", "anything-else"]:
        config = reload_config(monkeypatch, dash_debug=value)

        assert config.DASH_DEBUG is False
