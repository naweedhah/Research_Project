"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Calendar,
  ClipboardList,
  FileText,
  Info,
  Minus,
} from "lucide-react";
import { CurrentConditionCard, PredictionCard } from "@/components/component1/assessment-result-cards";
import { ProbabilityBar } from "@/components/clinical/primitives";
import { ChildModelHud } from "@/components/component1/child-model-hud";
import { ChildModelViewer } from "@/components/component1/child-model/ChildModelViewer";
import { LatentTrajectory, TrendChart, type TrendMetric } from "@/components/charts/child-profile-charts";
import { ExplainabilityTrigger } from "@/components/component1/explainability-dialog";
import { VisitMotionTimeline } from "@/components/futuristic/visit-motion";
import { FollowUpSchedulePanel } from "@/components/component1/follow-up-schedule-panel";
import { RegisterChildModal } from "@/components/component1/register-child-modal";
import { ConfirmAction, RecordActions } from "@/components/component1/record-actions";
import { Button } from "@/components/common/button";
import { Input, Label, Textarea } from "@/components/common/field";
import { EmptyState } from "@/components/common/states";
import { api } from "@/services/component4/httpClient";
import {
  architectureLabel,
  ageMonthsAtVisit,
  alertTone,
  formatPp,
  openAlert,
  probabilitySeries,
  progressLabel,
  reviewLabel,
  displayedMalnutritionType,
  conditionProbability,
  defaultTrendCondition,
  formatHighestConditionRisk,
  highestConditionRisk,
  predictedTypeChipProbability,
  primaryTypeProbabilityLabel,
  runtimeModeLabel,
  sameConditionDelta,
  TREND_CONDITIONS,
  visitProbabilityDeltaPp,
  riskVelocityPpMonth,
  monthlyVelocityDisplay,
  type ChildProfile,
  type ProfileTab,
  type ProfileVisit,
} from "@/data/child-profile";
import { getModelOutputDisplayMetadata } from "@/data/model-display";
import { clinicalPhrase, cn, displayPredictedSeverity, formatClinicalDate, formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";

function InfoTip({ text, label }: { text: string; label: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        className="rounded-full p-0.5 text-[#94a3b8] hover:text-[#2563eb] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#0e3a67]"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setOpen(false)}
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      {open ? (
        <span role="tooltip" className="absolute left-0 top-6 z-20 w-64 rounded-xl border border-line bg-white p-3 text-xs leading-relaxed text-[#475569] shadow-card">
          {text}
        </span>
      ) : null}
    </span>
  );
}

function ProgressGlyph({ state }: { state?: string | null }) {
  if (state === "improving") return <ArrowUpRight className="h-4 w-4 text-clinical-ok" aria-hidden />;
  if (state === "deteriorating") return <ArrowDownRight className="h-4 w-4 text-clinical-danger" aria-hidden />;
  if (state === "stagnating") return <ArrowRight className="h-4 w-4 text-clinical-warning" aria-hidden />;
  return <Minus className="h-4 w-4 text-[#64748b]" aria-hidden />;
}

function pillClass(selected: boolean, size: "sm" | "md" = "md") {
  return cn(
    "rounded-full border transition",
    size === "md" ? "px-3.5 py-1.5 text-sm" : "px-3 py-1.5 text-xs",
    selected
      ? "border-navy-800 bg-navy-50 font-medium text-navy-900 shadow-sm"
      : "border-line bg-white text-[#475569] hover:bg-[#f8fafc]",
  );
}

function FieldLabel({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748b]", className)}>{children}</p>;
}

function MetricTile({
  label,
  value,
  hint,
  action,
  className,
}: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70", className)}>
      <div className="flex items-center justify-between gap-2">
        <FieldLabel>{label}</FieldLabel>
        {action}
      </div>
      <div className="mt-1 text-lg font-semibold tabular-nums leading-tight text-[#0f2744]">{value}</div>
      {hint ? <p className="mt-0.5 text-xs text-[#64748b]">{hint}</p> : null}
    </div>
  );
}

function Section({
  id,
  title,
  subtitle,
  actions,
  children,
  className,
  bodyClassName,
}: {
  id?: string;
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section id={id} className={cn("rounded-2xl border border-line bg-white shadow-card", className)}>
      {title != null || actions != null ? (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-3.5">
          <div className="min-w-0">
            {title != null ? <h2 className="text-base font-semibold tracking-tight text-[#0f2744]">{title}</h2> : null}
            {subtitle != null ? <p className="mt-0.5 text-sm text-muted">{subtitle}</p> : null}
          </div>
          {actions}
        </header>
      ) : null}
      <div className={cn("px-5 py-4", bodyClassName)}>{children}</div>
    </section>
  );
}

