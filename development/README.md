# Hamiltonian Extension of the [Double Pendulum App](https://github.com/pineapple-bois/Double_Pendulum_App/tree/main)

This development section aims to extend the DoublePendulum App by deriving the Hamiltonian

There are a few disparate threads I'm trying to weave together. These have been started in a non-sequential fashion

1. Derive the Hamiltonian of the system and prepare equations of motion for numerical integration.
2. Abstract the derivation as a series of dependent functions to lambdify and substitute parameters.
3. Extend the `DoublePendulum` class to `DoublePendulumExplorer` capable of integrating a range of initial conditions. Specifically, $\theta_1, \theta_2 \in (-\pi, \pi)$
4. Write a data dictionary in JSON format of all angles, velocities and positions (currently this uses the Lagrangian and is 2 x 9Gb)
5. Host this data as a PostgreSQL DB on a cloud server
6. Iterate over and slice the DB to plot Poincaré sections and Lyapunov exponents


### Directory Structure

```
├── DevelopmentHamiltonian.ipynb
├── DevelopmentNewClass.ipynb
├── DoublePendulumRefactor.py
├── HamiltonianFunctions.py
├── HamiltonianFunctions2.py
├── JSONTest.ipynb
└── TestingHamiltonian.ipynb
```

----

1. ### [`DevelopmentHamiltonian.ipynb`](DevelopmentHamiltonian.ipynb)

Derive the Hamiltonian symbolically from first principles using similar methods to:
- [Diego Assencio](https://dassencio.org/46)
- [lehman.edu](https://www.lehman.edu/faculty/dgaranin/Mechanics/ProblemSet-Fall-2006-4-Solution.pdf)

Derived Equations:

$$
\left[\begin{matrix}\frac{d}{d t} \theta_{1}{\left(t \right)}\\\frac{d}{d t} \theta_{2}{\left(t \right)}\\\frac{d}{d t} \operatorname{p_{\theta 1}}{\left(t \right)}\\\frac{d}{d t} \operatorname{p_{\theta 2}}{\left(t \right)}\end{matrix}\right] = \left[\begin{matrix}\frac{- l_{1} \operatorname{p_{\theta 2}}{\left(t \right)} \cos{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)} + l_{2} \operatorname{p_{\theta 1}}{\left(t \right)}}{l_{1}^{2} l_{2} \left(m_{1} + m_{2} \sin^{2}{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}\right)}\\\frac{l_{1} m_{1} \operatorname{p_{\theta 2}}{\left(t \right)} + l_{1} m_{2} \operatorname{p_{\theta 2}}{\left(t \right)} - l_{2} m_{2} \operatorname{p_{\theta 1}}{\left(t \right)} \cos{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}}{l_{1} l_{2}^{2} m_{2} \left(m_{1} + m_{2} \sin^{2}{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}\right)}\\\frac{- g l_{1}^{3} l_{2}^{2} \left(m_{1} + m_{2}\right) \left(m_{1} + m_{2} \sin^{2}{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}\right)^{2} \sin{\left(\theta_{1}{\left(t \right)} \right)} - l_{1} l_{2} \left(m_{1} + m_{2} \sin^{2}{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}\right) \operatorname{p_{\theta 1}}{\left(t \right)} \operatorname{p_{\theta 2}}{\left(t \right)} \sin{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)} + \left(l_{1}^{2} m_{1} \operatorname{p_{\theta 2}}^{2}{\left(t \right)} + l_{1}^{2} m_{2} \operatorname{p_{\theta 2}}^{2}{\left(t \right)} - 2 l_{1} l_{2} m_{2} \operatorname{p_{\theta 1}}{\left(t \right)} \operatorname{p_{\theta 2}}{\left(t \right)} \cos{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)} + l_{2}^{2} m_{2} \operatorname{p_{\theta 1}}^{2}{\left(t \right)}\right) \sin{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)} \cos{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}}{l_{1}^{2} l_{2}^{2} \left(m_{1} + m_{2} \sin^{2}{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}\right)^{2}}\\\frac{- g l_{1}^{2} l_{2}^{3} m_{2} \left(m_{1} + m_{2} \sin^{2}{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}\right)^{2} \sin{\left(\theta_{2}{\left(t \right)} \right)} + l_{1} l_{2} \left(m_{1} + m_{2} \sin^{2}{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}\right) \operatorname{p_{\theta 1}}{\left(t \right)} \operatorname{p_{\theta 2}}{\left(t \right)} \sin{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)} - \left(l_{1}^{2} m_{1} \operatorname{p_{\theta 2}}^{2}{\left(t \right)} + l_{1}^{2} m_{2} \operatorname{p_{\theta 2}}^{2}{\left(t \right)} - 2 l_{1} l_{2} m_{2} \operatorname{p_{\theta 1}}{\left(t \right)} \operatorname{p_{\theta 2}}{\left(t \right)} \cos{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)} + l_{2}^{2} m_{2} \operatorname{p_{\theta 1}}^{2}{\left(t \right)}\right) \sin{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)} \cos{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}}{l_{1}^{2} l_{2}^{2} \left(m_{1} + m_{2} \sin^{2}{\left(\theta_{1}{\left(t \right)} - \theta_{2}{\left(t \right)} \right)}\right)^{2}}\end{matrix}\right]
$$

