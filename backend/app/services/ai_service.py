from typing import Any, Optional

from app.services.forecast_service import get_forecast_by_selected_month
from app.services.explainability_service import get_explanations_by_selected_month
from app.services.resource_service import get_resource_plan_by_selected_month
from app.services.warning_service import get_warning_summary


def _get_first(data: Any, keys: list[str], default=None):
    """
    Safely search nested dictionaries/lists for the first matching key.
    This avoids coupling the assistant too tightly to one response shape.
    """
    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]

        for value in data.values():
            result = _get_first(value, keys, None)
            if result is not None:
                return result

    elif isinstance(data, list):
        for item in data:
            result = _get_first(item, keys, None)
            if result is not None:
                return result

    return default


def _get_horizon_record(data: Any, horizon: int) -> Optional[dict]:
    """
    Attempts to locate the H1/H3/H6 record inside different response formats.
    """
    if isinstance(data, dict):
        possible_keys = [
            f"h{horizon}",
            f"H{horizon}",
            str(horizon),
        ]

        for key in possible_keys:
            value = data.get(key)
            if isinstance(value, dict):
                return value

        current_horizon = data.get("horizon") or data.get("Horizon_Months")
        if current_horizon is not None:
            try:
                if int(current_horizon) == horizon:
                    return data
            except (TypeError, ValueError):
                pass

        for value in data.values():
            result = _get_horizon_record(value, horizon)
            if result:
                return result

    elif isinstance(data, list):
        for item in data:
            result = _get_horizon_record(item, horizon)
            if result:
                return result

    return None


def _prediction_value(record: Optional[dict]):
    if not record:
        return None

    return _get_first(
        record,
        [
            "predicted_cases",
            "RF_Predicted_Cases",
            "prediction",
            "forecast",
        ],
    )


def _priority_value(record: Optional[dict]):
    if not record:
        return None

    return _get_first(
        record,
        [
            "priority_level",
            "Priority_Level",
            "severity",
        ],
    )


def _dmbi_value(record: Optional[dict]):
    if not record:
        return None

    return _get_first(
        record,
        [
            "dmbi_score",
            "DMBI_Score",
            "dmbi",
        ],
    )


def _triposha_value(record: Optional[dict]):
    if not record:
        return None

    return _get_first(
        record,
        [
            "estimated_triposha_packets",
            "Estimated_Triposha_Packets_Planning",
            "triposha_packets",
        ],
    )


def _context_required(
    district: Optional[str],
    year: Optional[int],
    month: Optional[int],
):
    return district is not None and year is not None and month is not None


def _forecast_summary(
    district: str,
    year: int,
    month: int,
) -> str:
    data = get_forecast_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    h1 = _get_horizon_record(data, 1)
    h3 = _get_horizon_record(data, 3)
    h6 = _get_horizon_record(data, 6)

    p1 = _prediction_value(h1)
    p3 = _prediction_value(h3)
    p6 = _prediction_value(h6)

    priority = (
        _priority_value(h1)
        or _priority_value(h3)
        or _priority_value(h6)
    )

    answer = (
        f"For {district}, the selected H1 target is "
        f"{year}-{month:02d}. "
    )

    if p1 is not None:
        answer += f"H1 predicts approximately {float(p1):.0f} cases. "

    if p3 is not None:
        answer += f"H3 predicts approximately {float(p3):.0f} cases. "

    if p6 is not None:
        answer += f"H6 predicts approximately {float(p6):.0f} cases. "

    if priority:
        answer += f"The current planning priority is {priority}. "

    answer += (
        "These forecasts are decision-support estimates and should be "
        "interpreted together with professional judgement."
    )

    return answer


def _explain_forecast(
    district: str,
    year: int,
    month: int,
) -> str:
    data = get_explanations_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    dominant_domain = _get_first(
        data,
        [
            "dominant_domain",
            "Dominant_Domain",
        ],
    )

    contribution = _get_first(
        data,
        [
            "dominant_domain_shap",
            "dominant_contribution",
            "Dominant_Domain_SHAP",
        ],
    )

    direction = _get_first(
        data,
        [
            "direction",
            "Direction",
        ],
    )

    explanation = _get_first(
        data,
        [
            "explanation",
            "forecast_explanation",
            "message",
        ],
    )

    answer = f"For {district}, "

    if dominant_domain:
        answer += (
            f"the strongest model explanation is "
            f"{dominant_domain}. "
        )

    if contribution is not None:
        try:
            answer += (
                f"Its model contribution is approximately "
                f"{float(contribution):+.2f} cases relative to the "
                f"model baseline. "
            )
        except (TypeError, ValueError):
            pass

    if direction:
        answer += f"The contribution direction is {direction}. "

    if explanation:
        answer += str(explanation)

    answer += (
        " SHAP describes how the model formed its prediction; "
        "it does not prove that a factor caused malnutrition."
    )

    return answer


