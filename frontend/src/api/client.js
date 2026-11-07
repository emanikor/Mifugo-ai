/**
 * Thin fetch wrapper for the Mifugo AI backend.
 *
 * VITE_API_BASE_URL is injected via docker-compose.yml environment, and
 * always points at localhost/the Docker network — never a remote host.
 * This is the ONLY file that should know the backend's URL; everything
 * else calls the named functions here.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("mifugo_token");
}

export function setToken(token) {
  localStorage.setItem("mifugo_token", token);
}

export function clearToken() {
  localStorage.removeItem("mifugo_token");
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (networkError) {
    // Most likely cause on this project: the backend container isn't
    // running, or Docker networking is misconfigured. Not "no internet" —
    // that's expected and fine, this is about reaching the LOCAL backend.
    throw new Error(
      "Could not reach the Mifugo AI backend. Is the backend container running?"
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || `Request failed (${response.status})`);
  }
  return data;
}

// ---- Auth ----
export const login = (username, password) =>
  request("/auth/login", { method: "POST", body: { username, password }, auth: false });

export const me = () => request("/auth/me");

// ---- Lookups ----
export const getRegions = () => request("/regions");
export const getSpecies = () => request("/species");

// ---- Prices ----
export const createPriceEntry = (payload) =>
  request("/prices", { method: "POST", body: payload });

export const getPriceEntries = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/prices${qs ? `?${qs}` : ""}`);
};

export const reviewPriceEntry = (entryId, newStatus) =>
  request(`/prices/${entryId}/review?new_status=${encodeURIComponent(newStatus)}`, {
    method: "PATCH",
  });

// ---- Chat ----
export const askQuestion = (question) =>
  request("/chat", { method: "POST", body: { question } });

// ---- Climate (Milestone 4) ----
export const createClimateBulletin = (payload) =>
  request("/climate", { method: "POST", body: payload });

export const getClimateBulletins = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/climate${qs ? `?${qs}` : ""}`);
};

// ---- Disease reports (Milestone 4) ----
export const createDiseaseReport = (payload) =>
  request("/disease-reports", { method: "POST", body: payload });

export const getDiseaseReports = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/disease-reports${qs ? `?${qs}` : ""}`);
};

export const reviewDiseaseReport = (reportId, newStatus, reviewNotes) => {
  const qs = new URLSearchParams({
    new_status: newStatus,
    ...(reviewNotes ? { review_notes: reviewNotes } : {}),
  }).toString();
  return request(`/disease-reports/${reportId}/review?${qs}`, { method: "PATCH" });
};

// ---- Alerts (Milestone 4) ----
export const getAlerts = () => request("/alerts");

// ---- Health ----
export const checkHealth = () => request("/health", { auth: false });
