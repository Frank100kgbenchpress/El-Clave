document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    const logoutBtn = document.getElementById("logoutBtn");

    // --- Lógica de Login (solo si existe el formulario) ---
    if (loginForm) {
        const usernameInput = document.getElementById("username");
        const passwordInput = document.getElementById("password");
        const usernameError = document.getElementById("usernameError");
        const passwordError = document.getElementById("passwordError");
        const generalError = document.getElementById("generalError");
        const togglePassword = document.getElementById("togglePassword");

        if (togglePassword && passwordInput) {
            togglePassword.addEventListener("click", () => {
                passwordInput.type = passwordInput.type === "password" ? "text" : "password";
            });
        }

        function clearErrors() {
            usernameError.textContent = "";
            passwordError.textContent = "";
            generalError.textContent = "";
            usernameInput.classList.remove("error");
            passwordInput.classList.remove("error");
        }

        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
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
                    console.log("Login successful. Redirecting to welcome page.");
                    window.location.href = "welcome.html";
                } else {
                    console.error("Login failed:", result);
                    generalError.textContent = result;
                }
            } catch (err) {
                console.error("Login error:", err);
                generalError.textContent = "Server error. Please try again.";
            }
        });
    }

    // --- Lógica de Logout (solo si existe el botón) ---
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            try {
                const res = await fetch("/logout", { method: "POST" });
                const txt = await res.text();
                if (txt === "LOGOUT_OK") {
                    alert("Sesión cerrada");
                    window.location.href = "index.html";
                } else {
                    alert("Error al cerrar sesión: " + txt);
                }
            } catch (e) {
                alert("Error de red al cerrar sesión");
            }
        });
    }
});