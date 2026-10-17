# ============================================================
# STEP 31 - FUTURE GIS DISTRICT PRIORITY MAPPING
# Childhood Malnutrition Forecasting Research - Component 4
#
# Uses:
#   data/raw/boundary/geoBoundaries-LKA-ADM2.geojson
#   outputs/reports/30_future_district_risk_prioritization.csv
#
# Keeps the final system layers separate:
#   RF      -> point forecast
#   NGBoost -> probabilistic uncertainty
#   DMBI    -> relative planning priority
#
# IMPORTANT:
# - Priority_Level is a relative planning-priority category,
#   not a clinical emergency classification.
# - NGBoost 95% interval is a probabilistic prediction interval,
#   not "95% accuracy" or "95% certainty".
# - This step does not retrain/recalculate any model or DMBI.
# ============================================================

from pathlib import Path
import json
import re
import warnings

import pandas as pd

try:
    import geopandas as gpd
except ImportError as exc:
    raise ImportError(
        "GeoPandas is required. Install with: pip install geopandas"
    ) from exc

try:
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise ImportError(
        "Matplotlib is required. Install with: pip install matplotlib"
    ) from exc

try:
    import folium
except ImportError as exc:
    raise ImportError(
        "Folium is required. Install with: pip install folium"
    ) from exc

warnings.filterwarnings("ignore")

# ------------------------------------------------------------
# 1. SETTINGS
# ------------------------------------------------------------
DISTRICT = "District"
ORIGIN = "Forecast_Origin_Date"
TARGET = "Forecast_Target_Date"
HORIZON = "Horizon_Months"

EXPECTED_DISTRICTS = 25
EXPECTED_ROWS = 4325

EXAMPLE_TARGET = pd.Timestamp("2026-01-01")
EXAMPLE_HORIZON = 1

PRIORITY_LEVELS = ["Low", "Medium", "High", "Critical"]
PRIORITY_COLORS = {
    "Low": "#2ca25f",
    "Medium": "#fee08b",
    "High": "#f46d43",
    "Critical": "#d73027",
}

# ------------------------------------------------------------
# 2. PATHS
# ------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent

BOUNDARY_PATH = (
    BASE / "data" / "raw" / "boundary" /
    "geoBoundaries-LKA-ADM2.geojson"
)

STEP30_PATH = (
    BASE / "outputs" / "reports" /
    "30_future_district_risk_prioritization.csv"
)

REPORT_DIR = BASE / "outputs" / "reports"
GIS_DIR = BASE / "outputs" / "gis"
MAP_DIR = BASE / "outputs" / "maps"

for folder in [REPORT_DIR, GIS_DIR, MAP_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

CROSSWALK_PATH = REPORT_DIR / "31_gis_district_name_crosswalk.csv"
GIS_CSV_PATH = REPORT_DIR / "31_future_gis_priority_2026_2030.csv"
AUDIT_PATH = REPORT_DIR / "31_future_gis_audit.csv"
METHOD_PATH = REPORT_DIR / "31_future_gis_methodology.json"

BOUNDARY_OUT = GIS_DIR / "31_sri_lanka_district_boundaries_wgs84.geojson"
EXAMPLE_GEOJSON = GIS_DIR / "31_example_priority_2026_01_h1.geojson"
EXAMPLE_HTML = MAP_DIR / "31_example_priority_map_2026_01_h1.html"
EXAMPLE_PNG = MAP_DIR / "31_example_priority_map_2026_01_h1.png"

# ------------------------------------------------------------
# 3. HELPERS
# ------------------------------------------------------------
def section(title):
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)


def normalize_name(value):
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Known spelling variants that can occur across Sri Lankan datasets.
    aliases = {
        "moneragala": "monaragala",
        "mullativu": "mullaitivu",
        "kilinochi": "kilinochchi",
        "kilinochchi district": "kilinochchi",
        "nuwara eliya district": "nuwara eliya",
        "trincomalee district": "trincomalee",
        "batticaloa district": "batticaloa",
    }

    if text.endswith(" district"):
        text = text[:-9].strip()

    return aliases.get(text, text)


