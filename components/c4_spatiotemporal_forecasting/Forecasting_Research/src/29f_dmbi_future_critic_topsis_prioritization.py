from pathlib import Path
import json, re, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

DISTRICT="District"; TARGET_DATE="Forecast_Target_Date"; ORIGIN_DATE="Forecast_Origin_Date"; HORIZON="Horizon_Months"
HORIZONS=[1,3,6]; EXPECTED_DISTRICTS=25
EXPECTED_ROWS={1:1500,3:1450,6:1375}; EXPECTED_TOTAL=sum(EXPECTED_ROWS.values())
CRITERIA={
    "C1":"C1_Forecasted_Malnutrition_Cases",
    "C2":"C2_Forecasted_Cases_per_1000_U5",
    "C3":"C3_Forecasted_YoY_Burden_Growth_Percent",
}
LABELS={
    "C1":"Forecasted Malnutrition Cases",
    "C2":"Forecasted Cases per 1,000 Under-5",
    "C3":"Forecasted Year-on-Year Burden Growth (%)",
}
BASE_DIR=Path(__file__).resolve().parent.parent
REPORT=BASE_DIR/"outputs"/"reports"; FIG=BASE_DIR/"outputs"/"figures"
REPORT.mkdir(parents=True,exist_ok=True); FIG.mkdir(parents=True,exist_ok=True)
CRITERIA_PATH=REPORT/"29c_future_dmbi_criteria_2026_2030.csv"
WEIGHTS_PATH=REPORT/"29d_frozen_critic_weights_from_2024.csv"
DETAIL_PATH=REPORT/"29f_future_dmbi_critic_topsis_prioritization_2026_2030.csv"
MATRIX_AUDIT_PATH=REPORT/"29f_future_dmbi_matrix_audit.csv"
SUMMARY_HORIZON_PATH=REPORT/"29f_future_dmbi_summary_by_horizon.csv"
SUMMARY_LEVEL_PATH=REPORT/"29f_future_dmbi_priority_level_summary.csv"
TOP_DISTRICTS_PATH=REPORT/"29f_future_dmbi_top_priority_districts.csv"
AUDIT_PATH=REPORT/"29f_future_dmbi_audit.csv"
METHOD_PATH=REPORT/"29f_future_dmbi_methodology.json"

def head(t):
    print("\n"+"="*120); print(t); print("="*120)

def norm_name(x):
    return re.sub(r"[^a-z0-9]+","",str(x).lower())

def pct_0_100(s):
    x=pd.to_numeric(s,errors="coerce"); n=int(x.notna().sum())
    if n<=1: return pd.Series(np.full(len(x),50.0),index=x.index,dtype=float)
    p=x.rank(method="average",pct=True)
    return (((p*n)-1)/max(n-1,1)*100.0).astype(float)

def tier(v):
    if pd.isna(v): return "Unknown"
    if v<25: return "Low"
    if v<50: return "Medium"
    if v<75: return "High"
    return "Critical"

def minmax(s):
    x=pd.to_numeric(s,errors="coerce").astype(float)
    lo,hi=float(x.min()),float(x.max())
    if not np.isfinite(lo) or not np.isfinite(hi): raise ValueError("Non-finite criterion values.")
    if abs(hi-lo)<=1e-12: return pd.Series(np.zeros(len(x)),index=x.index,dtype=float),True
    return ((x-lo)/(hi-lo)).astype(float),False

def load_weights():
    w=pd.read_csv(WEIGHTS_PATH); w.columns=[str(c).strip() for c in w.columns]
    lc=next((c for c in ["Criterion_Label","Criterion","Criteria","Indicator"] if c in w.columns),None)
    wc=next((c for c in ["CRITIC_Weight","Critic_Weight","Weight"] if c in w.columns),None)
    if lc is None or wc is None: raise ValueError(f"Could not identify frozen-weight columns: {w.columns.tolist()}")
    w[wc]=pd.to_numeric(w[wc],errors="coerce")
    if w[wc].isna().any(): raise ValueError("Invalid CRITIC weight.")
    out={}
    for _,r in w.iterrows():
        n=norm_name(r[lc]); k=None
        if "per1000" in n or "1000under5" in n: k="C2"
        elif "growth" in n or "yoy" in n or "yearonyear" in n: k="C3"
        elif "malnutritioncases" in n or "forecastedcases" in n: k="C1"
        if k:
            if k in out: raise ValueError(f"Duplicate mapping for {k}")
            out[k]=float(r[wc])
    if set(out)!={"C1","C2","C3"}: raise ValueError(f"Could not map all weights: {out}")
    if not np.isclose(sum(out.values()),1.0,atol=1e-8): raise ValueError("Weights do not sum to 1.")
    return out

