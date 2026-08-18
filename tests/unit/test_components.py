from app.components.derivation import render_branch_card, render_derivation_section, render_model_summary
from app.components.figure_style import mpl_layout
from app.components.footer import get_footer_section
from app.components.graphs import get_animation_phase_section, get_time_graph_section
from app.components.navigation import get_navbar
from app.components.references import get_references_section
from app.components.shell import get_body_section, get_footer_wrapper, get_header_section, get_title_section
from app.components.simulation_controls import build_simulation_controls
from app.content.math import MATH_PAGES
from app.content.equations import BRANCH_CARDS, DERIVATION_SECTIONS, MODEL_SUMMARIES


SIMULATION_CONTROL_IDS = {
    "model-type",
    "system-type",
    "param_g",
    "unity-parameters",
    "lengths-label",
    "param_l1",
    "param_l2",
    "masses-label",
    "param_m1",
    "param_m2",
    "param_M1",
    "param_M2",
    "init_cond_theta1",
    "init_cond_theta2",
    "init_cond_omega1",
    "init_cond_omega2",
    "time_start",
    "time_end",
}


def assert_dash_component(component):
    assert component is not None
    assert hasattr(component, "children")


def collect_component_ids(component):
    ids = set()
    stack = [component]

    while stack:
        item = stack.pop()
        if item is None or isinstance(item, (str, int, float)):
            continue
        if isinstance(item, (list, tuple)):
            stack.extend(item)
            continue

        component_id = getattr(item, "id", None)
        if component_id:
            ids.add(component_id)

        children = getattr(item, "children", None)
        if children is not None:
            stack.append(children)

    return ids


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


def test_shell_components_return_dash_components():
    assert_dash_component(get_header_section("/"))
    assert_dash_component(get_title_section("Example"))
    assert_dash_component(get_body_section([]))
    assert_dash_component(get_footer_wrapper(get_footer_section()))


def test_navigation_and_footer_components_return_dash_components():
    navbar = get_navbar("/simulation")
    footer = get_footer_section()
    attribution, github_link = footer.children

    assert_dash_component(navbar)
    assert "site-nav-toggle" in collect_classnames(navbar)
    assert_dash_component(footer)
    assert {"site-footer", "site-footer-link", "site-footer-icon"} <= collect_classnames(footer)
    assert github_link.className == "site-footer-link"
    assert github_link.children.src == "/assets/Images/github-mark.png"
    assert github_link.children.alt == "GitHub"
    assert getattr(github_link, "aria-label") == "GitHub repository"
    assert attribution.className == "site-footer-label"
    assert attribution.children == "pineapple-bois 2026"
    assert "submit-val" not in collect_component_ids(footer)
    assert "run-simulation-group" not in collect_classnames(footer)


def test_reference_and_graph_components_return_dash_components():
    assert_dash_component(get_references_section(MATH_PAGES["lagrangian"].references))
    assert_dash_component(get_animation_phase_section("Trace Animation", "Phase Portrait"))
    assert_dash_component(get_time_graph_section("Time Graph"))


def test_derivation_components_return_dash_components():
    assert_dash_component(render_model_summary(MODEL_SUMMARIES[0]))
    assert_dash_component(render_branch_card(BRANCH_CARDS[0]))
    section = render_derivation_section(DERIVATION_SECTIONS[0])

    assert_dash_component(section)
    assert "equations-section" in collect_classnames(section)


def test_matplotlib_plotly_style_helper_is_available():
    assert mpl_layout.paper_bgcolor == "#ffffff"
    assert mpl_layout.plot_bgcolor == "#ffffff"
    assert mpl_layout.font.family.startswith('"Helvetica Neue"')
    assert mpl_layout.font.color == "#1f2933"
    assert mpl_layout.xaxis.gridcolor == "#ddd8d0"
    assert mpl_layout.xaxis.linecolor == "#82908e"
    assert mpl_layout.colorway[:2] == ("#00635d", "#5f6b6b")
    assert mpl_layout.modebar.activecolor == "#00635d"
    assert mpl_layout.dragmode is False


def test_simulation_controls_return_dash_component_with_callback_bound_ids():
    controls = build_simulation_controls()

    assert_dash_component(controls)
    assert SIMULATION_CONTROL_IDS <= collect_component_ids(controls)
