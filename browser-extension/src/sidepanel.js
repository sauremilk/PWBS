/**
 * Side panel script for PWBS Browser Extension (TASK-140).
 *
 * Shows contextual information from the PWBS knowledge base:
 * - Entities related to the current page
 * - Related documents from other sources
 * - Quick search functionality
 */

const STORAGE_KEY_TOKEN = "pwbs_jwt_token";

// DOM elements
const notAuthEl = document.getElementById("not-auth");
const mainContent = document.getElementById("main-content");
const contextBar = document.getElementById("context-bar");
const ctxSite = document.getElementById("ctx-site");
const ctxTitle = document.getElementById("ctx-title");
const searchInput = document.getElementById("search-input");
const btnSearch = document.getElementById("btn-search");
const entitiesList = document.getElementById("entities-list");
const docsList = document.getElementById("docs-list");

/** Current page context from content script */
let pageContext = null;

// ----------------------------------------------------------------
// Auth check
// ----------------------------------------------------------------

async function checkAuth() {
  const data = await chrome.storage.local.get(STORAGE_KEY_TOKEN);
  if (data[STORAGE_KEY_TOKEN]) {
    notAuthEl.style.display = "none";
    mainContent.style.display = "block";
    requestPageContext();
  } else {
    notAuthEl.style.display = "block";
    mainContent.style.display = "none";
  }
}

// ----------------------------------------------------------------
// Context from content script
// ----------------------------------------------------------------

function requestPageContext() {
  chrome.runtime.sendMessage({ type: "GET_CURRENT_CONTEXT" }, (response) => {
    if (response && response.context) {
      updateContext(response.context);
    }
  });
}

function updateContext(ctx) {
  pageContext = ctx;
  ctxSite.textContent = ctx.site === "notion" ? "Notion" : "Google Docs";
  ctxTitle.textContent = ctx.title;
  contextBar.style.display = "block";
  searchInput.value = ctx.title;
  loadContextData(ctx.title);
}

// ----------------------------------------------------------------
// Data loading
// ----------------------------------------------------------------

async function loadContextData(query) {
  loadEntities(query);
  loadDocuments(query);
}

async function loadEntities(query) {
  entitiesList.innerHTML = '<span class="loading">Lade Entitaeten...</span>';
  chrome.runtime.sendMessage(
    { type: "ENTITIES_REQUEST", payload: { query } },
    (response) => {
      if (response && response.error) {
        entitiesList.innerHTML = '<span class="error">' + escapeHtml(response.error) + '</span>';
        return;
      }
      if (response && response.entities) {
        renderEntities(response.entities);
      } else {
        entitiesList.innerHTML = '<span class="empty">Keine Entitaeten gefunden</span>';
      }
    }
  );
}

async function loadDocuments(query) {
  docsList.innerHTML = '<span class="loading">Suche Dokumente...</span>';
  chrome.runtime.sendMessage(
    { type: "SEARCH_REQUEST", payload: { query, topK: 5 } },
    (response) => {
      if (response && response.error) {
        docsList.innerHTML = '<span class="error">' + escapeHtml(response.error) + '</span>';
        return;
      }
      if (response && response.results) {
        renderDocuments(response.results);
      } else {
        docsList.innerHTML = '<span class="empty">Keine Dokumente gefunden</span>';
      }
    }
  );
}

// ----------------------------------------------------------------
// Rendering
// ----------------------------------------------------------------

function renderEntities(data) {
  const entities = data.items || data.entities || data;
  if (!Array.isArray(entities) || entities.length === 0) {
    entitiesList.innerHTML = '<span class="empty">Keine Entitaeten gefunden</span>';
    return;
  }
  entitiesList.innerHTML = entities.map((e) => {
    const type = (e.entity_type || e.type || "topic").toLowerCase();
    const cssClass = ["person", "project", "decision"].includes(type) ? type : "";
    const name = escapeHtml(e.name || e.entity_name || "Unbekannt");
    return '<span class="entity-tag ' + cssClass + '">' + name + '</span>';
  }).join("");
}

function renderDocuments(data) {
  const results = data.results || data.items || data;
  if (!Array.isArray(results) || results.length === 0) {
    docsList.innerHTML = '<span class="empty">Keine Dokumente gefunden</span>';
    return;
  }
  docsList.innerHTML = results.map((doc) => {
    const title = escapeHtml(doc.title || "Ohne Titel");
    const source = escapeHtml(doc.source_type || doc.source || "");
    const date = escapeHtml(doc.created_at || doc.date || "");
    const snippet = escapeHtml((doc.content || "").substring(0, 150));
    return '<div class="card">' +
      '<div class="title">' + title + '</div>' +
      '<div class="meta">' + source + (date ? ' - ' + date : '') + '</div>' +
      (snippet ? '<div class="snippet">' + snippet + '...</div>' : '') +
      '</div>';
  }).join("");
}

// ----------------------------------------------------------------
// Search
// ----------------------------------------------------------------

btnSearch.addEventListener("click", () => {
  const query = searchInput.value.trim();
  if (query) {
    loadContextData(query);
  }
});

searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const query = searchInput.value.trim();
    if (query) {
      loadContextData(query);
    }
  }
});

// ----------------------------------------------------------------
// Message listener (context updates from content script)
// ----------------------------------------------------------------

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "CONTEXT_UPDATED" && message.payload) {
    updateContext(message.payload);
  }
});

// ----------------------------------------------------------------
// Utilities
// ----------------------------------------------------------------

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Init
checkAuth();