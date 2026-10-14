"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Input, Label, Select } from "@/components/common/field";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";
import { displayedMalnutritionType } from "@/data/child-profile";
import { formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";
import { X } from "lucide-react";

const STEPS = ["Visit details", "Anthropometry", "Socioeconomic", "Dietary", "Maternal / child health", "Review & submit"];

function VisitModalShell({
  children,
  labelledBy,
  onClose,
}: {
  children: ReactNode;
  labelledBy?: string;
  onClose?: () => void;
}) {
  useEffect(() => {
    if (!onClose) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 overflow-y-auto">
      <div className="absolute inset-0 bg-[#0A2748]/40 backdrop-blur-md" aria-hidden />
      <div className="relative flex min-h-full items-start justify-center px-4 py-10 sm:items-center sm:px-6 sm:py-12">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={labelledBy}
          className="relative w-full max-w-3xl"
        >
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              className="absolute right-3 top-3 z-10 rounded-lg p-2 text-[#64748b] hover:bg-white hover:text-[#0A2748]"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          ) : null}
          {children}
        </div>
      </div>
    </div>
  );
}

type TriState = "" | "yes" | "no" | "unknown";

function triFromBool(v: unknown): TriState {
  if (v === true) return "yes";
  if (v === false) return "no";
  return "";
}

function triToBool(v: TriState): boolean | null {
  if (v === "yes") return true;
  if (v === "no") return false;
  return null;
}

function requiredNumber(value: string, label: string): number {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    throw new Error(`${label} must be a number. Use a decimal point, for example 5.2.`);
  }
  return number;
}

function optionalNumber(value: string, label: string): number | null {
  if (!value.trim()) return null;
  const number = Number(value);
  if (!Number.isFinite(number)) {
    throw new Error(`${label} must be a number. Use a decimal point, for example 3.1.`);
  }
  return number;
}

function ageMonthsAtVisit(dobIso: string | undefined, visitLocal: string): string {
  if (!dobIso || !visitLocal) return "";
  const dob = new Date(dobIso);
  const visit = new Date(visitLocal);
  let months = (visit.getFullYear() - dob.getFullYear()) * 12 + (visit.getMonth() - dob.getMonth());
  if (visit.getDate() < dob.getDate()) months -= 1;
  return String(Math.max(0, months));
}

type Prefill = {
  child: {
    pseudonymous_id: string;
    full_name?: string | null;
    sex: string;
    date_of_birth?: string;
    age_months: number;
    visit_count: number;
    is_baseline: boolean;
    visit_label?: string;
  };
  anthropometric?: Record<string, unknown> | null;
  socioeconomic?: Record<string, unknown> | null;
  dietary?: Record<string, unknown> | null;
  maternal_child_health?: Record<string, unknown> | null;
  ga_rgca_context?: Record<string, unknown> | null;
  historical_growth?: {
    visit_number: number;
    visit_date: string;
    age_months?: number | null;
    height_cm?: number | null;
    weight_kg?: number | null;
  } | null;
};

type VisitForm = {
  visit_date: string;
  visit_type: string;
  scheduled: boolean;
  household_changed: boolean;
  age_months: string;
  sex: string;
  height_cm: string;
  weight_kg: string;
  birth_weight_kg: string;
  wealth_proxy: string;
  maternal_education: string;
  paternal_education: string;
  maternal_employment: string;
  household_size: string;
  geographical_area: string;
  breastfeeding_status: string;
  complementary_feeding: TriState;
  dietary_diversity_score: string;
  meal_frequency: string;
  micronutrient_supplementation: TriState;
  maternal_bmi: string;
  gestational_age_weeks: string;
  immunization_uptodate: TriState;
  vitamin_a: TriState;
  confirmation: boolean;
  maternal_age_years: string;
  research_maternal_education: string;
  household_income_range: string;
  father_occupation: string;
  mother_occupation: string;
  exclusive_breastfeeding: string;
  breastfeeding_duration_category: string;
  complementary_feeding_timing: string;
  meal_frequency_category: string;
  dietary_diversity_category: string;
  triposha_supplementation: string;
  vitamin_supplementation: string;
  historical_mam: string;
  historical_sam: string;
  historical_underweight: string;
  historical_stunting: string;
};

