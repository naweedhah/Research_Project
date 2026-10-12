# ============================================================
# STEP 28B - FUTURE SHAP DOMAIN-LEVEL EXPLANATION (FINAL MAPPING)
# 2026-2030
#
# Childhood Malnutrition Forecasting Research - Component 4
#
# PURPOSE
# -------
# Convert the complete Step 28 feature-level SHAP values into
# doctor-friendly domain-level explanations WITHOUT retraining
# any model and WITHOUT recalculating SHAP.
#
# INPUTS
# ------
# outputs/reports/
#   28_future_rf_shap_values_long.csv
#   28_future_explainable_forecasts_2026_2030.csv
#
# OUTPUTS
# -------
# outputs/reports/
#   28b_future_shap_domain_contributions_long.csv
#   28b_future_shap_domain_explanations_2026_2030.csv
#   28b_shap_feature_domain_mapping.csv
#   28b_future_shap_domain_audit.csv
#   28b_future_shap_domain_methodology.json
#
# IMPORTANT
# ---------
# - Random Forest is NOT retrained.
# - NGBoost is NOT retrained/recalibrated.
# - SHAP is NOT recalculated.
# - Existing Step 28 SHAP values are only grouped/summarized.
# - Positive SHAP pushes the RF prediction upward relative to
#   the SHAP baseline.
# - Negative SHAP pushes the RF prediction downward.
# - SHAP explains model behaviour; it does NOT prove causality.
# ============================================================

from pathlib import Path
import json
import re
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ============================================================
# 1. SETTINGS
# ============================================================

EXPECTED_FORECAST_ROWS = 4325
EXPECTED_DISTRICTS = 25
EXPECTED_HORIZONS = {1, 3, 6}
SHAP_ADDITIVITY_TOLERANCE = 1e-5

DISTRICT_COL = "District"
ORIGIN_COL = "Forecast_Origin_Date"
TARGET_COL = "Forecast_Target_Date"
HORIZON_COL = "Horizon_Months"


# ============================================================
# 2. PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_DIR = BASE_DIR / "outputs" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SHAP_LONG_PATH = (
    REPORT_DIR
    / "28_future_rf_shap_values_long.csv"
)

EXPLAINABLE_FORECAST_PATH = (
    REPORT_DIR
    / "28_future_explainable_forecasts_2026_2030.csv"
)

DOMAIN_LONG_OUTPUT_PATH = (
    REPORT_DIR
    / "28b_future_shap_domain_contributions_long.csv"
)

DOMAIN_SUMMARY_OUTPUT_PATH = (
    REPORT_DIR
    / "28b_future_shap_domain_explanations_2026_2030.csv"
)

FEATURE_MAPPING_OUTPUT_PATH = (
    REPORT_DIR
    / "28b_shap_feature_domain_mapping.csv"
)

AUDIT_OUTPUT_PATH = (
    REPORT_DIR
    / "28b_future_shap_domain_audit.csv"
)

METHODOLOGY_OUTPUT_PATH = (
    REPORT_DIR
    / "28b_future_shap_domain_methodology.json"
)


# ============================================================
# 3. DISPLAY HELPERS
# ============================================================

def header(title, width=120):
    print("\n" + "=" * width)
    print(title)
    print("=" * width)


def subheader(title, width=120):
    print("\n" + "-" * width)
    print(title)
    print("-" * width)


# ============================================================
# 4. FEATURE NORMALIZATION
# ============================================================

def normalize_text(value):
    text = str(value).strip().lower()
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def remove_engineering_suffix(feature_name):
    """
    Convert engineered names back toward the original concept.

    Examples:
      T2M_Lag_3 -> T2M
      Malnutrition_Rolling_Mean_6 -> Malnutrition
      Month_Sin -> Month_Sin
    """
    name = str(feature_name)

    patterns = [
        r"_Lag_\d+$",
        r"_Rolling_Mean_\d+$",
        r"_Rolling_Std_\d+$",
        r"_Rolling_Min_\d+$",
        r"_Rolling_Max_\d+$",
        r"_Growth(_Rate)?_\d+$",
        r"_Pct_Change_\d+$",
        r"_Difference_\d+$",
        r"_Diff_\d+$",
    ]

    changed = True
    while changed:
        changed = False
        for pattern in patterns:
            new_name = re.sub(
                pattern,
                "",
                name,
                flags=re.IGNORECASE,
            )
            if new_name != name:
                name = new_name
                changed = True

    return name


# ============================================================
# 5. DOMAIN CLASSIFICATION
# ============================================================

