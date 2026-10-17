# Security

## Authentication

- bcrypt password hashes
- Short-lived JWT access cookie (`cnip_access`)
- Rotating refresh cookie (`cnip_refresh`)
- CSRF token for unsafe methods
- Account lock after repeated failed logins
- Tokens are not stored in `localStorage`

## RBAC

Roles: system_admin, facility_admin, doctor, health_worker, nutritionist, researcher.

Enforced in the API (`require_permission`). Researchers cannot modify child records or view unnecessary identifiers.

## Tenancy and privacy

- Facility scoping on children, visits, alerts
- PostgreSQL RLS as defence in depth
- Caregiver identifiers isolated from ML tables
- External patient IDs encrypted at rest
- Audit log is append-only (no RLS update/delete policies)

## Secrets

Provide JWT and encryption keys via environment. Do not commit `.env`. Development values in `.env.example` are not for production.

## Audit

Login, child view/create/change, visit create, prediction, alert acknowledge, notes, exports, model activation and user changes are recorded without raw passwords, tokens or full feature dumps.
