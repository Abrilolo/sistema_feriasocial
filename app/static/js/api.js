/**
 * Escapa caracteres HTML especiales para prevenir XSS.
 * Usar antes de insertar contenido dinámico en innerHTML.
 */
export function escapeHtml(text) {
  if (text === null || text === undefined) {
    return '';
  }
  const str = String(text);
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Crea un elemento DOM de forma segura con contenido escapado.
 * Alternativa segura a innerHTML.
 */
export function createSafeElement(tag, attributes = {}, textContent = '') {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (key === 'className') {
      element.className = value;
    } else if (key.startsWith('data-')) {
      element.setAttribute(key, value);
    } else if (key.startsWith('on')) {
      // No permitir event handlers inline (seguridad)
      continue;
    } else {
      element.setAttribute(key, value);
    }
  }
  if (textContent) {
    element.textContent = textContent;
  }
  return element;
}

export async function requestJSON(url, options = {}) {
  // Add default JSON header if body exists and is a string
  if (options.body && typeof options.body === 'string') {
    options.headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };
  }
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
