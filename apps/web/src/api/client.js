/**
 * Auth-aware fetch wrapper for the ESG SCRM API.
 * All API calls should go through apiFetch() instead of raw fetch().
 */

const TOKEN_KEY = "esg_token";

export class AuthError extends Error {
  constructor(message) {
    super(message);
    this.name = "AuthError";
  }
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function refreshOnce() {
  const token = getToken();
  if (!token) return false;

  try {
    const res = await fetch("/api/auth/refresh", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return false;
    const data = await res.json();
    setToken(data.token);
    return true;
  } catch {
    return false;
  }
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...options.headers };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = path.startsWith("/api") ? path : `/api${path}`;
  let response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    const refreshed = await refreshOnce();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getToken()}`;
      response = await fetch(url, { ...options, headers });
    } else {
      clearToken();
      window.dispatchEvent(new CustomEvent("auth:logout"));
      throw new AuthError("Session expired. Please log in again.");
    }
  }

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new ApiError(
      response.status,
      text || `Request failed (${response.status})`,
    );
  }

  return response;
}

export { getToken, setToken, clearToken };
