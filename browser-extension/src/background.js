/**
 * Background service worker for PWBS Browser Extension (TASK-140).
 *
 * Manages communication between content scripts and the side panel.
 * Stores the latest page context for when the side panel opens.
 */

import { getToken, search, getRelatedEntities } from "./api.js";

/** @type {{ site: string, title: string } | null} */
let currentPageContext = null;

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener(async (tab) => {
  const token = await getToken();
  if (token) {
    await chrome.sidePanel.open({ tabId: tab.id });
  }
  // If no token, popup.html handles login
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PAGE_CONTEXT_UPDATE") {
    currentPageContext = message.payload;
    // Forward to side panel if open
    chrome.runtime.sendMessage({
      type: "CONTEXT_UPDATED",
      payload: currentPageContext,
    }).catch(() => {
      // Side panel not open, ignore
    });
  }

  if (message.type === "GET_CURRENT_CONTEXT") {
    sendResponse({ context: currentPageContext });
    return true;
  }

  if (message.type === "SEARCH_REQUEST") {
    handleSearch(message.payload.query, message.payload.topK)
      .then((results) => sendResponse({ results }))
      .catch((err) => sendResponse({ error: err.message }));
    return true; // async sendResponse
  }

  if (message.type === "ENTITIES_REQUEST") {
    handleEntities(message.payload.query)
      .then((entities) => sendResponse({ entities }))
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }
});

/**
 * Perform semantic search via API.
 * @param {string} query
 * @param {number} [topK=5]
 */
async function handleSearch(query, topK = 5) {
  return search(query, topK);
}

/**
 * Fetch related entities via API.
 * @param {string} query
 */
async function handleEntities(query) {
  return getRelatedEntities(query);
}