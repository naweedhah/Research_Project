"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Baby, Contact, Loader2, RefreshCw, Users, Utensils, X } from "lucide-react";
import { api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Input, Label, Select } from "@/components/common/field";
import { ageLabel } from "@/utils/utils";
import type { ChildProfile } from "@/data/child-profile";
import { toast } from "sonner";

type RegistrationOptions = {
  facility: { id: string; name: string | null; code: string | null; district: string | null };
  care_teams: string[];
  caregiver_relationships: string[];
  districts: string[];
  moh_areas: string[];
  doctors: { id: string; full_name: string; email: string }[];
  current_user_id: string;
};

const STEPS = [
  { label: "Child", icon: Baby },
  { label: "Family & household", icon: Users },
  { label: "Feeding & supplements", icon: Utensils },
  { label: "Care team", icon: Contact },
] as const;

const NOT_YET = "__not_applicable__";

const EDUCATION = ["No formal education", "Below O/ Level", "O/L passed", "A/ Level passes", "Degree/ diploma"];
const INCOME = ["Less than Rs. 20,000", "Rs.20,000 to Rs. 50,000", "Rs. 50,000 to Rs. 100,000", "More than Rs. 100,000"];
const FATHER_OCC = ["Abroad", "Government worker", "Manual worker", "No job", "Private sector worker", "Self-employed"];
const MOTHER_OCC = ["Government worker", "Housewife", "Private sector worker", "Self-employed"];
const BF_DURATION = ["Less than 6 months", "More than 6 months"];
const CF_TIMING = ["Before 6 months", "After 6 months"];
const FOOD_MEALS = ["2 meals/day", "3 meals/day", "4+ meals/day"];
const FOOD_DIVERSITY = ["Less than 2 varieties", "2 to 5 varieties", "More than 5 varieties"];
const TRIPOSHA = ["No", "Yes - irregular use", "Yes - regular use"];

const fieldClass = "border-[#d7e4f2] bg-white focus:border-[#2563eb] focus:outline-none focus:ring-2 focus:ring-[#2563eb]/20";

type RegState = {
  external: string;
  full_name: string;
  dob: string;
  sex: string;
  birth_weight_kg: string;
  maternal_age_years: string;
  maternal_education: string;
  household_income_range: string;
  household_size: string;
  father_occupation: string;
  mother_occupation: string;
  ebf: string;
  duration: string;
  timing: string;
  meals: string;
  diversity: string;
  triposha: string;
  vitamin: string;
  doctor: string;
  midwife: string;
  caregiver: string;
  rel: string;
  phone: string;
  reminder: boolean;
  district: string;
  moh: string;
  phm: string;
};

