# Hospital integration

Core domain is not coupled to a single hospital system.

## Adapters

- `HospitalAdapter` interface
- `MockHospitalAdapter` (default, supports local demo)
- `FHIRHospitalAdapter` (`FHIR_ENABLED=true`, `FHIR_BASE_URL`, `FHIR_VERSION=R4`)

Mapping helpers (`Patient`, `Encounter`, `Observation`) live in `services/api/app/integrations/fhir/mapping.py`.

Hospital-specific implementations should wrap the interface rather than changing visit/child tables.

External integration is not required for local development.