def _priority_explanation(
    district: str,
    year: int,
    month: int,
) -> str:
    data = get_forecast_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    h1 = _get_horizon_record(data, 1)

    priority = _priority_value(h1)
    dmbi = _dmbi_value(h1)
    prediction = _prediction_value(h1)

    answer = f"For {district}, "

    if priority:
        answer += f"the H1 planning priority is {priority}. "

    if dmbi is not None:
        try:
            answer += f"The DMBI score is approximately {float(dmbi):.2f}. "
        except (TypeError, ValueError):
            pass

    if prediction is not None:
        try:
            answer += (
                f"The H1 forecast is approximately "
                f"{float(prediction):.0f} cases. "
            )
        except (TypeError, ValueError):
            pass

    answer += (
        "Priority is a planning indicator produced by the existing "
        "decision-support pipeline; the assistant does not recalculate it."
    )

    return answer


def _resource_explanation(
    district: str,
    year: int,
    month: int,
) -> str:
    data = get_resource_plan_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    h1 = _get_horizon_record(data, 1)
    h3 = _get_horizon_record(data, 3)
    h6 = _get_horizon_record(data, 6)

    t1 = _triposha_value(h1)
    t3 = _triposha_value(h3)
    t6 = _triposha_value(h6)

    answer = f"Triposha planning for {district}: "

    if t1 is not None:
        answer += f"H1 approximately {int(round(float(t1)))} packets. "

    if t3 is not None:
        answer += f"H3 approximately {int(round(float(t3)))} packets. "

    if t6 is not None:
        answer += f"H6 approximately {int(round(float(t6)))} packets. "

    answer += (
        "These are planning estimates generated by the existing backend "
        "resource-planning pipeline, not prescriptions."
    )

    return answer


def _warning_explanation() -> str:
    summary = get_warning_summary()

    origin = _get_first(
        summary,
        ["forecast_origin", "Forecast_Origin_Date"],
    )

    warning_count = _get_first(
        summary,
        ["warning_count"],
        0,
    )

    critical_count = _get_first(
        summary,
        ["critical_count"],
        0,
    )

    high_count = _get_first(
        summary,
        ["high_count"],
        0,
    )

    return (
        f"The current early-warning cycle is based on origin {origin}. "
        f"There are {warning_count} active warning districts: "
        f"{critical_count} critical and {high_count} high. "
        "Warnings use the current backend warning cycle and are independent "
        "of the district/month selected on the Forecast page."
    )


def _terminology_answer(message: str) -> Optional[str]:
    text = message.lower()

    if "dmbi" in text:
        return (
            "DMBI is the District Malnutrition Burden Index used by the "
            "decision-support pipeline to support district prioritization. "
            "It combines multiple planning criteria into a district-level "
            "priority score."
        )

    if "shap" in text:
        return (
            "SHAP explains how input features contributed to a model "
            "prediction. Positive values push the prediction upward and "
            "negative values push it downward. SHAP indicates model "
            "contribution, not clinical causation."
        )

    if "h1" in text or "h3" in text or "h6" in text:
        return (
            "H1, H3 and H6 are forecast horizons. H1 is 1 month ahead, "
            "H3 is 3 months ahead, and H6 is 6 months ahead. "
            "The doctor selects the H1 target month on the Forecast page, "
            "and the backend generates all three horizons automatically."
        )

    if "uncertainty" in text or "confidence" in text:
        return (
            "Forecast uncertainty represents how much variability exists "
            "around the forecast estimate. Confidence labels summarize that "
            "uncertainty for decision-support use; they do not guarantee "
            "that the forecast will occur exactly."
        )

    if "forecast origin" in text or "origin" in text:
        return (
            "Forecast origin is the latest time point from which the model "
            "makes future predictions. For example, if the selected H1 "
            "target is January 2026, the forecast origin is December 2025."
        )

    return None


def answer_ai_question(
    message: str,
    district: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    text = message.lower().strip()

    terminology = _terminology_answer(text)

    if terminology:
        return {
            "answer": terminology,
            "intent": "terminology",
            "district": district,
            "year": year,
            "month": month,
        }

    if (
        "warning" in text
        or "alert" in text
        or "critical district" in text
    ):
        return {
            "answer": _warning_explanation(),
            "intent": "warning",
            "district": district,
            "year": year,
            "month": month,
        }

    if not _context_required(district, year, month):
        return {
            "answer": (
                "Please select a district, year, and month from the "
                "Forecast page first. I can then explain the forecast, "
                "priority, SHAP factors, and Triposha planning."
            ),
            "intent": "selection_required",
            "district": district,
            "year": year,
            "month": month,
        }

    if (
        "triposha" in text
        or "resource" in text
        or "packet" in text
    ):
        answer = _resource_explanation(
            district=district,
            year=year,
            month=month,
        )
        intent = "resource_planning"

    elif (
        "why" in text
        or "shap" in text
        or "factor" in text
        or "contribution" in text
        or "explain forecast" in text
    ):
        answer = _explain_forecast(
            district=district,
            year=year,
            month=month,
        )
        intent = "explainability"

    elif (
        "priority" in text
        or "risk" in text
        or "dmbi" in text
        or "critical" in text
        or "high risk" in text
    ):
        answer = _priority_explanation(
            district=district,
            year=year,
            month=month,
        )
        intent = "priority"

    else:
        answer = _forecast_summary(
            district=district,
            year=year,
            month=month,
        )
        intent = "forecast_summary"

    return {
        "answer": answer,
        "intent": intent,
        "district": district,
        "year": year,
        "month": month,
    }