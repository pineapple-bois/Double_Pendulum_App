from dataclasses import dataclass

from app.content.shared import read_project_text


INFORMATION_MARKDOWN_PATH = "assets/MarkdownScripts/information.txt"
INFORMATION_TEXT = read_project_text(INFORMATION_MARKDOWN_PATH)

GITHUB_LOGO_SRC = "assets/Images/github-mark.png"
REPOSITORY_URL = "https://github.com/pineapple-bois/Double_Pendulum_App"
REPOSITORY_LABEL = "GitHub Repository"
FOOTER_PREFIX = "The Double Pendulum application was built from this"
FOOTER_COPYRIGHT = "© pineapple-bois 2024"


@dataclass(frozen=True)
class MarkdownCopy:
    text: str


@dataclass(frozen=True)
class LinkCopy:
    text: str
    href: str


@dataclass(frozen=True)
class ModelCard:
    title: str
    markdown: str
    image_src: str
    card_class: str


DESCRIPTION_PARAGRAPHS = (
    (
        "The double pendulum is an archetypal non-linear system in classical mechanics that has "
        "been studied since the 18th century. ",
        "In this simulation, we model two types of double pendulum; simple and compound. ",
        MarkdownCopy(
            """
            Both pendulums move in the $(x,y)$-plane. The system has two degrees of freedom,
            uniquely determined by the values of $\\theta_1$ & $\\theta_2$.
            """
        ),
    ),
    (
        "Motion of a double pendulum system is characterised by extreme sensitivity to initial "
        "conditions, resulting in both periodic and chaotic behaviour. "
        "The system's equations of motion are derived using both ",
        LinkCopy("Lagrangian", "/lagrangian"),
        " and ",
        LinkCopy("Hamiltonian", "/hamiltonian"),
        " formalisms.",
        MarkdownCopy(
            """
            No closed-form solutions for $\\theta_1$ and $\\theta_2$ as
            functions of time are known. Therefore, the system must be solved numerically.
            """
        ),
    ),
    (
        "This simulation provides a rich context for exploring non-linear dynamics. "
        "We generate a time graph, phase portrait, and animation based on the selected model "
        "parameters including; mass, length, release angle, and angular velocity. "
        "Fascinating dynamics can be discovered by simply releasing the pendulums from rest. "
        "The acceleration due to gravity acts as the restoring force, influencing the oscillation "
        "period and stability of the motion. This model allows for the simulation of pendulum "
        "behaviour on different ",
        LinkCopy(
            "celestial bodies in our Solar System",
            "https://nssdc.gsfc.nasa.gov/planetary/factsheet/planet_table_ratio.html",
        ),
        ".",
    ),
)

MODEL_CARDS = (
    ModelCard(
        title="Simple Model",
        markdown=(
            "Rigid, massless, and inextensible rods $OP_1$ and $P_{1}P_{2}$ are connected by a "
            "frictionless hinge to point masses; $m_1$ & $m_2$."
        ),
        image_src="/assets/Images/Model_Simple_Transparent_NoText.png",
        card_class="simple-model",
    ),
    ModelCard(
        title="Compound Model",
        markdown=(
            "The rods are modeled as [uniform thin rods](https://phys.libretexts.org/Courses/"
            "Joliet_Junior_College/Physics_201_-_Fall_2019v2/Book%3A_Custom_Physics_textbook_for_JJC/"
            "11%3A_Rotational_Kinematics_Angular_Momentum_and_Energy/"
            "11.06%3A_Calculating_Moments_of_Inertia) of evenly distributed masses $M_1$ & $M_2$ "
            "with friction neglected at the hinge."
        ),
        image_src="/assets/Images/Model_Compound_Transparent_NoText.png",
        card_class="compound-model",
    ),
)

INFO_BUTTON_OPEN_LABEL = "What do I even choose?"
INFO_BUTTON_CLOSE_LABEL = "Close Information"
CLOSE_INFO_BUTTON_LABEL = "Close Information"

MODEL_SYSTEM_TITLE = "Model and System Selection"
MODEL_TYPE_LABEL = "Model Type:"
MODEL_TYPE_OPTIONS = (
    {"label": "Simple", "value": "simple"},
    {"label": "Compound", "value": "compound"},
)
SYSTEM_TYPE_LABEL = "System Type:"
SYSTEM_TYPE_OPTIONS = (
    {"label": "Lagrangian", "value": "lagrangian"},
    {"label": "Hamiltonian", "value": "hamiltonian"},
)
GRAVITY_LABEL = "Acceleration Due to Gravity"
GRAVITY_PLACEHOLDER = "Acceleration due to gravity, m/s²"
GRAVITY_OPTIONS = (
    {"label": "Mercury: 3.7 m/s²", "value": 3.7},
    {"label": "Venus: 8.87 m/s²", "value": 8.87},
    {"label": "Earth: 9.81 m/s²", "value": 9.81},
    {"label": "Moon: 1.62 m/s²", "value": 1.62},
    {"label": "Mars: 3.71 m/s²", "value": 3.71},
    {"label": "Jupiter: 23.15 m/s²", "value": 23.15},
    {"label": "Saturn: 10.44 m/s²", "value": 10.44},
    {"label": "Uranus: 8.69 m/s²", "value": 8.69},
    {"label": "Neptune: 11.15 m/s²", "value": 11.15},
    {"label": "Pluto: 0.696 m/s²", "value": 0.696},
)

PARAMETER_TITLE = "Parameter Selection"
UNITY_PARAMETERS_MARKDOWN = "Unity Parameters sets masses to $1 \\ \\text{kg}$ and lengths to $1 \\ \\text{m}$:"
UNITY_PARAMETERS_BUTTON_LABEL = "Set Unity Parameters"
LENGTHS_LABEL = "Lengths"
MASSES_LABEL = "Masses"
INITIAL_CONDITIONS_TITLE = "Initial Conditions"
ANGLES_LABEL = "Angles"
VELOCITIES_LABEL = "Velocities"
SIMULATION_INTERVAL_TITLE = "Simulation interval"
START_LABEL = "Start"
STOP_LABEL = "Stop"

INPUT_PLACEHOLDERS = {
    "l1": "l1 (length of rod 1)",
    "l2": "l2 (length of rod 2)",
    "m1": "m1 (mass of bob 1)",
    "m2": "m2 (mass of bob 2)",
    "M1": "M1 (mass of rod 1)",
    "M2": "M2 (mass of rod 2)",
    "theta1": "θ1 (Angle 1)",
    "theta2": "θ2 (Angle 2)",
    "omega1": "ω1 (Angular velocity 1)",
    "omega2": "ω2 (Angular velocity 2)",
    "time_start": "Start Time",
    "time_end": "End Time",
}

RUN_SIMULATION_LABEL = "RUN SIMULATION"
TRACE_ANIMATION_TITLE = "Trace Animation"
PHASE_PORTRAIT_TITLE = "Phase Portrait"
TIME_GRAPH_TITLE = "Time Graph"
