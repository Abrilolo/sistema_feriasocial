import { requestJSON, escapeHtml } from './api.js';
import { showMessage, hideMessage, badgeLabel } from './ui.js';
import { getAuthHeaders } from './auth.js';

let allStudents = [];
let allProjectsFull = [];
let carrerasArr = [];
let editCarrerasArr = [];

let checkinChartInstance = null;
let occupancyChartInstance = null;
let conversionChartInstance = null;
let qrChartInstance = null;
let staffChartInstance = null;

function renderAdminCharts(m, occupancyData) {
  if (!window.Chart) return;

  Chart.defaults.color = '#94a3b8'; // text-muted
  Chart.defaults.font.family = 'Inter, -apple-system, BlinkMacSystemFont, sans-serif';

  // 1. Donut Chart (Check-ins)
  const ctxCheckin = document.getElementById('checkinChart');
  if (ctxCheckin) {
    if (checkinChartInstance) checkinChartInstance.destroy();

    // Excluir a los que ya hicieron checkin para ver los faltantes
    const notCheckedIn = Math.max(0, m.students.total - m.operations.checkins);

    checkinChartInstance = new Chart(ctxCheckin, {
      type: 'doughnut',
      data: {
        labels: ['Check-In OK', 'Pendientes'],
        datasets: [{
          data: [m.operations.checkins, notCheckedIn],
          backgroundColor: ['#10b981', '#1e293b'], // emerald-500, surface
          borderColor: '#0f172a', // bg oscuro
          borderWidth: 2,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: { position: 'bottom', labels: { color: '#f8fafc', padding: 20 } }
        }
      }
    });
  }

  // 2. Bar Chart Heatmap (Ocupación)
  const ctxOccupancy = document.getElementById('occupancyChart');
  if (ctxOccupancy) {
    if (occupancyChartInstance) occupancyChartInstance.destroy();

    const sortedOccupancy = [...occupancyData].sort((a, b) => b.occupancy_percent - a.occupancy_percent);
    const labels = sortedOccupancy.map(p => p.name.length > 25 ? p.name.substring(0, 25) + '...' : p.name);
    const dataValues = sortedOccupancy.map(p => p.occupancy_percent);

    // Colores tipo Heatmap
    const backgroundColors = dataValues.map(pct => {
      if (pct >= 100) return 'rgba(225, 29, 72, 0.9)'; // saturado -> rose-600
      if (pct >= 75) return 'rgba(245, 158, 11, 0.9)'; // advertencia -> amber-500
      return 'rgba(16, 185, 129, 0.9)'; // libre -> emerald-500
    });

    occupancyChartInstance = new Chart(ctxOccupancy, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Ocupación',
          data: dataValues,
          backgroundColor: backgroundColors,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            max: Math.max(100, Math.max(...(dataValues.length ? dataValues : [0]))),
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { callback: function (value) { return value + "%"; } }
          },
          x: {
            grid: { display: false },
            ticks: { display: false } // Ocultar textos largos en el eje X, se leen en el tooltip
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return "Ocupación: " + context.raw + "%";
              },
              afterLabel: function (context) {
                const projectNode = sortedOccupancy[context.dataIndex];
                if (projectNode) {
                  return `Lugares: ${projectNode.taken_slots} inscritos / ${projectNode.capacity} cupo\nDisponibles: ${projectNode.remaining_slots} asientos`;
                }
                return "";
              }
            }
          }
        }
      }
    });
  }

  // 3. Conversion Funnel (Bar horizontal)
  const ctxConversion = document.getElementById('conversionChart');
  if (ctxConversion) {
    if (conversionChartInstance) conversionChartInstance.destroy();

    conversionChartInstance = new Chart(ctxConversion, {
      type: 'bar',
      data: {
        labels: ['Estudiantes Totales', 'Con Check-in', 'Registrados (Stand)'],
        datasets: [{
          label: 'Alumnos',
          data: [m.students.total, m.operations.checkins, m.operations.registrations],
          backgroundColor: ['#64748b', '#0ea5e9', '#10b981'], // slate-500, sky-500, emerald-500
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y', // Hace la gráfica horizontal
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' } },
          y: { grid: { display: false }, ticks: { color: '#f8fafc' } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  // 4. QR Codes (Doughnut)
  const ctxQR = document.getElementById('qrChart');
  if (ctxQR) {
    if (qrChartInstance) qrChartInstance.destroy();

    qrChartInstance = new Chart(ctxQR, {
      type: 'doughnut',
      data: {
        labels: ['Usados', 'Activos', 'Expirados'],
        datasets: [{
          data: [m.temp_codes.used, m.temp_codes.active, m.temp_codes.expired],
          backgroundColor: ['#10b981', '#f59e0b', '#e11d48'], // emerald, amber, rose
          borderColor: '#0f172a',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { color: '#f8fafc', padding: 15 } },
          tooltip: {
            callbacks: {
              label: function (context) {
                const raw = context.raw;
                const total = m.temp_codes.used + m.temp_codes.active + m.temp_codes.expired;
                const pct = total > 0 ? Math.round((raw / total) * 100) : 0;
                return ` ${context.label}: ${raw} boletos (${pct}%)`;
              }
            }
          }
        }
      }
    });
  }

  // 5. Staff Distribution (PolarArea o Doughnut)
  const ctxStaff = document.getElementById('staffChart');
  if (ctxStaff) {
    if (staffChartInstance) staffChartInstance.destroy();

    staffChartInstance = new Chart(ctxStaff, {
      type: 'polarArea',
      data: {
        labels: ['Socios (ONG)', 'Becarios (Puerta)', 'Administradores'],
        datasets: [{
          data: [m.users.socios, m.users.becarios, m.users.admins],
          backgroundColor: [
            'rgba(14, 165, 233, 0.7)', // sky
            'rgba(168, 85, 247, 0.7)', // purple
            'rgba(244, 63, 94, 0.7)'   // rose
          ],
          borderColor: '#0f172a',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            grid: { color: 'rgba(255,255,255,0.1)' },
            ticks: { display: false }
          }
        },
        plugins: {
          legend: { position: 'right', labels: { color: '#f8fafc' } }
        }
      }
    });
  }
}

async function loadAdminMetrics() {
  try {
    const data = await requestJSON("/admin/metrics", { headers: getAuthHeaders() });
    const m = data.metrics;
    document.getElementById("kpiStudents").textContent = m.students.total;
    document.getElementById("kpiCheckins").textContent = m.operations.checkins;
    document.getElementById("kpiRegistrations").textContent = m.operations.registrations;
    document.getElementById("kpiProjects").textContent = m.projects.total;
    document.getElementById("kpiProjectsFull").textContent = m.projects.full;

    // Renderizar Gráficas
    renderAdminCharts(m, data.project_occupancy);

    const tbody = document.getElementById("projectsTableBody");
    tbody.innerHTML = "";
    if (data.project_occupancy.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;">No hay proyectos registrados.</td></tr>`;
      return;
    }

    data.project_occupancy.forEach(p => {
      const tr = document.createElement("tr");

      const pct = p.occupancy_percent;
      let barColor = pct >= 100 ? "var(--error)" : "var(--primary)";
      const barHtml = `
        <div style="background: var(--surface-soft); border-radius: 4px; overflow: hidden; height: 8px; margin-top: 5px;">
          <div style="width: ${pct}%; background: ${barColor}; height: 100%;"></div>
        </div>
      `;

      // Escapar datos para prevenir XSS
      const safeName = escapeHtml(p.name);
      const safeTaken = escapeHtml(p.taken_slots);
      const safeCapacity = escapeHtml(p.capacity);
      const safePct = escapeHtml(pct);

      tr.innerHTML = `
        <td style="padding: 10px; border-bottom: 1px solid var(--border);">
          <strong>${safeName}</strong>
          ${!p.is_active ? badgeLabel(false, "Activo", "Inactivo") : ""}
        </td>
        <td style="padding: 10px; border-bottom: 1px solid var(--border);">${safeTaken} / ${safeCapacity}</td>
        <td style="padding: 10px; border-bottom: 1px solid var(--border);">${safePct}% ${barHtml}</td>
        <td style="padding: 10px; border-bottom: 1px solid var(--border);">
          <div style="display: flex; gap: 5px; flex-wrap: wrap;">
            <button class="btn-toggle-project" data-id="${p.project_id}" data-action="${p.is_active ? 'deactivate' : 'activate'}" style="padding: 5px 10px; border-radius: 4px; border: none; cursor:pointer; background: ${p.is_active ? '#fee2e2' : '#dcfce7'}; color: ${p.is_active ? '#b91c1c' : '#15803d'}; font-weight: 500;">
              ${p.is_active ? 'Desactivar' : 'Activar'}
            </button>
            <button class="btn-edit-project" data-id="${p.project_id}" style="padding: 5px 15px; border-radius: 4px; border: 1px solid var(--primary); background: white; color: var(--primary); cursor:pointer; font-weight: bold; transition: all 0.2s;">
              ✏️ Editar
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });

    document.querySelectorAll(".btn-toggle-project").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const id = e.target.dataset.id;
        const action = e.target.dataset.action;
        try {
          await requestJSON(`/admin/projects/${id}/${action}`, { method: "PATCH", headers: getAuthHeaders() });
          loadAdminMetrics(); // Reload UI
        } catch (err) {
          alert("Error: " + err.message);
        }
      });
    });

    document.querySelectorAll(".btn-edit-project").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const id = e.currentTarget.dataset.id;
        openEditProjectModal(id);
      });
    });

  } catch (error) {
    console.error("No se pudieron cargar métricas", error);
  }
}

async function loadAllStudents() {
  try {
    const data = await requestJSON("/admin/students", { headers: getAuthHeaders() });
    allStudents = data.students;
    renderStudentsTable(allStudents);
  } catch (error) {
    document.getElementById("studentsTableBody").innerHTML = `<tr><td colspan="4" style="text-align:center; color:red;">Error cargando alumnos</td></tr>`;
  }
}

function renderStudentsTable(studentsList) {
  const tbody = document.getElementById("studentsTableBody");
  tbody.innerHTML = "";
  if (studentsList.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;">No hay estudiantes registrados.</td></tr>`;
    return;
  }

  studentsList.forEach(s => {
    const tr = document.createElement("tr");

    // Escapar datos del estudiante para prevenir XSS
    const safeMatricula = escapeHtml(s.matricula);
    const safeEmail = escapeHtml(s.email);
    const safeProjectName = s.project ? escapeHtml(s.project.name) : null;

    let statusHtml = badgeLabel(s.has_checkin, "Check-In", "Sin Check-In");
    if (s.is_registered) {
      statusHtml += " " + badgeLabel(true, "Registrado");
    }

    let actionHtml = "";
    if (s.is_registered) {
      actionHtml = `<button class="btn-cancel-reg" data-id="${s.registration_id}" style="padding: 5px 10px; border-radius: 4px; border: none; cursor:pointer; background: #fee2e2; color: #b91c1c; font-weight: 500;">Cancelar Registro</button>`;
    }

    tr.innerHTML = `
      <td style="padding: 10px; border-bottom: 1px solid var(--border);">
        <strong>${safeMatricula}</strong><br><small class="muted">${safeEmail}</small>
      </td>
      <td style="padding: 10px; border-bottom: 1px solid var(--border);">${statusHtml}</td>
      <td style="padding: 10px; border-bottom: 1px solid var(--border); max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
        ${safeProjectName ? safeProjectName : '<span class="muted">-</span>'}
      </td>
      <td style="padding: 10px; border-bottom: 1px solid var(--border);">${actionHtml}</td>
    `;
    tbody.appendChild(tr);
  });

  document.querySelectorAll(".btn-cancel-reg").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      if (!confirm("¿Seguro que deseas anular este registro? El alumno perderá su lugar en el proyecto y el código quedará quemado.")) return;
      const regId = e.target.dataset.id;
      try {
        await requestJSON(`/admin/registrations/${regId}/cancel`, { method: "PATCH", headers: getAuthHeaders() });
        loadAllStudents();
        loadAdminMetrics();
      } catch (err) {
        alert("Error al cancelar: " + err.message);
      }
    });
  });
}

async function loadUsersForDropdown() {
  try {
    const data = await requestJSON("/admin/users", { headers: getAuthHeaders() });
    const ownerSelect = document.getElementById("projOwner");
    const editOwnerSelect = document.getElementById("editProjOwner");

    const validUsers = data.users.filter(u => u.role === "SOCIO" || u.role === "ADMIN");

    if (ownerSelect) {
      ownerSelect.innerHTML = '<option value="">Selecciona un dueño...</option>';
      validUsers.forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.id;
        const orgName = u.organization_name ? ` (${u.organization_name})` : "";
        opt.textContent = `${u.email} - ${u.role}${orgName}`;
        ownerSelect.appendChild(opt);
      });
    }
    if (editOwnerSelect) {
      editOwnerSelect.innerHTML = '<option value="">Selecciona un dueño...</option>';
      validUsers.forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.id;
        const orgName = u.organization_name ? ` (${u.organization_name})` : "";
        opt.textContent = `${u.email} - ${u.role}${orgName}`;
        editOwnerSelect.appendChild(opt);
      });
    }
  } catch (error) {
    console.error("Error cargando usuarios", error);
  }
}

