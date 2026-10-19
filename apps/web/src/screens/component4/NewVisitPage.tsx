"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Input, Label } from "@/components/common/field";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";
import { CurrentConditionCard, PredictionCard } from "@/components/component1/assessment-result-cards";
import { unusualMeasurementMessages } from "@/data/paediatric-measurement-bounds";
import { formatClinicalDate, formatStatus } from "@/utils/utils";
import { AlertTriangle, CheckCircle2, X } from "lucide-react";
import type { ChildProfile } from "@/data/child-profile";
import { measurementChange, predictionLabel, whoLabelForVisit } from "@/data/clinical-selectors";
import { assessWhoUndernutrition, NO_UNDERNUTRITION_LABEL } from "@/data/who-growth-standards";

const STEPS = ["Measurements", "Current feeding", "Review & submit"];

function localDateTimeValue(date = new Date()): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function VisitModalShell({
  children,
  labelledBy,
  onClose,
  wide = false,
}: {
  children: ReactNode;
  labelledBy?: string;
  onClose?: () => void;
  wide?: boolean;
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
          className={wide ? "relative w-full max-w-5xl" : "relative w-full max-w-3xl"}
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
    visit_date: localDateTimeValue(),
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

function modelCategory(value: string): string | null {
  if (!value || value === "__not_applicable__") return null;
  return value;
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
    scheduled: true,
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
    maternal_age_years: str(history.maternal_age_years),
    research_maternal_education: str(history.maternal_education),
    household_income_range: str(history.household_income_range),
    father_occupation: str(history.father_occupation),
    mother_occupation: str(history.mother_occupation),
    exclusive_breastfeeding: str(history.exclusive_breastfeeding),
    breastfeeding_duration_category: str(history.breastfeeding_duration),
    complementary_feeding_timing: str(history.complementary_feeding_timing),
    meal_frequency_category: str(history.meal_frequency),
    dietary_diversity_category: str(history.dietary_diversity),
    triposha_supplementation: str(history.triposha_supplementation),
    vitamin_supplementation: str(history.vitamin_supplementation),
  };
}

function validationHints(form: VisitForm, _isBaseline: boolean): string[] {
  const hints: string[] = [];
  if (!form.age_months) hints.push("Age in months is required.");
  if (!form.weight_kg) hints.push("Weight is required for prediction.");
  if (!form.height_cm) hints.push("Height is required for prediction.");
  if (!form.confirmation) hints.push("Confirm clinic record attestation before submitting.");
  return hints;
}

function ChoiceButton({
  selected,
  title,
  hint,
  onClick,
}: {
  selected: boolean;
  title: string;
  hint?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`rounded-2xl border px-3 py-3 text-left transition ${
        selected
          ? "border-[#0E3A67] bg-[#EAF2FA] shadow-[0_8px_20px_-16px_rgba(14,58,103,0.8)]"
          : "border-[#e4ecf4] bg-white hover:border-[#b7cbe0] hover:bg-[#f8fafc]"
      }`}
    >
      <span className={`block text-sm font-semibold ${selected ? "text-[#0E3A67]" : "text-[#0f2744]"}`}>{title}</span>
      {hint ? <span className="mt-1 block text-xs leading-snug text-[#64748b]">{hint}</span> : null}
    </button>
  );
}

function applyFeedingLogic(current: VisitForm, patch: Partial<VisitForm> = {}): VisitForm {
  const next = { ...current, ...patch };
  const mealsChosen = Boolean(patch.meal_frequency) && Number(next.meal_frequency) > 0;
  const zeroMeals = patch.meal_frequency === "0" || (Boolean(patch.meal_frequency) && Number(next.meal_frequency) === 0);

  if (patch.complementary_feeding === "yes" || mealsChosen) {
    if (next.breastfeeding_status === "exclusive") next.breastfeeding_status = "";
    if (mealsChosen) next.complementary_feeding = "yes";
  }

  if (zeroMeals) {
    next.complementary_feeding = "no";
    next.meal_frequency = "0";
  }

  if (next.breastfeeding_status === "exclusive") {
    next.complementary_feeding = "no";
    next.meal_frequency = "0";
    return next;
  }

  if (next.complementary_feeding === "no") {
    next.meal_frequency = "0";
  } else if (next.complementary_feeding === "yes" && Number(next.meal_frequency) === 0) {
    next.meal_frequency = "";
  }

  return next;
}

