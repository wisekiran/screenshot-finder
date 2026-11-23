const importForm = document.querySelector("#import-form");

if (importForm) {
    const submitButton = importForm.querySelector('button[type="submit"]');
    const statusMessage = document.querySelector("#import-status");

    importForm.addEventListener("submit", () => {
        submitButton.disabled = true;
        submitButton.textContent = "Processing screenshots…";
        importForm.setAttribute("aria-busy", "true");

        statusMessage.textContent =
            "Uploading and reading your screenshots. Keep this page open.";
    });

    window.addEventListener("pageshow", () => {
        submitButton.disabled = false;
        submitButton.textContent = "File the evidence ↗";
        importForm.removeAttribute("aria-busy");
        statusMessage.textContent = "";
    });
}