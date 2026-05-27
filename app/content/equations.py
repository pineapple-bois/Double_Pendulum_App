from dataclasses import dataclass

from app.content.math import HAMILTONIAN_REFERENCES, LAGRANGIAN_REFERENCES, Reference


SIMPLE_MODEL_IMAGE_SRC = "/assets/Images/Model_Simple_Transparent_NoText.png"
COMPOUND_MODEL_IMAGE_SRC = "/assets/Images/Model_Compound_Transparent_NoText.png"


@dataclass(frozen=True)
class ModelSummary:
    title: str
    image_src: str
    summary: str
    details: tuple[str, ...]


@dataclass(frozen=True)
class BranchCard:
    title: str
    href: str
    summary: str
    points: tuple[str, ...]


@dataclass(frozen=True)
class EquationBlock:
    title: str
    markdown: str
    note: str = ""
    collapsed: bool = False


@dataclass(frozen=True)
class DerivationSection:
    section_id: str
    eyebrow: str
    title: str
    lead: str
    blocks: tuple[EquationBlock, ...]


INTRODUCTION_PARAGRAPHS = (
    (
        "A double pendulum is a compact example of a classical mechanical system whose "
        "behaviour quickly becomes rich. Its configuration is determined by two angular "
        "degrees of freedom, $\\theta_1$ and $\\theta_2$, and small changes in the initial "
        "angles or angular velocities can lead to either regular motion or chaotic motion."
    ),
    (
        "The purpose of this page is to build the equations used by the numerical simulator. "
        "The derivation begins with geometry and energy, then branches into the "
        "Euler-Lagrange formulation and the Hamiltonian formulation."
    ),
    (
        "No closed-form solutions for $\\theta_1(t)$ and $\\theta_2(t)$ are known for the "
        "general double-pendulum problem, so the equations are rewritten as first-order "
        "systems and integrated numerically."
    ),
)

MECHANICAL_MODEL_LEAD = (
    "Before writing equations, we need to decide what physical object is being modelled. "
    "The app compares two idealisations of the same planar mechanism: two pendulums attached "
    "end-to-end, first as a point-mass model and then as a compound rigid-rod model."
)

MODEL_SUMMARIES = (
    ModelSummary(
        title="Simple model",
        image_src=SIMPLE_MODEL_IMAGE_SRC,
        summary=(
            "The rods are idealised as rigid, massless, and inextensible. The masses are "
            "concentrated at points $m_1$ and $m_2$"
        ),
        details=(
            "Only the point masses contribute translational kinetic energy.",
            "The rod lengths $l_1$ and $l_2$ are fixed constraints.",
        ),
    ),
    ModelSummary(
        title="Compound model",
        image_src=COMPOUND_MODEL_IMAGE_SRC,
        summary=(
            "The rods are uniform thin rods with distributed masses $M_1$ and $M_2$; hinge "
            "friction is neglected"
        ),
        details=(
            "The centre of mass of each rod contributes translational kinetic energy.",
            "Each rod also contributes rotational kinetic energy.",
            "The parallel axis theorem is used for rotation about the hinge.",
            "These inertia terms change the energy expressions and the equations of motion.",
        ),
    ),
)

