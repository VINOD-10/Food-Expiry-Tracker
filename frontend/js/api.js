// Thin fetch wrapper: timeouts, JSON handling and normalised errors.
const TIMEOUT_MS = 15000;

export class ApiError extends Error {
  constructor(message, { status = 0, fields = {}, network = false } = {}) {
    super(message);
    this.status = status;
    this.fields = fields;
    this.network = network;
  }
}

export function newRequestKey() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return `k${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`;
}

async function request(method, path, { body, params, headers } = {}) {
  const url = new URL(path, location.origin);
  for (const [key, value] of Object.entries(params || {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response;
  try {
    response = await fetch(url, {
      method,
      headers: { Accept: "application/json", ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (error) {
    const timedOut = error.name === "AbortError";
    throw new ApiError(
      timedOut ? "The server took too long to respond. Please try again." : "Can't reach the server. Check your connection and that the backend is running.",
      { network: true },
    );
  } finally {
    clearTimeout(timer);
  }
  let data = null;
  const text = await response.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = null; }
  }
  if (!response.ok) {
    const error = data?.error;
    // A 401 outside the auth endpoints means the session ended: the app shows the login page.
    if (response.status === 401 && !path.startsWith("/api/auth/")) window.dispatchEvent(new Event("fet:unauthorized"));
    throw new ApiError(error?.message || `Request failed (${response.status})`, { status: response.status, fields: error?.fields || {} });
  }
  if (data === null) throw new ApiError("The server sent an unexpected response.", { status: response.status });
  return data;
}

export const api = {
  get: (path, params) => request("GET", path, { params }),
  post: (path, body, headers) => request("POST", path, { body, headers }),
  put: (path, body) => request("PUT", path, { body }),
  patch: (path, body) => request("PATCH", path, { body }),
  del: (path, params) => request("DELETE", path, { params }),
};
