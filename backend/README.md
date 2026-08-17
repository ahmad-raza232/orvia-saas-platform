# ORVIA Backend — Modules 1–11

SaaS foundation and multi-tenant organization management for ORVIA.

This API is **not** the existing customer portal backend. The live customer app continues to use `https://goburq.com/api`. New SaaS endpoints live under `/api/v1/` on this service.

## Stack

- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.0
- Alembic
- Pydantic v2
- Argon2 password hashing
- JWT access tokens

## Requirements

- Python 3.12+
- Docker (for local PostgreSQL)
- pip

## PostgreSQL setup

From `backend/`:

```bash
docker compose up -d
```

This starts PostgreSQL on **host port 5433** (container 5432) and the API on **host port 8000**. Compose is a local/dev runtime: it does not embed production secrets. Point `DATABASE_URL` inside the API container at the `postgres` service (compose already overrides the host URL from `.env`).

Optional outbox worker:

```bash
docker compose --profile worker up -d --build
```

Optional local object storage (MinIO, development only):

```bash
docker compose --profile storage up -d
```

Production should use a private S3-compatible bucket. MinIO is not required and is not started by `docker compose up -d`.

Default development credentials (local only):

- user: `orvia`
- password: `orvia`
- database: `orvia`
- URL: `postgresql+psycopg://orvia:orvia@localhost:5433/orvia`

## Environment variables

```bash
cp .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy PostgreSQL URL |
| `JWT_SECRET` | Signing key for access tokens. Use a long random value in any shared environment. |
| `JWT_ALGORITHM` | Default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime |
| `CORS_ORIGINS` | Comma-separated browser origins |
| `AUTH_PASSWORD_MIN_LENGTH` | Minimum length for **new** registrations (default 10). Existing hashes still verify. |
| `AUTH_LOGIN_RATE_LIMIT_ENABLED` | Failed-login limiter (default true) |
| `AUTH_LOGIN_RATE_LIMIT_MAX_ATTEMPTS` | Failures per window before HTTP 429 (default 5) |
| `AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS` | Lock window in seconds (default 300) |
| `INVITATION_EXPIRE_HOURS` | Invitation lifetime (default 168 hours / 7 days) |
| `EMAIL_PROVIDER` | `logging` (default) or `smtp` |
| `SMTP_HOST` | SMTP server hostname when using `smtp` |
| `SMTP_PORT` | Default `587` |
| `SMTP_USERNAME` | Optional SMTP username |
| `SMTP_PASSWORD` | Optional SMTP password. Never commit real secrets. |
| `SMTP_FROM` | Legacy from address (used if `SMTP_FROM_EMAIL` is empty) |
| `SMTP_FROM_EMAIL` | Preferred SMTP from address |
| `SMTP_FROM_NAME` | Optional display name for the from header |
| `SMTP_USE_TLS` | Default `true` |
| `SMTP_TIMEOUT_SECONDS` | SMTP connect/send timeout (default 15) |
| `OUTBOX_WORKER_ENABLED` | Set `false` to make `python -m app.worker` exit immediately |
| `OUTBOX_POLL_INTERVAL_SECONDS` | Worker poll interval (default 5) |
| `OUTBOX_BATCH_SIZE` | Events claimed per cycle (default 50) |
| `OUTBOX_PROCESSING_TIMEOUT_SECONDS` | Stale `PROCESSING` recovery window (default 300) |
| `OUTBOX_MAX_ATTEMPTS` | Bounded delivery retries (default 3) |
| `OUTBOX_RETRY_BASE_SECONDS` | Exponential backoff base delay (default 10) |
| `STORAGE_PROVIDER` | `memory` (default, tests/local) or `s3` |
| `S3_ENDPOINT_URL` | Optional. Set to `http://localhost:9000` for local MinIO |
| `S3_REGION` | Default `us-east-1` |
| `S3_BUCKET` | Private bucket name. Required when `STORAGE_PROVIDER=s3` |
| `S3_ACCESS_KEY_ID` | Storage access key. Never commit real secrets |
| `S3_SECRET_ACCESS_KEY` | Storage secret. Never commit real secrets |
| `S3_FORCE_PATH_STYLE` | Default `false`. Set `true` for some MinIO setups |
| `POD_UPLOAD_URL_TTL_SECONDS` | Signed upload URL lifetime (default 300) |
| `POD_DOWNLOAD_URL_TTL_SECONDS` | Signed download URL lifetime (default 120) |
| `POD_SIGNATURE_MAX_BYTES` | Signature image size limit (default 2000000) |
| `POD_PHOTO_MAX_BYTES` | Delivery photo size limit (default 8000000) |
| `POD_EVIDENCE_PENDING_TTL_SECONDS` | Age after which PENDING evidence expires (default 86400) |
| `POD_EVIDENCE_CLEANUP_ENABLED` | Run TTL cleanup inside `python -m app.worker` (default `true`) |
| `POD_EVIDENCE_CLEANUP_INTERVAL_SECONDS` | Cleanup cadence in the worker loop (default 3600) |
| `POD_EVIDENCE_CLEANUP_BATCH_SIZE` | Max PENDING rows expired per cleanup cycle (default 100) |

