from pathlib import Path
import json
import warnings
import pandas as pd

try:
    import geopandas as gpd
except ImportError as exc:
    raise ImportError("Install GeoPandas first: python -m pip install geopandas") from exc

try:
    import folium
except ImportError as exc:
    raise ImportError("Install Folium first: python -m pip install folium") from exc

warnings.filterwarnings("ignore")

HORIZONS = [1, 3, 6]
EXPECTED_DISTRICTS = 25
EXPECTED_MONTHS = 12
MAP_CENTER = [7.8731, 80.7718]
MAP_ZOOM = 7

RISK_COLORS = {
    "LOW": "#2ca25f",
    "MEDIUM": "#fec44f",
    "HIGH": "#de2d26",
}

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
BOUNDARY_DIR = RAW_DIR / "boundary"
REPORT_DIR = BASE_DIR / "outputs" / "reports"
MAP_DIR = BASE_DIR / "outputs" / "maps"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
MAP_DIR.mkdir(parents=True, exist_ok=True)

RISK_INPUT_PATH = REPORT_DIR / "23_district_risk_prioritization.csv"

print("\n" + "=" * 120)
print("STEP 24 - SRI LANKA DISTRICT RISK MAP")
print("=" * 120)
print("\n- Step 23 risk results are used unchanged")
print("- No model training or tuning is performed")
print("- This step is visualization only")

if not RISK_INPUT_PATH.exists():
    raise FileNotFoundError(f"Step 23 risk file not found:\n{RISK_INPUT_PATH}")

def normalize_text(value):
    if pd.isna(value):
        return ""
    return (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace(".", "")
    )

def canonical_district_name(value):
    cleaned = normalize_text(value)
    cleaned = cleaned.replace(" district", "").strip()

    aliases = {
        "nuwaraeliya": "nuwara eliya",
        "kilinochi": "kilinochchi",
        "mullaittivu": "mullaitivu",
        "trincomalee": "trincomalee",
        "monaragala": "moneragala",
    }

    compact = cleaned.replace(" ", "")
    if compact in aliases:
        return aliases[compact]

    return cleaned

def find_boundary_file():
    locations = [BOUNDARY_DIR, RAW_DIR, DATA_DIR]
    patterns = ["*.geojson", "*.json", "*.shp"]
    candidates = []

    for location in locations:
        if not location.exists():
            continue
        for pattern in patterns:
            candidates.extend(location.rglob(pattern))

    if not candidates:
        return None

    keywords = ["district", "admin2", "adm2", "sri_lanka", "srilanka", "lka"]

    scored = []
    for path in candidates:
        name = path.name.lower()
        score = sum(keyword in name for keyword in keywords)
        scored.append((score, path))

    scored.sort(key=lambda x: (x[0], str(x[1])), reverse=True)
    return scored[0][1]

BOUNDARY_PATH = find_boundary_file()

if BOUNDARY_PATH is None:
    raise FileNotFoundError(
        "\nSri Lanka district boundary file not found.\n"
        f"Put a district-level .geojson/.json/.shp file inside:\n{BOUNDARY_DIR}\n"
        "Then run Step 24 again."
    )

print(f"\nRisk input     : {RISK_INPUT_PATH}")
print(f"Boundary input : {BOUNDARY_PATH}")

risk_df = pd.read_csv(RISK_INPUT_PATH)

required_cols = {
    "Horizon_Months",
    "District",
    "Forecast_Target_Date",
    "Prediction",
    "Risk_Level",
    "Priority_Rank",
    "Priority_Band",
}

missing_cols = required_cols - set(risk_df.columns)
if missing_cols:
    raise ValueError(f"Step 23 output is missing columns: {sorted(missing_cols)}")

risk_df["Forecast_Target_Date"] = pd.to_datetime(risk_df["Forecast_Target_Date"])
risk_df["District_Key"] = risk_df["District"].apply(canonical_district_name)

district_gdf = gpd.read_file(BOUNDARY_PATH)

if district_gdf.empty:
    raise ValueError("Boundary file contains no records.")

