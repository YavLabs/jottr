import { useEffect, useState } from "react";
import data from "./data/dataAccess.js";
import Login from "./components/Login.jsx";
import Shell from "./components/Shell.jsx";

export default function App() {
  const [user, setUser] = useState(undefined); // undefined = loading, null = logged out

  useEffect(() => {
    data.getCurrentUser().then(setUser).catch(() => setUser(null));
  }, []);

  if (user === undefined) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50 text-slate-400 dark:bg-slate-950">
        Loading…
      </div>
    );
  }

  if (user === null) return <Login />;

  return <Shell user={user} onLogout={() => setUser(null)} />;
}
