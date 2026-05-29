from .hamiltonian import DoublePendulumHamiltonian, hamiltonian_first_order_system
from .lagrangian import DoublePendulumLagrangian, add_equations
from .metadata import SolverMetadata

__all__ = [
    "DoublePendulumHamiltonian",
    "DoublePendulumLagrangian",
    "SolverMetadata",
    "add_equations",
    "hamiltonian_first_order_system",
]
