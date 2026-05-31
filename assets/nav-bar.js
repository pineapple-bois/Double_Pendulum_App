document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('click', function (event) {
        const menu = event.target.closest('.site-nav-menu');

        if (event.target.closest('.site-nav-link')) {
            document.querySelectorAll('.site-nav-menu[open]').forEach(openMenu => {
                openMenu.open = false;
            });
            return;
        }

        document.querySelectorAll('.site-nav-menu[open]').forEach(openMenu => {
            if (menu !== openMenu) {
                openMenu.open = false;
            }
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') {
            return;
        }

        document.querySelectorAll('.site-nav-menu[open]').forEach(openMenu => {
            openMenu.open = false;
        });
    });

    window.addEventListener('scroll', function () {
        document.querySelectorAll('.site-nav-menu[open]').forEach(openMenu => {
            openMenu.open = false;
        });
    }, { passive: true });

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
        }
    });
});