// Load All Projects Full
async function loadAllProjectsFull() {
  try {
    const data = await requestJSON("/admin/projects", { headers: getAuthHeaders() });
    if (data && data.projects) {
      allProjectsFull = data.projects;
    }
  } catch (err) {
    console.error("Error loading full projects:", err);
  }
}

// Open Edit Modal
function openEditProjectModal(id) {
  const proj = allProjectsFull.find(p => p.id === id);
  if (!proj) {
    alert("No se cargaron los detalles del proyecto correctamente.");
    return;
  }

  document.getElementById("editProjId").value = proj.id || "";
  document.getElementById("editProjName").value = proj.name || "";
  document.getElementById("editProjClave").value = proj.clave_programa || "";
  document.getElementById("editProjOwner").value = proj.owner ? proj.owner.id : "";
  document.getElementById("editProjCap").value = proj.capacity || 20;

  document.getElementById("editProjPeriodo").value = proj.periodo || "";
  document.getElementById("editProjObjetivo").value = proj.objetivo || "";
  document.getElementById("editProjActividades").value = proj.actividades || "";
  document.getElementById("editProjCompetencias").value = proj.competencias_requeridas || "";
  document.getElementById("editProjHorario").value = proj.horario || "";
  document.getElementById("editProjModalidad").value = proj.modalidad || "";
  document.getElementById("editProjLugar").value = proj.lugar_trabajo || "";
  document.getElementById("editProjDuracion").value = proj.duracion || "";
  document.getElementById("editProjHoras").value = proj.horas_acreditar || "";
  document.getElementById("editProjPoblacion").value = proj.poblacion_atendida || "";
  document.getElementById("editProjDesc").value = proj.comentarios_adicionales || proj.description || "";

  if (proj.carreras_permitidas) {
    editCarrerasArr = proj.carreras_permitidas.split(",").map(c => c.trim()).filter(c => c);
  } else {
    editCarrerasArr = [];
  }
  renderEditCarreras();

  hideMessage("adminEditProjectMessage");
  document.getElementById("editProjectModal").style.display = "flex";
}


