import { requestJSON } from './api.js';
import { showMessage, hideMessage } from './ui.js';

document.addEventListener("DOMContentLoaded", () => {
  const registroForm = document.getElementById("registroForm");

  if (registroForm) {
    registroForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideMessage("registroError");
      hideMessage("registroSuccess");

      const codigo = document.getElementById("codigo").value.trim();

      try {
        const data = await requestJSON("/public/register", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ temp_code: codigo }),
        });

        showMessage(
          "registroSuccess",
          "¡Registro exitoso! Ya estás inscrito en el proyecto.",
          "success"
        );
        // Opcional: Redirigir después de 2 segundos
        // setTimeout(() => window.location.href = "/acceso-estudiante", 2000);
      } catch (error) {
        showMessage("registroError", error.message);
      }
    });
  }
});