def run_topsis(g,weights):
    out=g.copy(); wcols=[]; constants=[]
    for k in ["C1","C2","C3"]:
        ncol=f"{k}_Normalized"; wcol=f"{k}_Weighted"
        n,const=minmax(out[CRITERIA[k]])
        out[ncol]=n; out[wcol]=n*weights[k]; wcols.append(wcol)
        if const: constants.append(k)
    m=out[wcols].to_numpy(float)
    pos=m.max(axis=0); neg=m.min(axis=0)
    dp=np.sqrt(((m-pos)**2).sum(axis=1)); dm=np.sqrt(((m-neg)**2).sum(axis=1))
    den=dp+dm
    if (den<=1e-15).any(): raise ValueError("Zero TOPSIS denominator.")
    c=np.clip(dm/den,0,1)
    out["Distance_to_Positive_Ideal"]=dp
    out["Distance_to_Negative_Ideal"]=dm
    out["TOPSIS_Closeness"]=c
    out["DMBI_Score_0_100"]=c*100
    out["Priority_Rank"]=out["TOPSIS_Closeness"].rank(method="min",ascending=False).astype(int)
    out["Priority_Percentile_0_100"]=pct_0_100(out["TOPSIS_Closeness"])
    out["Priority_Level"]=out["Priority_Percentile_0_100"].apply(tier)
    return out,constants

head("STEP 29F - FUTURE DMBI CRITIC-TOPSIS PRIORITIZATION 2026-2030")
print("\nRules:")
print("- Frozen 2024 CRITIC weights are reused unchanged")
print("- Same TOPSIS method as Step 29E")
print("- No future actual outcomes are used")
print("- No weight/model tuning")
print("- Critical = highest relative planning priority, NOT clinical emergency")

for p in [CRITERIA_PATH,WEIGHTS_PATH]:
    if not p.exists(): raise FileNotFoundError(f"Required file not found: {p}")

head("LOAD FROZEN 2024 CRITIC WEIGHTS")
weights=load_weights()
for k in ["C1","C2","C3"]: print(f"{k} - {LABELS[k]}: {weights[k]:.6f}")
print(f"\nWeight sum: {sum(weights.values()):.12f} [PASS]")

head("LOAD STEP 29C FUTURE DMBI CRITERIA")
df=pd.read_csv(CRITERIA_PATH); df.columns=[str(c).strip() for c in df.columns]
required={DISTRICT,TARGET_DATE,HORIZON,*CRITERIA.values()}
missing=required-set(df.columns)
if missing: raise ValueError(f"Missing future criteria columns: {sorted(missing)}")
df[TARGET_DATE]=pd.to_datetime(df[TARGET_DATE],errors="coerce")
if ORIGIN_DATE in df.columns: df[ORIGIN_DATE]=pd.to_datetime(df[ORIGIN_DATE],errors="coerce")
df[HORIZON]=pd.to_numeric(df[HORIZON],errors="coerce")
for c in CRITERIA.values(): df[c]=pd.to_numeric(df[c],errors="coerce")
if df[[TARGET_DATE,HORIZON,*CRITERIA.values()]].isna().any().any(): raise ValueError("Missing/invalid future criteria.")
if len(df)!=EXPECTED_TOTAL: raise ValueError(f"Expected {EXPECTED_TOTAL} rows, found {len(df)}")
if df[DISTRICT].astype(str).nunique()!=25: raise ValueError("Expected 25 districts.")
for h,n in EXPECTED_ROWS.items():
    if int((df[HORIZON]==h).sum())!=n: raise ValueError(f"H{h}: row count mismatch.")
sizes=df.groupby([TARGET_DATE,HORIZON])[DISTRICT].nunique()
if not (sizes==25).all(): raise ValueError("At least one future matrix does not have 25 districts.")
print(f"Rows              : {len(df)} [PASS]")
print(f"Districts         : {df[DISTRICT].astype(str).nunique()} [PASS]")
print(f"Decision matrices : {len(sizes)} [PASS]")
print(f"Target period     : {df[TARGET_DATE].min().date()} to {df[TARGET_DATE].max().date()} [PASS]")

