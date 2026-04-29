import { requestJSON } from './api.js';
import { toast, setButtonLoading } from './ui.js';

let form, matriculaInput, matriculaStatus, careerInput, careerValueInput;
let careerDropdown, careerStatusEl, errorDiv, submitBtn;
let careers = [];
let matriculaCheckTimeout;

function initializeDOM() {
  form = document.getElementById('preregForm');
  matriculaInput = document.getElementById('matricula');
  matriculaStatus = document.getElementById('matriculaStatus');
  careerInput = document.getElementById('career_id');
  careerValueInput = document.getElementById('career_id_value');
  careerDropdown = document.getElementById('careerDropdown');
  careerStatusEl = document.getElementById('careerStatus');
  errorDiv = document.getElementById('preregError');
  submitBtn = document.getElementById('submitBtn');

  if (!form) {
    console.error('preregForm not found');
    return false;
  }
  return true;
}

async function loadCareers() {
  try {
    careers = await requestJSON('/public/careers', {
      method: 'GET'
    });
  } catch (err) {
    console.error('Error loading careers:', err);
    toast('Error al cargar carreras', 'error');
  }
}

function setupEventListeners() {
  // Validar matrícula en tiempo real
  matriculaInput.addEventListener('input', async (e) => {
    clearTimeout(matriculaCheckTimeout);
    const value = e.target.value.trim().toUpperCase();

    if (!value) {
      matriculaStatus.textContent = '';
      return;
    }

    matriculaStatus.textContent = 'Verificando...';
    matriculaStatus.className = 'input-status checking';

    matriculaCheckTimeout = setTimeout(async () => {
      try {
        const res = await requestJSON(`/public/check-matricula/${value}`, {
          method: 'GET'
        });

        if (res.exists) {
          matriculaStatus.textContent = 'Matrícula ya registrada';
          matriculaStatus.className = 'input-status error';
          matriculaInput.classList.add('input-error');
          submitBtn.disabled = true;
        } else {
          matriculaStatus.textContent = 'Matrícula disponible';
          matriculaStatus.className = 'input-status success';
          matriculaInput.classList.remove('input-error');
          submitBtn.disabled = false;
        }
      } catch (err) {
        console.error('Error checking matricula:', err);
      }
    }, 500);
  });

  // Búsqueda de carreras
  careerInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();

    if (!query) {
      careerDropdown.style.display = 'none';
      careerValueInput.value = '';
      return;
    }

    const filtered = careers.filter(
      (c) =>
        c.nombre_carrera.toLowerCase().includes(query) ||
        c.siglas.toLowerCase().includes(query) ||
        c.escuela.toLowerCase().includes(query)
    );

    if (filtered.length === 0) {
      careerDropdown.innerHTML = '<div class="dropdown-empty">No se encontraron carreras</div>';
      careerDropdown.style.display = 'block';
      return;
    }

    careerDropdown.innerHTML = filtered
      .map(
        (c) => `
      <div class="dropdown-item" data-id="${c.id}">
        <div class="dropdown-title">${c.nombre_carrera}</div>
        <div class="dropdown-subtitle">${c.siglas} • ${c.escuela}</div>
      </div>
    `
      )
      .join('');

    careerDropdown.style.display = 'block';

    document.querySelectorAll('.dropdown-item').forEach((item) => {
      item.addEventListener('click', () => {
        const id = item.getAttribute('data-id');
        const career = careers.find((c) => c.id === id);
        if (career) {
          careerInput.value = career.nombre_carrera;
          careerValueInput.value = career.id;
          careerDropdown.style.display = 'none';
          careerStatusEl.textContent = 'Seleccionado';
          careerStatusEl.className = 'input-status success';
        }
      });
    });
  });

  // Cerrar dropdown al hacer click afuera
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.form-group')) {
      careerDropdown.style.display = 'none';
    }
  });

  // Enviar formulario
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorDiv.style.display = 'none';

    const formData = {
      matricula: matriculaInput.value.trim().toUpperCase(),
      email: document.getElementById('email').value.trim().toLowerCase(),
      full_name: document.getElementById('full_name').value.trim(),
      phone: document.getElementById('phone').value.trim(),
      career_id: careerValueInput.value || null,
    };

    setButtonLoading(submitBtn, true);

    try {
      const res = await requestJSON('/public/preregister', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (res.ok) {
        setButtonLoading(submitBtn, false);
        toast(res.message, 'success');

        // Mostrar formulario de éxito con botón para Google OAuth
        form.style.display = 'none';
        const successDiv = document.createElement('div');
        successDiv.innerHTML = `
          <div style="text-align: center; padding: 2rem;">
            <div style="font-size: 1.1rem; color: #059669; margin-bottom: 1rem; font-weight: 600;">
              Pre-registro completado exitosamente
            </div>
            <p style="color: #64748b; margin-bottom: 1.5rem; font-size: 0.95rem;">
              Tu matrícula <strong>${formData.matricula}</strong> ha sido registrada.
              Ahora inicia sesión con tu cuenta institucional.
            </p>
            <a href="/auth/google/login" class="est-google-btn" style="display: inline-flex; gap: 11px;">
              <svg viewBox="0 0 24 24" style="width: 19px; height: 19px; flex-shrink: 0;">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Continuar con Google
            </a>
          </div>
        `;
        form.parentElement.appendChild(successDiv);
      }
    } catch (err) {
      setButtonLoading(submitBtn, false);
      const errMsg = err.message || 'Error al registrar';
      errorDiv.textContent = errMsg;
      errorDiv.style.display = 'block';
      toast(errMsg, 'error');
    }
  });
}

// Ejecutar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

function init() {
  if (!initializeDOM()) {
    console.error('Failed to initialize DOM elements');
    return;
  }
  loadCareers();
  setupEventListeners();
}