Never commit `.env` or real secrets.

When `APP_ENV=production`, the process refuses to start with a weak/example `JWT_SECRET`, `DEBUG=true`, `EMAIL_PROVIDER=logging`, or `STORAGE_PROVIDER=memory`. OpenAPI `/docs` is also disabled in production.

## Virtualenv and install

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Migrations

```bash
alembic upgrade head
```

This creates:

- `organizations`
- `users`
- `roles`
- `organization_memberships`
- `organization_invitations`
- `platform_admin_grants`
- `audit_logs`
- `shipments`
- `shipment_status_history`
- `customers`
- `riders`
- `shipment_rider_assignments`
- `proof_of_deliveries`
- `outbox_events`
- `notifications`
- `notification_settings`

and seeds roles:

- `PLATFORM_SUPER_ADMIN` (platform scope, not an organization customer role)
- `TENANT_ADMIN`
- `OPERATIONS_MANAGER`
- `STAFF`
- `CUSTOMER`

```bash
alembic downgrade -1
alembic upgrade head
```

## Development server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API base URL: `http://127.0.0.1:8000/api/v1`
- Health: `GET http://127.0.0.1:8000/health`
- OpenAPI: `http://127.0.0.1:8000/docs`

## Outbox worker

The API process does not send email. Run a separate worker:

```bash
python -m app.worker
```

Optional Docker worker (API and Postgres start with `docker compose up -d`):

```bash
docker compose --profile worker up -d --build
```

The worker polls `outbox_events`, recovers rows stuck in `PROCESSING` longer than `OUTBOX_PROCESSING_TIMEOUT_SECONDS`, and calls `process_pending_outbox_events()`. On a separate interval (`POD_EVIDENCE_CLEANUP_INTERVAL_SECONDS`) it also expires abandoned `PENDING` POD evidence. Cleanup failures are logged and do not stop outbox processing. SMTP is optional; `EMAIL_PROVIDER=logging` records messages locally. `OUTBOX_WORKER_ENABLED=false` makes `python -m app.worker` exit immediately.

Email delivery is **at-least-once**. Duplicate delivery remains possible if SMTP accepts a message and the worker crashes before the database transaction commits. There is no second retry system beyond the outbox. JWT logout is **stateless**: `POST /api/v1/auth/logout` does not revoke tokens; clients must discard the access token.

Production rollback of populated databases should use backup/PITR. Empty-database Alembic round-trips do not prove live rollback safety. Known historical warnings:

- Migration `005_shipment_operations` downgrade cannot hold operational shipment statuses.
- Migration `011_pod_evidence_cleanup` downgrade maps `EXPIRED` evidence to `FAILED`.

## Tests

PostgreSQL must be running. Pytest uses a **separate** database (`orvia_test`) so
`TRUNCATE` never wipes app data in `orvia`.

```bash
# once
docker exec orvia-postgres psql -U orvia -d postgres -c "CREATE DATABASE orvia_test OWNER orvia;"
DATABASE_URL=postgresql+psycopg://orvia:orvia@localhost:5433/orvia_test alembic upgrade head

pytest
```

Override with `TEST_DATABASE_URL` if needed. Pytest refuses to run against DB name
`orvia` unless `TEST_ALLOW_APP_DB=1` (destructive; not recommended).

## Multi-tenant architecture

ORVIA is a platform that hosts many independent organizations (tenants).

```
User
  └── OrganizationMembership ── Organization
                └── Role

OrganizationInvitation (pending join, hashed token)
PlatformAdminGrant (platform scope, not a tenant role)
AuditLog (organization-level actions)
Customer (tenant-owned CRM record)
Rider (tenant-owned operational resource)
Shipment ── optional Customer
Shipment ── optional Rider
Shipment ── ShipmentStatusHistory
Shipment ── ShipmentRiderAssignment (history)
Shipment ── ProofOfDelivery (one, immutable)
OutboxEvent ── Notification (email delivery attempts)
NotificationSetting (per-tenant email enablement)
```

Example:

- Organization A = ABC Express (`abc-express`)
- Organization B = XYZ Logistics (`xyz-logistics`)

Users, members, invitations, and shipments of A must never appear in B. The backend never trusts a frontend-supplied organization id by itself. Access requires:

1. Authenticated user
2. Active membership in that organization
3. Organization status `ACTIVE` (for tenant APIs)

## Organization model

Generic tenant record. No courier-specific or branded fields.

| Field | Notes |
| --- | --- |
| `id` | UUID |
| `name` | Display name |
| `slug` | Unique, lowercase, hyphenated. Reserved values such as `api`, `admin`, `platform` are rejected. |
| `status` | `ACTIVE` or `SUSPENDED` |
| `created_at` / `updated_at` | Timestamps |

Lifecycle:

- Create (authenticated user with no active membership becomes `TENANT_ADMIN`)
- Read / update current organization (`TENANT_ADMIN` for update)
- Suspend / reactivate (`PLATFORM_SUPER_ADMIN` only)

Tenant Admin A cannot update, list, or otherwise act on Organization B.

