"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";
import { api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { ErrorState, Skeleton } from "@/components/common/states";
import { ageLabel, displayPredictedSeverity, formatClinicalDate, formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";
import {
  ageMonthsAtVisit,
  formatHighestConditionRisk,
  measurementDelta,
  predictedTypeChipProbability,
  primaryTypeProbabilityLabel,
  reviewLabel,
  type ChildProfile,
  type ProfileVisit,
} from "@/data/child-profile";
import { assessWhoUndernutrition, formatZ, NO_UNDERNUTRITION_LABEL, SAM_Z_CUTOFF, UNDERNUTRITION_Z_CUTOFF } from "@/data/who-growth-standards";

type Report = {
  pseudonymous_id: string;
  disclaimer: string;
  score_label?: string;
  velocity_label?: string;
  research_demonstration?: boolean;
  clinical_use?: boolean;
  progress: {
    progress_state?: string;
    risk_velocity?: number;
    current_risk?: number;
    previous_risk?: number;
    warning?: string;
  };
  risk_history: {
    visit_number: number;
    date: string;
    /** Highest of the four condition probabilities (backend primary risk score). */
    risk: number;
    severity: string;
    status: string;
    predicted_type_probability?: number | null;
    highest_risk_condition?: string | null;
    highest_risk_probability?: number | null;
    progress?: string | null;
    weight_kg?: number | null;
    height_cm?: number | null;
    muac_cm?: number | null;
  }[];
  measurements?: {
    weight_kg?: number | null;
    height_cm?: number | null;
    muac_cm?: number | null;
  } | null;
  ai_assessment?: {
    status?: string | null;
    severity?: string | null;
    risk?: number | null;
    score?: number | null;
    score_label?: string | null;
    predicted_type_probability?: number | null;
    highest_risk_condition?: string | null;
    highest_risk_probability?: number | null;
  } | null;
  alerts?: { type: string; status: string; message: string; headline?: string }[] | null;
  clinician_review?: {
    status?: string | null;
    assessment?: string | null;
    workflow?: string | null;
    reviewer_name?: string | null;
    note_excerpt?: string | null;
  } | null;
  follow_up?: {
    expected_date?: string | null;
    status?: string | null;
  } | null;
};

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">{label}</p>
      <p className="mt-0.5 text-[13px] font-semibold leading-snug text-[#0A2748]">{children ?? "—"}</p>
    </div>
  );
}

function SectionHead({ n, children }: { n: string; children: ReactNode }) {
  return (
    <h2 className="flex items-baseline gap-2 border-b border-[#0E3A67] pb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#0E3A67]">
      <span className="tabular-nums text-[#3E75B8]">{n}</span>
      {children}
    </h2>
  );
}

function zInterpretation(z?: number | null) {
  if (z == null || !Number.isFinite(z)) return "Not assessed";
  if (z < SAM_Z_CUTOFF) return "Below −3 SD";
  if (z < UNDERNUTRITION_Z_CUTOFF) return "Below −2 SD";
  return "Within reference range";
}

