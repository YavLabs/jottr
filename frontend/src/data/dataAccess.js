/**
 * dataAccess — the ONE module all client data access flows through.
 *
 * This is the "offline door" from the project principles: today every call
 * hits the FastAPI backend over HTTP. When offline support lands (Phase 7),
 * this module is swapped/extended to read-through a local cache — nothing
 * else in the app changes, because nothing else talks to the network directly.
 *
 * Rule for the rest of the codebase: never call fetch() outside this file.
 */

const BASE = "/api";

async function request(path, { method = "GET", body, headers } = {}) {
  const opts = {
    method,
    credentials: "same-origin", // send the session cookie
    headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...headers },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE}${path}`, opts);

  if (res.status === 204) return null;

  const contentType = res.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const detail = (payload && payload.detail) || res.statusText;
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return payload;
}

// --- Auth -----------------------------------------------------------------

export async function getCurrentUser() {
  try {
    return await request("/auth/me");
  } catch (err) {
    if (err.status === 401) return null;
    throw err;
  }
}

export function loginUrl() {
  // A full navigation (not fetch) so the OAuth redirect chain works.
  return `${BASE}/auth/login`;
}

export async function logout() {
  await request("/auth/logout", { method: "POST" });
}

// --- Health ---------------------------------------------------------------

export async function getHealth() {
  return request("/health");
}

// Phase 1+ will add: listNotes, getNote, saveNote, listTasks, ... all here.

export default { getCurrentUser, loginUrl, logout, getHealth };
