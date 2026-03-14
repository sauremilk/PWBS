/**
 * Notion-specific content extraction for PWBS Browser Extension (TASK-142).
 *
 * Enhanced extraction from Notion pages including:
 * - Page title
 * - Sub-headings (H1, H2, H3 blocks)
 * - Database properties (if on a database page)
 * - Breadcrumb path for context hierarchy
 */

/**
 * Extract rich context from a Notion page.
 * @returns {{ site: "notion", title: string, headings: string[], breadcrumb: string[], properties: object } | null}
 */
function extractNotionContext() {
  const title = extractNotionPageTitle();
  if (!title) return null;

  return {
    site: "notion",
    title,
    headings: extractNotionHeadings(),
    breadcrumb: extractNotionBreadcrumb(),
    properties: extractNotionProperties(),
  };
}

/**
 * Extract the Notion page title.
 * @returns {string|null}
 */
function extractNotionPageTitle() {
  // Primary: Notion's page title element
  const titleEl =
    document.querySelector(".notion-page-block .notranslate") ||
    document.querySelector('[data-block-id] [placeholder="Untitled"]') ||
    document.querySelector("header h1") ||
    document.querySelector(".notion-frame .notion-page-content h1");

  if (titleEl && titleEl.textContent) {
    return titleEl.textContent.trim();
  }

  // Fallback: document.title
  const docTitle = document.title || "";
  return docTitle.includes(" - Notion")
    ? docTitle.replace(/ - Notion$/, "").trim()
    : docTitle || null;
}

/**
 * Extract sub-headings from the Notion page content.
 * @returns {string[]}
 */
function extractNotionHeadings() {
  const headings = [];
  const selectors = [
    ".notion-header-block",
    ".notion-sub_header-block",
    ".notion-sub_sub_header-block",
    '[data-block-id] h1',
    '[data-block-id] h2',
    '[data-block-id] h3',
  ];

  for (const sel of selectors) {
    for (const el of document.querySelectorAll(sel)) {
      const text = el.textContent.trim();
      if (text && text.length > 0 && text.length < 200) {
        headings.push(text);
      }
    }
  }

  // Deduplicate while preserving order
  return [...new Set(headings)].slice(0, 15);
}

/**
 * Extract breadcrumb path for hierarchical context.
 * @returns {string[]}
 */
function extractNotionBreadcrumb() {
  const crumbs = [];
  const breadcrumbEl = document.querySelector(".notion-breadcrumb");
  if (breadcrumbEl) {
    for (const item of breadcrumbEl.querySelectorAll("a, span")) {
      const text = item.textContent.trim();
      if (text && text !== "/" && text !== "...") {
        crumbs.push(text);
      }
    }
  }
  return crumbs.slice(0, 5);
}

/**
 * Extract database properties if on a database page/row.
 * @returns {object}
 */
function extractNotionProperties() {
  const props = {};
  const propertyRows = document.querySelectorAll(
    '.notion-collection_view-block [data-content-editable-leaf="true"]'
  );

  for (const row of Array.from(propertyRows).slice(0, 10)) {
    const label = row.closest("[data-block-id]");
    if (label) {
      const text = row.textContent.trim();
      if (text) {
        const key = label.getAttribute("data-block-id") || "prop";
        props[key] = text;
      }
    }
  }
  return props;
}

// Export for use in content.js
if (typeof window !== "undefined") {
  window.__pwbs_notion = {
    extractNotionContext,
    extractNotionPageTitle,
    extractNotionHeadings,
    extractNotionBreadcrumb,
    extractNotionProperties,
  };
}