import { useCallback, useEffect, useRef, useState } from "react";
import data from "../data/dataAccess.js";
import Editor from "./Editor.jsx";

const AUTOSAVE_MS = 800;

// Loads a daily note and hosts the editor. Autosaves edits back through the
// data-access module. `day` is "YYYY-MM-DD" or null for today.
export default function DailyView({ day = null }) {
  const [note, setNote] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | saved | saving | error
  const saveTimer = useRef(null);
  const pending = useRef(null);

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

  // Flush any pending edit on unmount / navigation.
  useEffect(() => () => {
    clearTimeout(saveTimer.current);
    flush();
  }, [flush]);

  if (status === "loading" || !note) {
    return <div className="p-8 text-slate-400">Loading note…</div>;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-2 text-sm dark:border-slate-800">
        <span className="font-medium text-slate-700 dark:text-slate-200">{note.title}</span>
        <SaveBadge status={status} />
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <Editor key={note.path} initialValue={note.content} onChange={handleChange} />
      </div>
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
