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
        "The Euler-Lagrange formulation works directly with the shared Lagrangian. It produces "
        "two coupled second-order equations for the angular coordinates, then rewrites them as "
        "a first-order system for numerical integration."
    ),
    blocks=(
        EquationBlock(
            title="General Euler-Lagrange equation",
            markdown=r"""
            For each generalized coordinate $\theta_i$,
            
            $$
            \frac{\mathrm{d}}{\mathrm{d}t}
            \left(\frac{\partial \mathcal{L}}{\partial \dot{\theta}_i}\right)
            - \frac{\partial \mathcal{L}}{\partial \theta_i}=0.
            $$
            
            The partial derivatives treat $\theta_i$ and $\dot{\theta}_i$ as independent variables.
            The outer total time derivative then accounts for how
            $\partial\mathcal{L}/\partial\dot{\theta}_i$ changes along the actual motion.
            """,
        ),
        EquationBlock(
            title="Applying the operator to two coordinates",
            markdown=r"""
            For the double pendulum, the generalized coordinate vector is
            
            $$
            \mathbf{q}=(\theta_1,\theta_2).
            $$
            
            Applying the Euler-Lagrange operator separately gives two equations:
            
            $$
            \frac{\mathrm{d}}{\mathrm{d}t}
            \left(\frac{\partial \mathcal{L}}{\partial \dot{\theta}_1}\right)
            -\frac{\partial \mathcal{L}}{\partial \theta_1}=0,
            $$
            
            $$
            \frac{\mathrm{d}}{\mathrm{d}t}
            \left(\frac{\partial \mathcal{L}}{\partial \dot{\theta}_2}\right)
            -\frac{\partial \mathcal{L}}{\partial \theta_2}=0.
            $$
            
            Because the Lagrangian contains both $\dot{\theta}_1$ and $\dot{\theta}_2$ in a shared
            kinetic-energy term, these equations contain both angular accelerations. They are therefore
            coupled second-order equations rather than two independent pendulum equations.
            """,
        ),
        EquationBlock(
            title="Where the coupling enters",
            markdown=r"""
            The coupling comes from the kinetic-energy cross term in the shared Lagrangian:
            
            $$
            m_2l_1l_2\cos(\theta_1-\theta_2)\dot{\theta}_1\dot{\theta}_2.
            $$
            
            Differentiating this term contributes factors of $\cos(\theta_1-\theta_2)$ multiplying
            angular accelerations, and factors of $\sin(\theta_1-\theta_2)$ multiplying squared angular
            velocities. This is why the acceleration of one link appears in the equation for the other.
            """,
            note=(
                "The coupling depends on the relative angle $\\theta_1-\\theta_2$, even though "
                "the coordinates themselves are absolute angles measured from the vertical."
            ),
        ),
        EquationBlock(
            title="Coupled second-order equations for the simple model",
            markdown=r"""
            Let $\Delta=\theta_1-\theta_2$. Applying the Euler-Lagrange operator to the simple-model
            Lagrangian gives
            
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
            
            These are second-order because they contain $\ddot{\theta}_1$ and $\ddot{\theta}_2$.
            They are coupled because each equation contains the acceleration of the other coordinate.
            """,
        ),
        EquationBlock(
            title="Isolating the angular accelerations",
            markdown=r"""
            To solve numerically, the angular accelerations need to be isolated. Here the non-acceleration
            terms are moved to the right-hand side. With this sign convention,
            
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
            b_1 \\
            b_2
            \end{bmatrix},
            $$
            
            with
            
            $$
            \alpha_1=\frac{m_2l_2\cos(\Delta)}{l_1(m_1+m_2)}, \qquad
            \alpha_2=\frac{l_1\cos(\Delta)}{l_2},
            $$
            
            $$
            b_1=-\frac{g(m_1+m_2)\sin(\theta_1)+m_2l_2\sin(\Delta)\dot{\theta}_2^2}
            {l_1(m_1+m_2)},
            $$
            
            $$
            b_2=\frac{l_1\sin(\Delta)\dot{\theta}_1^2-g\sin(\theta_2)}{l_2}.
            $$
            
            Solving the $2\times2$ linear system gives
            
            $$
            \ddot{\theta}_1=\frac{b_1-\alpha_1b_2}{1-\alpha_1\alpha_2}, \qquad
            \ddot{\theta}_2=\frac{-\alpha_2b_1+b_2}{1-\alpha_1\alpha_2}.
            $$
            """,
            note=(
                "The signs of $b_1$ and $b_2$ come from moving every non-acceleration term "
                "to the right-hand side before inverting the acceleration matrix."
            ),
        ),
        EquationBlock(
            title="First-order simulation system",
            markdown=r"""
            Most numerical ODE solvers expect a first-order system. Introduce angular velocities
            
            $$
            \omega_i=\dot{\theta}_i.
            $$
            
            Then the simple-model Euler-Lagrange system becomes
            
            $$
            \frac{\mathrm{d}}{\mathrm{d}t}
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
            \dfrac{b_1-\alpha_1b_2}{1-\alpha_1\alpha_2} \\
            \dfrac{-\alpha_2b_1+b_2}{1-\alpha_1\alpha_2}
            \end{bmatrix}.
            $$
            """,
            note=(
                "This first-order form is the version used by numerical ODE solvers."
            ),
        ),
        EquationBlock(
            title="Compound model mechanics",
            markdown=r"""
            The compound model changes the energy terms, not the variational principle. The rods have
            distributed mass, so each rod contributes translational kinetic energy through its centre of
            mass and rotational kinetic energy about its own centre of mass.
            
            For a uniform thin rod,
            
            $$
            I_{\mathrm{cm}}=\frac{1}{12}Ml^2.
            $$
            
            Rotation about an end uses the parallel axis theorem:
            
            $$
            I_{\mathrm{end}}
            =I_{\mathrm{cm}}+M\left(\frac{l}{2}\right)^2
            =\frac{1}{3}Ml^2.
            $$
            
            The rotational kinetic energy of each rod is
            
            $$
            T_{\mathrm{rot}}=\frac{1}{2}I_{\mathrm{end}}\omega^2.
            $$
            """,
        ),
        EquationBlock(
            title="Compound-model Lagrangian",
            markdown=r"""
            Combining centre-of-mass translation, rotational kinetic energy, and gravitational potential
            energy gives the uniform-rod compound Lagrangian:
            
            $$
            \mathcal{L}_{\mathrm{c}}
            =\frac{7M_1l_1^2\dot{\theta}_1^2}{24}
            +\frac{M_2l_1^2\dot{\theta}_1^2}{8}
            +\frac{M_2l_1l_2\cos(\Delta)\dot{\theta}_1\dot{\theta}_2}{4}
            +\frac{7M_2l_2^2\dot{\theta}_2^2}{24}
            +\frac{g}{2}\left(M_1l_1\cos(\theta_1)+M_2l_1\cos(\theta_1)+M_2l_2\cos(\theta_2)\right).
            $$
            
            The coefficients differ from the simple model because mass is distributed along the rods
            instead of being concentrated only at the endpoints.
            """,
        ),
        EquationBlock(
            title="Compound-model Euler-Lagrange equations",
            markdown=r"""
            Applying the same Euler-Lagrange operator to $\mathcal{L}_{\mathrm{c}}$ gives
            
            $$
            (7M_1+3M_2)l_1\ddot{\theta}_1
            +3M_2l_2\cos(\Delta)\ddot{\theta}_2
            +6(M_1+M_2)g\sin(\theta_1)
            +3M_2l_2\sin(\Delta)\dot{\theta}_2^2=0,
            $$
            
            $$
            7l_2\ddot{\theta}_2
            +3l_1\cos(\Delta)\ddot{\theta}_1
            -3l_1\sin(\Delta)\dot{\theta}_1^2
            +6g\sin(\theta_2)=0.
            $$
            
            With non-acceleration terms moved to the right-hand side, the same matrix pattern appears:
            
            $$
            \begin{bmatrix}
            1 & \beta_1 \\
            \beta_2 & 1
            \end{bmatrix}
            \begin{bmatrix}
            \ddot{\theta}_1 \\
            \ddot{\theta}_2
            \end{bmatrix}
            =
            \begin{bmatrix}
            c_1 \\
            c_2
            \end{bmatrix},
            $$
            
            where
            
            $$
            \beta_1=\frac{3M_2l_2\cos(\Delta)}{l_1(7M_1+3M_2)}, \qquad
            \beta_2=\frac{3l_1\cos(\Delta)}{7l_2},
            $$
            
            $$
            c_1=-\frac{6(M_1+M_2)g\sin(\theta_1)+3M_2l_2\sin(\Delta)\dot{\theta}_2^2}
            {l_1(7M_1+3M_2)},
            $$
            
            $$
            c_2=\frac{3l_1\sin(\Delta)\dot{\theta}_1^2-6g\sin(\theta_2)}{7l_2}.
            $$
            """,
            note=(
                "The compound model has different inertia coefficients, but it is governed by "
                "the same Euler-Lagrange principle."
            ),
        ),
    ),
)

