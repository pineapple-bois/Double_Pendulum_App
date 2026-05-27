from app.content.routes import (
    CHAOS_PAGE,
    EQUATIONS_PAGE,
    HAMILTONIAN_PAGE,
    HOME_PAGE,
    LAGRANGIAN_PAGE,
    SIMULATION_PAGE,
)
from app.pages.chaos import layout as chaos_layout
from app.pages.equations import (
    get_equations_layout,
    get_euler_lagrange_layout,
    get_hamiltonian_layout,
)
from app.pages.home import layout as home_layout
from app.pages.not_found import layout as not_found_layout
from app.pages.simulation import layout as simulation_layout


PAGE_LAYOUTS = {
    HOME_PAGE.path: home_layout,
    SIMULATION_PAGE.path: simulation_layout,
    EQUATIONS_PAGE.path: get_equations_layout,
    LAGRANGIAN_PAGE.path: get_euler_lagrange_layout,
    HAMILTONIAN_PAGE.path: get_hamiltonian_layout,
    CHAOS_PAGE.path: chaos_layout,
}


def get_layout_for_path(pathname):
    layout_factory = PAGE_LAYOUTS.get(pathname)
    if layout_factory is None:
        return not_found_layout()
    return layout_factory()