SHARED_TRUNK = DerivationSection(
    section_id="shared-derivation",
    eyebrow="Shared trunk",
    title="The common Lagrangian starting point",
    lead=(
        "Both derivation branches begin with the same model setup. We first describe the "
        "planar geometry, convert that geometry into kinetic and potential energy, and then "
        "collect those energies into the Lagrangian."
    ),
    blocks=(
        EquationBlock(
            title="Physical assumptions",
            markdown=r"""
            The system consists of two pendulums attached end-to-end. Motion is restricted to the
            vertical plane, so every configuration can be described in the $(x,y)$-plane.
            
            Non-conservative forces such as air resistance and hinge friction are neglected. Under this
            idealisation the system is conservative: energy is exchanged between kinetic and potential
            forms, but the total mechanical energy is not dissipated.
            
            The two angular coordinates $\theta_1$ and $\theta_2$ determine the configuration. The derivation below 
            begins with the simple point-mass model. Once its Lagrangian has been built, the page branches into two 
            ways of obtaining equations of motion from it.
            """,
        ),
        EquationBlock(
            title="Coordinate convention",
            markdown=r"""
            The motion is planar. The origin is placed at the upper pivot, with $x$ horizontal and $y$
            vertical. The angles $\theta_1$ and $\theta_2$ are measured from the downward vertical, so
            the hanging equilibrium corresponds to $\theta_1=\theta_2=0$.
            
            Because the rod lengths are fixed, the two angles determine the full configuration of the
            simple model. Once $\theta_1(t)$ and $\theta_2(t)$ are known, the bob positions follow from
            the geometry.
            """,
        ),
        EquationBlock(
            title="Bob positions",
            markdown=r"""
            The first point mass $P_1$ is fixed at distance $l_1$ from the upper pivot. Its coordinates
            are
            
            $$
            x_1 = l_1 \sin(\theta_1(t)), \qquad
            y_1 = -l_1 \cos(\theta_1(t)).
            $$
            
            The second point mass $P_2$ is fixed at distance $l_2$ from $P_1$, so its position is built
            from the position of $P_1$ plus the displacement along the second rod:
            
            $$
            x_2 = x_1 + l_2 \sin(\theta_2(t)), \qquad
            y_2 = y_1 - l_2 \cos(\theta_2(t)).
            $$
            """,
            note=(
                "The two angles are absolute angles measured from the same downward vertical, "
                "not relative angles between the rods."
            ),
        ),
        EquationBlock(
            title="Velocities from the geometry",
            markdown=r"""
            Differentiating the coordinates gives the velocity of each mass. 
            
            For $P_1$,
            
            $$
            \dot{x}_1 = l_1\cos(\theta_1)\dot{\theta}_1, \qquad
            \dot{y}_1 = l_1\sin(\theta_1)\dot{\theta}_1,
            $$
            
            so
            
            $$
            v_1^2=\dot{x}_1^2+\dot{y}_1^2=l_1^2\dot{\theta}_1^2.
            $$
            
            For $P_2$,
            
            $$
            \dot{x}_2 = l_1\cos(\theta_1)\dot{\theta}_1
            + l_2\cos(\theta_2)\dot{\theta}_2,
            $$
            
            $$
            \dot{y}_2 = l_1\sin(\theta_1)\dot{\theta}_1
            + l_2\sin(\theta_2)\dot{\theta}_2.
            $$
            
            Collecting the squared speed gives
            
            $$
            v_2^2
            =l_1^2\dot{\theta}_1^2
            +l_2^2\dot{\theta}_2^2
            +2l_1l_2\cos(\theta_1-\theta_2)\dot{\theta}_1\dot{\theta}_2.
            $$
            """,
            note=(
                "The coupling term depends on the relative angle $\\theta_1-\\theta_2$."
            ),
        ),
        EquationBlock(
            title="Energy contribution from P1",
            markdown=r"""
            For a point mass, translational kinetic energy is
            
            $$
            T=\frac{1}{2}mv^2.
            $$
            
            Using $v_1^2=l_1^2\dot{\theta}_1^2$, the first bob contributes
            
            $$
            T_1=\frac{1}{2}m_1l_1^2\dot{\theta}_1^2.
            $$
            
            Gravitational potential energy is $V=mgy$. Since $y_1=-l_1\cos(\theta_1)$,
            
            $$
            V_1=-gm_1l_1\cos(\theta_1).
            $$
            """,
        ),
        EquationBlock(
            title="Energy contribution from P2",
            markdown=r"""
            The second bob moves because both rods move. Substituting $v_2^2$ into
            $T=\frac{1}{2}mv^2$ gives
            
            $$
            T_2=\frac{1}{2}m_2\left(
            l_1^2\dot{\theta}_1^2
            +l_2^2\dot{\theta}_2^2
            +2l_1l_2\cos(\theta_1-\theta_2)\dot{\theta}_1\dot{\theta}_2
            \right).
            $$
            
            Its vertical position is
            
            $$
            y_2=-l_1\cos(\theta_1(t))-l_2\cos(\theta_2(t)),
            $$
            
            so its gravitational potential energy is
            
            $$
            V_2=-gm_2\left(l_1\cos(\theta_1(t))+l_2\cos(\theta_2(t))\right).
            $$
            """,
        ),
        EquationBlock(
            title="Collecting total energy",
            markdown=r"""
            Adding the individual kinetic contributions gives
            
            $$
            T=T_1+T_2.
            $$
            
            After collecting terms,
            
            $$
            T = \frac{1}{2}(m_1+m_2)l_1^2\dot{\theta}_1^2
              + \frac{1}{2}m_2l_2^2\dot{\theta}_2^2
              + m_2l_1l_2\cos(\theta_1-\theta_2)\dot{\theta}_1\dot{\theta}_2.
            $$
            
            Adding the gravitational contributions gives
            
            $$
            V=V_1+V_2.
            $$
            
            After collecting terms,
            
            $$
            V = -g(m_1+m_2)l_1\cos(\theta_1) - gm_2l_2\cos(\theta_2).
            $$
            """,
            note=(
                "The cross term in $T$ is the first sign that the dynamics will not separate "
                "into two independent pendulums."
            ),
        ),
        EquationBlock(
            title="The Lagrangian as the common starting point",
            markdown=r"""
            For a conservative system, the Lagrangian is
            
            $$
            \mathcal{L}(\theta_1,\theta_2,\dot{\theta}_1,\dot{\theta}_2)=T-V.
            $$
            
            This is the common object from which both later formulations are derived. The
            Euler-Lagrange route differentiates $\mathcal{L}$ directly with respect to coordinates and
            velocities. The Hamiltonian route performs a Legendre transform and works in phase space
            using coordinates and canonical momenta. Both are different formulations of the same
            conservative model.
            
            Substituting the energies gives
            
            $$
            \mathcal{L}
            = \frac{1}{2}(m_1+m_2)l_1^2\dot{\theta}_1^2
            + \frac{1}{2}m_2l_2^2\dot{\theta}_2^2
            + m_2l_1l_2\cos(\theta_1-\theta_2)\dot{\theta}_1\dot{\theta}_2
            + g(m_1+m_2)l_1\cos(\theta_1)
            + gm_2l_2\cos(\theta_2).
            $$
            """,
            note=(
                "Everything in the branch sections starts from this same Lagrangian."
            ),
        ),
    ),
)