HAMILTONIAN_SECTION = DerivationSection(
    section_id="hamiltonian-formulation",
    eyebrow="Branch 2",
    title="Hamiltonian formulation",
    lead=(
        "The Hamiltonian formulation starts from the same Lagrangian, but changes variables. "
        "Instead of evolving angular velocities directly, it introduces canonical momenta and "
        "writes the dynamics as a first-order system in phase space."
    ),
    blocks=(
        EquationBlock(
            title="Why introduce momenta?",
            markdown=r"""
            The Euler-Lagrange branch works with coordinates and velocities. The Hamiltonian branch
            uses coordinates and canonical momenta:
            
            $$
            (\theta_1,\theta_2,\dot{\theta}_1,\dot{\theta}_2)
            \quad\longrightarrow\quad
            (\theta_1,\theta_2,p_{\theta_1},p_{\theta_2}).
            $$
            
            For a double pendulum, these momenta are not simply independent $mv$ terms. The kinetic
            energy is coupled, so the momentum associated with one angle can depend on both angular
            velocities.
            """,
            note=(
                "The Euler-Lagrange and Hamiltonian branches describe the same conservative system."
            ),
        ),
        EquationBlock(
            title="Canonical momenta",
            markdown=r"""
            The canonical momentum conjugate to each angular coordinate is defined by
            
            $$
            p_{\theta_i}=\frac{\partial \mathcal{L}}{\partial \dot{\theta}_i}.
            $$
            
            Applying this definition to the simple-model Lagrangian gives
            
            $$
            p_{\theta_1}=(m_1+m_2)l_1^2\dot{\theta}_1
            +m_2l_1l_2\cos(\Delta)\dot{\theta}_2,
            $$
            
            $$
            p_{\theta_2}=m_2l_1l_2\cos(\Delta)\dot{\theta}_1
            +m_2l_2^2\dot{\theta}_2.
            $$
            
            The cross terms come from differentiating the kinetic-energy coupling term. This is why
            $p_{\theta_1}$ and $p_{\theta_2}$ each contain information about both angular velocities.
            """,
            note="Canonical momenta are coupled because the kinetic energy is coupled.",
        ),
        EquationBlock(
            title="Momentum matrix for the simple model",
            markdown=r"""
            The two momentum equations can be collected into a matrix relation:
            
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
            
            where the symmetric matrix $\mathbf{B}$ is the configuration-dependent inertia matrix:
            
            $$
            \mathbf{B}=
            \begin{bmatrix}
            (m_1+m_2)l_1^2 & m_2l_1l_2\cos(\Delta) \\
            m_2l_1l_2\cos(\Delta) & m_2l_2^2
            \end{bmatrix}.
            $$
            
            The entries of $\mathbf{B}$ depend on the current configuration through
            $\Delta=\theta_1-\theta_2$. In compact form, the simple-model kinetic energy is
            
            $$
            T=\frac{1}{2}
            \begin{bmatrix}
            \dot{\theta}_1 & \dot{\theta}_2
            \end{bmatrix}
            \mathbf{B}
            \begin{bmatrix}
            \dot{\theta}_1 \\
            \dot{\theta}_2
            \end{bmatrix}.
            $$
            """,
        ),
        EquationBlock(
            title="Recovering velocities from momenta",
            markdown=r"""
            The Hamiltonian must be written in terms of coordinates and momenta, not velocities.
            That is why the momentum matrix must be inverted:
            
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
            
            For positive masses and lengths, this matrix is invertible. The angular velocities are
            
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
            
            These expressions are the first two Hamiltonian equations in explicit form: they recover
            the angular velocities from the phase-space variables.
            """,
        ),
        EquationBlock(
            title="Legendre transform",
            markdown=r"""
            The Legendre transform replaces the velocity description with the momentum description:
            
            $$
            \mathcal{H}
            =\sum_{i=1}^{2}\dot{\theta}_i p_{\theta_i}-\mathcal{L}.
            $$
            
            Because the simple and compound systems are conservative and their Lagrangians do not
            depend explicitly on time, this Hamiltonian is the total mechanical energy expressed in
            phase-space variables.
            """,
        ),
        EquationBlock(
            title="Hamiltonian as total energy",
            markdown=r"""
            Using the inverse momentum matrix, the kinetic energy can be written as
            
            $$
            T=\frac{1}{2}
            \begin{bmatrix}
            p_{\theta_1} & p_{\theta_2}
            \end{bmatrix}
            \mathbf{B}^{-1}
            \begin{bmatrix}
            p_{\theta_1} \\
            p_{\theta_2}
            \end{bmatrix}.
            $$
            
            For the simple model, the Hamiltonian becomes
            
            $$
            \mathcal{H}
            =\frac{
            l_1^2(m_1+m_2)p_{\theta_2}^2
            -2l_1l_2m_2p_{\theta_1}p_{\theta_2}\cos(\Delta)
            +l_2^2m_2p_{\theta_1}^2}
            {2l_1^2l_2^2m_2\left(m_1+m_2\sin^2(\Delta)\right)}
            -g\left((m_1+m_2)l_1\cos(\theta_1)+m_2l_2\cos(\theta_2)\right).
            $$
            
            This is the same total energy $T+V$, but now written using
            $(\theta_1,\theta_2,p_{\theta_1},p_{\theta_2})$ instead of
            $(\theta_1,\theta_2,\dot{\theta}_1,\dot{\theta}_2)$.
            """,
        ),
        EquationBlock(
            title="Hamilton's equations",
            markdown=r"""
            Hamilton's equations specify how each phase-space variable evolves:
            
            $$
            \dot{\theta}_i=\frac{\partial \mathcal{H}}{\partial p_{\theta_i}},
            \qquad
            \dot{p}_{\theta_i}=-\frac{\partial \mathcal{H}}{\partial \theta_i}.
            $$
            
            Unlike the Euler-Lagrange equations, which first appear as second-order equations in
            $\theta_1$ and $\theta_2$, Hamilton's equations are first-order by construction.
            """,
            note="Hamilton's equations are first-order by construction.",
        ),
        EquationBlock(
            title="First-order phase-space system",
            markdown=r"""
            For the simple model, the simulation state is
            
            $$
            \mathbf{y}=
            \begin{bmatrix}
            \theta_1 & \theta_2 & p_{\theta_1} & p_{\theta_2}
            \end{bmatrix}^{T}.
            $$
            
            The evolution law is
            
            $$
            \frac{\mathrm{d}}{\mathrm{d}t}
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
            
            The first two components are the velocity formulas obtained from $\mathbf{B}^{-1}$.
            The last two components give the momentum evolution from the position derivatives of
            the Hamiltonian.
            """,
        ),
        EquationBlock(
            title="Compound-model momentum matrix",
            markdown=r"""
            The compound model uses the same canonical construction, but the distributed rod mass
            changes the inertia matrix. Differentiating the compound Lagrangian with respect to the
            angular velocities gives
            
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
            
            with the compound momentum matrix
            
            $$
            \mathbf{B}_c=
            \begin{bmatrix}
            \left(\frac{7M_1}{12}+\frac{M_2}{4}\right)l_1^2
            & \frac{M_2l_1l_2\cos(\Delta)}{4} \\
            \frac{M_2l_1l_2\cos(\Delta)}{4}
            & \frac{7M_2l_2^2}{12}
            \end{bmatrix}.
            $$
            
            The diagonal coefficients include each rod's centre-of-mass translation and rotational
            inertia. The off-diagonal terms still depend on $\cos(\Delta)$, so the two generalized
            momenta remain coupled.
            """,
        ),
        EquationBlock(
            title="Compound Hamiltonian system",
            markdown=r"""
            The compound Hamiltonian is formed by using the inverse compound inertia matrix:
            
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
            
            Equivalently, expanding the inverse matrix gives
            
            $$
            \mathcal{H}_c
            =\frac{
            6\left[
            7M_1l_1^2p_{\theta_2}^2
             +3M_2l_1^2p_{\theta_2}^2
             -6M_2l_1l_2p_{\theta_1}p_{\theta_2}\cos(\Delta)
             +7M_2l_2^2p_{\theta_1}^2
            \right]}
            {M_2l_1^2l_2^2\left(49M_1+9M_2\sin^2(\Delta)+12M_2\right)}
            -\frac{g}{2}\left((M_1+M_2)l_1\cos(\theta_1)+M_2l_2\cos(\theta_2)\right).
            $$
            
            The first two Hamiltonian equations recover the angular velocities:
            
            $$
            \dot{\theta}_1=
            \frac{12\left(-3l_1p_{\theta_2}\cos(\Delta)+7l_2p_{\theta_1}\right)}
            {l_1^2l_2\left(49M_1+9M_2\sin^2(\Delta)+12M_2\right)},
            $$
            
            $$
            \dot{\theta}_2=
            \frac{12\left(l_1(7M_1+3M_2)p_{\theta_2}
            -3M_2l_2p_{\theta_1}\cos(\Delta)\right)}
            {M_2l_1l_2^2\left(49M_1+9M_2\sin^2(\Delta)+12M_2\right)}.
            $$
            
            The complete compound phase-space system is
            
            $$
            \frac{\mathrm{d}}{\mathrm{d}t}
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
                "The distributed rod mass changes the inertia matrix and Hamiltonian, while "
                "the canonical first-order structure remains the same."
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
