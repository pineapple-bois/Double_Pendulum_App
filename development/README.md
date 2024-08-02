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

Aim to derive the Hamiltonian symbolically from first principles using similar methods to:
- [Diego Assencio](https://dassencio.org/46)
- [lehman.edu](https://www.lehman.edu/faculty/dgaranin/Mechanics/ProblemSet-Fall-2006-4-Solution.pdf)


----

2.
   ### [`HamiltonianFunctions.py`](HamiltonianFunctions.py)
   ### [`HamiltonianFunctions2.py`](HamiltonianFunctions2.py) 
     - Ongoing works in progress for deriving integrable equations.
   ### [`TestingHamiltonian.ipynb`](TestingHamiltonian.ipynb)
     - A notebook for testing the Hamiltonian functions and their integration to the DoublePendulum class.

----

3. ### [`DoublePendulumRefactor.py`](DoublePendulumRefactor.py)
4. ### [`DevelopmentNewClass.ipynb`](DevelopmentNewClass.ipynb)

    
5.### [`JSONTest.ipynb`](JSONTest.ipynb)
Reading in the JSON data using Pandas (Will maybe swap for Polars once DB launched)



