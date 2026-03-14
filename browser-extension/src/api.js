/**
 * PWBS API Client for Browser Extension (TASK-140).
 *
 * Handles JWT-based authentication and API calls to the PWBS backend.
 * Tokens are stored in chrome.storage.local for persistence.
 */

const STORAGE_KEY_TOKEN = "pwbs_jwt_token";
const STORAGE_KEY_API_URL = "pwbs_api_url";
const DEFAULT_API_URL = "http://localhost:8000/api/v1";

/**
 * Retrieve the stored JWT token.
 * @returns {Promise<string|null>}
 */
export async function getToken() {
  const data = await chrome.storage.local.get(STORAGE_KEY_TOKEN);
  return data[STORAGE_KEY_TOKEN] || null;
}

/**
 * Store the JWT token.
 * @param {string} token
 */
export async function setToken(token) {
  await chrome.storage.local.set({ [STORAGE_KEY_TOKEN]: token });
}

/**
 * Remove stored token (logout).
 */
export async function clearToken() {
  await chrome.storage.local.remove(STORAGE_KEY_TOKEN);
}

/**
 * Get the configured API base URL.
 * @returns {Promise<string>}
 */
export async function getApiUrl() {
  const data = await chrome.storage.local.get(STORAGE_KEY_API_URL);
  return data[STORAGE_KEY_API_URL] || DEFAULT_API_URL;
}

/**
 * Set the API base URL.
 * @param {string} url
 */
export async function setApiUrl(url) {
  await chrome.storage.local.set({ [STORAGE_KEY_API_URL]: url });
}

/**
 * Make an authenticated API request to PWBS backend.
 * @param {string} path - API path (e.g. "/search")
 * @param {object} [options] - fetch options
 * @returns {Promise<object>} Parsed JSON response
 * @throws {Error} On auth failure or network error
 */
export async function apiFetch(path, options = {}) {
  const token = await getToken();
  if (!token) {
    throw new Error("Nicht authentifiziert. Bitte zuerst anmelden.");
  }

  const baseUrl = await getApiUrl();
  const url = `${baseUrl}${path}`;

  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    await clearToken();
    throw new Error("Token abgelaufen. Bitte erneut anmelden.");
  }

  if (!response.ok) {
    const detail = await response.text().catch(() => "Unbekannter Fehler");
    throw new Error(`API-Fehler ${response.status}: ${detail}`);
  }

  return response.json();
}

/**
 * Perform a semantic search via the PWBS Search API.
 * @param {string} query - Search query text
 * @param {number} [topK=5] - Number of results
 * @returns {Promise<object>} Search results
 */
export async function search(query, topK = 5) {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  return apiFetch(`/search?${params}`);
}

/**
 * Fetch entities related to a search query.
 * @param {string} query
 * @returns {Promise<object>} Knowledge/entities response
 */
export async function getRelatedEntities(query) {
  const params = new URLSearchParams({ q: query, limit: "10" });
  return apiFetch(`/knowledge/entities?${params}`);
}