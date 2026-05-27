from app.content.home import EXPLORE_LINKS, FURTHER_READING, HOME_TITLE
from app.content.equations import BRANCH_CARDS, DERIVATION_SECTIONS, MODEL_SUMMARIES
from app.content.math import MATH_PAGES
from app.content.not_found import NOT_FOUND_HAIKU_LINES
from app.content.routes import APP_TITLE, NAVIGATION_ITEMS, PAGES_BY_PATH, PUBLIC_ROUTE_ITEMS
from app.content.simulation import DESCRIPTION_PARAGRAPHS, INFORMATION_TEXT, MODEL_CARDS
from app.callbacks.routing import register_routing_callbacks
from app.callbacks.simulation import register_simulation_callbacks
from app.pages import chaos, equations, home, math, not_found, simulation
from app.pages.registry import PAGE_LAYOUTS, get_layout_for_path


def test_navigation_metadata_preserves_public_routes():
    assert APP_TITLE == "Double Pendulum Simulation - pineapple-bois"
    assert [page.path for page in NAVIGATION_ITEMS] == [
        "/",
        "/simulation",
        "/equations",
        "/chaos",
    ]
    assert [page.path for page in PUBLIC_ROUTE_ITEMS] == [
        "/",
        "/simulation",
        "/equations",
        "/lagrangian",
        "/hamiltonian",
        "/chaos",
    ]
    assert PAGES_BY_PATH["/"].title == "Double Pendulum Explorer"
    assert PAGES_BY_PATH["/simulation"].title == "Double Pendulum Simulation"
    assert PAGES_BY_PATH["/equations"].title == "Equations of Motion"
    assert set(PAGE_LAYOUTS) == {
        "/",
        "/simulation",
        "/equations",
        "/lagrangian",
        "/hamiltonian",
        "/chaos",
    }


def test_home_content_uses_double_pendulum_routes():
    assert HOME_TITLE == "Double Pendulum Explorer"
    assert [item.href for item in EXPLORE_LINKS] == [
        "/simulation",
        "/equations",
        "/chaos",
    ]
    assert FURTHER_READING
    reading_references = [item.reference for item in FURTHER_READING]
    assert "Gleick, J. (1997). Chaos. Vintage." in reading_references
    assert all("Taylor" not in reference for reference in reading_references)


def test_page_content_modules_load_existing_copy_and_markdown():
    assert INFORMATION_TEXT.strip()
    assert DESCRIPTION_PARAGRAPHS
    assert [card.title for card in MODEL_CARDS] == ["Simple Model", "Compound Model"]

    assert MATH_PAGES["lagrangian"].markdown.strip()
    assert MATH_PAGES["hamiltonian"].markdown.strip()
    assert len(MATH_PAGES["lagrangian"].references) == 3
    assert len(MATH_PAGES["hamiltonian"].references) == 4


def test_equations_content_is_structured_and_reuses_existing_assets():
    assert [card.title for card in MODEL_SUMMARIES] == ["Simple model", "Compound model"]
    assert MODEL_SUMMARIES[0].image_src == "/assets/Images/Model_Simple_Transparent_NoText.png"
    assert MODEL_SUMMARIES[1].image_src == "/assets/Images/Model_Compound_Transparent_NoText.png"
    assert "rigid, massless, and inextensible" in MODEL_SUMMARIES[0].summary
    assert "centre of mass" in MODEL_SUMMARIES[1].details[0]
    assert [card.href for card in BRANCH_CARDS] == [
        "#euler-lagrange-formulation",
        "#hamiltonian-formulation",
    ]
    assert [section.section_id for section in DERIVATION_SECTIONS] == [
        "shared-derivation",
        "euler-lagrange-formulation",
        "hamiltonian-formulation",
    ]
    shared_blocks = {
        block.title: " ".join((block.markdown + " " + block.note).split())
        for block in DERIVATION_SECTIONS[0].blocks
    }
    assert "Physical assumptions" in shared_blocks
    assert "Non-conservative forces such as air resistance and hinge friction are neglected" in shared_blocks["Physical assumptions"]
    assert "downward vertical" in shared_blocks["Coordinate convention"]
    assert "x_2 = x_1 + l_2 \\sin(\\theta_2(t))" in shared_blocks["Bob positions"]
    assert "V_2=-gm_2\\left(l_1\\cos(\\theta_1(t))+l_2\\cos(\\theta_2(t))\\right)" in shared_blocks["Energy contribution from P2"]
    kinetic_markdown = shared_blocks["Collecting total energy"]
    assert "will not separate into two independent pendulums" in kinetic_markdown
    assert "Both are different formulations of the same conservative model" in shared_blocks[
        "The Lagrangian as the common starting point"
    ]
    assert all(len(section.blocks) > 1 for section in DERIVATION_SECTIONS)


def test_page_registry_returns_404_for_unknown_routes():
    layout = get_layout_for_path("/does-not-exist")

    assert layout is not None
    assert hasattr(layout, "children")


def test_page_registry_resolves_preserved_routes_to_layouts():
    for pathname in ["/", "/simulation", "/equations", "/lagrangian", "/hamiltonian", "/chaos"]:
        layout = get_layout_for_path(pathname)

        assert layout is not None
        assert hasattr(layout, "children")


def test_home_and_404_have_chromeless_hero_layouts():
    home_layout = home.layout()
    not_found_layout = not_found.layout()

    home_classes = collect_classnames(home_layout)
    not_found_classes = collect_classnames(not_found_layout)
    not_found_text = " ".join(collect_text(not_found_layout))

    assert "site-header" not in home_classes
    assert "site-header" not in not_found_classes
    assert "home-hero" in home_classes
    assert "not-found-hero" in not_found_classes
    for line in NOT_FOUND_HAIKU_LINES:
        assert line in not_found_text


def test_simulation_callback_registration_is_importable():
    assert callable(register_simulation_callbacks)


def test_routing_callback_registration_is_importable():
    assert callable(register_routing_callbacks)


def test_page_modules_return_dash_components():
    page_layouts = [
        home.layout(),
        simulation.layout(),
        equations.layout(),
        math.lagrangian_layout(),
        math.hamiltonian_layout(),
        chaos.layout(),
        not_found.layout(),
    ]

    for layout in page_layouts:
        assert layout is not None
        assert hasattr(layout, "children")


def collect_classnames(component):
    classnames = set()
    stack = [component]

    while stack:
        item = stack.pop()
        if item is None or isinstance(item, (str, int, float)):
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue

        class_name = getattr(item, "className", None)
        if class_name:
            classnames.update(str(class_name).split())

        children = getattr(item, "children", None)
        if children is not None:
            stack.append(children)

    return classnames


def collect_text(component):
    text = []
    stack = [component]

    while stack:
        item = stack.pop()
        if item is None:
            continue
        if isinstance(item, (str, int, float)):
            text.append(str(item))
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue

        children = getattr(item, "children", None)
        if children is not None:
            stack.append(children)

    return text
