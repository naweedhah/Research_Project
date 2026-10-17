from __future__ import annotations

from abc import ABC, abstractmethod


class HospitalAdapter(ABC):
    @abstractmethod
    def fetch_patient(self, external_id: str) -> dict | None: ...

    @abstractmethod
    def fetch_encounter(self, external_id: str) -> dict | None: ...


class MockHospitalAdapter(HospitalAdapter):
    def fetch_patient(self, external_id: str) -> dict | None:
        return {"adapter": "mock", "external_id": external_id, "available": False}

    def fetch_encounter(self, external_id: str) -> dict | None:
        return {"adapter": "mock", "external_id": external_id, "available": False}


class FHIRHospitalAdapter(HospitalAdapter):
    def __init__(self, base_url: str, version: str = "R4"):
        self.base_url = base_url.rstrip("/")
        self.version = version

    def fetch_patient(self, external_id: str) -> dict | None:
        import httpx

        r = httpx.get(f"{self.base_url}/Patient/{external_id}", timeout=10)
        r.raise_for_status()
        return r.json()

    def fetch_encounter(self, external_id: str) -> dict | None:
        import httpx

        r = httpx.get(f"{self.base_url}/Encounter", params={"patient": external_id}, timeout=10)
        r.raise_for_status()
        return r.json()


def get_hospital_adapter() -> HospitalAdapter:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.hospital_adapter == "fhir" and settings.fhir_enabled and settings.fhir_base_url:
        return FHIRHospitalAdapter(settings.fhir_base_url, settings.fhir_version)
    return MockHospitalAdapter()
