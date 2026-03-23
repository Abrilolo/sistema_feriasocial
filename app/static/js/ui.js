export function showMessage(elementId, message, type = "error") {
  const el = document.getElementById(elementId);
  if (!el) return;

  el.style.display = "block";
  el.textContent =
    typeof message === "string" ? message : JSON.stringify(message, null, 2);

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
