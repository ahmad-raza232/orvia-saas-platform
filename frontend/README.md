# ORVIA frontend

Vite + React SPA for the ORVIA logistics SaaS (product) built by Softorica (company).

## Local

Copy `.env.example` to `.env`. Keep `VITE_TENANT_API_URL=/api/v1` so the Vite proxy forwards `/api` to `http://127.0.0.1:8000`.

```powershell
npm install
npm run dev
```

See [FREE_DEMO_DEPLOYMENT.md](../FREE_DEMO_DEPLOYMENT.md) for the free Cloudflare Pages + Render client demo, and [DEPLOYMENT.md](../DEPLOYMENT.md) for local/production notes.

## Scripts

- `npm run dev` — Vite dev server
- `npm run build` — production bundle
- `npm run test:shipment-form` — sender/receiver independence unit checks
- `npm run test:saas-smoke` — API smoke (requires backend on port 8000)
