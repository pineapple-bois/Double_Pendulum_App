import importlib

import app.config


def reload_config(monkeypatch, value=None):
    if value is None:
        monkeypatch.delenv("FORCE_HTTPS", raising=False)
    else:
        monkeypatch.setenv("FORCE_HTTPS", value)
    return importlib.reload(app.config)


def test_force_https_defaults_to_false(monkeypatch):
    config = reload_config(monkeypatch)

    assert config.FORCE_HTTPS is False


def test_force_https_truthy_values(monkeypatch):
    for value in ["1", "true", "TRUE", "yes", "Yes", "on", "ON"]:
        config = reload_config(monkeypatch, value)

        assert config.FORCE_HTTPS is True


def test_force_https_falsey_values(monkeypatch):
    for value in ["", "0", "false", "no", "off", "anything-else"]:
        config = reload_config(monkeypatch, value)

        assert config.FORCE_HTTPS is False