## Membership model

A user is not owned by a single `organization_id` column. Membership allows one person to belong to multiple organizations.

| Field | Notes |
| --- | --- |
| `user_id` + `organization_id` | Unique together |
| `role_id` | Organization role |
| `status` | `ACTIVE`, `INVITED`, or `SUSPENDED` |

## Role model

Tenant-assignable roles: `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF`, `CUSTOMER`.

`PLATFORM_SUPER_ADMIN` is **not** an organization role. Tenant admins cannot assign it. Platform access is stored in `platform_admin_grants`.

## Organization context and switching

The access token may include an `org` claim:

- After login, if the user has exactly one active membership
- After `POST /api/v1/auth/switch-organization`, which verifies membership and returns a new access token

Optional `X-Organization-Id` is accepted only when the caller already has an **active membership** in that organization. `localStorage` organization IDs are never trusted.

A user in Company A and Company B must call switch-organization (or send a verified membership header) before tenant routes can run. Switching to an organization the user does not belong to is rejected.

## Invitation workflow

Email delivery is **not** implemented in this module.

1. Tenant admin `POST /api/v1/organizations/me/members` with email + tenant role
2. Invitation is stored with a **SHA-256 token hash**. The raw token is **not** returned in API responses.
3. Invitee registers/logs in with that email
4. `POST /api/v1/invitations/accept` with the raw token delivered out of band (email delivery is not implemented in this module)
5. Membership becomes `ACTIVE`

Duplicate pending invitations for the same organization + email are rejected. Raw tokens are never stored and never returned on list endpoints.

## Tenant isolation rules

- Tenant Admin A cannot view, modify, or remove members of B
- Tenant Admin A cannot update or suspend B
- `GET /api/v1/auth/organizations` returns only organizations the caller belongs to
- Suspended organizations cannot be used as tenant context
- Last active `TENANT_ADMIN` cannot be demoted, suspended, or removed

## Super admin capabilities

API only (no dashboard):

- List organizations
- Get organization details (including suspended)
- Suspend organization
- Reactivate organization

## Authentication and organization APIs

| Method | Path | Who |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Public. Creates a user only. |
| `POST` | `/api/v1/auth/login` | Public. JWT access token. |
| `GET` | `/api/v1/auth/me` | Authenticated user |
| `GET` | `/api/v1/auth/organizations` | Authenticated user. Own memberships only. |
| `POST` | `/api/v1/auth/switch-organization` | Authenticated active member |
| `POST` | `/api/v1/auth/logout` | Stateless. Client discards the token. |
| `POST` | `/api/v1/organizations` | Authenticated user with no active membership |
| `GET` | `/api/v1/organizations/me` | Active member of current org |
| `PATCH` | `/api/v1/organizations/me` | `TENANT_ADMIN` |
| `GET` | `/api/v1/organizations/me/members` | `TENANT_ADMIN` |
| `POST` | `/api/v1/organizations/me/members` | `TENANT_ADMIN` (creates invitation) |
| `PATCH` | `/api/v1/organizations/me/members/{id}` | `TENANT_ADMIN` |
| `DELETE` | `/api/v1/organizations/me/members/{id}` | `TENANT_ADMIN` |
| `GET` | `/api/v1/organizations/me/invitations` | `TENANT_ADMIN` |
| `POST` | `/api/v1/invitations/accept` | Authenticated invitee |
| `GET` | `/api/v1/platform/organizations` | Platform super admin |
| `GET` | `/api/v1/platform/organizations/{id}` | Platform super admin |
| `POST` | `/api/v1/platform/organizations/{id}/suspend` | Platform super admin |
| `POST` | `/api/v1/platform/organizations/{id}/reactivate` | Platform super admin |
| `POST` | `/api/v1/shipments` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `GET` | `/api/v1/shipments` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `GET` | `/api/v1/shipments/{id}` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `PATCH` | `/api/v1/shipments/{id}` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `POST` | `/api/v1/shipments/{id}/cancel` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `POST` | `/api/v1/shipments/{id}/status` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `GET` | `/api/v1/shipments/{id}/history` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `POST` | `/api/v1/shipments/{id}/assign-rider` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `POST` | `/api/v1/shipments/{id}/unassign-rider` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `GET` | `/api/v1/shipments/{id}/rider-history` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `POST` | `/api/v1/shipments/{id}/pod` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `GET` | `/api/v1/shipments/{id}/pod` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `POST` | `/api/v1/shipments/{id}/pod/uploads` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `POST` | `/api/v1/shipments/{id}/pod/uploads/{upload_id}/complete` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `GET` | `/api/v1/shipments/{id}/pod/evidence` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `GET` | `/api/v1/shipments/{id}/pod/evidence/{evidence_id}/download` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `GET` | `/api/v1/notifications/settings` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `PATCH` | `/api/v1/notifications/settings` | `TENANT_ADMIN` |
| `GET` | `/api/v1/notifications` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `GET` | `/api/v1/notifications/{id}` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `POST` | `/api/v1/customers` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `GET` | `/api/v1/customers` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `GET` | `/api/v1/customers/{id}` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `PATCH` | `/api/v1/customers/{id}` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `POST` | `/api/v1/customers/{id}/deactivate` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `POST` | `/api/v1/customers/{id}/reactivate` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `GET` | `/api/v1/customers/{id}/shipments` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `POST` | `/api/v1/riders` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `GET` | `/api/v1/riders` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `GET` | `/api/v1/riders/{id}` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |
| `PATCH` | `/api/v1/riders/{id}` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `POST` | `/api/v1/riders/{id}/deactivate` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `POST` | `/api/v1/riders/{id}/reactivate` | `TENANT_ADMIN`, `OPERATIONS_MANAGER` |
| `GET` | `/api/v1/riders/{id}/shipments` | `TENANT_ADMIN`, `OPERATIONS_MANAGER`, `STAFF` |

