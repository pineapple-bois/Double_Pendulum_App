from app.content.routes import CHAOS_PAGE, HAMILTONIAN_PAGE, HOME_PAGE, LAGRANGIAN_PAGE
from app.pages.chaos import layout as chaos_layout
from app.pages.main import layout as main_layout
from app.pages.math import hamiltonian_layout, lagrangian_layout
from app.pages.not_found import layout as not_found_layout


PAGE_LAYOUTS = {
    HOME_PAGE.path: main_layout,
    LAGRANGIAN_PAGE.path: lagrangian_layout,
    HAMILTONIAN_PAGE.path: hamiltonian_layout,
    CHAOS_PAGE.path: chaos_layout,
}


def get_layout_for_path(pathname):
    layout_factory = PAGE_LAYOUTS.get(pathname)
    if layout_factory is None:
        return not_found_layout()
    return layout_factory()
