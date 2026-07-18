import data from "../data/dataAccess.js";

// The authenticated app shell. Empty for Phase 0 — the daily-note editor,
// task rail and calendar all land in later phases inside this frame.
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

      <main className="flex flex-1 items-center justify-center p-8">
        <div className="text-center">
          <p className="text-slate-400 dark:text-slate-500">
            Empty workspace. The daily note lands in Phase 1.
          </p>
        </div>
      </main>
    </div>
  );
}
