import json

from app.config import (
    WARNINGS_FILE,
    WARNING_SUMMARY_FILE,
)


def get_warning_summary():
    if not WARNING_SUMMARY_FILE.exists():
        raise FileNotFoundError(
            f"Warning summary file not found: {WARNING_SUMMARY_FILE}"
        )

    with open(
        WARNING_SUMMARY_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_warnings(
    severity: str | None = None,
    district: str | None = None,
    horizon: int | None = None,
):
    if not WARNINGS_FILE.exists():
        raise FileNotFoundError(
            f"Warnings file not found: {WARNINGS_FILE}"
        )

    with open(
        WARNINGS_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        warnings = json.load(file)

    results = warnings

    if severity:
        severity_clean = severity.strip().upper()

        results = [
            item
            for item in results
            if item["overall_severity"].upper() == severity_clean
        ]

    if district:
        district_clean = district.strip().lower()

        results = [
            item
            for item in results
            if item["district"].strip().lower() == district_clean
        ]

    if horizon:
        results = [
            item
            for item in results
            if horizon in item.get("triggered_horizons", [])
        ]

    return {
        "count": len(results),
        "warnings": results,
    }