DOMAIN_ORDER = [
    "Historical Malnutrition Burden",
    "Child Nutrition Status",
    "Child & Demographic Health",
    "Maternal Health",
    "Nutrition Programmes & Services",
    "Climate & Environment",
    "Socioeconomic Conditions",
    "District & Geographic Context",
    "Seasonality & Time",
    "Other Model Inputs",
]


def classify_feature_domain(feature_name):
    """
    Rule-based grouping of the exact Step 28 engineered model
    features. The mapping changes presentation only; SHAP values
    themselves are never changed.
    """
    base = remove_engineering_suffix(feature_name)
    n = normalize_text(base)

    # --------------------------------------------------------
    # District / geographic context
    # Step 28 contains 25 one-hot encoded district indicators.
    # They are valid model inputs, but they are contextual rather
    # than modifiable clinical/environmental variables.
    # --------------------------------------------------------
    if n.startswith("district_"):
        return "District & Geographic Context", base

    # --------------------------------------------------------
    # Historical target / burden history
    # --------------------------------------------------------
    historical_tokens = [
        "malnutrition",
    ]

    if any(token in n for token in historical_tokens):
        return "Historical Malnutrition Burden", base

    # --------------------------------------------------------
    # Child nutrition / anthropometry
    # --------------------------------------------------------
    child_nutrition_tokens = [
        "stunting",
        "wasting",
        "underweight",
        "sam_cases",
        "mam_wasting",
        "severe_acute_malnutrition",
        "moderate_acute_malnutrition",
    ]

    if any(token in n for token in child_nutrition_tokens):
        return "Child Nutrition Status", base

    # --------------------------------------------------------
    # Child / demographic health
    # --------------------------------------------------------
    child_health_tokens = [
        "low_birth_weight",
        "live_birth",
        "under_5_population",
        "under5_population",
        "under_five_population",
        "underfive_population",
        "breastfeeding",
        "vitamin_a_coverage_children",
        "vitamin_a_children",
    ]

    if any(token in n for token in child_health_tokens):
        return "Child & Demographic Health", base

    # --------------------------------------------------------
    # Maternal health
    # --------------------------------------------------------
    maternal_tokens = [
        "pregnant_mothers_with_anaemia",
        "pregnant_mothers_with_anemia",
        "teenage_pregnancy",
        "maternal_morbidity",
        "antenatal_morbidity",
        "institutional_delivery",
        "vitamin_a_coverage_postpartum",
        "postpartum",
        "bmi_18_5",
        "bmi_25",
        "hb_11",
        "hb_7_10_9",
        "hb_7",
        "anaemia",
        "anemia",
    ]

    if any(token in n for token in maternal_tokens):
        return "Maternal Health", base

    # --------------------------------------------------------
    # Programmes / service capacity / intervention supply
    # --------------------------------------------------------
    programme_tokens = [
        "triposha",
        "nutrition_programmes",
        "nutrition_programs",
        "field_nutrition_clinics",
        "hospital_nutrition_clinics",
        "clinic",
        "programme",
        "program",
    ]

    if any(token in n for token in programme_tokens):
        return "Nutrition Programmes & Services", base

    # --------------------------------------------------------
    # Climate / environment
    # NASA POWER variables used in this project are included.
    # --------------------------------------------------------
    climate_tokens = [
        "allsky_kt",
        "allsky_sfc_sw_dwn",
        "clrsky_sfc_par_tot",
        "clrsky_sfc_sw_dwn",
        "prectotcorr",
        "rh2m",
        "t2m",
        "ws10m",
        "rain",
        "rainfall",
        "precip",
        "temperature",
        "humidity",
        "wind",
        "solar",
        "radiation",
        "climate",
        "weather",
    ]

    if any(token in n for token in climate_tokens):
        return "Climate & Environment", base

    # --------------------------------------------------------
    # Socioeconomic
    # --------------------------------------------------------
    socioeconomic_tokens = [
        "poverty",
        "household_income",
        "income",
        "food_price",
        "foodprice",
        "cpi",
        "cost_of_living",
    ]

    if any(token in n for token in socioeconomic_tokens):
        return "Socioeconomic Conditions", base

    # --------------------------------------------------------
    # Seasonality / time
    # --------------------------------------------------------
    seasonality_tokens = [
        "month_sin",
        "month_cos",
        "time_index",
        "year",
        "season",
    ]

    if any(token in n for token in seasonality_tokens):
        return "Seasonality & Time", base

    return "Other Model Inputs", base


