from app.content.shared import read_project_text


INFORMATION_MARKDOWN_PATH = "assets/MarkdownScripts/information.txt"
INFORMATION_TEXT = read_project_text(INFORMATION_MARKDOWN_PATH)

REPOSITORY_URL = "https://github.com/pineapple-bois/Double_Pendulum_App"


MODEL_SYSTEM_TITLE = "System"
MODEL_TYPE_OPTIONS = (
    {"label": "Simple", "value": "simple"},
    {"label": "Compound", "value": "compound"},
)
SYSTEM_TYPE_OPTIONS = (
    {"label": "Euler-Lagrange", "value": "lagrangian"},
    {"label": "Hamiltonian", "value": "hamiltonian"},
)
GRAVITY_LABEL = "Gravity"
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

PARAMETER_TITLE = "Parameters"
UNITY_PARAMETERS_BUTTON_LABEL = "Set Unity Parameters"
LENGTHS_LABEL = "Lengths"
MASSES_LABEL = "Masses"
INITIAL_CONDITIONS_TITLE = "Initial state"
INITIAL_STATE_HELP_LINES = (
    "The four initial state values define the starting configuration.",
    "Angles are measured in degrees. Positive angles rotate counterclockwise; negative angles rotate clockwise.",
    "A good first experiment is θ₁ = 0, ω₁ = 0, ω₂ = 0, then vary θ₂.",
    "Good starting values for θ₂ include 30°, 45°, 60°, 90°, 120°, and 150°.",
)
INITIAL_STATE_PRESET_LABEL = "Example state"
INITIAL_STATE_PRESET_PLACEHOLDER = "Choose a preset"
INITIAL_STATE_PRESET_OPTIONS = (
    {"label": "Simple start: θ₁ = 0, θ₂ = 60, ω₁ = 0, ω₂ = 0", "value": "simple-start"},
    {"label": "Quasi-periodic: θ₁ = 45, θ₂ = 45, ω₁ = 0, ω₂ = 0", "value": "quasi-periodic"},
    {"label": "Wide swing: θ₁ = 0, θ₂ = 120, ω₁ = 0, ω₂ = 0", "value": "wide-swing"},
    {"label": "Spirograph-like: θ₁ = 90, θ₂ = 0, ω₁ = 572.95, ω₂ = -458.37", "value": "spirograph-like"},
)
SIMULATION_INTERVAL_TITLE = "Duration (s)"

INPUT_PLACEHOLDERS = {
    "l1": "Length 1",
    "l2": "Length 2",
    "m1": "Mass 1",
    "m2": "Mass 2",
    "M1": "Mass 1",
    "M2": "Mass 2",
    "theta1": "θ1 (Angle 1)",
    "theta2": "θ2 (Angle 2)",
    "omega1": "ω1 (Angular velocity 1)",
    "omega2": "ω2 (Angular velocity 2)",
    "time_start": "Start Time",
    "time_end": "End Time",
}

RUN_SECTION_TITLE = "Run"
RUN_VALIDATION_INITIAL = "Ready once the setup is complete."
RUN_SIMULATION_LABEL = "Run simulation"
TRACE_ANIMATION_TITLE = "Trace Animation"
PHASE_PORTRAIT_TITLE = "Phase Portrait"
TIME_GRAPH_TITLE = "Time Graph"