function formMeasurementIssues(form: VisitForm): string[] {
  if (!form.age_months.trim() || !form.weight_kg.trim() || !form.height_cm.trim()) return [];
  const age = Number(form.age_months);
  const weight = Number(form.weight_kg);
  const height = Number(form.height_cm);
  if (!Number.isFinite(age) || !Number.isFinite(weight) || !Number.isFinite(height)) return [];
  return unusualMeasurementMessages(age, weight, height);
}

function FieldPanel({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-[#d7e4f2] bg-gradient-to-br from-[#f4f8fc] to-white p-4">
      <Label className="text-[#0f2744]">{label}</Label>
      {children}
      {hint ? <p className="mt-1.5 text-xs text-[#64748b]">{hint}</p> : null}
    </div>
  );
}

function ContextRow({ label, value, accent }: { label: string; value: string; accent?: "navy" }) {
  return (
    <div className={accent === "navy" ? "rounded-xl bg-[#0E243D] px-3 py-2 text-white" : "rounded-xl bg-white/80 px-3 py-2"}>
      <p className={`text-[10px] font-semibold uppercase tracking-[0.12em] ${accent === "navy" ? "text-[#58D3CA]" : "text-[#5C6E82]"}`}>{label}</p>
      <p className={`mt-0.5 text-sm font-semibold ${accent === "navy" ? "text-white" : "text-[#102A4C]"}`}>{value}</p>
    </div>
  );
}

function ChildContextPanel({
  prefill,
  profile,
  form,
}: {
  prefill: Prefill;
  profile?: ChildProfile;
  form: VisitForm;
}) {
  const child = prefill.child;
  const prev = prefill.anthropometric ?? {};
  const prevWeight = typeof prev.weight_kg === "number" ? prev.weight_kg : null;
  const prevHeight = typeof prev.height_cm === "number" ? prev.height_cm : null;
  const history = prefill.historical_growth;
  // Previous WHO status: prefer the stored profile visit; otherwise use the prefill anthropometrics with the age at that visit.
  const previousWho =
    !child.is_baseline && prevWeight != null && prevHeight != null
      ? assessWhoUndernutrition({
          ageMonths: history?.age_months ?? child.age_months,
          sex: child.sex,
          weightKg: prevWeight,
          heightCm: prevHeight,
        })
      : null;
  const previousWhoLabel = profile?.current
    ? whoLabelForVisit(profile, profile.current)
    : previousWho
      ? previousWho.label === NO_UNDERNUTRITION_LABEL
        ? "Normal"
        : previousWho.label
      : "Not assessed";
  const liveWeight = measurementChange(form.weight_kg ? Number(form.weight_kg) : null, prevWeight, "kg");
  const liveHeight = measurementChange(form.height_cm ? Number(form.height_cm) : null, prevHeight, "cm");
  return (
    <aside className="rounded-2xl border border-[#d7e4f2] bg-[#F4F7FA] p-4 lg:sticky lg:top-0" aria-label="Child context">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#3E75B8]">Child context</p>
      <p className="mt-1 text-base font-semibold text-[#102A4C]">{child.full_name?.trim() || child.pseudonymous_id}</p>
      <p className="text-xs text-[#5C6E82]">{child.pseudonymous_id}</p>
      <div className="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-1">
        <ContextRow label="Age today" value={`${form.age_months || child.age_months} months`} />
        <ContextRow label="Sex" value={formatStatus(child.sex)} />
        {child.is_baseline ? (
          <ContextRow label="Visit" value="Baseline · first assessment" />
        ) : (
          <>
            <ContextRow label="Previous visit" value={profile?.current?.visit_date ? formatClinicalDate(profile.current.visit_date) : "Loading…"} />
            <ContextRow label="Previous weight" value={prevWeight != null ? `${prevWeight} kg${liveWeight && liveWeight.direction !== "same" ? ` → today ${liveWeight.text}` : ""}` : "—"} />
            <ContextRow label="Previous height" value={prevHeight != null ? `${prevHeight} cm${liveHeight && liveHeight.direction !== "same" ? ` → today ${liveHeight.text}` : ""}` : "—"} />
            <ContextRow label="Previous WHO assessment" value={previousWhoLabel} />
            <ContextRow label="Previous 12-month prediction" value={profile?.current?.prediction ? predictionLabel(profile.current.prediction) : "Not available"} accent="navy" />
          </>
        )}
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-[#5C6E82]">Previous values are shown for comparison only. Today&apos;s measurements produce a new current WHO assessment and a new 12-month prediction.</p>
    </aside>
  );
}

export default function NewVisitPage() {
  const childId = useParams<{ childId: string }>()?.childId ?? "";
  const router = useRouter();
  const prefillQ = useQuery({
    queryKey: ["visit-prefill", childId],
    queryFn: () => api<Prefill>(`/children/${childId}/visits/prefill`),
    enabled: childId.length > 0,
  });
  const profileQ = useQuery({
    queryKey: ["child", childId],
    queryFn: () => api<ChildProfile>(`/children/${childId}`),
    enabled: childId.length > 0 && prefillQ.data?.child.is_baseline === false,
  });

  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qualityIssues, setQualityIssues] = useState<string[]>([]);
  const [unusualIssues, setUnusualIssues] = useState<string[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState<VisitForm>(() => emptyForm());

  useEffect(() => {
    if (prefillQ.data) setForm(applyFeedingLogic(applyPrefill(emptyForm(prefillQ.data.child.sex), prefillQ.data)));
  }, [prefillQ.data]);

  useEffect(() => {
    if (!prefillQ.data?.child.date_of_birth) return;
    const months = ageMonthsAtVisit(prefillQ.data.child.date_of_birth, form.visit_date);
    if (months) setForm((f) => ({ ...f, age_months: months }));
  }, [form.visit_date, prefillQ.data?.child.date_of_birth]);

  const isBaseline = prefillQ.data?.child.is_baseline ?? false;
  const carrySocio = !form.household_changed && !isBaseline && Boolean(prefillQ.data?.socioeconomic);

  function set<K extends keyof VisitForm>(key: K, value: VisitForm[K]) {
    setForm((f) => {
      return { ...f, [key]: value };
    });
  }

  function setFeeding<K extends keyof VisitForm>(key: K, value: VisitForm[K]) {
    setForm((f) => applyFeedingLogic(f, { [key]: value } as Partial<VisitForm>));
  }

  const hints = useMemo(() => validationHints(form, isBaseline), [form, isBaseline]);

  function continueOrWarn() {
    if (step === 0) {
      const issues = formMeasurementIssues(form);
      if (issues.length) {
        setUnusualIssues(issues);
        return;
      }
    }
    setUnusualIssues([]);
    setStep((s) => s + 1);
  }

  async function submit() {
    if (hints.length > 0) {
      setError("Complete the required fields highlighted in the review step.");
      return;
    }
    const unusual = formMeasurementIssues(form);
    if (unusual.length) {
      setUnusualIssues(unusual);
      return;
    }
    setBusy(true);
    setError(null);
    setQualityIssues([]);
    try {
      const recordedAt = new Date();
      const prev = prefillQ.data?.anthropometric;
      const payload = {
        visit_date: recordedAt.toISOString(),
        visit_type: form.visit_type,
        scheduled: form.scheduled,
        confirmation_attested: form.confirmation,
        anthropometric: {
          age_months: requiredNumber(
            ageMonthsAtVisit(prefillQ.data?.child.date_of_birth, localDateTimeValue(recordedAt)) || form.age_months,
            "Age",
          ),
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
          dietary_diversity_score: null,
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
          exclusive_breastfeeding: modelCategory(form.exclusive_breastfeeding),
          breastfeeding_duration: modelCategory(form.breastfeeding_duration_category),
          complementary_feeding_timing: modelCategory(form.complementary_feeding_timing),
          meal_frequency: modelCategory(form.meal_frequency_category),
          dietary_diversity: modelCategory(form.dietary_diversity_category),
          triposha_supplementation: modelCategory(form.triposha_supplementation),
          vitamin_supplementation: modelCategory(form.vitamin_supplementation),
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
          ? "Please review the highlighted visit information."
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
        binary_variance?: number;
        uncertainty_threshold?: number;
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
        <div className="overflow-hidden rounded-[28px] border border-white/80 bg-white/95 shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)] backdrop-blur-xl">
          <div className="border-b border-[#e4ecf4] bg-[#f7f9fc] px-6 py-5 pr-14">
            <div className="flex items-center gap-2 text-emerald-700">
              <CheckCircle2 className="h-5 w-5" />
              <p className="text-xs font-semibold uppercase tracking-[0.08em]">Visit recorded · prediction generated</p>
            </div>
            <h1 id="visit-result-title" className="mt-1 text-2xl font-bold text-[#0f2744]">
              WHO current <span className="text-[#45C4BB]">→</span> AI future
            </h1>
            <p className="mt-1 text-sm text-[#64748b]">
              {child.full_name ? `${child.full_name} · ` : ""}
              {child.pseudonymous_id} · Visit {recordedVisit?.visit_number ?? child.visit_count}
            </p>
          </div>

          <div className="grid gap-4 px-6 py-5 lg:grid-cols-2">
            <CurrentConditionCard
              weightKg={form.weight_kg}
              heightCm={form.height_cm}
              ageMonths={form.age_months}
              sex={form.sex}
              feeding={{
                breastfeeding_status: form.breastfeeding_status,
                complementary_feeding: form.complementary_feeding,
                meal_frequency: form.meal_frequency,
                micronutrient_supplementation: form.micronutrient_supplementation,
              }}
            />
            <PredictionCard prediction={p} />
          </div>

          <div className="flex flex-wrap gap-2 px-6 pb-6">
            <Button onClick={() => router.push(`/children/${childId}`)}>Open child profile</Button>
            <Button variant="secondary" onClick={() => router.push(`/children/${childId}?tab=ai`)}>
              View AI details
            </Button>
            <Button variant="secondary" onClick={() => router.push(`/children/${childId}/report`)}>
              Report
            </Button>
          </div>
          <p className="px-6 pb-5 text-xs text-[#5C6E82]">Research decision-support prototype. Clinician confirmation required.</p>
        </div>
      </VisitModalShell>
    );
  }

  return (
    <VisitModalShell wide labelledBy="visit-form-title" onClose={() => router.push(`/children/${childId}`)}>
    <div className="overflow-hidden rounded-[28px] border border-white/80 bg-white/95 shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)] backdrop-blur-xl">
      <div className="border-b border-[#e4ecf4] bg-[#f7f9fc] px-6 py-5 pr-14">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#3E75B8]">New visit</p>
        <h1 id="visit-form-title" className="mt-1 text-2xl font-bold text-[#0f2744]">
          {isBaseline ? "Record baseline assessment" : "Record follow-up visit"}
        </h1>
        <p className="mt-1 text-sm text-[#64748b]">
          Enter today&apos;s measurements and feeding context. Visit {child.visit_label ?? (isBaseline ? "V1" : `V${(child.visit_count ?? 0) + 1}`)}.
        </p>
      </div>
      <div className="grid gap-4 p-4 lg:grid-cols-[260px_minmax(0,1fr)] lg:p-5">
      <ChildContextPanel prefill={prefillQ.data} profile={profileQ.data} form={form} />
      <div className="min-w-0">
      <ol className="flex flex-wrap gap-2 border-b border-[#e4ecf4] pb-3.5">
        {STEPS.map((label, i) => (
          <li
            key={label}
            className={`rounded-2xl border px-3 py-2 text-xs font-medium ${
              i === step
                ? "border-[#0E3A67] bg-[#0E3A67] text-white shadow-[0_8px_20px_-16px_rgba(14,58,103,0.8)]"
                : "border-[#e4ecf4] bg-white text-[#475569]"
            }`}
          >
            {i + 1}. {label}
          </li>
        ))}
      </ol>
      <div className="pt-5">
        <div className="space-y-4">
          {step === 0 ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <FieldPanel
                  label="Age (months)"
                  hint={
                    <span className="font-medium text-[#0E3A67]">
                      Birth weight: {form.birth_weight_kg ? `${form.birth_weight_kg} kg` : "not recorded"}
                    </span>
                  }
                >
                  <Input type="number" step="0.1" value={form.age_months} readOnly className="border-[#d7e4f2] bg-white" />
                </FieldPanel>
                <FieldPanel label="Sex">
                  <Input value={formatStatus(form.sex)} readOnly className="border-[#d7e4f2] bg-white" />
                </FieldPanel>
                <FieldPanel
                  label="Weight (kg) *"
                  hint={
                    !isBaseline && prefillQ.data.anthropometric?.weight_kg != null ? (
                      <span className="font-medium text-[#0E3A67]">
                        Last visit: {str(prefillQ.data.anthropometric.weight_kg)} kg
                        {(() => {
                          const d = form.weight_kg ? measurementChange(Number(form.weight_kg), Number(prefillQ.data.anthropometric?.weight_kg), "kg") : null;
                          return d && d.direction !== "same" ? ` · change ${d.text}` : "";
                        })()}
                      </span>
                    ) : (
                      <span>Kilograms, e.g. 9.4</span>
                    )
                  }
                >
                  <Input
                    type="number"
                    step="0.01"
                    value={form.weight_kg}
                    onChange={(e) => set("weight_kg", e.target.value)}
                    className="border-[#d7e4f2] bg-white"
                  />
                </FieldPanel>
                <FieldPanel
                  label="Height / length (cm) *"
                  hint={
                    !isBaseline && prefillQ.data.anthropometric?.height_cm != null ? (
                      <span className="font-medium text-[#0E3A67]">
                        Last visit: {str(prefillQ.data.anthropometric.height_cm)} cm
                        {(() => {
                          const d = form.height_cm ? measurementChange(Number(form.height_cm), Number(prefillQ.data.anthropometric?.height_cm), "cm") : null;
                          return d && d.direction !== "same" ? ` · change ${d.text}` : "";
                        })()}
                      </span>
                    ) : (
                      <span>Centimetres, recumbent length under 24 months</span>
                    )
                  }
                >
                  <Input
                    type="number"
                    step="0.1"
                    value={form.height_cm}
                    onChange={(e) => set("height_cm", e.target.value)}
                    className="border-[#d7e4f2] bg-white"
                  />
                </FieldPanel>
              </div>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="space-y-5">
              <div>
                <p className="mb-2 text-sm font-medium text-[#0f2744]">Breastfeeding status</p>
                <div className="grid gap-2 sm:grid-cols-3">
                  {(
                    [
                      ["exclusive", "Exclusive", "Breast milk only"],
                      ["stopped", "Stopped", "No longer breastfeeding"],
                      ["never", "Never", "Never breastfed"],
                    ] as const
                  ).map(([value, title, hint]) => (
                    <ChoiceButton
                      key={title}
                      selected={form.breastfeeding_status === value}
                      title={title}
                      hint={hint}
                      onClick={() => setFeeding("breastfeeding_status", value)}
                    />
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-[#0f2744]">Complementary feeding</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  {(
                    [
                      ["yes", "Yes"],
                      ["no", "No"],
                    ] as const
                  ).map(([value, title]) => (
                    <ChoiceButton
                      key={title}
                      selected={form.complementary_feeding === value}
                      title={title}
                      onClick={() => setFeeding("complementary_feeding", value)}
                    />
                  ))}
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="mb-2 text-sm font-medium text-[#0f2744]">Meal frequency (per day)</p>
                  <div className="grid grid-cols-4 gap-2">
                    {(
                      [
                        ["0", "0", form.meal_frequency !== "" && Number(form.meal_frequency) === 0],
                        ["2", "1–2", Number(form.meal_frequency) >= 1 && Number(form.meal_frequency) <= 2],
                        ["4", "3–4", Number(form.meal_frequency) >= 3 && Number(form.meal_frequency) <= 4],
                        ["5", "5 or more", Number(form.meal_frequency) >= 5],
                      ] as const
                    ).map(([value, title, selected]) => (
                      <ChoiceButton
                        key={title}
                        selected={selected}
                        title={title}
                        onClick={() => setFeeding("meal_frequency", value)}
                      />
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-sm font-medium text-[#0f2744]">Micronutrient supplementation</p>
                  <div className="grid grid-cols-2 gap-2">
                    {(
                      [
                        ["yes", "Yes"],
                        ["no", "No"],
                      ] as const
                    ).map(([value, title]) => (
                      <ChoiceButton
                        key={`micro-${title}`}
                        selected={form.micronutrient_supplementation === value}
                        title={title}
                        onClick={() => set("micronutrient_supplementation", value)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="space-y-4 text-sm">
              <p className="font-medium text-[#0f2744]">Review before running the model</p>
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-2xl border border-[#d7e4f2] bg-gradient-to-br from-[#f4f8fc] to-white px-4 py-3">
                  <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">Measurements</p>
                  <p className="mt-1 font-semibold text-[#0f2744]">
                    {form.weight_kg || "—"} kg · {form.height_cm || "—"} cm
                  </p>
                  <p className="mt-1 text-xs text-[#64748b]">
                    {form.age_months || "—"} months
                  </p>
                </div>
                <div className="rounded-2xl border border-[#d7e4f2] bg-gradient-to-br from-[#f4f8fc] to-white px-4 py-3">
                  <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#94a3b8]">Current feeding</p>
                  <p className="mt-1 font-semibold text-[#0f2744]">
                    {form.breastfeeding_status ? formatStatus(form.breastfeeding_status) : "Not recorded"}
                  </p>
                  <p className="mt-1 text-xs text-[#64748b]">Meals/day: {form.meal_frequency || "—"}</p>
                </div>
              </div>
              {carrySocio ? (
                <p className="rounded-2xl border border-[#e4ecf4] bg-[#f8fafc] px-4 py-3 text-xs text-[#64748b]">
                  Household data carried forward from registration / previous visit
                </p>
              ) : null}
              {hints.length > 0 ? (
                <ul className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-clinical-warning">
                  {hints.map((h) => (
                    <li key={h}>• {h}</li>
                  ))}
                </ul>
              ) : null}
              {qualityIssues.length > 0 ? (
                <ul className="rounded-2xl border border-clinical-danger/30 bg-red-50 p-4 text-clinical-danger">
                  {qualityIssues.map((q) => (
                    <li key={q}>• {q}</li>
                  ))}
                </ul>
              ) : null}
              <label className="flex items-start gap-3 rounded-2xl border border-[#e4ecf4] bg-white px-4 py-3 text-sm text-[#0f2744]">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 accent-[#0E3A67]"
                  checked={form.confirmation}
                  onChange={(e) => set("confirmation", e.target.checked)}
                />
                <span>
                  <span className="block font-semibold">Confirm clinic record</span>
                  <span className="mt-1 block text-xs text-[#64748b]">
                    I confirm that the entered information matches the available clinic record.
                  </span>
                </span>
              </label>
            </div>
          ) : null}

          {busy ? (
            <p className="rounded-2xl border border-[#45C4BB]/40 bg-[#F4F7FA] px-4 py-3 text-sm text-[#102A4C]" role="status">
              Generating 12-month nutritional risk prediction
              <span className="mt-2 block h-1 overflow-hidden rounded-full bg-[#d7e2ec]">
                <span className="block h-full w-1/2 rounded-full bg-[#45C4BB] progress-sweep" />
              </span>
            </p>
          ) : null}
          {error ? <p className="text-sm text-clinical-danger" role="alert">{error}</p> : null}
          <div className="flex justify-between pt-2">
            <Button variant="secondary" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
              Back
            </Button>
            {step < 2 ? (
              <Button onClick={continueOrWarn}>Continue</Button>
            ) : (
              <Button onClick={submit} disabled={busy || !form.confirmation}>
                {busy ? "Generating 12-month nutritional risk prediction" : "Run 12-month assessment"}
              </Button>
            )}
          </div>
        </div>
      </div>
      </div>
      </div>
    </div>
    {unusualIssues.length > 0 ? (
      <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
        <div className="absolute inset-0 bg-[#0A2748]/50" aria-hidden />
        <div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="unusual-measurement-title"
          className="relative w-full max-w-md rounded-2xl border border-[#e4ecf4] bg-white p-5 shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]"
        >
          <div className="mb-3 flex items-start gap-3">
            <div className="mt-0.5 rounded-full bg-amber-50 p-2 text-amber-700">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h2 id="unusual-measurement-title" className="text-lg font-bold text-[#0f2744]">
                Check these measurements
              </h2>
              <p className="mt-1 text-sm text-[#64748b]">
                These values are not realistic for this child&apos;s age. The visit was not saved. Please verify weight (kg) and height (cm) and enter them again.
              </p>
            </div>
          </div>
          <ul className="space-y-2 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            {unusualIssues.map((issue) => (
              <li key={issue}>• {issue}</li>
            ))}
          </ul>
          <div className="mt-4 flex justify-end">
            <Button
              onClick={() => {
                setUnusualIssues([]);
                set("confirmation", false);
                setStep(1);
              }}
            >
              Review measurements
            </Button>
          </div>
        </div>
      </div>
    ) : null}
    </VisitModalShell>
  );
}