function deltaText(current?: number | null, previous?: number | null, unit = "") {
  const delta = measurementDelta(current, previous);
  if (delta == null) return "—";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta}${unit}`;
}

function whoLabelForVisit(profile: ChildProfile, visit: ProfileVisit) {
  const age = ageMonthsAtVisit(profile.date_of_birth, visit.visit_date, profile.age_months);
  const weight = visit.measurements?.weight_kg;
  const height = visit.measurements?.height_cm;
  if (age == null || weight == null || height == null) return "—";
  const who = assessWhoUndernutrition({ ageMonths: age, sex: profile.sex, weightKg: weight, heightCm: height });
  if (!who) return "—";
  return who.label === NO_UNDERNUTRITION_LABEL ? "Normal" : who.label;
}

export default function ReportPage() {
  const childId = useParams<{ childId: string }>()?.childId ?? "";
  const { data, isLoading, error } = useQuery({
    queryKey: ["report", childId],
    queryFn: () => api<Report>(`/children/${childId}/report`),
    enabled: childId.length > 0,
  });
  const profile = useQuery({
    queryKey: ["child", childId],
    queryFn: () => api<ChildProfile>(`/children/${childId}`),
    enabled: childId.length > 0,
  });

  if (isLoading) return <Skeleton className="mx-auto h-96 max-w-3xl rounded-[24px]" />;
  if (error || !data) return <ErrorState message={error instanceof Error ? error.message : "Report could not be generated."} />;

  const latest = data.risk_history.at(-1);
  const previous = data.risk_history.length > 1 ? data.risk_history.at(-2) : undefined;
  const meas = data.measurements ?? {
    weight_kg: latest?.weight_kg,
    height_cm: latest?.height_cm,
    muac_cm: latest?.muac_cm,
  };
  const alerts = data.alerts ?? profile.data?.alerts?.filter((a) => ["OPEN", "ACKNOWLEDGED", "IN_REVIEW"].includes(a.status)) ?? [];
  const review = data.clinician_review ?? profile.data?.clinician_review ?? null;
  const followUp = data.follow_up ?? {
    expected_date: profile.data?.next_follow_up,
    status: profile.data?.follow_up_status,
  };
  const aiStatus = data.ai_assessment?.status ?? latest?.status;
  const aiSeverity = data.ai_assessment?.severity ?? latest?.severity;
  const severityLabel = displayPredictedSeverity(aiStatus, aiSeverity);
  const aiRisk = data.ai_assessment?.risk ?? data.ai_assessment?.score ?? latest?.risk ?? data.progress.current_risk;
  const latestPrediction = profile.data?.current?.prediction ?? profile.data?.visits.at(-1)?.prediction ?? null;
  // Pair the predicted type with its own probability; the report score stays the highest condition risk.
  const aiSource = {
    status: aiStatus,
    risk: aiRisk,
    predicted_type_probability: data.ai_assessment?.predicted_type_probability ?? latest?.predicted_type_probability,
    highest_risk_condition: data.ai_assessment?.highest_risk_condition ?? latest?.highest_risk_condition,
    highest_risk_probability: data.ai_assessment?.highest_risk_probability ?? latest?.highest_risk_probability,
    ga_rgca: latestPrediction?.ga_rgca ?? null,
  };
  const isConditionModel = Boolean(aiSource.ga_rgca || aiSource.highest_risk_condition);
  const aiTypeProbability = predictedTypeChipProbability(aiSource);
  const currentVisit = profile.data?.current ?? null;
  const ageAtLatest = profile.data ? ageMonthsAtVisit(profile.data.date_of_birth, currentVisit?.visit_date, profile.data.age_months) : null;
  const who =
    profile.data && meas.weight_kg != null && meas.height_cm != null && ageAtLatest != null
      ? assessWhoUndernutrition({ ageMonths: ageAtLatest, sex: profile.data.sex, weightKg: meas.weight_kg, heightCm: meas.height_cm })
      : null;
  const whoLabel = who ? (who.label === NO_UNDERNUTRITION_LABEL ? "Normal" : who.label) : "Not assessed";
  const ga = latestPrediction?.ga_rgca ?? null;
  const predictedType = formatNutritionalStatus(aiStatus, aiSeverity);
  const patientName = profile.data?.full_name?.trim() || data.pseudonymous_id;
  const generatedOn = formatClinicalDate(new Date().toISOString());
  const facilityName = profile.data?.facility?.name ?? "Nutrition clinic";
  const attending = profile.data?.assigned_doctor?.full_name ?? review?.reviewer_name ?? "—";
  const hasAlerts = alerts.length > 0;

  let section = 1;
  const n = () => String(section++).padStart(2, "0");

  return (
    <div className="space-y-4">
      <div className="no-print mx-auto flex w-[210mm] max-w-full flex-wrap items-center justify-end gap-3 print:hidden">
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => window.print()}>Print report</Button>
          <Link href={`/children/${childId}`}>
            <Button variant="secondary">Back to profile</Button>
          </Link>
        </div>
      </div>

      <article className="print-plain mx-auto w-[210mm] max-w-full border border-[#c5d4e4] bg-white shadow-[0_16px_40px_-28px_rgba(10,39,72,0.55)]">
        <header className="bg-[#0E3A67] px-6 py-3.5 text-white">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-white/70">
                {facilityName}
                {profile.data?.facility?.district ? ` · ${profile.data.facility.district}` : ""}
              </p>
              <h1 className="mt-0.5 text-xl font-semibold tracking-tight">Paediatric Nutrition Report</h1>
            </div>
            <div className="text-right text-[11px] text-white/80">
              <p className="font-semibold uppercase tracking-[0.14em]">Confidential</p>
              <p className="mt-0.5 tabular-nums">Generated {generatedOn}</p>
            </div>
          </div>
        </header>

        <div className="space-y-4 px-6 py-4">
          <section>
            <SectionHead n={n()}>Patient</SectionHead>
            <div className="mt-2.5 grid grid-cols-4 gap-x-5 gap-y-2.5">
              <Field label="Patient">{patientName}</Field>
              <Field label="Record ID">{data.pseudonymous_id}</Field>
              <Field label="Sex">{profile.data ? formatStatus(profile.data.sex) : "—"}</Field>
              <Field label="Age">{ageLabel(ageAtLatest ?? profile.data?.age_months)}</Field>
              <Field label="Date of birth">{profile.data?.date_of_birth ? formatClinicalDate(profile.data.date_of_birth) : "—"}</Field>
              <Field label="Visit">{currentVisit ? `V${currentVisit.visit_number} · ${formatClinicalDate(currentVisit.visit_date)}` : "—"}</Field>
              <Field label="Facility">{facilityName}</Field>
              <Field label="Attending">{attending}</Field>
            </div>
          </section>

          <section>
            <SectionHead n={n()}>Clinical summary</SectionHead>
            <div className="mt-2.5 grid grid-cols-4 gap-x-5 border border-[#d7e4f2] bg-[#f7f9fc] px-3 py-2.5">
              <Field label="Today · WHO">{whoLabel}</Field>
              <Field label="12-month type">{predictedType}{severityLabel ? ` · ${severityLabel}` : ""}</Field>
              <Field label="Review">{reviewLabel(review?.status)}</Field>
              <Field label="Next review">{followUp?.expected_date ? formatClinicalDate(followUp.expected_date) : "Not scheduled"}</Field>
            </div>
          </section>

          <section className="grid grid-cols-2 gap-5">
            <div>
              <SectionHead n={n()}>Anthropometry</SectionHead>
              <table className="mt-2 w-full text-left text-[12px]">
                <thead>
                  <tr className="border-b border-[#d7e4f2] text-[9px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">
                    <th className="py-1.5 pr-3">Parameter</th>
                    <th className="py-1.5 pr-3">This visit</th>
                    <th className="py-1.5 pr-3">Previous</th>
                    <th className="py-1.5">Change</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-[#eef2f7]">
                    <td className="py-1.5 pr-3 text-[#475569]">Weight</td>
                    <td className="py-1.5 pr-3 font-semibold tabular-nums">{meas.weight_kg != null ? `${meas.weight_kg} kg` : "—"}</td>
                    <td className="py-1.5 pr-3 tabular-nums text-[#64748b]">{previous?.weight_kg != null ? `${previous.weight_kg} kg` : "—"}</td>
                    <td className="py-1.5 font-medium tabular-nums">{deltaText(meas.weight_kg, previous?.weight_kg, " kg")}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 pr-3 text-[#475569]">Height</td>
                    <td className="py-1.5 pr-3 font-semibold tabular-nums">{meas.height_cm != null ? `${meas.height_cm} cm` : "—"}</td>
                    <td className="py-1.5 pr-3 tabular-nums text-[#64748b]">{previous?.height_cm != null ? `${previous.height_cm} cm` : "—"}</td>
                    <td className="py-1.5 font-medium tabular-nums">{deltaText(meas.height_cm, previous?.height_cm, " cm")}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div>
              <SectionHead n={n()}>Current WHO</SectionHead>
              <table className="mt-2 w-full text-left text-[12px]">
                <thead>
                  <tr className="border-b border-[#d7e4f2] text-[9px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">
                    <th className="py-1.5 pr-3">Index</th>
                    <th className="py-1.5 pr-3 text-right">z-score</th>
                    <th className="py-1.5">Interpretation</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["WAZ", who?.zScores.waz],
                    ["HAZ", who?.zScores.haz],
                    ["WHZ", who?.zScores.whz],
                  ].map(([label, z]) => (
                    <tr key={String(label)} className="border-b border-[#eef2f7] last:border-0">
                      <td className="py-1.5 pr-3 text-[#475569]">{label}</td>
                      <td className="py-1.5 pr-3 text-right font-semibold tabular-nums">{formatZ(typeof z === "number" ? z : null)}</td>
                      <td className="py-1.5 text-[#334155]">{zInterpretation(typeof z === "number" ? z : null)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <SectionHead n={n()}>12-month nutritional risk</SectionHead>
            <div className="mt-2.5 grid grid-cols-4 gap-x-5">
              <Field label="Predicted type">{predictedType}</Field>
              <Field label="Severity">{severityLabel ?? "—"}</Field>
              <Field label={isConditionModel ? primaryTypeProbabilityLabel(aiSource) : "Predicted risk"}>
                {isConditionModel ? formatPercent(aiTypeProbability) : formatPercent(aiRisk)}
              </Field>
              <Field label="Highest condition risk">{isConditionModel ? formatHighestConditionRisk(aiSource) : "—"}</Field>
            </div>
            {ga ? (
              <div className="mt-2.5 grid grid-cols-4 gap-3 text-[12px]">
                {[
                  ["Underweight", ga.underweight_probability],
                  ["Stunting", ga.stunting_probability],
                  ["MAM", ga.mam_probability],
                  ["SAM", ga.sam_probability],
                ].map(([label, value]) => (
                  <div key={String(label)} className="border-b border-[#eef2f7] pb-1.5">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">{label}</p>
                    <p className="mt-0.5 font-semibold tabular-nums text-[#0A2748]">{formatPercent(value as number | undefined)}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </section>

          {hasAlerts ? (
            <section>
              <SectionHead n={n()}>Clinical attention</SectionHead>
              <ul className="mt-2 space-y-1.5 text-[12px]">
                {alerts.map((a, i) => (
                  <li key={`${a.type}-${i}`} className="text-[#334155]">
                    <span className="font-semibold text-[#0A2748]">{a.headline ?? formatStatus(a.type)}.</span> {a.message}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section>
            <SectionHead n={n()}>Visit record</SectionHead>
            <table className="mt-2 w-full text-left text-[12px]">
              <thead>
                <tr className="border-b border-[#0E3A67] text-[9px] font-semibold uppercase tracking-[0.12em] text-[#0E3A67]">
                  <th className="py-1.5 pr-2">Visit</th>
                  <th className="py-1.5 pr-2">Date</th>
                  <th className="py-1.5 pr-2">Weight</th>
                  <th className="py-1.5 pr-2">Height</th>
                  <th className="py-1.5 pr-2">WHO today</th>
                  <th className="py-1.5 pr-2">12-month type</th>
                  {isConditionModel ? <th className="py-1.5">Type probability</th> : null}
                </tr>
              </thead>
              <tbody>
                {data.risk_history.map((row) => {
                  const visit = profile.data?.visits.find((v) => v.visit_number === row.visit_number);
                  return (
                    <tr key={row.visit_number} className="border-b border-[#eef2f7] last:border-0">
                      <td className="py-1.5 pr-2 font-semibold tabular-nums">V{row.visit_number}</td>
                      <td className="py-1.5 pr-2">{formatClinicalDate(row.date)}</td>
                      <td className="py-1.5 pr-2 tabular-nums">{row.weight_kg != null ? `${row.weight_kg} kg` : "—"}</td>
                      <td className="py-1.5 pr-2 tabular-nums">{row.height_cm != null ? `${row.height_cm} cm` : "—"}</td>
                      <td className="py-1.5 pr-2">{profile.data && visit ? whoLabelForVisit(profile.data, visit) : "—"}</td>
                      <td className="py-1.5 pr-2">{formatNutritionalStatus(row.status, row.severity)}</td>
                      {isConditionModel ? <td className="py-1.5 tabular-nums">{formatPercent(predictedTypeChipProbability(row))}</td> : null}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        </div>
      </article>
    </div>
  );
}