Passwords are hashed with Argon2. They are never stored or returned in plaintext.

## Errors

Responses use:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password."
  }
}
```

| Code | HTTP |
| --- | --- |
| `VALIDATION_ERROR` | 422 |
| `RESERVED_ORGANIZATION_SLUG` | 422 |
| `INVALID_ROLE` | 400 |
| `INVALID_INVITATION` | 400 |
| `INVITATION_EXPIRED` | 410 |
| `INVALID_CREDENTIALS` | 401 |
| `UNAUTHORIZED` | 401 |
| `INVALID_TOKEN` | 401 |
| `FORBIDDEN` | 403 |
| `MISSING_ORGANIZATION_MEMBERSHIP` | 403 |
| `ORGANIZATION_SUSPENDED` | 403 |
| `NOT_FOUND` | 404 |
| `DUPLICATE_EMAIL` | 409 |
| `DUPLICATE_ORGANIZATION_SLUG` | 409 |
| `DUPLICATE_MEMBERSHIP` | 409 |
| `DUPLICATE_INVITATION` | 409 |
| `LAST_TENANT_ADMIN` | 409 |
| `SHIPMENT_NOT_EDITABLE` | 409 |
| `SHIPMENT_NOT_CANCELLABLE` | 409 |
| `SHIPMENT_INVALID_TRANSITION` | 409 |
| `DUPLICATE_CUSTOMER_EMAIL` | 409 |
| `CUSTOMER_INACTIVE` | 409 |
| `RIDER_INACTIVE` | 409 |
| `RIDER_ALREADY_ASSIGNED` | 409 |
| `RIDER_NOT_ASSIGNED` | 409 |
| `SHIPMENT_NOT_ASSIGNABLE` | 409 |
| `SHIPMENT_NOT_UNASSIGNABLE` | 409 |
| `POD_ALREADY_EXISTS` | 409 |
| `POD_NOT_ALLOWED` | 409 |
| `POD_EVIDENCE_EXPIRED` | 409 |

## Shipment domain

A shipment is a delivery transaction owned by exactly one organization. The existing customer portal still calls this a booking/parcel on `https://goburq.com/api`. This API does not use GBQ tracking IDs.

```
Organization
  ├── Customer
  └── Shipment
        ├── optional Customer
        └── ShipmentStatusHistory
```

Sender and receiver data remain snapshots stored on the shipment at booking time. `customer_id` is optional so Module 3 shipments without a customer continue to work. When present, the customer must belong to the same organization.

### Lifecycle

```
DRAFT
  ↓
BOOKED
  ↓
PICKED_UP
  ↓
IN_TRANSIT
  ↓
OUT_FOR_DELIVERY
  ↓
DELIVERED

DRAFT / BOOKED
      ↓
  CANCELLED
```

Create with `status=DRAFT` or `BOOKED` (default `BOOKED`). Operational advances use `POST /api/v1/shipments/{id}/status`. Cancellation uses `POST /api/v1/shipments/{id}/cancel` only; sending `CANCELLED` to `/status` is rejected.

Valid transitions:

| From | To |
| --- | --- |
| `DRAFT` | `BOOKED`, `CANCELLED` |
| `BOOKED` | `PICKED_UP`, `CANCELLED` |
| `PICKED_UP` | `IN_TRANSIT` |
| `IN_TRANSIT` | `OUT_FOR_DELIVERY` |
| `OUT_FOR_DELIVERY` | `DELIVERED` |

Invalid examples (all `409 SHIPMENT_INVALID_TRANSITION` on `/status`): `DRAFT → DELIVERED`, `BOOKED → IN_TRANSIT`, `PICKED_UP → DELIVERED`, `DELIVERED → IN_TRANSIT`, `IN_TRANSIT → IN_TRANSIT`, `CANCELLED → BOOKED`. Same-status requests are never treated as success and do not write history.

`DELIVERED` and `CANCELLED` are terminal. There is no reopen path. Cancellation after pickup is `409 SHIPMENT_NOT_CANCELLABLE`.

Edit rules:

- `DRAFT`: sender, receiver, parcel, service, reference, notes, pickup, COD amount/currency, customer_id
- `BOOKED`: notes, reference_number, receiver phone/email, customer_id
- `PICKED_UP` / `IN_TRANSIT` / `OUT_FOR_DELIVERY` / `DELIVERED`: notes and reference_number only
- `CANCELLED`: not editable
- `organization_id`, `created_by`, `tracking_number`, and status history cannot be changed through PATCH
- Status itself cannot be changed through PATCH