def detect_boundary_name_column(gdf):
    preferred = [
        "shapeName", "shape_name", "NAME_2", "NAME2",
        "ADM2_EN", "ADM2_NAME", "District", "district",
        "NAME", "name"
    ]

    for col in preferred:
        if col in gdf.columns:
            return col

    candidates = []
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        try:
            n = gdf[col].astype(str).nunique()
        except Exception:
            continue
        if 20 <= n <= 30:
            candidates.append(col)

    if len(candidates) == 1:
        return candidates[0]

    raise ValueError(
        "Could not detect ADM2 district-name column. "
        f"Columns found: {list(gdf.columns)}"
    )


# ------------------------------------------------------------
# 4. START
# ------------------------------------------------------------
section("STEP 31 - FUTURE GIS DISTRICT PRIORITY MAPPING")
print("\nRules:")
print("- Uses Step 30 final forecast + DMBI + NGBoost output")
print("- Uses Sri Lanka ADM2 district boundary")
print("- No RF/NGBoost retraining")
print("- No CRITIC/TOPSIS/DMBI recalculation")
print("- Map colors represent DMBI planning priority")
print("- NGBoost uncertainty remains a separate map attribute")

# ------------------------------------------------------------
# 5. REQUIRED FILES
# ------------------------------------------------------------
section("CHECK REQUIRED INPUT FILES")
for path in [BOUNDARY_PATH, STEP30_PATH]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found:\n{path}")
    print(f"Found: {path} [PASS]")

# ------------------------------------------------------------
# 6. LOAD STEP 30
# ------------------------------------------------------------
section("LOAD STEP 30 FUTURE PRIORITY + UNCERTAINTY OUTPUT")
forecast = pd.read_csv(STEP30_PATH, low_memory=False)
forecast.columns = [str(c).strip() for c in forecast.columns]

required = {
    DISTRICT, ORIGIN, TARGET, HORIZON,
    "RF_Predicted_Cases",
    "NGBoost_Predictive_Mean",
    "NGBoost_Lower_95",
    "NGBoost_Upper_95",
    "Uncertainty_Level",
    "DMBI_Score",
    "Priority_Rank",
    "Priority_Level",
}
missing = required - set(forecast.columns)
if missing:
    raise ValueError(f"Step 30 missing columns: {sorted(missing)}")

forecast[ORIGIN] = pd.to_datetime(forecast[ORIGIN], errors="coerce")
forecast[TARGET] = pd.to_datetime(forecast[TARGET], errors="coerce")
forecast[HORIZON] = pd.to_numeric(forecast[HORIZON], errors="coerce")

if forecast[[DISTRICT, ORIGIN, TARGET, HORIZON]].isna().any().any():
    raise ValueError("Step 30 contains invalid district/date/horizon values.")

if len(forecast) != EXPECTED_ROWS:
    raise ValueError(f"Expected {EXPECTED_ROWS} rows, found {len(forecast)}")

if forecast[DISTRICT].nunique() != EXPECTED_DISTRICTS:
    raise ValueError("Expected 25 forecast districts.")

forecast["_district_key"] = forecast[DISTRICT].apply(normalize_name)

print(f"Rows              : {len(forecast)} [PASS]")
print(f"Districts         : {forecast[DISTRICT].nunique()} [PASS]")
print(
    f"Target period     : {forecast[TARGET].min().date()} "
    f"to {forecast[TARGET].max().date()}"
)

# ------------------------------------------------------------
# 7. LOAD BOUNDARY
# ------------------------------------------------------------
section("LOAD SRI LANKA ADM2 DISTRICT BOUNDARY")
boundary = gpd.read_file(BOUNDARY_PATH)

if boundary.empty:
    raise ValueError("Boundary GeoJSON is empty.")
if boundary.crs is None:
    raise ValueError("Boundary GeoJSON has no CRS metadata.")
if boundary.geometry.isna().any():
    raise ValueError("Boundary GeoJSON contains missing geometry.")

name_col = detect_boundary_name_column(boundary)
boundary["Boundary_District"] = boundary[name_col].astype(str).str.strip()
boundary["_district_key"] = boundary["Boundary_District"].apply(normalize_name)

print(f"Boundary rows          : {len(boundary)}")
print(f"District-name column   : {name_col}")
print(f"Unique district names  : {boundary['_district_key'].nunique()}")
print(f"Input CRS              : {boundary.crs}")

# ------------------------------------------------------------
# 8. GEOMETRY / CRS QUALITY
# ------------------------------------------------------------
section("BOUNDARY QUALITY CHECK")
invalid_before = int((~boundary.geometry.is_valid).sum())
empty_count = int(boundary.geometry.is_empty.sum())

