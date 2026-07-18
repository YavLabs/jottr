import { useState } from "react";
import InkCanvas from "./InkCanvas.jsx";
import { DEFAULT_COLOR, strokesToSvg } from "./inkSvg.js";

const CANVAS_W = 640;
const CANVAS_H = 320;
const COLORS = ["#0f172a", "#e11d48", "#2563eb", "#16a34a", "#d97706"];
const SIZES = [4, 8, 14];

/**
 * Modal wrapper around the drawing surface. Owns the committed strokes so it
 * can offer undo/clear, and serializes to SVG on save.
 *
 * onSave(svg, strokes) — svg is a self-contained, re-editable ink SVG string.
 */
export default function InkModal({ initialStrokes = [], onSave, onClose }) {
  const [strokes, setStrokes] = useState(() => initialStrokes.map((s) => ({ ...s })));
  const [color, setColor] = useState(DEFAULT_COLOR);
  const [size, setSize] = useState(8);

  const commit = (stroke) => setStrokes((prev) => [...prev, stroke]);
  const undo = () => setStrokes((prev) => prev.slice(0, -1));
  const clear = () => setStrokes([]);

  const save = () => {
    const svg = strokesToSvg(strokes, {
      width: CANVAS_W,
      height: CANVAS_H,
      background: "#ffffff",
    });
    onSave?.(svg, strokes);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-4 shadow-xl dark:border-slate-700 dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Sketch</h2>
          <div className="flex items-center gap-3">
            {/* colors */}
            <div className="flex items-center gap-1">
              {COLORS.map((c) => (
                <button
                  key={c}
                  aria-label={`color ${c}`}
                  onClick={() => setColor(c)}
                  className={`h-5 w-5 rounded-full border ${color === c ? "ring-2 ring-offset-1 ring-slate-400" : "border-slate-300"}`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            {/* sizes */}
            <div className="flex items-center gap-1">
              {SIZES.map((s) => (
                <button
                  key={s}
                  aria-label={`size ${s}`}
                  onClick={() => setSize(s)}
                  className={`flex h-6 w-6 items-center justify-center rounded ${size === s ? "bg-slate-200 dark:bg-slate-700" : ""}`}
                >
                  <span className="rounded-full bg-slate-700 dark:bg-slate-200" style={{ width: s, height: s }} />
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="aspect-[2/1] w-full overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
          <InkCanvas
            strokes={strokes}
            onCommit={commit}
            color={color}
            size={size}
            width={CANVAS_W}
            height={CANVAS_H}
          />
        </div>

        <div className="mt-3 flex items-center justify-between">
          <div className="flex gap-2 text-sm">
            <button onClick={undo} className="rounded-md border border-slate-200 px-3 py-1 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800">
              Undo
            </button>
            <button onClick={clear} className="rounded-md border border-slate-200 px-3 py-1 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800">
              Clear
            </button>
          </div>
          <div className="flex gap-2 text-sm">
            <button onClick={onClose} className="rounded-md px-3 py-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">
              Cancel
            </button>
            <button
              onClick={save}
              className="rounded-md bg-slate-900 px-4 py-1 font-medium text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
            >
              Insert
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