### Operational timestamps

`pickup_at` remains the **scheduled** pickup time from booking.

Operational timestamps are set once, in UTC, and never overwritten:

| Transition | Timestamp |
| --- | --- |
| `BOOKED` → `PICKED_UP` | `picked_up_at` |
| `PICKED_UP` → `IN_TRANSIT` | `in_transit_at` |
| `IN_TRANSIT` → `OUT_FOR_DELIVERY` | `out_for_delivery_at` |
| `OUT_FOR_DELIVERY` → `DELIVERED` | `delivered_at` |
| `DRAFT`/`BOOKED` → `CANCELLED` | `cancelled_at` |

Existing Module 3 cancelled shipments may have `cancelled_at = NULL`; the column is only set on new cancellations.

### Tracking numbers

Format: `ORVIA-XXXXXXXXXX`

- Prefix `ORVIA` is platform-level today. The generator accepts a prefix argument so a later module can use a tenant prefix.
- Body is 10 non-sequential characters from a Crockford-style alphabet (no `0/O/1/I`).
- Globally unique and indexed.
- Not compatible with legacy `GBQ` IDs.

Reference numbers (for example `ORDER-10023`) are optional, organization-searchable, and not globally unique.

### Permissions

| Role | Create | View | Update | Cancel | Operational status |
| --- | --- | --- | --- | --- | --- |
| `TENANT_ADMIN` | yes | yes | yes | yes | yes |
| `OPERATIONS_MANAGER` | yes | yes | yes | yes | yes |
| `STAFF` | yes | yes | yes | no | yes |
| `CUSTOMER` | disabled | disabled | disabled | disabled | disabled |

CUSTOMER (the membership role) still cannot use shipment or customer-management APIs. That role is reserved for a future end-user portal.

### Tenant isolation

Organization is taken from authenticated membership context. `organization_id` in the request body is ignored. Listing, get, update, cancel, status change, history, and search are all scoped to the current organization. A shipment ID from another tenant returns `404 NOT_FOUND` (existence is not revealed).

### Search and pagination

`GET /api/v1/shipments?page=1&page_size=20&status=BOOKED&q=...`

- `page` starts at 1
- `page_size` maximum 100
- `status` exact filter: `DRAFT`, `BOOKED`, `PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `DELIVERED`, `CANCELLED`
- `rider_id` optional current-rider filter (always combined with the current organization)
- `q` matches tracking number, reference number, receiver name, receiver phone (LIKE, wildcard-escaped)
- Sorted by `created_at` descending
- Database `LIMIT/OFFSET`; lists do not load status history

### Status history

Every create, operational transition, and cancel appends exactly one immutable `shipment_status_history` row. Columns remain `previous_status` / `new_status` (API aliases: `from_status` / `to_status`). Creation still records `previous_status = null` and `new_status = DRAFT|BOOKED` with note `Shipment created` — not a fake transition.

History is append-only. It cannot be sent or rewritten through `PATCH /shipments/{id}`. `GET /api/v1/shipments/{id}/history` returns oldest → newest for the current tenant only.

Concurrent status changes lock the shipment row (`SELECT FOR UPDATE`) so two operators cannot write conflicting status/history in the same transaction.

Shipment rows are not cascade-deleted when an organization is removed (`ON DELETE RESTRICT`). History rows are not cascade-deleted when a shipment is removed (`ON DELETE RESTRICT`).

### Indexes

| Index | Why |
| --- | --- |
| `ix_shipments_organization_id` | Tenant scoping on every query |
| `uq_shipments_tracking_number` | Global uniqueness for public tracking |
| `ix_shipments_org_tracking` | Tenant lookup by tracking number |
| `ix_shipments_org_reference` | Tenant search by customer reference |
| `ix_shipments_org_status` | Status filters |
| `ix_shipments_org_created_at` | Date sorting / pagination |
| `ix_shipments_org_customer` | Tenant-scoped listing by customer |

### Audit events

`SHIPMENT_CREATED`, `SHIPMENT_UPDATED`, `SHIPMENT_CANCELLED`, `SHIPMENT_STATUS_CHANGED`, `SHIPMENT_CUSTOMER_ASSIGNED`

Operational transitions emit `SHIPMENT_STATUS_CHANGED` with `tracking_number`, `from`, and `to`. Cancellation emits `SHIPMENT_CANCELLED` and `SHIPMENT_STATUS_CHANGED` (existing Module 3 contract). Audit details do not include customer phone or address.

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/v1/shipments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sender": {"name": "Asha", "phone": "+10001", "address": "1 Main", "city": "Lahore"},
    "receiver": {"name": "Ben", "phone": "+10002", "address": "2 Harbor", "city": "Karachi"},
    "parcel": {"weight_kg": "2.5", "quantity": 1},
    "service_type": "EXPRESS",
    "reference_number": "ORDER-10023",
    "cod_amount": "1500.00",
    "currency": "PKR"
  }'
```

