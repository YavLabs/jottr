import { useEffect, useState } from "react";
import data from "../data/dataAccess.js";

export default function Login() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    data.getHealth().then(setHealth).catch(() => {});
  }, []);

  const devMode = health?.dev_auth;

  return (
    <div className="flex h-full items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
            Jottr
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Your daily workspace — notes, tasks, ink, calendar.
          </p>
        </div>

        <a
          href={data.loginUrl()}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        >
          {devMode ? "Continue (dev login)" : "Sign in with Google"}
        </a>

        {devMode && (
          <p className="mt-4 text-center text-xs text-amber-600 dark:text-amber-500">
            Dev auth is on — Google OAuth is not configured.
          </p>
        )}
      </div>
    </div>
  );
}
