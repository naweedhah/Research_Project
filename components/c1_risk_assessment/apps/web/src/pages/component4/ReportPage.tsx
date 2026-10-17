"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api, PRODUCT } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { StatusBadge } from "@/components/cards/status-badge";
import { ErrorState, Skeleton } from "@/components/common/states";
import { clinicalPhrase, formatClinicalDate, formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";
import { formatPp, formatRv, progressLabel as profileProgressLabel, reviewLabel, type ChildProfile } from "@/data/child-profile";

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
    risk: number;
    severity: string;
    status: string;
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
    score_label?: string | null;
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
  const { childId } = useParams<{ childId: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ["report", childId],
    queryFn: () => api<Report>(`/children/${childId}/report`),
  });
  const profile = useQuery({
    queryKey: ["child", childId],
    queryFn: () => api<ChildProfile>(`/children/${childId}`),
  });

  if (isLoading) return <Skeleton className="h-96" />;
  if (error || !data) return <ErrorState message="Report could not be generated." />;

  const latest = data.risk_history.at(-1);
  const previous = data.risk_history.length > 1 ? data.risk_history.at(-2) : undefined;
  const first = data.risk_history[0];
  const scoreLabel = clinicalPhrase(data.score_label ?? data.ai_assessment?.score_label, "Model-assessed probability");
  const velocityLabel = clinicalPhrase(data.velocity_label, "Risk velocity");
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
  const aiRisk = data.ai_assessment?.risk ?? latest?.risk ?? data.progress.current_risk;
  const comparable = profile.data?.longitudinal_comparable !== false;

  return (
    <article className="print-plain mx-auto max-w-3xl space-y-6 rounded-2xl bg-white p-8 shadow-card">
      <header className="border-b border-line pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">Child progress summary</p>
        <h1 className="mt-1 text-2xl font-semibold">{data.pseudonymous_id}</h1>
        <p className="mt-2 text-sm font-medium text-[#0A2748]" data-testid="report-disclaimer">
          {clinicalPhrase(data.disclaimer, "AI-assisted assessment. Clinical review required.")}
        </p>
        <p className="mt-1 text-xs text-muted">{PRODUCT.disclaimer}</p>
      </header>

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
        <h2 className="text-lg font-semibold">AI-assisted assessment</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">Latest predicted status</p>
            <p className="mt-1 text-xl font-semibold">{formatNutritionalStatus(aiStatus, aiSeverity)}</p>
            <StatusBadge value={aiSeverity} />
          </div>
          <div className="rounded-xl bg-canvas p-4">
            <p className="text-xs text-muted">{scoreLabel}</p>
            <p className="mt-1 text-xl font-semibold">{formatPercent(aiRisk)}</p>
            <p className="text-xs text-muted">AI-assisted assessment. Clinical review required.</p>
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
            <p className="text-xs text-muted">Score sequence</p>
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
              <th className="py-2 pr-3">Status</th>
              <th className="py-2">Score</th>
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
                <td className="py-2.5">{formatPercent(row.risk)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="rounded-xl border border-line bg-canvas p-4 text-xs text-muted">
        <p data-testid="report-footer-disclaimer">{data.disclaimer}</p>
        <p className="mt-2">Latent embedding vectors and raw model internals are excluded from this clinician report by design.</p>
        <p className="mt-2">Clinical review and WHO growth standards interpretation remain the responsibility of the attending clinician.</p>
      </section>

      <div className="flex flex-wrap gap-3 print:hidden">
        <Button onClick={() => window.print()}>Print report</Button>
        <Link href={`/children/${childId}`}>
          <Button variant="secondary">Back to profile</Button>
        </Link>
      </div>
    </article>
  );
}
