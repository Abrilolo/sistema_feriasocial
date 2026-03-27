import { requestJSON } from './api.js';
import { showMessage, hideMessage } from './ui.js';

export function saveSession(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
  localStorage.setItem("role", user.role || "");
  document.cookie = `access_token=Bearer ${token}; path=/; SameSite=Lax`;
}

export function clearSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  localStorage.removeItem("role");
  localStorage.removeItem("selectedProjectId");

  document.cookie =
    "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
}

export function redirectByRole(role) {
  if (role === "ADMIN") {
    window.location.href = "/admin-panel";
  } else if (role === "SOCIO") {
    window.location.href = "/socio";
  } else if (role === "BECARIO") {
    window.location.href = "/becario";
  } else {
    throw new Error("No se pudo detectar el rol del usuario.");
  }
}

export function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

// Global init for auth features like logout and login forms
document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  const logoutBtn = document.getElementById("logoutBtn");
  const navLogin = document.getElementById("navLogin");

  const token = localStorage.getItem("token");
  if (token) {
    if (navLogin) navLogin.style.display = "none";
    if (logoutBtn) logoutBtn.style.display = "inline-block";
  } else {
    if (navLogin) navLogin.style.display = "inline-block";
    if (logoutBtn) logoutBtn.style.display = "none";
  }

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideMessage("loginError");
      clearSession();

      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;

      try {
        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);

        const loginData = await requestJSON("/auth/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData.toString(),
        });

        const token = loginData.access_token;
        if (!token) {
          throw new Error("El backend no devolvió access_token.");
        }

        const meData = await requestJSON("/auth/me", {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        saveSession(token, meData);
        redirectByRole(meData.role);
      } catch (error) {
        clearSession();
        showMessage("loginError", error.message);
      }
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      clearSession();
      window.location.href = "/login";
    });
  }
});
