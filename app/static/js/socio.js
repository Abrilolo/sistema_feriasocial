import { requestJSON, escapeHtml } from './api.js';
import { formatDate } from './ui.js';
import { getAuthHeaders } from './auth.js';

// ── Error helpers (preserve soc-error class) ──────────────
function showErr(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.style.display = 'block';
}
function hideErr(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = '';
  el.style.display = 'none';
}

// ── Chart.js config ───────────────────────────────────────
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
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          titleColor: '#f1f5f9',
          bodyColor: '#94a3b8',
          padding: 10,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            title: () => '',
            label: (ctx) => `${ctx.parsed.y} inscritos`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false, drawBorder: false },
          ticks: { font: { size: 9, family: 'JetBrains Mono' }, color: '#475569' },
        },
        y: {
          border: { display: false },
          grid: { color: 'rgba(148,163,184,0.06)', drawBorder: false },
          ticks: { font: { size: 9, family: 'JetBrains Mono' }, color: '#475569', padding: 6 },
          min: 0,
        },
      },
      elements: {
        line: { tension: 0.4, borderWidth: 2 },
        point: { radius: 0, hitRadius: 20, hoverRadius: 5, hoverBorderWidth: 2 },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  },
};

// ── Load projects ─────────────────────────────────────────
async function loadSocioProjects() {
  const container = document.getElementById('projectsContainer');
  if (!container) return;

  hideErr('projectsError');
  container.innerHTML = `
    <div class="soc-skeleton" style="height:200px;"></div>
    <div class="soc-skeleton" style="height:200px;"></div>
    <div class="soc-skeleton" style="height:200px;"></div>
  `;

  try {
    const data = await requestJSON('/socio/projects', {
      method: 'GET',
      headers: { ...getAuthHeaders() },
    });

    const projects = data.projects || [];

    // Logo de organización
    const withImage = projects.find((p) => p.image_filename);
    if (withImage) {
      const img = document.getElementById('orgLogoImg');
      const wrap = document.getElementById('orgLogoContainer');
      if (img && wrap) {
        img.src = `/static/img/img_socios/${withImage.image_filename}?t=${Date.now()}`;
        wrap.classList.add('visible');
      }
    }

    if (projects.length === 0) {
      container.innerHTML = `
        <div style="grid-column:1/-1;">
          <div class="soc-empty">
            <div class="soc-empty-icon">
              <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 12h8M12 8v8"/></svg>
            </div>
            <strong>Sin proyectos asignados</strong>
            <p>Contacta al administrador para que te asigne proyectos.</p>
          </div>
        </div>
      `;
      return;
    }

    container.innerHTML = projects.map((p) => {
      const pct = p.capacity > 0 ? Math.round((p.taken_slots / p.capacity) * 100) : 0;
      const barClass = pct >= 100 ? 'danger' : pct >= 85 ? 'full' : '';

      const safeName    = escapeHtml(p.name);
      const safeDesc    = escapeHtml(p.description || 'Sin descripción disponible');
      const statusClass = p.is_active ? 'active' : 'inactive';
      const statusText  = p.is_active ? 'Activo' : 'Inactivo';

      return `
        <div class="soc-project-card" data-project-id="${p.id}">
          <div>
            <div class="soc-card-header">
              <div>
                <span class="soc-label">Proyecto</span>
                <h3 class="soc-card-title">${safeName}</h3>
              </div>
              <span class="soc-status ${statusClass}">${statusText}</span>
            </div>
            <p class="soc-card-desc" style="margin-top:0.5rem;">${safeDesc}</p>

            <div class="soc-bar-wrap">
              <div class="soc-bar-meta">
                <span>${p.taken_slots} inscritos</span>
                <span>${pct}%</span>
              </div>
              <div class="soc-bar-track">
                <div class="soc-bar-fill ${barClass}" style="width:${pct}%"></div>
              </div>
            </div>

            <div class="soc-stats-row" style="margin-top:1rem;">
              <div class="soc-stat">
                <span class="soc-stat-label">Capacidad</span>
                <strong class="soc-stat-value">${escapeHtml(p.capacity)}</strong>
              </div>
              <div class="soc-stat">
                <span class="soc-stat-label">Ocupados</span>
                <strong class="soc-stat-value">${escapeHtml(p.taken_slots)}</strong>
              </div>
              <div class="soc-stat">
                <span class="soc-stat-label">Disponibles</span>
                <strong class="soc-stat-value">${escapeHtml(p.remaining_slots)}</strong>
              </div>
              <div class="soc-stat">
                <span class="soc-stat-label">Codigos</span>
                <strong class="soc-stat-value">${escapeHtml(p.active_codes)}</strong>
              </div>
            </div>

            <div class="soc-mini-chart" style="margin-top:1rem;">
              <canvas id="miniChart-${p.id}" class="soc-chart-canvas"></canvas>
            </div>
          </div>

          <div class="soc-card-footer">
            <button class="open-project-btn soc-btn soc-btn-outline soc-btn-sm" data-project-id="${p.id}">
              Ver detalles
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Mini charts
    projects.forEach((p) => {
      const ctx = document.getElementById(`miniChart-${p.id}`);
      if (!ctx || !window.Chart) return;

      const grad = ctx.getContext('2d').createLinearGradient(0, 0, 0, 60);
      grad.addColorStop(0, 'rgba(129,140,248,0.22)');
      grad.addColorStop(1, 'rgba(129,140,248,0.01)');

      new window.Chart(ctx, {
        ...CHART_CONFIG.line,
        data: {
          labels: ['Lun', 'Mar', 'Mié', 'Jue', 'Hoy'],
          datasets: [{
            data: [
              Math.floor(p.taken_slots * 0.1),
              Math.floor(p.taken_slots * 0.3),
              Math.floor(p.taken_slots * 0.55),
              Math.floor(p.taken_slots * 0.8),
              p.taken_slots,
            ],
            borderColor: '#818cf8',
            backgroundColor: grad,
            fill: true,
          }],
        },
        options: {
          ...CHART_CONFIG.line.options,
          scales: {
            ...CHART_CONFIG.line.options.scales,
            y: { ...CHART_CONFIG.line.options.scales.y, max: Math.max(p.capacity, p.taken_slots, 5) },
          },
        },
      });
    });

    // Click en tarjetas
    document.querySelectorAll('.open-project-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const projectId = btn.dataset.projectId;
        const selected  = localStorage.getItem('selectedProjectId');
        const detail    = document.getElementById('projectDetailPanel');

        if (selected === projectId && detail?.style.display !== 'none') {
          detail.style.display = 'none';
          document.getElementById('generateCodePanel').style.display = 'none';
          document.getElementById('studentsPanel').style.display = 'none';
          btn.textContent = 'Ver detalles';
          btn.classList.replace('soc-btn-primary', 'soc-btn-outline');
          document.querySelector(`.soc-project-card[data-project-id="${projectId}"]`)?.classList.remove('selected');
          localStorage.setItem('selectedProjectId', '');
          return;
        }

        // Reset todos
        document.querySelectorAll('.open-project-btn').forEach((b) => {
          b.textContent = 'Ver detalles';
          b.classList.replace('soc-btn-primary', 'soc-btn-outline');
        });
        document.querySelectorAll('.soc-project-card').forEach((c) => c.classList.remove('selected'));

        btn.textContent = 'Ocultar detalles';
        btn.classList.replace('soc-btn-outline', 'soc-btn-primary');
        btn.closest('.soc-project-card')?.classList.add('selected');

        localStorage.setItem('selectedProjectId', projectId);
        await loadSocioProjectDetail(projectId);
        await loadSocioStudents(projectId);
      });
    });

  } catch (err) {
    container.innerHTML = '';
    showErr('projectsError', err.message);
  }
}

// ── Project detail ─────────────────────────────────────────
async function loadSocioProjectDetail(projectId) {
  hideErr('detailError');

  try {
    const data    = await requestJSON(`/socio/projects/${projectId}`, {
      method: 'GET',
      headers: { ...getAuthHeaders() },
    });
    const project = data.project;

    document.getElementById('projectDetailPanel').style.display = 'block';
    document.getElementById('generateCodePanel').style.display  = 'block';
    document.getElementById('studentsPanel').style.display      = 'block';

    document.getElementById('projectDetailPanel').classList.add('soc-fade-up');

    const titleEl = document.getElementById('detailProjectName');
    if (titleEl) titleEl.textContent = project.name || 'Proyecto';

    const descEl = document.getElementById('detailProjectDescription');
    if (descEl) descEl.textContent = project.description || '';

    const capacity  = project.capacity       ?? 0;
    const taken     = project.taken_slots    ?? 0;
    const available = project.remaining_slots ?? 0;

    animateValue('statCapacity',  0, capacity,  800);
    animateValue('statTaken',     0, taken,      800);
    animateValue('statRemaining', 0, available,  800);

    const gaugeFill         = document.getElementById('gaugeFill');
    const statTakenGauge    = document.getElementById('statTakenGauge');
    const statCapacityGauge = document.getElementById('statCapacityGauge');

    if (gaugeFill && statTakenGauge && statCapacityGauge) {
      const pct = capacity > 0 ? Math.min(taken / capacity, 1) : 0;
      setTimeout(() => {
        gaugeFill.style.strokeDashoffset = 125.66 * (1 - pct);
        gaugeFill.style.stroke =
          pct >= 0.9 ? '#f87171' :
          pct >= 0.7 ? '#fbbf24' :
          '#818cf8';
      }, 100);
      animateValue('statTakenGauge', 0, taken, 1000);
      statCapacityGauge.textContent = capacity;
    }
  } catch (err) {
    showErr('detailError', err.message);
  }
}

// ── Animate counter ────────────────────────────────────────
function animateValue(id, start, end, duration) {
  const el = document.getElementById(id);
  if (!el) return;
  const range    = end - start;
  if (range === 0) { el.textContent = end; return; }
  const stepTime = Math.max(Math.abs(Math.floor(duration / range)), 50);
  const endTime  = Date.now() + duration;
  const timer    = setInterval(() => {
    const remaining = Math.max((endTime - Date.now()) / duration, 0);
    const value     = Math.round(end - remaining * range);
    el.textContent  = value;
    if (value === end) clearInterval(timer);
  }, stepTime);
}

// ── Generate code ──────────────────────────────────────────
async function generateSocioCode(projectId) {
  hideErr('generateCodeError');

  const btn = document.getElementById('quickGenerateCodeBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Generando...'; }

  try {
    const data = await requestJSON('/socio/temp-codes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ project_id: projectId, expires_in_minutes: 10 }),
    });

    const code      = data.temp_code?.code      || '—';
    const expiresAt = formatDate(data.temp_code?.expires_at);

    const wrapper = document.getElementById('codeDisplayWrapper');
    if (wrapper) wrapper.classList.add('visible');

    const codeEl = document.getElementById('currentCodeDisplay');
    if (codeEl) { codeEl.textContent = code; codeEl.classList.add('soc-fade-up'); }

    const expiryEl = document.getElementById('codeExpiryDisplay');
    if (expiryEl) expiryEl.textContent = `Expira: ${expiresAt}`;

    await loadSocioProjectDetail(projectId);
  } catch (err) {
    showErr('generateCodeError', err.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Crear nuevo código'; }
  }
}

// ── Load students ──────────────────────────────────────────
async function loadSocioStudents(projectId) {
  const tbody = document.getElementById('studentsTableBody');
  if (!tbody) return;
  hideErr('studentsError');

  tbody.innerHTML = `
    <tr>
      <td colspan="5" style="padding:2rem 1rem;">
        <div class="soc-skeleton" style="height:16px;width:60%;margin:0 auto;"></div>
      </td>
    </tr>
  `;

  try {
    const data     = await requestJSON(`/socio/projects/${projectId}/students`, {
      method: 'GET',
      headers: { ...getAuthHeaders() },
    });
    const students = data.students || [];

    if (students.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5">
            <div class="soc-empty">
              <div class="soc-empty-icon">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
              </div>
              <strong>Sin estudiantes aún</strong>
              <p>Genera un código para que los estudiantes se registren.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = students.map((s) => {
      const badgeClass = s.status === 'registered' ? 'soc-badge-ok' : 'soc-badge-pending';
      return `
        <tr>
          <td><code>${escapeHtml(s.matricula || '—')}</code></td>
          <td>${escapeHtml(s.email || '—')}</td>
          <td><strong>${escapeHtml(s.full_name || '—')}</strong></td>
          <td><span class="soc-badge ${badgeClass}">${escapeHtml(s.status || '—')}</span></td>
          <td>${formatDate(s.registered_at)}</td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    tbody.innerHTML = '';
    showErr('studentsError', err.message);
  }
}

// ── Export CSV ─────────────────────────────────────────────
function exportSocioStudents(projectId) {
  const token = localStorage.getItem('token');
  if (!token) { alert('No hay sesión activa.'); return; }

  const btn = document.getElementById('exportStudentsBtn');
  if (btn) { btn.disabled = true; btn.textContent = 'Exportando...'; }

  fetch(`/socio/projects/${projectId}/students/export`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(async (res) => {
      if (!res.ok) {
        const d   = await res.json().catch(() => ({}));
        throw new Error(d.detail || 'No se pudo exportar el CSV.');
      }
      return res.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a   = Object.assign(document.createElement('a'), {
        href: url,
        download: `estudiantes_${projectId}_${new Date().toISOString().split('T')[0]}.csv`,
      });
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    })
    .catch((err) => showErr('studentsError', err.message))
    .finally(() => {
      if (btn) { btn.disabled = false; btn.textContent = 'Exportar CSV'; }
    });
}

// ── Init ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Datos del usuario
  requestJSON('/auth/me', { headers: getAuthHeaders() })
    .then((me) => {
      localStorage.setItem('user', JSON.stringify(me));
      const span = document.getElementById('orgNameSpan');
      if (span && me.organization_name) span.textContent = me.organization_name;
      const roleEl = document.getElementById('userRoleDisplay');
      if (roleEl) roleEl.textContent = `Socio Formador · ${me.organization_name || ''}`;
    })
    .catch(() => {
      try {
        const usr  = JSON.parse(localStorage.getItem('user') || '{}');
        const span = document.getElementById('orgNameSpan');
        if (span && usr.organization_name) span.textContent = usr.organization_name;
      } catch (_) {}
    });

  // Botones
  document.getElementById('quickGenerateCodeBtn')?.addEventListener('click', async (e) => {
    e.preventDefault();
    const id = localStorage.getItem('selectedProjectId');
    if (!id) { showErr('generateCodeError', 'Primero selecciona un proyecto.'); return; }
    await generateSocioCode(id);
  });

  document.getElementById('refreshDetailBtn')?.addEventListener('click', async () => {
    const id = localStorage.getItem('selectedProjectId');
    if (id) await loadSocioProjectDetail(id);
  });

  document.getElementById('refreshStudentsBtn')?.addEventListener('click', async () => {
    const id = localStorage.getItem('selectedProjectId');
    if (id) await loadSocioStudents(id);
  });

  document.getElementById('exportStudentsBtn')?.addEventListener('click', () => {
    const id = localStorage.getItem('selectedProjectId');
    if (!id) { showErr('studentsError', 'Primero selecciona un proyecto.'); return; }
    exportSocioStudents(id);
  });

  // Cargar proyectos y restaurar estado previo
  if (document.getElementById('projectsContainer')) {
    loadSocioProjects().then(async () => {
      const id = localStorage.getItem('selectedProjectId');
      if (!id) return;
      const btn = document.querySelector(`.open-project-btn[data-project-id="${id}"]`);
      if (btn) {
        btn.textContent = 'Ocultar detalles';
        btn.classList.replace('soc-btn-outline', 'soc-btn-primary');
        btn.closest('.soc-project-card')?.classList.add('selected');
      }
      await loadSocioProjectDetail(id);
      await loadSocioStudents(id);
    });
  }
});
