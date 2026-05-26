from dataclasses import dataclass

from app.content.routes import HAMILTONIAN_PAGE, LAGRANGIAN_PAGE
from app.content.shared import read_project_text


REFERENCES_TITLE = "References"

LAGRANGIAN_MARKDOWN_PATH = "assets/MarkdownScripts/mathematics_lagrangian.txt"
HAMILTONIAN_MARKDOWN_PATH = "assets/MarkdownScripts/mathematics_hamiltonian.txt"


@dataclass(frozen=True)
class Reference:
    text: str
    href: str


@dataclass(frozen=True)
class MathPageContent:
    title: str
    path: str
    scroll_target_id: str
    markdown_path: str
    markdown: str
    references: tuple[Reference, ...]


LAGRANGIAN_REFERENCES = (
    Reference(
        text="Massachusetts Institute of Technology: myPhysicsLab Double Pendulum",
        href="https://web.mit.edu/jorloff/www/chaosTalk/double-pendulum/double-pendulum-en.html",
    ),
    Reference(
        text="Double pendulum: Lagrangian formulation - Diego Assencio",
        href="https://dassencio.org/33",
    ),
    Reference(
        text="Lagrangian Mechanics - Wikipedia",
        href="https://en.wikipedia.org/wiki/Lagrangian_mechanics",
    ),
)

HAMILTONIAN_REFERENCES = (
    Reference(
        text="Massachusetts Institute of Technology: myPhysicsLab Double Pendulum",
        href="https://web.mit.edu/jorloff/www/chaosTalk/double-pendulum/double-pendulum-en.html",
    ),
    Reference(
        text="Double pendulum: Hamiltonian formulation - Diego Assencio",
        href="https://dassencio.org/46",
    ),
    Reference(
        text=(
            "Prof. D. Garanin, City University of New York Graduate Centre: Exercises in Classical "
            "Mechanics 1, Hamiltonian formalism"
        ),
        href="https://www.lehman.edu/faculty/dgaranin/Mechanics/ProblemSet-Fall-2006-4-Solution.pdf",
    ),
    Reference(
        text="Hamiltonian Mechanics - Wikipedia",
        href="https://en.wikipedia.org/wiki/Hamiltonian_mechanics",
    ),
)

MATH_PAGES = {
    "lagrangian": MathPageContent(
        title=LAGRANGIAN_PAGE.title,
        path=LAGRANGIAN_PAGE.path,
        scroll_target_id="lagrangian-scroll-target",
        markdown_path=LAGRANGIAN_MARKDOWN_PATH,
        markdown=read_project_text(LAGRANGIAN_MARKDOWN_PATH),
        references=LAGRANGIAN_REFERENCES,
    ),
    "hamiltonian": MathPageContent(
        title=HAMILTONIAN_PAGE.title,
        path=HAMILTONIAN_PAGE.path,
        scroll_target_id="hamiltonian-scroll-target",
        markdown_path=HAMILTONIAN_MARKDOWN_PATH,
        markdown=read_project_text(HAMILTONIAN_MARKDOWN_PATH),
        references=HAMILTONIAN_REFERENCES,
    ),
}