BRANCH_CARDS = (
    BranchCard(
        title="Euler-Lagrange formulation",
        href="#euler-lagrange-formulation",
        summary=(
            "Differentiate the Lagrangian with respect to coordinates and angular velocities."
        ),
        points=(
            "Produces coupled second-order equations in $\\theta_1$ and $\\theta_2$.",
            "Converts accelerations into a first-order simulation state using $\\omega_i$.",
        ),
    ),
    BranchCard(
        title="Hamiltonian formulation",
        href="#hamiltonian-formulation",
        summary=(
            "Introduce canonical momenta and rewrite the system in phase space."
        ),
        points=(
            "Uses the Legendre transform to replace velocities with momenta.",
            "Produces first-order equations for $(\\theta_1, \\theta_2, p_1, p_2)$.",
        ),
    ),
)

EULER_LAGRANGE_SECTION = DerivationSection(
    section_id="euler-lagrange-formulation",
    eyebrow="Branch 1",
    title="Euler-Lagrange formulation",
    lead=(
        "The Euler-Lagrange equations turn the Lagrangian into two coupled second-order "
        "equations. For numerical integration, the accelerations are then isolated and the "
        "state is rewritten using angular velocities."
    ),
    blocks=(
        EquationBlock(
            title="General Euler-Lagrange equation",
            markdown=r"""
For each generalized coordinate $\theta_i$,

$$
\frac{d}{dt}\left(\frac{\partial \mathcal{L}}{\partial \dot{\theta}_i}\right)
- \frac{\partial \mathcal{L}}{\partial \theta_i}=0.
$$
""",
        ),
        EquationBlock(
            title="Simple model equations",
            markdown=r"""
Let $\Delta=\theta_1-\theta_2$. After differentiating and simplifying,

$$
(m_1+m_2)l_1\ddot{\theta}_1
+m_2l_2\cos(\Delta)\ddot{\theta}_2
+m_2l_2\sin(\Delta)\dot{\theta}_2^2
+g(m_1+m_2)\sin(\theta_1)=0,
$$

$$
l_2\ddot{\theta}_2
+l_1\cos(\Delta)\ddot{\theta}_1
-l_1\sin(\Delta)\dot{\theta}_1^2
+g\sin(\theta_2)=0.
$$
""",
        ),
        EquationBlock(
            title="Coupled acceleration system",
            markdown=r"""
The equations can be arranged as

$$
\begin{bmatrix}
1 & \alpha_1 \\
\alpha_2 & 1
\end{bmatrix}
\begin{bmatrix}
\ddot{\theta}_1 \\
\ddot{\theta}_2
\end{bmatrix}
=
\begin{bmatrix}
f_1 \\
f_2
\end{bmatrix},
$$

where

$$
\alpha_1=\frac{m_2l_2\cos(\Delta)}{l_1(m_1+m_2)}, \qquad
\alpha_2=\frac{l_1\cos(\Delta)}{l_2},
$$

$$
f_1=\frac{g(m_1+m_2)\sin(\theta_1)+m_2l_2\sin(\Delta)\dot{\theta}_2^2}
{l_1(m_1+m_2)}, \qquad
f_2=\frac{g\sin(\theta_2)-l_1\sin(\Delta)\dot{\theta}_1^2}{l_2}.
$$
""",
            note=(
                "This matrix form keeps the coupling visible while making the numerical state "
                "update easy to implement."
            ),
        ),
        EquationBlock(
            title="First-order simulation system",
            markdown=r"""
Set $\omega_i=\dot{\theta}_i$. Then

$$
\frac{d}{dt}
\begin{bmatrix}
\theta_1 \\
\theta_2 \\
\omega_1 \\
\omega_2
\end{bmatrix}
=
\begin{bmatrix}
\omega_1 \\
\omega_2 \\
g_1(\theta_1,\theta_2,\omega_1,\omega_2) \\
g_2(\theta_1,\theta_2,\omega_1,\omega_2)
\end{bmatrix},
$$

with

$$
g_1=\frac{f_1-\alpha_1f_2}{1-\alpha_1\alpha_2}, \qquad
g_2=\frac{-\alpha_2f_1+f_2}{1-\alpha_1\alpha_2}.
$$
""",
        ),
        EquationBlock(
            title="Compound model summary",
            markdown=r"""
The same Euler-Lagrange procedure applies to the compound model, but the rods now have
distributed mass and rotational inertia. The kinetic energy therefore includes center-of-mass
translation and rod rotation:

$$
I_{\mathrm{cm}}=\frac{1}{12}Ml^2.
$$

After applying the parallel axis theorem, the final simulation state has the same shape,

$$
\frac{d}{dt}
\begin{bmatrix}
\theta_1 \\
\theta_2 \\
\omega_1 \\
\omega_2
\end{bmatrix}
=
\begin{bmatrix}
\omega_1 \\
\omega_2 \\
G_1(\theta_1,\theta_2,\omega_1,\omega_2; M_1,M_2,l_1,l_2,g) \\
G_2(\theta_1,\theta_2,\omega_1,\omega_2; M_1,M_2,l_1,l_2,g)
\end{bmatrix}.
$$
""",
            note=(
                "The page keeps the compound branch compact because its algebra follows the same "
                "method while changing the inertia terms."
            ),
        ),
    ),
)