function generateChildId(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const stamp = `${String(d.getFullYear()).slice(-2)}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `CH-${stamp}-${rand}`;
}

function emptyState(): RegState {
  return {
    external: generateChildId(),
    full_name: "",
    dob: "",
    sex: "",
    birth_weight_kg: "",
    maternal_age_years: "",
    maternal_education: "",
    household_income_range: "",
    household_size: "",
    father_occupation: "",
    mother_occupation: "",
    ebf: "",
    duration: "",
    timing: "",
    meals: "",
    diversity: "",
    triposha: "",
    vitamin: "",
    doctor: "",
    midwife: "",
    caregiver: "",
    rel: "Mother",
    phone: "",
    reminder: false,
    district: "",
    moh: "",
    phm: "",
  };
}

function str(v: unknown): string {
  if (v === null || v === undefined) return "";
  return String(v);
}

function stateFromRecord(record: ChildProfile): RegState {
  const intake = record.registration_intake;
  const anthro = intake?.anthropometric ?? {};
  const socio = intake?.socioeconomic ?? {};
  const history = intake?.ga_rgca_context ?? {};
  return {
    ...emptyState(),
    external: record.external_patient_id ?? "",
    full_name: record.full_name ?? "",
    dob: record.date_of_birth?.slice(0, 10) ?? "",
    sex: record.sex ?? "",
    birth_weight_kg: str(anthro.birth_weight_kg),
    maternal_age_years: str(history.maternal_age_years),
    maternal_education: str(history.maternal_education),
    household_income_range: str(history.household_income_range),
    household_size: str(socio.household_size),
    father_occupation: str(history.father_occupation),
    mother_occupation: str(history.mother_occupation),
    ebf: str(history.exclusive_breastfeeding),
    duration: str(history.breastfeeding_duration),
    timing: str(history.complementary_feeding_timing),
    meals: str(history.meal_frequency),
    diversity: str(history.dietary_diversity),
    triposha: str(history.triposha_supplementation),
    vitamin: str(history.vitamin_supplementation),
    doctor: record.assigned_doctor?.id ?? "",
    midwife: record.responsible_team ?? "",
    caregiver: record.caregiver?.display_name ?? "",
    rel: record.caregiver?.relationship ?? "Mother",
    phone: record.caregiver?.phone ?? "",
    reminder: Boolean(record.caregiver?.reminder_consent),
    district: record.district ?? "",
    moh: record.moh_area ?? "",
    phm: record.phm_area ?? "",
  };
}

/** Same clinical coupling as before: feeding history answers must agree with each other. */
function applyFeedingLogic(current: RegState, patch: Partial<RegState>): RegState {
  const next = { ...current, ...patch };

  if (patch.timing === "Before 6 months") next.ebf = "No";
  if (patch.ebf === "Yes" && next.timing === "Before 6 months") next.timing = NOT_YET;

  if (next.timing === NOT_YET) {
    next.meals = NOT_YET;
    next.diversity = NOT_YET;
  }
  if (patch.timing === "Before 6 months" || patch.timing === "After 6 months") {
    if (next.meals === NOT_YET) next.meals = "";
    if (next.diversity === NOT_YET) next.diversity = "";
  }
  if ((FOOD_MEALS.includes(next.meals) || FOOD_DIVERSITY.includes(next.diversity)) && next.timing === NOT_YET) {
    next.timing = "";
  }

  return next;
}

function nullable(v: string): string | null {
  const t = v.trim();
  return !t || t === NOT_YET ? null : t;
}

function numeric(v: string): number | null {
  const t = nullable(v);
  if (t === null) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

/** Keeps the registration_intake contract the visit prefill already consumes. */
function buildRegistrationIntake(s: RegState, earlier?: Record<string, unknown> | null) {
  return {
    anthropometric: { birth_weight_kg: numeric(s.birth_weight_kg) },
    socioeconomic: {
      household_changed: false,
      wealth_proxy: null,
      maternal_education: null,
      paternal_education: null,
      maternal_employment: null,
      household_size: numeric(s.household_size),
      geographical_area: null,
      drinking_water: null,
      sanitation: null,
    },
    dietary: {
      breastfeeding_status: null,
      complementary_feeding: null,
      dietary_diversity_score: null,
      meal_frequency: null,
      micronutrient_supplementation: null,
    },
    maternal_child_health: {
      maternal_bmi: null,
      gestational_age_weeks: null,
      immunization_uptodate: null,
      vitamin_a: null,
      recent_diarrhoea: null,
      recent_respiratory_illness: null,
      recent_hospitalization: null,
    },
    ga_rgca_context: {
      maternal_age_years: numeric(s.maternal_age_years),
      maternal_education: nullable(s.maternal_education),
      household_income_range: nullable(s.household_income_range),
      father_occupation: nullable(s.father_occupation),
      mother_occupation: nullable(s.mother_occupation),
      exclusive_breastfeeding: nullable(s.ebf),
      breastfeeding_duration: nullable(s.duration),
      complementary_feeding_timing: nullable(s.timing),
      meal_frequency: nullable(s.meals),
      dietary_diversity: nullable(s.diversity),
      triposha_supplementation: nullable(s.triposha),
      vitamin_supplementation: nullable(s.vitamin),
      historical_mam: earlier?.historical_mam === 0 || earlier?.historical_mam === 1 ? earlier.historical_mam : null,
      historical_sam: earlier?.historical_sam === 0 || earlier?.historical_sam === 1 ? earlier.historical_sam : null,
      historical_underweight: typeof earlier?.historical_underweight === "string" ? earlier.historical_underweight : null,
      historical_stunting: typeof earlier?.historical_stunting === "string" ? earlier.historical_stunting : null,
    },
  };
}

function ageFromDob(dob: string): string {
  if (!dob) return "—";
  const birth = new Date(dob);
  const today = new Date();
  let months = (today.getFullYear() - birth.getFullYear()) * 12 + (today.getMonth() - birth.getMonth());
  if (today.getDate() < birth.getDate()) months -= 1;
  return ageLabel(Math.max(0, months));
}

function Panel({
  label,
  hint,
  required,
  children,
  className = "",
}: {
  label: string;
  hint?: ReactNode;
  required?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl border border-[#d7e4f2] bg-gradient-to-br from-[#f4f8fc] to-white p-4 ${className}`}>
      <Label className="text-[#0f2744]">
        {label}
        {required ? <span className="ml-1 text-clinical-danger">*</span> : null}
      </Label>
      <div className="mt-2">{children}</div>
      {hint ? <p className="mt-1.5 text-xs text-[#64748b]">{hint}</p> : null}
    </div>
  );
}

