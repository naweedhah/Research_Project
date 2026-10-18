"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Suspense, useEffect } from "react";
import { toast } from "sonner";
import { ChildProfileView } from "@/components/component1/child-profile-view";
import { ErrorState, Skeleton } from "@/components/common/states";
import { api } from "@/services/component4/httpClient";
import { PROFILE_TABS, type ChildProfile, type ProfileTab } from "@/data/child-profile";

const ASSESSMENT_API: Record<string, string> = {
  agree: "AGREE",
  disagree: "DISAGREE",
  uncertain: "FURTHER_ASSESSMENT_REQUIRED",
  AGREE: "AGREE",
  DISAGREE: "DISAGREE",
  FURTHER_ASSESSMENT_REQUIRED: "FURTHER_ASSESSMENT_REQUIRED",
};

const WORKFLOW_API: Record<string, string> = {
  monitor: "CONTINUE_MONITORING",
  nutrition: "NUTRITION_REVIEW",
  investigate: "FURTHER_INVESTIGATION",
  refer: "REFER",
  reassess: "REQUEST_INTERVENTION_REASSESSMENT",
  intervention: "REQUEST_INTERVENTION_REASSESSMENT",
  CONTINUE_MONITORING: "CONTINUE_MONITORING",
  NUTRITION_REVIEW: "NUTRITION_REVIEW",
  FURTHER_INVESTIGATION: "FURTHER_INVESTIGATION",
  REFER: "REFER",
  REQUEST_INTERVENTION_REASSESSMENT: "REQUEST_INTERVENTION_REASSESSMENT",
};

export default function ChildProfilePage() {
  return (
    <Suspense fallback={<Skeleton className="h-96" />}>
      <ChildProfileContent />
    </Suspense>
  );
}

function isProfileTab(value: string | null): value is ProfileTab {
  return PROFILE_TABS.includes(value as ProfileTab);
}

function ChildProfileContent() {
  const childId = useParams<{ childId: string }>()?.childId ?? "";
  const searchParams = useSearchParams();
  const router = useRouter();
  const qc = useQueryClient();
  const justRegistered = searchParams?.get("registered") === "1";
  const focus = searchParams?.get("focus") ?? null;
  const tabQuery = searchParams?.get("tab") ?? null;
  const tab: ProfileTab = isProfileTab(tabQuery) ? tabQuery : "overview";

  const profile = useQuery({
    queryKey: ["child", childId],
    queryFn: () => api<ChildProfile>(`/children/${childId}`),
    enabled: childId.length > 0,
  });

  const acknowledge = useMutation({
    mutationFn: (id: string) => api(`/alerts/${id}/acknowledge`, { method: "PATCH", body: JSON.stringify({}) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["child", childId] }),
  });
  const addNote = useMutation({
    mutationFn: (payload: { body: string; visit_id?: string }) =>
      api(`/children/${childId}/notes`, {
        method: "POST",
        body: JSON.stringify({ body: payload.body, visit_id: payload.visit_id ?? null }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["child", childId] }),
  });
  const saveReview = useMutation({
    mutationFn: (payload: { assessment: string; workflow: string; note: string }) => {
      const visitId = profile.data?.current?.id;
      if (!visitId) throw new Error("No active visit available for clinician review");
      const assessment = ASSESSMENT_API[payload.assessment] ?? payload.assessment;
      const workflow_action = WORKFLOW_API[payload.workflow] ?? payload.workflow;
      return api(`/visits/${visitId}/clinician-review`, {
        method: "POST",
        body: JSON.stringify({
          assessment,
          workflow_action,
          clinical_note: payload.note,
        }),
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["child", childId] });
      qc.invalidateQueries({ queryKey: ["c3-reassessment", childId] });
      toast.success("Clinician review saved. The AI prediction was not changed.");
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Unable to save clinician review"),
  });

  useEffect(() => {
    if (!profile.data || !focus) return;
    const targetId = focus === "followup" ? "follow-up" : focus === "review" ? "clinician-review" : null;
    if (!targetId) return;
    const timer = window.setTimeout(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [profile.data, focus]);

  function setTab(next: ProfileTab) {
    const q = new URLSearchParams(searchParams?.toString() ?? "");
    if (next === "overview") q.delete("tab");
    else q.set("tab", next);
    router.replace(`/children/${childId}?${q.toString()}`, { scroll: false });
  }

  if (profile.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-40" />
        <div className="grid gap-4 xl:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }
  if (profile.isError || !profile.data) {
    return <ErrorState message="This child record is unavailable or you are not authorized to view it." />;
  }

  return (
    <ChildProfileView
      profile={profile.data}
      tab={tab}
      onTab={setTab}
      justRegistered={justRegistered}
      onDismissRegistered={() => router.replace(`/children/${profile.data!.id}`)}
      onSaveReview={(payload) => saveReview.mutate(payload)}
      reviewSaving={saveReview.isPending}
      onAddNote={(body) =>
        addNote.mutate(
          { body },
          {
            onSuccess: () => toast.success("Clinical note saved"),
          },
        )
      }
      noteSaving={addNote.isPending}
      onAcknowledge={(id) => acknowledge.mutate(id)}
    />
  );
}