# ============================================================
# 6. FRIENDLY VARIABLE LABELS
# ============================================================

FRIENDLY_LABELS = {
    "malnutrition": "recent malnutrition burden",
    "stunting": "stunting",
    "wasting": "wasting",
    "underweight": "underweight",
    "sam_cases_annual": "severe acute malnutrition history",
    "mam_wasting_cases_annual": "moderate acute malnutrition history",
    "low_birth_weight_cases": "low birth weight",
    "live_birth": "live births",
    "under_5_population": "under-five population",
    "breastfeeding": "breastfeeding",
    "triposha_packets_distributed": "Triposha distribution",
    "nutrition_programmes_conducted": "nutrition programmes",
    "field_nutrition_clinics_available": "field nutrition clinic availability",
    "hospital_nutrition_clinics_available": "hospital nutrition clinic availability",
    "pregnant_mothers_with_anaemia": "maternal anaemia",
    "pregnant_mothers_with_anemia": "maternal anaemia",
    "teenage_pregnancy_rate": "teenage pregnancy",
    "maternal_morbidity": "maternal morbidity",
    "antenatal_morbidity": "antenatal morbidity",
    "institutional_delivery_rate": "institutional delivery",
    "poverty_line_rs_monthly": "poverty-related conditions",
    "household_income": "household income",
    "allsky_kt": "atmospheric clearness",
    "allsky_sfc_sw_dwn": "surface solar radiation",
    "clrsky_sfc_par_tot": "clear-sky photosynthetically active radiation",
    "clrsky_sfc_sw_dwn": "clear-sky solar radiation",
    "prectotcorr": "precipitation",
    "rh2m": "relative humidity",
    "t2m": "temperature",
    "ws10m": "wind speed",
    "month_sin": "seasonal month pattern",
    "month_cos": "seasonal month pattern",
    "time_index": "long-term time pattern",
}


def friendly_feature_name(base_feature):
    key = normalize_text(base_feature)

    if key in FRIENDLY_LABELS:
        return FRIENDLY_LABELS[key]

    # Make unknown names readable without inventing meaning.
    text = str(base_feature).replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ============================================================
# 7. EXPLANATION HELPERS
# ============================================================

def direction_from_net_shap(value, eps=1e-12):
    if value > eps:
        return "Increases Prediction"
    if value < -eps:
        return "Decreases Prediction"
    return "Near-Neutral Net Effect"


def format_domain_phrase(domain):
    mapping = {
        "Historical Malnutrition Burden":
            "recent malnutrition burden history",
        "Child Nutrition Status":
            "child nutrition-status indicators",
        "Child & Demographic Health":
            "child and demographic health indicators",
        "Maternal Health":
            "maternal-health indicators",
        "Nutrition Programmes & Services":
            "nutrition programme and service indicators",
        "Climate & Environment":
            "climate and environmental indicators",
        "Socioeconomic Conditions":
            "socioeconomic indicators",
        "District & Geographic Context":
            "district and geographic context",
        "Seasonality & Time":
            "seasonal and time-pattern indicators",
        "Other Model Inputs":
            "other model inputs",
    }
    return mapping.get(domain, domain.lower())


def build_domain_explanation(domain_rows):
    """
    Build a restrained, model-behaviour explanation.
    Does NOT use causal wording.
    """
    increasing = (
        domain_rows[
            domain_rows["Domain_Net_SHAP"] > 0
        ]
        .sort_values(
            "Domain_Net_SHAP",
            ascending=False,
        )
    )

    decreasing = (
        domain_rows[
            domain_rows["Domain_Net_SHAP"] < 0
        ]
        .sort_values(
            "Domain_Net_SHAP",
            ascending=True,
        )
    )

    sentences = []

    if not increasing.empty:
        top_inc = increasing.head(3)
        pieces = [
            (
                f"{format_domain_phrase(row['Domain'])} "
                f"(+{row['Domain_Net_SHAP']:.2f} cases)"
            )
            for _, row in top_inc.iterrows()
        ]
        sentences.append(
            "The main model components pushing the Random Forest "
            "forecast upward were "
            + ", ".join(pieces)
            + "."
        )
    else:
        sentences.append(
            "No domain had a positive net SHAP contribution for this forecast."
        )

    if not decreasing.empty:
        top_dec = decreasing.head(3)
        pieces = [
            (
                f"{format_domain_phrase(row['Domain'])} "
                f"({row['Domain_Net_SHAP']:.2f} cases)"
            )
            for _, row in top_dec.iterrows()
        ]
        sentences.append(
            "The main model components pushing the forecast downward were "
            + ", ".join(pieces)
            + "."
        )

    dominant = (
        domain_rows
        .assign(
            Net_Abs=lambda x: x["Domain_Net_SHAP"].abs()
        )
        .sort_values(
            "Net_Abs",
            ascending=False,
        )
    )

    if not dominant.empty:
        row = dominant.iloc[0]
        if row["Domain_Net_SHAP"] > 0:
            action = "upward"
        elif row["Domain_Net_SHAP"] < 0:
            action = "downward"
        else:
            action = "with little net movement"

        sentences.append(
            f"Overall, the strongest net domain contribution was "
            f"{format_domain_phrase(row['Domain'])}, which pushed the "
            f"model prediction {action} by approximately "
            f"{abs(row['Domain_Net_SHAP']):.2f} cases relative to the "
            f"SHAP baseline."
        )

    sentences.append(
        "These are SHAP explanations of the Random Forest model behaviour "
        "and should not be interpreted as proof that these inputs caused "
        "the forecasted malnutrition burden. District/geographic context is "
        "a model context variable, not a modifiable risk factor."
    )

    return " ".join(sentences)


