import axios from 'axios';
import { TENANT_API_URL } from '../config/api';

/** Softorica SaaS public tracking (ORVIA-XXXXXXXXXX) — no auth. */
export function publicTrackUrl(trackingNumber) {
  const id = encodeURIComponent(String(trackingNumber || '').trim().toUpperCase());
  return `/track?tracking_id=${id}`;
}

export function absolutePublicTrackUrl(trackingNumber) {
  if (typeof window === 'undefined') return publicTrackUrl(trackingNumber);
  return `${window.location.origin}${publicTrackUrl(trackingNumber)}`;
}

const ORVIA_RE = /^ORVIA-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{10}$/;
const GBQ_RE = /^GBQ\d{7,}$/i;

export function isOrviaTrackingId(value) {
  return ORVIA_RE.test(String(value || '').trim().toUpperCase());
}

/** True when the value is intended as an ORVIA ID but may still be malformed. */
export function looksLikeOrviaTrackingId(value) {
  return String(value || '')
    .trim()
    .toUpperCase()
    .startsWith('ORVIA-');
}

export function isGbqTrackingId(value) {
  const cleaned = String(value || '').trim().toUpperCase();
  return GBQ_RE.test(cleaned) && cleaned.length >= 10;
}

export async function fetchSoftoricaPublicTracking(trackingNumber) {
  const cleaned = String(trackingNumber || '').trim().toUpperCase();
  const { data } = await axios.get(
    `${TENANT_API_URL}/public/tracking/${encodeURIComponent(cleaned)}`,
    { headers: { 'Content-Type': 'application/json' } }
  );
  return data;
}
