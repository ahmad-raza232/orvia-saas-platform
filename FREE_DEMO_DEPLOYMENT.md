# Free ORVIA client demo

Deploy the current ORVIA SaaS (product by Softorica) as a **completely free** client demo.

- Frontend: Cloudflare Pages (static Vite/React build)
- Backend: Render Free Web Service
- Database: Render Free PostgreSQL
- Repository: https://github.com/ahmad-raza232/orvia-saas-platform.git

This guide does **not** add Module 12 or new product features. It does **not** require a custom domain. Do **not** enable paid Render or Cloudflare plans. Do **not** add keep-alive pingers or fake health polling to keep Render awake.

GoBurq remains legacy-only. Do not point `VITE_TENANT_API_URL` at goburq.com.

Use `APP_ENV=demo` on Render. `APP_ENV=production` requires SMTP and S3 and will refuse to start on this free stack.

## Limits you should expect

- The Render free web service sleeps after idle time. The first request after sleep can take about 30–60 seconds. That is normal. Do not try to bypass it.
- Free Render PostgreSQL expires **30 days** after creation (then a short grace period). Recreate the database and re-run this guide if the demo must continue past that window.
- One free Postgres instance per Render workspace. 1 GB storage. No backups.
- Notification email is logging-only on this demo. There is no second worker process.

## A. Create a Render account

1. Open https://render.com and sign up (GitHub sign-in is simplest).
2. Stay on the **Free** instance types. Do not add a credit card unless you choose to.
3. Create or select a workspace.

## B. Connect the GitHub repository

1. In Render, open **Account / Git** (or the New service GitHub step) and authorize Render to read `ahmad-raza232/orvia-saas-platform`.
2. Confirm the connected repo is https://github.com/ahmad-raza232/orvia-saas-platform.git and the branch is `main`.

## C. Create Render PostgreSQL

1. Dashboard → **New** → **PostgreSQL**.
2. Settings:

   | Field | Value |
   |---|---|
   | Name | `orvia-demo-db` |
   | Database | `orvia` |
   | User | leave default, or `orvia` |
   | Region | pick one and reuse it for the web service |
   | Instance type | **Free** |
   | PostgreSQL version | 16 (or the latest Render offers) |

3. Create the database. Wait until it is **Available**.
4. Open the database → **Connections**. Copy **Internal Database URL**.
   - Use Internal URL because the web service will run in the same Render account.
   - Do not paste this URL into git, issues, or chat.
   - The API accepts Render’s `postgres://…` form and rewrites it to SQLAlchemy `postgresql+psycopg://…`. External `*.render.com` URLs also get `sslmode=require`. Prefer Internal URL anyway.

Do **not** point production/demo at local Docker PostgreSQL (`localhost:5433`).

## D. Create Render Web Service

1. Dashboard → **New** → **Web Service**.
2. Connect `ahmad-raza232/orvia-saas-platform`.
3. Settings:

   | Field | Value |
   |---|---|
   | Name | `orvia-demo-api` (must be unique; Render URL becomes `https://<name>.onrender.com`) |
   | Region | same as the database |
   | Branch | `main` |
   | Root Directory | `backend` |
   | Runtime | **Python 3** |
   | Instance type | **Free** |
   | Health Check Path | `/health` |

Do not attach a persistent disk (not available on free). Do not create a paid Background Worker.

## E. Required build and start commands

On the web service:

| Field | Value |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `sh start.sh` |

`start.sh` runs Alembic, then binds Uvicorn to `0.0.0.0` and Render’s `$PORT`. Local development still defaults to port 8000 when `$PORT` is unset.

Equivalent explicit start command if you prefer not to use the script:

```text
python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Do **not** hardcode `--port 8000` on Render.

## F. Required environment variables

Add these on the web service → **Environment**. Never commit the real values.

### Required

| Key | Value |
|---|---|
| `APP_ENV` | `demo` |
| `DEBUG` | `false` |
| `DATABASE_URL` | Internal Database URL from step C |
| `JWT_SECRET` | 32+ random characters (not `change-me-to-a-long-random-secret`) |
| `CORS_ORIGINS` | Exact Cloudflare Pages origin, e.g. `https://orvia-saas-platform.pages.dev` (no `*`, no trailing slash) |
| `EMAIL_PROVIDER` | `logging` |
| `STORAGE_PROVIDER` | `memory` |
| `MEMORY_STORAGE_PUBLIC_BASE_URL` | `https://<web-service-name>.onrender.com` (no trailing slash) |

Generate `JWT_SECRET` locally:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`CORS_ORIGINS` must be the **exact** Pages origin. Starlette does not treat `*.pages.dev` as a wildcard. Preview URLs (`https://<hash>.<project>.pages.dev`) will fail CORS unless you add them as extra comma-separated origins.

If you do not know the Pages URL yet: create the Cloudflare Pages project in step I (it assigns `https://<project>.pages.dev` before the first successful build), paste that origin here, then continue.

