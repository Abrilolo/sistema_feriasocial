import { requestJSON } from './api.js';
import { showMessage, hideMessage } from './ui.js';

document.addEventListener("DOMContentLoaded", () => {
  const registroForm = document.getElementById("registroForm");

  if (registroForm) {
    registroForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideMessage("registroError");
      hideMessage("registroSuccess");

      const matricula = document.getElementById("matricula").value.trim();
      const email = document.getElementById("registroEmail").value.trim();
      const codigo = document.getElementById("codigo").value.trim();

      try {
        const data = await requestJSON("/public/register", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ matricula, email, temp_code: codigo }),
        });

        showMessage(
          "registroSuccess",
          JSON.stringify(data, null, 2),
          "success"
        );
      } catch (error) {
        showMessage("registroError", error.message);
      }
    });
  }
});