function Choice({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`rounded-xl border px-3 py-2 text-left text-sm font-medium transition ${
        selected
          ? "border-[#0E3A67] bg-[#EAF2FA] text-[#0E3A67] shadow-[0_8px_20px_-16px_rgba(14,58,103,0.8)]"
          : "border-[#e4ecf4] bg-white text-[#0f2744] hover:border-[#b7cbe0] hover:bg-[#f8fafc]"
      }`}
    >
      {children}
    </button>
  );
}

/** Pill group. Clicking the selected pill again clears it (leaves the field not recorded). */
function Choices({
  value,
  onChange,
  options,
  columns = 2,
  notYet,
}: {
  value: string;
  onChange: (v: string) => void;
  options: readonly string[] | readonly { value: string; label: string }[];
  columns?: 1 | 2 | 3;
  notYet?: boolean;
}) {
  const items = (options as readonly (string | { value: string; label: string })[]).map((o) =>
    typeof o === "string" ? { value: o, label: o } : o,
  );
  const grid = columns === 3 ? "grid-cols-3" : columns === 2 ? "grid-cols-2" : "grid-cols-1";
  return (
    <div className={`grid gap-2 ${grid}`}>
      {items.map((o) => (
        <Choice key={o.value} selected={value === o.value} onClick={() => onChange(value === o.value ? "" : o.value)}>
          {o.label}
        </Choice>
      ))}
      {notYet ? (
        <Choice selected={value === NOT_YET} onClick={() => onChange(value === NOT_YET ? "" : NOT_YET)}>
          Not yet applicable
        </Choice>
      ) : null}
    </div>
  );
}

type RegisterChildModalProps = {
  open: boolean;
  onClose: () => void;
  editChildId?: string | null;
};

