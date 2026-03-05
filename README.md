# Papertrail

## Run with Docker

```bash
docker compose up -d
```

- **Frontend:** http://localhost:3000  
- **Backend:** http://localhost:8000  
- **Postgres:** localhost:5433 (user `postgres`, password `postgres`, db `mydb`)

The backend container runs `alembic upgrade head` on startup.

---

## Local setup (Alembic + seed, no Docker app)

1. **Start Postgres** (optional if already up via Docker):

   ```bash
   docker compose up -d postgres
   ```

2. **Backend env** — from repo root, use `backend/.env.local` or set:

   ```bash
   export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/mydb
   ```

   (Windows PowerShell: `$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5433/mydb"`)

3. **Install deps and run migrations:**

   ```bash
   cd backend
   pip install -r requirements.txt
   alembic upgrade head
   ```

4. **Seed the database:**

   ```bash
   python -m scripts.seed_db
   ```

---

## Local dev: run backend on port 8001

Use port 8001 so Docker (backend on 8000) can run at the same time, or just to avoid conflicts.

1. **Start the backend** (from repo root or `backend/`):

   ```bash
   cd backend
   set DATABASE_URL=postgresql://postgres:postgres@localhost:5433/mydb
   hypercorn app.main:app --bind 0.0.0.0:8001
   ```
---

## Environments & `NEXT_PUBLIC_API_URL`

| Context | API URL | Env file |
|--------|---------|----------|
| **Docker locally** (`docker compose up`) | `http://localhost:8000` | `.env` (default) — browser on host calls backend on host |
| **Run locally** (frontend + backend on your machine) | `http://localhost:8000` or `http://localhost:8001` | `.env` (8000) or `.env.local` (e.g. 8001 for local Hypercorn) |
| **Production** | `https://api.yourdomain.com` | `.env.production` — used by `next build`; set real URL before deploy |

- Frontend reads `NEXT_PUBLIC_API_URL` (or `NEXT_PUBLIC_API_BASE`) from these files. Restart dev server after changing env.
- For prod Docker builds, pass the URL at build time, e.g. `docker build --build-arg NEXT_PUBLIC_API_URL=https://api.yourdomain.com ...` (and add `ARG`/`ENV` in the Dockerfile if needed).

---

## After changing `models.py`

From `backend/`:

```bash
alembic revision --autogenerate -m "describe change"
# Review backend/alembic/versions/<new_file>.py, then:
alembic upgrade head
```
