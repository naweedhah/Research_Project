"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api, PRODUCT } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { StatusBadge } from "@/components/cards/status-badge";
import { ErrorState, Skeleton } from "@/components/common/states";
import { clinicalPhrase, formatClinicalDate, formatNutritionalStatus, formatPercent, formatStatus, malnutritionSeverityApplies } from "@/utils/utils";
import {
  formatHighestConditionRisk,
  formatPp,
  formatRv,
  primaryTypeProbability,
  primaryTypeProbabilityLabel,
  progressLabel as profileProgressLabel,
  reviewLabel,
  type ChildProfile,
  ageMonthsAtVisit,
} from "@/data/child-profile";
import { assessWhoUndernutrition, NO_UNDERNUTRITION_LABEL } from "@/data/who-growth-standards";
import { applicabilityState, uncertaintyState } from "@/data/clinical-selectors";

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

function progressLabel(state?: string) {
  if (!state || state === "unknown") return "Insufficient visits";
  if (state === "stagnating") return "Limited progress";
  return formatStatus(state);
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
  const first = data.risk_history[0];
  const scoreLabel = clinicalPhrase(data.score_label ?? data.ai_assessment?.score_label, "12-month GA-RGCA prediction");
  const velocityLabel = clinicalPhrase(data.velocity_label, "Risk Velocity");
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
  const aiTypeProbability = primaryTypeProbability(aiSource);
  const comparable = profile.data?.longitudinal_comparable !== false;
  const currentVisit = profile.data?.current ?? null;
  const ageAtLatest = profile.data ? ageMonthsAtVisit(profile.data.date_of_birth, currentVisit?.visit_date, profile.data.age_months) : null;
  const who =
    profile.data && meas.weight_kg != null && meas.height_cm != null && ageAtLatest != null
      ? assessWhoUndernutrition({ ageMonths: ageAtLatest, sex: profile.data.sex, weightKg: meas.weight_kg, heightCm: meas.height_cm })
      : null;
  const whoLabel = who ? (who.label === NO_UNDERNUTRITION_LABEL ? "Normal" : who.label) : "Not assessed";
  const ga = latestPrediction?.ga_rgca ?? null;
  const uncertainty = uncertaintyState(latestPrediction);
  const applicability = applicabilityState(latestPrediction);
  const inputs = profile.data?.latest_inputs ?? null;
  const contextRows: [string, unknown][] = [];
  if (inputs) {
    const dietary = inputs.dietary ?? {};
    const socio = inputs.socioeconomic ?? {};
    const mch = inputs.maternal_child_health ?? {};
    contextRows.push(
      ["Breastfeeding", dietary.breastfeeding_status],
      ["Complementary feeding", dietary.complementary_feeding],
      ["Meal frequency", dietary.meal_frequency],
      ["Micronutrient supplementation", dietary.micronutrient_supplementation],
      ["Household size", socio.household_size],
      ["Maternal education", socio.maternal_education],
      ["Immunisation up to date", mch.immunization_uptodate],
      ["Vitamin A", mch.vitamin_a],
    );
  }
  const fmtContext = (v: unknown) => (v === true ? "Yes" : v === false ? "No" : v == null || v === "" ? "Not recorded" : formatStatus(String(v)));

  return (
    <article className="print-plain mx-auto max-w-3xl space-y-6 rounded-[28px] border border-white/80 bg-white p-8 shadow-card">
      <header className="border-b border-line pb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#3E75B8]">Child nutrition report</p>
        <h1 className="mt-1 text-2xl font-semibold text-[#102A4C]">{profile.data?.full_name?.trim() || data.pseudonymous_id}</h1>
        <p className="text-sm text-muted">
          {data.pseudonymous_id}
          {profile.data ? ` · ${formatStatus(profile.data.sex)} · ${ageAtLatest ?? profile.data.age_months} months at latest visit` : ""}
          {currentVisit ? ` · Visit ${currentVisit.visit_number} on ${formatClinicalDate(currentVisit.visit_date)}` : ""}
          {profile.data?.facility?.name ? ` · ${profile.data.facility.name}` : ""}
        </p>
        <p className="mt-2 text-sm font-medium text-[#0A2748]" data-testid="report-disclaimer">
          {clinicalPhrase(data.disclaimer, "AI-assisted assessment. Clinical review required.")}
        </p>
        <p className="mt-1 text-xs text-muted">{PRODUCT.disclaimer}</p>
      </header>

      <section>
        <h2 className="text-lg font-semibold">Current WHO assessment</h2>
        <p className="text-xs text-muted">Based on latest recorded anthropometric measurements. WHO growth standards, 0–60 months.</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-[1fr_2fr]">
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">Status</p>
            <p className="mt-1 text-xl font-semibold">{whoLabel}</p>
          </div>
          <div className="grid grid-cols-3 gap-2 rounded-xl bg-canvas p-4 text-center">
            {[
              ["Weight-for-age", who?.zScores.waz],
              ["Height-for-age", who?.zScores.haz],
              ["Weight-for-height", who?.zScores.whz],
            ].map(([label, z]) => (
              <div key={String(label)}>
                <p className="text-[10px] uppercase tracking-wide text-muted">{label}</p>
                <p className="mt-1 font-semibold tabular-nums">{typeof z === "number" && Number.isFinite(z) ? `${z >= 0 ? "+" : ""}${z.toFixed(2)} z` : "—"}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold">Current clinical measurements</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">Weight</p>
            <p className="mt-1 text-xl font-semibold">{meas.weight_kg != null ? `${meas.weight_kg} kg` : "—"}</p>
            {previous?.weight_kg != null ? <p className="text-xs text-muted">Previous {previous.weight_kg} kg</p> : null}
          </div>
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">Height</p>
            <p className="mt-1 text-xl font-semibold">{meas.height_cm != null ? `${meas.height_cm} cm` : "—"}</p>
            {previous?.height_cm != null ? <p className="text-xs text-muted">Previous {previous.height_cm} cm</p> : null}
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold">12-month GA-RGCA prediction</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">Latest predicted type</p>
            <p className="mt-1 text-xl font-semibold">{formatNutritionalStatus(aiStatus, aiSeverity)}</p>
            {malnutritionSeverityApplies(aiStatus) ? <StatusBadge value={aiSeverity} /> : null}
            {isConditionModel && aiTypeProbability != null ? (
              <p className="mt-1 text-xs text-muted">
                {primaryTypeProbabilityLabel(aiSource)}: <strong className="text-[#0f2744]">{formatPercent(aiTypeProbability)}</strong>
              </p>
            ) : null}
          </div>
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">{scoreLabel}</p>
            <p className="mt-1 text-xl font-semibold">{formatPercent(aiRisk)}</p>
            {isConditionModel ? (
              <p className="text-xs text-muted">Leading condition: {formatHighestConditionRisk(aiSource)}</p>
            ) : null}
            <p className="text-xs text-muted">AI-assisted assessment. Clinical review required.</p>
          </div>
        </div>
        {ga ? (
          <div className="mt-3 grid gap-2 rounded-xl bg-canvas p-4 text-sm sm:grid-cols-4">
            {[
              ["Underweight", ga.underweight_probability],
              ["Stunting", ga.stunting_probability],
              ["MAM", ga.mam_probability],
              ["SAM", ga.sam_probability],
            ].map(([label, value]) => (
              <div key={String(label)}>
                <p className="text-xs text-muted">{label}</p>
                <p className="font-semibold tabular-nums">{formatPercent(value as number | undefined)}</p>
              </div>
            ))}
            <p className="text-xs text-muted sm:col-span-4">Prediction of nutritional status over the next {ga.prediction_horizon_months ?? 12} months from this visit. Not the current WHO assessment.</p>
          </div>
        ) : null}
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl bg-canvas p-4 text-sm">
            <p className="text-xs text-muted">Severity and review</p>
            <p className="mt-1 font-medium">{aiSeverity ?? "—"}{ga?.triage ? ` · ${ga.triage}` : ""}</p>
            <p className="mt-1 text-xs text-muted">Model uncertainty: {uncertainty.label}</p>
          </div>
          <div className="rounded-xl bg-canvas p-4 text-sm">
            <p className="text-xs text-muted">Similarity to training population</p>
            <p className="mt-1 font-medium">{applicability.label}</p>
            <p className="mt-1 text-xs text-muted">Internal applicability signal; not externally validated.</p>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold">Longitudinal progress</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">Progress state</p>
            <p className="mt-1 font-medium">
              {profile.data
                ? profileProgressLabel(profile.data.progress_display, comparable)
                : progressLabel(data.progress.progress_state)}
            </p>
          </div>
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">{velocityLabel}</p>
            <p className="mt-1 font-medium">
              {profile.data?.risk_velocity_pp_month != null
                ? formatRv(profile.data.risk_velocity_pp_month, comparable)
                : data.progress.risk_velocity != null
                  ? formatRv(Math.round(data.progress.risk_velocity * 1000) / 10, true)
                  : "Not available"}
            </p>
          </div>
          <div className="rounded-xl bg-canvas p-4 sm:col-span-2">
            <p className="text-xs text-muted">{scoreLabel} sequence</p>
            <p className="mt-1 font-medium">
              {first && latest
                ? data.risk_history.map((r) => formatPercent(r.risk)).join(" → ")
                : "—"}
            </p>
            {profile.data?.risk_change_pp != null ? (
              <p className="mt-1 text-xs text-muted">Change since previous: {formatPp(profile.data.risk_change_pp)}</p>
            ) : null}
          </div>
        </div>
        {data.progress.warning ? <p className="mt-3 text-sm text-clinical-warning">{data.progress.warning}</p> : null}
      </section>

      <section>
        <h2 className="text-lg font-semibold">Clinical attention</h2>
        {alerts.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No open or in-review alerts.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {alerts.map((a, i) => (
              <li key={`${a.type}-${i}`} className="rounded-xl bg-canvas p-4 text-sm">
                <p className="font-medium">{a.headline ?? formatStatus(a.type)}</p>
                <p className="mt-1 text-muted">{a.message}</p>
                <p className="mt-1 text-xs text-muted">Status: {formatStatus(a.status)}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold">Clinician review</h2>
        <div className="mt-3 rounded-xl bg-canvas p-4 text-sm">
          <p>
            Status: <strong>{reviewLabel(review?.status)}</strong>
          </p>
          {review?.assessment ? <p className="mt-1">Assessment: {review.assessment}</p> : null}
          {review?.workflow ? <p className="mt-1">Workflow: {review.workflow}</p> : null}
          {review?.reviewer_name ? <p className="mt-1">Reviewed by {review.reviewer_name}</p> : null}
          {review?.note_excerpt ? <p className="mt-1 text-muted">{review.note_excerpt}</p> : null}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold">Follow-up</h2>
        <div className="mt-3 rounded-xl bg-canvas p-4 text-sm">
          <p>
            {followUp?.expected_date ? formatClinicalDate(followUp.expected_date) : "Not scheduled"}
          </p>
          <p className="mt-1 text-muted">
            {followUp?.status === "SUGGESTED" ? "Suggested" : followUp?.status ? formatStatus(followUp.status) : "—"}
          </p>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold">Visit history</h2>
        <table className="mt-3 w-full text-left text-sm">
          <thead className="text-muted">
            <tr>
              <th className="py-2 pr-3">Visit</th>
              <th className="py-2 pr-3">Date</th>
              <th className="py-2 pr-3">Weight</th>
              <th className="py-2 pr-3">Height</th>
              <th className="py-2 pr-3">Predicted type</th>
              {isConditionModel ? <th className="py-2 pr-3">Type probability</th> : null}
              <th className="py-2">{isConditionModel ? "Highest condition risk" : scoreLabel}</th>
            </tr>
          </thead>
          <tbody>
            {data.risk_history.map((row) => (
              <tr key={row.visit_number} className="border-t border-line">
                <td className="py-2.5 pr-3 font-medium">V{row.visit_number}</td>
                <td className="py-2.5 pr-3">{new Date(row.date).toLocaleDateString()}</td>
                <td className="py-2.5 pr-3">{row.weight_kg ?? "—"}</td>
                <td className="py-2.5 pr-3">{row.height_cm ?? "—"}</td>
                <td className="py-2.5 pr-3">{formatNutritionalStatus(row.status, row.severity)}</td>
                {isConditionModel ? <td className="py-2.5 pr-3">{formatPercent(primaryTypeProbability(row))}</td> : null}
                <td className="py-2.5">{isConditionModel ? formatHighestConditionRisk(row) : formatPercent(row.risk)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2 className="text-lg font-semibold">Clinical context</h2>
        {contextRows.length === 0 ? (
          <p className="mt-2 text-sm text-muted">No feeding or household context stored for the latest visit.</p>
        ) : (
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            {contextRows.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-3 rounded-xl bg-canvas px-4 py-2.5">
                <dt className="text-muted">{label}</dt>
                <dd className="font-medium">{fmtContext(value)}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold">Model information</h2>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div className="rounded-xl bg-canvas px-4 py-2.5"><dt className="text-xs text-muted">Model</dt><dd className="font-medium">{ga?.model_version ?? profile.data?.model?.label ?? "GA-RGCA-v4-Rolling-RSL"}</dd></div>
          <div className="rounded-xl bg-canvas px-4 py-2.5"><dt className="text-xs text-muted">Prediction horizon</dt><dd className="font-medium">{ga?.prediction_horizon_months ?? 12} months</dd></div>
          <div className="rounded-xl bg-canvas px-4 py-2.5"><dt className="text-xs text-muted">Prediction generated</dt><dd className="font-medium">{currentVisit ? formatClinicalDate(currentVisit.visit_date) : "—"}</dd></div>
          <div className="rounded-xl bg-canvas px-4 py-2.5"><dt className="text-xs text-muted">Status</dt><dd className="font-medium">Research decision-support prototype</dd></div>
        </dl>
      </section>

      <section className="rounded-xl border border-line bg-canvas p-4 text-xs text-muted">
        <p className="font-semibold text-[#102A4C]">Research disclaimer</p>
        <p className="mt-1" data-testid="report-footer-disclaimer">{data.disclaimer}</p>
        <p className="mt-2">Clinician confirmation required. One historical 12-month origin validated; repeated rolling-origin and external prospective validation are still required. Incident SAM is underpowered. The applicability signal is not externally validated.</p>
        <p className="mt-2">Latent embedding vectors and raw model internals are excluded from this clinician report by design.</p>
        <p className="mt-2">Clinical review and WHO growth standards interpretation remain the responsibility of the attending clinician.</p>
      </section>

      <div className="no-print flex flex-wrap gap-3 print:hidden">
        <Button onClick={() => window.print()}>Print report</Button>
        <Link href={`/children/${childId}`}>
          <Button variant="secondary">Back to profile</Button>
        </Link>
      </div>
    </article>
  );
}
