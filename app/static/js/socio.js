import { requestJSON } from './api.js';
import { showMessage, hideMessage, safeShow, safeHide, formatDate, badgeLabel } from './ui.js';
import { getAuthHeaders } from './auth.js';

// Configuración premium para Chart.js
const CHART_CONFIG = {
  line: {
    type: 'line',
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#fff',
          bodyColor: '#fff',
          padding: 12,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            title: () => '',
            label: (context) => `${context.parsed.y} inscritos`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false, drawBorder: false },
          ticks: {
            font: { size: 10, family: 'Inter' },
            color: '#64748b'
          }
        },
        y: {
          border: { display: false },
          grid: {
            color: 'rgba(148, 163, 184, 0.1)',
            drawBorder: false
          },
          ticks: {
            font: { size: 10, family: 'Inter' },
            color: '#64748b',
            padding: 8
          },
          min: 0
        }
      },
      elements: {
        line: {
          tension: 0.4,
          borderWidth: 3
        },
        point: {
          radius: 0,
          hitRadius: 20,
          hoverRadius: 6,
          hoverBorderWidth: 3
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    }
  }
};

async function loadSocioProjects() {
  const container = document.getElementById("projectsContainer");
  if (!container) return;

  hideMessage("projectsError");
  container.innerHTML = `
    <div class="skeleton" style="height: 200px; border-radius: var(--radius-xl);"></div>
    <div class="skeleton" style="height: 200px; border-radius: var(--radius-xl);"></div>
    <div class="skeleton" style="height: 200px; border-radius: var(--radius-xl);"></div>
  `;

  try {
    const data = await requestJSON("/socio/projects", {
      method: "GET",
      headers: {
        ...getAuthHeaders(),
      },
    });

    const projects = data.projects || [];

    // Pintar logo de organización si al menos un proyecto lo tiene
    const projectWithImage = projects.find(p => p.image_filename);
    if (projectWithImage) {
      const orgLogoImg = document.getElementById("orgLogoImg");
      if (orgLogoImg) {
        const ts = new Date().getTime();
        orgLogoImg.src = `/static/img/img_socios/${projectWithImage.image_filename}?t=${ts}`;
        safeShow("orgLogoContainer", "flex");
        document.getElementById("orgLogoContainer")?.classList.add("visible");
      }
    }

    if (projects.length === 0) {
      container.innerHTML = `
        <div class="card" style="grid-column: 1 / -1; text-align: center; padding: var(--space-12);">
          <div style="font-size: 3rem; margin-bottom: var(--space-4);">📋</div>
          <h3 style="color: var(--text);">No tienes proyectos asignados</h3>
          <p style="color: var(--text-muted); margin-top: var(--space-2);">Contacta al administrador para asignarte proyectos.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = projects
      .map((project) => {
        const statusClass = project.is_active ? 'active' : 'inactive';
        const statusText = project.is_active ? 'Activo' : 'Inactivo';

        return `
          <div class="modern-project-card" data-project-id="${project.id}">
            <div class="mp-top">
              <div class="mp-info">
                <h3 class="mp-title">${project.name}</h3>
                <p class="mp-description">${project.description || "Sin descripción disponible"}</p>

                <div class="mp-stats-row">
                  <div class="mp-stat-col">
                    <span class="mp-stat-icon">👥</span>
                    <span class="mp-stat-label">Capacidad</span>
                    <strong class="mp-stat-value">${project.capacity}</strong>
                  </div>
                  <div class="mp-stat-col">
                    <span class="mp-stat-icon">👤</span>
                    <span class="mp-stat-label">Ocupados</span>
                    <strong class="mp-stat-value">${project.taken_slots}</strong>
                  </div>
                  <div class="mp-stat-col">
                    <span class="mp-stat-icon">🪑</span>
                    <span class="mp-stat-label">Disponibles</span>
                    <strong class="mp-stat-value">${project.remaining_slots}</strong>
                  </div>
                  <div class="mp-stat-col">
                    <span class="mp-stat-icon">🔲</span>
                    <span class="mp-stat-label">Códigos</span>
                    <strong class="mp-stat-value">${project.active_codes}</strong>
                  </div>
                  <div class="mp-stat-col">
                    <span class="mp-stat-icon">${project.is_active ? '✅' : '⏸️'}</span>
                    <span class="mp-stat-label">Estado</span>
                    <span class="status-badge ${statusClass}">${statusText}</span>
                  </div>
                </div>
              </div>

              <div class="mp-graph">
                <span class="mp-graph-title">Inscripciones</span>
                <canvas id="miniChart-${project.id}" class="mp-chart-canvas"></canvas>
              </div>
            </div>

            <div class="mp-bottom">
              <button class="open-project-btn btn btn-secondary btn-sm" data-project-id="${project.id}">
                Ver detalles
              </button>
            </div>
          </div>
        `;
      })
      .join("");

    // Initialize mini charts con configuración premium
    projects.forEach((project) => {
      const ctx = document.getElementById("miniChart-" + project.id);
      if (ctx && window.Chart) {
        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 120);
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.25)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.02)');

        const maxSlots = Math.max(project.taken_slots, project.capacity, 10);

        new window.Chart(ctx, {
          ...CHART_CONFIG.line,
          data: {
            labels: ["Lun", "Mar", "Mié", "Jue", "Vie"],
            datasets: [{
              data: [
                Math.floor(project.taken_slots * 0.1),
                Math.floor(project.taken_slots * 0.3),
                Math.floor(project.taken_slots * 0.5),
                Math.floor(project.taken_slots * 0.75),
                project.taken_slots
              ],
              borderColor: "#3b82f6",
              backgroundColor: gradient,
              fill: true,
              borderWidth: 3
            }]
          },
          options: {
            ...CHART_CONFIG.line.options,
            scales: {
              ...CHART_CONFIG.line.options.scales,
              y: {
                ...CHART_CONFIG.line.options.scales.y,
                max: maxSlots
              }
            }
          }
        });
      }
    });

    // Event listeners para botones
    document.querySelectorAll(".open-project-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const projectId = btn.dataset.projectId;
        const currentSelected = localStorage.getItem("selectedProjectId");
        const detailPanel = document.getElementById("projectDetailPanel");

        // Toggle logic
        if (currentSelected === projectId && detailPanel && detailPanel.style.display !== "none") {
          safeHide("projectDetailPanel");
          safeHide("generateCodePanel");
          safeHide("studentsPanel");
          btn.textContent = "Ver detalles";
          btn.classList.remove("btn-primary");
          btn.classList.add("btn-secondary");
          localStorage.setItem("selectedProjectId", "");
          return;
        }

        // Reset other buttons
        document.querySelectorAll(".open-project-btn").forEach(b => {
          b.textContent = "Ver detalles";
          b.classList.remove("btn-primary");
          b.classList.add("btn-secondary");
        });

        btn.textContent = "Ocultar detalles";
        btn.classList.remove("btn-secondary");
        btn.classList.add("btn-primary");

        localStorage.setItem("selectedProjectId", projectId);
        await loadSocioProjectDetail(projectId);
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
    safeShow("projectDetailPanel", "block");
    safeShow("generateCodePanel", "block");
    safeShow("studentsPanel", "block");

    // Animar aparición
    setTimeout(() => {
      document.getElementById("projectDetailPanel")?.classList.add("animate-fade-up");
    }, 50);

    const titleEl = document.getElementById("detailProjectName");
    if (titleEl) titleEl.textContent = project.name || "Proyecto";

    const descEl = document.getElementById("detailProjectDescription");
    if (descEl) descEl.textContent = project.description || "Sin descripción disponible";

    const capacity = project.capacity ?? 0;
    const taken = project.taken_slots ?? 0;
    const available = project.remaining_slots ?? 0;

    // Update stats con animación
    animateValue("statCapacity", 0, capacity, 800);
    animateValue("statTaken", 0, taken, 800);
    animateValue("statRemaining", 0, available, 800);

    // Update gauge
    const gaugeFill = document.getElementById("gaugeFill");
    const statTakenGauge = document.getElementById("statTakenGauge");
    const statCapacityGauge = document.getElementById("statCapacityGauge");

    if (gaugeFill && statTakenGauge && statCapacityGauge) {
      let percentage = 0;
      if (capacity > 0) percentage = Math.min(taken / capacity, 1);

      const offset = 125.66 * (1 - percentage);

      // Pequeña demora para la animación visual
      setTimeout(() => {
        gaugeFill.style.strokeDashoffset = offset;
      }, 100);

      // Animar el número
      animateValue("statTakenGauge", 0, taken, 1000);
      statCapacityGauge.textContent = capacity;

      // Cambiar color según ocupación
      if (percentage >= 0.9) {
        gaugeFill.style.stroke = '#f43f5e'; // Rojo - casi lleno
      } else if (percentage >= 0.7) {
        gaugeFill.style.stroke = '#f59e0b'; // Amarillo - medio lleno
      } else {
        gaugeFill.style.stroke = '#ffffff'; // Blanco - normal
      }
    }
  } catch (error) {
    showMessage("detailError", error.message);
  }
}

// Helper para animar números
function animateValue(id, start, end, duration) {
  const obj = document.getElementById(id);
  if (!obj) return;

  const range = end - start;
  const minTimer = 50;
  let stepTime = Math.abs(Math.floor(duration / range));
  stepTime = Math.max(stepTime, minTimer);

  let startTime = new Date().getTime();
  let endTime = startTime + duration;
  let timer;

  function run() {
    let now = new Date().getTime();
    let remaining = Math.max((endTime - now) / duration, 0);
    let value = Math.round(end - (remaining * range));
    obj.textContent = value;

    if (value == end) {
      clearInterval(timer);
    }
  }

  timer = setInterval(run, stepTime);
  run();
}

async function generateSocioCode(projectId) {
  hideMessage("generateCodeError");

  const btn = document.getElementById("quickGenerateCodeBtn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin">⏳</span> Generando...`;
  }

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
    if (codeDisplay) {
      codeDisplay.textContent = code;
      codeDisplay.classList.add("animate-fade-up");
    }

    const expiryDisplay = document.getElementById("codeExpiryDisplay");
    if (expiryDisplay) expiryDisplay.textContent = `Expira: ${expiresAt}`;

    await loadSocioProjectDetail(projectId);
  } catch (error) {
    showMessage("generateCodeError", error.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>✨</span> Crear Nuevo Código`;
    }
  }
}

async function loadSocioStudents(projectId) {
  const tbody = document.getElementById("studentsTableBody");
  if (!tbody) return;

  hideMessage("studentsError");
  tbody.innerHTML = `
    <tr>
      <td colspan="5" style="text-align: center; padding: var(--space-8);">
        <div class="skeleton" style="height: 20px; width: 80%; margin: 0 auto;"></div>
      </td>
    </tr>
  `;

  try {
    const data = await requestJSON(`/socio/projects/${projectId}/students`, {
      method: "GET",
      headers: {
        ...getAuthHeaders(),
      },
    });

    const students = data.students || [];

    if (students.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: var(--space-8);">
            <div style="color: var(--text-muted);">
              <div style="font-size: 2rem; margin-bottom: var(--space-3);">👥</div>
              <p>No hay estudiantes registrados aún.</p>
              <p style="font-size: var(--text-sm);">Genera un código para que los estudiantes se registren.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = students
      .map((student) => {
        const statusClass = student.status === 'registered' ? 'badge-ok' : 'badge-warn';
        return `
          <tr>
            <td><code>${student.matricula || "-"}</code></td>
            <td>${student.email || "-"}</td>
            <td><strong>${student.full_name || "-"}</strong></td>
            <td><span class="badge ${statusClass}">${student.status || "-"}</span></td>
            <td>${formatDate(student.registered_at)}</td>
          </tr>
        `;
      })
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

  const btn = document.getElementById("exportStudentsBtn");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `⏳ Exportando...`;
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
      a.download = `estudiantes_proyecto_${projectId}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `⬇️ Exportar CSV`;
      }
    })
    .catch((error) => {
      showMessage("studentsError", error.message);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `⬇️ Exportar CSV`;
      }
    });
}

