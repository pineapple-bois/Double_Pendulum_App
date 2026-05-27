from pathlib import Path

from dash import dcc

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
        "/equations",
        "/simulation",
        "/chaos",
    ]
    assert [page.path for page in PUBLIC_ROUTE_ITEMS] == [
        "/",
        "/equations",
        "/simulation",
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
        "/equations",
        "/simulation",
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
        "/equations",
        "/lagrangian",
        "/hamiltonian",
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


def test_equations_euler_lagrange_branch_is_guided_and_uses_project_notation():
    agents_text = Path("AGENTS.md").read_text()
    assert "\\frac{\\mathrm{d}}{\\mathrm{d}t}" in agents_text
    assert "Preserve standard `\\partial` notation" in agents_text

    euler_blocks = {
        block.title: " ".join((block.markdown + " " + block.note).split())
        for block in DERIVATION_SECTIONS[1].blocks
    }
    assert list(euler_blocks) == [
        "General Euler-Lagrange equation",
        "Applying the operator to two coordinates",
        "Where the coupling enters",
        "Coupled second-order equations for the simple model",
        "Isolating the angular accelerations",
        "First-order simulation system",
        "Compound model mechanics",
        "Compound-model Lagrangian",
        "Compound-model Euler-Lagrange equations",
    ]
    assert "\\frac{d" not in " ".join(euler_blocks.values())
    assert "\\frac{\\mathrm{d}}{\\mathrm{d}t}" in euler_blocks["General Euler-Lagrange equation"]
    assert "partial derivatives treat" in euler_blocks["General Euler-Lagrange equation"]
    assert "kinetic-energy cross term" in euler_blocks["Where the coupling enters"]
    assert "b_1=-\\frac" in euler_blocks["Isolating the angular accelerations"]
    assert "I_{\\mathrm{cm}}=\\frac{1}{12}Ml^2" in euler_blocks["Compound model mechanics"]
    assert "I_{\\mathrm{end}}" in euler_blocks["Compound model mechanics"]
    assert "\\mathcal{L}_{\\mathrm{c}}" in euler_blocks["Compound-model Lagrangian"]
    assert "7M_1l_1^2\\dot{\\theta}_1^2" in euler_blocks["Compound-model Lagrangian"]
    assert "c_1=-\\frac" in euler_blocks["Compound-model Euler-Lagrange equations"]
    assert "page keeps" not in " ".join(euler_blocks.values())


def test_equations_hamiltonian_branch_is_guided_and_uses_project_notation():
    hamiltonian_blocks = {
        block.title: " ".join((block.markdown + " " + block.note).split())
        for block in DERIVATION_SECTIONS[2].blocks
    }
    assert list(hamiltonian_blocks) == [
        "Why introduce momenta?",
        "Canonical momenta",
        "Momentum matrix for the simple model",
        "Recovering velocities from momenta",
        "Legendre transform",
        "Hamiltonian as total energy",
        "Hamilton's equations",
        "First-order phase-space system",
        "Compound-model momentum matrix",
        "Compound Hamiltonian system",
    ]
    hamiltonian_text = " ".join(hamiltonian_blocks.values())
    assert "\\frac{d" not in hamiltonian_text
    assert "p_{\\theta_i}=\\frac{\\partial \\mathcal{L}}{\\partial \\dot{\\theta}_i}" in hamiltonian_blocks[
        "Canonical momenta"
    ]
    assert "not simply independent $mv$ terms" in hamiltonian_blocks["Why introduce momenta?"]
    assert "configuration-dependent inertia matrix" in hamiltonian_blocks[
        "Momentum matrix for the simple model"
    ]
    assert "must be written in terms of coordinates and momenta" in hamiltonian_blocks[
        "Recovering velocities from momenta"
    ]
    assert "total mechanical energy expressed in phase-space variables" in hamiltonian_blocks[
        "Legendre transform"
    ]
    assert "\\frac{\\mathrm{d}}{\\mathrm{d}t}" in hamiltonian_blocks[
        "First-order phase-space system"
    ]
    assert "first-order by construction" in hamiltonian_blocks["Hamilton's equations"]
    assert "\\mathbf{B}_c" in hamiltonian_blocks["Compound-model momentum matrix"]
    assert "7M_1l_1^2p_{\\theta_2}^2" in hamiltonian_blocks["Compound Hamiltonian system"]
    assert "49M_1+9M_2\\sin^2(\\Delta)+12M_2" in hamiltonian_blocks[
        "Compound Hamiltonian system"
    ]
    assert "source says" not in hamiltonian_text
    assert "corrected" not in hamiltonian_text


def test_page_registry_returns_404_for_unknown_routes():
    layout = get_layout_for_path("/does-not-exist")

    assert layout is not None
    assert hasattr(layout, "children")


def test_page_registry_resolves_preserved_routes_to_layouts():
    for pathname in ["/", "/simulation", "/equations", "/lagrangian", "/hamiltonian", "/chaos"]:
        layout = get_layout_for_path(pathname)

        assert layout is not None
        assert hasattr(layout, "children")


def test_equations_route_lazy_mounts_overview_without_branches():
    layout = get_layout_for_path("/equations")
    text = " ".join(collect_text(layout))

    assert "The common Lagrangian starting point" in text
    assert "Physical assumptions" in text
    assert "General Euler-Lagrange equation" not in text
    assert "Why introduce momenta?" not in text


def test_lagrangian_route_mounts_only_euler_lagrange_branch():
    layout = get_layout_for_path("/lagrangian")
    text = " ".join(collect_text(layout))

    assert "The common Lagrangian starting point" in text
    assert "General Euler-Lagrange equation" in text
    assert "Coupled second-order equations for the simple model" in text
    assert "Why introduce momenta?" not in text
    assert "Hamiltonian as total energy" not in text


def test_hamiltonian_route_mounts_only_hamiltonian_branch():
    layout = get_layout_for_path("/hamiltonian")
    text = " ".join(collect_text(layout))

    assert "The common Lagrangian starting point" in text
    assert "Why introduce momenta?" in text
    assert "Hamiltonian as total energy" in text
    assert "General Euler-Lagrange equation" not in text
    assert "Coupled second-order equations for the simple model" not in text


def test_equations_overview_has_reduced_markdown_component_count():
    overview_count = count_components(get_layout_for_path("/equations"), dcc.Markdown)
    euler_count = count_components(get_layout_for_path("/lagrangian"), dcc.Markdown)
    hamiltonian_count = count_components(get_layout_for_path("/hamiltonian"), dcc.Markdown)

    assert overview_count < 35
    assert overview_count < euler_count
    assert overview_count < hamiltonian_count


def test_equations_layout_calls_only_selected_derivation_branch(monkeypatch):
    called_section_ids = []
    original_renderer = equations.render_derivation_section

    def recording_renderer(section):
        called_section_ids.append(section.section_id)
        return original_renderer(section)

    monkeypatch.setattr(equations, "render_derivation_section", recording_renderer)

    equations.layout()
    assert called_section_ids == ["shared-derivation"]

    called_section_ids.clear()
    equations.layout(equations.EULER_LAGRANGE_BRANCH)
    assert called_section_ids == ["shared-derivation", "euler-lagrange-formulation"]

    called_section_ids.clear()
    equations.layout(equations.HAMILTONIAN_BRANCH)
    assert called_section_ids == ["shared-derivation", "hamiltonian-formulation"]


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


def count_components(component, component_type):
    count = 0
    stack = [component]

    while stack:
        item = stack.pop()
        if item is None or isinstance(item, (str, int, float)):
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue

        if isinstance(item, component_type):
            count += 1

        children = getattr(item, "children", None)
        if children is not None:
            stack.append(children)

    return count
