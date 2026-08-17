/**
 * Legacy customer-portal API (goburq.com). Used only by leftover booking/track
 * compatibility routes. Do not rename. Do not point SaaS /app traffic here.
 */
export const API_URL = (
  import.meta.env.VITE_API_URL || 'https://goburq.com/api'
).replace(/\/$/, '');

/**
 * ORVIA tenant SaaS API (FastAPI /api/v1).
 * Local Vite: keep VITE_TENANT_API_URL=/api/v1 so the proxy forwards to 127.0.0.1:8000.
 * Cloudflare Pages: set VITE_TENANT_API_URL to the public Render origin + /api/v1.
 * Never bake localhost into a production build.
 */
export const TENANT_API_URL = (
  import.meta.env.VITE_TENANT_API_URL ||
  (import.meta.env.PROD ? '/api/v1' : '/api/v1')
).replace(/\/$/, '');

/** Legacy portal session keys — keep for booking/tracking compatibility only. */
export const TOKEN_KEY = 'goburq_token';
export const USER_KEY = 'goburq_user';

/**
 * ORVIA SaaS session keys (separate from legacy portal keys).
 * Prevents SaaS JWTs from being sent to goburq.com and vice versa.
 */
export const TENANT_TOKEN_KEY = 'softorica_access_token';
export const TENANT_USER_KEY = 'softorica_user';
export const TENANT_ORG_KEY = 'softorica_org_id';

/** @deprecated Use TENANT_ORG_KEY for SaaS; kept for any transitional reads. */
export const ORG_KEY = TENANT_ORG_KEY;
