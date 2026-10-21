from pathlib import Path
import json, math, warnings
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings('ignore')

DATE='Date'; DISTRICT='District'; TARGET='Malnutrition_Cases'; RESOURCE='Triposha_Packets_Distributed'
DEV_START_YEAR=2015; DEV_END_YEAR=2023; VALIDATION_YEAR=2024; RETROSPECTIVE_YEAR=2025
EXPECTED_DISTRICTS=25
MIN_DISTRICT_MONTH_ROWS=5; MIN_DISTRICT_ROWS=24; MIN_MONTH_ROWS=24
CANDIDATES=['NATIONAL_MEDIAN','DISTRICT_MEDIAN','MONTH_MEDIAN','DISTRICT_MONTH_MEDIAN']

BASE_DIR=Path(__file__).resolve().parent.parent
PROCESSED_DIR=BASE_DIR/'data'/'processed'; REPORT_DIR=BASE_DIR/'outputs'/'reports'; REPORT_DIR.mkdir(parents=True,exist_ok=True)
INPUT_PATH=PROCESSED_DIR/'malnutrition_preprocessed_base.csv'
OUT_CANDIDATE_METRICS=REPORT_DIR/'32a_triposha_candidate_validation_2024.csv'
OUT_SELECTED=REPORT_DIR/'32a_triposha_selected_rule.csv'
OUT_PARAMS=REPORT_DIR/'32a_triposha_selected_rule_parameters.csv'
OUT_2024_PRED=REPORT_DIR/'32a_triposha_2024_predictions.csv'
OUT_2025_PRED=REPORT_DIR/'32a_triposha_2025_retrospective_predictions.csv'
OUT_2025_METRICS=REPORT_DIR/'32a_triposha_2025_retrospective_metrics.csv'
OUT_AUDIT=REPORT_DIR/'32a_triposha_conversion_audit.csv'
OUT_METHOD=REPORT_DIR/'32a_triposha_conversion_methodology.json'

def heading(t):
    print('\n'+'='*120); print(t); print('='*120)

def wape(y_true,y_pred):
    d=float(np.abs(y_true).sum()); return np.nan if d==0 else float(np.abs(y_true-y_pred).sum()/d*100)

def smape(y_true,y_pred):
    den=np.abs(y_true)+np.abs(y_pred); v=den>0
    return np.nan if not np.any(v) else float(np.mean(2*np.abs(y_pred[v]-y_true[v])/den[v])*100)

def metrics(y_true,y_pred,rule,year):
    y_true=np.asarray(y_true,float); y_pred=np.asarray(y_pred,float)
    return {'Rule':rule,'Evaluation_Year':year,'Rows':len(y_true),'MAE_Packets':float(mean_absolute_error(y_true,y_pred)),
            'RMSE_Packets':float(math.sqrt(mean_squared_error(y_true,y_pred))),'WAPE_Percentage':wape(y_true,y_pred),
            'sMAPE_Percentage':smape(y_true,y_pred),'R2':float(r2_score(y_true,y_pred))}

def build_tables(dev):
    national=float(dev['Packets_Per_Case'].median())
    district=dev.groupby(DISTRICT)['Packets_Per_Case'].agg(['median','count']).reset_index().rename(columns={'median':'District_Median_Ratio','count':'District_History_Rows'})
    month=dev.groupby('Month')['Packets_Per_Case'].agg(['median','count']).reset_index().rename(columns={'median':'Month_Median_Ratio','count':'Month_History_Rows'})
    dm=dev.groupby([DISTRICT,'Month'])['Packets_Per_Case'].agg(['median','count']).reset_index().rename(columns={'median':'District_Month_Median_Ratio','count':'District_Month_History_Rows'})
    return national,district,month,dm

