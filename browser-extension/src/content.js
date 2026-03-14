/**
 * Content script for PWBS Browser Extension (TASK-140).
 *
 * Runs on Notion and Google Docs pages. Extracts the current page
 * title/context and sends it to the background service worker
 * for sidebar updates.
 */

/**
 * Extract page title from Notion.
 * @returns {string|null}
 */
function extractNotionTitle() {
  // Notion renders the page title in a specific heading element
  const titleEl =
    document.querySelector(".notion-page-block .notranslate") ||
    document.querySelector('[data-block-id] [placeholder="Untitled"]') ||
    document.querySelector("header h1") ||
    document.querySelector(".notion-frame .notion-page-content h1");

  if (titleEl && titleEl.textContent) {
    return titleEl.textContent.trim();
  }

  // Fallback: use document.title (format: "Page Title - Notion")
  const docTitle = document.title || "";
  if (docTitle.includes(" - Notion")) {
    return docTitle.replace(/ - Notion$/, "").trim();
  }
  return docTitle || null;
}

/**
 * Extract page title from Google Docs.
 * @returns {string|null}
 */
function extractGoogleDocsTitle() {
  const titleInput = document.querySelector('input.docs-title-input[type="text"]');
  if (titleInput && titleInput.value) {
    return titleInput.value.trim();
  }

  const docTitle = document.title || "";
  if (docTitle.includes(" - Google")) {
    return docTitle.replace(/ - Google [\w]+$/, "").trim();
  }
  return docTitle || null;
}

/**
 * Detect which supported site we are on and extract context.
 * @returns {{ site: string, title: string } | null}
 */
function extractPageContext() {
  const url = window.location.href;

  if (url.includes("notion.so")) {
    const title = extractNotionTitle();
    return title ? { site: "notion", title } : null;
  }

  if (url.includes("docs.google.com")) {
    const title = extractGoogleDocsTitle();
    return title ? { site: "google_docs", title } : null;
  }

  return null;
}

/**
 * Send the current page context to the background service worker.
 */
function notifyBackground() {
  const context = extractPageContext();
  if (context) {
    chrome.runtime.sendMessage({
      type: "PAGE_CONTEXT_UPDATE",
      payload: context,
    });
  }
}

// Initial extraction after page load
notifyBackground();

// Re-extract on title changes (Notion uses client-side navigation)
let lastTitle = document.title;
const observer = new MutationObserver(() => {
  if (document.title !== lastTitle) {
    lastTitle = document.title;
    notifyBackground();
  }
});
observer.observe(document.querySelector("title") || document.head, {
  childList: true,
  subtree: true,
  characterData: true,
});

// Listen for explicit requests from the sidebar/popup
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "GET_PAGE_CONTEXT") {
    const context = extractPageContext();
    sendResponse({ context });
  }
});