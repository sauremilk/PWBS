/**
 * Popup script for PWBS Browser Extension (TASK-140).
 * Handles JWT token input and API URL configuration.
 */

const STORAGE_KEY_TOKEN = "pwbs_jwt_token";
const STORAGE_KEY_API_URL = "pwbs_api_url";

const statusEl = document.getElementById("status");
const loginForm = document.getElementById("login-form");
const loggedInEl = document.getElementById("logged-in");
const apiUrlInput = document.getElementById("api-url");
const tokenInput = document.getElementById("token");
const btnSave = document.getElementById("btn-save");
const btnLogout = document.getElementById("btn-logout");

function showStatus(text, ok) {
  statusEl.textContent = text;
  statusEl.className = "status " + (ok ? "ok" : "err");
  statusEl.style.display = "block";
}

async function checkAuth() {
  const data = await chrome.storage.local.get([STORAGE_KEY_TOKEN, STORAGE_KEY_API_URL]);
  if (data[STORAGE_KEY_TOKEN]) {
    loginForm.style.display = "none";
    loggedInEl.style.display = "block";
    showStatus("Verbunden", true);
  } else {
    loginForm.style.display = "block";
    loggedInEl.style.display = "none";
  }
  if (data[STORAGE_KEY_API_URL]) {
    apiUrlInput.value = data[STORAGE_KEY_API_URL];
  }
}

btnSave.addEventListener("click", async () => {
  const token = tokenInput.value.trim();
  const apiUrl = apiUrlInput.value.trim();

  if (!token) {
    showStatus("Bitte JWT-Token eingeben", false);
    return;
  }
  if (!apiUrl) {
    showStatus("Bitte API-URL eingeben", false);
    return;
  }

  await chrome.storage.local.set({
    [STORAGE_KEY_TOKEN]: token,
    [STORAGE_KEY_API_URL]: apiUrl,
  });

  showStatus("Token gespeichert", true);
  loginForm.style.display = "none";
  loggedInEl.style.display = "block";
});

btnLogout.addEventListener("click", async () => {
  await chrome.storage.local.remove(STORAGE_KEY_TOKEN);
  loginForm.style.display = "block";
  loggedInEl.style.display = "none";
  statusEl.style.display = "none";
  tokenInput.value = "";
});

checkAuth();