`cod_amount` / `currency` are booking-time fields only. There is no COD collection or settlement in this module. Currency is a 3-letter code; PKR is not hardcoded.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/shipments/$ID/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "PICKED_UP", "note": "Picked up from customer"}'
```

## Customer domain

A customer is a tenant-owned business record. There is no global customer table. Organization A can never read or assign Organization B customers.

```
Organization A
    ├── Customer A1
    └── Shipment A1 → Customer A1

Organization B
    ├── Customer B1
    └── Shipment B1 → Customer B1
```

### Fields

| Field | Notes |
| --- | --- |
| `id` | UUID |
| `organization_id` | Required. Taken from authenticated tenant context, never from the request body. |
| `customer_code` | `CUS-XXXXXXXX`, unique per organization |
| `name` | Required |
| `phone` | Required. International strings accepted; not Pakistan-only. |
| `email` | Optional. Unique **within one organization** when present. The same email may exist in other organizations. |
| `alternate_phone` | Optional. Not unique. |
| `company_name`, `address`, `city`, `state`, `country`, `postal_code`, `notes` | Optional. `country` is a 2-letter ISO code. |
| `status` | `ACTIVE` or `INACTIVE` |
| `created_by_user_id` | Actor at create time |

### Duplicate handling

- Email is **not** globally unique.
- Within one organization, a non-null email may belong to only one customer (`uq_customers_org_email` partial unique index).
- Phone is not unique. Shared business lines and family numbers are valid.
- `customer_code` is unique per organization.

### Customer code

Format: `CUS-XXXXXXXX`

- 8 non-sequential characters from the same Crockford-style alphabet as tracking numbers (no `0/O/1/I`).
- Tenant uniqueness is enforced in the database.
- Distinct from shipment tracking numbers (`ORVIA-...`). Not GBQ.

### Status lifecycle

`ACTIVE` ↔ `INACTIVE`

- Create starts as `ACTIVE`.
- Deactivate is a soft action. Records are not hard-deleted. There is no `DELETE /customers/{id}` endpoint.
- Inactive customers cannot be assigned to **new** shipments (`409 CUSTOMER_INACTIVE`).
- Existing shipments for an inactive customer remain readable.
- Tenant Admin and Operations Manager can reactivate.

Foreign key: `shipments.customer_id → customers.id` uses **`ON DELETE RESTRICT`**. Customers are business records; if a hard delete were ever attempted, historical shipments must not be silently unlinked or cascade-deleted. Existing Module 3 shipments keep `customer_id = NULL`.

### Assignment rules

When `customer_id` is supplied on create or update:

1. Customer must exist
2. `customer.organization_id` must equal the current organization
3. Customer must be `ACTIVE` when assigning a **different** customer (keeping an existing inactive assignment on a historical shipment is allowed)

Cross-tenant customer IDs return `404 NOT_FOUND`. Existence is not revealed.

`customer_id` remains optional for backward compatibility. Making it mandatory would break existing Module 3 clients that create shipments without a CRM customer.

Shipment responses expose only a safe summary: `customer_id`, `customer_code`, `customer_name`. Email, phone, and address are not included on shipment lists. Lists use `selectinload(Shipment.customer)` to avoid N+1 queries.

`GET /api/v1/customers/{id}` includes simple counts: `shipment_count`, `active_shipment_count` (`DRAFT` + `BOOKED`), `latest_shipment_at`.

`GET /api/v1/customers/{id}/shipments` always filters **both** `organization_id` and `customer_id`.

### Permissions

| Role | Create | View | Update | Deactivate / Reactivate |
| --- | --- | --- | --- | --- |
| `TENANT_ADMIN` | yes | yes | yes | yes |
| `OPERATIONS_MANAGER` | yes | yes | yes | yes |
| `STAFF` | yes | yes | yes | no |
| `CUSTOMER` | disabled | disabled | disabled | disabled |

### Search and pagination

`GET /api/v1/customers?page=1&page_size=20&status=ACTIVE&q=...&sort=created_at&order=desc`

- `page` starts at 1
- `page_size` maximum 100
- `status` exact filter
- `q` matches customer_code, name, email, phone, company_name (LIKE, wildcard-escaped)
- `sort`: `created_at`, `name`, `customer_code`
- `order`: `asc` or `desc`
- Database `LIMIT/OFFSET`; lists do not load shipments

### Indexes

| Index | Why |
| --- | --- |
| `ix_customers_organization_id` | Tenant scoping on every query |
| `uq_customers_org_code` | Unique customer code per organization |
| `ix_customers_org_status` | Status filters |
| `ix_customers_org_email` | Tenant email search |
| `uq_customers_org_email` | Unique non-null email per organization |
| `ix_customers_org_phone` | Tenant phone search |
| `ix_customers_org_created_at` | Default sort / pagination |
| `ix_shipments_org_customer` | Customer shipment listing without scanning all tenant shipments |

### Audit events

`CUSTOMER_CREATED`, `CUSTOMER_UPDATED`, `CUSTOMER_DEACTIVATED`, `CUSTOMER_REACTIVATED`, `SHIPMENT_CUSTOMER_ASSIGNED`

Audit details store codes and field names, not phone numbers or full addresses.

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/v1/customers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Buyer",
    "phone": "+15550000001",
    "email": "john@example.com",
    "company_name": "Buyer Co",
    "city": "Lahore",
    "country": "PK"
  }'
```

