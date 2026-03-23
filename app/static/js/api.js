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
