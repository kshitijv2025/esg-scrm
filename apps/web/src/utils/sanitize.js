/**
 * XSS sanitization utility using DOMPurify.
 *
 * NOTE: To install DOMPurify, run:
 *   cd apps/web && npm install dompurify
 *
 * This utility sanitizes user-generated content before rendering to prevent XSS attacks.
 */
import DOMPurify from "dompurify";

/**
 * Sanitize a string containing potentially malicious HTML.
 *
 * @param {string} dirty - The potentially dirty/untrusted string
 * @returns {string} The sanitized string safe for rendering
 */
export function sanitize(dirty) {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: [
      "b",
      "i",
      "em",
      "strong",
      "a",
      "p",
      "br",
      "span",
      "div",
      "ul",
      "ol",
      "li",
    ],
    ALLOWED_ATTR: ["href", "title", "class", "style"],
    // Allow safe link protocols only
    ALLOWED_URI_REGEXP:
      /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  });
}

/**
 * Sanitize a string and also strip all HTML tags, returning plain text.
 *
 * @param {string} dirty - The potentially dirty/untrusted string
 * @returns {string} Plain text with all HTML tags removed
 */
export function sanitizeToText(dirty) {
  return DOMPurify.sanitize(dirty, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
}
