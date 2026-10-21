from pathlib import Path
import json, re, warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

warnings.filterwarnings('ignore')

# ============================================================
# STEP 29C - DMBI BURDEN-CRITERIA PREPARATION
# ============================================================
# DMBI is a relative district planning-priority index.
# It is NOT a clinical diagnosis and NOT a probability.
#
# Final criteria:
# C1 = Forecasted Malnutrition Cases
# C2 = Forecasted Cases per 1,000 Under-5 Population
# C3 = Forecasted Year-on-Year Burden Growth (%)
#
# Predictors such as Triposha, income, climate and maternal
# morbidity remain forecasting / SHAP inputs; they are NOT
# direct DMBI criteria.
#
# This step prepares raw criteria only. CRITIC and TOPSIS are
# NOT run here.
# ============================================================

RANDOM_STATE = 42
TARGET = 'Malnutrition_Cases'
MODEL_TARGET = 'Forecast_Target'
DISTRICT = 'District'
DATE = 'Date'
ORIGIN = 'Forecast_Origin_Date'
TARGET_DATE = 'Forecast_Target_Date'
HORIZONS = [1, 3, 6]
EXPECTED_DISTRICTS = 25
EXPECTED_FEATURES = 153

RF_CONFIGS = {
    1: dict(Config_ID='RF_B', n_estimators=400, max_depth=20,
            min_samples_split=4, min_samples_leaf=1, max_features='sqrt',
            bootstrap=True, random_state=42, n_jobs=-1),
    3: dict(Config_ID='RF_BASE', n_estimators=300, max_depth=None,
            min_samples_split=2, min_samples_leaf=1, max_features='sqrt',
            bootstrap=True, random_state=42, n_jobs=-1),
    6: dict(Config_ID='RF_BASE', n_estimators=300, max_depth=None,
            min_samples_split=2, min_samples_leaf=1, max_features='sqrt',
            bootstrap=True, random_state=42, n_jobs=-1),
}

EXPECTED_FUTURE_ROWS = {1: 1500, 3: 1450, 6: 1375}
EXPECTED_FUTURE_TOTAL = sum(EXPECTED_FUTURE_ROWS.values())

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / 'data' / 'processed'
REPORT = BASE_DIR / 'outputs' / 'reports'
REPORT.mkdir(parents=True, exist_ok=True)

BASE_PATH = PROCESSED / 'malnutrition_preprocessed_base.csv'
FEATURE_PATHS = {
    1: PROCESSED / 'malnutrition_features_h1.csv',
    3: PROCESSED / 'malnutrition_features_h3.csv',
    6: PROCESSED / 'malnutrition_features_h6.csv',
}
STEP21_PATH = REPORT / '21_final_2025_lockbox_predictions.csv'
STEP27_PATH = REPORT / '27_future_forecasts_2026_2030.csv'
STEP27_PREDICTOR_PATH = REPORT / '27_future_predictor_projection.csv'

OUT_2024_RF = REPORT / '29c_2024_strict_final_rf_predictions.csv'
OUT_2024 = REPORT / '29c_2024_dmbi_criteria_development.csv'
OUT_2025 = REPORT / '29c_2025_dmbi_criteria_validation.csv'
OUT_FUTURE = REPORT / '29c_future_dmbi_criteria_2026_2030.csv'
OUT_SUMMARY = REPORT / '29c_dmbi_criteria_summary.csv'
OUT_AUDIT = REPORT / '29c_dmbi_criteria_audit.csv'
OUT_METHOD = REPORT / '29c_dmbi_criteria_methodology.json'


def head(title):
    print('\n' + '=' * 120)
    print(title)
    print('=' * 120)


def subhead(title):
    print('\n' + '-' * 120)
    print(title)
    print('-' * 120)


def norm(x):
    return re.sub(r'[^a-z0-9]+', '', str(x).lower())


def find_under5(df):
    lookup = {norm(c): c for c in df.columns}
    for key in ['under5population', 'underfivepopulation',
                'under5childpopulation', 'underfivechildpopulation']:
        if key in lookup:
            return lookup[key]
    candidates = [c for c in df.columns
                  if 'under' in norm(c) and 'population' in norm(c)
                  and ('5' in norm(c) or 'five' in norm(c))]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(f'Could not uniquely identify Under-5 population column: {candidates}')


