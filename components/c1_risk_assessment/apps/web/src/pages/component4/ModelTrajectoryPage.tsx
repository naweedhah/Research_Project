"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { AdvancedAiSummary } from "@/components/component1/child-profile-view";
import { ErrorState, Skeleton } from "@/components/common/states";
import { type ChildProfile } from "@/data/child-profile";
import { api } from "@/services/component4/httpClient";

export default function ModelTrajectoryPage() {
  const children = useQuery({
    queryKey: ["children", "trajectory-index"],
    queryFn: () => api<{ items: { id: string; pseudonymous_id: string }[] }>("/children?page=1&page_size=50"),
  });
  const items = children.data?.items ?? [];
  const profiles = useQueries({
    queries: items.map((child) => ({
      queryKey: ["child", child.id],
      queryFn: () => api<ChildProfile>(`/children/${child.id}`),
    })),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-[#0f2744]">Model trajectory</h1>
      <p className="max-w-xl text-sm leading-relaxed text-[#64748b]">
        Visit-to-visit model trajectory for each child. It is not a clinical measurement chart.
      </p>
      {children.isLoading ? <p className="text-sm text-[#64748b]">Loading children…</p> : null}
      {items.length === 0 && !children.isLoading ? (
        <p className="text-sm text-[#64748b]">No child records yet. Register a child before opening a model trajectory.</p>
      ) : null}
      {items.map((child, index) => {
        const profile = profiles[index];
        if (!profile || profile.isLoading) return <Skeleton key={child.id} className="h-64" />;
        if (profile.isError || !profile.data) {
          return <ErrorState key={child.id} message="This child record is unavailable or you are not authorized to view it." />;
        }
        return (
          <AdvancedAiSummary
            key={child.id}
            profile={profile.data}
            comparable={profile.data.longitudinal_comparable !== false}
          />
        );
      })}
    </div>
  );
}
