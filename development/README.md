# Hamiltonian Extension of the [Double Pendulum App](https://github.com/pineapple-bois/Double_Pendulum_App/tree/main)

This development section aims to extend the DoublePendulum App by deriving the Hamiltonian. There are a few disparate threads I'm trying to weave together. These have been started in a non-sequential fashion

----

1. #### Derive the Hamiltonian of the system and prepare equations of motion for numerical integration 🥳🍍
2. #### Abstract the derivation as a series of dependent functions to lambdify and substitute parameters 🥳🍍
3. #### Extend the `DoublePendulum` class to `DoublePendulumExplorer` capable of integrating a range of initial conditions. 
- Specifically; $\theta_2 \in [-\pi, \pi], \text{step}=0.5^{\circ}$ and $t \in [0, 120]\text{s}$
4. #### Write a data dictionary in JSON format of all angles, velocities and positions 
- Currently these use the Lagrangian and are 2 x 9Gb!
5. #### Host this data as a PostgreSQL DB on a cloud server (aiming for v.cheap/free)
6. #### Iterate over and slice the DB to plot Poincaré sections and Lyapunov exponents

----

### All of the above will form the basis of a new page for the web app; 'chaotic dynamics'. Instead of deriving a double pendulum system 'on-the-fly', we will pull data from the database with simple slicing queries.

### Development Directory Structure

```
development/
├── JSONdata/
├── Notebooks/
│   ├── DevelopmentSubClass.ipynb
│   ├── JSONTest.ipynb
│   └── TestingHamiltonian.ipynb
├── pyscripts/
│   ├── __init__.py
│   ├── DoublePendulumHamiltonian.py
│   ├── DoublePendulumSubclass.py
│   └── HamiltonianFunctions.py
├── __init__.py
└── README.md
```

----

1. ### [`DevelopmentHamiltonian.ipynb`](https://github.com/pineapple-bois/Double_Pendulum/blob/master/DevelopmentHamiltonian.ipynb)

