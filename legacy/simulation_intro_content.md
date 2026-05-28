# Legacy Simulation Intro Content

Archived during Phase 5D.1 when `/simulation` changed from a documentation-style
page into a production workspace. This material is no longer rendered on the
live simulation page, but it is preserved here for reference and possible reuse
in future teaching or documentation pages.

## Introductory Copy

The double pendulum is an archetypal non-linear system in classical mechanics
that has been studied since the 18th century. In this simulation, we model two
types of double pendulum; simple and compound.

Both pendulums move in the $(x,y)$-plane. The system has two degrees of freedom,
uniquely determined by the values of $\theta_1$ & $\theta_2$.

Motion of a double pendulum system is characterised by extreme sensitivity to
initial conditions, resulting in both periodic and chaotic behaviour. The
system's equations of motion are derived using both Lagrangian and Hamiltonian
formalisms.

No closed-form solutions for $\theta_1$ and $\theta_2$ as functions of time are
known. Therefore, the system must be solved numerically.

This simulation provides a rich context for exploring non-linear dynamics. We
generate a time graph, phase portrait, and animation based on the selected model
parameters including; mass, length, release angle, and angular velocity.
Fascinating dynamics can be discovered by simply releasing the pendulums from
rest. The acceleration due to gravity acts as the restoring force, influencing
the oscillation period and stability of the motion. This model allows for the
simulation of pendulum behaviour on different celestial bodies in our Solar
System.

Reference link used in the original copy:
https://nssdc.gsfc.nasa.gov/planetary/factsheet/planet_table_ratio.html

## Simple Model

Rigid, massless, and inextensible rods $OP_1$ and $P_{1}P_{2}$ are connected by
a frictionless hinge to point masses; $m_1$ & $m_2$.

Image used in the original card:

`/assets/Images/Model_Simple_Transparent_NoText.png`

## Compound Model

The rods are modeled as uniform thin rods of evenly distributed masses $M_1$ &
$M_2$ with friction neglected at the hinge.

Reference link used in the original copy:
https://phys.libretexts.org/Courses/Joliet_Junior_College/Physics_201_-_Fall_2019v2/Book%3A_Custom_Physics_textbook_for_JJC/11%3A_Rotational_Kinematics_Angular_Momentum_and_Energy/11.06%3A_Calculating_Moments_of_Inertia

Image used in the original card:

`/assets/Images/Model_Compound_Transparent_NoText.png`