def get_feature_cols(df, h):
    excluded = {'Year', 'Month', 'Month_Name', DISTRICT, DATE, ORIGIN,
                TARGET_DATE, TARGET, 'Horizon_Months', 'Forecast_Horizon',
                'Forecast_Horizon_Months', MODEL_TARGET}
    cols = [c for c in df.columns if c not in excluded
            and pd.api.types.is_numeric_dtype(df[c])]
    if len(cols) != EXPECTED_FEATURES:
        raise ValueError(f'H{h}: expected {EXPECTED_FEATURES} engineered features, found {len(cols)}')
    return cols


def pct_change(cur, prev):
    if pd.isna(cur) or pd.isna(prev):
        return np.nan
    return (float(cur) - float(prev)) / max(abs(float(prev)), 1.0) * 100.0


def find_prediction_col(df):
    for c in ['RF_Predicted_Cases', 'Prediction', 'Predicted_Cases', 'Point_Forecast']:
        if c in df.columns:
            return c
    candidates = [c for c in df.columns if 'predict' in norm(c) and 'case' in norm(c)]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(f'Could not identify future RF prediction column. Candidates={candidates}')


def assert_groups_25(df, label):
    counts = df.groupby([TARGET_DATE, 'Horizon_Months'])[DISTRICT].nunique()
    if counts.empty or not (counts == EXPECTED_DISTRICTS).all():
        raise ValueError(f'{label}: every target-month/horizon group must contain 25 districts')


head('STEP 29C - DMBI BURDEN-CRITERIA PREPARATION')
print('Final criteria:')
print('1. Forecasted Malnutrition Cases')
print('2. Forecasted Cases per 1,000 Under-5 Population')
print('3. Forecasted Year-on-Year Burden Growth (%)')
print('\nNo Triposha / programme / climate / income / morbidity variable is a direct DMBI criterion.')
print('CRITIC and TOPSIS are NOT run in this step.')

for p in [BASE_PATH, STEP21_PATH, STEP27_PATH, STEP27_PREDICTOR_PATH, *FEATURE_PATHS.values()]:
    if not p.exists():
        raise FileNotFoundError(f'Required file not found: {p}')

# ============================================================
# BASE DATA
# ============================================================
head('LOAD BASE DATA')
base = pd.read_csv(BASE_PATH)
base.columns = [str(c).strip() for c in base.columns]
for c in [DISTRICT, DATE, TARGET]:
    if c not in base.columns:
        raise ValueError(f'Base data missing required column: {c}')
base[DATE] = pd.to_datetime(base[DATE], errors='coerce')
base[TARGET] = pd.to_numeric(base[TARGET], errors='coerce')
if base[DATE].isna().any():
    raise ValueError('Invalid dates in base data')
under5_col = find_under5(base)
base[under5_col] = pd.to_numeric(base[under5_col], errors='coerce')
base = base.sort_values([DISTRICT, DATE]).reset_index(drop=True)
districts = sorted(base[DISTRICT].astype(str).dropna().unique().tolist())
if len(districts) != 25:
    raise ValueError(f'Expected 25 districts, found {len(districts)}')
print(f'Observed period           : {base[DATE].min().date()} to {base[DATE].max().date()}')
print(f'Districts                 : {len(districts)} [PASS]')
print(f'Under-5 population column : {under5_col}')

actual_lookup = dict(zip(zip(base[DISTRICT].astype(str), base[DATE]), base[TARGET]))
pop_lookup = dict(zip(zip(base[DISTRICT].astype(str), base[DATE]), base[under5_col]))

# ============================================================
# STRICT 2024 FINAL RF PREDICTIONS
# ============================================================
head('REBUILD STRICT 2024 FINAL RANDOM FOREST PREDICTIONS')
pred_records = []
audit_origins = []

