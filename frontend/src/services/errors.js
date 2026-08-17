/** Map Modules 1–11 `{ error: { code, message } }` payloads to user-facing copy. */

const CODE_MESSAGES = {
  INVALID_CREDENTIALS: 'Invalid email or password.',
  INVALID_TOKEN: 'Your session has expired. Please sign in again.',
  UNAUTHORIZED: 'Your session has expired. Please log in again.',
  FORBIDDEN: "You don't have permission to perform this action.",
  NOT_FOUND: 'The requested resource could not be found.',
  TOO_MANY_REQUESTS: 'Too many attempts. Please try again later.',
  VALIDATION_ERROR: 'Please check the highlighted fields.',
  DUPLICATE_EMAIL: 'An account with this email already exists.',
  DUPLICATE_ORGANIZATION_SLUG: 'That organization slug is already taken.',
  MISSING_ORGANIZATION_MEMBERSHIP: 'Create or join an organization to continue.',
  ORGANIZATION_SUSPENDED: 'This organization is suspended.',
  SHIPMENT_INVALID_TRANSITION: 'That status change is not allowed.',
  SHIPMENT_NOT_CANCELLABLE: 'This shipment cannot be cancelled.',
  SHIPMENT_NOT_EDITABLE: 'This shipment cannot be edited in its current status.',
  POD_ALREADY_EXISTS: 'Proof of delivery already exists for this shipment.',
  POD_NOT_ALLOWED: 'Proof of delivery is only available for delivered shipments.',
  POD_EVIDENCE_EXPIRED: 'This evidence upload has expired.',
  POD_EVIDENCE_NOT_READY: 'This evidence is not ready for download.',
  STORAGE_UNAVAILABLE: 'File storage is temporarily unavailable.',
  INVALID_TRACKING_NUMBER:
    'That is not a valid ORVIA tracking ID. Use the format ORVIA-XXXXXXXXXX.',
};

/** True only for shipment detail URLs like /shipments/{uuid}, not list/query routes. */
function isShipmentDetailPath(path) {
  const clean = String(path || '').split('?')[0];
  return /\/shipments\/[^/]+$/.test(clean) && !/\/shipments\/?$/.test(clean);
}

function shipmentNotFoundMessage(path) {
  if (isShipmentDetailPath(path)) {
    return 'Shipment not found.';
  }
      return 'Shipments could not be loaded. Confirm the ORVIA API is running and your organization is selected.';
}

export function getApiErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const data = error?.response?.data;
  const status = error?.response?.status;
  const code = data?.error?.code;
  const message = data?.error?.message;
  const url = error?.config?.baseURL
    ? `${error.config.baseURL}${error.config.url || ''}`
    : error?.config?.url;
  const path = String(error?.config?.url || '');

  if (error?.message === 'Network Error' || error?.code === 'ERR_NETWORK') {
    return 'Unable to connect to the ORVIA API.';
  }

  if (code && CODE_MESSAGES[code] && code !== 'HTTP_ERROR') {
    if (code === 'NOT_FOUND' && path.includes('/shipments')) {
      return shipmentNotFoundMessage(path);
    }
    return CODE_MESSAGES[code];
  }
  if (code === 'HTTP_ERROR' && typeof message === 'string' && message.trim()) {
    if (/not found/i.test(message)) {
      if (import.meta.env.DEV && url) {
        return `API route not found (${status || 404}): ${url}. Confirm VITE_TENANT_API_URL points at Softorica Modules 1–11 and the backend was restarted.`;
      }
      if (path.includes('/shipments')) return shipmentNotFoundMessage(path);
      return 'The requested ORVIA API route was not found. Confirm the tenant API is running.';
    }
    return message;
  }
  if (typeof message === 'string' && message.trim() && code !== 'HTTP_ERROR') return message;
  if (typeof data?.message === 'string') return data.message;
  if (status === 401) return CODE_MESSAGES.UNAUTHORIZED;
  if (status === 403) return CODE_MESSAGES.FORBIDDEN;
  if (status === 404) {
    if (path.includes('/shipments')) return shipmentNotFoundMessage(path);
    return CODE_MESSAGES.NOT_FOUND;
  }
  if (status === 409) return message || 'Conflict with the current resource state.';
  if (status === 422) return CODE_MESSAGES.VALIDATION_ERROR;
  if (status === 429) return CODE_MESSAGES.TOO_MANY_REQUESTS;
  if (status === 500) return CODE_MESSAGES.INTERNAL_ERROR;
  if (status === 503) return 'Service temporarily unavailable.';
  return fallback;
}

export function getValidationDetails(error) {
  const details = error?.response?.data?.error?.details;
  if (!Array.isArray(details)) return {};
  const map = {};
  for (const item of details) {
    const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : null;
    if (field && typeof field === 'string') {
      map[field] = item.msg || 'Invalid value';
    }
  }
  return map;
}