## Rider domain

A rider is a tenant-owned operational resource, not a login identity. Module 6 does not implement rider authentication or a rider app.

```
Organization
   ↓
Riders
   ↓
Shipment Assignment
   ↓
OUT_FOR_DELIVERY
   ↓
DELIVERED
```

### Fields

| Field | Notes |
| --- | --- |
| `id` | UUID |
| `organization_id` | From authenticated tenant context |
| `rider_code` | `RDR-XXXXXXXX`, unique per organization |
| `name`, `phone` | Required. International phone strings. |
| `email` | Optional. Not unique globally or per tenant. |
| `vehicle_type` | Optional: `MOTORCYCLE`, `BICYCLE`, `CAR`, `VAN`, `TRUCK`, `WALKING`, `OTHER` |
| `vehicle_number`, `notes` | Optional |
| `status` | `ACTIVE` or `INACTIVE` |

### Status and deactivation

Create starts `ACTIVE`. Deactivate is soft; there is no `DELETE`. **Deactivation is allowed even when the rider is currently assigned.** Current `shipment.rider_id` values are left unchanged. Inactive riders cannot receive **new** assignments.

### Assignment rules

`shipment.rider_id` is the **current** rider. `shipment_rider_assignments` is append-only history.

A rider may be assigned only when:

1. Shipment and rider belong to the current organization
2. Rider is `ACTIVE`
3. Shipment status is `OUT_FOR_DELIVERY`

Unassignment is allowed only while `OUT_FOR_DELIVERY`. After `DELIVERED`, `rider_id` is preserved and unassignment is rejected. `CANCELLED` shipments cannot be assigned or unassigned.

Reassignment while `OUT_FOR_DELIVERY` closes the previous history row (`unassigned_at`) and opens a new one. Assigning the same rider again returns `409 RIDER_ALREADY_ASSIGNED` and does not duplicate history.

The shipment row is locked (`SELECT FOR UPDATE`) before changing `rider_id`. A partial unique index allows only one active assignment (`unassigned_at IS NULL`) per shipment.

### Permissions

| Role | View | Create / update | Deactivate | Assign / unassign |
| --- | --- | --- | --- | --- |
| `TENANT_ADMIN` | yes | yes | yes | yes |
| `OPERATIONS_MANAGER` | yes | yes | yes | yes |
| `STAFF` | yes | no | no | no |
| `CUSTOMER` | no | no | no | no |

### Search

`GET /api/v1/riders?page=1&page_size=20&status=ACTIVE&q=...&sort=created_at&order=desc`

Search matches rider_code, name, phone, email, vehicle_number. Maximum page size 100.

### Audit events

`RIDER_CREATED`, `RIDER_UPDATED`, `RIDER_DEACTIVATED`, `RIDER_REACTIVATED`, `RIDER_ASSIGNED_TO_SHIPMENT`, `RIDER_UNASSIGNED_FROM_SHIPMENT`

Details store rider_code, tracking_number, and previous rider_code when reassigning. Phone and addresses are not logged.

## Proof of delivery

POD is an immutable operational record attached to a **DELIVERED** shipment. It belongs to the shipment's organization.

```
DELIVERED shipment
   ↓
Proof of Delivery (exactly one)
```

Create with `POST /api/v1/shipments/{id}/pod`. There is no PATCH or DELETE.

Rules:

- Status must be `DELIVERED`. All other statuses return `409 POD_NOT_ALLOWED`.
- A second POD returns `409 POD_ALREADY_EXISTS`.
- `organization_id` comes from tenant context.
- `recorded_by_user_id` comes from the authenticated user.
- `delivered_at` is copied from `shipment.delivered_at` (UTC). Clients cannot override it.
- `rider_id` is copied from the shipment when present; a rider is not required.
- Signature and photo are **metadata placeholders only** (file name, MIME type, storage key, optional https URL, size, checksum). Raw files are not stored. URLs are untrusted hints, not verified content. Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`.

Actual POD files are uploaded with signed object-storage URLs (Module 10). Placeholder metadata on the POD row is unchanged.

Permissions: `TENANT_ADMIN` and `OPERATIONS_MANAGER` may create. `STAFF` may view. `CUSTOMER` cannot. Cross-tenant get/create returns `404 NOT_FOUND`.

Shipment detail exposes a safe summary: `pod_id`, `recipient_name`, `delivered_at`, `has_signature`, `has_photo`. Storage keys are only on `GET /pod`.

Audit: `POD_CREATED` with tracking_number, shipment_id, rider_code, recipient_name.

## POD object storage

POD evidence files are stored in private object storage. The API never keeps uploaded binaries, and PostgreSQL never stores file bytes.

Flow:

1. Operations user requests `POST /api/v1/shipments/{id}/pod/uploads`
2. Backend creates a `PENDING` `pod_evidence` row and returns a short-lived signed PUT URL
3. Client uploads directly to object storage
4. Backend `POST .../uploads/{upload_id}/complete` HEADs the object, then marks `UPLOADED` or `FAILED`
5. Authorized users request `GET .../pod/evidence/{evidence_id}/download` for a short-lived signed GET URL

Rules:

- Shipment must be `DELIVERED` and a POD must already exist.
- Evidence types: `SIGNATURE`, `DELIVERY_PHOTO`.
- Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`. `application/octet-stream` is rejected.
- Object keys are generated (`organizations/{org}/shipments/{shipment}/pod/{pod}/{random}`). Client filenames are metadata only.
- Objects stay private. Signed URLs expire. Storage credentials are never returned.
- Evidence is immutable after `UPLOADED`. There is no PATCH or DELETE.
- Abandoned `PENDING` rows older than `POD_EVIDENCE_PENDING_TTL_SECONDS` are marked `EXPIRED` by the worker. Object storage is not deleted.