for h in HORIZONS:
    cfg = dict(RF_CONFIGS[h])
    cfg_id = cfg.pop('Config_ID')
    subhead(f'H{h} - {cfg_id}')
    df = pd.read_csv(FEATURE_PATHS[h])
    df.columns = [str(c).strip() for c in df.columns]
    for c in [DISTRICT, ORIGIN, TARGET_DATE, MODEL_TARGET]:
        if c not in df.columns:
            raise ValueError(f'H{h}: feature file missing {c}')
    df[ORIGIN] = pd.to_datetime(df[ORIGIN], errors='coerce')
    df[TARGET_DATE] = pd.to_datetime(df[TARGET_DATE], errors='coerce')
    df[MODEL_TARGET] = pd.to_numeric(df[MODEL_TARGET], errors='coerce')
    features = get_feature_cols(df, h)

    val = df[df[TARGET_DATE].between(pd.Timestamp('2024-01-01'), pd.Timestamp('2024-12-01'))
             & df[MODEL_TARGET].notna()].copy()
    if len(val) != 300:
        raise ValueError(f'H{h}: expected 300 2024 rows, found {len(val)}')
    origins = sorted(pd.to_datetime(val[ORIGIN].unique()).tolist())
    if len(origins) != 12:
        raise ValueError(f'H{h}: expected 12 origins, found {len(origins)}')

    for i, origin in enumerate(origins, 1):
        origin = pd.Timestamp(origin)
        pred_rows = val[val[ORIGIN] == origin].copy()
        train = df[df[MODEL_TARGET].notna() & (df[TARGET_DATE] <= origin)].copy()
        if len(pred_rows) != 25:
            raise ValueError(f'H{h} {origin.date()}: expected 25 prediction rows')
        if train.empty:
            raise ValueError(f'H{h} {origin.date()}: empty training pool')
        latest_target = train[TARGET_DATE].max()
        if latest_target > origin:
            raise ValueError(f'H{h} {origin.date()}: future-label leakage')

        med = train[features].median(numeric_only=True).fillna(0.0)
        xtr_num = train[features].copy().fillna(med).astype(float).reset_index(drop=True)
        xpr_num = pred_rows[features].copy().fillna(med).astype(float).reset_index(drop=True)

        cats = sorted(train[DISTRICT].astype(str).dropna().unique().tolist())
        if cats != districts:
            raise ValueError(f'H{h} {origin.date()}: district categories mismatch')
        tr_cat = pd.Categorical(train[DISTRICT].astype(str), categories=cats)
        pr_cat = pd.Categorical(pred_rows[DISTRICT].astype(str), categories=cats)
        xtr = pd.concat([xtr_num, pd.get_dummies(tr_cat, prefix='District', dtype=float).reset_index(drop=True)], axis=1)
        xpr = pd.concat([xpr_num, pd.get_dummies(pr_cat, prefix='District', dtype=float).reset_index(drop=True)], axis=1)
        xpr = xpr.reindex(columns=xtr.columns, fill_value=0.0)
        ytr = train[MODEL_TARGET].astype(float).to_numpy()

        model = RandomForestRegressor(**cfg)
        model.fit(xtr, ytr)
        preds = model.predict(xpr)

        audit_origins.append({
            'Horizon_Months': h,
            'Config_ID': cfg_id,
            ORIGIN: origin,
            'Training_Rows': len(train),
            'Prediction_Rows': len(pred_rows),
            'Latest_Training_Target_Date': latest_target,
            'Future_Label_Leakage': False,
        })

        for j, (_, row) in enumerate(pred_rows.iterrows()):
            district = str(row[DISTRICT])
            target_date = pd.Timestamp(row[TARGET_DATE])
            actual = actual_lookup.get((district, target_date), np.nan)
            if pd.isna(actual):
                actual = float(row[MODEL_TARGET])
            pred_records.append({
                'Model': 'Random Forest',
                'Horizon_Months': h,
                'Config_ID': cfg_id,
                DISTRICT: district,
                ORIGIN: origin,
                TARGET_DATE: target_date,
                'Actual_Target': float(actual),
                'Prediction': float(preds[j]),
            })
        print(f'Origin {i:02d}/12 {origin.date()} | train={len(train)} | predict={len(pred_rows)}')

pred2024 = pd.DataFrame(pred_records)
if len(pred2024) != 900:
    raise ValueError(f'Expected 900 2024 predictions, found {len(pred2024)}')
pred2024.to_csv(OUT_2024_RF, index=False)
print(f'2024 strict RF predictions: {len(pred2024)} [PASS]')

# ============================================================
# FROZEN 2025 STEP 21
# ============================================================
head('LOAD FROZEN 2025 STEP 21 PREDICTIONS')
pred2025 = pd.read_csv(STEP21_PATH)
pred2025.columns = [str(c).strip() for c in pred2025.columns]
required_21 = {'Horizon_Months', DISTRICT, ORIGIN, TARGET_DATE, 'Actual_Target', 'Prediction'}
missing = required_21 - set(pred2025.columns)
if missing:
    raise ValueError(f'Step 21 missing columns: {sorted(missing)}')
