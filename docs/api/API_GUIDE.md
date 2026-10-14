# API guide

OpenAPI UI: `/docs`.

Base URL (development): `http://localhost:8000`

## Auth

`POST /auth/login` `{ email, password, remember_me }` sets HttpOnly cookies and returns `csrf_token`.  
Send `X-CSRF-Token` on POST/PATCH/PUT/DELETE.  
`POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`.

## Roles

`system_admin`, `facility_admin`, `doctor`, `health_worker`, `nutritionist`, `researcher`.

Researchers: `research:read` only — no identifiable child writes.

## Principal resources

- Children: `GET/POST /children`, `GET/PATCH /children/{id}`
- Visits: `POST /children/{id}/visits`, `GET /visits/{id}`, `POST /visits/{id}/predict`
- Trajectory: `GET /children/{id}/trajectory|risk-history|progress`
- Alerts: `GET /alerts`, `PATCH /alerts/{id}/acknowledge|resolve`
- Follow-ups: `POST /children/{id}/follow-ups`, `GET /follow-ups`
- Models: `GET /models`, `POST /models/{id}/activate` (admin)
- Research: `GET /research/model-comparison|experiments|metrics`
- C3: `POST /integrations/counterfactual/request`
- C2: `POST /integrations/explainability/request`
- C4: `POST /integrations/drift/observe`

## Errors

| Code | Meaning |
|---|---|
| 401 | Not authenticated |
| 403 | Insufficient permissions / CSRF |
| 404 | Not found or out of facility scope |
| 422 | Validation / data quality / missing confirmation |
| 503 | Inference unavailable (visit still saved) |

## Health

`GET /health`, `GET /ready`, `GET /metrics` (operational only, no patient data).