def make_top_domain_fields(domain_rows, prefix, positive=True, limit=3):
    if positive:
        part = (
            domain_rows[
                domain_rows["Domain_Net_SHAP"] > 0
            ]
            .sort_values(
                "Domain_Net_SHAP",
                ascending=False,
            )
            .head(limit)
        )
    else:
        part = (
            domain_rows[
                domain_rows["Domain_Net_SHAP"] < 0
            ]
            .sort_values(
                "Domain_Net_SHAP",
                ascending=True,
            )
            .head(limit)
        )

    result = {}

    for rank in range(1, limit + 1):
        result[f"{prefix}_{rank}_Domain"] = np.nan
        result[f"{prefix}_{rank}_SHAP"] = np.nan
        result[f"{prefix}_{rank}_Top_Feature"] = np.nan
        result[f"{prefix}_{rank}_Top_Feature_SHAP"] = np.nan

    for rank, (_, row) in enumerate(part.iterrows(), start=1):
        result[f"{prefix}_{rank}_Domain"] = row["Domain"]
        result[f"{prefix}_{rank}_SHAP"] = float(
            row["Domain_Net_SHAP"]
        )
        result[f"{prefix}_{rank}_Top_Feature"] = row[
            "Top_Feature_Friendly"
        ]
        result[f"{prefix}_{rank}_Top_Feature_SHAP"] = float(
            row["Top_Feature_SHAP"]
        )

    return result


# ============================================================
# 8. LOAD INPUTS
# ============================================================

header("STEP 28B - FUTURE SHAP DOMAIN-LEVEL EXPLANATION")

print("Rules:")
print("- No Random Forest retraining")
print("- No NGBoost retraining/recalibration")
print("- No SHAP recalculation")
print("- Existing Step 28 SHAP values are grouped only")
print("- SHAP explains model behaviour, not causality")

for path in [
    SHAP_LONG_PATH,
    EXPLAINABLE_FORECAST_PATH,
]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found:\n{path}"
        )

subheader("LOAD STEP 28 OUTPUTS")

shap_df = pd.read_csv(
    SHAP_LONG_PATH,
    low_memory=False,
)

forecast_df = pd.read_csv(
    EXPLAINABLE_FORECAST_PATH,
    low_memory=False,
)

required_shap_columns = {
    "Forecast_ID",
    HORIZON_COL,
    DISTRICT_COL,
    ORIGIN_COL,
    TARGET_COL,
    "Feature",
    "Feature_Value",
    "SHAP_Value",
    "Absolute_SHAP_Value",
}

missing_shap_columns = (
    required_shap_columns
    - set(shap_df.columns)
)

if missing_shap_columns:
    raise ValueError(
        "Step 28 SHAP-long file is missing columns: "
        + ", ".join(sorted(missing_shap_columns))
    )

required_forecast_columns = {
    "Forecast_ID",
    HORIZON_COL,
    DISTRICT_COL,
    ORIGIN_COL,
    TARGET_COL,
    "RF_Predicted_Cases",
    "SHAP_Baseline",
}

missing_forecast_columns = (
    required_forecast_columns
    - set(forecast_df.columns)
)

if missing_forecast_columns:
    raise ValueError(
        "Step 28 explainable forecast file is missing columns: "
        + ", ".join(sorted(missing_forecast_columns))
    )