if empty_count:
    raise ValueError(f"Boundary contains {empty_count} empty geometries.")

if invalid_before:
    print(f"Invalid geometries before repair: {invalid_before}")
    boundary["geometry"] = boundary.geometry.buffer(0)

invalid_after = int((~boundary.geometry.is_valid).sum())
if invalid_after:
    raise ValueError(f"{invalid_after} invalid geometries remain after repair.")

boundary = boundary.to_crs(epsg=4326)

print(f"Invalid geometries      : {invalid_after} [PASS]")
print(f"Empty geometries        : {empty_count} [PASS]")
print(f"Output CRS              : {boundary.crs} [PASS]")

# ------------------------------------------------------------
# 9. DISTRICT NAME ALIGNMENT
# ------------------------------------------------------------
section("DISTRICT NAME ALIGNMENT")
forecast_names = (
    forecast[[DISTRICT, "_district_key"]]
    .drop_duplicates()
    .sort_values(DISTRICT)
)
boundary_names = (
    boundary[["Boundary_District", "_district_key"]]
    .drop_duplicates()
    .sort_values("Boundary_District")
)

crosswalk = forecast_names.merge(
    boundary_names,
    on="_district_key",
    how="outer",
    indicator=True,
)
crosswalk.to_csv(CROSSWALK_PATH, index=False)

forecast_keys = set(forecast_names["_district_key"])
boundary_keys = set(boundary_names["_district_key"])
missing_boundary = forecast_keys - boundary_keys
extra_boundary = boundary_keys - forecast_keys

print(f"Forecast district keys  : {len(forecast_keys)}")
print(f"Boundary district keys  : {len(boundary_keys)}")
print(f"Missing matches         : {len(missing_boundary)}")
print(f"Extra boundary names    : {len(extra_boundary)}")

if missing_boundary or extra_boundary or len(boundary_keys) != 25:
    if missing_boundary:
        print("\nMissing in boundary:")
        for x in sorted(missing_boundary):
            print(f"- {x}")
    if extra_boundary:
        print("\nExtra in boundary:")
        for x in sorted(extra_boundary):
            print(f"- {x}")
    raise ValueError(
        "District alignment failed. Review: "
        f"{CROSSWALK_PATH}"
    )

print("District alignment     : PASS")

# ------------------------------------------------------------
# 10. SAVE STANDARDIZED 25-DISTRICT BOUNDARY
# ------------------------------------------------------------
section("SAVE STANDARDIZED WGS84 DISTRICT BOUNDARY")
boundary_out = boundary[["Boundary_District", "_district_key", "geometry"]].copy()
boundary_out = boundary_out.rename(columns={"Boundary_District": "District"})
boundary_out.to_file(BOUNDARY_OUT, driver="GeoJSON")
print(f"Saved: {BOUNDARY_OUT}")

# ------------------------------------------------------------
# 11. GIS-READY CSV (NO DUPLICATED GEOMETRY)
# ------------------------------------------------------------
section("CREATE GIS-READY 2026-2030 FORECAST TABLE")

# The full 4325-row output is kept as CSV. Geometry stays in one
# separate 25-feature boundary file, which is much smaller and is
# better for a React/Leaflet frontend than repeating the polygon
# geometry 4325 times.
gis_csv = forecast.drop(columns=["_district_key"]).copy()
gis_csv.to_csv(GIS_CSV_PATH, index=False)

print(f"GIS forecast rows       : {len(gis_csv)} [PASS]")
print(f"Saved                   : {GIS_CSV_PATH}")

# ------------------------------------------------------------
# 12. EXAMPLE JOIN FOR JAN 2026 H1
# ------------------------------------------------------------
section("CREATE EXAMPLE JANUARY 2026 H1 GIS MAP")
example = forecast[
    (forecast[TARGET] == EXAMPLE_TARGET) &
    (forecast[HORIZON] == EXAMPLE_HORIZON)
].copy()

if len(example) != 25:
    raise ValueError(
        f"Example map expected 25 districts, found {len(example)}."
    )

example = boundary[["Boundary_District", "_district_key", "geometry"]].merge(
    example,
    on="_district_key",
    how="left",
    validate="one_to_one",
)

example_gdf = gpd.GeoDataFrame(example, geometry="geometry", crs="EPSG:4326")

if example_gdf["RF_Predicted_Cases"].isna().any():
    raise ValueError("Example map has unmatched forecast rows.")