document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("kpiStudents")) {
    loadAdminMetrics();
    loadAllStudents();
    loadUsersForDropdown();
    loadAllProjectsFull();

    // Filtro de búsqueda
    const searchInput = document.getElementById("searchStudent");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        const term = e.target.value.toLowerCase().trim();
        const filtered = allStudents.filter(s =>
          s.matricula.toLowerCase().includes(term) ||
          s.email.toLowerCase().includes(term)
        );
        renderStudentsTable(filtered);
      });
    }

    // Exportar CSV
    const btnExportStudents = document.getElementById("btnExportStudents");
    if (btnExportStudents) {
      btnExportStudents.addEventListener("click", () => {
        if (allStudents.length === 0) {
          alert("No hay alumnos para exportar.");
          return;
        }

        let csvContent = "Matricula;Correo;Nombre Completo;Check-In;Registrado a Proyecto;Clave del Programa;Nombre del Programa\n";

        allStudents.forEach(s => {
          const checkinStr = s.has_checkin ? "SI" : "NO";
          const regStr = s.is_registered ? "SI" : "NO";
          const projName = s.project ? `"${s.project.name.replace(/"/g, '""')}"` : "";
          const projClave = s.project && s.project.clave_programa ? `"${s.project.clave_programa.replace(/"/g, '""')}"` : "";
          const nameStr = s.full_name ? `"${s.full_name.replace(/"/g, '""')}"` : "";

          csvContent += `${s.matricula};${s.email};${nameStr};${checkinStr};${regStr};${projClave};${projName}\n`;
        });

        // \uFEFF to support UTF-8 formatting seamlessly in excel
        const blob = new Blob(["\uFEFF" + csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", `Alumnos_FeriaSocial_${new Date().toISOString().slice(0, 10)}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      });
    }
  }

  // Formulario Añadir Alumno
  const adminAddStudentForm = document.getElementById("adminAddStudentForm");
  if (adminAddStudentForm) {
    adminAddStudentForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideMessage("adminAddStudentMessage");
      const matricula = document.getElementById("adminMatricula").value.trim();
      const email = document.getElementById("adminEmail").value.trim();
      const full_name = document.getElementById("adminName").value.trim();
      const auto_checkin = document.getElementById("adminAutoCheckin").checked;

      try {
        await requestJSON("/admin/students", {
          method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() },
          body: JSON.stringify({ matricula, email, full_name: full_name || null, auto_checkin })
        });
        showMessage("adminAddStudentMessage", `¡Estudiante guardado!`, "success");
        adminAddStudentForm.reset();
        document.getElementById("adminAutoCheckin").checked = true;
        loadAdminMetrics();
        loadAllStudents();
      } catch (error) { showMessage("adminAddStudentMessage", error.message, "error"); }
    });
  }

  // Formulario Añadir Personal
  const adminAddUserForm = document.getElementById("adminAddUserForm");
  if (adminAddUserForm) {
    adminAddUserForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideMessage("adminAddUserMessage");
      const email = document.getElementById("userEmail").value.trim();
      const password = document.getElementById("userPassword").value;
      const role = document.getElementById("userRole").value;

      try {
        await requestJSON("/admin/users", {
          method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() },
          body: JSON.stringify({ email, password, role })
        });
        showMessage("adminAddUserMessage", `¡Usuario ${role} creado exitosamente!`, "success");
        adminAddUserForm.reset();
        loadAdminMetrics();
        loadUsersForDropdown();
      } catch (error) { showMessage("adminAddUserMessage", error.message, "error"); }
    });
  }

  // Lógica Listado Carreras
  const carrerasInput = document.getElementById("projCarreraInput");
  const btnAddCarrera = document.getElementById("btnAddCarrera");
  const carrerasList = document.getElementById("carrerasList");

  function renderCarreras() {
    if (!carrerasList) return;
    carrerasList.innerHTML = "";
    if (carrerasArr.length === 0) {
      carrerasList.innerHTML = '<span class="muted" style="font-size: 0.85rem;">Sin carreras específicas...</span>';
    }
    carrerasArr.forEach((carrera, index) => {
      const badge = document.createElement("span");
      badge.style.cssText = "background: var(--primary); color: white; padding: 4px 10px; border-radius: 14px; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 6px;";
      badge.innerHTML = `${carrera} <span style="cursor:pointer; font-weight:bold; font-size:1.1rem; line-height: 1;" data-index="${index}">&times;</span>`;
      carrerasList.appendChild(badge);
    });

    carrerasList.querySelectorAll("span[data-index]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(e.target.dataset.index, 10);
        carrerasArr.splice(idx, 1);
        renderCarreras();
      });
    });
  }

  function addCarrera() {
    const val = carrerasInput.value.trim().toUpperCase();
    if (val && !carrerasArr.includes(val)) {
      carrerasArr.push(val);
      renderCarreras();
    }
    carrerasInput.value = "";
  }

  if (btnAddCarrera && carrerasInput) {
    renderCarreras(); // render initial empty state
    btnAddCarrera.addEventListener("click", addCarrera);
    carrerasInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault(); // Evitar submit
        addCarrera();
      }
    });
  }

  // Formulario Añadir Proyecto
  const adminAddProjectForm = document.getElementById("adminAddProjectForm");
  if (adminAddProjectForm) {
    adminAddProjectForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideMessage("adminAddProjectMessage");
      const name = document.getElementById("projName").value.trim();
      const clave_programa = document.getElementById("projClave").value.trim();
      const description = document.getElementById("projDesc").value.trim();
      const capacity = parseInt(document.getElementById("projCap").value, 10);
      const owner_user_id = document.getElementById("projOwner").value;

      const periodo = document.getElementById("projPeriodo").value.trim();
      const carreras_permitidas = carrerasArr.length > 0 ? carrerasArr.join(", ") : null;
      const objetivo = document.getElementById("projObjetivo").value.trim();
      const actividades = document.getElementById("projActividades").value.trim();
      const horario = document.getElementById("projHorario").value.trim();
      const competencias_requeridas = document.getElementById("projCompetencias").value.trim();
      const modalidad = document.getElementById("projModalidad").value.trim();
      const lugar_trabajo = document.getElementById("projLugar").value.trim();
      const duracion = document.getElementById("projDuracion").value.trim();
      const poblacion_atendida = document.getElementById("projPoblacion").value.trim();
      const horas_acreditar = document.getElementById("projHoras").value.trim();

      if (!owner_user_id) {
        showMessage("adminAddProjectMessage", "Selecciona un dueño para el proyecto", "error");
        return;
      }

      const payload = {
        name,
        clave_programa: clave_programa || null,
        description: description || null,
        capacity,
        owner_user_id,
        periodo: periodo || null,
        carreras_permitidas: carreras_permitidas || null,
        objetivo: objetivo || null,
        actividades: actividades || null,
        horario: horario || null,
        competencias_requeridas: competencias_requeridas || null,
        modalidad: modalidad || null,
        lugar_trabajo: lugar_trabajo || null,
        duracion: duracion || null,
        poblacion_atendida: poblacion_atendida || null,
        horas_acreditar: horas_acreditar || null,
        comentarios_adicionales: description || null
      };

      try {
        await requestJSON("/admin/projects", {
          method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() },
          body: JSON.stringify(payload)
        });
        showMessage("adminAddProjectMessage", `¡Proyecto "${name}" creado exitosamente!`, "success");
        adminAddProjectForm.reset();
        carrerasArr = []; renderCarreras();
        loadAdminMetrics();
      } catch (error) { showMessage("adminAddProjectMessage", error.message, "error"); }
    });
  }
});
