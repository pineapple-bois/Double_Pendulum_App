from dataclasses import dataclass


HERO_IMAGE_SRC = "/assets/Heros/double_pend_hero1_navy.png"
GITHUB_LOGO_SRC = "/assets/Images/github-mark.png"
REPOSITORY_URL = "https://github.com/pineapple-bois/Double_Pendulum_App"
REPOSITORY_LABEL = "pineapple-bois/Double_Pendulum_App"
ATTRIBUTION_LABEL = "pineapple-bois"
HOME_TITLE = "Double Pendulum Explorer"
HOME_INTRODUCTION = (
    "A double pendulum looks simple: two links, two angles, and gravity. "
    "Its motion is anything but simple."
)
HOME_CONTEXT_NOTE = (
    "From this simple model, explore equations of motion, numerical methods, "
    "phase portraits, and the onset of chaos."
)


@dataclass(frozen=True)
class ExploreLink:
    title: str
    href: str
    description: str


@dataclass(frozen=True)
class ReadingItem:
    reference: str
    href: str
    role: str


EXPLORE_LINKS = (
    ExploreLink(
        title="Equations of Motion",
        href="/equations",
        description="Compare the Euler-Lagrange and Hamiltonian routes from one shared derivation.",
    ),
    ExploreLink(
        title="Simulation",
        href="/simulation",
        description="Set parameters, run the model, and inspect motion, phase, and time plots.",
    ),
    ExploreLink(
        title="Chaos",
        href="/chaos",
        description="Connect sensitivity to initial conditions with broader nonlinear behaviour.",
    ),
)

FURTHER_READING = (
    ReadingItem(
        reference=(
            "Strogatz, S. H. Nonlinear Dynamics and Chaos: With Applications to "
            "Physics, Biology, Chemistry, and Engineering."
        ),
        href="https://www.taylorfrancis.com/books/mono/10.1201/9780429398490/nonlinear-dynamics-chaos-steven-strogatz",
        role="A clear route into phase portraits, bifurcation, sensitivity, and chaos.",
    ),
    ReadingItem(
        reference="Gleick, J. (1997). Chaos. Vintage.",
        href="https://www.penguin.co.uk/books/369228/chaos-by-gleickjames/9780749386061",
        role=(
            "Accessible background reading on the history and development of "
            "nonlinear dynamics and chaos."
        ),
    ),
)
