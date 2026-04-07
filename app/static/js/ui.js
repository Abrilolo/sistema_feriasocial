export function showMessage(elementId, message, type = "error") {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.style.display = "block";
  // Usar textContent para evitar XSS (no interpreta HTML)
  const text = typeof message === "string" ? message : JSON.stringify(message, null, 2);
  el.textContent = text;

  el.className = type === "success" ? "success" : "error";
}

export function hideMessage(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.style.display = "none";
  el.textContent = "";
}

export function safeShow(elementId, display = "block") {
  const el = document.getElementById(elementId);
  if (el) el.style.display = display;
}

export function safeHide(elementId) {
  const el = document.getElementById(elementId);
  if (el) el.style.display = "none";
}

export function formatDate(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return isNaN(date.getTime()) ? isoString : date.toLocaleString();
}

export function badgeLabel(value, trueText = "Sí", falseText = "No") {
  if (value) {
    return `<span class="badge badge-ok">${trueText}</span>`;
  }
  return `<span class="badge badge-off">${falseText}</span>`;
}

// ============================================
// TOAST NOTIFICATIONS
// ============================================

let toastContainer = null;

function getToastContainer() {
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toast-container";
    toastContainer.style.cssText = `
      position: fixed;
      top: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 12px;
      pointer-events: none;
    `;
    document.body.appendChild(toastContainer);
  }
  return toastContainer;
}

// Función auxiliar para crear elementos con textContent seguro
function createSafeTextElement(text, cssText = "") {
  const el = document.createElement("span");
  if (cssText) el.style.cssText = cssText;
  el.textContent = text;
  return el;
}

export function toast(message, type = "info", duration = 4000) {
  const container = getToastContainer();

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.style.cssText = `
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    border-radius: 14px;
    background: ${type === "success" ? "#dcfce7" : type === "error" ? "#fee2e2" : type === "warning" ? "#fef3c7" : "#eff6ff"};
    color: ${type === "success" ? "#166534" : type === "error" ? "#991b1b" : type === "warning" ? "#92400e" : "#1e40af"};
    border: 1px solid ${type === "success" ? "rgba(34, 197, 94, 0.2)" : type === "error" ? "rgba(239, 68, 68, 0.2)" : type === "warning" ? "rgba(245, 158, 11, 0.2)" : "rgba(59, 130, 246, 0.2)"};
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
    backdrop-filter: blur(8px);
    font-weight: 600;
    font-size: 14px;
    animation: slideInRight 0.3s ease;
    pointer-events: auto;
    max-width: 380px;
  `;

  // Usar textContent y crear elementos de forma segura para evitar XSS
  const iconChar = type === "success" ? "✓" : type === "error" ? "✕" : type === "warning" ? "⚠" : "ℹ";
  
  const iconSpan = document.createElement("span");
  iconSpan.style.fontSize = "18px";
  iconSpan.style.lineHeight = "1";
  iconSpan.textContent = iconChar;
  
  const messageSpan = document.createElement("span");
  messageSpan.textContent = message;
  
  toast.appendChild(iconSpan);
  toast.appendChild(messageSpan);

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "fadeOut 0.3s ease forwards";
    setTimeout(() => toast.remove(), 300);
  }, duration);

  return toast;
}

export function toastSuccess(message, duration = 4000) {
  return toast(message, "success", duration);
}

export function toastError(message, duration = 5000) {
  return toast(message, "error", duration);
}

export function toastWarning(message, duration = 5000) {
  return toast(message, "warning", duration);
}

export function toastInfo(message, duration = 4000) {
  return toast(message, "info", duration);
}

// ============================================
// MODAL SYSTEM
// ============================================