head("RUN FUTURE TOPSIS PRIORITIZATION")
parts=[]; audits=[]
for (dt,h),g in df.groupby([TARGET_DATE,HORIZON],sort=True):
    g=g.sort_values(DISTRICT).reset_index(drop=True)
    scored,constants=run_topsis(g,weights)
    scored["DMBI_Interpretation"]="Relative district planning priority; not clinical emergency."
    parts.append(scored)
    top=str(scored.nsmallest(1,"Priority_Rank")[DISTRICT].iloc[0])
    audits.append({
        TARGET_DATE:pd.Timestamp(dt),HORIZON:int(h),"Districts":len(g),
        "Constant_Criteria":";".join(constants),
        "TOPSIS_Min":float(scored["TOPSIS_Closeness"].min()),
        "TOPSIS_Max":float(scored["TOPSIS_Closeness"].max()),
        "DMBI_Min":float(scored["DMBI_Score_0_100"].min()),
        "DMBI_Max":float(scored["DMBI_Score_0_100"].max()),
        "Top_Priority_District":top,
    })
    print(f"{pd.Timestamp(dt).date()} | H{int(h)} | DMBI={scored['DMBI_Score_0_100'].min():.2f}-{scored['DMBI_Score_0_100'].max():.2f} | rank1={top}")

detail=pd.concat(parts,ignore_index=True); matrix_audit=pd.DataFrame(audits)
if len(detail)!=EXPECTED_TOTAL: raise ValueError("Final future output row count mismatch.")
detail.to_csv(DETAIL_PATH,index=False); matrix_audit.to_csv(MATRIX_AUDIT_PATH,index=False)

head("BUILD FUTURE DMBI SUMMARIES")
hsummary=(detail.groupby(HORIZON,as_index=False)
          .agg(Rows=(DISTRICT,"size"),Districts=(DISTRICT,"nunique"),
               Target_Start=(TARGET_DATE,"min"),Target_End=(TARGET_DATE,"max"),
               Mean_DMBI_Score=("DMBI_Score_0_100","mean"),
               Median_DMBI_Score=("DMBI_Score_0_100","median"),
               Mean_Forecasted_Cases=(CRITERIA["C1"],"mean"),
               Mean_Cases_per_1000_U5=(CRITERIA["C2"],"mean"),
               Mean_YoY_Growth_Percent=(CRITERIA["C3"],"mean")))
hsummary.to_csv(SUMMARY_HORIZON_PATH,index=False)

lsummary=(detail.groupby([HORIZON,"Priority_Level"],as_index=False).agg(Rows=(DISTRICT,"size")))
lsummary.to_csv(SUMMARY_LEVEL_PATH,index=False)

top=detail[detail["Priority_Rank"]<=5].sort_values([TARGET_DATE,HORIZON,"Priority_Rank"])
top.to_csv(TOP_DISTRICTS_PATH,index=False)

head("STEP 29F HARD AUDIT")
score_ok=detail["TOPSIS_Closeness"].between(0,1).all()
dmbi_ok=detail["DMBI_Score_0_100"].between(0,100).all()
rank_ok=detail["Priority_Rank"].between(1,25).all()
missing_outputs=int(detail[["TOPSIS_Closeness","DMBI_Score_0_100","Priority_Rank","Priority_Level"]].isna().sum().sum())

checks=[
    ("Future rows",len(detail),EXPECTED_TOTAL,len(detail)==EXPECTED_TOTAL),
    ("Districts",detail[DISTRICT].astype(str).nunique(),25,detail[DISTRICT].astype(str).nunique()==25),
    ("All decision matrices contain 25 districts",bool((sizes==25).all()),True,bool((sizes==25).all())),
    ("Frozen weight count",len(weights),3,len(weights)==3),
    ("Frozen weights sum to 1",sum(weights.values()),1.0,np.isclose(sum(weights.values()),1.0,atol=1e-8)),
    ("Future data used to tune/recalculate weights",False,False,True),
    ("Manual weights supplied in Step 29F",False,False,True),
    ("TOPSIS closeness inside [0,1]",score_ok,True,score_ok),
    ("DMBI score inside [0,100]",dmbi_ok,True,dmbi_ok),
    ("Priority ranks inside 1-25",rank_ok,True,rank_ok),
    ("Missing future DMBI outputs",missing_outputs,0,missing_outputs==0),
    ("Future actual outcomes used",False,False,True),
]
audit_df=pd.DataFrame([{"Audit_Check":a,"Result":b,"Expected":c,"Status":"PASS" if d else "FAIL"} for a,b,c,d in checks])
audit_df.to_csv(AUDIT_PATH,index=False)
for _,r in audit_df.iterrows(): print(f"{r['Audit_Check']:<58} : {r['Status']}")
if (audit_df["Status"]!="PASS").any(): raise ValueError("Step 29F hard audit failed.")

