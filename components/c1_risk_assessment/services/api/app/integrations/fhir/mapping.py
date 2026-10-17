"""FHIR mapping stubs. Core domain is never coupled to a single hospital system."""

from __future__ import annotations


def map_patient(resource: dict) -> dict:
    return {
        "external_id": resource.get("id"),
        "birth_date": resource.get("birthDate"),
        "sex": (resource.get("gender") or "unknown"),
    }


def map_encounter(resource: dict) -> dict:
    return {
        "external_id": resource.get("id"),
        "period": resource.get("period"),
        "status": resource.get("status"),
    }


def map_observation(resource: dict) -> dict:
    return {
        "code": resource.get("code"),
        "value": resource.get("valueQuantity") or resource.get("valueString"),
        "effective": resource.get("effectiveDateTime"),
    }
