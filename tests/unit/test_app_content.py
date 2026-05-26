from app.content.home import DESCRIPTION_PARAGRAPHS, INFORMATION_TEXT, MODEL_CARDS
from app.content.math import MATH_PAGES
from app.content.routes import APP_TITLE, NAVIGATION_ITEMS, PAGES_BY_PATH
from app.callbacks.routing import register_routing_callbacks
from app.callbacks.simulation import register_simulation_callbacks
from app.pages import chaos, main, math, not_found
from app.pages.registry import PAGE_LAYOUTS, get_layout_for_path


def test_navigation_metadata_preserves_public_routes():
    assert APP_TITLE == "Double Pendulum Simulation - pineapple-bois"
    assert [page.path for page in NAVIGATION_ITEMS] == ["/", "/lagrangian", "/hamiltonian", "/chaos"]
    assert PAGES_BY_PATH["/"].title == "Double Pendulum Simulation"
    assert set(PAGE_LAYOUTS) == {"/", "/lagrangian", "/hamiltonian", "/chaos"}


def test_page_content_modules_load_existing_copy_and_markdown():
    assert INFORMATION_TEXT.strip()
    assert DESCRIPTION_PARAGRAPHS
    assert [card.title for card in MODEL_CARDS] == ["Simple Model", "Compound Model"]

    assert MATH_PAGES["lagrangian"].markdown.strip()
    assert MATH_PAGES["hamiltonian"].markdown.strip()
    assert len(MATH_PAGES["lagrangian"].references) == 3
    assert len(MATH_PAGES["hamiltonian"].references) == 4


def test_page_registry_returns_404_for_unknown_routes():
    layout = get_layout_for_path("/does-not-exist")

    assert layout is not None
    assert hasattr(layout, "children")


def test_page_registry_resolves_preserved_routes_to_layouts():
    for pathname in ["/", "/lagrangian", "/hamiltonian", "/chaos"]:
        layout = get_layout_for_path(pathname)

        assert layout is not None
        assert hasattr(layout, "children")


def test_simulation_callback_registration_is_importable():
    assert callable(register_simulation_callbacks)


def test_routing_callback_registration_is_importable():
    assert callable(register_routing_callbacks)


def test_page_modules_return_dash_components():
    page_layouts = [
        main.layout(),
        math.lagrangian_layout(),
        math.hamiltonian_layout(),
        chaos.layout(),
        not_found.layout(),
    ]

    for layout in page_layouts:
        assert layout is not None
        assert hasattr(layout, "children")
