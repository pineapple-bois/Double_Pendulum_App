from dataclasses import dataclass


APP_TITLE = "Double Pendulum Simulation - pineapple-bois"


@dataclass(frozen=True)
class PageMetadata:
    path: str
    label: str
    title: str
    description: str = ""


HOME_PAGE = PageMetadata(
    path="/",
    label="Home",
    title="Double Pendulum Explorer",
    description="Landing page for the nonlinear dynamics and chaos companion app.",
)
SIMULATION_PAGE = PageMetadata(
    path="/simulation",
    label="Simulation",
    title="Double Pendulum Simulation",
    description="Interactive double-pendulum simulation and visualisation.",
)
LAGRANGIAN_PAGE = PageMetadata(
    path="/lagrangian",
    label="Lagrangian",
    title="Lagrangian Derivation",
    description="Symbolic Lagrangian derivation for the double pendulum.",
)
HAMILTONIAN_PAGE = PageMetadata(
    path="/hamiltonian",
    label="Hamiltonian",
    title="Hamiltonian Derivation",
    description="Symbolic Hamiltonian derivation for the double pendulum.",
)
CHAOS_PAGE = PageMetadata(
    path="/chaos",
    label="Chaos",
    title="Exploring Non-Linear Dynamics",
    description="Work-in-progress nonlinear dynamics and chaos section.",
)
NOT_FOUND_PAGE = PageMetadata(
    path="",
    label="Not Found",
    title="Page not found",
    description="The requested page was not found.",
)

NAVIGATION_ITEMS = (
    HOME_PAGE,
    SIMULATION_PAGE,
    LAGRANGIAN_PAGE,
    HAMILTONIAN_PAGE,
    CHAOS_PAGE,
)

PAGES_BY_PATH = {page.path: page for page in NAVIGATION_ITEMS}