The notebook (moved to [Double_Pendulum Repo](https://github.com/pineapple-bois/Double_Pendulum/tree/master)) derives the Hamiltonian symbolically from first principles using similar methods to:
- [Diego Assencio](https://dassencio.org/46)
- [lehman.edu](https://www.lehman.edu/faculty/dgaranin/Mechanics/ProblemSet-Fall-2006-4-Solution.pdf)

The DoublePendulum class [`DoublePendulumHamiltonian.py`](../DoublePendulumHamiltonian.py) has been refactored to handle only the Hamiltonian system

----

2.
   ### [`HamiltonianFunctions.py`](pyscripts/HamiltonianFunctions.py)
     - Maybe a few of the functions could be optimised, particularly in relation to logic gates. 
     - Ultimately, this was much easier to derive than the Lagrangian
   ### [`TestingHamiltonian.ipynb`](Notebooks/TestingHamiltonian.ipynb)
     - Tests DoublePendulumHamiltonian instantiation for both `simple` and `compound` models

----

3. ### [`DoublePendulumSubclass.py`](pyscripts/DoublePendulumSubclass.py)

   #### This needs to be incorporated with `DoublePendulumHamiltonian.pu` after unit testing
   The `DoublePendulumExplorer` subclass extends the functionality of the `DoublePendulum` class to explore a range of initial conditions for a double pendulum system. It focuses on how varying the initial angle $\theta_2$ affects the system's dynamics, and it provides tools for visualizing Poincaré sections and other dynamic behaviors.

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

4. ### [`DevelopmentSubClass.ipynb`](Notebooks/DevelopmentSubClass.ipynb)
   - Have started writing the base methods for the subclass.
   - The data dictionaries appear to be quite good!
   - The Poincaré sections are really not what we are looking for...

----

5. ### [`JSONTest.ipynb`](Notebooks/JSONTest.ipynb)
   - Reading in the JSON data using Pandas (Will maybe swap for Polars once DB launched)

----

### Overview of Lagrangian and Hamiltonian Mechanics

**Lagrangian Mechanics:**
- The Lagrangian $\mathcal{L}$ is defined as $\mathcal{L} = T - V$, where $T$ is the kinetic energy and $V$ is the potential energy.
- The equations of motion are derived using the Euler-Lagrange equations.
- The Lagrangian formalism is particularly useful when dealing with generalised coordinates and constraints.

**Hamiltonian Mechanics:**
- The Hamiltonian $\mathcal{H}$ is defined as the total energy of the system $\mathcal{H} = T + V$ (for conservative systems {which this is!}).
- The equations of motion are derived using Hamilton's equations, which describe the time evolution of the generalised coordinates and momenta.
- The Hamiltonian formalism is advantageous in systems with conserved quantities and is deeply connected to the principles of modern physics, such as quantum mechanics.

### Using the Hamiltonian for Analysing Chaos and Periodic Orbits

**Advantages of Hamiltonian Mechanics in Chaos and Periodic Orbits:**
1. **Phase Space Analysis:**
   - Hamiltonian mechanics naturally leads to the analysis of the system in phase space (coordinates and momenta), which is crucial for studying chaotic behaviour and periodic orbits.
   - Trajectories in phase space can reveal fixed points, periodic orbits, and chaotic regions.

2. **Energy Conservation:**
   - In conservative systems, the Hamiltonian is a conserved quantity (total energy). This restriction of analysis to constant energy surfaces, simplifying the study of dynamics.

3. **Symplectic Structure:**
   - The Hamiltonian framework preserves the symplectic structure, which is important in the study of dynamical systems and chaos theory.

### Steps to Map Trajectories and Analyse Chaos

1. **Derive the Hamiltonian:**
   - Ensure that the Hamiltonian is correctly derived from the Lagrangian. In your case, you’ve already done this for the double pendulum.

2. **Compute Hamilton's Equations:**
   - Use Hamilton's equations to obtain the equations of motion:
     $\dot{q}_i = \frac{\partial H}{\partial p_i}$, $\dot{p}_i = -\frac{\partial H}{\partial q_i}$ where $\mathbf{q}=(\theta_1, \theta_2)$
   - These equations describe how the coordinates $q_i$ and momenta $p_i$ evolve over time.

3. **Phase Space Trajectories:**
   - Solve Hamilton’s equations numerically to obtain trajectories in phase space. Use Runge-Kutta integration.
   - Visualise the trajectories to identify periodic orbits, fixed points, and chaotic behaviour.

4. **Poincaré Sections:**
   - Create Poincaré sections (intersections of phase space trajectories with a lower-dimensional subspace) to visualise the structure of the system. This will help in identifying periodic orbits and chaotic regions.

5. **Lyapunov Exponents:**
   - Calculate Lyapunov exponents to quantify the sensitivity of the system to initial conditions. Positive Lyapunov exponents indicate chaos.

6. **Energy Conservation:**
   - Ensure that energy is conserved in numerical simulations. Deviations may indicate numerical errors.

7. **Bifurcation Diagrams:**
   - Vary a system parameter (e.g., length or mass) and observe changes in the system's behaviour. Plot bifurcation diagrams to identify transitions between periodic and chaotic behaviour.

8. **Periodic Orbits and Stability:**
   - Identify periodic orbits and analyse their stability. Unstable periodic orbits can be indicative of chaotic regions.

### Further Reading and Tools:
- **Books:**
  - "Nonlinear Dynamics and Chaos" by Steven Strogatz
  - "Chaos: An Introduction to Dynamical Systems" by Kathleen T. Alligood, Tim D. Sauer, and James A. Yorke
- **Software Tools:**
  - Check out [`chaospy`](https://chaospy.readthedocs.io/en/master/)
- **Papers:**
  - [Numerical analysis of a Double Pendulum System - Dartmouth](https://math.dartmouth.edu/archive/m53f09/public_html/proj/Roja_writeup.pdf)
  - [The double pendulum: a numerical study - A M Calvão and T J P Penna](https://iopscience-iop-org.libezproxy.open.ac.uk/article/10.1088/0143-0807/36/4/045018)

----
