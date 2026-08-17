/**
 * Legacy customer-portal API (goburq.com). Do not rename.
 * Used by BookParcel, MyBookings, TrackOrder, etc.
 */
export const API_URL = (
  import.meta.env.VITE_API_URL || 'https://goburq.com/api'
).replace(/\/$/, '');

/**
 * Modules 1–11 Softorica tenant SaaS API (FastAPI /api/v1).
 * Override with VITE_TENANT_API_URL in local/production env.
 */
export const TENANT_API_URL = (
  import.meta.env.VITE_TENANT_API_URL || 'http://127.0.0.1:8000/api/v1'
).replace(/\/$/, '');

/** Legacy GoBurq portal session keys — keep forever for booking/tracking. */
export const TOKEN_KEY = 'goburq_token';
export const USER_KEY = 'goburq_user';

/**
 * Softorica SaaS session keys (separate from legacy GoBurq).
 * Prevents SaaS JWTs from being sent to goburq.com and vice versa.
 */
export const TENANT_TOKEN_KEY = 'softorica_access_token';
export const TENANT_USER_KEY = 'softorica_user';
export const TENANT_ORG_KEY = 'softorica_org_id';

/** @deprecated Use TENANT_ORG_KEY for SaaS; kept for any transitional reads. */
export const ORG_KEY = TENANT_ORG_KEY;