pred2025[ORIGIN] = pd.to_datetime(pred2025[ORIGIN], errors='coerce')
pred2025[TARGET_DATE] = pd.to_datetime(pred2025[TARGET_DATE], errors='coerce')
pred2025['Actual_Target'] = pd.to_numeric(pred2025['Actual_Target'], errors='coerce')
pred2025['Prediction'] = pd.to_numeric(pred2025['Prediction'], errors='coerce')
if pred2025[[ORIGIN, TARGET_DATE, 'Actual_Target', 'Prediction']].isna().any().any():
    raise ValueError('Step 21 contains invalid required values')
for h in HORIZONS:
    if int((pred2025['Horizon_Months'] == h).sum()) != 300:
        raise ValueError(f'H{h}: Step 21 must contain 300 rows')
print(f'Step 21 rows: {len(pred2025)} [PASS]')
print('2025 predictions are reused exactly; no retraining or tuning is done.')

# ============================================================
# FUTURE STEP 27
# ============================================================
head('LOAD FROZEN STEP 27 FUTURE FORECASTS')
future = pd.read_csv(STEP27_PATH)
future.columns = [str(c).strip() for c in future.columns]
for c in ['Horizon_Months', DISTRICT, ORIGIN, TARGET_DATE]:
    if c not in future.columns:
        raise ValueError(f'Step 27 missing column: {c}')
future_pred_col = find_prediction_col(future)
future[ORIGIN] = pd.to_datetime(future[ORIGIN], errors='coerce')
future[TARGET_DATE] = pd.to_datetime(future[TARGET_DATE], errors='coerce')
future[future_pred_col] = pd.to_numeric(future[future_pred_col], errors='coerce')
if future[[ORIGIN, TARGET_DATE, future_pred_col]].isna().any().any():
    raise ValueError('Step 27 contains invalid required values')
if len(future) != EXPECTED_FUTURE_TOTAL:
    raise ValueError(f'Expected {EXPECTED_FUTURE_TOTAL} future rows, found {len(future)}')
for h, expected in EXPECTED_FUTURE_ROWS.items():
    if int((future['Horizon_Months'] == h).sum()) != expected:
        raise ValueError(f'H{h}: expected {expected} future rows')
print(f'Future rows     : {len(future)} [PASS]')
print(f'RF point column: {future_pred_col}')

future_predictors = pd.read_csv(STEP27_PREDICTOR_PATH)
future_predictors.columns = [str(c).strip() for c in future_predictors.columns]
if DISTRICT not in future_predictors.columns or DATE not in future_predictors.columns:
    raise ValueError('Step 27 predictor projection must contain District and Date')
future_predictors[DATE] = pd.to_datetime(future_predictors[DATE], errors='coerce')
future_u5_col = find_under5(future_predictors)
future_predictors[future_u5_col] = pd.to_numeric(future_predictors[future_u5_col], errors='coerce')
if future_predictors[[DATE, future_u5_col]].isna().any().any():
    raise ValueError('Step 27 future predictor projection contains invalid Date/U5 values')
future_pop_lookup = dict(zip(zip(future_predictors[DISTRICT].astype(str), future_predictors[DATE]),
                             future_predictors[future_u5_col]))
print(f'Future U5 column: {future_u5_col}')

h1_future = future[future['Horizon_Months'] == 1].copy()
h1_lookup = dict(zip(zip(h1_future[DISTRICT].astype(str), h1_future[TARGET_DATE]),
                     h1_future[future_pred_col]))
print(f'H1 future burden reference rows: {len(h1_future)} [PASS]')

# ============================================================
# CRITERIA LOOKUPS
# ============================================================
def planning_u5(district, origin_date):
    district = str(district)
    origin_date = pd.Timestamp(origin_date)
    if origin_date <= pd.Timestamp('2025-12-01'):
        return pop_lookup.get((district, origin_date), np.nan)
    return future_pop_lookup.get((district, origin_date), np.nan)


def actual_u5(district, target_date):
    return pop_lookup.get((str(district), pd.Timestamp(target_date)), np.nan)


