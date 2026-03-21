async function requestJSON(url, options = {}) {
  const response = await fetch(url, options);

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = data?.detail || data || "Error en la solicitud";
    throw new Error(detail);
  }

  return data;
}

function showMessage(elementId, message, type = "error") {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.style.display = "block";
  el.textContent =
    typeof message === "string" ? message : JSON.stringify(message, null, 2);

  el.className = type === "success" ? "success" : "error";
}

function hideMessage(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.style.display = "none";
  el.textContent = "";
}

function saveSession(token, user) {
  localStorage.setItem("token", token);
  localStorage.setItem("user", JSON.stringify(user));
  localStorage.setItem("role", user.role || "");
  document.cookie = `access_token=Bearer ${token}; path=/; SameSite=Lax`;
}

function clearSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  localStorage.removeItem("role");
  localStorage.removeItem("selectedProjectId");

  document.cookie =
    "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
}

function redirectByRole(role) {
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

function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

function formatDate(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return isNaN(date.getTime()) ? isoString : date.toLocaleString();
}

function badgeLabel(value, trueText = "Sí", falseText = "No") {
  if (value) {
    return `<span class="badge badge-ok">${trueText}</span>`;
  }
  return `<span class="badge badge-off">${falseText}</span>`;
}

async function loadSocioProjects() {
  const container = document.getElementById("projectsContainer");
  if (!container) return;

  hideMessage("projectsError");
  container.innerHTML = "<p>Cargando proyectos...</p>";

  try {
    const data = await requestJSON("/socio/projects", {
      method: "GET",
      headers: {
        ...getAuthHeaders(),
      },
    });

    const projects = data.projects || [];

    if (projects.length === 0) {
      container.innerHTML = "<p>No tienes proyectos asignados.</p>";
      return;
    }

    container.innerHTML = projects
      .map(
        (project) => `
          <div class="project-card">
            <h3>${project.name}</h3>
            <p>${project.description || "Sin descripción"}</p>
            <p><strong>Capacidad:</strong> ${project.capacity}</p>
            <p><strong>Ocupados:</strong> ${project.taken_slots}</p>
            <p><strong>Disponibles:</strong> ${project.remaining_slots}</p>
            <p><strong>Códigos activos:</strong> ${project.active_codes}</p>
            <p><strong>Estado:</strong> ${
              project.is_active
                ? '<span class="badge badge-ok">Activo</span>'
                : '<span class="badge badge-off">Inactivo</span>'
            }</p>
            <div class="actions">
              <button type="button" class="open-project-btn" data-project-id="${project.id}">
                Ver detalle
              </button>
            </div>
          </div>
        `
      )
      .join("");

    document.querySelectorAll(".open-project-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const projectId = btn.dataset.projectId;
        localStorage.setItem("selectedProjectId", projectId);
        await loadSocioProjectDetail(projectId);
        await loadSocioCodes(projectId);
        await loadSocioStudents(projectId);
      });
    });
  } catch (error) {
    container.innerHTML = "";
    showMessage("projectsError", error.message);
  }
}

async function loadSocioProjectDetail(projectId) {
  hideMessage("detailError");

  try {
    const data = await requestJSON(`/socio/projects/${projectId}`, {
      method: "GET",
      headers: {
        ...getAuthHeaders(),
      },
    });

    const project = data.project;
    document.getElementById("projectDetailPanel").style.display = "block";
    document.getElementById("generateCodePanel").style.display = "block";
    document.getElementById("codesPanel").style.display = "block";
    document.getElementById("studentsPanel").style.display = "block";

    document.getElementById("detailProjectName").textContent = project.name || "Proyecto";
    document.getElementById("detailProjectDescription").textContent =
      project.description || "Sin descripción";

    document.getElementById("statCapacity").textContent = project.capacity ?? 0;
    document.getElementById("statTaken").textContent =
      project.taken_slots ?? project.taken_slots_query ?? 0;
    document.getElementById("statRemaining").textContent = project.remaining_slots ?? 0;
    document.getElementById("statActiveCodes").textContent = project.active_codes ?? 0;
    document.getElementById("statUsedCodes").textContent = project.used_codes ?? 0;
    document.getElementById("statExpiredCodes").textContent = project.expired_codes ?? 0;
  } catch (error) {
    showMessage("detailError", error.message);
  }
}

async function generateSocioCode(projectId) {
  hideMessage("generateCodeError");
  hideMessage("generateCodeSuccess");

  const expiresInMinutes = Number(document.getElementById("expiresInMinutes").value);

  try {
    const data = await requestJSON("/socio/temp-codes", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        project_id: projectId,
        expires_in_minutes: expiresInMinutes,
      }),
    });

    const code = data.temp_code?.code || "-";
    const expiresAt = formatDate(data.temp_code?.expires_at);

    showMessage(
      "generateCodeSuccess",
      `Código generado: ${code} | Expira: ${expiresAt}`,
      "success"
    );

    await loadSocioProjectDetail(projectId);
    await loadSocioCodes(projectId);
  } catch (error) {
    showMessage("generateCodeError", error.message);
  }
}

