/**
 * Pure ink <-> SVG serialization. No DOM, no React — unit-testable in Node.
 *
 * An ink block is stored as a normal SVG file in attachments/, referenced from
 * the note like an image. To keep it *re-editable* (not re-rasterized), the raw
 * stroke data is embedded in a <metadata> element as base64 JSON. Rendering
 * uses perfect-freehand to turn each stroke into a filled outline path.
 *
 * Stroke shape: { color: "#0f172a", size: 8, points: [[x, y, pressure], ...] }
 */

import { getStroke } from "perfect-freehand";

export const INK_VERSION = 1;
export const DEFAULT_COLOR = "#0f172a";
export const DEFAULT_SIZE = 8;

const STROKE_OPTIONS = {
  thinning: 0.6,
  smoothing: 0.5,
  streamline: 0.5,
};

// perfect-freehand outline points -> SVG path `d` (quadratic-smoothed).
export function getSvgPathFromStroke(stroke) {
  if (!stroke.length) return "";
  const d = stroke.reduce(
    (acc, [x0, y0], i, arr) => {
      const [x1, y1] = arr[(i + 1) % arr.length];
      acc.push(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2);
      return acc;
    },
    ["M", ...stroke[0], "Q"],
  );
  d.push("Z");
  return d.map((n) => (typeof n === "number" ? Math.round(n * 100) / 100 : n)).join(" ");
}

function b64encode(str) {
  // unicode-safe base64 (colors/numbers are ascii, but be safe)
  return btoa(unescape(encodeURIComponent(str)));
}

function b64decode(b64) {
  return decodeURIComponent(escape(atob(b64)));
}

export function encodeStrokes(strokes) {
  return b64encode(JSON.stringify({ v: INK_VERSION, strokes }));
}

export function decodeStrokes(encoded) {
  try {
    const parsed = JSON.parse(b64decode(encoded));
    return Array.isArray(parsed.strokes) ? parsed.strokes : [];
  } catch {
    return [];
  }
}

export function strokeToPath(stroke) {
  const outline = getStroke(stroke.points || [], {
    size: stroke.size ?? DEFAULT_SIZE,
    ...STROKE_OPTIONS,
    simulatePressure: !stroke.hasPressure,
  });
  return getSvgPathFromStroke(outline);
}

/** Serialize strokes to a self-contained, re-editable SVG string. */
export function strokesToSvg(strokes, { width, height, background = null } = {}) {
  const w = Math.max(1, Math.round(width || 640));
  const h = Math.max(1, Math.round(height || 320));
  const bg = background ? `<rect width="${w}" height="${h}" fill="${background}"/>` : "";
  const paths = (strokes || [])
    .filter((s) => s.points && s.points.length)
    .map((s) => `<path d="${strokeToPath(s)}" fill="${s.color || DEFAULT_COLOR}"/>`)
    .join("");
  const meta = `<metadata id="jottr-ink">${encodeStrokes(strokes || [])}</metadata>`;
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" ` +
    `viewBox="0 0 ${w} ${h}" data-jottr-ink="${INK_VERSION}">${meta}${bg}${paths}</svg>`
  );
}

const META_RE = /<metadata id="jottr-ink">([\s\S]*?)<\/metadata>/;

/** Recover editable strokes from a Jottr ink SVG (empty array if not one). */
export function svgToStrokes(svg) {
  const m = META_RE.exec(svg || "");
  return m ? decodeStrokes(m[1]) : [];
}

export function isInkSvg(svg) {
  return typeof svg === "string" && svg.includes('data-jottr-ink=');
}