def previous_year_reference(district, target_date):
    district = str(district)
    prev_date = pd.Timestamp(target_date) - pd.DateOffset(months=12)
    if prev_date <= pd.Timestamp('2025-12-01'):
        return actual_lookup.get((district, prev_date), np.nan), 'Historical actual'
    return h1_lookup.get((district, prev_date), np.nan), 'Step 27 H1 RF future burden state'


def actual_previous_year(district, target_date):
    prev_date = pd.Timestamp(target_date) - pd.DateOffset(months=12)
    return actual_lookup.get((str(district), prev_date), np.nan)


def build_historical_criteria(pred_df, label):
    rows = []
    for _, r in pred_df.iterrows():
        d = str(r[DISTRICT])
        origin = pd.Timestamp(r[ORIGIN])
        target_date = pd.Timestamp(r[TARGET_DATE])
        h = int(r['Horizon_Months'])
        pred = float(r['Prediction'])
        actual = float(r['Actual_Target'])
        u5_origin = planning_u5(d, origin)
        u5_target = actual_u5(d, target_date)
        prev_pred_ref, prev_source = previous_year_reference(d, target_date)
        prev_actual = actual_previous_year(d, target_date)
        pred_rate = pred / float(u5_origin) * 1000.0 if pd.notna(u5_origin) and float(u5_origin) > 0 else np.nan
        actual_rate = actual / float(u5_target) * 1000.0 if pd.notna(u5_target) and float(u5_target) > 0 else np.nan
        rows.append({
            'Criteria_Period': label,
            DISTRICT: d,
            'Horizon_Months': h,
            ORIGIN: origin,
            TARGET_DATE: target_date,
            'C1_Forecasted_Malnutrition_Cases': pred,
            'C2_Forecasted_Cases_per_1000_U5': pred_rate,
            'C3_Forecasted_YoY_Burden_Growth_Percent': pct_change(pred, prev_pred_ref),
            'Planning_U5_Population_At_Origin': u5_origin,
            'Previous_Year_Burden_Reference': prev_pred_ref,
            'Previous_Year_Burden_Source': prev_source,
            'Actual_Malnutrition_Cases': actual,
            'Actual_Cases_per_1000_U5': actual_rate,
            'Actual_YoY_Burden_Growth_Percent': pct_change(actual, prev_actual),
            'Actual_U5_Population_At_Target': u5_target,
            'Actual_Previous_Year_Burden': prev_actual,
        })
    out = pd.DataFrame(rows)
    needed = ['C1_Forecasted_Malnutrition_Cases', 'C2_Forecasted_Cases_per_1000_U5',
              'C3_Forecasted_YoY_Burden_Growth_Percent', 'Planning_U5_Population_At_Origin',
              'Previous_Year_Burden_Reference', 'Actual_Malnutrition_Cases',
              'Actual_Cases_per_1000_U5', 'Actual_YoY_Burden_Growth_Percent']
    if out[needed].isna().any().any():
        raise ValueError(f'{label}: missing DMBI criteria inputs:\n{out[needed].isna().sum()}')
    assert_groups_25(out, label)
    return out

# ============================================================
# 2024 + 2025 CRITERIA
# ============================================================
head('PREPARE 2024 DEVELOPMENT CRITERIA')
criteria_2024 = build_historical_criteria(pred2024, '2024_DEVELOPMENT')
criteria_2024.to_csv(OUT_2024, index=False)
print(f'2024 criteria rows: {len(criteria_2024)} [PASS]')

head('PREPARE 2025 RETROSPECTIVE VALIDATION CRITERIA')
criteria_2025 = build_historical_criteria(pred2025, '2025_RETROSPECTIVE_VALIDATION')
criteria_2025.to_csv(OUT_2025, index=False)
print(f'2025 criteria rows: {len(criteria_2025)} [PASS]')