HAMILTONIAN_SECTION = DerivationSection(
    section_id="hamiltonian-formulation",
    eyebrow="Branch 2",
    title="Hamiltonian formulation",
    lead=(
        "The Hamiltonian branch is denser algebraically, but conceptually direct: exchange "
        "angular velocities for canonical momenta, write total energy in those variables, and "
        "differentiate the Hamiltonian."
    ),
    blocks=(
        EquationBlock(
            title="Legendre transform and Hamiltonian equations",
            markdown=r"""
The Hamiltonian is the Legendre transform of the Lagrangian:

$$
\mathcal{H}=\sum_{i=1}^{2}\dot{\theta}_i p_{\theta_i}-\mathcal{L}.
$$

Hamilton's equations are

$$
\dot{\theta}_i=\frac{\partial \mathcal{H}}{\partial p_{\theta_i}}, \qquad
\dot{p}_{\theta_i}=-\frac{\partial \mathcal{H}}{\partial \theta_i}.
$$
""",
        ),
        EquationBlock(
            title="Canonical momenta",
            markdown=r"""
The canonical momenta are

$$
p_{\theta_1}=(m_1+m_2)l_1^2\dot{\theta}_1
+m_2l_1l_2\cos(\Delta)\dot{\theta}_2,
$$

$$
p_{\theta_2}=m_2l_1l_2\cos(\Delta)\dot{\theta}_1
+m_2l_2^2\dot{\theta}_2.
$$
""",
        ),
        EquationBlock(
            title="Momentum matrix",
            markdown=r"""
The momenta can be written as

$$
\begin{bmatrix}
p_{\theta_1} \\
p_{\theta_2}
\end{bmatrix}
=
\mathbf{B}
\begin{bmatrix}
\dot{\theta}_1 \\
\dot{\theta}_2
\end{bmatrix},
$$

where

$$
\mathbf{B}=
\begin{bmatrix}
(m_1+m_2)l_1^2 & m_2l_1l_2\cos(\Delta) \\
m_2l_1l_2\cos(\Delta) & m_2l_2^2
\end{bmatrix}.
$$
""",
            note=(
                "The symmetric matrix $\\mathbf{B}$ is the angle-dependent inertia matrix."
            ),
        ),
        EquationBlock(
            title="Velocities in terms of momenta",
            markdown=r"""
Since $\mathbf{B}$ is invertible for positive masses and lengths,

$$
\begin{bmatrix}
\dot{\theta}_1 \\
\dot{\theta}_2
\end{bmatrix}
=
\mathbf{B}^{-1}
\begin{bmatrix}
p_{\theta_1} \\
p_{\theta_2}
\end{bmatrix}.
$$

Explicitly,

$$
\dot{\theta}_1 =
\frac{-l_1p_{\theta_2}\cos(\Delta)+l_2p_{\theta_1}}
{l_1^2l_2\left(m_1+m_2\sin^2(\Delta)\right)},
$$

$$
\dot{\theta}_2 =
\frac{l_1(m_1+m_2)p_{\theta_2}-l_2m_2p_{\theta_1}\cos(\Delta)}
{l_1l_2^2m_2\left(m_1+m_2\sin^2(\Delta)\right)}.
$$
""",
        ),
        EquationBlock(
            title="Hamiltonian and first-order system",
            markdown=r"""
The simple-model Hamiltonian can be written as

$$
\mathcal{H}
=\frac{
l_1^2(m_1+m_2)p_{\theta_2}^2
-2l_1l_2m_2p_{\theta_1}p_{\theta_2}\cos(\Delta)
+l_2^2m_2p_{\theta_1}^2}
{2l_1^2l_2^2m_2\left(m_1+m_2\sin^2(\Delta)\right)}
-g\left((m_1+m_2)l_1\cos(\theta_1)+m_2l_2\cos(\theta_2)\right).
$$

The final state is already first order:

$$
\frac{d}{dt}
\begin{bmatrix}
\theta_1 \\
\theta_2 \\
p_{\theta_1} \\
p_{\theta_2}
\end{bmatrix}
=
\begin{bmatrix}
\partial\mathcal{H}/\partial p_{\theta_1} \\
\partial\mathcal{H}/\partial p_{\theta_2} \\
-\partial\mathcal{H}/\partial \theta_1 \\
-\partial\mathcal{H}/\partial \theta_2
\end{bmatrix}.
$$
""",
        ),
        EquationBlock(
            title="Compound model summary",
            markdown=r"""
For the compound model, the momentum relation keeps the same matrix form,

$$
\begin{bmatrix}
p_{\theta_1} \\
p_{\theta_2}
\end{bmatrix}
=
\mathbf{B}_c
\begin{bmatrix}
\dot{\theta}_1 \\
\dot{\theta}_2
\end{bmatrix},
$$

with

$$
\mathbf{B}_c=
\begin{bmatrix}
\left(\frac{7M_1}{12}+\frac{M_2}{4}\right)l_1^2
& \frac{M_2l_1l_2\cos(\Delta)}{4} \\
\frac{M_2l_1l_2\cos(\Delta)}{4}
& \frac{7M_2l_2^2}{12}
\end{bmatrix}.
$$

The Hamiltonian is then formed by the same energy expression,

$$
\mathcal{H}_c
=\frac{1}{2}
\begin{bmatrix}
p_{\theta_1} & p_{\theta_2}
\end{bmatrix}
\mathbf{B}_c^{-1}
\begin{bmatrix}
p_{\theta_1} \\
p_{\theta_2}
\end{bmatrix}
-\frac{g}{2}\left(M_1l_1\cos(\theta_1)+M_2l_1\cos(\theta_1)+M_2l_2\cos(\theta_2)\right).
$$

Its simulation system is

$$
\frac{d}{dt}
\begin{bmatrix}
\theta_1 \\
\theta_2 \\
p_{\theta_1} \\
p_{\theta_2}
\end{bmatrix}
=
\begin{bmatrix}
\partial\mathcal{H}_c/\partial p_{\theta_1} \\
\partial\mathcal{H}_c/\partial p_{\theta_2} \\
-\partial\mathcal{H}_c/\partial \theta_1 \\
-\partial\mathcal{H}_c/\partial \theta_2
\end{bmatrix}.
$$
""",
            note=(
                "The distributed rod mass changes the inertia matrix and Hamiltonian, while the "
                "canonical first-order structure remains the same."
            ),
        ),
    ),
)

DERIVATION_SECTIONS = (
    SHARED_TRUNK,
    EULER_LAGRANGE_SECTION,
    HAMILTONIAN_SECTION,
)

EQUATIONS_REFERENCES = tuple(
    dict.fromkeys(
        LAGRANGIAN_REFERENCES
        + HAMILTONIAN_REFERENCES
        + (
            Reference(
                text="Double pendulum derivation notebooks - pineapple-bois",
                href="https://github.com/pineapple-bois/Double_Pendulum",
            ),
        )
    )
)
