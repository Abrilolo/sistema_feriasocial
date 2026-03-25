import { requestJSON } from './api.js';
import { showMessage, hideMessage, safeShow, safeHide, formatDate, badgeLabel } from './ui.js';
import { getAuthHeaders } from './auth.js';

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

    // Pintar logo de organización permanentemente si al menos un proyecto lo tiene asociado
    const projectWithImage = projects.find(p => p.image_filename);
    if (projectWithImage) {
      const orgLogoImg = document.getElementById("orgLogoImg");
      if (orgLogoImg) {
        const ts = new Date().getTime();
        orgLogoImg.src = `/static/img/img_socios/${projectWithImage.image_filename}?t=${ts}`;
        safeShow("orgLogoContainer", "flex");
      }
    }

    if (projects.length === 0) {
      container.innerHTML = "<p>No tienes proyectos asignados.</p>";
      return;
    }

    container.innerHTML = projects
      .map(
        (project) => `
          <div class="project-card modern-project-card fade-in" style="display: flex; flex-direction: column; gap: 20px; background: #ffffff; border-radius: 20px; padding: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid #f1f5f9; transition: all 0.3s ease;">
            <div class="mp-top" style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
              <div class="mp-info" style="flex: 1; min-width: 250px;">
                <h3 style="margin: 0 0 8px 0; font-size: 1.4rem; font-weight: 800; color: #0f172a; letter-spacing: -0.02em;">${project.name}</h3>
                <p style="margin: 0; font-size: 0.95rem; color: #64748b; line-height: 1.5;">${project.description || "Sin descripción"}</p>
                
                <div class="mp-stats-row" style="display: flex; gap: 20px; margin-top: 30px; flex-wrap: wrap;">
                  <!-- Capacidad -->
                  <div class="mp-stat-col" style="display: flex; flex-direction: column; align-items: center; min-width: 80px;">
                     <span style="font-size: 1.5rem; margin-bottom: 5px;">👥</span>
                     <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Capacidad</span>
                     <strong style="font-size: 1.5rem; color: #0f172a;">${project.capacity}</strong>
                  </div>
                  <!-- Ocupados -->
                  <div class="mp-stat-col" style="display: flex; flex-direction: column; align-items: center; min-width: 80px; border-left: 1px solid #f1f5f9; padding-left: 20px;">
                     <span style="font-size: 1.5rem; margin-bottom: 5px;">👤</span>
                     <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Ocupados</span>
                     <strong style="font-size: 1.5rem; color: #0f172a;">${project.taken_slots}</strong>
                  </div>
                  <!-- Disponibles -->
                  <div class="mp-stat-col" style="display: flex; flex-direction: column; align-items: center; min-width: 80px; border-left: 1px solid #f1f5f9; padding-left: 20px;">
                     <span style="font-size: 1.5rem; margin-bottom: 5px;">🪑</span>
                     <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Libres</span>
                     <strong style="font-size: 1.5rem; color: #0f172a;">${project.remaining_slots}</strong>
                  </div>
                </div>
              </div>
              
              <div class="mp-graph" style="width: 200px; height: 120px; background: #f8fafc; border-radius: 15px; padding: 15px; display: flex; flex-direction: column; border: 1px solid #f1f5f9;">
                <span style="font-size: 0.75rem; font-weight: 800; color: #475569; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em;">Tendencia</span>
                <canvas id="miniChart-${project.id}" style="width: 100%; flex: 1;"></canvas>
              </div>
            </div>

            <div class="mp-bottom" style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 20px; margin-top: 10px;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: ${project.is_active ? '#22c55e' : '#ef4444'};"></span>
                <span style="font-size: 0.85rem; font-weight: 600; color: #475569;">${project.is_active ? 'Activo' : 'Inactivo'}</span>
              </div>
              <button class="open-project-btn" data-project-id="${project.id}" style="background: #f1f5f9; color: #0f172a; border: none; padding: 10px 24px; border-radius: 12px; font-weight: 700; cursor: pointer; transition: all 0.2s; border: 1px solid transparent;">Ver detalles</button>
            </div>
          </div>
        `
      )
      .join("");

    // Initialize mini charts
    projects.forEach((project) => {
      const ctx = document.getElementById("miniChart-" + project.id);
      if (ctx && window.Chart) {
        new window.Chart(ctx, {
          type: "line",
          data: {
            labels: ["1-Sep", "2-Sep", "3-Sep", "4-Sep", "5-Sep"],
            datasets: [{
              data: [0, Math.floor(project.taken_slots * 0.2), Math.floor(project.taken_slots * 0.5), Math.floor(project.taken_slots * 0.8), project.taken_slots],
              borderColor: "#3b82f6",
              backgroundColor: "rgba(59, 130, 246, 0.15)",
              borderWidth: 3,
              fill: true,
              tension: 0.4,
              pointRadius: 0
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: {
              x: { grid: { display: false }, ticks: { font: { size: 10 } } },
              y: { border: { display: false }, grid: { display: false }, ticks: { display: false }, min: 0, max: Math.max(project.taken_slots, 10) }
            }
          }
        });
      }
    });

    document.querySelectorAll(".open-project-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const projectId = btn.dataset.projectId;
        const currentSelected = localStorage.getItem("selectedProjectId");

        // Toggle logic
        const detailPanel = document.getElementById("projectDetailPanel");
        if (currentSelected === projectId && detailPanel && detailPanel.style.display !== "none") {
          safeHide("projectDetailPanel");
          safeHide("generateCodePanel");
          safeHide("studentsPanel");
          btn.textContent = "Ver detalles";
          localStorage.setItem("selectedProjectId", "");
          return;
        }

        // Reset other buttons
        document.querySelectorAll(".open-project-btn").forEach(b => b.textContent = "Ver detalles");
        btn.textContent = "Ocultar detalles";

        localStorage.setItem("selectedProjectId", projectId);
        await loadSocioProjectDetail(projectId);
        await loadSocioStudents(projectId);

        // Smooth scroll to details
        detailPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    safeShow("projectDetailPanel", "block");
    safeShow("generateCodePanel", "block");
    safeShow("studentsPanel", "block");

    const titleEl = document.getElementById("detailProjectName");
    if (titleEl) titleEl.textContent = project.name || "Proyecto";

    const descEl = document.getElementById("detailProjectDescription");
    if (descEl) descEl.textContent = project.description || "Sin descripción";

    const capacity = project.capacity ?? 0;
    const taken = project.taken_slots ?? project.taken_slots_query ?? 0;
    const available = project.remaining_slots ?? 0;

    const statCap = document.getElementById("statCapacity");
    if (statCap) statCap.textContent = capacity;

    const statTak = document.getElementById("statTaken");
    if (statTak) statTak.textContent = taken;

    const statRem = document.getElementById("statRemaining");
    if (statRem) statRem.textContent = available;

    const gaugeFill = document.getElementById("gaugeFill");
    const statTakenGauge = document.getElementById("statTakenGauge");
    const statCapacityGauge = document.getElementById("statCapacityGauge");

    if (gaugeFill && statTakenGauge && statCapacityGauge) {
      let percentage = 0;
      if (capacity > 0) percentage = Math.min(taken / capacity, 1);

      // Calculate SVG stroke offset for semi-circle
      const offset = 125.66 * (1 - percentage);
      gaugeFill.style.strokeDashoffset = offset;
      statTakenGauge.textContent = taken;
      statCapacityGauge.textContent = capacity;
    }
  } catch (error) {
    showMessage("detailError", error.message);
  }
}

async function generateSocioCode(projectId) {
  hideMessage("generateCodeError");

  const expiresInMinutes = 10;

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

    safeShow("codeDisplayWrapper", "flex");
    const codeDisplay = document.getElementById("currentCodeDisplay");
    if (codeDisplay) codeDisplay.textContent = code;

    const expiryDisplay = document.getElementById("codeExpiryDisplay");
    if (expiryDisplay) expiryDisplay.textContent = `Expira: ${expiresAt}`;

    await loadSocioProjectDetail(projectId);
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
            <td>${code.is_expired
            ? '<span class="badge badge-warn">Sí</span>'
            : '<span class="badge badge-ok">No</span>'
          }</td>
            <td>${formatDate(code.expires_at)}</td>
            <td>
              ${code.is_active && !code.is_used
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
          <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.2s;">
            <td style="padding: 15px 20px; font-weight: 700; color: #0f172a;">${student.matricula || "-"}</td>
            <td style="padding: 15px 20px; color: #475569;">${student.email || "-"}</td>
            <td style="padding: 15px 20px; font-weight: 600; color: #334155;">${student.full_name || "-"}</td>
            <td style="padding: 15px 20px;">
              <span style="background: #f1f5f9; color: #475569; padding: 4px 12px; border-radius: 99px; font-size: 0.8rem; font-weight: 600;">${student.status || "-"}</span>
            </td>
            <td style="padding: 15px 20px; color: #94a3b8; font-size: 0.85rem;">${formatDate(student.registered_at)}</td>
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
        } catch (_) { }
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
  // Siempre pedir los datos frescos al hacer refresh
  requestJSON("/auth/me", { headers: getAuthHeaders() })
    .then(meData => {
      localStorage.setItem("user", JSON.stringify(meData));
      const orgNameSpan = document.getElementById("orgNameSpan");
      if (orgNameSpan && meData.organization_name) {
        orgNameSpan.textContent = meData.organization_name;
      }
    })
    .catch(() => {
      try {
        const usr = JSON.parse(localStorage.getItem("user") || "{}");
        const orgNameSpan = document.getElementById("orgNameSpan");
        if (orgNameSpan && usr.organization_name) {
          orgNameSpan.textContent = usr.organization_name;
        }
      } catch (e) { }
    });

  const quickGenerateCodeBtn = document.getElementById("quickGenerateCodeBtn");
  const refreshDetailBtn = document.getElementById("refreshDetailBtn");
  const refreshStudentsBtn = document.getElementById("refreshStudentsBtn");
  const exportStudentsBtn = document.getElementById("exportStudentsBtn");

  if (quickGenerateCodeBtn) {
    quickGenerateCodeBtn.addEventListener("click", async (e) => {
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

  if (document.getElementById("projectsContainer")) {
    loadSocioProjects().then(async () => {
      const selectedProjectId = localStorage.getItem("selectedProjectId");
      if (selectedProjectId) {
        const btn = document.querySelector(`.open-project-btn[data-project-id="${selectedProjectId}"]`);
        if (btn) btn.textContent = "Ocultar detalles";

        await loadSocioProjectDetail(selectedProjectId);
        await loadSocioStudents(selectedProjectId);
      }
    });
  }
});
