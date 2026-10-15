"use client";

import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, ChevronRight, Info, Search } from "lucide-react";
import { Suspense, useEffect, useMemo, useState } from "react";
import { api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Input, Select } from "@/components/common/field";
import { RegisterChildModal } from "@/components/component1/register-child-modal";
import { ConfirmAction, RecordActions } from "@/components/component1/record-actions";
import { toast } from "sonner";
import { displayedConditionList, displayedMalnutritionType } from "@/data/child-profile";
import { formatClinicalDate, formatPercent, formatNutritionalStatus, formatStatus, clinicalPhrase, ageLabel, cn } from "@/utils/utils";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";

type ClinicalAttention = { type: string; label: string; severity?: string; status?: string };

type Item = {
  id: string;
  pseudonymous_id: string;
  full_name?: string | null;
  age_months: number;
  sex: string;
  responsible_team?: string | null;
  last_visit?: string;
  latest_visit_number?: number | null;
  visit_count: number;
  assessment_count: number;
  has_assessment: boolean;
  current_status?: string;
  predicted_malnutrition_type?: string | null;
  detected_conditions?: string[] | null;
  score_kind?: string;
  severity?: string;
  current_risk?: number;
  previous_risk?: number | null;
  risk_change_pp?: number | null;
  probability_label?: string;
  prediction_confidence?: string | null;
  risk_velocity_pp_month?: number | null;
  risk_velocity_available?: boolean;
  progress?: string;
  progress_display?: string;
  progress_warning?: string | null;
  probability_history?: number[];
  clinical_attention?: ClinicalAttention[];
  clinician_review_status?: string;
  next_follow_up?: string;
  follow_up_display_status?: string;
  follow_up_overdue_days?: number | null;
  facility_code?: string;
  measurements?: {
    weight_kg?: number | null;
    height_cm?: number | null;
    muac_cm?: number | null;
    previous_weight_kg?: number | null;
    previous_muac_cm?: number | null;
  } | null;
  requires_attention?: boolean;
};

type Summary = {
  children_under_monitoring: number;
  requiring_clinical_attention: number;
  awaiting_clinical_review: number;
  follow_up_upcoming: number;
  follow_up_overdue: number;
  model_is_demo: boolean;
};

type ListResponse = {
  items: Item[];
  total: number;
  page: number;
  page_size: number;
  summary: Summary;
};

const PROGRESS_LABELS: Record<string, string> = {
  improving: "Improving",
  stable: "Stable",
  stagnating: "Limited improvement",
  deteriorating: "Deteriorating",
  incompatible_model: "Trend comparison unavailable",
  insufficient_history: "Insufficient history",
  not_available: "Not available",
  baseline: "Insufficient history",
};

const REVIEW_LABELS: Record<string, string> = {
  AWAITING_REVIEW: "Awaiting review",
  IN_REVIEW: "In review",
  REVIEWED: "Reviewed",
  DISAGREED: "Disagreed with assessment",
  FURTHER_ASSESSMENT: "Further assessment required",
  NOT_REQUIRED: "Review not required",
};

function progressTone(display?: string | null) {
  if (display === "improving") return "bg-emerald-50/30";
  if (display === "deteriorating") return "bg-red-50/20";
  if (display === "stagnating") return "bg-amber-50/20";
  if (display === "incompatible_model") return "bg-slate-50/40";
  return "";
}

function progressBadgeClass(display?: string | null) {
  if (display === "improving") return "bg-emerald-50 text-emerald-800 ring-emerald-200";
  if (display === "deteriorating") return "bg-red-50 text-red-800 ring-red-200";
  if (display === "stagnating") return "bg-amber-50 text-amber-900 ring-amber-200";
  if (display === "stable") return "bg-slate-100 text-slate-700 ring-slate-200";
  return "bg-slate-100 text-slate-600 ring-slate-200";
}

function ProbabilitySparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const w = 72;
  const h = 28;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / (max - min || 1)) * (h - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} className="mt-1 opacity-80" aria-hidden>
      <polyline points={points} fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function InfoTip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <button type="button" className="rounded p-0.5 text-[#94a3b8] hover:text-[#2563eb]" aria-label="More information">
        <Info className="h-3.5 w-3.5" />
      </button>
      <span className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-56 -translate-x-1/2 rounded-lg bg-[#0f2744] px-2.5 py-2 text-[11px] font-normal normal-case leading-snug text-white shadow-lg group-hover:block group-focus-within:block">
        {text}
      </span>
    </span>
  );
}

