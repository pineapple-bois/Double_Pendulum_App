// This function looks for the "Run Simulation" button on the page.
// Once the button is found, it adds a click event to it.
// When the button is clicked, the page scrolls smoothly to a specific section.
// If the button is not found immediately, it retries every 500ms until it appears.

function attachRunButtonEvent() {
    const runButton = document.getElementById('submit-val');
    if (runButton) {
        runButton.addEventListener('click', function () {
            const target = document.getElementById('scroll-target');
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            } else {
                console.error("Scroll target not found!");
            }
        });
    } else {
        console.log("Run Simulation button not found yet, retrying...");
        setTimeout(attachRunButtonEvent, 500); // Retry after 500ms if button is not found
    }
}

// This function initializes the home page behavior.
// It calls the function to attach the scroll functionality to the "Run Simulation" button.
// This function should be called both on the initial page load and whenever the user navigates back to the home page.

function initializeHomePage() {
    attachRunButtonEvent();
}