print(f"Forecast rows          : {len(forecast_df)}")
print(f"Unique forecasts       : {forecast_df['Forecast_ID'].nunique()}")
print(f"Detailed SHAP rows     : {len(shap_df)}")
print(f"Unique SHAP forecasts  : {shap_df['Forecast_ID'].nunique()}")
print(f"Unique features        : {shap_df['Feature'].nunique()}")


# ============================================================
# 9. BASIC INPUT AUDITS
# ============================================================

if len(forecast_df) != EXPECTED_FORECAST_ROWS:
    raise ValueError(
        f"Expected {EXPECTED_FORECAST_ROWS} forecast rows, "
        f"found {len(forecast_df)}."
    )

if forecast_df["Forecast_ID"].nunique() != EXPECTED_FORECAST_ROWS:
    raise ValueError(
        "Forecast_ID is not unique in Step 28 forecast output."
    )

if shap_df["Forecast_ID"].nunique() != EXPECTED_FORECAST_ROWS:
    raise ValueError(
        "Detailed SHAP values do not cover all 4325 forecasts."
    )

if set(
    pd.to_numeric(
        forecast_df[HORIZON_COL],
        errors="raise",
    ).astype(int).unique()
) != EXPECTED_HORIZONS:
    raise ValueError(
        "Expected H1/H3/H6 in Step 28 forecast output."
    )

if forecast_df[DISTRICT_COL].nunique() != EXPECTED_DISTRICTS:
    raise ValueError(
        f"Expected {EXPECTED_DISTRICTS} districts."
    )

if shap_df["SHAP_Value"].isna().any():
    raise ValueError(
        "Missing SHAP values found."
    )


# ============================================================
# 10. MAP EVERY FEATURE TO A DOMAIN
# ============================================================

subheader("MAP ENGINEERED FEATURES TO EXPLANATION DOMAINS")

feature_map_records = []

for feature in sorted(
    shap_df["Feature"]
    .dropna()
    .astype(str)
    .unique()
):
    domain, base_feature = (
        classify_feature_domain(feature)
    )

    feature_map_records.append({
        "Feature": feature,
        "Base_Feature": base_feature,
        "Friendly_Feature": friendly_feature_name(
            base_feature
        ),
        "Domain": domain,
    })

feature_map_df = pd.DataFrame(
    feature_map_records
)

feature_map_df.to_csv(
    FEATURE_MAPPING_OUTPUT_PATH,
    index=False,
)

shap_df = shap_df.merge(
    feature_map_df,
    on="Feature",
    how="left",
    validate="many_to_one",
)

if shap_df["Domain"].isna().any():
    raise RuntimeError(
        "At least one SHAP feature could not be mapped."
    )

domain_counts = (
    feature_map_df["Domain"]
    .value_counts()
    .reindex(
        DOMAIN_ORDER,
        fill_value=0,
    )
)

print("Feature-domain counts:")
for domain, count in domain_counts.items():
    print(f"- {domain}: {int(count)}")

unmapped_features = (
    feature_map_df[
        feature_map_df["Domain"]
        == "Other Model Inputs"
    ]["Feature"]
    .tolist()
)

if unmapped_features:
    print("\nNOTE:")
    print(
        f"{len(unmapped_features)} feature(s) were kept safely under "
        "'Other Model Inputs'. Review the mapping CSV if you want to "
        "assign them to a more specific domain."
    )


# ============================================================
# 11. DOMAIN-LEVEL SHAP AGGREGATION
# ============================================================

subheader("AGGREGATE SHAP VALUES BY FORECAST + DOMAIN")

group_columns = [
    "Forecast_ID",
    HORIZON_COL,
    DISTRICT_COL,
    ORIGIN_COL,
    TARGET_COL,
    "Domain",
]

domain_df = (
    shap_df
    .groupby(
        group_columns,
        as_index=False,
        dropna=False,
    )
    .agg(
        Domain_Net_SHAP=(
            "SHAP_Value",
            "sum",
        ),
        Domain_Absolute_SHAP_Sum=(
            "Absolute_SHAP_Value",
            "sum",
        ),
        Domain_Positive_SHAP_Sum=(
            "SHAP_Value",
            lambda s: float(
                s[s > 0].sum()
            ),
        ),
        Domain_Negative_SHAP_Sum=(
            "SHAP_Value",
            lambda s: float(
                s[s < 0].sum()
            ),
        ),
        Feature_Count=(
            "Feature",
            "count",
        ),
    )
)