Permissions: create/complete = `TENANT_ADMIN`, `OPERATIONS_MANAGER`. Read/download follows shipment read roles (`STAFF` allowed, `CUSTOMER` denied). Cross-tenant access returns `404 NOT_FOUND`.

Local development can use `STORAGE_PROVIDER=memory` or optional MinIO (`docker compose --profile storage up -d`). Production uses `STORAGE_PROVIDER=s3` against a private bucket.

Audit: `POD_EVIDENCE_UPLOAD_REQUESTED`, `POD_EVIDENCE_UPLOADED`, `POD_EVIDENCE_UPLOAD_FAILED`, `POD_EVIDENCE_DOWNLOAD_REQUESTED`, `POD_EVIDENCE_EXPIRED`. Audit details never include file bytes, signed URLs, or credentials.

## Abandoned POD evidence cleanup

The existing worker expires stale `PENDING` evidence. It does not expose an HTTP endpoint and does not delete storage objects.

Lifecycle:

```
PENDING → UPLOADED
PENDING → FAILED
PENDING → EXPIRED
```

`UPLOADED` and `FAILED` are never expired. Completing or downloading `EXPIRED` evidence returns `409 POD_EVIDENCE_EXPIRED`.

Cleanup claims rows with `SELECT FOR UPDATE SKIP LOCKED`, ordered by `created_at`, in batches of `POD_EVIDENCE_CLEANUP_BATCH_SIZE`. Each expiration writes `expired_at` and `POD_EVIDENCE_EXPIRED` in the same transaction. Repeat runs are idempotent.

## Notifications and outbox

Shipment lifecycle changes write a tenant-scoped **outbox event** in the same database transaction as the shipment, status history, and audit log. A separate processor (cron/worker later) claims pending events with `SELECT FOR UPDATE SKIP LOCKED`, resolves the customer email, renders a template, and calls an `EmailProvider` adapter.

Events: `SHIPMENT_BOOKED`, `SHIPMENT_PICKED_UP`, `SHIPMENT_IN_TRANSIT`, `SHIPMENT_OUT_FOR_DELIVERY`, `SHIPMENT_DELIVERED`, `SHIPMENT_CANCELLED`, `POD_CREATED`.

Rules:

- Payloads store operational identifiers only (tracking number, shipment id, status, customer id, actor id). No addresses, tokens, or file contents.
- Email is sent only to `customer.email` when the shipment has a linked customer. Otherwise the notification is `SKIPPED`. Staff and tenant admins are not emailed by default.
- Duplicate lifecycle events for the same shipment are ignored (`uq_outbox_org_event_aggregate`). One notification per outbox event and channel.
- Delivery retries are bounded (default 3). A failed send never rolls back the shipment.
- Default provider is `logging`. SMTP is optional via environment variables. Credentials are never hardcoded.
- Settings default to email enabled for every event type. `TENANT_ADMIN` may PATCH `/api/v1/notifications/settings`. `OPERATIONS_MANAGER` may view. `STAFF` and `CUSTOMER` cannot.
- There is no HTTP endpoint to trigger arbitrary emails. Run `python -m app.worker` (or call `process_pending_outbox_events` from a scheduler). Stuck `PROCESSING` rows older than `OUTBOX_PROCESSING_TIMEOUT_SECONDS` are returned to `PENDING`. Retries use exponential backoff: `OUTBOX_RETRY_BASE_SECONDS * 2^(attempt-1)`, then `FAILED`.

Audit logs remain separate. Settings changes emit `NOTIFICATION_SETTINGS_UPDATED`.

## Out of scope (later modules)

Riders exist as tenant records with assignment APIs, delivered shipments can store POD metadata and private object-storage evidence, abandoned PENDING evidence is expired by the worker, and tenants have an email notification outbox with a background worker, but rider login, rider mobile apps, GPS, SMS/WhatsApp, dispatcher, delivery routes, hubs, COD settlement, billing, Stripe, Shopify, WooCommerce, AI, white-label UI, custom domains, international shipping, advanced pricing, public tracking UI, operations dashboard UI, POD file UI, object-storage garbage collection, and a customer-facing portal are not part of this module. The live customer app continues to use `https://goburq.com/api`.
