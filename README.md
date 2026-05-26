# Double Pendulum App

#### This repo serves a [`Plotly Dash`](https://dash.plotly.com) application built on [`Flask`](https://flask.palletsprojects.com/en/3.0.x/). It is currently associated with an older [`Heroku`](https://www.heroku.com) deployment, but active development is now focused on modernization first and redeployment later.

![img](assets/Images/Screenshot.png)

#### It is available at: [www.double-pendulum.net](http://www.double-pendulum.net)

The application is an extension of [Double_Pendulum](https://github.com/pineapple-bois/Double_Pendulum), which derived the symbolic equations of motion.

For the current modernization direction, see [`ROADMAP.md`](ROADMAP.md).

----

### Physics of a double pendulum

![img](assets/Images/Models_Joint_White.png)

#### The above figure shows `Simple` and `Compound` pendulum models. 
Both models move in the $(x,y)$-plane and the systems have two degrees of freedom. The motion is uniquely determined by the values of $\theta_1$ and $\theta_2$

`Simple Model`: 

- The rods $OP_1$ and $P_1P_2$ are rigid, massless and inextensible.
- Masses at $P_1$ and $P_2$ are subject to a uniform acceleration due to gravity.

`Compound Model`:

- Masses $M_1$ and $M_2$ are uniformly distributed along rod lengths $l_1$ and $l_2$. 
- Each rod is subject to a rotational kinetic energy and moment of inertia about its centre of mass. 
- Applying the parallel axis theorem, we account for the rotational dynamics about the pendulum ends.

The effects of any dissipative forces such as air resistance or friction are neglected therefore, the total mechanical energy is conserved. 

----

### Mathematical formulation

For this conservative system, the equations of motion are derived from Lagrangian, $\mathcal{L}$ which is given,

$$\mathcal{L}=T-V$$

Where $T$ is the kinetic energy and $V$ is the potential energy.

#### Forming a system of differential equations

1. `Lagrangian System`

We solve the Euler-Lagrange equations for $\textbf{q} = [\theta_1, \theta_2]$ such that, 

$$
\frac{\text{d}}{\text{d}t}\left(\frac{\partial L}{\partial \dot{\textbf{q}}}\right)-\frac{\partial L}{\partial \textbf{q}}=0
$$

The result is a system of $|\textbf{q}|$ coupled, second-order differential equations.

Uncoupling the equations involves extensive algebra and can be found in this [Python derivation](https://github.com/pineapple-bois/Double_Pendulum/blob/master/DerivationLagrangian.ipynb)

2. `Hamiltonian System`

The Hamiltonian $\mathcal{H}$ is the Legendre transformation of the Lagrangian and is given, 

$$
\mathcal{H} = \sum_{i=1}^2  \dot{\theta_i} p_{\theta_i} - \mathcal{L}
$$

Here, generalised velocities are replaced with generalised momenta and we form the equations of motion,

$$
\dot{\theta_i}=\frac{\partial \mathcal{H}}{\partial p_{\theta_i}}
$$

$$
\dot{p}_{\theta_i}=-\frac{\partial \mathcal{H}}{\partial \theta_i}
$$

Hamilton's equations are first-order and the [Python derivation](https://github.com/pineapple-bois/Double_Pendulum/blob/master/DevelopmentHamiltonian.ipynb) proved simpler than uncoupling the Euler-Lagrange equations. 

In this instance, the Hamiltonian was the first integral of the Lagrangian, representing total energy of the system. For $\textbf{q} = [\theta_1, \theta_2]$,

$$
\mathcal{H}(\mathbf{p}, \mathbf{q}) = \sum_{i=1}^2  \dot{q_i} p_{i} - \mathcal{L}(\mathbf{q}, \dot{\mathbf{q}}) \equiv T+V \equiv E_{\text{mech}}
$$

#### Solving the equations of motion

Closed-form, analytical solutions of the double pendulum system are not known to exist. The system must be integrated numerically. 

----

## The Application

This application represents a hybrid of web-development and dashboard engineering all written in Python. CSS code handles the styling of elements.

#### Main Features

- **Deriving the equations**: 
  - The equations of motion are derived symbolically with `SymPy` and abstracted as a series of [dependent functions](https://github.com/pineapple-bois/Double_Pendulum_App/blob/main/MathFunctions.py). 
  - A simple conditional logic structure controls which model is derived.
- **DoublePendulum Class**:
  - Instantiating a Lagrangian or Hamiltonian double-pendulum model object; *clicking the `Run Simulation` button*, derives the symbolic equations "on-the-fly".
  - The equations are cached to reduce runtime for further simulations of the same model.
  - The equations are numerically integrated using `SciPy`'s [solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html) function. Integrator arguments are available in the class structure but this functionality is yet to be added to the UI.
- **Visualisation**: 
  - Figures are rendered with `Plotly` and `Matplotlib`.
  - [`MathJax`](https://www.mathjax.org) API is used for rendering latex expressions.
- **Error Handling**: 
  - Robust validation of user inputs, ensures computational load is never too high.

#### Directory Structure

```
Double_Pendulum_App/
├── assets/
│   ├── Images/
│   │   ├── github-mark.png
│   │   ├── Model_Compound_Transparent_NoText.png
│   │   ├── Model_Simple_Transparent_NoText.png
│   │   ├── Models_Joint_White.png
│   │   └── Screenshot.png
│   ├── MarkdownScripts/
│   │   ├── information.txt
│   │   ├── mathematics_hamiltonian.txt
│   │   └── mathematics_lagrangian.txt
│   ├── custom-header.html
│   ├── nav-bar.js
│   ├── scroll.js
│   └── styles.css
├── layouts/
│   ├── layout_404.py
│   ├── layout_chaos.py
│   ├── layout_main.py
│   ├── layout_math.py
│   └── layout_matplotlib.py
├── src/
│   └── double_pendulum/
│       ├── math/
│       ├── models/
│       ├── plotting/
│       └── validation/
├── tests/
├── AppFunctions.py
├── DoublePendulumHamiltonian.py
├── DoublePendulumLagrangian.py
├── LICENSE.md
├── MathFunctions.py
├── ROADMAP.md
├── pendulum_app.py
├── Procfile
├── README.md
├── requirements.txt
└── .python-version
```

- For Dash applications, several key files are often required to ensure proper deployment and operation:
  - `Procfile` specifies the command to run the app.
  - `.python-version` defines the Python version for future Heroku deployment.
  - `requirements.txt` lists necessary dependencies.
  - `runtime.txt` has intentionally been removed and should not be reintroduced.
- Dash applications automatically read and serve files located in the root of the assets/ directory:
  - `custom-header.html` - Defines the page meta-data.
  - `nav-bar.js` - Script to scroll to the top of the math pages.
  - `scroll.js` - Script triggered by the "Run Simulation" button scrolls to the input/figures section of the page.
  - `styles.css` - Handles app styles such as fonts, colours, media queries, and layout structure.
- The `layouts/` directory contains a series of nested python functions that all return `dash.html.Div` objects:
  - Dash applications are designed to be single page dashboards. By abstracting the page layout as `layouts/`, the pathname is tracked by dash callbacks producing this pseudo-multi-page web application.
- The `src/double_pendulum/` package is the home for reusable simulation, symbolic math, validation, and plotting/helper logic. Root-level modules such as `AppFunctions.py`, `MathFunctions.py`, `DoublePendulumLagrangian.py`, and `DoublePendulumHamiltonian.py` remain as compatibility wrappers during the transition.

----

### Future Development

The [chaos/non-linear dynamics page](https://www.double-pendulum.net/chaos) is a work in progress. 

The active product and architecture direction is tracked in [`ROADMAP.md`](ROADMAP.md). The local `development/` directory contains exploratory/reference work for chaos features and earlier double-pendulum model development. Code from `development/` should be reviewed, tested, and migrated into the modern source layout before it becomes production app code.

Future chaos work aims to:

1. Produce a semi-structured database of angles, velocities, positions, and momenta within specified bounds using the Hamiltonian derivation.
2. Produce bifurcation diagrams, and Poincaré sections to qualitatively analyse periodicity.
3. Analyse the truncation error of the numerical integration.
4. Analyse orbits quantitatively using Lyapunov exponents.


----


### Running the App Locally

#### 1. Fork and Clone the Repository

- Fork the [Double Pendulum App repository](https://github.com/pineapple-bois/Double_Pendulum_App) on GitHub.
- Clone your forked repository:

```bash
  git clone <your-forked-repo-url>
  cd Double_Pendulum_App
```

#### 2. Set Up a Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # On macOS/Linux
.\.venv\Scripts\activate    # On Windows
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Stage For Development

- In the [`pendulum_app.py`](pendulum_app.py) file;

```python
# Comment out all below (from line 43)

@server.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
```
```python
# Optionally set debug=True below (line 320)

if __name__ == '__main__':
    app.run(debug=False)
```
#### 5. Run the Application

```bash
python pendulum_app.py
```

#### 6. Access the app at http://127.0.0.1:8050/ (The development server)

----

### Running the Test Suite

Install the app and test dependencies in the Python 3.12 virtual environment:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run the full test suite with:

```bash
python -m pytest
```

The current test layout is organized by purpose:

- `tests/unit/` covers validation and lightweight symbolic fidelity checks.
- `tests/integration/` covers app import, route layout smoke behavior, and the Flask `server` object used by Gunicorn.
- `tests/numerical/` covers basic Lagrangian and Hamiltonian simulation shape, finite values, and initial-condition consistency.

Known Phase 2 limits: these tests are a foundation, not a complete numerical validation project. Full derivation audits, compound-equation symbolic checks, energy-conservation tolerances, trajectory regression fixtures, and a Hamiltonian state/input convention audit are still future work.

----

### Project Dependencies

#### Core Libraries
- `dash`
- `dash-bootstrap-components`

#### Web Server and Framework
- `Flask`
- `gunicorn`

#### Math and Science Libraries
- `numpy`
- `scipy`
- `sympy`

#### Visualisation
- `matplotlib`
- `plotly`

The [`requirements.txt`](requirements.txt) file intentionally lists only top-level application/runtime dependencies. The old fully frozen dependency list is preserved in [`requirements-old-freeze.txt`](legacy/requirements-old-freeze.txt) for reference.

Development and test-only dependencies are listed separately in [`requirements-dev.txt`](requirements-dev.txt).

----

[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE.md) [![Pineapple Bois](https://img.shields.io/badge/Website-Pineapple_Bois-5087B2.svg?style=flat&logo=telegram)](https://pineapple-bois.github.io)

----