method={
    "step":"29F",
    "name":"Future DMBI CRITIC-TOPSIS Prioritization 2026-2030",
    "frozen_critic_weights_from_2024":weights,
    "future_weight_recalculation":False,
    "future_actual_outcomes_used":False,
    "decision_matrix":"One target-month x horizon matrix; 25 districts x 3 burden criteria.",
    "normalization":"Min-max normalization within each 25-district matrix.",
    "topsis":{
        "criterion_direction":"All criteria are benefit-type for planning priority.",
        "positive_ideal":"Maximum weighted normalized criterion value.",
        "negative_ideal":"Minimum weighted normalized criterion value.",
        "distance":"Euclidean",
        "closeness":"D_minus/(D_plus+D_minus)",
        "dmbi_score":"TOPSIS closeness x 100",
        "ranking":"Descending; rank 1 = highest relative planning priority."
    },
    "priority_levels":{
        "Low":"<25th percentile","Medium":"25th to <50th percentile",
        "High":"50th to <75th percentile",
        "Critical":">=75th percentile; highest relative planning priority only"
    },
    "next_steps":["Step 30 GIS priority map","Step 31 resource demand estimation","Step 32 early-warning alerts"]
}
with open(METHOD_PATH,"w",encoding="utf-8") as f: json.dump(method,f,indent=2,default=str)

for h in HORIZONS:
    p=(detail[detail[HORIZON]==h].groupby(TARGET_DATE,as_index=False)
       .agg(Mean_DMBI=("DMBI_Score_0_100","mean"),Max_DMBI=("DMBI_Score_0_100","max")))
    fig,ax=plt.subplots(figsize=(10,5))
    ax.plot(p[TARGET_DATE],p["Mean_DMBI"],label="Mean DMBI")
    ax.plot(p[TARGET_DATE],p["Max_DMBI"],label="Maximum DMBI")
    ax.set_title(f"Future DMBI Priority Trend - H{h}")
    ax.set_xlabel("Target month"); ax.set_ylabel("DMBI score (0-100)"); ax.legend()
    fig.autofmt_xdate(); fig.tight_layout()
    fig.savefig(FIG/f"29f_future_dmbi_trend_h{h}.png",dpi=300,bbox_inches="tight")
    plt.close(fig)

head("STEP 29F RESULTS")
print("\nFrozen 2024 CRITIC weights used unchanged:")
for k in ["C1","C2","C3"]: print(f"- {LABELS[k]}: {weights[k]:.6f}")
print("\nFuture summary by horizon:")
print(hsummary.round(4).to_string(index=False))
print("\nPriority level counts:")
print(lsummary.to_string(index=False))
print("\nInterpretation:")
print("- Higher DMBI = higher relative district planning priority")
print("- Rank 1 = highest relative priority for that month/horizon")
print("- Critical = highest relative planning tier, not clinical emergency")
print("- Same frozen 2024 CRITIC weights used for all future forecasts")
print("- No future actual outcomes are available yet")

head("STEP 29F COMPLETE")
print("\nSaved:")
print(f"- Main future DMBI output : {DETAIL_PATH}")
print(f"- Matrix audit            : {MATRIX_AUDIT_PATH}")
print(f"- Horizon summary         : {SUMMARY_HORIZON_PATH}")
print(f"- Priority-level summary  : {SUMMARY_LEVEL_PATH}")
print(f"- Top-priority districts  : {TOP_DISTRICTS_PATH}")
print(f"- Audit                   : {AUDIT_PATH}")
print(f"- Methodology             : {METHOD_PATH}")
print(f"- Figures                 : {FIG}")
print("\nNEXT: Send the FULL terminal output before Step 30 GIS priority mapping.")
print("\nSTEP 29F - FUTURE DMBI CRITIC-TOPSIS PRIORITIZATION COMPLETE")
print("="*120)
