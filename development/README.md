# Hamiltonian Extension of the [Double Pendulum App](https://github.com/pineapple-bois/Double_Pendulum_App/tree/main)

This development section aims to extend the DoublePendulum App by deriving the Hamiltonian. There are a few disparate threads I'm trying to weave together. These have been started in a non-sequential fashion

----

1. ### Derive the Hamiltonian of the system and prepare equations of motion for numerical integration.
2. ### Abstract the derivation as a series of dependent functions to lambdify and substitute parameters.
3. ### Extend the `DoublePendulum` class to `DoublePendulumExplorer` capable of integrating a range of initial conditions. 
- Specifically; $\theta_2 \in [-\pi, \pi], \text{step}=0.5^{\circ}$ and $t \in [0, 120]\text{s}$
4. ### Write a data dictionary in JSON format of all angles, velocities and positions 
- Currently these use the Lagrangian and are 2 x 9Gb!
5. ### Host this data as a PostgreSQL DB on a cloud server (aiming for v.cheap/free)
6. ### Iterate over and slice the DB to plot Poincaré sections and Lyapunov exponents

----

#### All of the above will form the basis of a new page for the web app; 'chaotic dynamics'. Instead of deriving a double pendulum system 'on-the-fly', we will pull data from the database with simple slicing queries.

## Development Directory Structure

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

The notebook aims to derive the Hamiltonian symbolically from first principles using similar methods to:
- [Diego Assencio](https://dassencio.org/46)
- [lehman.edu](https://www.lehman.edu/faculty/dgaranin/Mechanics/ProblemSet-Fall-2006-4-Solution.pdf)

I'm happy with what I have derived but not yet sure how to integrate them. Maybe I need to substitute for $p_{\theta_i}$

Now aiming to refactor the DoublePendulum class in [`DoublePendulumHamiltonian.py`](DoublePendulumHamiltonian.py) to handle only the Hamiltonian system

----

2.
   ### [`HamiltonianFunctions.py`](HamiltonianFunctions.py)
     - Ongoing work in progress for deriving integrable equations.
   ### [`TestingHamiltonian.ipynb`](TestingHamiltonian.ipynb)
     - A notebook for testing the Hamiltonian functions and their integration to the DoublePendulum class.

----

3. ### [`DoublePendulumSubclass.py`](DoublePendulumSubclass.py)
   The `DoublePendulumExplorer` subclass extends the functionality of the `DoublePendulum` class to explore a range of initial conditions for a double pendulum system. It focuses on how varying the initial angle \(\theta_2\) affects the system's dynamics, and it provides tools for visualizing Poincaré sections and other dynamic behaviors.

   &nbsp;
     - **Exploration of Initial Conditions**: Vary $\theta_2$ while keeping other initial conditions fixed to see how different initial angles affect the dynamics.
     - **Poincaré Sections**: Calculate and visualize Poincaré sections to gain insights into the system's phase space structure and identify periodic or chaotic behavior.
     - **Simulations and Data Structures**: Run multiple simulations and organise the results in a structured format for easy analysis and visualisation.

   
   #### Class Methods

   `_generate_initial_conditions(step_size=0.5)`
   - Generate a list of initial conditions for the pendulum by varying $\theta_2$ within the specified range.

   
   `_run_simulations(integrator)`
   - Run multiple simulations of the double pendulum, each with a different initial $\theta_2$ value.


   `_calculate_and_store_positions()`
   - Calculate the (x, y) positions of both pendulum bobs for each simulation and store them in separate arrays.


   `_create_data_structure()`
   - Create a dictionary to store simulation data, including angular displacements, velocities, and positions.


   `get_simulation_data(integrator)`
   - Public method to access the simulation data dictionary. Runs the full simulation and analysis if not already done.


   `find_poincare_section(y_fixed, time_interval, angle_interval)`
   - Find the Poincaré section by identifying points where the second pendulum bob crosses a fixed vertical position within a specified time and angle interval.


   `plot_poincare_map()`
   - Plot the Poincaré map, showing the points where the pendulum crosses the specified vertical position. Each trajectory is plotted with a different color.

---

4. ### [`DevelopmentSubClass.ipynb`](DevelopmentSubClass.ipynb)
   - Have started writing the base methods for the subclass. Really, I need a working Hamiltonian model to go any further.
   - The data dictionaries appear to be quite good!
   - The Poincaré sections are really not what we are looking for...

----

5. ### [`JSONTest.ipynb`](JSONTest.ipynb)
   - Reading in the JSON data using Pandas (Will maybe swap for Polars once DB launched)

----