export function ChildProfileView({
  profile,
  tab,
  onTab,
  justRegistered,
  onDismissRegistered,
  onSaveReview,
  reviewSaving,
  onAddNote,
  noteSaving,
  onAcknowledge,
}: {
  profile: ChildProfile;
  tab: ProfileTab;
  onTab: (tab: ProfileTab) => void;
  justRegistered?: boolean;
  onDismissRegistered?: () => void;
  onSaveReview: (payload: { assessment: string; workflow: string; note: string }) => void;
  reviewSaving?: boolean;
  onAddNote: (body: string) => void;
  noteSaving?: boolean;
  onAcknowledge?: (id: string) => void;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<{ permissions?: string[] }>("/auth/me"),
  });
  const canWrite = me.data?.permissions?.includes("child:write") ?? false;
  const hasBaseline = profile.has_baseline ?? profile.visits.length > 0;
  const alert = openAlert(profile);
  const comparable = profile.longitudinal_comparable !== false;
  const series = useMemo(() => probabilitySeries(profile), [profile]);
  const [metric, setMetric] = useState<TrendMetric>("probability");
  const [qualityOpen, setQualityOpen] = useState(false);
  const [inputsOpen, setInputsOpen] = useState(false);
  const [editChild, setEditChild] = useState(false);
  const [removeChild, setRemoveChild] = useState(false);
  const [removingChild, setRemovingChild] = useState(false);
  const [visitEditor, setVisitEditor] = useState<ProfileVisit | null>(null);
  const [visitDate, setVisitDate] = useState("");
  const [visitWeight, setVisitWeight] = useState("");
  const [visitHeight, setVisitHeight] = useState("");
  const [visitSaving, setVisitSaving] = useState(false);
  const [visitError, setVisitError] = useState<string | null>(null);
  const [removeVisit, setRemoveVisit] = useState<ProfileVisit | null>(null);
  const [removingVisit, setRemovingVisit] = useState(false);

  function openVisitEditor(visit: ProfileVisit) {
    setVisitEditor(visit);
    setVisitDate(visit.visit_date.slice(0, 10));
    setVisitWeight(visit.measurements?.weight_kg != null ? String(visit.measurements.weight_kg) : "");
    setVisitHeight(visit.measurements?.height_cm != null ? String(visit.measurements.height_cm) : "");
    setVisitError(null);
  }

  async function saveVisitCorrection() {
    if (!visitEditor) return;
    const weight = Number(visitWeight);
    const height = Number(visitHeight);
    if (!visitDate || !Number.isFinite(weight) || !Number.isFinite(height)) {
      setVisitError("Enter the visit date, weight in kilograms, and height in centimetres.");
      return;
    }
    setVisitSaving(true);
    setVisitError(null);
    try {
      await api(`/visits/${visitEditor.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          visit_date: new Date(visitDate).toISOString(),
          weight_kg: weight,
          height_cm: height,
        }),
      });
      await queryClient.invalidateQueries({ queryKey: ["child", profile.id] });
      toast.success(`Visit ${visitEditor.visit_number} was updated and the assessment was run again.`);
      setVisitEditor(null);
    } catch (err) {
      setVisitError(err instanceof Error ? err.message : "Unable to update this visit");
    } finally {
      setVisitSaving(false);
    }
  }

  async function confirmRemoveChild() {
    setRemovingChild(true);
    try {
      await api(`/children/${profile.id}`, { method: "DELETE" });
      await queryClient.invalidateQueries({ queryKey: ["children"] });
      toast.success(`${profile.pseudonymous_id} was removed from the clinic list.`);
      router.push("/children");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to remove this child");
      setRemovingChild(false);
    }
  }

  async function confirmRemoveVisit() {
    if (!removeVisit) return;
    setRemovingVisit(true);
    try {
      await api(`/visits/${removeVisit.id}`, { method: "DELETE" });
      await queryClient.invalidateQueries({ queryKey: ["child", profile.id] });
      toast.success(`Visit ${removeVisit.visit_number} was removed.`);
      setRemoveVisit(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to remove this visit");
    } finally {
      setRemovingVisit(false);
    }
  }

  const weightHist = series.map((s) => s.weight).filter((v): v is number => v != null);
  const heightHist = series.map((s) => s.height).filter((v): v is number => v != null);

  return (
    <div className="space-y-4 pb-6">
      <RegisterChildModal open={editChild} editChildId={profile.id} onClose={() => setEditChild(false)} />
      <ConfirmAction
        open={removeChild}
        title="Remove child"
        message={`${profile.pseudonymous_id} will be removed from the clinic list.`}
        confirmLabel="Remove child"
        busy={removingChild}
        onCancel={() => setRemoveChild(false)}
        onConfirm={confirmRemoveChild}
      />
      <ConfirmAction
        open={Boolean(removeVisit)}
        title="Remove visit"
        message={removeVisit ? `Visit ${removeVisit.visit_number} on ${formatClinicalDate(removeVisit.visit_date)} and its assessment will be removed.` : ""}
        confirmLabel="Remove visit"
        busy={removingVisit}
        onCancel={() => setRemoveVisit(null)}
        onConfirm={confirmRemoveVisit}
      />
      {visitEditor ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <button type="button" className="absolute inset-0 bg-[#0A2748]/40" aria-label="Close" onClick={() => setVisitEditor(null)} />
          <form
            className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
            onSubmit={(event) => {
              event.preventDefault();
              void saveVisitCorrection();
            }}
          >
            <h2 className="text-lg font-semibold text-[#0f2744]">Edit visit {visitEditor.visit_number}</h2>
            <p className="mt-1 text-sm text-[#64748b]">Correct the recorded measurements. The assessment for this visit is run again.</p>
            <div className="mt-4 space-y-3">
              <div>
                <Label htmlFor="edit-visit-date">Visit date</Label>
                <Input id="edit-visit-date" type="date" value={visitDate} onChange={(event) => setVisitDate(event.target.value)} required />
              </div>
              <div>
                <Label htmlFor="edit-visit-weight">Weight (kg)</Label>
                <Input id="edit-visit-weight" type="number" step="0.01" value={visitWeight} onChange={(event) => setVisitWeight(event.target.value)} required />
              </div>
              <div>
                <Label htmlFor="edit-visit-height">Height / length (cm)</Label>
                <Input id="edit-visit-height" type="number" step="0.1" value={visitHeight} onChange={(event) => setVisitHeight(event.target.value)} required />
              </div>
              {visitError ? <p className="text-sm text-clinical-danger">{visitError}</p> : null}
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setVisitEditor(null)} disabled={visitSaving}>
                Cancel
              </Button>
              <Button type="submit" disabled={visitSaving}>
                {visitSaving ? "Saving…" : "Save and reassess"}
              </Button>
            </div>
          </form>
        </div>
      ) : null}
      <header>
        <h1 className="sr-only">{profile.pseudonymous_id}</h1>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            {tab !== "overview" ? (
              <button
                type="button"
                onClick={() => onTab("overview")}
                className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-full border border-[#e7eef6] bg-[#f8fafc] px-3.5 text-sm font-medium text-[#0A2748] hover:bg-white"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden />
                Go back
              </button>
            ) : null}
            <h2 className="text-xl font-semibold tracking-tight text-[#0A2748] sm:text-2xl">Progress Tracking</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link href={`/children/${profile.id}/report`}>
              <Button variant="secondary" className="h-10 rounded-full px-4 text-sm">
                <FileText className="h-4 w-4" /> Export Report
              </Button>
            </Link>
            <Link href={`/children/${profile.id}/visits/new`}>
              <Button className="h-10 rounded-full px-5 text-sm">
                <ClipboardList className="h-4 w-4" /> {hasBaseline ? "Record Visit" : "Record first visit"}
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {justRegistered ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-950">
          <p className="font-semibold">Child registered successfully.</p>
          <p className="mt-1">No nutritional assessment has been recorded yet.</p>
          <Button variant="secondary" className="mt-3 h-9 rounded-xl text-xs" onClick={onDismissRegistered}>
            Dismiss
          </Button>
        </div>
      ) : null}

      {tab === "overview" ? (
        <div id="profile-panel-overview" role="tabpanel" aria-labelledby="profile-tab-overview">
          <Overview
            profile={profile}
            hasBaseline={hasBaseline}
            alert={alert}
            comparable={comparable}
            series={series}
            weightHist={weightHist}
            heightHist={heightHist}
            onSaveReview={onSaveReview}
            reviewSaving={reviewSaving}
            onAcknowledge={onAcknowledge}
            onTab={onTab}
            canWrite={canWrite}
            onEditVisit={openVisitEditor}
            onDeleteVisit={setRemoveVisit}
          />
        </div>
      ) : null}

      {tab === "visits" ? (
        <div id="profile-panel-visits" role="tabpanel" aria-labelledby="profile-tab-visits">
          <VisitsTab
            profile={profile}
            canWrite={canWrite}
            onEditVisit={openVisitEditor}
            onDeleteVisit={setRemoveVisit}
          />
        </div>
      ) : null}

      {tab === "progress" ? (
        <div id="profile-panel-progress" role="tabpanel" aria-labelledby="profile-tab-progress">
          <ProgressTab
            profile={profile}
            comparable={comparable}
            series={series}
            metric={metric}
            setMetric={setMetric}
          />
        </div>
      ) : null}

      {tab === "notes" ? (
        <div id="profile-panel-notes" role="tabpanel" aria-labelledby="profile-tab-notes">
          <NotesTab profile={profile} onAddNote={onAddNote} noteSaving={noteSaving} />
        </div>
      ) : null}

      {tab === "ai" ? (
        <div id="profile-panel-ai" role="tabpanel" aria-labelledby="profile-tab-ai">
          <AiDetailsTab profile={profile} inputsOpen={inputsOpen} setInputsOpen={setInputsOpen} qualityOpen={qualityOpen} setQualityOpen={setQualityOpen} />
        </div>
      ) : null}
    </div>
  );
}

function Overview({
  profile,
  hasBaseline,
  alert,
  comparable,
  series,
  weightHist,
  heightHist,
  onSaveReview,
  reviewSaving,
  onAcknowledge,
  onTab,
  canWrite,
  onEditVisit,
  onDeleteVisit,
}: {
  profile: ChildProfile;
  hasBaseline: boolean;
  alert: ReturnType<typeof openAlert>;
  comparable: boolean;
  series: ReturnType<typeof probabilitySeries>;
  weightHist: number[];
  heightHist: number[];
  onSaveReview: (payload: { assessment: string; workflow: string; note: string }) => void;
  reviewSaving?: boolean;
  onAcknowledge?: (id: string) => void;
  onTab: (tab: ProfileTab) => void;
  canWrite?: boolean;
  onEditVisit?: (visit: ProfileVisit) => void;
  onDeleteVisit?: (visit: ProfileVisit) => void;
}) {
  const semantics = getModelOutputDisplayMetadata(profile);
  const visits = profile.visits;
  const latestVisitId = profile.current?.id ?? visits.at(-1)?.id ?? "";
  const [selectedVisitId, setSelectedVisitId] = useState(latestVisitId);

  useEffect(() => {
    setSelectedVisitId(profile.current?.id ?? profile.visits.at(-1)?.id ?? "");
  }, [profile.id, profile.current?.id]);

  const selected = visits.find((v) => v.id === selectedVisitId) ?? visits.at(-1);
  const selectedIndex = selected ? visits.findIndex((v) => v.id === selected.id) : -1;
  const prior = selectedIndex > 0 ? visits[selectedIndex - 1] : undefined;
  const pred = selected?.prediction;
  const prevPred = prior?.prediction;
  const meas = selected?.measurements;
  const prevMeas = prior?.measurements;
  const isLatest = Boolean(selected && selected.id === latestVisitId);
  const [trendCondition, setTrendCondition] = useState(() => defaultTrendCondition(pred));
  const hasConditionProbabilities = visits.some((visit) => visit.prediction?.ga_rgca?.stunting_probability != null);
  const conditionSeries = useMemo(() => probabilitySeries(profile, trendCondition), [profile, trendCondition]);
  const predictedType = displayedMalnutritionType(pred);
  const isNormalType = predictedType === "Normal";
  const hudSeriesCondition = isNormalType ? defaultTrendCondition(pred) : predictedType;
  // Sparkline behind the HUD chip follows the number shown: condition probability, or highest condition risk when type is Normal.
  const typeSeries = useMemo(
    () => (hasConditionProbabilities && hudSeriesCondition ? probabilitySeries(profile, hudSeriesCondition) : null),
    [profile, hasConditionProbabilities, hudSeriesCondition],
  );
  const change = comparable
    ? pred?.ga_rgca
      ? isNormalType
        ? visitProbabilityDeltaPp(highestConditionRisk(pred).probability, highestConditionRisk(prevPred).probability)
        : sameConditionDelta(pred, prevPred)
      : isLatest
        ? profile.risk_change_pp
        : visitProbabilityDeltaPp(pred?.risk ?? null, prevPred?.risk ?? null)
    : null;
  const ageAtVisit = ageMonthsAtVisit(profile.date_of_birth, selected?.visit_date, profile.age_months);
  const visitProgress = isLatest ? profile.progress_display : selected?.progress;
  const visitRv = isLatest ? profile.risk_velocity_pp_month : comparable ? riskVelocityPpMonth(selected?.risk_velocity ?? null) : null;
  const visitVelocity = monthlyVelocityDisplay(visitRv, comparable, prior?.visit_date, selected?.visit_date);
  const latestVelocity = monthlyVelocityDisplay(
    profile.risk_velocity_pp_month,
    comparable,
    profile.previous?.visit_date,
    profile.current?.visit_date,
  );
  const tone = alert ? alertTone(alert.type) : "amber";

  if (!hasBaseline) {
    return (
      <Section title="First visit">
        <p className="font-semibold text-[#0f2744]">No nutritional assessment has been recorded yet.</p>
        <p className="mt-1 text-sm text-[#64748b]">Record the first visit to start this child's clinical record.</p>
        <Link href={`/children/${profile.id}/visits/new`} className="mt-4 inline-block">
          <Button>Record first visit</Button>
        </Link>
      </Section>
    );
  }

  const clinicName = profile.facility?.name || profile.facility?.code;

  return (
    <div className="space-y-4">
      {alert ? (
        <section
          id="clinical-attention"
          className={cn(
            "rounded-2xl border px-5 py-4 shadow-card",
            tone === "red" ? "border-red-200/80 bg-red-50/70" : "border-amber-200/80 bg-amber-50/80",
          )}
        >
          <p className={cn("flex items-center gap-2 text-sm font-semibold", tone === "red" ? "text-red-950" : "text-amber-950")}>
            <AlertTriangle className="h-4 w-4" />
            {alert.headline ?? formatStatus(alert.type)}
            <span className="rounded-md bg-white/70 px-2 py-0.5 text-[11px] font-medium text-[#475569]">
              {formatStatus(alert.status)}
            </span>
          </p>
          <p className="mt-1 text-sm leading-relaxed text-[#3f3f46]">{alert.message}</p>
          {alert.trigger_value?.basis === "predicted_risk_change" ? (
            <p className="mt-1 text-sm text-[#3f3f46]">
              Highest predicted condition risk changed from {formatPercent(alert.trigger_value.previous_risk)} to{" "}
              {formatPercent(alert.trigger_value.current_risk)}. Weight and height changes are shown separately and were not used for this alert.
            </p>
          ) : alert.trigger_value?.previous_risk != null && alert.trigger_value?.current_risk != null ? (
            <p className="mt-1 text-sm text-[#3f3f46]">
              {semantics.score_label} changed from {formatPercent(alert.trigger_value.previous_risk)} to{" "}
              {formatPercent(alert.trigger_value.current_risk)} since the previous assessment.
            </p>
          ) : null}
          <p className="mt-2 text-sm">
            Current longitudinal state: <strong>{progressLabel(profile.progress_display, comparable)}</strong>
          </p>
          <p className="mt-1 text-sm">Clinical review recommended.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a href="#clinician-review">
              <Button className="h-9 rounded-xl text-xs">Review Assessment</Button>
            </a>
            {onAcknowledge && alert.status === "OPEN" ? (
              <Button variant="secondary" className="h-9 rounded-xl text-xs" onClick={() => onAcknowledge(alert.id)}>
                Acknowledge
              </Button>
            ) : null}
          </div>
        </section>
      ) : null}

      {profile.model_warning && comparable === false ? (
        <p className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-950">{profile.model_warning}</p>
      ) : null}

      <div className="grid items-stretch gap-4 lg:grid-cols-[minmax(0,1.45fr)_minmax(280px,0.8fr)]">
      <section id="patient-stage" className="clinical-twin-panel relative h-full overflow-hidden rounded-[28px]">
        <div className="px-4 pb-5 pt-4 sm:px-5">
          <ChildModelHud
            compact
            childId={profile.pseudonymous_id}
            weight={meas?.weight_kg}
            height={meas?.height_cm}
            previousWeight={prevMeas?.weight_kg}
            previousHeight={prevMeas?.height_cm}
            weightHistory={weightHist}
            heightHistory={heightHist}
            probabilityHistory={(typeSeries ?? series)
              .map((s) => s.probability)
              .filter((value): value is number => value != null)}
            ageMonths={ageAtVisit}
            sex={formatStatus(profile.sex)}
            latestAssessment={selected ? formatClinicalDate(selected.visit_date) : null}
            assessmentLabel={isLatest ? "Latest assessment date" : "Assessment date"}
            status={formatNutritionalStatus(displayedMalnutritionType(pred), pred?.severity)}
            statusLabel="Status"
            severity={displayPredictedSeverity(displayedMalnutritionType(pred), pred?.severity) ?? undefined}
            probability={
              isNormalType
                ? formatPercent(highestConditionRisk(pred).probability)
                : formatPercent(predictedTypeChipProbability(pred))
            }
            previousProbability={
              comparable
                ? formatPercent(
                    isNormalType
                      ? highestConditionRisk(prevPred).probability
                      : conditionProbability(prevPred, predictedType),
                  )
                : null
            }
            probabilityChange={comparable ? change : null}
            progress={progressLabel(visitProgress, comparable)}
            riskVelocity={visitVelocity.value}
            scoreLabel={
              isNormalType ? "Highest predicted condition risk" : pred?.ga_rgca ? primaryTypeProbabilityLabel(pred) : semantics.score_label
            }
            scoreTip={
              pred?.ga_rgca
                ? isNormalType
                  ? `Predicted type is Normal. The number shown is the highest of Underweight, Stunting, MAM and SAM, not a Normal-class probability. ${semantics.score_label}: ${formatHighestConditionRisk(pred)}.`
                  : `Probability of the predicted type shown beside it. ${semantics.score_label}: ${formatHighestConditionRisk(pred)}.`
                : semantics.score_description
            }
            velocityLabel={semantics.velocity_label}
            velocityTip={semantics.velocity_description}
            stageFooter={
              visits.length > 0 ? (
                <div
                  className="inline-flex max-w-full flex-wrap justify-center rounded-lg bg-[#f4f7fb] p-1 ring-1 ring-[#e2eaf3]"
                  role="tablist"
                  aria-label="Visit timeline"
                >
                  {visits.map((v) => {
                    const selectedVisit = v.id === selected?.id;
                    return (
                      <button
                        key={v.id}
                        type="button"
                        role="tab"
                        aria-selected={selectedVisit}
                        title={`${formatClinicalDate(v.visit_date)}${displayedMalnutritionType(v.prediction) ? ` · ${formatNutritionalStatus(displayedMalnutritionType(v.prediction), v.prediction?.severity)}` : ""}`}
                        onClick={() => setSelectedVisitId(v.id)}
                        className={cn(
                          "rounded-lg px-5 py-2.5 text-base transition",
                          selectedVisit
                            ? "bg-[#0E3A67] font-medium text-white shadow-sm"
                            : "text-[#475569] hover:bg-white/90 hover:text-[#0A2748]",
                        )}
                      >
                        Visit {v.visit_number}
                      </button>
                    );
                  })}
                </div>
              ) : null
            }
          >
            <ChildModelViewer className="h-full min-h-[320px] md:min-h-[520px]" riskIntensity={pred?.risk} />
            <span className="sr-only">
              Animated three-dimensional patient model with connected clinical measurements. Visual metaphor for progress only, not anatomical imaging.
            </span>
          </ChildModelHud>
        </div>
      </section>

      <Section
        id="longitudinal-progress"
        className="flex h-full flex-col"
        bodyClassName="flex flex-1 flex-col"
        title="Longitudinal progress"
        subtitle={`${hasConditionProbabilities ? `${trendCondition} probability` : semantics.score_label} across completed assessments.`}
      >
        <p className="inline-flex w-fit items-center gap-1.5 rounded-full bg-[#f4f7fb] px-3 py-1 text-sm font-medium text-[#0f2744] ring-1 ring-[#e4ecf4]">
          <ProgressGlyph state={profile.progress_display} />
          {progressLabel(profile.progress_display, comparable)}
        </p>
        {hasConditionProbabilities ? (
          <div className="mt-3 flex flex-wrap gap-1.5" role="tablist" aria-label="Condition trend">
            {TREND_CONDITIONS.map((condition) => (
              <button
                key={condition}
                type="button"
                role="tab"
                aria-selected={trendCondition === condition}
                onClick={() => setTrendCondition(condition)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-medium",
                  trendCondition === condition ? "bg-[#0E3A67] text-white" : "bg-[#f1f5f9] text-[#475569]",
                )}
              >
                {condition}
              </button>
            ))}
          </div>
        ) : null}
        <div className="mt-4 flex min-h-[7.5rem] flex-1 flex-col [&>div]:!h-full [&>div]:min-h-[14rem] [&>div]:flex-1 [&>p]:flex [&>p]:flex-1 [&>p]:items-center [&>p]:rounded-2xl [&>p]:bg-[#f7f9fc] [&>p]:px-5 [&>p]:py-8 [&>p]:leading-relaxed [&>p]:ring-1 [&>p]:ring-[#e7eef6]">
          <TrendChart
            data={hasConditionProbabilities ? conditionSeries : series}
            metric="probability"
            comparable={comparable}
            scoreLabel={hasConditionProbabilities ? `${trendCondition} probability` : semantics.score_label}
          />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <MetricTile
            label={semantics.velocity_label}
            value={latestVelocity.value}
            hint={latestVelocity.hint}
            action={<InfoTip label={`About ${semantics.velocity_label.toLowerCase()}`} text={semantics.velocity_description} />}
          />
          <MetricTile
            label="Since baseline"
            value={comparable ? formatPp(profile.since_baseline_pp) : "Not available"}
            hint={semantics.score_label}
          />
        </div>
        <button type="button" className="mt-4 border-t border-[#eef2f6] pt-3 text-right text-sm font-medium text-[#2563eb]" onClick={() => onTab("progress")}>
          Weight and height trends →
        </button>
      </Section>
      </div>

      <div className="grid items-stretch gap-4 lg:grid-cols-2">
        <CurrentConditionCard
          id="clinical-snapshot"
          eyebrow={`${isLatest ? "Latest visit" : `Visit ${selected?.visit_number ?? "—"}`} · ${selected ? formatClinicalDate(selected.visit_date) : "—"}${clinicName ? ` · ${clinicName}` : ""}`}
          title={isLatest ? "Current condition" : "Condition at this visit"}
          weightKg={meas?.weight_kg}
          heightCm={meas?.height_cm}
          ageMonths={ageAtVisit}
          sex={profile.sex}
          previous={prior ? { weightKg: prevMeas?.weight_kg, heightCm: prevMeas?.height_cm } : null}
          feeding={selected?.feeding}
        />
        <div id="ai-assessment" className="flex h-full flex-col scroll-mt-20">
          {pred ? (
            <PredictionCard prediction={pred} className="h-full" />
          ) : (
            <Section className="flex h-full flex-col" title="AI-assisted assessment" subtitle="Clinical review required.">
              <div className="grid gap-3 sm:grid-cols-2">
                <MetricTile label="Nutritional status" value="—" hint="No prediction stored for this visit." />
                <MetricTile label="Data quality" value={profile.data_quality_label ? formatStatus(profile.data_quality_label) : "—"} />
              </div>
            </Section>
          )}
        </div>
      </div>


      <div className="grid items-stretch gap-4 lg:grid-cols-2">
        <Section
          id="clinician-review"
          className="scroll-mt-20"
          title="Clinician review"
          subtitle="Stored independently of the AI prediction."
        >
          <FieldLabel>Review status</FieldLabel>
          <p className="mt-1 font-semibold text-[#0f2744]">
            {reviewLabel(isLatest ? profile.clinician_review?.status : selected?.review_status)}
          </p>
          <p className="mt-2 text-sm text-[#475569]">
            Predicted type: <span className="font-medium text-[#0f2744]">{formatNutritionalStatus(predictedType, pred?.severity)}</span>
            {predictedTypeChipProbability(pred) != null ? (
              <span className="tabular-nums"> {formatPercent(predictedTypeChipProbability(pred))}</span>
            ) : null}
          </p>
          {pred?.ga_rgca ? (
            <p className="mt-0.5 text-xs text-[#64748b]">
              Highest predicted condition risk: {formatHighestConditionRisk(pred)}
            </p>
          ) : null}
          {isLatest &&
          (profile.clinician_review?.status === "REVIEWED" ||
            profile.clinician_review?.status === "DISAGREED" ||
            profile.clinician_review?.status === "FURTHER_ASSESSMENT") ? (
            <div className="mt-3 space-y-1 text-sm">
              <p>Reviewed by {profile.clinician_review.reviewer_name ?? "clinician"}</p>
              {profile.clinician_review.created_at ? (
                <p className="text-xs text-[#64748b]">{formatClinicalDate(profile.clinician_review.created_at)}</p>
              ) : null}
              <p>Assessment: {profile.clinician_review.assessment}</p>
              {profile.clinician_review.note_excerpt ? <p className="text-[#475569]">{profile.clinician_review.note_excerpt}</p> : null}
            </div>
          ) : isLatest ? (
            <ReviewForm onSave={onSaveReview} saving={reviewSaving} />
          ) : (
            <p className="mt-3 text-sm text-[#64748b]">Review actions apply to the latest visit.</p>
          )}
          {isLatest ? <C3ReassessmentPanel childId={profile.id} /> : null}
        </Section>

        <div className="flex flex-col gap-4">
        <Section
          id="follow-up"
          title={
            <span className="inline-flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              {overdueFollowUp(profile) ? "Follow-up overdue" : "Next follow-up"}
            </span>
          }
        >
          <FollowUpBody profile={profile} />
        </Section>
        <section id="assessment-history" className="overflow-hidden rounded-2xl border border-line bg-white shadow-card">
          <header className="flex items-center justify-between gap-3 border-b border-[#0E3A67] px-5 py-3">
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.14em] text-[#0E3A67]">Assessment history</h2>
            <button
              type="button"
              className="inline-flex shrink-0 items-center gap-1 text-[12px] font-semibold text-[#0E3A67] hover:underline"
              onClick={() => onTab("visits")}
            >
              Full visit record
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </button>
          </header>
          <div className={profile.visits.length > 6 ? "max-h-64 overflow-auto" : undefined}>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[#e8eef5] bg-[#f7f9fc] text-[10px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">
                  <th className="whitespace-nowrap px-5 py-2.5">Visit</th>
                  <th className="whitespace-nowrap px-4 py-2.5">Date</th>
                  <th className="whitespace-nowrap px-4 py-2.5">Predicted type</th>
                  <th className="whitespace-nowrap px-4 py-2.5">Probability</th>
                  <th className="whitespace-nowrap px-4 py-2.5">Review</th>
                  <th className="px-3 py-2.5"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {[...profile.visits].reverse().map((v) => {
                  const predictedType = formatNutritionalStatus(displayedMalnutritionType(v.prediction), v.prediction?.severity);
                  const selectedRow = v.id === selected?.id;
                  const isLatest = v.id === latestVisitId;
                  return (
                    <tr
                      key={v.id}
                      className={cn(
                        "border-b border-[#eef2f7] last:border-0",
                        selectedRow ? "bg-[#f4f8fb]" : "hover:bg-[#f8fafc]",
                      )}
                    >
                      <td className="whitespace-nowrap px-5 py-3 font-semibold tabular-nums text-[#0A2748]">
                        <button type="button" onClick={() => setSelectedVisitId(v.id)}>
                          V{v.visit_number}
                        </button>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-[#334155]">
                        <button type="button" onClick={() => setSelectedVisitId(v.id)}>
                          {formatClinicalDate(v.visit_date)}
                        </button>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-semibold text-[#0A2748]">{predictedType}</td>
                      <td className="whitespace-nowrap px-4 py-3 tabular-nums text-[#0A2748]">
                        {formatPercent(predictedTypeChipProbability(v.prediction))}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        {v.review_status === "AWAITING_REVIEW" ? (
                          <button
                            type="button"
                            className="rounded-md bg-amber-50 px-2 py-0.5 text-[12px] font-semibold text-amber-900 ring-1 ring-amber-200 hover:bg-amber-100"
                            onClick={() => {
                              setSelectedVisitId(v.id);
                              window.requestAnimationFrame(() => {
                                document.getElementById("clinician-review")?.scrollIntoView({ behavior: "smooth", block: "start" });
                              });
                            }}
                          >
                            Awaiting review
                          </button>
                        ) : (
                          <span className="text-[#334155]">{reviewLabel(v.review_status)}</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-right">
                        {canWrite && isLatest && onEditVisit && onDeleteVisit ? (
                          <RecordActions
                            onEdit={() => onEditVisit(v)}
                            onDelete={() => onDeleteVisit(v)}
                            editLabel={`Edit visit ${v.visit_number}`}
                            deleteLabel={`Remove visit ${v.visit_number}`}
                          />
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
        </div>
      </div>

    </div>
  );
}

export function AdvancedAiSummary({
  profile,
  comparable,
}: {
  profile: ChildProfile;
  comparable: boolean;
}) {
  const semantics = getModelOutputDisplayMetadata(profile);
  const m = profile.model;
  const projectedCount = profile.visits.filter((v) => v.projection != null).length;
  const visitCount = profile.visits.length;
  const projectionVersion =
    profile.current?.projection_version ??
    [...profile.visits].reverse().find((v) => v.projection_version)?.projection_version ??
    semantics.projection_version ??
    null;

  return (
    <section id="advanced-ai" aria-labelledby="latent-trajectory-title">
      <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-card">
        <div className="grid lg:grid-cols-[minmax(0,1.55fr)_minmax(260px,0.72fr)] lg:items-stretch lg:pb-6">
          <div className="flex items-start justify-between gap-4 px-5 pt-5 sm:px-6 sm:pt-6 lg:col-span-2 lg:pb-5">
            <div className="min-w-0">
            <h2 id="latent-trajectory-title" className="text-lg font-semibold tracking-tight text-[#0f2744]">
              Latent representation trajectory
            </h2>
            <p className="mt-1 max-w-xl text-sm leading-relaxed text-[#64748b]">{semantics.projection_description}</p>

            {profile.model_warning ? (
              <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-950">{profile.model_warning}</p>
            ) : null}
            {!comparable ? (
              <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-950">
                Longitudinal comparison unavailable. The active model or embedding space changed between assessments.
              </p>
            ) : null}
            </div>
            <ExplainabilityTrigger profile={profile} className="shrink-0" />
          </div>

          <div className="px-5 pb-5 pt-5 sm:px-6 sm:pb-6 lg:col-start-1 lg:row-start-2 lg:py-0">
              {projectedCount === 0 ? (
                <div className="relative flex min-h-[22rem] items-center justify-center overflow-hidden rounded-2xl bg-[#f7f9fc] ring-1 ring-[#e7eef6]">
                  <div className="pointer-events-none absolute inset-6 rounded-xl border border-dashed border-[#d7e2ee]" aria-hidden />
                  <div className="pointer-events-none absolute left-6 right-6 top-1/2 border-t border-[#e4edf6]" aria-hidden />
                  <div className="pointer-events-none absolute bottom-6 left-1/2 top-6 border-l border-[#e4edf6]" aria-hidden />
                  <div className="relative max-w-sm px-8 text-center">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#94a3b8]">Projection</p>
                    <p className="mt-2 text-xl font-semibold tracking-tight text-[#0f2744]">No stored projection yet</p>
                    <p className="mt-2 text-sm leading-relaxed text-[#64748b]">
                      A point is placed here after a visit stores an embedding. Record the next visit to draw the path.
                    </p>
                  </div>
                </div>
              ) : (
                <LatentTrajectory visits={profile.visits} />
              )}
          </div>

          <aside className="border-t border-line bg-[#f7f9fc] p-4 sm:p-5 lg:col-start-2 lg:row-start-2 lg:h-auto lg:self-stretch lg:border-l lg:border-t-0">
            <div className="rounded-2xl bg-white p-4 ring-1 ring-[#e7eef6]">
              <div className="space-y-3.5">
                <div>
                  <FieldLabel>Active model</FieldLabel>
                  <p className="mt-1 truncate text-sm font-semibold text-[#0f2744]" title={m?.label ?? undefined}>
                    {m?.label ?? "—"}
                  </p>
                </div>
                <div>
                  <FieldLabel>Model type</FieldLabel>
                  <p className="mt-1 text-sm font-semibold text-[#0f2744]">{architectureLabel(m?.architecture)}</p>
                </div>
                <div>
                  <FieldLabel>{semantics.projection_label}</FieldLabel>
                  <p className="mt-1 break-all text-sm font-semibold leading-snug text-[#0f2744]" title={projectionVersion ?? undefined}>
                    {projectionVersion ?? "—"}
                  </p>
                </div>
                <div className="flex items-end justify-between gap-3 border-t border-[#eef2f6] pt-3">
                  <FieldLabel>Projected visits</FieldLabel>
                  <p className="text-sm font-semibold tabular-nums text-[#0f2744]">
                    {projectedCount} of {visitCount}
                  </p>
                </div>
                <div className="border-t border-[#eef2f6] pt-3">
                  <FieldLabel>Recorded visits</FieldLabel>
                  <ul className="mt-2 space-y-2">
                    {[...profile.visits].reverse().map((visit) => (
                      <li key={visit.id} className="flex items-center justify-between gap-3 rounded-xl bg-[#f7f9fc] px-3 py-3 ring-1 ring-[#e7eef6]">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-[#0f2744]">Visit {visit.visit_number}</p>
                          <p className="mt-0.5 text-xs text-[#64748b]">{formatClinicalDate(visit.visit_date)}</p>
                        </div>
                        <span
                          className={cn(
                            "shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium",
                            visit.projection ? "bg-[#e8f6ef] text-[#047857]" : "bg-[#eef2f6] text-[#64748b]",
                          )}
                        >
                          {visit.projection ? "Stored" : "Not stored"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}

function overdueFollowUp(profile: ChildProfile) {
  return profile.follow_up_overdue_days != null;
}

function C3ReassessmentPanel({ childId }: { childId: string }) {
  const { data } = useQuery({
    queryKey: ["c3-reassessment", childId],
    queryFn: () =>
      api<{
        connected: boolean;
        configured: boolean;
        message?: string | null;
        request?: {
          status: string;
          requested_at?: string | null;
          result_url?: string | null;
          queued_offline?: boolean;
        } | null;
      }>(`/children/${childId}/c3-reassessment`),
    staleTime: 15_000,
  });
  if (!data?.request) {
    return (
      <div className="mt-4 rounded-xl border border-dashed border-line bg-[#f8fafc] px-3 py-2 text-xs text-[#64748b]">
        Intervention reassessment · Component 3 · {data?.connected ? "Ready" : "Not connected"}
      </div>
    );
  }
  const req = data.request;
  return (
    <div className="mt-4 rounded-xl border border-line bg-white px-3 py-3 text-sm" data-testid="c3-reassessment-panel">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#64748b]">Intervention reassessment</p>
      <p className="mt-1 font-medium text-[#0f2744]">Component 3</p>
      <p className="mt-2 text-xs text-[#64748b]">
        Requested {req.requested_at ? formatClinicalDate(req.requested_at) : "—"}
      </p>
      <p className="mt-1 text-sm text-[#0f2744]">
        Status · {req.status === "COMPLETED" ? "Available" : req.queued_offline ? "Queued" : req.status}
      </p>
      {data.message ? <p className="mt-2 text-xs text-[#b45309]">{data.message}</p> : null}
      {req.status === "COMPLETED" && req.result_url ? (
        <a className="mt-2 inline-block text-sm font-medium text-[#2563eb]" href={req.result_url} target="_blank" rel="noreferrer">
          Open Component 3 result
        </a>
      ) : null}
    </div>
  );
}

function ReviewForm({
  onSave,
  saving,
}: {
  onSave: (payload: { assessment: string; workflow: string; note: string }) => void;
  saving?: boolean;
}) {
  const [assessment, setAssessment] = useState("");
  const [workflow, setWorkflow] = useState("monitor");
  const [note, setNote] = useState("");
  return (
    <div className="mt-4 space-y-3">
      <p className="text-sm font-medium text-[#0f2744]">Do you agree with the AI-assisted assessment?</p>
      <div className="flex flex-wrap gap-2">
        {[
          { id: "agree", label: "Agree" },
          { id: "disagree", label: "Disagree" },
          { id: "uncertain", label: "Further assessment required" },
        ].map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => setAssessment(opt.id)}
            className={pillClass(assessment === opt.id, "sm")}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <label className="block text-xs font-medium text-[#64748b]">
        Workflow
        <select
          className="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm"
          value={workflow}
          onChange={(e) => setWorkflow(e.target.value)}
        >
          <option value="monitor">Continue monitoring</option>
          <option value="nutrition">Nutrition review</option>
          <option value="investigate">Further investigation</option>
          <option value="refer">Refer</option>
          <option value="reassess">Request intervention reassessment</option>
        </select>
      </label>
      <label className="block text-xs font-medium text-[#64748b]">
        Clinical note
        <Textarea className="mt-1" rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Document clinical reasoning. This is not sent to the model." />
      </label>
      <Button className="h-9 text-xs" disabled={!assessment || !note.trim() || saving} onClick={() => onSave({ assessment, workflow, note })}>
        {saving ? "Saving…" : "Save Review"}
      </Button>
    </div>
  );
}

function FollowUpBody({ profile }: { profile: ChildProfile }) {
  const overdue = overdueFollowUp(profile);
  const suggested = profile.follow_up_status === "SUGGESTED";
  return (
    <div className="space-y-3 text-sm">
      <p className={cn("text-2xl font-semibold tabular-nums", overdue ? "text-clinical-warning" : "text-[#0f2744]")}>
        {profile.next_follow_up ? formatClinicalDate(profile.next_follow_up) : "Not scheduled"}
      </p>
      {profile.facility?.name ? <p className="text-[#64748b]">{profile.facility.name}</p> : null}
      <p className="text-[#64748b]">
        {overdue
          ? `Overdue by ${profile.follow_up_overdue_days} days`
          : suggested
            ? "Suggested"
            : profile.follow_up_status
              ? formatStatus(profile.follow_up_status)
              : "—"}
      </p>
      <FollowUpSchedulePanel
        compact
        childId={profile.id}
        followUpId={profile.follow_up_id}
        nextFollowUp={profile.next_follow_up}
        followUpStatus={profile.follow_up_status}
      />
    </div>
  );
}

function recordChipClass(kind: "type" | "severity" | "review", value: string) {
  if (value === "—") return "text-[#94a3b8]";
  if (kind === "type") {
    if (value.includes("SAM")) return "bg-red-50 text-red-800 ring-1 ring-red-100";
    if (value.includes("MAM")) return "bg-orange-50 text-orange-900 ring-1 ring-orange-100";
    if (value.includes("Stunting")) return "bg-violet-50 text-violet-900 ring-1 ring-violet-100";
    if (value.includes("Underweight")) return "bg-amber-50 text-amber-900 ring-1 ring-amber-100";
    if (value === "Normal") return "bg-emerald-50 text-emerald-900 ring-1 ring-emerald-100";
    return "bg-slate-100 text-slate-800 ring-1 ring-slate-200";
  }
  if (kind === "severity") {
    if (value.toLowerCase().includes("severe")) return "bg-red-50 text-red-800 ring-1 ring-red-100";
    if (value.toLowerCase().includes("moderate")) return "bg-orange-50 text-orange-900 ring-1 ring-orange-100";
    if (value.toLowerCase().includes("mild")) return "bg-amber-50 text-amber-900 ring-1 ring-amber-100";
    return "bg-slate-100 text-slate-700 ring-1 ring-slate-200";
  }
  if (value === "Reviewed") return "bg-emerald-50 text-emerald-900 ring-1 ring-emerald-100";
  if (value === "Awaiting review" || value === "In review") return "bg-amber-50 text-amber-900 ring-1 ring-amber-100";
  if (value === "Disagreed") return "bg-red-50 text-red-800 ring-1 ring-red-100";
  return "bg-slate-100 text-slate-700 ring-1 ring-slate-200";
}

function RecordChip({ kind, value }: { kind: "type" | "severity" | "review"; value: string }) {
  if (value === "—") return <span className="text-[#94a3b8]">—</span>;
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold", recordChipClass(kind, value))}>
      {value}
    </span>
  );
}

function VisitsTab({
  profile,
  canWrite,
  onEditVisit,
  onDeleteVisit,
}: {
  profile: ChildProfile;
  canWrite?: boolean;
  onEditVisit?: (visit: ProfileVisit) => void;
  onDeleteVisit?: (visit: ProfileVisit) => void;
}) {
  const latestVisitId = profile.current?.id ?? profile.visits.at(-1)?.id;
  const visitCount = profile.visits.length;
  return (
    <section className="overflow-hidden rounded-[24px] border border-[#d7e4f2] bg-white shadow-[0_12px_32px_-24px_rgba(10,39,72,0.5)]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e8eef5] bg-[linear-gradient(180deg,#f7fbfd_0%,#ffffff_100%)] px-5 py-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#EAF7F6] text-[#0f766e]">
            <ClipboardList className="h-5 w-5" aria-hidden />
          </span>
          <h2 className="text-lg font-semibold tracking-tight text-[#0A2748]">Visit record</h2>
        </div>
        <span className="rounded-full bg-[#eef4fa] px-3 py-1 text-xs font-semibold tabular-nums text-[#0E3A67] ring-1 ring-[#d7e4f2]">
          {visitCount} {visitCount === 1 ? "visit" : "visits"}
        </span>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead>
            <tr className="border-b border-[#e8eef5] bg-[#f8fafc] text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">
              <th className="px-5 py-3">Visit</th>
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Weight</th>
              <th className="px-5 py-3">Height</th>
              <th className="px-5 py-3">Predicted type</th>
              <th className="px-5 py-3">Severity</th>
              <th className="px-5 py-3">Type probability</th>
              <th className="px-5 py-3">Highest condition risk</th>
              <th className="px-5 py-3">Review</th>
              <th className="px-5 py-3"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {profile.visits.map((v) => {
              const predictedType = formatNutritionalStatus(displayedMalnutritionType(v.prediction), v.prediction?.severity);
              const severity = displayPredictedSeverity(displayedMalnutritionType(v.prediction), v.prediction?.severity) ?? "—";
              const review = reviewLabel(v.review_status);
              const isLatest = v.id === latestVisitId;
              return (
                <tr
                  key={v.id}
                  className={cn(
                    "border-b border-[#eef2f7] last:border-0",
                    isLatest ? "bg-[#f5f9fc]" : "bg-white hover:bg-[#f8fafc]",
                  )}
                >
                  <td className="px-5 py-3.5">
                    <span className="inline-flex min-w-[2.5rem] items-center justify-center rounded-full bg-[#0E3A67] px-2.5 py-1 text-[11px] font-semibold tabular-nums text-white">
                      V{v.visit_number}
                    </span>
                    {isLatest ? (
                      <span className="ml-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#3E75B8]">Latest</span>
                    ) : null}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="inline-flex items-center gap-1.5 text-[#0A2748]">
                      <Calendar className="h-3.5 w-3.5 text-[#94a3b8]" aria-hidden />
                      {formatClinicalDate(v.visit_date)}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 tabular-nums text-[#0A2748]">
                    {v.measurements?.weight_kg != null ? (
                      <>
                        {v.measurements.weight_kg} <span className="text-xs text-[#94a3b8]">kg</span>
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-5 py-3.5 tabular-nums text-[#0A2748]">
                    {v.measurements?.height_cm != null ? (
                      <>
                        {v.measurements.height_cm} <span className="text-xs text-[#94a3b8]">cm</span>
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <RecordChip kind="type" value={predictedType} />
                  </td>
                  <td className="px-5 py-3.5">
                    <RecordChip kind="severity" value={severity} />
                  </td>
                  <td className="px-5 py-3.5 font-semibold tabular-nums text-[#0A2748]">
                    {formatPercent(predictedTypeChipProbability(v.prediction))}
                  </td>
                  <td className="px-5 py-3.5 tabular-nums text-[#334155]">
                    {v.prediction ? formatHighestConditionRisk(v.prediction) : "—"}
                  </td>
                  <td className="px-5 py-3.5">
                    <RecordChip kind="review" value={review} />
                  </td>
                  <td className="px-3 py-3.5 text-right">
                    {canWrite && isLatest && onEditVisit && onDeleteVisit ? (
                      <RecordActions
                        onEdit={() => onEditVisit(v)}
                        onDelete={() => onDeleteVisit(v)}
                        editLabel={`Edit visit ${v.visit_number}`}
                        deleteLabel={`Remove visit ${v.visit_number}`}
                      />
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ProgressTab({
  profile,
  comparable,
  series,
  metric,
  setMetric,
}: {
  profile: ChildProfile;
  comparable: boolean;
  series: ReturnType<typeof probabilitySeries>;
  metric: TrendMetric;
  setMetric: (m: TrendMetric) => void;
}) {
  const semantics = getModelOutputDisplayMetadata(profile);
  const [trendCondition, setTrendCondition] = useState(() => defaultTrendCondition(profile.current?.prediction));
  const hasConditionProbabilities = profile.visits.some((visit) => visit.prediction?.ga_rgca?.stunting_probability != null);
  const conditionSeries = useMemo(() => probabilitySeries(profile, trendCondition), [profile, trendCondition]);
  const chartSeries = metric === "probability" && hasConditionProbabilities ? conditionSeries : series;
  const latestVelocity = monthlyVelocityDisplay(
    profile.risk_velocity_pp_month,
    comparable,
    profile.previous?.visit_date,
    profile.current?.visit_date,
  );
  return (
    <div className="space-y-4">
      <Section title="Recorded visits in motion" subtitle="Each point is a stored visit. Nothing is interpolated between visits.">
        <VisitMotionTimeline profile={profile} />
      </Section>
      <Section
        title="Trends"
        actions={
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["probability", semantics.score_label],
                ["weight", "Weight"],
                ["height", "Height"],
              ] as const
            ).map(([id, label]) => (
              <button key={id} type="button" onClick={() => setMetric(id)} className={pillClass(metric === id, "sm")}>
                {label}
              </button>
            ))}
          </div>
        }
      >
        {metric === "probability" && hasConditionProbabilities ? (
          <div className="mb-3 flex flex-wrap gap-1.5" role="tablist" aria-label="Condition trend">
            {TREND_CONDITIONS.map((condition) => (
              <button
                key={condition}
                type="button"
                role="tab"
                aria-selected={trendCondition === condition}
                onClick={() => setTrendCondition(condition)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-medium",
                  trendCondition === condition ? "bg-[#0E3A67] text-white" : "bg-[#f1f5f9] text-[#475569]",
                )}
              >
                {condition}
              </button>
            ))}
          </div>
        ) : null}
        <TrendChart
          data={chartSeries}
          metric={metric}
          comparable={comparable}
          scoreLabel={metric === "probability" && hasConditionProbabilities ? `${trendCondition} probability` : semantics.score_label}
        />
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <MetricTile label={semantics.velocity_label} value={latestVelocity.value} hint={latestVelocity.hint} />
          <MetricTile
            label="Progress"
            value={
              <span className="inline-flex items-center gap-1.5">
                <ProgressGlyph state={profile.progress_display} />
                {progressLabel(profile.progress_display, comparable)}
              </span>
            }
          />
        </div>
      </Section>
    </div>
  );
}

function NotesTab({
  profile,
  onAddNote,
  noteSaving,
}: {
  profile: ChildProfile;
  onAddNote: (body: string) => void;
  noteSaving?: boolean;
}) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [removeId, setRemoveId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function saveEdit() {
    if (!editingId || !draft.trim()) return;
    setBusy(true);
    try {
      await api(`/notes/${editingId}`, { method: "PATCH", body: JSON.stringify({ body: draft.trim() }) });
      await queryClient.invalidateQueries({ queryKey: ["child", profile.id] });
      toast.success("Clinical note updated.");
      setEditingId(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to update this note");
    } finally {
      setBusy(false);
    }
  }

  async function removeNote() {
    if (!removeId) return;
    setBusy(true);
    try {
      await api(`/notes/${removeId}`, { method: "DELETE" });
      await queryClient.invalidateQueries({ queryKey: ["child", profile.id] });
      toast.success("Clinical note removed.");
      setRemoveId(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to remove this note");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Section title="Clinical notes" subtitle="Notes are never sent to the prediction model.">
      <div className="space-y-4">
        <Textarea rows={4} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a clinical note" />
        <Button onClick={() => onAddNote(note)} disabled={!note.trim() || noteSaving}>
          Save note
        </Button>
        {profile.notes.length === 0 ? <EmptyState title="No clinical notes yet." /> : null}
        <ConfirmAction
          open={Boolean(removeId)}
          title="Remove note"
          message="This clinical note will be removed. It is not used by the assessment model."
          confirmLabel="Remove note"
          busy={busy}
          onCancel={() => setRemoveId(null)}
          onConfirm={removeNote}
        />
        {profile.notes.map((n) => (
          <article key={n.id} className="rounded-xl bg-[#f8fafc] p-3 text-sm ring-1 ring-line/70">
            <div className="flex items-start justify-between gap-3">
              {editingId === n.id ? (
                <Textarea className="flex-1" rows={3} value={draft} onChange={(event) => setDraft(event.target.value)} />
              ) : (
                <p className="min-w-0 flex-1">{n.body}</p>
              )}
              <RecordActions
                onEdit={() => {
                  setEditingId(n.id);
                  setDraft(n.body);
                }}
                onDelete={() => setRemoveId(n.id)}
                editLabel="Edit clinical note"
                deleteLabel="Remove clinical note"
              />
            </div>
            {editingId === n.id ? (
              <div className="mt-2 flex gap-2">
                <Button className="h-8 text-xs" disabled={busy || !draft.trim()} onClick={() => void saveEdit()}>
                  Save note
                </Button>
                <Button className="h-8 text-xs" variant="secondary" disabled={busy} onClick={() => setEditingId(null)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <p className="mt-1 text-xs text-[#64748b]">{new Date(n.created_at).toLocaleString()}</p>
            )}
          </article>
        ))}
      </div>
    </Section>
  );
}

function AiDetailsTab({
  profile,
  inputsOpen,
  setInputsOpen,
  qualityOpen,
  setQualityOpen,
}: {
  profile: ChildProfile;
  inputsOpen: boolean;
  setInputsOpen: (v: boolean) => void;
  qualityOpen: boolean;
  setQualityOpen: (v: boolean) => void;
}) {
  const m = profile.model;
  const semantics = getModelOutputDisplayMetadata(profile);
  const ga = profile.current?.prediction?.ga_rgca;
  const detected = ga?.detected_conditions?.length ? ga.detected_conditions.join(", ") : "—";
  return (
    <div className="space-y-4">
      {ga ? (
        <Section
          className="border-white/10 bg-[#102A4C] text-white [&_h2]:text-white [&_header]:border-white/10 [&_header_p]:text-white/70"
          title="Prediction interpretation"
          subtitle="Stored GA-RGCA-v4-Rolling-RSL outputs. Research decision-support prototype. Clinician confirmation required."
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Meta label="Predicted malnutrition type" value={formatNutritionalStatus(displayedMalnutritionType(profile.current?.prediction), ga.severity)} />
            <Meta label="Detected conditions" value={detected} />
            <Meta label="Acute malnutrition status" value={ga.acute_status ?? "—"} />
            {displayPredictedSeverity(displayedMalnutritionType(profile.current?.prediction), ga.severity) ? (
              <Meta label="Overall severity" value={displayPredictedSeverity(displayedMalnutritionType(profile.current?.prediction), ga.severity)!} />
            ) : null}
          </div>
          <p className="mt-3 text-sm text-white/70">
            Acute status represents the model&apos;s Normal/MAM/SAM acute-malnutrition output and is separate from Underweight and Stunting prediction. Modality reliability is not feature importance.
          </p>
          <div className="mt-4 grid gap-3">
            <ProbabilityBar label="Underweight" value={ga.underweight_probability} tone="gold" />
            <ProbabilityBar label="Stunting" value={ga.stunting_probability} tone="amber" />
            <ProbabilityBar label="MAM" value={ga.mam_probability} tone="orange" />
            <ProbabilityBar label="SAM" value={ga.sam_probability} tone="coral" />
          </div>
          {ga.binary_thresholds ? (
            <div className="mt-4 space-y-2 text-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">Decision Thresholds</p>
              <p>Underweight probability: {formatPercent(ga.underweight_probability)}</p>
              <p>Underweight decision threshold: {formatPercent(ga.binary_thresholds.Underweight)}</p>
              <p>Decision: {ga.underweight_positive ? "Positive" : "Negative"}</p>
              <p>Stunting probability: {formatPercent(ga.stunting_probability)}</p>
              <p>Stunting threshold: {formatPercent(ga.binary_thresholds.Stunting)}</p>
              <p>Decision: {ga.stunting_positive ? "Positive" : "Negative"}</p>
            </div>
          ) : null}
          {ga.modality_reliability ? (
            <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <li className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">
                Growth anchor · Reliability {formatPercent(ga.modality_reliability.history)}
                {completenessLabel(ga.input_snapshot?.values, ["Hist_2025_Age_months", "Hist_2025_Height_cm", "Hist_2025_Weight_kg", "Birth_Weight_g", "Hist_2025_MAM", "Hist_2025_SAM", "Hist_2025_Underweight", "Hist_2025_Stunting"])}
              </li>
              <li className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">
                Socioeconomic · Reliability {formatPercent(ga.modality_reliability.socioeconomic)}
                {completenessLabel(ga.input_snapshot?.values, ["Maternal_Age_2025_years", "Family_Size", "Maternal_Education", "Household_Income_Range", "Father_Occupation", "Mother_Occupation"])}
              </li>
              <li className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">
                Feeding · Reliability {formatPercent(ga.modality_reliability.feeding)}
                {completenessLabel(ga.input_snapshot?.values, ["Exclusive_Breastfeeding", "Breastfeeding_Duration", "Complementary_Feeding_Timing", "Meal_Frequency_per_Day", "Dietary_Diversity"])}
              </li>
              <li className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">
                Supplementation · Reliability {formatPercent(ga.modality_reliability.supplementation)}
                {completenessLabel(ga.input_snapshot?.values, ["Triposha_Supplementation", "Vitamin_Supplementation"])}
              </li>
            </ul>
          ) : null}
          <p className="mt-3 text-sm text-[#64748b]">
            Modality reliability reflects how the GA-RGCA fusion mechanism weighted the quality and availability of each information source for this prediction. It is not a causal explanation or feature importance measure.
          </p>
        </Section>
      ) : null}
      <Section title="Research Limitations" subtitle="Prototype constraints. This is not a clinical validation statement.">
        <ul className="list-disc space-y-1 pl-5 text-sm text-[#64748b]">
          <li>Research decision-support prototype.</li>
          <li>Clinician confirmation required.</li>
          <li>One historical 12-month origin validated.</li>
          <li>Repeated rolling-origin prospective validation required.</li>
          <li>External prospective validation required.</li>
          <li>Context timing limitations: household, feeding and supplementation context may not align exactly with the measurement date.</li>
          <li>Incident SAM underpowered.</li>
          <li>Applicability/OOD signal not externally validated.</li>
          <li>Modality reliability is not causal explanation.</li>
          {ga?.applicability?.message ? <li>{ga.applicability.message}</li> : null}
        </ul>
      </Section>
      <Section
        title="AI Details"
        subtitle="Stored model outputs for this visit in clinical language. Clinical review required."
        actions={<ExplainabilityTrigger profile={profile} label="Open AI Details" />}
      >
        <p className="text-sm text-[#475569]">
          Prediction, severity, model uncertainty, similarity to the training population, modality reliability and model identity. Feature attributions are not generated here.
        </p>
      </Section>
      <Section title="Model information">
        <div className="grid gap-3 sm:grid-cols-2">
          <Meta label="Active model" value={m?.label ?? "—"} mono />
          <Meta label="Model type" value={architectureLabel(m?.architecture)} />
          <Meta label="Prediction task" value={semantics.prediction_task_label} />
          <Meta label="Embedding dimension" value={m?.embedding_dimension != null ? String(m.embedding_dimension) : "—"} />
          <Meta label="Calibration" value={m?.calibration_version ?? profile.current?.prediction?.calibration_version ?? "—"} />
          <Meta label="Model assessment mode" value={runtimeModeLabel(profile.current?.prediction?.mode)} />
          <Meta label="Feature schema" value={m?.feature_schema_version ?? "—"} />
          <Meta label="Embedding space" value={m?.embedding_space_id ?? "—"} />
          <Meta label={semantics.projection_label} value={profile.current?.projection_version ?? semantics.projection_version ?? "—"} mono />
          <Meta label="Score kind" value={semantics.score_label} />
        </div>
      </Section>
      <Section title="Data inputs" subtitle="Counts from the stored latest visit. Unavailable is not treated as No.">
        <div className="space-y-3 text-sm">
          {profile.modalities ? (
            <ul className="grid gap-2 sm:grid-cols-2">
              <li className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">Anthropometric · {profile.modalities.anthropometric.available} of {profile.modalities.anthropometric.total} fields available</li>
              <li className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">Socioeconomic · {profile.modalities.socioeconomic.available} of {profile.modalities.socioeconomic.total} fields available</li>
              <li className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">Dietary · {profile.modalities.dietary.available} of {profile.modalities.dietary.total} fields available</li>
              <li className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">Maternal / child health · {profile.modalities.maternal_child_health.available} of {profile.modalities.maternal_child_health.total} fields available</li>
            </ul>
          ) : (
            <p className="text-[#64748b]">No visit inputs stored.</p>
          )}
          <button type="button" className="font-medium text-[#2563eb]" onClick={() => setInputsOpen(!inputsOpen)}>
            {inputsOpen ? "Hide submitted inputs" : "View submitted inputs"}
          </button>
          {inputsOpen && profile.latest_inputs ? (
            <pre className="overflow-x-auto rounded-xl bg-[#f8fafc] p-3 text-xs ring-1 ring-line/70">{JSON.stringify(profile.latest_inputs, null, 2)}</pre>
          ) : null}
          <button type="button" className="block font-medium text-[#2563eb]" onClick={() => setQualityOpen(!qualityOpen)}>
            Data quality details
          </button>
          {qualityOpen && profile.modalities ? (
            <ul className="grid gap-1 text-xs sm:grid-cols-2">
              {profile.modalities.anthropometric.fields.map((f) => (
                <li key={f.field}>
                  {f.available ? "✓" : "⚠"} {f.field.replaceAll("_", " ")}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </Section>
      <p className="text-center">
        <Link href="/research/models" className="inline-flex items-center gap-1 text-sm text-[#2563eb]">
          Research model registry <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </p>
    </div>
  );
}

function completenessLabel(values: Record<string, unknown> | undefined, fields: string[]) {
  if (!values) return null;
  const recorded = fields.filter((field) => values[field] != null && values[field] !== "").length;
  return ` · Completeness ${recorded} of ${fields.length} fields recorded`;
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-xl bg-[#f8fafc] px-4 py-3 ring-1 ring-line/70">
      <FieldLabel>{label}</FieldLabel>
      <p className={cn("mt-1 text-sm text-[#0f2744]", mono && "font-mono text-xs")}>{value}</p>
    </div>
  );
}