export function showModal(options = {}) {
  const {
    title = "",
    content = "",
    showClose = true,
    onClose,
    actions = []
  } = options;

  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.style.cssText = `
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(4px);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: fadeIn 0.2s ease;
  `;

  const modal = document.createElement("div");
  modal.className = "modal-content";
  modal.style.cssText = `
    background: white;
    border-radius: 24px;
    padding: 28px;
    max-width: 520px;
    width: 100%;
    max-height: 85vh;
    overflow-y: auto;
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
    animation: modalSlideUp 0.3s ease;
  `;

  // Construir modal de forma segura usando DOM API en lugar de innerHTML
  modal.innerHTML = ""; // Limpiar contenido previo

  if (title) {
    const titleEl = document.createElement("h2");
    titleEl.style.cssText = "margin: 0 0 12px 0; font-size: 22px; color: #0f172a;";
    titleEl.textContent = title;
    modal.appendChild(titleEl);
  }

  if (content) {
    const contentEl = document.createElement("div");
    contentEl.style.cssText = "color: #475569; line-height: 1.6;";
    // Si el contenido es HTML confiable (como botones internos), se puede usar innerHTML
    // Pero si viene de inputs de usuario, debería ser sanitizado.
    // Para simplificar y dar seguridad, si es string plana usamos textContent.
    if (typeof content === 'string' && !content.includes('<')) {
        contentEl.textContent = content;
    } else {
        contentEl.innerHTML = content;
    }
    modal.appendChild(contentEl);
  }

  if (actions.length > 0) {
    const actionsEl = document.createElement("div");
    actionsEl.style.cssText = "display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px;";
    
    actions.forEach(action => {
      const btn = document.createElement("button");
      btn.className = "modal-action";
      btn.dataset.action = action.id || "";
      btn.textContent = action.label;
      btn.style.cssText = `padding: 12px 20px; border-radius: 12px; font-weight: 600; cursor: pointer; border: none; background: ${action.primary ? 'linear-gradient(135deg, #2563eb, #3b82f6)' : '#e2e8f0'}; color: ${action.primary ? 'white' : '#1e293b'};`;
      actionsEl.appendChild(btn);
    });
    modal.appendChild(actionsEl);
  }

  if (showClose) {
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "✕";
    closeBtn.style.cssText = `
      position: absolute;
      top: 16px;
      right: 16px;
      background: transparent;
      border: none;
      font-size: 20px;
      cursor: pointer;
      color: #64748b;
      padding: 8px;
      border-radius: 8px;
      transition: all 0.2s;
    `;
    closeBtn.onmouseover = () => closeBtn.style.background = "#f1f5f9";
    closeBtn.onmouseout = () => closeBtn.style.background = "transparent";
    closeBtn.onclick = () => closeModal(overlay, onClose);
    modal.appendChild(closeBtn);
  }

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  overlay.onclick = (e) => {
    if (e.target === overlay) {
      closeModal(overlay, onClose);
    }
  };

  // Agregar event listeners a los botones de acción
  const actionButtons = modal.querySelectorAll(".modal-action");
  actionButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const actionId = btn.dataset.action;
      const action = actions.find(a => a.id === actionId);
      if (action && action.onClick) {
        action.onClick();
      }
      closeModal(overlay, onClose);
    });
  });

  return overlay;
}

export function closeModal(overlay, onClose) {
  overlay.style.animation = "fadeOut 0.25s ease forwards";
  setTimeout(() => {
    overlay.remove();
    if (onClose) onClose();
  }, 250);
}

export function confirmModal(options = {}) {
  const {
    title = "¿Estás seguro?",
    content = "",
    confirmText = "Confirmar",
    cancelText = "Cancelar",
    type = "warning",
    onConfirm
  } = options;

  return showModal({
    title,
    content,
    actions: [
      { label: cancelText, primary: false, onClick: () => {} },
      { label: confirmText, primary: true, onClick: onConfirm || (() => {}) }
    ]
  });
}

// ============================================
// PROGRESS BARS
// ============================================