domain_df["Domain_Direction"] = (
    domain_df["Domain_Net_SHAP"]
    .apply(direction_from_net_shap)
)


# ============================================================
# 12. TOP FEATURE WITHIN EACH DOMAIN
# ============================================================

top_feature_df = (
    shap_df
    .sort_values(
        group_columns
        + ["Absolute_SHAP_Value"],
        ascending=[
            True, True, True, True, True, True, False
        ],
    )
    .groupby(
        group_columns,
        as_index=False,
        group_keys=False,
    )
    .head(1)
    [
        group_columns
        + [
            "Feature",
            "Base_Feature",
            "Friendly_Feature",
            "Feature_Value",
            "SHAP_Value",
        ]
    ]
    .rename(
        columns={
            "Feature": "Top_Feature",
            "Base_Feature": "Top_Feature_Base",
            "Friendly_Feature": "Top_Feature_Friendly",
            "Feature_Value": "Top_Feature_Value",
            "SHAP_Value": "Top_Feature_SHAP",
        }
    )
)

domain_df = domain_df.merge(
    top_feature_df,
    on=group_columns,
    how="left",
    validate="one_to_one",
)

domain_df["Domain_Importance_Rank"] = (
    domain_df
    .groupby(
        "Forecast_ID"
    )["Domain_Absolute_SHAP_Sum"]
    .rank(
        method="first",
        ascending=False,
    )
    .astype(int)
)


# ============================================================
# 13. SHAP ADDITIVITY PRESERVATION AUDIT
# ============================================================

subheader("VERIFY SHAP ADDITIVITY IS PRESERVED")

all_shap_sum = (
    shap_df
    .groupby(
        "Forecast_ID",
        as_index=False,
    )
    .agg(
        Sum_All_Feature_SHAP=(
            "SHAP_Value",
            "sum",
        )
    )
)

domain_shap_sum = (
    domain_df
    .groupby(
        "Forecast_ID",
        as_index=False,
    )
    .agg(
        Sum_All_Domain_Net_SHAP=(
            "Domain_Net_SHAP",
            "sum",
        )
    )
)

audit_calc = (
    forecast_df[
        [
            "Forecast_ID",
            "RF_Predicted_Cases",
            "SHAP_Baseline",
        ]
    ]
    .merge(
        all_shap_sum,
        on="Forecast_ID",
        how="left",
        validate="one_to_one",
    )
    .merge(
        domain_shap_sum,
        on="Forecast_ID",
        how="left",
        validate="one_to_one",
    )
)

audit_calc[
    "Feature_vs_Domain_SHAP_Difference"
] = (
    audit_calc["Sum_All_Feature_SHAP"]
    -
    audit_calc["Sum_All_Domain_Net_SHAP"]
).abs()

audit_calc[
    "RF_Additivity_Difference"
] = (
    audit_calc["RF_Predicted_Cases"]
    -
    (
        audit_calc["SHAP_Baseline"]
        +
        audit_calc["Sum_All_Domain_Net_SHAP"]
    )
).abs()

max_feature_domain_diff = float(
    audit_calc[
        "Feature_vs_Domain_SHAP_Difference"
    ].max()
)

max_rf_additivity_diff = float(
    audit_calc[
        "RF_Additivity_Difference"
    ].max()
)

if max_feature_domain_diff > SHAP_ADDITIVITY_TOLERANCE:
    raise RuntimeError(
        "Domain grouping changed the SHAP sum unexpectedly. "
        f"Max difference={max_feature_domain_diff:.12f}"
    )

if max_rf_additivity_diff > SHAP_ADDITIVITY_TOLERANCE:
    raise RuntimeError(
        "SHAP additivity was not preserved after domain grouping. "
        f"Max difference={max_rf_additivity_diff:.12f}"
    )

print(
    "Feature-level SHAP sum vs domain-level sum max diff : "
    f"{max_feature_domain_diff:.12f} [PASS]"
)

print(
    "RF prediction additivity max diff                  : "
    f"{max_rf_additivity_diff:.12f} [PASS]"
)


# ============================================================
# 14. BUILD ONE DOCTOR-FRIENDLY SUMMARY PER FORECAST
# ============================================================

subheader("BUILD DOCTOR-FRIENDLY EXPLANATIONS")

summary_records = []