def detect_district_column(gdf, target_names):
    best_column = None
    best_matches = -1

    for column in gdf.columns:
        if column == gdf.geometry.name:
            continue

        values = {
            canonical_district_name(v)
            for v in gdf[column].dropna().unique()
        }

        matches = len(values & target_names)

        if matches > best_matches:
            best_matches = matches
            best_column = column

    return best_column, best_matches

target_names = set(risk_df["District_Key"].unique())

district_name_column, match_count = detect_district_column(
    district_gdf,
    target_names
)

if district_name_column is None:
    raise ValueError("Could not detect a district-name column in the boundary file.")

district_gdf["District_Key"] = district_gdf[district_name_column].apply(
    canonical_district_name
)

boundary_names = set(district_gdf["District_Key"].unique())

missing_in_boundary = sorted(target_names - boundary_names)
extra_in_boundary = sorted(boundary_names - target_names)

print("\n" + "=" * 120)
print("DISTRICT NAME ALIGNMENT")
print("=" * 120)
print(f"Detected boundary district column : {district_name_column}")
print(f"Matched district names            : {len(target_names & boundary_names)}/{EXPECTED_DISTRICTS}")

if missing_in_boundary:
    print("\nMissing from boundary:")
    for name in missing_in_boundary:
        print(f"- {name}")

if extra_in_boundary:
    print("\nAdditional boundary names:")
    for name in extra_in_boundary:
        print(f"- {name}")

if missing_in_boundary:
    raise ValueError(
        "\nDistrict alignment is incomplete. "
        "Add aliases in canonical_district_name() and run again."
    )

if district_gdf.crs is None:
    print("\n[WARNING] Boundary CRS missing; assuming EPSG:4326.")
    district_gdf = district_gdf.set_crs(epsg=4326)
else:
    district_gdf = district_gdf.to_crs(epsg=4326)

alignment_df = pd.DataFrame({
    "District_Key": sorted(target_names),
    "Status": [
        "MATCHED" if name in boundary_names else "NOT MATCHED"
        for name in sorted(target_names)
    ]
})

alignment_path = REPORT_DIR / "24_district_boundary_alignment_audit.csv"
alignment_df.to_csv(alignment_path, index=False)

for horizon in HORIZONS:
    hdf = risk_df[risk_df["Horizon_Months"] == horizon].copy()

    if len(hdf) != 300:
        raise ValueError(f"H{horizon}: expected 300 rows, found {len(hdf)}")

    if hdf["Forecast_Target_Date"].nunique() != EXPECTED_MONTHS:
        raise ValueError(f"H{horizon}: expected 12 target months.")

    month_counts = hdf.groupby("Forecast_Target_Date")["District_Key"].nunique()

    if not month_counts.eq(EXPECTED_DISTRICTS).all():
        raise ValueError(f"H{horizon}: each month must contain 25 districts.")

    print(
        f"H{horizon}: rows={len(hdf)}, "
        f"months={hdf['Forecast_Target_Date'].nunique()}, "
        f"districts={hdf['District_Key'].nunique()} [PASS]"
    )

def risk_color(level):
    return RISK_COLORS.get(str(level).upper(), "#bdbdbd")