export function createProgressBar(container, options = {}) {
  const {
    value = 0,
    max = 100,
    label,
    showValue = true,
    color = "primary",
    size = "md"
  } = options;

  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const colors = {
    primary: "linear-gradient(135deg, #2563eb, #3b82f6)",
    success: "linear-gradient(135deg, #16a34a, #22c55e)",
    warning: "linear-gradient(135deg, #d97706, #f59e0b)",
    danger: "linear-gradient(135deg, #dc2626, #ef4444)",
    info: "linear-gradient(135deg, #0891b2, #06b6d4)"
  };

  const heights = { sm: "6px", md: "10px", lg: "14px" };

  const wrapper = document.createElement("div");
  wrapper.className = "progress-wrapper";
  wrapper.style.cssText = `width: 100%;`;

  let html = "";
  if (label || showValue) {
    html += `<div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #475569;">`;
    if (label) html += `<span>${label}</span>`;
    if (showValue) html += `<span>${Math.round(percentage)}%</span>`;
    html += `</div>`;
  }

  html += `
    <div style="background: #e2e8f0; border-radius: 99px; overflow: hidden; height: ${heights[size]};">
      <div class="progress-fill" style="
        width: ${percentage}%;
        height: 100%;
        background: ${colors[color] || colors.primary};
        border-radius: 99px;
        transition: width 0.5s ease;
      "></div>
    </div>
  `;

  wrapper.innerHTML = html;

  if (container) {
    container.appendChild(wrapper);
  }

  return { wrapper, update: (newValue) => {
    const newPercentage = Math.min(100, Math.max(0, (newValue / max) * 100));
    wrapper.querySelector(".progress-fill").style.width = `${newPercentage}%`;
    if (showValue) {
      wrapper.querySelector("span:last-child").textContent = `${Math.round(newPercentage)}%`;
    }
  }};
}

// ============================================
// LOADING STATES
// ============================================

export function showLoading(target, options = {}) {
  const {
    message = "Cargando...",
    overlay = false
  } = options;

  const spinner = document.createElement("div");
  spinner.className = "loading-spinner";
  spinner.style.cssText = `
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 32px;
    ${overlay ? `
      position: absolute;
      inset: 0;
      background: rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(4px);
      z-index: 100;
    ` : ""}
  `;

  spinner.innerHTML = `
    <div style="
      width: 42px;
      height: 42px;
      border: 4px solid #e2e8f0;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    "></div>
    ${message ? `<span style="color: #64748b; font-weight: 600; font-size: 14px;">${message}</span>` : ""}
  `;

  if (target) {
    target.style.position = "relative";
    target.appendChild(spinner);
  }

  return spinner;
}

export function hideLoading(spinner) {
  if (spinner && spinner.parentNode) {
    spinner.remove();
  }
}

export function setButtonLoading(button, loading = true, originalText = "") {
  if (loading) {
    button.dataset.originalText = button.textContent;
    button.disabled = true;
    button.innerHTML = `
      <span style="display: inline-flex; align-items: center; gap: 8px;">
        <span style="
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        "></span>
        Procesando...
      </span>
    `;
  } else {
    button.textContent = button.dataset.originalText || originalText;
    button.disabled = false;
  }
}

// ============================================
// ENHANCED BADGES
// ============================================

export function badge(text, variant = "default") {
  const variants = {
    default: { bg: "#e2e8f0", color: "#475569" },
    success: { bg: "#dcfce7", color: "#166534" },
    error: { bg: "#fee2e2", color: "#991b1b" },
    warning: { bg: "#fef3c7", color: "#92400e" },
    info: { bg: "#dbeafe", color: "#1e40af" },
    primary: { bg: "#dbeafe", color: "#1e40af" }
  };

  const v = variants[variant] || variants.default;

  return `<span style="
    display: inline-flex;
    align-items: center;
    padding: 5px 12px;
    border-radius: 99px;
    font-size: 12px;
    font-weight: 700;
    background: ${v.bg};
    color: ${v.color};
  ">${text}</span>`;
}

