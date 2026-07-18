# Jottr

> Local-first notes + daily task tracker + calendar with inline text-and-ink notes.
> Self-hosted as one Docker container. MIT-licensed.

A single markdown-backed daily workspace — notes, tasks, ink, and calendar in one
screen — that you self-host in one container, own the files for, and drive from any
device or AI tool.

**Markdown files are the source of truth.** Delete the app, keep the notes.

---

## Status

🚧 Early development. **Phase 0 (Foundation)** is in place:

- FastAPI backend serving a Vite/React SPA from one container
- Google OAuth login with an email allowlist (plus a dev-login bypass)
- Health check, named data volume, one-line deploy
- Single client-side data-access module (the seam for future offline support)

See the [build phases](#build-phases) for what's next.

---

## Quick start

### Run with Docker (dev login, no Google needed)

```bash
docker compose up --build
```

Open <http://localhost:8000> and click **Continue (dev login)**. You land in an empty
workspace. Notes files live in the `jottr_data` volume under `/data`.

### Enable Google sign-in

1. Create an **OAuth 2.0 Client ID** (type: *Web application*) at
   <https://console.cloud.google.com/apis/credentials>.
2. Add the authorized redirect URI: `http://localhost:8000/api/auth/callback`
   (match your `JOTTR_BASE_URL`).
3. Copy `.env.example` to `.env` and set:

   ```
   JOTTR_GOOGLE_CLIENT_ID=...
   JOTTR_GOOGLE_CLIENT_SECRET=...
   JOTTR_ALLOWED_EMAILS=you@example.com
   JOTTR_JWT_SECRET=<long random string>
   ```

4. `docker compose up --build` — the login button now uses Google.

---

## Local development (without Docker)

Two processes: FastAPI on `:8000`, Vite dev server on `:5173` (proxies `/api`).

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
JOTTR_DATA_DIR=./data uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

---

## Configuration

All settings are environment variables prefixed `JOTTR_`. See
[`.env.example`](./.env.example) for the full list. Key ones:

| Variable | Default | Purpose |
| --- | --- | --- |
| `JOTTR_BASE_URL` | `http://localhost:8000` | Public URL; builds the OAuth redirect |
| `JOTTR_JWT_SECRET` | *(dev default)* | Signs the session cookie — **change in prod** |
| `JOTTR_GOOGLE_CLIENT_ID` / `_SECRET` | *(blank)* | Google OAuth; blank ⇒ dev login |
| `JOTTR_ALLOWED_EMAILS` | *(blank)* | Comma-separated login allowlist |
| `JOTTR_DATA_DIR` | `/data` | Data volume mount point |

---

## Architecture

One Docker image runs FastAPI, which serves the built SPA and the REST/MCP API.
All data lives in one named volume:

```
/data
├── notes/**.md            markdown notes (source of truth)
├── daily/YYYY-MM-DD.md    one note per day
├── attachments/           images, ink SVGs
├── index.sqlite           rebuildable FTS + task + event cache
└── auth/token.json        Google refresh token
```

The client is thin; the server owns the truth. Every client read/write goes through
`frontend/src/data/dataAccess.js` — the single seam where offline support slots in later.

---

## Build phases

- **Phase 0 — Foundation** ✅ container, OAuth, volume, data-access seam
- **Phase 1 — Daily note + editor** (Milkdown, inline ink, SQLite FTS)
- **Phase 2 — Tasks** (checkbox parsing, today/upcoming/overdue, roll-over)
- **Phase 3 — Calendar (read)** (Google, then Apple CalDAV)
- **Phase 4 — MCP server (read)**
- **Phase 5 — Calendar (write) + MCP (write)**
- **Phase 6 — Backup + hardening** (versioned rclone/restic)
- **Phase 7 — PWA polish + offline**
- **Phase 8 — Open-source release**

---

## License

[MIT](./LICENSE).