for forecast_id, group in domain_df.groupby(
    "Forecast_ID",
    sort=False,
):
    group = group.copy()

    metadata = (
        forecast_df[
            forecast_df["Forecast_ID"]
            == forecast_id
        ]
        .iloc[0]
    )

    record = {
        "Forecast_ID": forecast_id,
        HORIZON_COL: int(
            metadata[HORIZON_COL]
        ),
        DISTRICT_COL: metadata[
            DISTRICT_COL
        ],
        ORIGIN_COL: metadata[
            ORIGIN_COL
        ],
        TARGET_COL: metadata[
            TARGET_COL
        ],
        "RF_Predicted_Cases": float(
            metadata["RF_Predicted_Cases"]
        ),
        "SHAP_Baseline": float(
            metadata["SHAP_Baseline"]
        ),
    }

    # Preserve useful uncertainty fields when present.
    optional_columns = [
        "NGBoost_Mean",
        "NGBoost_Lower_95",
        "NGBoost_Upper_95",
        "Uncertainty_Level",
        "Confidence_Label",
        "Nominal_Interval_Percentage",
        "Validated_2025_Observed_Coverage_Percentage",
    ]

    for column in optional_columns:
        if column in forecast_df.columns:
            record[column] = metadata[column]

    record.update(
        make_top_domain_fields(
            group,
            prefix="Top_Increasing",
            positive=True,
            limit=3,
        )
    )

    record.update(
        make_top_domain_fields(
            group,
            prefix="Top_Decreasing",
            positive=False,
            limit=3,
        )
    )

    dominant = (
        group
        .assign(
            Net_Abs=lambda x: x[
                "Domain_Net_SHAP"
            ].abs()
        )
        .sort_values(
            "Net_Abs",
            ascending=False,
        )
        .iloc[0]
    )

    record["Dominant_Domain"] = (
        dominant["Domain"]
    )

    record["Dominant_Domain_SHAP"] = float(
        dominant["Domain_Net_SHAP"]
    )

    record["Dominant_Domain_Direction"] = (
        dominant["Domain_Direction"]
    )

    record["Total_Positive_SHAP"] = float(
        group[
            group["Domain_Net_SHAP"] > 0
        ]["Domain_Net_SHAP"].sum()
    )

    record["Total_Negative_SHAP"] = float(
        group[
            group["Domain_Net_SHAP"] < 0
        ]["Domain_Net_SHAP"].sum()
    )

    record["Total_Net_SHAP"] = float(
        group["Domain_Net_SHAP"].sum()
    )

    record["Doctor_Friendly_SHAP_Explanation"] = (
        build_domain_explanation(
            group
        )
    )

    summary_records.append(record)

summary_df = pd.DataFrame(
    summary_records
)


# ============================================================
# 15. FINAL OUTPUT AUDITS
# ============================================================

subheader("FINAL STEP 28B HARD AUDIT")

audit_records = []