export function statusBadge(status) {
  const statuses = {
    active: { text: "Activo", variant: "success" },
    inactive: { text: "Inactivo", variant: "error" },
    pending: { text: "Pendiente", variant: "warning" },
    full: { text: "Lleno", variant: "error" },
    available: { text: "Disponible", variant: "success" }
  };

  const s = statuses[status] || { text: status, variant: "default" };
  return badge(s.text, s.variant);
}

// ============================================
// CARD ANIMATIONS
// ============================================

export function fadeInUp(element, delay = 0) {
  if (!element) return;
  element.style.opacity = "0";
  element.style.transform = "translateY(20px)";
  element.style.transition = `opacity 0.4s ease ${delay}s, transform 0.4s ease ${delay}s`;

  requestAnimationFrame(() => {
    element.style.opacity = "1";
    element.style.transform = "translateY(0)";
  });
}

export function staggerAnimate(elements, options = {}) {
  const {
    delay = 0,
    stagger = 0.1,
    type = "fadeUp"
  } = options;

  elements.forEach((el, index) => {
    fadeInUp(el, delay + (index * stagger));
  });
}

// ============================================
// UTILITY COMPONENTS
// ============================================

export function emptyState(options = {}) {
  const {
    icon = "📭",
    title = "Sin datos",
    message = "",
    action
  } = options;

  return `
    <div style="
      text-align: center;
      padding: 48px 24px;
      color: #64748b;
    ">
      <div style="font-size: 48px; margin-bottom: 16px;">${icon}</div>
      <h3 style="margin: 0 0 8px 0; color: #334155; font-size: 18px;">${title}</h3>
      ${message ? `<p style="margin: 0 0 24px 0; font-size: 14px;">${message}</p>` : ""}
      ${action ? `<button style="
        padding: 12px 24px;
        background: linear-gradient(135deg, #2563eb, #3b82f6);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      ">${action.label}</button>` : ""}
    </div>
  `;
}

export function tooltip(element, content, options = {}) {
  const { position = "top" } = options;

  const tooltip = document.createElement("div");
  tooltip.className = "tooltip";
  tooltip.textContent = content;
  tooltip.style.cssText = `
    position: absolute;
    background: #1e293b;
    color: white;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    z-index: 1000;
    pointer-events: none;
    opacity: 0;
    transform: translateY(4px);
    transition: opacity 0.2s, transform 0.2s;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  `;

  const positions = {
    top: { bottom: "100%", left: "50%", transform: "translateX(-50%) translateY(-4px)" },
    bottom: { top: "100%", left: "50%", transform: "translateX(-50%) translateY(4px)" },
    left: { right: "100%", top: "50%", transform: "translateY(-50%) translateX(-4px)" },
    right: { left: "100%", top: "50%", transform: "translateY(-50%) translateX(4px)" }
  };

  Object.assign(tooltip.style, positions[position]);

  element.style.position = "relative";
  element.appendChild(tooltip);

  element.addEventListener("mouseenter", () => {
    tooltip.style.opacity = "1";
    tooltip.style.transform = positions[position].transform;
  });

  element.addEventListener("mouseleave", () => {
    tooltip.style.opacity = "0";
    tooltip.style.transform = positions[position].transform + " translateY(4px)";
  });

  return tooltip;
}

// ============================================
// ANIMATION STYLES (inject once)
// ============================================

if (!document.getElementById("ui-animations-styles")) {
  const style = document.createElement("style");
  style.id = "ui-animations-styles";
  style.textContent = `
    @keyframes slideInRight {
      from { opacity: 0; transform: translateX(20px); }
      to { opacity: 1; transform: translateX(0); }
    }
    @keyframes fadeOut {
      from { opacity: 1; }
      to { opacity: 0; }
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    @keyframes modalSlideUp {
      from { opacity: 0; transform: translateY(30px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `;
  document.head.appendChild(style);
}