function emptyForm(sex = ""): VisitForm {
  return {
    visit_date: new Date().toISOString().slice(0, 16),
    visit_type: "follow_up",
    scheduled: true,
    household_changed: false,
    age_months: "",
    sex,
    height_cm: "",
    weight_kg: "",
    birth_weight_kg: "",
    wealth_proxy: "",
    maternal_education: "",
    paternal_education: "",
    maternal_employment: "",
    household_size: "",
    geographical_area: "",
    breastfeeding_status: "",
    complementary_feeding: "",
    dietary_diversity_score: "",
    meal_frequency: "",
    micronutrient_supplementation: "",
    maternal_bmi: "",
    gestational_age_weeks: "",
    immunization_uptodate: "",
    vitamin_a: "",
    confirmation: false,
    maternal_age_years: "",
    research_maternal_education: "",
    household_income_range: "",
    father_occupation: "",
    mother_occupation: "",
    exclusive_breastfeeding: "",
    breastfeeding_duration_category: "",
    complementary_feeding_timing: "",
    meal_frequency_category: "",
    dietary_diversity_category: "",
    triposha_supplementation: "",
    vitamin_supplementation: "",
    historical_mam: "",
    historical_sam: "",
    historical_underweight: "",
    historical_stunting: "",
  };
}

function CategorySelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Not recorded</option>
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </Select>
    </div>
  );
}

function str(v: unknown): string {
  if (v === null || v === undefined) return "";
  return String(v);
}

function applyPrefill(base: VisitForm, prefill: Prefill): VisitForm {
  const a = prefill.anthropometric ?? {};
  const s = prefill.socioeconomic ?? {};
  const d = prefill.dietary ?? {};
  const m = prefill.maternal_child_health ?? {};
  const history = prefill.ga_rgca_context ?? {};
  const isBaseline = prefill.child.is_baseline;
  const recordedFlag = (value: unknown) => (value === 0 || value === 1 ? String(value) : "");
  const recordedGrade = (value: unknown) =>
    value === "Normal" || value === "Moderate" || value === "Severe" ? value : "";

  return {
    ...base,
    visit_type: isBaseline ? "routine" : "follow_up",
    age_months: str(prefill.child.age_months),
    sex: prefill.child.sex || base.sex,
    height_cm: isBaseline ? "" : str(a.height_cm),
    weight_kg: isBaseline ? "" : str(a.weight_kg),
    birth_weight_kg: str(a.birth_weight_kg),
    wealth_proxy: str(s.wealth_proxy),
    maternal_education: str(s.maternal_education),
    paternal_education: str(s.paternal_education),
    maternal_employment: str(s.maternal_employment),
    household_size: str(s.household_size),
    geographical_area: str(s.geographical_area),
    breastfeeding_status: str(d.breastfeeding_status),
    complementary_feeding: triFromBool(d.complementary_feeding),
    dietary_diversity_score: str(d.dietary_diversity_score),
    meal_frequency: str(d.meal_frequency),
    micronutrient_supplementation: triFromBool(d.micronutrient_supplementation),
    maternal_bmi: str(m.maternal_bmi),
    gestational_age_weeks: str(m.gestational_age_weeks),
    immunization_uptodate: triFromBool(m.immunization_uptodate),
    vitamin_a: triFromBool(m.vitamin_a),
    historical_mam: recordedFlag(history.historical_mam),
    historical_sam: recordedFlag(history.historical_sam),
    historical_underweight: recordedGrade(history.historical_underweight),
    historical_stunting: recordedGrade(history.historical_stunting),
  };
}

function validationHints(form: VisitForm, isBaseline: boolean): string[] {
  const hints: string[] = [];
  if (!form.age_months) hints.push("Age in months is required.");
  if (!form.weight_kg) hints.push("Weight is required for prediction.");
  if (!form.height_cm) hints.push("Height is required for prediction.");
  if (isBaseline && !form.birth_weight_kg) hints.push("Birth weight is recommended at baseline registration visit.");
  if (!form.confirmation) hints.push("Confirm clinic record attestation before submitting.");
  return hints;
}

/** Aligns with backend QualityReport: required anthro must be present; optional gaps are review-only. */
function dataQualityGate(form: VisitForm, isBaseline: boolean): "READY" | "REVIEW_REQUIRED" | "BLOCKED" {
  const missingRequired = !form.age_months || !form.weight_kg || !form.height_cm || !form.confirmation;
  if (missingRequired) return "BLOCKED";
  const optionalGaps = isBaseline && !form.birth_weight_kg;
  if (optionalGaps) return "REVIEW_REQUIRED";
  return "READY";
}