### Optional demo account (explicit only)

Leave these unset unless you want a shared client login. Seed never runs unless `DEMO_SEED_ENABLED=true`. `APP_ENV=production` always refuses this flag.

| Key | Example |
|---|---|
| `DEMO_SEED_ENABLED` | `true` |
| `DEMO_SEED_EMAIL` | `demo@orvia.app` |
| `DEMO_SEED_PASSWORD` | at least 10 characters, unique to this demo |
| `DEMO_SEED_ORG_NAME` | `ORVIA Demo` |

Seed creates the user and organization **once**. If that email already exists, it skips. It never overwrites passwords or org data.

### Optional SMTP / S3

Not required for `APP_ENV=demo`. Leave the defaults (logging email, memory storage). If you later add real SMTP or S3, set:

- SMTP: `EMAIL_PROVIDER=smtp`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_USE_TLS`
- S3: `STORAGE_PROVIDER=s3`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, optional `S3_ENDPOINT_URL`

Do not put SMTP or S3 secrets in git.

## G. Run Alembic migrations

Migrations run automatically on each web service start via `start.sh` (`python -m alembic upgrade head`).

You do not need a separate migration job. Confirm in **Logs** that Alembic reaches `head` and Uvicorn starts.

If the service crashed before migrations, fix `DATABASE_URL` and **Manual Deploy**.

## H. Get the Render API URL

After the first deploy:

1. Web service → **Settings** or the header URL.
2. Public API origin: `https://<web-service-name>.onrender.com`
3. Tenant API base used by the frontend: `https://<web-service-name>.onrender.com/api/v1`
4. Health: open `https://<web-service-name>.onrender.com/health` → `{"status":"ok"}`
5. Ready (database): `https://<web-service-name>.onrender.com/ready` → `{"status":"ok"}`

The first request after sleep can take up to a minute.

## I. Configure Cloudflare Pages

1. Open https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Select `ahmad-raza232/orvia-saas-platform`.
3. Build settings:

   | Field | Value |
   |---|---|
   | Project name | `orvia-saas-platform` (URL becomes `https://<project>.pages.dev`) |
   | Production branch | `main` |
   | Root directory | `frontend` |
   | Framework preset | Vite (or None) |
   | Build command | `npm run build` |
   | Build output directory | `dist` |
   | Node version | `20` (or env `NODE_VERSION=20`) |

Do not add a custom domain. Do not enable Pages Functions.

SPA fallback is already in `frontend/public/_redirects` (`/* /index.html 200`) and is copied into `dist` on build. That covers `/login`, `/register`, `/app`, `/app/shipments`, `/app/shipments/new`, `/app/shipments/:id`, `/track`.

## J. Set `VITE_TENANT_API_URL`

In the Pages project → **Settings** → **Environment variables** → **Production**:

| Key | Value |
|---|---|
| `VITE_TENANT_API_URL` | `https://<web-service-name>.onrender.com/api/v1` |
| `NODE_VERSION` | `20` |

Optional (legacy booking compatibility only; already defaulted in code):

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://goburq.com/api` |

Vite inlines `VITE_*` at **build** time. Changing this variable requires a new Pages deployment.

Do not set `VITE_TENANT_API_URL` to `http://localhost:8000` or any `127.0.0.1` URL. The production build will refuse localhost.

## K. Deploy the frontend

1. **Save** the env vars, then **Deployments** → **Retry deployment** (or push to `main`).
2. Wait for a successful build.
3. Confirm the live URL, for example `https://orvia-saas-platform.pages.dev`.
4. If the live origin differs from what you put in `CORS_ORIGINS`, update Render `CORS_ORIGINS` to the exact `https://…pages.dev` origin and restart the web service.

## L. Test the complete client demo

After the API has finished its first cold start:

1. Open `https://<project>.pages.dev`
2. Confirm ORVIA + Softorica branding (not GoBurq) on the landing page
3. `/register` — create an account, or `/login` with the demo seed email if you enabled seed
4. Complete org onboarding if prompted
5. `/app` — dashboard loads (empty counts are `0` or `—`, not a crash)
6. `/app/shipments/new` — create a shipment
7. Open the success/receipt page and print/download the ORVIA slip
8. `/app/shipments` and `/app/shipments/:id`
9. `/track?tracking_id=ORVIA-XXXXXXXXXX` — public tracking without login
10. Hard-refresh `/login` and `/app/shipments/new` to confirm SPA fallback (no Cloudflare 404)

If the browser shows a CORS error, `CORS_ORIGINS` does not match the Pages origin exactly.

## Local development (unchanged)

```powershell
cd backend
docker compose up -d postgres
copy .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
copy .env.example .env
# keep VITE_TENANT_API_URL=/api/v1
npm install
npm run dev
```

Open http://localhost:5173. Local Docker PostgreSQL is for local use only.

## Quality checks before you push

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

`test:saas-smoke` needs the API on port 8000.
