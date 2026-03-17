"use client";

/**
 * Skip-to-content link for keyboard users.
 * Visually hidden until focused.
 */
export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-gray-900 focus:px-4 focus:py-2 focus:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
    >
      Zum Hauptinhalt springen
    </a>
  );
}
