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

// --- Notes ----------------------------------------------------------------

export async function listNotes() {
  return request("/notes");
}

export async function getNote(path) {
  return request(`/notes/${path}`);
}

export async function saveNote(path, content) {
  return request(`/notes/${path}`, { method: "PUT", body: { content } });
}

export async function deleteNote(path) {
  return request(`/notes/${path}`, { method: "DELETE" });
}

// --- Daily notes ----------------------------------------------------------

export async function getDaily(day) {
  // day is "YYYY-MM-DD"; omit for today.
  return request(day ? `/daily/${day}` : "/daily");
}

// --- Search ---------------------------------------------------------------

export async function search(query, limit = 30) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return request(`/search?${params.toString()}`);
}

// --- Tasks ----------------------------------------------------------------

export async function listTasks(view = "open", { tag, limit } = {}) {
  const params = new URLSearchParams({ view });
  if (tag) params.set("tag", tag);
  if (limit) params.set("limit", String(limit));
  return request(`/tasks?${params.toString()}`);
}

export async function taskCounts() {
  return request("/tasks/counts");
}

export async function toggleTask(path, line, done) {
  return request("/tasks/toggle", { method: "POST", body: { path, line, done } });
}

export async function addTask({ text, due, priority }) {
  return request("/tasks/add", { method: "POST", body: { text, due, priority } });
}

export async function rolloverTasks() {
  return request("/tasks/rollover", { method: "POST" });
}

// --- Attachments ----------------------------------------------------------

export async function uploadAttachment(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/attachments`, {
    method: "POST",
    credentials: "same-origin",
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function saveInk(name, svg) {
  return request(`/attachments/ink/${name}`, { method: "PUT", body: { name, svg } });
}

export function attachmentUrl(name) {
  return `${BASE}/attachments/${name}`;
}

export default {
  getCurrentUser,
  loginUrl,
  logout,
  getHealth,
  listNotes,
  getNote,
  saveNote,
  deleteNote,
  getDaily,
  search,
  listTasks,
  taskCounts,
  toggleTask,
  addTask,
  rolloverTasks,
  uploadAttachment,
  saveInk,
  attachmentUrl,
};
