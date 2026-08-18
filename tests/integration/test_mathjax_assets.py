"""Tests for the locally hosted MathJax runtime."""

from dash import Dash

from pendulum_app import (
    ASSETS_DIR,
    MATHJAX_ASSET_PATH,
    MATHJAX_VENDOR_DIR,
    app,
    server,
)


REQUIRED_FONTS = {
    "MathJax_AMS-Regular.woff",
    "MathJax_Main-Regular.woff",
    "MathJax_Math-Italic.woff",
    "MathJax_Size4-Regular.woff",
}


def test_local_entry_and_licence_exist():
    entry = ASSETS_DIR / MATHJAX_ASSET_PATH
    licence = MATHJAX_VENDOR_DIR / "LICENSE"

    assert entry.is_file()
    assert licence.is_file()
    assert "Apache License" in licence.read_text(encoding="utf-8")


def test_common_html_font_runtime_exists():
    font_dir = MATHJAX_VENDOR_DIR / "output" / "chtml" / "fonts" / "woff-v2"
    font_names = {path.name for path in font_dir.glob("*.woff")}

    assert len(font_names) == 23
    assert REQUIRED_FONTS <= font_names
    assert list(MATHJAX_VENDOR_DIR.rglob("*.js")) == [
        ASSETS_DIR / MATHJAX_ASSET_PATH
    ]


def test_index_emits_only_the_local_mathjax_url():
    response = server.test_client().get("/")
    index = response.get_data(as_text=True)

    assert response.status_code == 200
    assert app.get_asset_url(MATHJAX_ASSET_PATH) in index
    assert "cdnjs.cloudflare.com" not in index
    assert "https://cdn" not in index


def test_asset_url_respects_requests_pathname_prefix():
    prefixed_app = Dash(
        "mathjax-prefix-test",
        assets_folder=str(ASSETS_DIR),
        requests_pathname_prefix="/course/",
    )

    assert prefixed_app.get_asset_url(MATHJAX_ASSET_PATH) == (
        f"/course/assets/{MATHJAX_ASSET_PATH}"
    )