document.addEventListener("DOMContentLoaded", () => {
  // Cargar información del usuario
  requestJSON("/auth/me", { headers: getAuthHeaders() })
    .then(meData => {
      localStorage.setItem("user", JSON.stringify(meData));
      const orgNameSpan = document.getElementById("orgNameSpan");
      if (orgNameSpan && meData.organization_name) {
        orgNameSpan.textContent = meData.organization_name;
      }

      // Actualizar display de rol en header
      const userRoleDisplay = document.getElementById("userRoleDisplay");
      if (userRoleDisplay) {
        userRoleDisplay.textContent = `Socio Formador • ${meData.organization_name || ''}`;
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

  // Event listeners
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

  // Cargar proyectos
  if (document.getElementById("projectsContainer")) {
    loadSocioProjects().then(async () => {
      const selectedProjectId = localStorage.getItem("selectedProjectId");
      if (selectedProjectId) {
        const btn = document.querySelector(`.open-project-btn[data-project-id="${selectedProjectId}"]`);
        if (btn) {
          btn.textContent = "Ocultar detalles";
          btn.classList.remove("btn-secondary");
          btn.classList.add("btn-primary");
        }

        await loadSocioProjectDetail(selectedProjectId);
        await loadSocioStudents(selectedProjectId);
      }
    });
  }
});