async function loadSocioCodes(projectId) {
  const tbody = document.getElementById("codesTableBody");
  if (!tbody) return;

  hideMessage("codesError");
  tbody.innerHTML = `<tr><td colspan="6">Cargando códigos...</td></tr>`;

  try {
    const data = await requestJSON(`/socio/projects/${projectId}/codes`, {
      method: "GET",
      headers: {
        ...getAuthHeaders(),
      },
    });

    const codes = data.codes || [];

    if (codes.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6">No hay códigos para este proyecto.</td></tr>`;
      return;
    }

    tbody.innerHTML = codes
      .map(
        (code) => `
          <tr>
            <td><strong>${code.code}</strong></td>
            <td>${badgeLabel(code.is_active, "Sí", "No")}</td>
            <td>${badgeLabel(code.is_used, "Sí", "No")}</td>
            <td>${
              code.is_expired
                ? '<span class="badge badge-warn">Sí</span>'
                : '<span class="badge badge-ok">No</span>'
            }</td>
            <td>${formatDate(code.expires_at)}</td>
            <td>
              ${
                code.is_active && !code.is_used
                  ? `<button type="button" class="deactivate-code-btn" data-code-id="${code.id}">Desactivar</button>`
                  : "-"
              }
            </td>
          </tr>
        `
      )
      .join("");

    document.querySelectorAll(".deactivate-code-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const codeId = btn.dataset.codeId;
        await deactivateSocioCode(codeId, projectId);
      });
    });
  } catch (error) {
    tbody.innerHTML = "";
    showMessage("codesError", error.message);
  }
}

async function deactivateSocioCode(tempCodeId, projectId) {
  hideMessage("codesError");

  try {
    await requestJSON(`/socio/temp-codes/${tempCodeId}/deactivate`, {
      method: "PATCH",
      headers: {
        ...getAuthHeaders(),
      },
    });

    await loadSocioProjectDetail(projectId);
    await loadSocioCodes(projectId);
  } catch (error) {
    showMessage("codesError", error.message);
  }
}

async function loadSocioStudents(projectId) {
  const tbody = document.getElementById("studentsTableBody");
  if (!tbody) return;

  hideMessage("studentsError");
  tbody.innerHTML = `<tr><td colspan="5">Cargando estudiantes...</td></tr>`;

  try {
    const data = await requestJSON(`/socio/projects/${projectId}/students`, {
      method: "GET",
      headers: {
        ...getAuthHeaders(),
      },
    });

    const students = data.students || [];

    if (students.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5">No hay estudiantes registrados.</td></tr>`;
      return;
    }

    tbody.innerHTML = students
      .map(
        (student) => `
          <tr>
            <td>${student.matricula || "-"}</td>
            <td>${student.email || "-"}</td>
            <td>${student.full_name || "-"}</td>
            <td>${student.status || "-"}</td>
            <td>${formatDate(student.registered_at)}</td>
          </tr>
        `
      )
      .join("");
  } catch (error) {
    tbody.innerHTML = "";
    showMessage("studentsError", error.message);
  }
}

function exportSocioStudents(projectId) {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("No hay sesión activa.");
    return;
  }

  fetch(`/socio/projects/${projectId}/students/export`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
    .then(async (response) => {
      if (!response.ok) {
        let message = "No se pudo exportar el CSV.";
        try {
          const data = await response.json();
          message = data.detail || message;
        } catch (_) {}
        throw new Error(message);
      }
      return response.blob();
    })
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "estudiantes_proyecto.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch((error) => {
      showMessage("studentsError", error.message);
    });
}

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  const registroForm = document.getElementById("registroForm");
  const logoutBtn = document.getElementById("logoutBtn");
  const generateCodeForm = document.getElementById("generateCodeForm");
  const refreshDetailBtn = document.getElementById("refreshDetailBtn");
  const refreshCodesBtn = document.getElementById("refreshCodesBtn");
  const refreshStudentsBtn = document.getElementById("refreshStudentsBtn");
  const exportStudentsBtn = document.getElementById("exportStudentsBtn");

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
          body: JSON.stringify({ matricula, email, codigo }),
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

  if (generateCodeForm) {
    generateCodeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const projectId = localStorage.getItem("selectedProjectId");
      if (!projectId) {
        showMessage("generateCodeError", "Primero selecciona un proyecto.");
        return;
      }

      await generateSocioCode(projectId);
    });
  }

  if (refreshDetailBtn) {
    refreshDetailBtn.addEventListener("click", async () => {
      const projectId = localStorage.getItem("selectedProjectId");
      if (projectId) {
        await loadSocioProjectDetail(projectId);
      }
    });
  }

  if (refreshCodesBtn) {
    refreshCodesBtn.addEventListener("click", async () => {
      const projectId = localStorage.getItem("selectedProjectId");
      if (projectId) {
        await loadSocioCodes(projectId);
      }
    });
  }

  if (refreshStudentsBtn) {
    refreshStudentsBtn.addEventListener("click", async () => {
      const projectId = localStorage.getItem("selectedProjectId");
      if (projectId) {
        await loadSocioStudents(projectId);
      }
    });
  }

  if (exportStudentsBtn) {
    exportStudentsBtn.addEventListener("click", () => {
      const projectId = localStorage.getItem("selectedProjectId");
      if (!projectId) {
        showMessage("studentsError", "Primero selecciona un proyecto.");
        return;
      }
      exportSocioStudents(projectId);
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      clearSession();
      window.location.href = "/login";
    });
  }

  if (document.getElementById("projectsContainer")) {
    loadSocioProjects().then(async () => {
      const selectedProjectId = localStorage.getItem("selectedProjectId");
      if (selectedProjectId) {
        await loadSocioProjectDetail(selectedProjectId);
        await loadSocioCodes(selectedProjectId);
        await loadSocioStudents(selectedProjectId);
      }
    });
  }
});