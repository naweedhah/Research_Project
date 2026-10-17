from app.services.forecast_service import (
    get_forecast_by_selected_month,
)


def _percentage_change(start_value, end_value):
    if start_value is None or end_value is None:
        return None

    if float(start_value) == 0:
        return None

    return (
        (float(end_value) - float(start_value))
        / float(start_value)
    ) * 100


def _get_direction(
    start_value,
    end_value,
    stable_threshold_percent=5.0,
):
    change_percent = _percentage_change(
        start_value,
        end_value,
    )

    if change_percent is None:
        return "Unknown"

    if change_percent > stable_threshold_percent:
        return "Increasing"

    if change_percent < -stable_threshold_percent:
        return "Decreasing"

    return "Stable"


def _build_planning_interpretation(
    burden_direction,
    resource_direction,
    h1,
    h3,
    h6,
):
    priority_levels = [
        str(h1.get("priority_level", "")).upper(),
        str(h3.get("priority_level", "")).upper(),
        str(h6.get("priority_level", "")).upper(),
    ]

    high_priority = any(
        level in ["HIGH", "CRITICAL"]
        for level in priority_levels
    )

    if (
        burden_direction == "Increasing"
        and high_priority
    ):
        return (
            "Forecasted malnutrition burden is increasing "
            "and the district remains at a high planning "
            "priority. Maintain close nutrition surveillance "
            "and prepare resources according to the forecast "
            "demand and uncertainty range."
        )

    if (
        burden_direction == "Decreasing"
        and high_priority
    ):
        return (
            "Forecasted malnutrition burden shows a decreasing "
            "direction, but the district remains at a high "
            "planning priority. Continue monitoring and maintain "
            "adequate nutrition resources until the improvement "
            "is sustained."
        )

    if burden_direction == "Increasing":
        return (
            "Forecasted malnutrition burden is increasing. "
            "Closer monitoring and forward resource planning "
            "are recommended for the selected district."
        )

    if burden_direction == "Decreasing":
        return (
            "Forecasted malnutrition burden is decreasing. "
            "Continue routine monitoring and review whether "
            "the improvement is sustained across forecast "
            "horizons."
        )

    if resource_direction == "Increasing":
        return (
            "Forecasted case burden is relatively stable, but "
            "resource demand is increasing. Resource planning "
            "should account for the higher projected demand."
        )

    return (
        "Forecasted malnutrition burden is relatively stable "
        "across the available horizons. Continue routine "
        "monitoring and use the uncertainty intervals when "
        "planning resources."
    )


def get_clinical_trend_by_selected_month(
    year: int,
    month: int,
    district: str,
):
    forecast = get_forecast_by_selected_month(
        year=year,
        month=month,
        district=district,
    )

    if forecast is None:
        return None

    forecasts = forecast.get(
        "forecasts",
        {},
    )

    h1 = forecasts.get("h1")
    h3 = forecasts.get("h3")
    h6 = forecasts.get("h6")

    if not h1 or not h3 or not h6:
        return None

    h1_cases = h1.get("predicted_cases")
    h3_cases = h3.get("predicted_cases")
    h6_cases = h6.get("predicted_cases")

    h1_triposha = h1.get("triposha_packets")
    h3_triposha = h3.get("triposha_packets")
    h6_triposha = h6.get("triposha_packets")

    burden_direction = _get_direction(
        h1_cases,
        h6_cases,
    )

    resource_direction = _get_direction(
        h1_triposha,
        h6_triposha,
    )

    h1_to_h3_change = _percentage_change(
        h1_cases,
        h3_cases,
    )

    h3_to_h6_change = _percentage_change(
        h3_cases,
        h6_cases,
    )

    h1_to_h6_change = _percentage_change(
        h1_cases,
        h6_cases,
    )

    resource_h1_to_h6_change = _percentage_change(
        h1_triposha,
        h6_triposha,
    )

    planning_interpretation = (
        _build_planning_interpretation(
            burden_direction=burden_direction,
            resource_direction=resource_direction,
            h1=h1,
            h3=h3,
            h6=h6,
        )
    )

    return {
        "district": forecast["district"],

        "selected_year": year,
        "selected_month": month,
        "selected_month_name": forecast[
            "selected_month_name"
        ],

        "forecast_origin": forecast[
            "forecast_origin"
        ],

        "available_horizons": [
            1,
            3,
            6,
        ],

        "trend_summary": {
            "burden_direction": burden_direction,

            "h1_to_h3_change_percent": (
                round(h1_to_h3_change, 2)
                if h1_to_h3_change is not None
                else None
            ),

            "h3_to_h6_change_percent": (
                round(h3_to_h6_change, 2)
                if h3_to_h6_change is not None
                else None
            ),

            "h1_to_h6_change_percent": (
                round(h1_to_h6_change, 2)
                if h1_to_h6_change is not None
                else None
            ),

            "resource_direction": resource_direction,

            "triposha_h1_to_h6_change_percent": (
                round(
                    resource_h1_to_h6_change,
                    2,
                )
                if resource_h1_to_h6_change
                is not None
                else None
            ),
        },

        "forecast_points": {
            "h1": {
                "horizon": 1,
                "target_date": h1.get(
                    "target_date"
                ),
                "predicted_cases": h1_cases,
                "priority_level": h1.get(
                    "priority_level"
                ),
                "dmbi_score": h1.get(
                    "dmbi_score"
                ),
                "triposha_packets": h1_triposha,
                "lower_95": h1.get(
                    "lower_95"
                ),
                "upper_95": h1.get(
                    "upper_95"
                ),
                "confidence_label": h1.get(
                    "confidence_label"
                ),
            },

            "h3": {
                "horizon": 3,
                "target_date": h3.get(
                    "target_date"
                ),
                "predicted_cases": h3_cases,
                "priority_level": h3.get(
                    "priority_level"
                ),
                "dmbi_score": h3.get(
                    "dmbi_score"
                ),
                "triposha_packets": h3_triposha,
                "lower_95": h3.get(
                    "lower_95"
                ),
                "upper_95": h3.get(
                    "upper_95"
                ),
                "confidence_label": h3.get(
                    "confidence_label"
                ),
            },

            "h6": {
                "horizon": 6,
                "target_date": h6.get(
                    "target_date"
                ),
                "predicted_cases": h6_cases,
                "priority_level": h6.get(
                    "priority_level"
                ),
                "dmbi_score": h6.get(
                    "dmbi_score"
                ),
                "triposha_packets": h6_triposha,
                "lower_95": h6.get(
                    "lower_95"
                ),
                "upper_95": h6.get(
                    "upper_95"
                ),
                "confidence_label": h6.get(
                    "confidence_label"
                ),
            },
        },

        "planning_interpretation": (
            planning_interpretation
        ),

        "interpretation_note": (
            "This trend summarizes model forecasts for "
            "decision-support. It does not establish clinical "
            "causation or replace professional assessment."
        ),
    }