from dash import Input, Output, ctx, no_update

from app.pages import equations


ACTIVE_BRANCH_CLASS = "equations-branch-card equations-branch-card--active"
INACTIVE_BRANCH_CLASS = "equations-branch-card"


def _branch_button_state(selected_branch):
    euler_active = selected_branch == equations.EULER_LAGRANGE_BRANCH
    hamiltonian_active = selected_branch == equations.HAMILTONIAN_BRANCH

    return (
        ACTIVE_BRANCH_CLASS if euler_active else INACTIVE_BRANCH_CLASS,
        ACTIVE_BRANCH_CLASS if hamiltonian_active else INACTIVE_BRANCH_CLASS,
        "true" if euler_active else "false",
        "true" if hamiltonian_active else "false",
    )


def _branch_children(selected_branch):
    section = equations.BRANCH_SECTIONS.get(selected_branch)
    if section is None:
        return []
    return [equations.render_derivation_section(section)]


def register_equations_callbacks(app):
    @app.callback(
        Output("equations-branch-output", "children"),
        Output("equations-branch-euler_lagrange-button", "className"),
        Output("equations-branch-hamiltonian-button", "className"),
        Output("equations-branch-euler_lagrange-button", "aria-pressed"),
        Output("equations-branch-hamiltonian-button", "aria-pressed"),
        Input("equations-branch-euler_lagrange-button", "n_clicks"),
        Input("equations-branch-hamiltonian-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def select_equations_branch(_euler_clicks, _hamiltonian_clicks):
        selected_branch = {
            "equations-branch-euler_lagrange-button": equations.EULER_LAGRANGE_BRANCH,
            "equations-branch-hamiltonian-button": equations.HAMILTONIAN_BRANCH,
        }.get(ctx.triggered_id)

        if selected_branch is None:
            return no_update, no_update, no_update, no_update, no_update

        return (
            _branch_children(selected_branch),
            *_branch_button_state(selected_branch),
        )
