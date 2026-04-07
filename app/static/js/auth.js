import { requestJSON } from './api.js';
import { showMessage, hideMessage, toastSuccess, toastError } from './ui.js';

export function saveSession(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
  localStorage.setItem("role", user.role || "");
  // Cookie ahora se configura desde el servidor con HttpOnly
  // Solo mantenemos la cookie de fallback para compatibilidad
  // SameSite=Lax protege contra CSRF básico
  const secureFlag = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `access_token=Bearer ${token}; path=/; SameSite=Lax${secureFlag}`;
}

export async function clearSession() {
  // Intentar logout en backend para limpiar cookie HttpOnly
  try {
    await fetch("/auth/logout", {
      method: "POST",
      credentials: "same-origin"
    });
  } catch (e) {
    // Silenciar error si el backend no responde
  }

  localStorage.removeItem("token");
  localStorage.removeItem("user");
  localStorage.removeItem("role");
  localStorage.removeItem("selectedProjectId");

  const secureFlag = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie =
    `access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax${secureFlag}`;
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

        // Usar login-cookie para cookie HttpOnly segura
        const loginData = await requestJSON("/auth/login-cookie", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData.toString(),
          credentials: "same-origin" // Importante para enviar/recibir cookies
        });

        const token = loginData.access_token;
        if (!token) {
          throw new Error("El backend no devolvió access_token.");
        }

        // El endpoint login-cookie ya devuelve los datos del usuario
        const meData = loginData.user || await requestJSON("/auth/me", {
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
    logoutBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      await clearSession();
      window.location.href = "/login";
    });
  }
});