export function RegisterChildModal({ open, onClose, editChildId = null }: RegisterChildModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [step, setStep] = useState(0);
  const [s, setS] = useState<RegState>(() => emptyState());

  const options = useQuery({
    queryKey: ["registration-options"],
    queryFn: () => api<RegistrationOptions>("/children/registration-options"),
    enabled: open,
  });
  const existing = useQuery({
    queryKey: ["child", editChildId],
    queryFn: () => api<ChildProfile>(`/children/${editChildId}`),
    enabled: open && Boolean(editChildId),
  });

  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    setError(null);
    setStep(0);
    if (!editChildId) setS(emptyState());
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, editChildId]);

  useEffect(() => {
    if (!open || !editChildId || !existing.data) return;
    setS(stateFromRecord(existing.data));
  }, [open, editChildId, existing.data]);

  useEffect(() => {
    if (!open || editChildId || !options.data) return;
    setS((current) => ({
      ...current,
      district: current.district || options.data.facility.district || "",
      doctor: current.doctor || options.data.current_user_id,
    }));
  }, [open, editChildId, options.data]);

  const mohAreas = useMemo(() => {
    if (!options.data) return [];
    if (s.district && s.district !== options.data.facility.district) {
      return options.data.districts.includes(s.district) ? [`${s.district} MOH — configure`] : options.data.moh_areas;
    }
    return options.data.moh_areas;
  }, [options.data, s.district]);

  if (!open) return null;

  const set = <K extends keyof RegState>(key: K, value: RegState[K]) => setS((current) => applyFeedingLogic(current, { [key]: value } as Partial<RegState>));

  function stepProblems(index: number): string[] {
    const problems: string[] = [];
    if (index === 0) {
      if (!s.external.trim()) problems.push("Child ID is missing.");
      if (s.full_name.trim().length < 2) problems.push("Enter the child's full name.");
      if (!s.dob) problems.push("Enter the date of birth.");
      else if (new Date(s.dob) > new Date()) problems.push("Date of birth cannot be in the future.");
      if (!s.sex) problems.push("Select the child's sex.");
      const bw = Number(s.birth_weight_kg);
      if (!s.birth_weight_kg.trim()) problems.push("Enter the birth weight.");
      else if (!Number.isFinite(bw) || bw < 0.4 || bw > 6.5) problems.push("Birth weight should be between 0.4 and 6.5 kg (kilograms, not grams).");
    }
    if (index === 1) {
      if (s.maternal_age_years.trim()) {
        const age = Number(s.maternal_age_years);
        if (!Number.isFinite(age) || age < 12 || age > 60) problems.push("Maternal age should be between 12 and 60 years.");
      }
      if (s.household_size.trim()) {
        const size = Number(s.household_size);
        if (!Number.isInteger(size) || size < 1 || size > 30) problems.push("Family size should be a whole number between 1 and 30.");
      }
    }
    if (index === 3 && s.phone.trim()) {
      const digits = s.phone.replace(/\D/g, "");
      if (digits.length < 9 || digits.length > 15) problems.push("Caregiver contact number should have 9 to 15 digits.");
    }
    return problems;
  }

  function next() {
    const problems = stepProblems(step);
    if (problems.length) {
      setError(problems.join(" "));
      return;
    }
    setError(null);
    setStep((v) => Math.min(STEPS.length - 1, v + 1));
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    // Enter in a field submits the form. Only the last step may save; earlier steps just advance.
    if (step < STEPS.length - 1) {
      next();
      return;
    }
    const problems = [...stepProblems(0), ...stepProblems(1), ...stepProblems(3)];
    if (problems.length) {
      setError(problems.join(" "));
      setStep(stepProblems(0).length ? 0 : stepProblems(1).length ? 1 : 3);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const facilityName = options.data?.facility.name || "Clinic";
      const payload = {
        full_name: s.full_name.trim(),
        date_of_birth: s.dob,
        sex: s.sex,
        external_patient_id: s.external.trim(),
        responsible_team: s.midwife.trim() || facilityName,
        assigned_doctor_id: s.doctor || options.data?.current_user_id,
        district: s.district || null,
        moh_area: s.moh || null,
        phm_area: s.phm.trim() || null,
        caregiver_relationship: s.rel || "Mother",
        caregiver_display_name: s.caregiver.trim() || null,
        caregiver_phone: s.phone.trim() || null,
        reminder_consent: s.reminder,
        registration_intake: buildRegistrationIntake(
          s,
          (existing.data?.registration_intake?.ga_rgca_context as Record<string, unknown> | null | undefined) ?? null,
        ),
      };
      if (editChildId) {
        await api(`/children/${editChildId}`, { method: "PATCH", body: JSON.stringify(payload) });
        await queryClient.invalidateQueries({ queryKey: ["children"] });
        await queryClient.invalidateQueries({ queryKey: ["child", editChildId] });
        toast.success("Child record updated.");
        onClose();
        return;
      }
      const created = await api<{ id: string; pseudonymous_id: string; message: string }>("/children", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await queryClient.invalidateQueries({ queryKey: ["children"] });
      toast.success(created.message);
      onClose();
      router.push(`/children/${created.id}?registered=1`);
    } catch (err) {
      setError(err instanceof Error ? err.message : editChildId ? "Unable to save this child record" : "Unable to register child");
    } finally {
      setSaving(false);
    }
  }

  const loading = options.isLoading || (Boolean(editChildId) && existing.isLoading);
  const facilityName = options.data?.facility.name ?? "Your facility";
  const relationships = options.data?.caregiver_relationships ?? ["Mother"];
  const relationshipOptions = s.rel && !relationships.includes(s.rel) ? [s.rel, ...relationships] : relationships;
  const districts = options.data?.districts ?? [];
  const districtOptions = s.district && !districts.includes(s.district) ? [s.district, ...districts] : districts;
  const mohOptions = s.moh && !mohAreas.includes(s.moh) ? [s.moh, ...mohAreas] : mohAreas;
  const phmAreas = mohAreas.map((area) => area.replaceAll("MOH", "PHM"));
  const midwifeOptions = s.midwife && !phmAreas.includes(s.midwife) ? [s.midwife, ...phmAreas] : phmAreas;
  const phmOptions = s.phm && !phmAreas.includes(s.phm) ? [s.phm, ...phmAreas] : phmAreas;
  const lastStep = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-40 overflow-y-auto">
      <div className="absolute inset-0 bg-[#0A2748]/40 backdrop-blur-md" aria-hidden />
      <div className="relative flex min-h-full items-start justify-center px-4 py-10 sm:items-center sm:px-6 sm:py-12">
        <div role="dialog" aria-modal="true" aria-labelledby="register-child-title" className="relative w-full max-w-3xl">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 z-10 rounded-lg p-2 text-[#64748b] hover:bg-white hover:text-[#0A2748]"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="overflow-hidden rounded-2xl border border-[#e4ecf4] bg-white shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]">
            <div className="border-b border-[#e4ecf4] bg-[#f7f9fc] px-6 py-5 pr-14">
              <h2 id="register-child-title" className="text-2xl font-bold text-[#0f2744]">
                {editChildId ? "Edit child record" : "Register new child"}
              </h2>
              <p className="mt-1 text-sm text-[#64748b]">
                {facilityName}
                {s.full_name.trim() ? ` · ${s.full_name.trim()}` : ""}
                {s.external ? ` · ${s.external}` : ""}
              </p>
            </div>

            <ol className="flex flex-wrap gap-2 border-b border-[#e4ecf4] px-6 py-3.5">
              {STEPS.map((item, i) => {
                const Icon = item.icon;
                const done = i < step;
                return (
                  <li key={item.label}>
                    <button
                      type="button"
                      onClick={() => (i < step ? setStep(i) : undefined)}
                      className={`flex items-center gap-1.5 rounded-2xl border px-3 py-2 text-xs font-medium transition ${
                        i === step
                          ? "border-[#0E3A67] bg-[#0E3A67] text-white shadow-[0_8px_20px_-16px_rgba(14,58,103,0.8)]"
                          : done
                            ? "border-[#0E3A67]/30 bg-[#EAF2FA] text-[#0E3A67]"
                            : "border-[#e4ecf4] bg-white text-[#475569]"
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {i + 1}. {item.label}
                    </button>
                  </li>
                );
              })}
            </ol>

            <form onSubmit={onSubmit}>
              <div className="max-h-[min(70vh,40rem)] overflow-y-auto px-6 pb-6 pt-5">
                {loading ? (
                  <p className="py-8 text-center text-sm text-[#64748b]">Loading registration options…</p>
                ) : step === 0 ? (
                  <div className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-2">
                      <Panel label="Child ID" hint={editChildId ? "Identifier assigned at registration." : "Generated automatically for this registration."}>
                        <div className="flex items-center gap-2">
                          <Input value={s.external} readOnly className="border-[#d7e4f2] bg-[#f8fafc] font-mono text-[#0f2744]" />
                          {!editChildId ? (
                            <button
                              type="button"
                              onClick={() => set("external", generateChildId())}
                              className="inline-flex h-10 shrink-0 items-center gap-1 rounded-xl border border-[#d7e4f2] bg-white px-3 text-xs font-medium text-[#0E3A67] hover:bg-[#f8fafc]"
                              aria-label="Generate a new child ID"
                            >
                              <RefreshCw className="h-3.5 w-3.5" />
                              New
                            </button>
                          ) : null}
                        </div>
                      </Panel>
                      <Panel label="Child full name" required>
                        <Input value={s.full_name} onChange={(e) => set("full_name", e.target.value)} minLength={2} className={fieldClass} placeholder="As written on the CHDR" />
                      </Panel>
                      <Panel label="Date of birth" required>
                        <Input type="date" max={new Date().toISOString().slice(0, 10)} value={s.dob} onChange={(e) => set("dob", e.target.value)} className={fieldClass} />
                      </Panel>
                      <Panel label="Age" hint="Calculated from the date of birth.">
                        <Input readOnly value={ageFromDob(s.dob)} className="border-[#d7e4f2] bg-[#f8fafc] text-[#0f2744]" />
                      </Panel>
                      <Panel label="Sex" required>
                        <Choices
                          value={s.sex}
                          onChange={(v) => set("sex", v)}
                          options={[
                            { value: "female", label: "Female" },
                            { value: "male", label: "Male" },
                          ]}
                        />
                      </Panel>
                      <Panel label="Birth weight (kg)" required hint="Kilograms, for example 2.9. Not grams.">
                        <Input type="number" step="0.01" min="0.4" max="6.5" value={s.birth_weight_kg} onChange={(e) => set("birth_weight_kg", e.target.value)} className={fieldClass} />
                      </Panel>
                    </div>
                  </div>
                ) : step === 1 ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    <Panel label="Maternal age (years)">
                      <Input type="number" min="12" max="60" value={s.maternal_age_years} onChange={(e) => set("maternal_age_years", e.target.value)} className={fieldClass} />
                    </Panel>
                    <Panel label="Family size" hint="Number of people living in the household, including the child.">
                      <Input type="number" min="1" max="30" step="1" value={s.household_size} onChange={(e) => set("household_size", e.target.value)} className={fieldClass} />
                    </Panel>
                    <Panel label="Maternal education" className="md:col-span-2">
                      <Choices value={s.maternal_education} onChange={(v) => set("maternal_education", v)} options={EDUCATION} columns={3} />
                    </Panel>
                    <Panel label="Household income range" className="md:col-span-2">
                      <Choices value={s.household_income_range} onChange={(v) => set("household_income_range", v)} options={INCOME} />
                    </Panel>
                    <Panel label="Father's occupation">
                      <Choices value={s.father_occupation} onChange={(v) => set("father_occupation", v)} options={FATHER_OCC} />
                    </Panel>
                    <Panel label="Mother's occupation">
                      <Choices value={s.mother_occupation} onChange={(v) => set("mother_occupation", v)} options={MOTHER_OCC} />
                    </Panel>
                  </div>
                ) : step === 2 ? (
                  <div className="space-y-3">
                    <p className="text-xs text-[#64748b]">Usual or earlier feeding pattern. The doctor records today&apos;s intake at each visit.</p>
                    <div className="grid gap-3 md:grid-cols-2">
                      <Panel label="Exclusive breastfeeding" hint="Breast milk only for the first six months.">
                        <Choices value={s.ebf} onChange={(v) => set("ebf", v)} options={["Yes", "No"]} />
                      </Panel>
                      <Panel label="Breastfeeding duration">
                        <Choices value={s.duration} onChange={(v) => set("duration", v)} options={BF_DURATION} />
                      </Panel>
                      <Panel label="Complementary feeding started" className="md:col-span-2">
                        <Choices value={s.timing} onChange={(v) => set("timing", v)} options={CF_TIMING} columns={3} notYet />
                      </Panel>
                      <Panel label="Meal frequency per day" hint="Complementary food meals, not breastfeeds.">
                        <Choices value={s.meals} onChange={(v) => set("meals", v)} options={FOOD_MEALS} columns={2} notYet />
                      </Panel>
                      <Panel label="Dietary diversity" hint="Food varieties usually eaten in a day.">
                        <Choices value={s.diversity} onChange={(v) => set("diversity", v)} options={FOOD_DIVERSITY} columns={2} notYet />
                      </Panel>
                      <Panel label="Triposha supplementation">
                        <Choices value={s.triposha} onChange={(v) => set("triposha", v)} options={TRIPOSHA} columns={1} />
                      </Panel>
                      <Panel label="Vitamin supplementation">
                        <Choices value={s.vitamin} onChange={(v) => set("vitamin", v)} options={["Yes", "No"]} />
                      </Panel>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-xs text-[#64748b]">Optional. Defaults to you as the assigned doctor and this facility.</p>
                    <div className="grid gap-3 md:grid-cols-2">
                      <Panel label="Midwife area">
                        <Select id="reg-midwife" value={s.midwife} onChange={(e) => set("midwife", e.target.value)} className={fieldClass}>
                          <option value="">Select…</option>
                          {midwifeOptions.map((team) => (
                            <option key={team} value={team}>
                              {team}
                            </option>
                          ))}
                        </Select>
                      </Panel>
                      <Panel label="Caregiver name">
                        <Input id="reg-caregiver" value={s.caregiver} onChange={(e) => set("caregiver", e.target.value)} className={fieldClass} />
                      </Panel>
                      <Panel label="Relationship">
                        <Select id="reg-rel" value={s.rel} onChange={(e) => set("rel", e.target.value)} className={fieldClass}>
                          {relationshipOptions.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </Select>
                      </Panel>
                      <Panel label="Contact number">
                        <Input id="reg-phone" type="tel" value={s.phone} onChange={(e) => set("phone", e.target.value)} className={fieldClass} />
                      </Panel>
                      <Panel label="Follow-up reminders">
                        <label className="flex min-h-11 items-center gap-2 text-sm text-[#0f2744]">
                          <input type="checkbox" checked={s.reminder} onChange={(e) => set("reminder", e.target.checked)} className="h-4 w-4 accent-[#0E3A67]" />
                          Allow follow-up reminders
                        </label>
                      </Panel>
                      <Panel label="PHM area">
                        <Select id="reg-phm" value={s.phm} onChange={(e) => set("phm", e.target.value)} className={fieldClass}>
                          <option value="">Select…</option>
                          {phmOptions.map((area) => (
                            <option key={area} value={area}>
                              {area}
                            </option>
                          ))}
                        </Select>
                      </Panel>
                    </div>
                  </div>
                )}

                {error ? (
                  <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
                    {error}
                  </p>
                ) : null}
              </div>

              <div className="flex items-center justify-between gap-2 border-t border-[#e4ecf4] bg-[#f7f9fc] px-6 py-4">
                {step === 0 ? (
                  <Button type="button" variant="secondary" onClick={onClose}>
                    Cancel
                  </Button>
                ) : (
                  <Button type="button" variant="secondary" onClick={() => setStep((v) => Math.max(0, v - 1))}>
                    Back
                  </Button>
                )}
                {lastStep ? (
                  <Button type="submit" disabled={saving || loading}>
                    {saving ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {editChildId ? "Saving…" : "Registering…"}
                      </>
                    ) : editChildId ? (
                      "Save changes"
                    ) : (
                      <>
                        Register child
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </Button>
                ) : (
                  <Button type="submit" disabled={loading}>
                    Continue
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
