/**
 * Softorica SaaS API smoke / regression checks.
 * Run: node scripts/saas-e2e-smoke.mjs
 * Requires tenant API at VITE_TENANT_API_URL (default http://127.0.0.1:8000/api/v1).
 */
import assert from 'node:assert/strict';

const BASE = (process.env.VITE_TENANT_API_URL || 'http://127.0.0.1:8000/api/v1').replace(
  /\/$/,
  ''
);

async function req(method, path, { token, org, body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (org) headers['X-Organization-Id'] = org;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  return { status: res.status, data, url: `${BASE}${path}` };
}

function assertOk(label, result, expected = 200) {
  assert.equal(
    result.status,
    expected,
    `${label} → ${result.status} ${JSON.stringify(result.data)} @ ${result.url}`
  );
}

const stamp = Date.now();
const email = `saas.e2e.${stamp}@example.com`;
const password = 'Password123!';

console.log('BASE', BASE);

// Wrong base regression: legacy goburq host must not be used for tenant SaaS.
assert.notEqual(
  BASE.includes('goburq.com'),
  true,
  'tenant API must not use goburq.com'
);

let r = await req('GET', '/../health'.replace('/api/v1/../health', '')).catch(() => null);
// health is outside /api/v1
{
  const healthBase = BASE.replace(/\/api\/v1$/, '');
  const health = await fetch(`${healthBase}/health`);
  assert.equal(health.status, 200, 'GET /health');
}

r = await req('POST', '/auth/register', {
  body: {
    email,
    password,
    first_name: 'Soft',
    last_name: 'E2E',
    phone: null,
  },
});
assertOk('register', r, 201);

r = await req('POST', '/auth/login', { body: { email, password } });
assertOk('login', r, 200);
assert.ok(r.data.access_token, 'access_token present');
let token = r.data.access_token;

r = await req('GET', '/auth/me', { token });
assertOk('me', r, 200);
assert.equal(r.data.user.email, email);

r = await req('GET', '/auth/organizations', { token });
assertOk('auth/organizations', r, 200);

const slug = `soft-e2e-${stamp}`;
r = await req('POST', '/organizations', {
  token,
  body: { name: `Soft E2E ${stamp}`, slug },
});
assertOk('create org', r, 201);
const orgId = r.data.id;

r = await req('POST', '/auth/switch-organization', {
  token,
  body: { organization_id: orgId },
});
assertOk('switch org', r, 200);
token = r.data.access_token;

r = await req('GET', '/organizations/me', { token, org: orgId });
assertOk('org me', r, 200);

r = await req('GET', '/shipments?page=1&page_size=8', { token, org: orgId });
assertOk('list shipments', r, 200);

r = await req('GET', '/notifications?page=1&page_size=5', { token, org: orgId });
assertOk('list notifications', r, 200);

r = await req('POST', '/customers', {
  token,
  org: orgId,
  body: { name: 'Cust E2E', phone: '03001234567', email: null, country: 'PK' },
});
assertOk('create customer', r, 201);
const customerId = r.data.id;

r = await req('GET', `/customers/${customerId}`, { token, org: orgId });
assertOk('get customer', r, 200);

r = await req('POST', '/shipments', {
  token,
  org: orgId,
  body: {
    status: 'BOOKED',
    service_type: 'STANDARD',
    customer_id: customerId,
    pickup_at: `${new Date().toISOString().slice(0, 10)}T09:00:00`,
    cod_amount: '2500.00',
    currency: 'PKR',
    sender: {
      name: 'Sender A',
      phone: '03001111111',
      email: null,
      address: 'Street 1',
      city: 'Lahore',
      state: null,
      country: 'PK',
      postal_code: null,
    },
    receiver: {
      name: 'Receiver B',
      phone: '03002222222',
      email: null,
      address: 'Street 2',
      city: 'Karachi',
      state: null,
      country: 'PK',
      postal_code: null,
    },
    parcel: { weight_kg: '1.25', package_type: 'BOX', description: 'E2E parcel', quantity: 1 },
  },
});
assertOk('create shipment', r, 201);
const shipmentId = r.data.id;
assert.equal(r.data.receiver.name, 'Receiver B');
assert.equal(r.data.sender.name, 'Sender A');
assert.notEqual(r.data.receiver.name, r.data.sender.name);
assert.ok(String(r.data.tracking_number).startsWith('ORVIA-'), 'ORVIA tracking');
assert.equal(Number(r.data.cod_amount), 2500);
assert.equal(r.data.currency, 'PKR');
assert.ok(r.data.pickup_at, 'pickup_at persisted');

// Prepaid shipment must not carry COD fields
r = await req('POST', '/shipments', {
  token,
  org: orgId,
  body: {
    status: 'BOOKED',
    service_type: 'STANDARD',
    pickup_at: `${new Date().toISOString().slice(0, 10)}T09:00:00`,
    cod_amount: null,
    currency: null,
    sender: {
      name: 'Prepaid Sender',
      phone: '03001111111',
      address: 'Street 1',
      city: 'Lahore',
      country: 'PK',
    },
    receiver: {
      name: 'Prepaid Receiver',
      phone: '03002222222',
      address: 'Street 2',
      city: 'Islamabad',
      country: 'PK',
    },
    parcel: { weight_kg: '1', package_type: 'BOX', quantity: 1 },
  },
});
assertOk('create prepaid shipment', r, 201);
assert.equal(r.data.cod_amount, null);
assert.equal(r.data.sender.name, 'Prepaid Sender');
assert.equal(r.data.receiver.name, 'Prepaid Receiver');

r = await req('GET', `/shipments/${shipmentId}`, { token, org: orgId });
assertOk('shipment detail', r, 200);
assert.equal(r.data.sender.name, 'Sender A');
assert.equal(r.data.receiver.name, 'Receiver B');
const trackingNumber = r.data.tracking_number;

r = await req('GET', '/shipments?page=1&page_size=8', { token, org: orgId });
assertOk('list shipments after create', r, 200);
assert.ok((r.data.items || []).some((s) => s.id === shipmentId), 'shipment in list');

r = await req('GET', `/shipments/${shipmentId}/history`, { token, org: orgId });
assertOk('shipment history', r, 200);

r = await req('GET', `/public/tracking/${encodeURIComponent(trackingNumber)}`);
assertOk('public ORVIA tracking', r, 200);
assert.equal(r.data.tracking_number, trackingNumber);

r = await req('POST', '/riders', {
  token,
  org: orgId,
  body: {
    name: 'Rider E2E',
    phone: '03003333333',
    email: null,
    vehicle_type: 'MOTORCYCLE',
  },
});
assertOk('create rider', r, 201);
const riderId = r.data.id;

for (const status of ['PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY']) {
  r = await req('POST', `/shipments/${shipmentId}/status`, {
    token,
    org: orgId,
    body: { status, note: `to ${status}` },
  });
  assertOk(`status ${status}`, r, 200);
}

r = await req('POST', `/shipments/${shipmentId}/assign-rider`, {
  token,
  org: orgId,
  body: { rider_id: riderId },
});
assertOk('assign rider', r, 200);

r = await req('POST', `/shipments/${shipmentId}/unassign-rider`, {
  token,
  org: orgId,
  body: {},
});
assertOk('unassign rider', r, 200);

r = await req('POST', `/shipments/${shipmentId}/assign-rider`, {
  token,
  org: orgId,
  body: { rider_id: riderId },
});
assertOk('re-assign rider', r, 200);

r = await req('POST', `/shipments/${shipmentId}/status`, {
  token,
  org: orgId,
  body: { status: 'DELIVERED', note: 'delivered' },
});
assertOk('status DELIVERED', r, 200);

r = await req('POST', `/shipments/${shipmentId}/pod`, {
  token,
  org: orgId,
  body: { recipient_name: 'Receiver B', delivery_note: 'left at door' },
});
assertOk('create pod', r, 201);

r = await req('POST', `/shipments/${shipmentId}/pod/uploads`, {
  token,
  org: orgId,
  body: {
    type: 'DELIVERY_PHOTO',
    filename: 'photo.jpg',
    content_type: 'image/jpeg',
    size_bytes: 12,
  },
});
assertOk('request upload', r, 201);
const uploadId = r.data.upload_id;
const uploadUrl = r.data.upload_url;
assert.ok(uploadUrl, 'signed upload url');

const put = await fetch(uploadUrl, {
  method: 'PUT',
  headers: r.data.headers || { 'Content-Type': 'image/jpeg' },
  body: Uint8Array.from([0xff, 0xd8, 0xff, 0xe0, 5, 6, 7, 8, 9, 10, 11, 12]),
});
assert.ok(put.ok || put.status === 200 || put.status === 204, `storage put ${put.status}`);

r = await req('POST', `/shipments/${shipmentId}/pod/uploads/${uploadId}/complete`, {
  token,
  org: orgId,
});
assertOk('complete upload', r, 200);

r = await req('GET', `/shipments/${shipmentId}/pod/evidence`, { token, org: orgId });
assertOk('list evidence', r, 200);
assert.ok((r.data.items || []).length >= 1, 'evidence present');
const evidenceId = r.data.items[0].id;

r = await req('GET', `/shipments/${shipmentId}/pod/evidence/${evidenceId}/download`, {
  token,
  org: orgId,
});
assertOk('download evidence', r, 200);
assert.ok(r.data.download_url, 'signed download url');

r = await req('POST', '/auth/logout', { token });
assert.ok(r.status === 204 || r.status === 200, `logout ${r.status}`);

console.log('PASS Softorica SaaS E2E smoke');