# ============================================================
# FUTURE CRITERIA
# ============================================================
head('PREPARE 2026-2030 FUTURE CRITERIA')
future_rows = []
for _, r in future.iterrows():
    d = str(r[DISTRICT])
    origin = pd.Timestamp(r[ORIGIN])
    target_date = pd.Timestamp(r[TARGET_DATE])
    h = int(r['Horizon_Months'])
    pred = float(r[future_pred_col])
    u5_origin = planning_u5(d, origin)
    prev_ref, prev_source = previous_year_reference(d, target_date)
    pred_rate = pred / float(u5_origin) * 1000.0 if pd.notna(u5_origin) and float(u5_origin) > 0 else np.nan
    future_rows.append({
        'Criteria_Period': '2026_2030_FUTURE',
        DISTRICT: d,
        'Horizon_Months': h,
        ORIGIN: origin,
        TARGET_DATE: target_date,
        'C1_Forecasted_Malnutrition_Cases': pred,
        'C2_Forecasted_Cases_per_1000_U5': pred_rate,
        'C3_Forecasted_YoY_Burden_Growth_Percent': pct_change(pred, prev_ref),
        'Planning_U5_Population_At_Origin': u5_origin,
        'Previous_Year_Burden_Reference': prev_ref,
        'Previous_Year_Burden_Source': prev_source,
    })
criteria_future = pd.DataFrame(future_rows)
needed_future = ['C1_Forecasted_Malnutrition_Cases', 'C2_Forecasted_Cases_per_1000_U5',
                 'C3_Forecasted_YoY_Burden_Growth_Percent', 'Planning_U5_Population_At_Origin',
                 'Previous_Year_Burden_Reference']
if criteria_future[needed_future].isna().any().any():
    raise ValueError(f'Future criteria missing required values:\n{criteria_future[needed_future].isna().sum()}')
if len(criteria_future) != EXPECTED_FUTURE_TOTAL:
    raise ValueError(f'Expected {EXPECTED_FUTURE_TOTAL} future criteria rows, found {len(criteria_future)}')
assert_groups_25(criteria_future, '2026-2030 future')
criteria_future.to_csv(OUT_FUTURE, index=False)
print(f'Future criteria rows: {len(criteria_future)} [PASS]')

# ============================================================
# SUMMARY
# ============================================================
summary_rows = []
for period, df in [('2024_DEVELOPMENT', criteria_2024),
                   ('2025_RETROSPECTIVE_VALIDATION', criteria_2025),
                   ('2026_2030_FUTURE', criteria_future)]:
    for h in HORIZONS:
        s = df[df['Horizon_Months'] == h]
        summary_rows.append({
            'Period': period,
            'Horizon_Months': h,
            'Rows': len(s),
            'Districts': s[DISTRICT].nunique(),
            'Target_Start': s[TARGET_DATE].min(),
            'Target_End': s[TARGET_DATE].max(),
            'Mean_C1_Forecasted_Cases': s['C1_Forecasted_Malnutrition_Cases'].mean(),
            'Mean_C2_Cases_per_1000_U5': s['C2_Forecasted_Cases_per_1000_U5'].mean(),
            'Mean_C3_YoY_Growth_Percent': s['C3_Forecasted_YoY_Burden_Growth_Percent'].mean(),
        })
summary = pd.DataFrame(summary_rows)
summary.to_csv(OUT_SUMMARY, index=False)

# ============================================================
# HARD AUDIT
# ============================================================
head('STEP 29C HARD AUDIT')
origin_audit = pd.DataFrame(audit_origins)
criteria_cols = ['C1_Forecasted_Malnutrition_Cases',
                 'C2_Forecasted_Cases_per_1000_U5',
                 'C3_Forecasted_YoY_Burden_Growth_Percent']
forbidden_in_criteria = any(any(k in norm(c) for k in ['triposha', 'morbidity', 'income', 'rain', 'temperature'])
                            for c in criteria_cols)
checks = [
    ('2024 strict RF prediction rows', len(pred2024), 900, len(pred2024) == 900),
    ('2024 future-label leakage', bool(origin_audit['Future_Label_Leakage'].any()), False,
     not bool(origin_audit['Future_Label_Leakage'].any())),
    ('2025 frozen Step 21 rows', len(pred2025), 900, len(pred2025) == 900),
    ('2026-2030 frozen Step 27 rows', len(criteria_future), EXPECTED_FUTURE_TOTAL,
     len(criteria_future) == EXPECTED_FUTURE_TOTAL),
    ('Final DMBI criterion count', len(criteria_cols), 3, len(criteria_cols) == 3),
    ('Triposha/driver variables in direct DMBI criteria', forbidden_in_criteria, False, not forbidden_in_criteria),
    ('2024 criteria missing values', int(criteria_2024[criteria_cols].isna().sum().sum()), 0,
     int(criteria_2024[criteria_cols].isna().sum().sum()) == 0),
    ('2025 criteria missing values', int(criteria_2025[criteria_cols].isna().sum().sum()), 0,
     int(criteria_2025[criteria_cols].isna().sum().sum()) == 0),
    ('Future criteria missing values', int(criteria_future[criteria_cols].isna().sum().sum()), 0,
     int(criteria_future[criteria_cols].isna().sum().sum()) == 0),
    ('CRITIC executed in Step 29C', False, False, True),
    ('TOPSIS executed in Step 29C', False, False, True),
]
audit = pd.DataFrame([{'Audit_Check': a, 'Result': b, 'Expected': c, 'Status': 'PASS' if ok else 'FAIL'}
                      for a, b, c, ok in checks])
