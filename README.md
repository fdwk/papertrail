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

## After changing `models.py`

From `backend/`:

```bash
alembic revision --autogenerate -m "describe change"
# Review backend/alembic/versions/<new_file>.py, then:
alembic upgrade head
```