# Save only the 25-feature example joined GeoJSON.
example_geojson = example_gdf.drop(columns=["_district_key"]).copy()
for col in [ORIGIN, TARGET]:
    example_geojson[col] = pd.to_datetime(example_geojson[col]).dt.strftime("%Y-%m-%d")
example_geojson.to_file(EXAMPLE_GEOJSON, driver="GeoJSON")

print(f"Example districts       : {len(example_gdf)} [PASS]")
print(f"Example GeoJSON         : {EXAMPLE_GEOJSON}")

# ------------------------------------------------------------
# 13. STATIC PNG MAP
# ------------------------------------------------------------
section("CREATE STATIC PRIORITY MAP")
fig, ax = plt.subplots(figsize=(9, 12))

for level in PRIORITY_LEVELS:
    layer = example_gdf[example_gdf["Priority_Level"] == level]
    if layer.empty:
        continue
    layer.plot(
        ax=ax,
        color=PRIORITY_COLORS[level],
        edgecolor="black",
        linewidth=0.5,
        label=level,
    )

ax.set_title(
    "Sri Lanka Future Childhood Malnutrition Planning Priority\n"
    "Target: January 2026 | Horizon: H1"
)
ax.axis("off")
ax.legend(title="Planning Priority", loc="lower left")
fig.tight_layout()
fig.savefig(EXAMPLE_PNG, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {EXAMPLE_PNG}")

# ------------------------------------------------------------
# 14. INTERACTIVE HTML MAP
# ------------------------------------------------------------
section("CREATE INTERACTIVE PRIORITY MAP")

minx, miny, maxx, maxy = example_gdf.total_bounds
center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=7,
    tiles="CartoDB positron",
)

example_web = example_gdf.copy()
for col in [ORIGIN, TARGET]:
    example_web[col] = pd.to_datetime(example_web[col]).dt.strftime("%Y-%m-%d")


def style_function(feature):
    level = feature["properties"].get("Priority_Level", "Low")
    return {
        "fillColor": PRIORITY_COLORS.get(level, "#cccccc"),
        "color": "#333333",
        "weight": 1,
        "fillOpacity": 0.75,
    }

folium.GeoJson(
    data=json.loads(example_web.to_json()),
    name="District Planning Priority",
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=[
            DISTRICT,
            "RF_Predicted_Cases",
            "DMBI_Score",
            "Priority_Rank",
            "Priority_Level",
            "NGBoost_Lower_95",
            "NGBoost_Upper_95",
            "Uncertainty_Level",
        ],
        aliases=[
            "District:",
            "RF Predicted Cases:",
            "DMBI Score:",
            "Priority Rank:",
            "Planning Priority:",
            "NGBoost Lower 95%:",
            "NGBoost Upper 95%:",
            "Uncertainty:",
        ],
        localize=True,
        sticky=False,
    ),
).add_to(m)

legend = """
<div style="position:fixed;bottom:30px;left:30px;z-index:9999;
background:white;border:1px solid #999;padding:10px 12px;font-size:13px;">
<b>Planning Priority</b><br>
<span style="color:#2ca25f;">&#9632;</span> Low<br>
<span style="color:#fee08b;">&#9632;</span> Medium<br>
<span style="color:#f46d43;">&#9632;</span> High<br>
<span style="color:#d73027;">&#9632;</span> Critical<br><br>
<b>Note:</b> Relative planning priority,<br>
not a clinical emergency classification.
</div>
"""

m.get_root().html.add_child(folium.Element(legend))
folium.LayerControl().add_to(m)
m.save(EXAMPLE_HTML)
print(f"Saved: {EXAMPLE_HTML}")

# ------------------------------------------------------------
# 15. HARD AUDIT
# ------------------------------------------------------------
section("STEP 31 HARD AUDIT")
checks = [
    ("Boundary file exists", BOUNDARY_PATH.exists(), True),
    ("Step 30 file exists", STEP30_PATH.exists(), True),
    ("Step 30 rows = 4325", len(forecast) == 4325, True),
    ("Forecast districts = 25", forecast[DISTRICT].nunique() == 25, True),
    ("Boundary districts = 25", boundary["_district_key"].nunique() == 25, True),
    ("District names fully aligned", not missing_boundary and not extra_boundary, True),
    ("Boundary geometry valid", bool(boundary.geometry.is_valid.all()), True),
    ("Boundary CRS is WGS84", str(boundary.crs).upper() == "EPSG:4326", True),
    ("GIS CSV rows = 4325", len(gis_csv) == 4325, True),
    ("Example map districts = 25", len(example_gdf) == 25, True),
    ("RF retrained in Step 31", False, False),
    ("NGBoost recalibrated in Step 31", False, False),
    ("DMBI recalculated in Step 31", False, False),
    ("Priority level recalculated in Step 31", False, False),
]

