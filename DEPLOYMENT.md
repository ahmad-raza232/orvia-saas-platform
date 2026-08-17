# ORVIA production and demo configuration

ORVIA is the product. Softorica is the company. The FastAPI service is the tenant SaaS API (Modules 1–11). Do not point `VITE_TENANT_API_URL` at goburq.com.

For a completely free client demo (Cloudflare Pages + Render Web Service + Render PostgreSQL), follow **[FREE_DEMO_DEPLOYMENT.md](FREE_DEMO_DEPLOYMENT.md)**. Do not use this file’s production SMTP/S3 requirements for that demo.

Never commit `.env` files, JWT secrets, database passwords, SMTP passwords, or S3 keys.

## Local demo (recommended)

### 1. PostgreSQL

```powershell
cd backend
docker compose up -d postgres
```

Create the app database if needed (compose already creates `orvia`). For tests:

```powershell
docker exec orvia-postgres psql -U orvia -d postgres -c "CREATE DATABASE orvia_test OWNER orvia;"
```

### 2. Backend

```powershell
cd backend
copy .env.example .env
# Edit .env: set JWT_SECRET, keep APP_ENV=development for local demo
# Optional durable demo login:
# DEMO_SEED_ENABLED=true
# DEMO_SEED_EMAIL=demo@orvia.app
# DEMO_SEED_PASSWORD=<at least 10 characters>
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Accounts live in PostgreSQL. Restarting the API does not wipe users or organizations.

Optional outbox worker (notifications):

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.worker
```

### 3. Frontend

```powershell
cd frontend
copy .env.example .env
# Keep VITE_TENANT_API_URL=/api/v1 so Vite proxies /api to http://127.0.0.1:8000
npm install
npm run dev
```

Open http://localhost:5173

- Register a new account, or sign in with the demo seed email if enabled
- Create an organization on `/app/onboarding` if prompted
- Book a shipment, print the ORVIA slip, open `/track?tracking_id=ORVIA-...`

### 4. Quality checks

```powershell
cd frontend
npm run build
npm run test:shipment-form
npm run test:saas-smoke
```

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

`test:saas-smoke` requires the API on port 8000.

## Production

### Frontend

- Set `VITE_TENANT_API_URL` to the public API base, e.g. `https://api.your-domain.com/api/v1`
- Or keep `/api/v1` if nginx/Caddy/Cloudflare serves the SPA and proxies `/api` to FastAPI
- Do not use `http://127.0.0.1` or `localhost` in a production build
- `VITE_API_URL` is legacy portal compatibility only

Build:

```powershell
cd frontend
npm ci
npm run build
```

Serve `frontend/dist` as static files.

### Backend

Set `APP_ENV=production`. The process will refuse to start unless:

- `DEBUG=false`
- `JWT_SECRET` is 32+ characters and not a known weak value
- `CORS_ORIGINS` is an explicit HTTPS origin list (no `*`)
- `EMAIL_PROVIDER=smtp` with `SMTP_HOST` and `SMTP_FROM` / `SMTP_FROM_EMAIL`
- `STORAGE_PROVIDER=s3` with bucket and credentials
- `DEMO_SEED_ENABLED` is not true

Example (placeholders only):

```
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/orvia
JWT_SECRET=<long-random-secret>
CORS_ORIGINS=https://app.your-domain.com
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.your-provider.com
SMTP_FROM_EMAIL=noreply@your-domain.com
STORAGE_PROVIDER=s3
S3_BUCKET=orvia-pod
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
```

Run migrations before starting:

```
python -m alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

On Render, use `sh start.sh` instead (see [FREE_DEMO_DEPLOYMENT.md](FREE_DEMO_DEPLOYMENT.md)).

Run the outbox worker as a second process.

### Reverse proxy sketch

- `https://app.your-domain.com/` → frontend `dist`
- `https://app.your-domain.com/api/` → FastAPI
- In that layout, frontend `VITE_TENANT_API_URL=/api/v1`

## Tracking IDs

Public SaaS tracking IDs are `ORVIA-XXXXXXXXXX`. The public page is `/track?tracking_id=ORVIA-...` and does not require login.