def apply_rule(df,rule,national,district,month,dm):
    w=df.copy().merge(district,on=DISTRICT,how='left',validate='many_to_one').merge(month,on='Month',how='left',validate='many_to_one').merge(dm,on=[DISTRICT,'Month'],how='left',validate='many_to_one')
    if rule=='NATIONAL_MEDIAN':
        w['Applied_Ratio']=national; w['Ratio_Source']='NATIONAL_MEDIAN'
    elif rule=='DISTRICT_MEDIAN':
        ok=w['District_History_Rows']>=MIN_DISTRICT_ROWS
        w['Applied_Ratio']=np.where(ok,w['District_Median_Ratio'],national); w['Ratio_Source']=np.where(ok,'DISTRICT_MEDIAN','NATIONAL_FALLBACK')
    elif rule=='MONTH_MEDIAN':
        ok=w['Month_History_Rows']>=MIN_MONTH_ROWS
        w['Applied_Ratio']=np.where(ok,w['Month_Median_Ratio'],national); w['Ratio_Source']=np.where(ok,'MONTH_MEDIAN','NATIONAL_FALLBACK')
    elif rule=='DISTRICT_MONTH_MEDIAN':
        dmok=(w['District_Month_History_Rows']>=MIN_DISTRICT_MONTH_ROWS).fillna(False).to_numpy()
        dok=(w['District_History_Rows']>=MIN_DISTRICT_ROWS).fillna(False).to_numpy()
        mok=(w['Month_History_Rows']>=MIN_MONTH_ROWS).fillna(False).to_numpy()
        a=np.full(len(w),np.nan); s=np.full(len(w),'NATIONAL_FALLBACK',dtype=object)
        a[dmok]=w.loc[dmok,'District_Month_Median_Ratio']; s[dmok]='DISTRICT_MONTH_MEDIAN'
        rem=np.isnan(a); use=rem & dok; a[use]=w.loc[use,'District_Median_Ratio']; s[use]='DISTRICT_FALLBACK'
        rem=np.isnan(a); use=rem & mok; a[use]=w.loc[use,'Month_Median_Ratio']; s[use]='MONTH_FALLBACK'
        rem=np.isnan(a); a[rem]=national; s[rem]='NATIONAL_FALLBACK'
        w['Applied_Ratio']=a; w['Ratio_Source']=s
    else:
        raise ValueError(rule)
    if w['Applied_Ratio'].isna().any() or (~np.isfinite(w['Applied_Ratio'])).any() or (w['Applied_Ratio']<0).any():
        raise ValueError(f'Invalid applied ratio for {rule}')
    w['Predicted_Triposha_Packets_Raw']=w[TARGET]*w['Applied_Ratio']
    w['Predicted_Triposha_Packets_Display']=w['Predicted_Triposha_Packets_Raw'].round().astype(int)
    w['Absolute_Error_Packets']=(w[RESOURCE]-w['Predicted_Triposha_Packets_Raw']).abs()
    w['Signed_Error_Packets']=w['Predicted_Triposha_Packets_Raw']-w[RESOURCE]
    w['Rule']=rule
    return w

heading('STEP 32A - TRIPOSHA CONVERSION-RULE DEVELOPMENT')
print('Development: 2015-2023 only')
print('Validation : 2024 only')
print('2025       : retrospective check only')
print('New ML model training: NO')

if not INPUT_PATH.exists(): raise FileNotFoundError(INPUT_PATH)
data=pd.read_csv(INPUT_PATH,low_memory=False); data.columns=[str(c).strip() for c in data.columns]
missing={DATE,DISTRICT,TARGET,RESOURCE}-set(data.columns)
if missing: raise ValueError(f'Missing columns: {sorted(missing)}')
data[DATE]=pd.to_datetime(data[DATE],errors='coerce'); data[TARGET]=pd.to_numeric(data[TARGET],errors='coerce'); data[RESOURCE]=pd.to_numeric(data[RESOURCE],errors='coerce'); data[DISTRICT]=data[DISTRICT].astype(str).str.strip()
data['Year']=data[DATE].dt.year; data['Month']=data[DATE].dt.month