export default function NewVisitPage() {
  const { childId } = useParams<{ childId: string }>();
  const router = useRouter();
  const prefillQ = useQuery({
    queryKey: ["visit-prefill", childId],
    queryFn: () => api<Prefill>(`/children/${childId}/visits/prefill`),
  });

  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qualityIssues, setQualityIssues] = useState<string[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState<VisitForm>(() => emptyForm());

  useEffect(() => {
    if (prefillQ.data) setForm(applyPrefill(emptyForm(prefillQ.data.child.sex), prefillQ.data));
  }, [prefillQ.data]);

  useEffect(() => {
    if (!prefillQ.data?.child.date_of_birth) return;
    const months = ageMonthsAtVisit(prefillQ.data.child.date_of_birth, form.visit_date);
    if (months) setForm((f) => ({ ...f, age_months: months }));
  }, [form.visit_date, prefillQ.data?.child.date_of_birth]);

  const isBaseline = prefillQ.data?.child.is_baseline ?? false;
  const carrySocio = !form.household_changed && !isBaseline && Boolean(prefillQ.data?.socioeconomic);

  function set<K extends keyof VisitForm>(key: K, value: VisitForm[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  const hints = useMemo(() => validationHints(form, isBaseline), [form, isBaseline]);
  const qualityGate = useMemo(() => dataQualityGate(form, isBaseline), [form, isBaseline]);

  async function submit() {
    if (hints.length > 0) {
      setError("Complete the required fields highlighted in the review step.");
      return;
    }
    setBusy(true);
    setError(null);
    setQualityIssues([]);
    try {
      const prev = prefillQ.data?.anthropometric;
      const payload = {
        visit_date: new Date(form.visit_date).toISOString(),
        visit_type: form.visit_type,
        scheduled: form.scheduled,
        confirmation_attested: form.confirmation,
        anthropometric: {
          age_months: requiredNumber(form.age_months, "Age"),
          sex: form.sex,
          height_cm: requiredNumber(form.height_cm, "Height"),
          weight_kg: requiredNumber(form.weight_kg, "Weight"),
          muac_cm: null,
          birth_weight_kg: optionalNumber(form.birth_weight_kg, "Birth weight"),
          previous_weight_kg: prev?.weight_kg ?? null,
          previous_height_cm: prev?.height_cm ?? null,
        },
        socioeconomic: {
          household_changed: form.household_changed,
          wealth_proxy: form.wealth_proxy || null,
          maternal_education: form.maternal_education || null,
          paternal_education: form.paternal_education || null,
          maternal_employment: form.maternal_employment || null,
          household_size: optionalNumber(form.household_size, "Household size"),
          geographical_area: form.geographical_area || null,
          drinking_water: null,
          sanitation: null,
        },
        dietary: {
          breastfeeding_status: form.breastfeeding_status || null,
          complementary_feeding: triToBool(form.complementary_feeding),
          dietary_diversity_score: optionalNumber(form.dietary_diversity_score, "Dietary diversity score"),
          meal_frequency: optionalNumber(form.meal_frequency, "Meal frequency"),
          micronutrient_supplementation: triToBool(form.micronutrient_supplementation),
        },
        maternal_child_health: {
          maternal_bmi: optionalNumber(form.maternal_bmi, "Maternal BMI"),
          gestational_age_weeks: optionalNumber(form.gestational_age_weeks, "Gestational age"),
          immunization_uptodate: triToBool(form.immunization_uptodate),
          vitamin_a: triToBool(form.vitamin_a),
          recent_diarrhoea: null,
          recent_respiratory_illness: null,
          recent_hospitalization: null,
        },
        ga_rgca_context: {
          maternal_age_years: optionalNumber(form.maternal_age_years, "Maternal age"),
          maternal_education: form.research_maternal_education || null,
          household_income_range: form.household_income_range || null,
          father_occupation: form.father_occupation || null,
          mother_occupation: form.mother_occupation || null,
          exclusive_breastfeeding: form.exclusive_breastfeeding || null,
          breastfeeding_duration: form.breastfeeding_duration_category || null,
          complementary_feeding_timing: form.complementary_feeding_timing || null,
          meal_frequency: form.meal_frequency_category || null,
          dietary_diversity: form.dietary_diversity_category || null,
          triposha_supplementation: form.triposha_supplementation || null,
          vitamin_supplementation: form.vitamin_supplementation || null,
          historical_mam: form.historical_mam === "" ? null : Number(form.historical_mam),
          historical_sam: form.historical_sam === "" ? null : Number(form.historical_sam),
          historical_underweight: form.historical_underweight || null,
          historical_stunting: form.historical_stunting || null,
        },
      };
      const created = await api<{ visit: { id: string }; prediction: Record<string, unknown>; quality: Record<string, unknown> }>(
        `/children/${childId}/visits`,
        { method: "POST", body: JSON.stringify(payload) },
      );
      setResult(created);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : null;
      const quality =
        detail && typeof detail === "object" && !Array.isArray(detail)
          ? (detail as { quality?: { blocking_errors?: { field?: string; message?: string }[] } }).quality
          : null;
      const issues = quality?.blocking_errors ?? [];
      setQualityIssues(issues.map((issue) => issue.message ?? "Review this field."));
      setError(
        issues.length
          ? "This visit was not saved. Review the measurements below."
          : err instanceof Error
            ? err.message
            : "Visit could not be saved",
      );
    } finally {
      setBusy(false);
    }
  }

  if (prefillQ.isLoading) {
    return (
      <VisitModalShell onClose={() => router.push(`/children/${childId}`)}>
        <div className="rounded-2xl border border-[#e4ecf4] bg-white p-6 shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]">
          <Skeleton className="h-96" />
        </div>
      </VisitModalShell>
    );
  }
  if (prefillQ.isError || !prefillQ.data) {
    return (
      <VisitModalShell onClose={() => router.push(`/children/${childId}`)}>
        <div className="rounded-2xl border border-[#e4ecf4] bg-white p-6 shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]">
          <ErrorState message="Unable to load visit context for this child." />
        </div>
      </VisitModalShell>
    );
  }

  const child = prefillQ.data.child;

  if (result?.prediction) {
    const recordedVisit = result.visit as { visit_number?: number } | undefined;
    const p = result.prediction as {
      status: string;
      severity: string;
      risk: number;
      confidence?: string;
      mode: string;
      prediction_source?: string;
      predicted_malnutrition_type?: string;
      detected_conditions?: string[];
      acute_status?: "Normal" | "MAM" | "SAM" | string;
      ga_rgca?: {
        underweight_probability?: number;
        stunting_probability?: number;
        mam_probability?: number;
        sam_probability?: number;
        underweight_positive?: boolean;
        stunting_positive?: boolean;
        predicted_malnutrition_type?: "Normal" | "Underweight" | "Stunting" | "MAM" | "SAM" | string;
        detected_conditions?: string[];
        acute_status?: "Normal" | "MAM" | "SAM" | string;
        severity?: string;
        uncertainty_flag?: boolean;
        uncertainty_label?: string;
        triage?: string;
        model_version?: string;
        prediction_source?: string;
        historical_inputs?: {
          assessment_date?: string | null;
          horizon_end_date?: string | null;
          uses_current_visit_measurements?: boolean;
          fields: Record<string, string>;
        };
      } | null;
    };
    return (
      <VisitModalShell labelledBy="visit-result-title" onClose={() => router.push(`/children/${childId}`)}>
      <Card className="max-w-xl border-[#e4ecf4] shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]">
        <CardHeader>
          <CardTitle id="visit-result-title">
            {p.ga_rgca ? "12-Month Nutritional Risk Prediction" : "AI-assisted assessment"}
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <p>
            Child <strong>{child.pseudonymous_id}</strong> · Visit {recordedVisit?.visit_number ?? child.visit_count}
          </p>
          {p.ga_rgca ? (
            <>
              <div className="grid gap-2 text-sm sm:grid-cols-2">
                <p>Underweight <strong>{formatPercent(p.ga_rgca.underweight_probability)}</strong></p>
                <p>Stunting <strong>{formatPercent(p.ga_rgca.stunting_probability)}</strong></p>
                <p>MAM <strong>{formatPercent(p.ga_rgca.mam_probability)}</strong></p>
                <p>SAM <strong>{formatPercent(p.ga_rgca.sam_probability)}</strong></p>
              </div>
              <p>Predicted Malnutrition Type <strong>{formatNutritionalStatus(displayedMalnutritionType(p), p.ga_rgca.severity)}</strong></p>
              <p>Overall Severity <strong>{p.ga_rgca.severity}</strong></p>
              <p>Model Uncertainty <strong>{p.ga_rgca.uncertainty_flag ? "Elevated" : "Low"}</strong></p>
              <p className="text-sm text-muted">{p.ga_rgca.uncertainty_label}</p>
              <p>Clinical Recommendation <strong>{p.ga_rgca.triage}</strong></p>
              <p>Highest Predicted Condition Risk <strong>{formatPercent(p.risk)}</strong></p>
              <p>Acute Malnutrition Status <strong>{p.ga_rgca.acute_status}</strong></p>
              <p className="text-sm text-muted">
                Acute status represents the model&apos;s Normal/MAM/SAM acute-malnutrition output and is separate from Underweight and Stunting prediction.
              </p>
              {p.ga_rgca.historical_inputs ? (
                <p className="text-sm text-muted">
                  Baseline {p.ga_rgca.historical_inputs.assessment_date ? new Date(p.ga_rgca.historical_inputs.assessment_date).toLocaleDateString() : "date not recorded"}
                  {p.ga_rgca.historical_inputs.horizon_end_date
                    ? `, 12-month horizon ends ${new Date(p.ga_rgca.historical_inputs.horizon_end_date).toLocaleDateString()}`
                    : ""}
                  .{" "}
                  {p.ga_rgca.historical_inputs.uses_current_visit_measurements
                    ? "This visit is the baseline assessment."
                    : "Today's measurements were not copied over the earlier baseline."}{" "}
                  {Object.entries(p.ga_rgca.historical_inputs.fields)
                    .filter(([, state]) => state === "not_recorded")
                    .map(([name]) => name)
                    .join(", ") || "All baseline fields were recorded"}
                  {Object.values(p.ga_rgca.historical_inputs.fields).some((state) => state === "not_recorded")
                    ? " not recorded. Not recorded is unknown, not a confirmed absence."
                    : "."}
                </p>
              ) : null}
              <p>Model <strong>GA-RGCA v3</strong></p>
              <p className="text-sm text-muted">AI-assisted assessment. Clinical review required.</p>
            </>
          ) : (
            <>
              <p>Predicted status <strong>{formatNutritionalStatus(displayedMalnutritionType(p), p.severity)}</strong></p>
              <p>Model-assessed probability <strong>{formatPercent(p.risk)}</strong></p>
              <p className="text-sm text-muted">AI-assisted assessment from the measurements recorded at this visit. Clinical review required.</p>
            </>
          )}
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => router.push(`/children/${childId}`)}>Open child profile</Button>
            <Button variant="secondary" onClick={() => router.push(`/children/${childId}/report`)}>
              View progress report
            </Button>
          </div>
        </CardBody>
      </Card>
      </VisitModalShell>
    );
  }

  return (
    <VisitModalShell labelledBy="visit-form-title" onClose={() => router.push(`/children/${childId}`)}>
    <div className="overflow-hidden rounded-2xl border border-[#e4ecf4] bg-white shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]">
      <div className="border-b border-[#e4ecf4] bg-[#f7f9fc] px-6 py-5 pr-14">
        <h1 id="visit-form-title" className="text-2xl font-bold text-[#0f2744]">
          {isBaseline ? "Baseline nutritional assessment" : "Follow-up nutritional assessment"}
        </h1>
        <p className="mt-1 text-sm text-[#64748b]">
          Patient: {child.full_name ? `${child.full_name} · ` : ""}
          {child.pseudonymous_id} · Visit {child.visit_label ?? (isBaseline ? "V1" : `V${(child.visit_count ?? 0) + 1}`)} ·{" "}
          {new Date(form.visit_date).toLocaleDateString()}
        </p>
      </div>
      <ol className="flex flex-wrap gap-2 border-b border-[#e4ecf4] px-6 py-3.5">
        {STEPS.map((label, i) => (
          <li
            key={label}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
              i === step ? "bg-[#0E3A67] text-white" : "bg-[#f1f5f9] text-[#475569]"
            }`}
          >
            {i + 1}. {label}
          </li>
        ))}
      </ol>
      <div className="px-6 pb-6 pt-5">
        <div className="space-y-4">
          {step === 0 ? (
            <>
              <Label>Visit date/time</Label>
              <Input type="datetime-local" value={form.visit_date} onChange={(e) => set("visit_date", e.target.value)} />
              <Label>Visit type</Label>
              <Select value={form.visit_type} onChange={(e) => set("visit_type", e.target.value)}>
                <option value="routine">Routine / baseline</option>
                <option value="follow_up">Follow-up</option>
                <option value="unscheduled">Unscheduled</option>
              </Select>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.scheduled} onChange={(e) => set("scheduled", e.target.checked)} />
                Scheduled appointment (uncheck if walk-in)
              </label>
            </>
          ) : null}

          {step === 1 ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <Label>Age (months)</Label>
                <Input type="number" step="0.1" value={form.age_months} readOnly className="bg-[#f8fafc]" />
                <p className="mt-1 text-xs text-[#64748b]">Calculated from date of birth and visit date</p>
              </div>
              <div>
                <Label>Sex</Label>
                <Input value={formatStatus(form.sex)} readOnly className="bg-[#f8fafc]" />
              </div>
              <div>
                <Label>Weight (kg) *</Label>
                <Input type="number" step="0.01" value={form.weight_kg} onChange={(e) => set("weight_kg", e.target.value)} />
                <p className="mt-1 text-xs text-[#64748b]">Kilograms, for example 5.2. Not grams.</p>
              </div>
              <div>
                <Label>Height / length (cm) *</Label>
                <Input type="number" step="0.1" value={form.height_cm} onChange={(e) => set("height_cm", e.target.value)} />
                <p className="mt-1 text-xs text-[#64748b]">Centimetres, for example 58.</p>
              </div>
              <div>
                <Label>Birth weight (kg)</Label>
                <Input type="number" step="0.01" value={form.birth_weight_kg} onChange={(e) => set("birth_weight_kg", e.target.value)} />
                <p className="mt-1 text-xs text-[#64748b]">Kilograms, for example 2.9. Not grams.</p>
              </div>
              {!isBaseline && prefillQ.data.anthropometric ? (
                <p className="md:col-span-2 text-xs text-muted">
                  Previous visit: weight {str(prefillQ.data.anthropometric.weight_kg)} kg · height{" "}
                  {str(prefillQ.data.anthropometric.height_cm)} cm
                </p>
              ) : null}
              <div className="md:col-span-2 space-y-2 rounded-xl border border-[#e4ecf4] bg-[#f8fafc] p-3">
                <p className="text-sm font-medium text-[#0f2744]">Earlier clinical record</p>
                <p className="text-xs text-[#64748b]">
                  These are verified earlier findings. They are not taken from a model prediction. Underweight and stunting can both be present. Not recorded means unknown, not confirmed absent.
                </p>
                {prefillQ.data.historical_growth ? (
                  <p className="text-xs text-[#334155]">
                    The 12-month model uses visit {prefillQ.data.historical_growth.visit_number} on{" "}
                    {new Date(prefillQ.data.historical_growth.visit_date).toLocaleDateString()} as its baseline
                    ({str(prefillQ.data.historical_growth.age_months)} months, {str(prefillQ.data.historical_growth.weight_kg)} kg,{" "}
                    {str(prefillQ.data.historical_growth.height_cm)} cm). Today&apos;s weight and height stay on this visit and are not copied into that baseline. The horizon is 12 months after that earlier date.
                  </p>
                ) : (
                  <p className="text-xs text-[#334155]">
                    No earlier measurement is stored. This visit is the baseline. Today&apos;s age, height, and weight are used with this visit date, and the horizon is 12 months after that date.
                  </p>
                )}
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <Label>Earlier MAM</Label>
                    <Select value={form.historical_mam} onChange={(e) => set("historical_mam", e.target.value)}>
                      <option value="">Not recorded</option>
                      <option value="0">No, confirmed absent</option>
                      <option value="1">Yes, confirmed present</option>
                    </Select>
                  </div>
                  <div>
                    <Label>Earlier SAM</Label>
                    <Select value={form.historical_sam} onChange={(e) => set("historical_sam", e.target.value)}>
                      <option value="">Not recorded</option>
                      <option value="0">No, confirmed absent</option>
                      <option value="1">Yes, confirmed present</option>
                    </Select>
                  </div>
                  <CategorySelect label="Earlier underweight" value={form.historical_underweight} options={["Normal", "Moderate", "Severe"]} onChange={(value) => set("historical_underweight", value)} />
                  <CategorySelect label="Earlier stunting" value={form.historical_stunting} options={["Normal", "Moderate", "Severe"]} onChange={(value) => set("historical_stunting", value)} />
                </div>
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <>
              {!isBaseline ? (
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.household_changed} onChange={(e) => set("household_changed", e.target.checked)} />
                  Household information has changed since the previous visit
                </label>
              ) : null}
              {carrySocio ? (
                <p className="rounded-xl bg-canvas p-3 text-xs text-muted">
                  Socioeconomic fields will be carried forward from the previous visit unless you mark household information as changed.
                </p>
              ) : null}
              <div className={`grid gap-3 md:grid-cols-2 ${carrySocio ? "opacity-60 pointer-events-none" : ""}`}>
                <div>
                  <Label>Wealth proxy</Label>
                  <Select value={form.wealth_proxy} onChange={(e) => set("wealth_proxy", e.target.value)}>
                    <option value="">Select…</option>
                    <option value="poorest">Poorest</option>
                    <option value="second">Second quintile</option>
                    <option value="middle">Middle</option>
                    <option value="fourth">Fourth quintile</option>
                    <option value="richest">Richest</option>
                  </Select>
                </div>
                <div>
                  <Label>Maternal education</Label>
                  <Select value={form.maternal_education} onChange={(e) => set("maternal_education", e.target.value)}>
                    <option value="">Select…</option>
                    <option value="none">None</option>
                    <option value="primary">Primary</option>
                    <option value="secondary">Secondary</option>
                    <option value="tertiary">Tertiary</option>
                  </Select>
                </div>
                <div>
                  <Label>Household size</Label>
                  <Input type="number" value={form.household_size} onChange={(e) => set("household_size", e.target.value)} />
                </div>
                <div>
                  <Label>Geographical area</Label>
                  <Input value={form.geographical_area} onChange={(e) => set("geographical_area", e.target.value)} placeholder="e.g. colombo, rural north" />
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium text-[#0f2744]">12-month risk model — household</p>
                <p className="text-xs text-[#64748b]">Leave a field as not recorded when the clinic did not assess it. These labels match the trained categories.</p>
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <Label>Maternal age (years)</Label>
                    <Input type="number" value={form.maternal_age_years} onChange={(e) => set("maternal_age_years", e.target.value)} />
                  </div>
                  <CategorySelect label="Maternal education" value={form.research_maternal_education} options={["No formal education", "Below O/ Level", "O/L passed", "A/ Level passes", "Degree/ diploma"]} onChange={(value) => set("research_maternal_education", value)} />
                  <CategorySelect label="Household income range" value={form.household_income_range} options={["Less than Rs. 20,000", "Rs.20,000 to Rs. 50,000", "Rs. 50,000 to Rs. 100,000", "More than Rs. 100,000"]} onChange={(value) => set("household_income_range", value)} />
                  <CategorySelect label="Father occupation" value={form.father_occupation} options={["Abroad", "Government worker", "Manual worker", "No job", "Private sector worker", "Self-employed"]} onChange={(value) => set("father_occupation", value)} />
                  <CategorySelect label="Mother occupation" value={form.mother_occupation} options={["Government worker", "Housewife", "Private sector worker", "Self-employed"]} onChange={(value) => set("mother_occupation", value)} />
                </div>
              </div>
            </>
          ) : null}

          {step === 3 ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <Label>Breastfeeding status</Label>
                <Select value={form.breastfeeding_status} onChange={(e) => set("breastfeeding_status", e.target.value)}>
                  <option value="">Select…</option>
                  <option value="exclusive">Exclusive</option>
                  <option value="continued">Continued with complementary foods</option>
                  <option value="stopped">Stopped</option>
                  <option value="never">Never breastfed</option>
                </Select>
              </div>
              <div>
                <Label>Dietary diversity score (0–7)</Label>
                <Input type="number" min={0} max={7} value={form.dietary_diversity_score} onChange={(e) => set("dietary_diversity_score", e.target.value)} />
              </div>
              <div>
                <Label>Meal frequency (per day)</Label>
                <Input type="number" min={1} max={8} value={form.meal_frequency} onChange={(e) => set("meal_frequency", e.target.value)} />
              </div>
              <label className="flex items-center gap-2 text-sm md:col-span-2">
                <span className="min-w-[200px] text-sm">Complementary feeding</span>
                <Select value={form.complementary_feeding} onChange={(e) => set("complementary_feeding", e.target.value as TriState)} className="max-w-xs">
                  <option value="">Not assessed</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                  <option value="unknown">Unknown</option>
                </Select>
              </label>
              <label className="flex items-center gap-2 text-sm md:col-span-2">
                <span className="min-w-[200px] text-sm">Micronutrient supplementation</span>
                <Select value={form.micronutrient_supplementation} onChange={(e) => set("micronutrient_supplementation", e.target.value as TriState)} className="max-w-xs">
                  <option value="">Not assessed</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                  <option value="unknown">Unknown</option>
                </Select>
              </label>
            </div>
          ) : null}
          {step === 3 ? (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium text-[#0f2744]">12-month risk model — feeding and supplementation</p>
              <p className="text-xs text-[#64748b]">These are separate from the fields above. A yes/no answer is not converted into a timing or variety category.</p>
              <div className="grid gap-3 md:grid-cols-2">
                <CategorySelect label="Exclusive breastfeeding" value={form.exclusive_breastfeeding} options={["Yes", "No"]} onChange={(value) => set("exclusive_breastfeeding", value)} />
                <CategorySelect label="Breastfeeding duration" value={form.breastfeeding_duration_category} options={["Less than 6 months", "More than 6 months"]} onChange={(value) => set("breastfeeding_duration_category", value)} />
                <CategorySelect label="Complementary feeding timing" value={form.complementary_feeding_timing} options={["Before 6 months", "After 6 months"]} onChange={(value) => set("complementary_feeding_timing", value)} />
                <CategorySelect label="Meal frequency" value={form.meal_frequency_category} options={["2 meals/day", "3 meals/day", "4+ meals/day"]} onChange={(value) => set("meal_frequency_category", value)} />
                <CategorySelect label="Dietary diversity" value={form.dietary_diversity_category} options={["Less than 2 varieties", "2 to 5 varieties", "More than 5 varieties"]} onChange={(value) => set("dietary_diversity_category", value)} />
                <CategorySelect label="Triposha supplementation" value={form.triposha_supplementation} options={["No", "Yes - irregular use", "Yes - regular use"]} onChange={(value) => set("triposha_supplementation", value)} />
                <CategorySelect label="Vitamin supplementation" value={form.vitamin_supplementation} options={["Yes", "No"]} onChange={(value) => set("vitamin_supplementation", value)} />
              </div>
            </div>
          ) : null}

          {step === 4 ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <Label>Maternal BMI</Label>
                <Input type="number" step="0.1" value={form.maternal_bmi} onChange={(e) => set("maternal_bmi", e.target.value)} />
              </div>
              <div>
                <Label>Gestational age at birth (weeks)</Label>
                <Input type="number" value={form.gestational_age_weeks} onChange={(e) => set("gestational_age_weeks", e.target.value)} />
              </div>
              {(
                [
                  ["immunization_uptodate", "Immunization up to date"],
                  ["vitamin_a", "Vitamin A supplementation"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 text-sm">
                  <span className="min-w-[200px]">{label}</span>
                  <Select value={form[key]} onChange={(e) => set(key, e.target.value as TriState)} className="max-w-xs">
                    <option value="">Not assessed</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                    <option value="unknown">Unknown</option>
                  </Select>
                </label>
              ))}
            </div>
          ) : null}

          {step === 5 ? (
            <div className="space-y-3 text-sm">
              <p className="font-medium">Review before running the model</p>
              <ul className="list-disc space-y-1 pl-5 text-muted">
                <li>Weight: {form.weight_kg || "—"} kg · Height: {form.height_cm || "—"} cm</li>
                <li>Visit type: {formatStatus(form.visit_type)} · Age: {form.age_months || "—"} months</li>
                {carrySocio ? <li>Socioeconomic data carried forward from previous visit</li> : null}
              </ul>
              <p
                className={
                  qualityGate === "READY"
                    ? "rounded-xl bg-emerald-50 px-3 py-2 text-emerald-900"
                    : qualityGate === "REVIEW_REQUIRED"
                      ? "rounded-xl bg-amber-50 px-3 py-2 text-clinical-warning"
                      : "rounded-xl bg-red-50 px-3 py-2 text-clinical-danger"
                }
                data-testid="data-quality-gate"
              >
                Data quality: <strong>{qualityGate}</strong>
                {qualityGate === "READY"
                  ? " — required fields complete; prediction can proceed."
                  : qualityGate === "REVIEW_REQUIRED"
                    ? " — optional fields missing; prediction can proceed after confirmation."
                    : " — required fields incomplete; prediction is blocked."}
              </p>
              {hints.length > 0 ? (
                <ul className="rounded-xl bg-amber-50 p-3 text-clinical-warning">
                  {hints.map((h) => (
                    <li key={h}>• {h}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">Required fields appear complete. The server will validate ranges against clinic policy.</p>
              )}
              {qualityIssues.length > 0 ? (
                <ul className="rounded-xl border border-clinical-danger/30 bg-red-50 p-3 text-clinical-danger">
                  {qualityIssues.map((q) => (
                    <li key={q}>• {q}</li>
                  ))}
                </ul>
              ) : null}
              <label className="flex items-start gap-2">
                <input type="checkbox" checked={form.confirmation} onChange={(e) => set("confirmation", e.target.checked)} />
                I confirm that the entered information matches the available clinic record.
              </label>
            </div>
          ) : null}

          {error ? <p className="text-sm text-clinical-danger">{error}</p> : null}
          <div className="flex justify-between pt-2">
            <Button variant="secondary" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
              Back
            </Button>
            {step < 5 ? (
              <Button onClick={() => setStep((s) => s + 1)}>Continue</Button>
            ) : (
              <Button onClick={submit} disabled={busy || !form.confirmation}>
                {busy ? "Running assessment…" : "Run AI assessment"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
    </VisitModalShell>
  );
}
