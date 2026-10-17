"""Single approved de-identified feature snapshot for C3/C4 — never invent fields."""

from __future__ import annotations

from typing import Any

from app.models.paediatric import Child, Visit
from app.services.prediction import current_visit_payload


def build_approved_external_feature_snapshot(
    visit: Visit,
    child: Child,
    *,
    feature_schema_version: str,
) -> dict[str, Any]:
    """Approved research predictors only. No names, phones, MRN, notes, or addresses."""
    base = current_visit_payload(visit, child)
    anthro = dict(base.get("anthropometric") or {})
    socio = dict(base.get("socioeconomic") or {})
    dietary = dict(base.get("dietary") or {})
    mch = dict(base.get("maternal_child_health") or {})

    missingness = {
        "anthropometric": sorted(k for k, v in anthro.items() if v is None),
        "socioeconomic": sorted(k for k, v in socio.items() if v is None),
        "dietary": sorted(k for k, v in dietary.items() if v is None),
        "maternal_child_health": sorted(k for k, v in mch.items() if v is None),
    }

    return {
        "feature_schema_version": feature_schema_version,
        "values": {
            "anthropometric": anthro,
            "socioeconomic": socio,
            "dietary": dietary,
            "maternal_child_health": mch,
        },
        "missingness": missingness,
    }


def data_quality_status_from_visit(visit: Visit) -> dict[str, Any]:
    dq = visit.data_quality if isinstance(visit.data_quality, dict) else {}
    flags = list(dq.get("flags") or [])
    complete = dq.get("complete")
    if complete is True:
        status = "READY"
    elif complete is False:
        status = "INCOMPLETE"
    else:
        status = "UNKNOWN"
    return {"status": status, "flags": flags}