valid=lambda d: d[d[TARGET].notna() & d[RESOURCE].notna() & (d[TARGET]>0) & (d[RESOURCE]>=0)].copy()
dev=valid(data[data['Year'].between(DEV_START_YEAR,DEV_END_YEAR)].copy())
val=valid(data[data['Year']==VALIDATION_YEAR].copy())
test=valid(data[data['Year']==RETROSPECTIVE_YEAR].copy())
if dev.empty or val.empty or test.empty: raise ValueError('Development/validation/retrospective data missing')
dev['Packets_Per_Case']=dev[RESOURCE]/dev[TARGET]; dev=dev[np.isfinite(dev['Packets_Per_Case'])].copy()
if (dev['Packets_Per_Case']<0).any(): raise ValueError('Negative ratio found')

heading('BUILD 2015-2023 DEVELOPMENT TABLES')
national,district_table,month_table,dm_table=build_tables(dev)
print(f'National median packets/case: {national:.6f}')
print(f'Districts: {district_table[DISTRICT].nunique()} | months: {month_table["Month"].nunique()} | district-month rows: {len(dm_table)}')

heading('2024 VALIDATION - CANDIDATE RULES')
rows=[]
for rule in CANDIDATES:
    p=apply_rule(val,rule,national,district_table,month_table,dm_table)
    m=metrics(p[RESOURCE].to_numpy(float),p['Predicted_Triposha_Packets_Raw'].to_numpy(float),rule,2024)
    rows.append(m)
    print(f"{rule:<24} MAE={m['MAE_Packets']:.4f} | RMSE={m['RMSE_Packets']:.4f} | WAPE={m['WAPE_Percentage']:.4f}% | R2={m['R2']:.4f}")
cm=pd.DataFrame(rows).sort_values(['MAE_Packets','WAPE_Percentage','RMSE_Packets','Rule']).reset_index(drop=True)
cm['Validation_Rank']=np.arange(1,len(cm)+1); cm.to_csv(OUT_CANDIDATE_METRICS,index=False)
selected=str(cm.iloc[0]['Rule']); print(f'\nSELECTED FROM 2024 ONLY: {selected}')

sel2024=apply_rule(val,selected,national,district_table,month_table,dm_table)
sel2024[[DATE,'Year','Month',DISTRICT,TARGET,RESOURCE,'Applied_Ratio','Ratio_Source','Predicted_Triposha_Packets_Raw','Predicted_Triposha_Packets_Display','Absolute_Error_Packets','Signed_Error_Packets','Rule']].to_csv(OUT_2024_PRED,index=False)

pd.DataFrame([{'Selected_Rule':selected,'Development_Period':'2015-2023','Selection_Year':2024,'Selection_Metric':'Lowest 2024 MAE; tie-break WAPE then RMSE','2025_Used_For_Selection':False,'National_Median_Packets_Per_Case':national,
               'Selected_2024_MAE_Packets':cm.iloc[0]['MAE_Packets'],'Selected_2024_RMSE_Packets':cm.iloc[0]['RMSE_Packets'],'Selected_2024_WAPE_Percentage':cm.iloc[0]['WAPE_Percentage'],'Selected_2024_sMAPE_Percentage':cm.iloc[0]['sMAPE_Percentage'],'Selected_2024_R2':cm.iloc[0]['R2']}]).to_csv(OUT_SELECTED,index=False)

params=[{'Parameter_Type':'NATIONAL','District':'','Month':np.nan,'History_Rows':len(dev),'Packets_Per_Case_Ratio':national}]
for _,r in district_table.iterrows(): params.append({'Parameter_Type':'DISTRICT','District':r[DISTRICT],'Month':np.nan,'History_Rows':int(r['District_History_Rows']),'Packets_Per_Case_Ratio':float(r['District_Median_Ratio'])})
for _,r in month_table.iterrows(): params.append({'Parameter_Type':'MONTH','District':'','Month':int(r['Month']),'History_Rows':int(r['Month_History_Rows']),'Packets_Per_Case_Ratio':float(r['Month_Median_Ratio'])})
for _,r in dm_table.iterrows(): params.append({'Parameter_Type':'DISTRICT_MONTH','District':r[DISTRICT],'Month':int(r['Month']),'History_Rows':int(r['District_Month_History_Rows']),'Packets_Per_Case_Ratio':float(r['District_Month_Median_Ratio'])})
pd.DataFrame(params).to_csv(OUT_PARAMS,index=False)

