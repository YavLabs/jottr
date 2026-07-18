import { useCallback, useEffect, useRef, useState } from "react";
import data from "../data/dataAccess.js";
import Editor from "./Editor.jsx";
import InkModal from "../ink/InkModal.jsx";
import { svgToStrokes } from "../ink/inkSvg.js";

const AUTOSAVE_MS = 800;

// Loads a daily note and hosts the editor. Autosaves edits back through the
// data-access module. `day` is "YYYY-MM-DD" or null for today.
export default function DailyView({ day = null }) {
  const [note, setNote] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | saved | saving | error
  const [ink, setInk] = useState(null); // null | { mode, strokes, name?, img? }
  const saveTimer = useRef(null);
  const pending = useRef(null);
  const editorApi = useRef(null);

  useEffect(() => {
    setStatus("loading");
    data
      .getDaily(day)
      .then((n) => {
        setNote(n);
        setStatus("saved");
      })
      .catch(() => setStatus("error"));
  }, [day]);

  const flush = useCallback(async () => {
    if (pending.current == null || !note) return;
    const content = pending.current;
    pending.current = null;
    setStatus("saving");
    try {
      await data.saveNote(note.path, content);
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  }, [note]);

  const handleChange = useCallback(
    (markdown) => {
      pending.current = markdown;
      setStatus("saving");
      clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(flush, AUTOSAVE_MS);
    },
    [flush],
  );

  useEffect(() => () => {
    clearTimeout(saveTimer.current);
    flush();
  }, [flush]);

  // --- ink ---------------------------------------------------------------
  const openNewSketch = () => setInk({ mode: "new", strokes: [] });

  const openEditSketch = useCallback(async (name, img) => {
    try {
      const res = await fetch(data.attachmentUrl(name), { credentials: "same-origin" });
      const svg = await res.text();
      setInk({ mode: "edit", strokes: svgToStrokes(svg), name, img });
    } catch {
      // If we can't load it, fall back to a fresh sketch keyed to that name.
      setInk({ mode: "edit", strokes: [], name, img });
    }
  }, []);

  const saveSketch = useCallback(async (svg) => {
    if (!ink) return;
    if (ink.mode === "new") {
      const name = `ink-${crypto.randomUUID().slice(0, 8)}.svg`;
      await data.saveInk(name, svg);
      editorApi.current?.insertMarkdown(`\n![sketch](${data.attachmentUrl(name)})\n`);
    } else {
      await data.saveInk(ink.name, svg);
      // Markdown is unchanged (same URL); nudge the <img> to re-fetch.
      if (ink.img) ink.img.src = `${data.attachmentUrl(ink.name)}?t=${Date.now()}`;
    }
    setInk(null);
  }, [ink]);

  if (status === "loading" || !note) {
    return <div className="p-8 text-slate-400">Loading note…</div>;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-2 text-sm dark:border-slate-800">
        <span className="font-medium text-slate-700 dark:text-slate-200">{note.title}</span>
        <div className="flex items-center gap-3">
          <button
            onClick={openNewSketch}
            className="rounded-md border border-slate-200 px-2.5 py-1 text-xs hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            ✎ Sketch
          </button>
          <SaveBadge status={status} />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        <Editor
          key={note.path}
          initialValue={note.content}
          onChange={handleChange}
          onReady={(api) => (editorApi.current = api)}
          onEditInk={openEditSketch}
        />
      </div>

      {ink && (
        <InkModal
          initialStrokes={ink.strokes}
          onSave={saveSketch}
          onClose={() => setInk(null)}
        />
      )}
    </div>
  );
}

function SaveBadge({ status }) {
  const map = {
    saving: ["Saving…", "text-amber-600 dark:text-amber-500"],
    saved: ["Saved", "text-slate-400"],
    error: ["Save failed", "text-red-600 dark:text-red-500"],
  };
  const [label, cls] = map[status] || ["", ""];
  return <span className={`text-xs ${cls}`}>{label}</span>;
}
