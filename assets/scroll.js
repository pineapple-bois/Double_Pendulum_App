// This script waits for the DOM to fully load before starting.
// It continuously checks if the "Run Simulation" button is present on the page.
// Once the button is found, an event listener is attached to it.
// When the button is clicked, the page scrolls smoothly to a target section
// (only if the current scroll position is above the target section).

document.addEventListener('DOMContentLoaded', function () {
    const checkButtonExistence = setInterval(function() {
        const runButton = document.getElementById('submit-val');

        if (runButton) {
            runButton.addEventListener('click', function() {
                const target = document.getElementById('scroll-target');
                if (target) {
                    // Always scroll to the specific section
                    target.scrollIntoView({ behavior: 'smooth' });
                } else {
                    console.error("Scroll target not found!");
                }
            });

            clearInterval(checkButtonExistence); // Stop checking once the button is found
        } else {
            console.log("Run Simulation button not found yet, retrying...");
        }
    }, 500); // Check every 500ms
});