function WorklistContent() {
  const params = useSearchParams() ?? new URLSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [status, setStatus] = useState(params.get("status") ?? "");
  const [progress, setProgress] = useState(params.get("progress") ?? "");
  const [attention, setAttention] = useState(params.get("attention") ?? "");
  const [review, setReview] = useState(params.get("review") ?? "");
  const [myAttention, setMyAttention] = useState(params.get("my_attention") === "1");
  const [sort, setSort] = useState(params.get("sort") ?? "priority");
  const [page, setPage] = useState(Number(params.get("page") ?? "1"));
  const [pageSize, setPageSize] = useState(Number(params.get("page_size") ?? "20"));
  const [expanded, setExpanded] = useState<string | null>(null);
  const [registerOpen, setRegisterOpen] = useState(params.get("register") === "1");
  const [editChildId, setEditChildId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Item | null>(null);
  const [deleting, setDeleting] = useState(false);
  const queryClient = useQueryClient();

  const user = useQuery({
    queryKey: ["me"],
    queryFn: () => api<{ permissions: string[] }>("/auth/me"),
  });
  const canRegister = user.data?.permissions?.includes("child:write") ?? false;

  useEffect(() => {
    setRegisterOpen(params.get("register") === "1");
  }, [params]);

  const queryString = useMemo(() => {
    const p = new URLSearchParams();
    if (q) p.set("q", q);
    if (status) p.set("nutritional_status", status);
    if (progress) p.set("progress", progress);
    if (attention) p.set("attention", attention);
    if (review) p.set("review_status", review);
    if (myAttention) p.set("requires_my_attention", "true");
    p.set("sort", sort);
    p.set("page", String(page));
    p.set("page_size", String(pageSize));
    return p.toString();
  }, [q, status, progress, attention, review, myAttention, sort, page, pageSize]);

  const query = useQuery({
    queryKey: ["children", queryString],
    queryFn: () => api<ListResponse>(`/children?${queryString}`),
  });

  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const closeRegister = () => {
    setRegisterOpen(false);
    setEditChildId(null);
    if (params.get("register")) router.replace("/children");
  };

  async function removeChild() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api(`/children/${deleteTarget.id}`, { method: "DELETE" });
      await queryClient.invalidateQueries({ queryKey: ["children"] });
      toast.success(`${deleteTarget.pseudonymous_id} was removed from the clinic list.`);
      setDeleteTarget(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to remove this child");
    } finally {
      setDeleting(false);
    }
  }

  if (query.isLoading) return <Skeleton className="h-64" />;
  if (query.isError) return <ErrorState message="Unable to load the child registry." />;

  return (
    <div className="-mx-6 -mt-2 min-h-[calc(100vh-4rem)] bg-[#eef2f7] px-4 pb-8 pt-2 sm:px-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#0f2744]">Children Under Monitoring</h1>
        </div>
        {canRegister ? (
          <Button type="button" className="rounded-xl bg-[#2563eb] shadow-sm hover:bg-[#1d4ed8]" onClick={() => setRegisterOpen(true)}>
            Register child
          </Button>
        ) : null}
      </div>

      <RegisterChildModal open={registerOpen || Boolean(editChildId)} editChildId={editChildId} onClose={closeRegister} />
      <ConfirmAction
        open={Boolean(deleteTarget)}
        title="Remove child"
        message={deleteTarget ? `${deleteTarget.pseudonymous_id} will be removed from the clinic list.` : ""}
        confirmLabel="Remove child"
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={removeChild}
      />

      <div className="overflow-hidden rounded-3xl bg-white shadow-[0_4px_24px_rgba(15,40,80,0.06)]">
      <div className="grid gap-3 border-b border-[#e8eef5] p-4 lg:grid-cols-[1fr_auto_auto_auto_auto_auto]">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-[#94a3b8]" />
          <Input className="pl-9" placeholder="Search child ID" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
        </div>
        <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Nutritional status">
          <option value="">All nutritional statuses</option>
          <option value="normal">Normal</option>
          <option value="mam">MAM</option>
          <option value="sam">SAM</option>
          <option value="stunting">Stunting</option>
          <option value="underweight">Underweight</option>
        </Select>
        <Select value={progress} onChange={(e) => { setProgress(e.target.value); setPage(1); }} aria-label="Progress state">
          <option value="">All progress states</option>
          <option value="improving">Improving</option>
          <option value="stable">Stable</option>
          <option value="stagnating">Limited improvement</option>
          <option value="deteriorating">Deteriorating</option>
          <option value="insufficient_history">Insufficient history</option>
        </Select>
        <Select value={attention} onChange={(e) => { setAttention(e.target.value); setMyAttention(false); setPage(1); }} aria-label="Clinical attention">
          <option value="">All children</option>
          <option value="requires_attention">Requires attention</option>
          <option value="no_alert">No open alert</option>
          <option value="follow_up_overdue">Follow-up overdue</option>
        </Select>
        <Select value={review} onChange={(e) => { setReview(e.target.value); setPage(1); }} aria-label="Review state">
          <option value="">All review states</option>
          <option value="AWAITING_REVIEW">Awaiting review</option>
          <option value="REVIEWED">Reviewed</option>
          <option value="IN_REVIEW">In review</option>
          <option value="FURTHER_ASSESSMENT">Further assessment required</option>
        </Select>
        <Select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort">
          <option value="priority">Clinical priority</option>
          <option value="latest_assessment">Latest assessment</option>
          <option value="probability">Probability</option>
          <option value="follow_up">Follow-up</option>
        </Select>
      </div>

      {items.length === 0 ? (
        <EmptyState title="No children match the current filters." />
      ) : (
        <>
          <div className="hidden overflow-x-auto lg:block">
            <table className="w-full min-w-[1180px] text-left text-sm">
              <thead>
                <tr className="border-b border-[#e8eef5] text-[10px] uppercase tracking-wide text-[#64748b]">
                  <th className="px-4 py-3 font-semibold">Child name</th>
                  <th className="px-3 py-3 font-semibold">Latest Assessment</th>
                  <th className="px-3 py-3 font-semibold">AI-Assisted Assessment</th>
                  <th className="px-3 py-3 font-semibold">Longitudinal Progress</th>
                  <th className="px-3 py-3 font-semibold">Clinical Attention</th>
                  <th className="px-3 py-3 font-semibold">Next Follow-Up</th>
                  <th className="px-4 py-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <WorklistRow
                    key={row.id}
                    row={row}
                    expanded={expanded === row.id}
                    canWrite={canRegister}
                    onEdit={() => setEditChildId(row.id)}
                    onDelete={() => setDeleteTarget(row)}
                    onToggle={() => setExpanded(expanded === row.id ? null : row.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-3 p-4 lg:hidden">
            {items.map((row) => (
              <MobileCard
                key={row.id}
                row={row}
                canWrite={canRegister}
                onEdit={() => setEditChildId(row.id)}
                onDelete={() => setDeleteTarget(row)}
              />
            ))}
          </div>
        </>
      )}
      </div>

      {totalPages > 1 ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white px-4 py-3 text-sm shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-[#64748b]">Per page</span>
            <Select className="h-8 w-20 py-0 text-xs" value={String(pageSize)} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" className="h-8 px-3" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
            <span className="text-[#64748b]">Page {page} of {totalPages}</span>
            <Button variant="secondary" className="h-8 px-3" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function WorklistRow({
  row,
  expanded,
  canWrite,
  onEdit,
  onDelete,
  onToggle,
}: {
  row: Item;
  expanded: boolean;
  canWrite: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onToggle: () => void;
}) {
  const progressLabel = PROGRESS_LABELS[row.progress_display ?? ""] ?? formatStatus(row.progress_display);
  const reviewLabel = REVIEW_LABELS[row.clinician_review_status ?? ""] ?? row.clinician_review_status;
  const needsReview = row.clinician_review_status === "AWAITING_REVIEW" || row.clinician_review_status === "IN_REVIEW";
  const actionLabel = !row.has_assessment ? "Start baseline" : needsReview ? "Review" : "Open";
  const href = !row.has_assessment
    ? `/children/${row.id}/visits/new`
    : needsReview
      ? `/children/${row.id}?focus=review`
      : `/children/${row.id}`;

  return (
    <>
      <tr className={cn("border-b border-[#e8eef5] last:border-0", progressTone(row.progress_display))}>
        <td className="px-4 py-3 align-top">
          <button type="button" onClick={onToggle} className="mr-1 inline-flex text-[#94a3b8] hover:text-[#2563eb]" aria-label="Expand row">
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
          <p className="inline font-semibold text-[#0f2744]">{row.full_name?.trim() || "—"}</p>
          <p className="mt-0.5 text-xs text-[#64748b]">
            {row.pseudonymous_id}
            {" · "}
            {ageLabel(row.age_months)} · {formatStatus(row.sex)}
            {row.facility_code ? ` · ${row.facility_code}` : ""}
          </p>
        </td>
        <td className="px-3 py-3 align-top">
          {row.last_visit ? (
            <>
              <p className="font-medium text-[#0f2744]">{formatClinicalDate(row.last_visit)}</p>
              <p className="text-xs text-[#64748b]">
                V{row.latest_visit_number ?? row.visit_count} · {row.assessment_count} assessment{row.assessment_count === 1 ? "" : "s"}
              </p>
            </>
          ) : (
            <span className="text-[#64748b]">No assessments yet</span>
          )}
        </td>
        <td className="px-3 py-3 align-top">
          <AssessmentCell row={row} />
        </td>
        <td className="px-3 py-3 align-top">
          <ProgressCell row={row} progressLabel={progressLabel} />
        </td>
        <td className="px-3 py-3 align-top">
          <AttentionCell row={row} reviewLabel={reviewLabel} />
        </td>
        <td className="px-3 py-3 align-top">
          <FollowUpCell row={row} />
        </td>
        <td className="px-4 py-3 text-right align-top">
          <div className="inline-flex items-center justify-end gap-2">
            {canWrite ? <RecordActions onEdit={onEdit} onDelete={onDelete} editLabel={`Edit ${row.pseudonymous_id}`} deleteLabel={`Remove ${row.pseudonymous_id}`} /> : null}
            <Link href={href} className="inline-flex items-center gap-1 text-sm font-medium text-[#2563eb] hover:underline">
              {actionLabel} <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </td>
      </tr>
      {expanded ? (
        <tr className="bg-[#f8fafc]">
          <td colSpan={7} className="px-6 py-4 text-sm text-[#475569]">
            <ExpandedDetail row={row} progressLabel={progressLabel} reviewLabel={reviewLabel} />
          </td>
        </tr>
      ) : null}
    </>
  );
}

function AssessmentCell({ row }: { row: Item }) {
  if (!row.has_assessment) {
    return <p className="text-sm text-[#64748b]">Not assessed</p>;
  }
  const showSeverity = row.severity && row.severity !== "none";
  const delta = row.risk_change_pp;
  const prevPct = row.previous_risk != null ? Math.round(row.previous_risk * 100) : null;

  return (
    <div>
      <div className="flex flex-wrap gap-1">
        <span className="rounded-full bg-[#eef2ff] px-2 py-0.5 text-xs font-medium text-[#1e40af]">
          {row.score_kind === "highest_condition_probability"
            ? displayedConditionList(row).join(", ") || "—"
            : formatNutritionalStatus(displayedMalnutritionType(row), row.severity)}
        </span>
        {showSeverity && !["MAM", "SAM"].includes(formatNutritionalStatus(displayedMalnutritionType(row), row.severity)) ? (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">{formatStatus(row.severity)}</span>
        ) : null}
      </div>
      <p className="mt-1.5 text-lg font-semibold tabular-nums text-[#0f2744]">{formatPercent(row.current_risk)}</p>
      <p className="flex items-center gap-1 text-[10px] text-[#64748b]">
        {clinicalPhrase(row.probability_label, "Model-assessed probability")}
        <InfoTip text="Generated by the active model. Interpretation depends on the configured prediction task and does not replace clinical assessment." />
      </p>
      {prevPct != null && delta != null ? (
        <p className="mt-0.5 text-xs text-[#64748b]">
          Previous {prevPct}% ·{" "}
          <span className={delta > 0 ? "text-clinical-warning" : delta < 0 ? "text-emerald-700" : ""}>
            {delta > 0 ? "↑" : delta < 0 ? "↓" : "→"} {Math.abs(delta)} pp
          </span>
        </p>
      ) : null}
    </div>
  );
}

function ProgressCell({ row, progressLabel }: { row: Item; progressLabel: string }) {
  if (row.progress_display === "incompatible_model") {
    return (
      <div>
        <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1", progressBadgeClass(row.progress_display))}>{progressLabel}</span>
        <p className="mt-1 text-xs text-[#64748b]">Model version changed</p>
      </div>
    );
  }
  return (
    <div>
      <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1", progressBadgeClass(row.progress_display))}>{progressLabel}</span>
      {row.risk_velocity_available && row.risk_velocity_pp_month != null ? (
        <p className="mt-1 flex items-center gap-1 text-xs text-[#475569]">
          RV {row.risk_velocity_pp_month > 0 ? "+" : ""}
          {row.risk_velocity_pp_month} pp/month
          <InfoTip text="Visit-to-visit change in model-assessed probability, adjusted for elapsed time. Clinical review required." />
        </p>
      ) : row.progress_display === "insufficient_history" || !row.has_assessment ? (
        <p className="mt-1 text-xs text-[#64748b]">RV not available</p>
      ) : null}
      {row.probability_history && row.probability_history.length >= 2 ? <ProbabilitySparkline values={row.probability_history} /> : null}
    </div>
  );
}

function AttentionCell({ row, reviewLabel }: { row: Item; reviewLabel: string }) {
  const alerts = row.clinical_attention ?? [];
  if (!row.has_assessment && row.visit_count === 0) {
    return <p className="text-xs font-medium text-[#475569]">Baseline assessment required</p>;
  }
  return (
    <div className="space-y-1">
      {alerts.length === 0 ? <p className="text-xs text-[#64748b]">No open clinical alert</p> : null}
      {alerts.map((a) => (
        <p key={a.type} className="text-xs font-medium text-clinical-warning">⚠ {a.label}</p>
      ))}
      <p className="text-xs text-[#475569]">{reviewLabel}</p>
    </div>
  );
}

function FollowUpCell({ row }: { row: Item }) {
  if (!row.next_follow_up) return <p className="text-xs text-[#64748b]">No follow-up scheduled</p>;
  const st = row.follow_up_display_status;
  return (
    <div>
      <p className={cn("font-medium", st === "overdue" ? "text-clinical-warning" : "text-[#0f2744]")}>{formatClinicalDate(row.next_follow_up)}</p>
      {st === "overdue" && row.follow_up_overdue_days != null ? (
        <p className="text-xs text-clinical-warning">Overdue by {row.follow_up_overdue_days} days</p>
      ) : st === "due_today" ? (
        <p className="text-xs text-amber-700">Due today</p>
      ) : (
        <p className="text-xs capitalize text-[#64748b]">Scheduled</p>
      )}
    </div>
  );
}

function ExpandedDetail({ row, progressLabel, reviewLabel }: { row: Item; progressLabel: string; reviewLabel: string }) {
  const m = row.measurements;
  const hist = row.probability_history ?? [];
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div>
        <p className="text-xs font-semibold uppercase text-[#64748b]">Latest measurements</p>
        {m ? (
          <ul className="mt-2 space-y-1 text-sm">
            <li>Weight {m.weight_kg ?? "—"} kg</li>
            <li>Height {m.height_cm ?? "—"} cm</li>
            {m.previous_weight_kg != null ? <li className="text-[#64748b]">Prev weight {m.previous_weight_kg} kg</li> : null}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-[#64748b]">No measurements recorded</p>
        )}
      </div>
      <div>
        <p className="text-xs font-semibold uppercase text-[#64748b]">Probability history</p>
        <p className="mt-2 text-sm">{hist.length ? hist.map((v) => `${v}%`).join(" → ") : "—"}</p>
        <p className="mt-2 text-xs text-[#64748b]">Progress: {progressLabel}</p>
        {row.risk_velocity_available ? <p className="text-xs">RV {row.risk_velocity_pp_month} pp/month</p> : null}
      </div>
      <div>
        <p className="text-xs font-semibold uppercase text-[#64748b]">Review & alerts</p>
        <p className="mt-2 text-sm">{reviewLabel}</p>
        {(row.clinical_attention ?? []).map((a) => (
          <p key={a.type} className="text-sm text-clinical-warning">{a.label}</p>
        ))}
      </div>
    </div>
  );
}

function MobileCard({
  row,
  canWrite,
  onEdit,
  onDelete,
}: {
  row: Item;
  canWrite: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const needsReview = row.clinician_review_status === "AWAITING_REVIEW";
  const href = !row.has_assessment ? `/children/${row.id}/visits/new` : needsReview ? `/children/${row.id}?focus=review` : `/children/${row.id}`;
  return (
    <article className={cn("rounded-2xl border border-[#e8eef5] bg-white p-4 shadow-sm", progressTone(row.progress_display))}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-[#0f2744]">{row.full_name?.trim() || "—"}</p>
          <p className="text-xs text-[#64748b]">
            {row.pseudonymous_id} · {ageLabel(row.age_months)} · {formatStatus(row.sex)}
          </p>
        </div>
        <div className="flex items-center gap-1">
          {canWrite ? <RecordActions onEdit={onEdit} onDelete={onDelete} editLabel={`Edit ${row.pseudonymous_id}`} deleteLabel={`Remove ${row.pseudonymous_id}`} /> : null}
          <Link href={href} className="text-sm font-medium text-[#2563eb]">{needsReview ? "Review" : "Open"}</Link>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div><span className="text-[#64748b]">Assessment</span><p>{formatPercent(row.current_risk)}</p></div>
        <div><span className="text-[#64748b]">Progress</span><p>{PROGRESS_LABELS[row.progress_display ?? ""] ?? "—"}</p></div>
      </div>
    </article>
  );
}

export function ChildrenWorklist() {
  return (
    <Suspense fallback={<Skeleton className="h-64" />}>
      <WorklistContent />
    </Suspense>
  );
}