audit.to_csv(OUT_AUDIT, index=False)
for _, r in audit.iterrows():
    print(f"{r['Audit_Check']:<58}: {r['Status']}")
if (audit['Status'] != 'PASS').any():
    raise ValueError('Step 29C hard audit failed; inspect 29c_dmbi_criteria_audit.csv')

# ============================================================
# METHODOLOGY RECORD
# ============================================================
methodology = {
    'step': '29C',
    'name': 'DMBI Burden-Criteria Preparation',
    'interpretation': 'Relative district planning-priority index; not a clinical diagnosis or probability.',
    'criteria': {
        'C1_Forecasted_Malnutrition_Cases': 'Absolute predicted district malnutrition burden.',
        'C2_Forecasted_Cases_per_1000_U5': 'Forecasted cases divided by Under-5 population available at forecast origin, multiplied by 1000.',
        'C3_Forecasted_YoY_Burden_Growth_Percent': 'Forecasted burden compared with the same target month one year earlier.',
    },
    'criteria_direction': 'Higher value means higher planning priority for all three criteria.',
    'excluded_from_direct_dmbi_criteria': [
        'Triposha/resource/intervention outputs',
        'Programme/clinic variables',
        'Climate variables',
        'Socioeconomic variables',
        'Maternal-health variables',
        'Other forecasting predictors',
    ],
    'excluded_predictor_role': 'They remain forecasting and SHAP explanation inputs.',
    '2024_rule': 'Strict rolling-origin RF predictions rebuilt with frozen final RF configurations; used for DMBI method development.',
    '2025_rule': 'Frozen Step 21 predictions reused; 2025 reserved for retrospective DMBI validation and must not tune DMBI weights.',
    'future_rule': 'Frozen Step 27 RF forecasts reused for 2026-2030 planning.',
    'predicted_rate_population_rule': 'Under-5 population at forecast origin; observed for historical origins and Step 27 projected for future origins.',
    'growth_reference_rule': 'Same target month one year earlier; historical actual through 2025, then Step 27 H1 RF future burden state.',
    'critic_run_here': False,
    'topsis_run_here': False,
    'next_step': '29d_dmbi_critic_weight_development.py using 2024 development criteria only.',
}
with open(OUT_METHOD, 'w', encoding='utf-8') as f:
    json.dump(methodology, f, indent=2, default=str)

# ============================================================
# COMPLETE
# ============================================================
head('STEP 29C COMPLETE')
print('\nFINAL DMBI CRITERIA:')
print('1. Forecasted Malnutrition Cases')
print('2. Forecasted Cases per 1,000 Under-5 Population')
print('3. Forecasted Year-on-Year Burden Growth (%)')
print('\nPrepared datasets:')
print(f'- 2024 development criteria : {len(criteria_2024)} rows')
print(f'- 2025 validation criteria  : {len(criteria_2025)} rows')
print(f'- 2026-2030 future criteria : {len(criteria_future)} rows')
print('\nSaved:')
print(f'- 2024 strict RF predictions : {OUT_2024_RF}')
print(f'- 2024 criteria              : {OUT_2024}')
print(f'- 2025 criteria              : {OUT_2025}')
print(f'- Future criteria            : {OUT_FUTURE}')
print(f'- Summary                    : {OUT_SUMMARY}')
print(f'- Audit                      : {OUT_AUDIT}')
print(f'- Methodology                : {OUT_METHOD}')
print('\nNEXT: Send the FULL terminal output before Step 29D CRITIC.')
print('\nSTEP 29C - DMBI BURDEN-CRITERIA PREPARATION COMPLETE')
print('=' * 120)
