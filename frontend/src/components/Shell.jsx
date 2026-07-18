import data from "../data/dataAccess.js";
import DailyView from "./DailyView.jsx";
import TaskRail from "./TaskRail.jsx";

// The authenticated app shell. Phase 1: daily-note editor. Phase 2: task rail
// beside it. The calendar lands to the right of the rail in Phase 3.
export default function Shell({ user, onLogout }) {
  async function handleLogout() {
    await data.logout();
    onLogout();
  }

  return (
    <div className="flex h-full flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <span className="text-lg font-semibold tracking-tight">Jottr</span>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-500 dark:text-slate-400">{user.email}</span>
          <button
            onClick={handleLogout}
            className="rounded-md border border-slate-200 px-3 py-1 transition hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <main className="min-w-0 flex-1">
          <div className="mx-auto h-full max-w-3xl">
            <DailyView />
          </div>
        </main>
        <TaskRail />
      </div>
    </div>
  );
}
