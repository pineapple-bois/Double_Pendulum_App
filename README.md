# [Double Pendulum App](https://double-pendulum-dbd9c9702654.herokuapp.com)

This project extends the [Double Pendulum Repo](https://github.com/pineapple-bois/Double_Pendulum), a Lagrangian formulation of the equations of motion of a double pendulum system. 

----

![img](assets/Double_Pendulum.png)

#### The above figure shows simple pendulum suspended from another simple pendulum by a frictionless hinge. 
- Both pendulums move in the same plane. 
- In this system, the rods $OP_1$ and $P_1P_2$ are rigid, massless and inextensible.
- The system has two degrees of freedom and is uniquely determined by the values of $\theta_1$ and $\theta_2$

----

We solve the Euler-Lagrange equations for $\textbf{q} = [\theta_1, \theta_2]$ such that, 

$$
\frac{\text{d}}{\text{d}t}\left(\frac{\partial L}{\partial \dot{\textbf{q}}}\right)-\frac{\partial L}{\partial \textbf{q}}=0
$$

The result is a system of $|\textbf{q}|$ coupled, second-order differential equations

----

The equations are uncoupled by letting $\omega_i = \frac{\text{d}}{\text{d} t}\theta_i$

So $\omega_i$ for $i=1,2$ represents the angular velocity with $\frac{\text{d}}{\text{d} t}\omega_i \equiv \frac{\text{d}^2}{\text{d} t^2}\theta_i$

#### [Derivation](https://github.com/pineapple-bois/Double_Pendulum/blob/master/Derivation.ipynb)

----

## The Application




----

[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE.md) [![Pineapple Bois](https://img.shields.io/badge/Website-Pineapple_Bois-5087B2.svg?style=flat&logo=telegram)](https://pineapple-bois.github.io)

----
