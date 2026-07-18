import { useCallback, useEffect, useState } from "react";
import data from "../data/dataAccess.js";

const VIEWS = [
  { key: "today", label: "Today" },
  { key: "overdue", label: "Overdue" },
  { key: "upcoming", label: "Upcoming" },
  { key: "completed", label: "Done" },
];

const PRIORITY_DOT = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-slate-400",
};

/**
 * Right-hand task rail: parsed-checkbox views with toggle, quick-add, and
 * roll-over. `onMutate` lets the parent know a file changed (e.g. after a
 * toggle or roll-over) so the open note can refresh if it wants to.
 */
export default function TaskRail({ onMutate }) {
  const [view, setView] = useState("today");
  const [tasks, setTasks] = useState([]);
  const [counts, setCounts] = useState({});
  const [adding, setAdding] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async (v = view) => {
    const [list, c] = await Promise.all([data.listTasks(v), data.taskCounts()]);
    setTasks(list.tasks);
    setCounts(c);
  }, [view]);

  useEffect(() => {
    refresh(view).catch(() => {});
  }, [view, refresh]);

  const toggle = async (t) => {
    // optimistic
    setTasks((prev) => prev.filter((x) => !(x.path === t.path && x.line === t.line)));
    try {
      await data.toggleTask(t.path, t.line, !t.done);
      await refresh();
      onMutate?.(t.path);
    } catch {
      await refresh();
    }
  };

  const add = async (e) => {
    e.preventDefault();
    const text = adding.trim();
    if (!text) return;
    setAdding("");
    await data.addTask({ text });
    await refresh();
    onMutate?.();
  };

  const rollover = async () => {
    setBusy(true);
    try {
      const res = await data.rolloverTasks();
      await refresh();
      onMutate?.();
      if (res.moved) setView("today");
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="flex h-full w-80 flex-col border-l border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-1 border-b border-slate-200 px-2 py-2 dark:border-slate-800">
        {VIEWS.map((v) => (
          <button
            key={v.key}
            onClick={() => setView(v.key)}
            className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition ${
              view === v.key
                ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            {v.label}
            {counts[v.key === "completed" ? "completed" : v.key] > 0 && (
              <span className="opacity-70">{counts[v.key === "completed" ? "completed" : v.key]}</span>
            )}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-2 py-2">
        {tasks.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs text-slate-400">Nothing here.</p>
        ) : (
          <ul className="space-y-1">
            {tasks.map((t) => (
              <li
                key={`${t.path}:${t.line}`}
                className="group flex items-start gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <button
                  aria-label={t.done ? "Mark incomplete" : "Mark complete"}
                  onClick={() => toggle(t)}
                  className={`mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border ${
                    t.done
                      ? "border-slate-400 bg-slate-400 text-white"
                      : "border-slate-300 dark:border-slate-600"
                  }`}
                >
                  {t.done && <span className="text-[10px] leading-none">✓</span>}
                </button>
                <div className="min-w-0 flex-1">
                  <p className={`text-sm ${t.done ? "text-slate-400 line-through" : "text-slate-700 dark:text-slate-200"}`}>
                    {t.priority && (
                      <span className={`mr-1 inline-block h-2 w-2 rounded-full ${PRIORITY_DOT[t.priority]}`} />
                    )}
                    {t.text}
                  </p>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1 text-[10px] text-slate-400">
                    {t.due && <span className="rounded bg-slate-100 px-1 dark:bg-slate-800">{t.due}</span>}
                    {t.tags?.map((tag) => (
                      <span key={tag} className="text-blue-500 dark:text-blue-400">#{tag}</span>
                    ))}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border-t border-slate-200 p-2 dark:border-slate-800">
        <form onSubmit={add} className="mb-2">
          <input
            value={adding}
            onChange={(e) => setAdding(e.target.value)}
            placeholder="Add task to today…  (due:2026-07-20 !high #tag)"
            className="w-full rounded-md border border-slate-200 bg-slate-50 px-2 py-1.5 text-sm outline-none focus:border-slate-400 dark:border-slate-700 dark:bg-slate-800"
          />
        </form>
        <button
          onClick={rollover}
          disabled={busy}
          className="w-full rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          {busy ? "Rolling over…" : "↪ Roll over unfinished tasks"}
        </button>
      </div>
    </aside>
  );
}