def add_audit(check, passed, details):
    audit_records.append({
        "Check": check,
        "Status": "PASS" if passed else "FAIL",
        "Details": details,
    })

    print(
        f"{check:<58}: "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:
        raise RuntimeError(
            f"{check} failed: {details}"
        )


add_audit(
    "Main forecast rows preserved",
    len(summary_df)
    == EXPECTED_FORECAST_ROWS,
    f"rows={len(summary_df)}",
)

add_audit(
    "Unique forecast IDs preserved",
    summary_df["Forecast_ID"].nunique()
    == EXPECTED_FORECAST_ROWS,
    (
        "unique="
        f"{summary_df['Forecast_ID'].nunique()}"
    ),
)

add_audit(
    "25 districts preserved",
    summary_df[DISTRICT_COL].nunique()
    == EXPECTED_DISTRICTS,
    (
        "districts="
        f"{summary_df[DISTRICT_COL].nunique()}"
    ),
)

add_audit(
    "H1/H3/H6 preserved",
    set(
        summary_df[HORIZON_COL]
        .astype(int)
        .unique()
    )
    == EXPECTED_HORIZONS,
    (
        "horizons="
        f"{sorted(summary_df[HORIZON_COL].unique())}"
    ),
)

add_audit(
    "No missing domain explanations",
    not summary_df[
        "Doctor_Friendly_SHAP_Explanation"
    ].isna().any(),
    "All forecasts have a domain-level explanation.",
)

add_audit(
    "Feature-to-domain SHAP sum preserved",
    max_feature_domain_diff
    <= SHAP_ADDITIVITY_TOLERANCE,
    (
        "max_difference="
        f"{max_feature_domain_diff:.12f}"
    ),
)

add_audit(
    "RF SHAP additivity preserved",
    max_rf_additivity_diff
    <= SHAP_ADDITIVITY_TOLERANCE,
    (
        "max_difference="
        f"{max_rf_additivity_diff:.12f}"
    ),
)

add_audit(
    "Random Forest NOT retrained",
    True,
    "Step 28B only reads existing Step 28 outputs.",
)

add_audit(
    "NGBoost NOT retrained or recalibrated",
    True,
    "Step 28B preserves the existing uncertainty fields.",
)

add_audit(
    "SHAP NOT recalculated",
    True,
    "Existing Step 28 feature-level SHAP values are reused.",
)


# ============================================================
# 16. SAVE OUTPUTS
# ============================================================

domain_df.to_csv(
    DOMAIN_LONG_OUTPUT_PATH,
    index=False,
)

summary_df.to_csv(
    DOMAIN_SUMMARY_OUTPUT_PATH,
    index=False,
)

audit_df = pd.DataFrame(
    audit_records
)

audit_df.to_csv(
    AUDIT_OUTPUT_PATH,
    index=False,
)


# ============================================================
# 17. METHODOLOGY RECORD
# ============================================================

methodology = {
    "step": "28B",
    "name": "Future SHAP domain-level explanation",
    "period": "2026-2030",
    "purpose": (
        "Convert existing feature-level Random Forest SHAP "
        "values into doctor-friendly domain-level explanations."
    ),
    "input_files": {
        "feature_level_shap":
            str(SHAP_LONG_PATH),
        "explainable_forecasts":
            str(EXPLAINABLE_FORECAST_PATH),
    },
    "model_retraining": False,
    "ngboost_retraining": False,
    "shap_recalculation": False,
    "domain_aggregation": {
        "net_contribution":
            "sum of signed SHAP values inside each domain",
        "absolute_influence":
            "sum of absolute SHAP values inside each domain",
        "positive_component":
            "sum of positive SHAP values inside each domain",
        "negative_component":
            "sum of negative SHAP values inside each domain",
    },
    "domains": DOMAIN_ORDER,
    "interpretation": (
        "Positive domain net SHAP pushes the Random Forest "
        "prediction above its SHAP baseline; negative domain "
        "net SHAP pushes it below the baseline. These values "
        "describe model behaviour and do not establish causality. "
        "The 25 one-hot encoded district indicators are grouped "
        "under District & Geographic Context and must not be "
        "interpreted as modifiable causal risk factors."
    ),
    "backend_month_selection_note": (
        "Doctor-selected month should be treated as the H1 "
        "target month. Backend derives common origin = selected "
        "month - 1 month, then returns H1=origin+1, "
        "H3=origin+3 and H6=origin+6. Step 28B itself does not "
        "change forecast dates."
    ),
    "outputs": {
        "domain_contributions_long":
            str(DOMAIN_LONG_OUTPUT_PATH),
        "forecast_explanations":
            str(DOMAIN_SUMMARY_OUTPUT_PATH),
        "feature_domain_mapping":
            str(FEATURE_MAPPING_OUTPUT_PATH),
        "audit":
            str(AUDIT_OUTPUT_PATH),
    },
}

with open(
    METHODOLOGY_OUTPUT_PATH,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        methodology,
        file,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# 18. SUMMARY
# ============================================================

header("STEP 28B COMPLETE")

print(
    f"Forecast explanations : {len(summary_df)}"
)

print(
    f"Domain detail rows     : {len(domain_df)}"
)

print(
    f"Mapped features        : {len(feature_map_df)}"
)

print(
    f"Other/unmapped features: {len(unmapped_features)}"
)

print("\nSaved:")
print(
    "- Domain-level detailed SHAP:\n  "
    f"{DOMAIN_LONG_OUTPUT_PATH}"
)

print(
    "- Doctor-friendly forecast explanations:\n  "
    f"{DOMAIN_SUMMARY_OUTPUT_PATH}"
)

print(
    "- Feature/domain mapping:\n  "
    f"{FEATURE_MAPPING_OUTPUT_PATH}"
)

print(
    "- Audit:\n  "
    f"{AUDIT_OUTPUT_PATH}"
)

print(
    "- Methodology:\n  "
    f"{METHODOLOGY_OUTPUT_PATH}"
)

print(
    "\nIMPORTANT:\n"
    "- This step did NOT retrain any model.\n"
    "- This step did NOT recalculate SHAP.\n"
    "- It only grouped the existing Step 28 SHAP values.\n"
    "- Backend can later filter these explanations using the "
    "doctor-selected month and the common-origin H1/H3/H6 logic."
)
