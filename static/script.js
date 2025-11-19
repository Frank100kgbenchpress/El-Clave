document.addEventListener("DOMContentLoaded", () => {

    const loginForm = document.getElementById("loginForm");

    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    const usernameError = document.getElementById("usernameError");
    const passwordError = document.getElementById("passwordError");
    const generalError = document.getElementById("generalError");

    const togglePassword = document.getElementById("togglePassword");

    // Mostrar/ocultar contraseña
    togglePassword.addEventListener("click", () => {
        passwordInput.type = passwordInput.type === "password" ? "text" : "password";
    });

    function clearErrors() {
        usernameError.textContent = "";
        passwordError.textContent = "";
        generalError.textContent = "";

        usernameInput.classList.remove("error");
        passwordInput.classList.remove("error");
    }

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault(); // Evita reload del formulario
        clearErrors();

        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        let valid = true;

        if (!username) {
            usernameError.textContent = "Username is required.";
            usernameInput.classList.add("error");
            valid = false;
        }

        if (!password) {
            passwordError.textContent = "Password is required.";
            passwordInput.classList.add("error");
            valid = false;
        }

        if (!valid) return;

        // Preparar body
        const body = new URLSearchParams();
        body.append("username", username);
        body.append("password", password);

        try {
            const response = await fetch("/login", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: body.toString()
            });

            const result = await response.text();

            if (result === "OK") {
                window.location.href = "welcome.html";
            } else {
                generalError.textContent = result;
            }

        } catch (err) {
            console.error("Login error:", err);
            generalError.textContent = "Server error. Please try again.";
        }
    });
});