audit_rows = []
for name, result, expected in checks:
    status = "PASS" if result == expected else "FAIL"
    audit_rows.append({
        "Audit_Check": name,
        "Result": result,
        "Expected": expected,
        "Status": status,
    })
    print(f"{name:<58} : {status}")

audit = pd.DataFrame(audit_rows)
audit.to_csv(AUDIT_PATH, index=False)

if (audit["Status"] != "PASS").any():
    raise ValueError("Step 31 hard audit failed.")

# ------------------------------------------------------------
# 16. METHODOLOGY RECORD
# ------------------------------------------------------------
methodology = {
    "step": "31",
    "name": "Future GIS District Priority Mapping",
    "future_period": "2026-01 to 2030-12",
    "boundary_input": str(BOUNDARY_PATH),
    "forecast_input": str(STEP30_PATH),
    "boundary_level": "Sri Lanka ADM2 / district",
    "expected_districts": 25,
    "output_crs": "EPSG:4326",
    "dashboard_design": (
        "Use the standardized 25-district boundary GeoJSON once, "
        "then dynamically join/filter the 4325-row forecast CSV by "
        "District + Forecast_Target_Date + Horizon_Months."
    ),
    "semantics": {
        "RF_Predicted_Cases": "Final Random Forest point forecast",
        "DMBI_Score": "Relative forecast-derived planning priority",
        "Priority_Level": (
            "Low/Medium/High/Critical relative planning-priority tier; "
            "not clinical emergency classification"
        ),
        "NGBoost_95_range": (
            "Probabilistic NGBoost 95% prediction interval; "
            "not 95% accuracy/certainty"
        ),
        "Uncertainty_Level": "Low/Moderate/High forecast uncertainty",
    },
    "recalculation_policy": {
        "random_forest_retrained": False,
        "ngboost_recalibrated": False,
        "critic_recalculated": False,
        "topsis_rerun": False,
        "dmbi_recalculated": False,
        "priority_recalculated": False,
    },
    "next_step": "Step 32 Resource Demand Estimation",
}

with open(METHOD_PATH, "w", encoding="utf-8") as f:
    json.dump(methodology, f, indent=2, default=str)

# ------------------------------------------------------------
# 17. RESULTS
# ------------------------------------------------------------
section("STEP 31 RESULTS")
print("\nRows by horizon:")
print(forecast[HORIZON].value_counts().sort_index().to_string())

print("\nPriority distribution:")
print(
    forecast["Priority_Level"]
    .value_counts()
    .reindex(PRIORITY_LEVELS)
    .to_string()
)

print("\nUncertainty distribution:")
print(forecast["Uncertainty_Level"].value_counts().to_string())

# ------------------------------------------------------------
# 18. COMPLETE
# ------------------------------------------------------------
section("STEP 31 COMPLETE")
print("\nSaved:")
print(f"- District crosswalk      : {CROSSWALK_PATH}")
print(f"- WGS84 district boundary : {BOUNDARY_OUT}")
print(f"- 2026-2030 GIS CSV       : {GIS_CSV_PATH}")
print(f"- Example joined GeoJSON  : {EXAMPLE_GEOJSON}")
print(f"- Example PNG map         : {EXAMPLE_PNG}")
print(f"- Example HTML map        : {EXAMPLE_HTML}")
print(f"- Audit                   : {AUDIT_PATH}")
print(f"- Methodology             : {METHOD_PATH}")

print("\nIMPORTANT:")
print("- Map color = DMBI relative planning priority")
print("- Tooltip includes RF forecast + NGBoost uncertainty")
print("- NGBoost interval is NOT 95% accuracy/certainty")
print("- Full 4325-row geometry is not duplicated; frontend should join the CSV to the 25-district boundary dynamically")

print("\nNEXT:")
print("Send the FULL terminal output before Step 32 Resource Demand Estimation.")
print("\nSTEP 31 - FUTURE GIS DISTRICT PRIORITY MAPPING COMPLETE")
print("=" * 120)
