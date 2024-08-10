document.addEventListener('DOMContentLoaded', function () {
    const links = [
        { id: 'lagrangian-link', targetId: 'lagrangian-scroll-target' },
        { id: 'hamiltonian-link', targetId: 'hamiltonian-scroll-target' }
    ];

    links.forEach(link => {
        const navLink = document.getElementById(link.id);

        if (navLink) {
            navLink.addEventListener('click', function(event) {
                event.preventDefault(); // Prevent the default link behavior
                const target = document.getElementById(link.targetId);

                if (target) {
                    // Scroll to the specific section
                    target.scrollIntoView({ behavior: 'smooth' });
                } else {
                    console.error(`Scroll target ${link.targetId} not found!`);
                }
            });
        } else {
            console.error(`Navigation link ${link.id} not found!`);
        }
    });
});