def create_map(month_df, horizon, target_date):
    joined = district_gdf.merge(
        month_df,
        on="District_Key",
        how="left",
        suffixes=("_boundary", "_risk"),
    )

    if joined["Risk_Level"].isna().any():
        raise ValueError(
            f"H{horizon} {target_date.date()}: some boundary districts have no risk data."
        )

    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles="CartoDB positron",
        control_scale=True,
    )

    for _, row in joined.iterrows():
        district = str(row["District"])
        prediction = float(row["Prediction"])
        risk_level = str(row["Risk_Level"])
        priority_rank = int(row["Priority_Rank"])
        priority_band = str(row["Priority_Band"])

        one_feature = gpd.GeoDataFrame(
            [row],
            geometry="geometry",
            crs=joined.crs,
        )

        popup_html = (
            f"<b>District:</b> {district}<br>"
            f"<b>Forecast Horizon:</b> H{horizon}<br>"
            f"<b>Target Month:</b> {target_date.strftime('%B %Y')}<br>"
            f"<b>Predicted Cases:</b> {prediction:.2f}<br>"
            f"<b>Risk Level:</b> {risk_level}<br>"
            f"<b>Priority Rank:</b> {priority_rank}<br>"
            f"<b>Priority Band:</b> {priority_band}"
        )

        tooltip_text = (
            f"{district} | {risk_level} | "
            f"Predicted: {prediction:.1f} | Rank: {priority_rank}"
        )

        folium.GeoJson(
           data=row.geometry.__geo_interface__,
            style_function=lambda feature, color=risk_color(risk_level): {
                "fillColor": color,
                "color": "#333333",
                "weight": 1.0,
                "fillOpacity": 0.70,
            },
            highlight_function=lambda feature: {
                "weight": 3,
                "fillOpacity": 0.85,
            },
            tooltip=folium.Tooltip(tooltip_text, sticky=True),
            popup=folium.Popup(popup_html, max_width=350),
        ).add_to(m)

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        z-index: 9999;
        background: white;
        border: 1px solid #666;
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 13px;">
        <b>District Risk Level</b><br>
        <span style="color:{RISK_COLORS['HIGH']};">&#9632;</span> HIGH<br>
        <span style="color:{RISK_COLORS['MEDIUM']};">&#9632;</span> MEDIUM<br>
        <span style="color:{RISK_COLORS['LOW']};">&#9632;</span> LOW
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    title_html = f"""
    <div style="
        position: fixed;
        top: 10px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        background: white;
        border: 1px solid #666;
        border-radius: 6px;
        padding: 8px 15px;
        font-size: 16px;
        font-weight: bold;">
        Sri Lanka Malnutrition Forecast Risk - H{horizon} - {target_date.strftime('%B %Y')}
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    return m

map_index_records = []

for horizon in HORIZONS:
    horizon_df = risk_df[risk_df["Horizon_Months"] == horizon].copy()
    target_dates = sorted(horizon_df["Forecast_Target_Date"].unique())

    horizon_dir = MAP_DIR / f"h{horizon}"
    horizon_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "-" * 120)
    print(f"H{horizon} MAP GENERATION")
    print("-" * 120)

    for i, target_date in enumerate(target_dates, start=1):
        target_date = pd.Timestamp(target_date)

        month_df = horizon_df[
            horizon_df["Forecast_Target_Date"] == target_date
        ].copy()

        m = create_map(
            month_df,
            horizon,
            target_date,
        )

        output_path = (
            horizon_dir
            / f"24_h{horizon}_{target_date.strftime('%Y_%m')}_district_risk_map.html"
        )

        m.save(str(output_path))

        print(
            f"H{horizon} month {i}/{len(target_dates)} | "
            f"{target_date.strftime('%Y-%m')} | map saved"
        )

        map_index_records.append({
            "Horizon_Months": horizon,
            "Forecast_Target_Date": target_date,
            "District_Count": month_df["District_Key"].nunique(),
            "Map_File": str(output_path),
        })

map_index_df = pd.DataFrame(map_index_records)

map_index_path = REPORT_DIR / "24_district_risk_map_index.csv"
map_index_df.to_csv(map_index_path, index=False)

expected_map_count = len(HORIZONS) * EXPECTED_MONTHS
actual_map_count = len(map_index_df)

print("\n" + "=" * 120)
print("STEP 24 VALIDATION")
print("=" * 120)
print(f"Expected maps : {expected_map_count}")
print(f"Created maps  : {actual_map_count}")

if actual_map_count != expected_map_count:
    raise ValueError("Unexpected number of maps.")

if not map_index_df["District_Count"].eq(EXPECTED_DISTRICTS).all():
    raise ValueError("One or more maps do not contain all 25 districts.")

print("All maps contain 25 districts: [PASS]")

print("\n" + "=" * 120)
print("STEP 24 SUMMARY")
print("=" * 120)
print("- 36 interactive district risk maps created")
print("- H1, H3 and H6 mapped separately")
print("- 12 target months mapped per horizon")
print("- Popup shows prediction, risk level and priority rank")
print("- No model training or tuning was performed")
print(f"\nMaps saved to:\n{MAP_DIR}")
print(f"\nMap index:\n{map_index_path}")
print(f"\nAlignment audit:\n{alignment_path}")
print("\nSTEP 24 - SRI LANKA DISTRICT RISK MAP COMPLETE")
print("=" * 120)