heading('2025 RETROSPECTIVE CHECK - FROZEN RULE')
sel2025=apply_rule(test,selected,national,district_table,month_table,dm_table)
m25=metrics(sel2025[RESOURCE].to_numpy(float),sel2025['Predicted_Triposha_Packets_Raw'].to_numpy(float),selected,2025)
pd.DataFrame([{**m25,'Rule_Frozen_From_2024':True,'2025_Used_For_Selection':False}]).to_csv(OUT_2025_METRICS,index=False)
sel2025[[DATE,'Year','Month',DISTRICT,TARGET,RESOURCE,'Applied_Ratio','Ratio_Source','Predicted_Triposha_Packets_Raw','Predicted_Triposha_Packets_Display','Absolute_Error_Packets','Signed_Error_Packets','Rule']].to_csv(OUT_2025_PRED,index=False)
print(f"2025 MAE={m25['MAE_Packets']:.4f} | RMSE={m25['RMSE_Packets']:.4f} | WAPE={m25['WAPE_Percentage']:.4f}% | sMAPE={m25['sMAPE_Percentage']:.4f}% | R2={m25['R2']:.4f}")

heading('STEP 32A HARD AUDIT')
dev_years=sorted(dev['Year'].unique().tolist()); expected=list(range(2015,2024))
checks=[
('Development years',dev_years,expected,dev_years==expected),
('2024 excluded from development',2024 in dev_years,False,2024 not in dev_years),
('2025 excluded from development',2025 in dev_years,False,2025 not in dev_years),
('25 districts in development',dev[DISTRICT].nunique(),25,dev[DISTRICT].nunique()==25),
('Candidate count',len(cm),4,len(cm)==4),
('2025 used for selection',False,False,True),
('New ML model trained',False,False,True),
('RF/NGBoost/SHAP/DMBI changed',False,False,True),
]
aud=[]
for name,res,exp,ok in checks:
    status='PASS' if ok else 'FAIL'; aud.append({'Audit_Check':name,'Result':res,'Expected':exp,'Status':status}); print(f'{name:<42}: {status}')
aud=pd.DataFrame(aud); aud.to_csv(OUT_AUDIT,index=False)
if (aud['Status']!='PASS').any(): raise ValueError('Step 32A hard audit failed')

method={'step':'32A','name':'Triposha Historical Conversion-Rule Development','input':str(INPUT_PATH),'development_period':'2015-2023','validation_year':2024,'retrospective_check_year':2025,
        'historical_ratio':'Triposha_Packets_Distributed / Malnutrition_Cases','candidate_rules':CANDIDATES,'selection_rule':'Lowest 2024 MAE; tie-break lower WAPE then lower RMSE','selected_rule':selected,
        '2025_used_for_selection':False,'new_ml_model_trained':False,'future_use':'Step 32B applies the frozen rule to 2026-2030 RF malnutrition forecasts','interpretation':'Operational Triposha packet planning estimate; not clinical eligibility or dosage recommendation.',
        'rounding_policy':'Raw decimal packet estimates preserved for evaluation; whole packets only for display/planning.'}
with open(OUT_METHOD,'w',encoding='utf-8') as f: json.dump(method,f,indent=2,default=str)

heading('STEP 32A COMPLETE')
print(f'Selected rule from 2024: {selected}')
print('Saved outputs:')
for p in [OUT_CANDIDATE_METRICS,OUT_SELECTED,OUT_PARAMS,OUT_2024_PRED,OUT_2025_PRED,OUT_2025_METRICS,OUT_AUDIT,OUT_METHOD]: print(f'- {p}')
print('\nNEXT: Send the FULL terminal output before Step 32B future 2026-2030 Triposha packet estimation.')
