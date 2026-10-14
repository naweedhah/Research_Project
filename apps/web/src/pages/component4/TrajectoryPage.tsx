"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { AdvancedAiSummary } from "@/components/component4/child-profile-view";
import { ErrorState, Skeleton } from "@/components/common/states";
import { type ChildProfile } from "@/data/child-profile";
import { api } from "@/services/component4/httpClient";

export default function TrajectoryPage() {
  const params = useParams<{ childId: string }>();
  const profile = useQuery({
    queryKey: ["child", params.childId],
    queryFn: () => api<ChildProfile>(`/children/${params.childId}`),
  });

  if (profile.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-64" />
      </div>
    );
  }
  if (profile.isError || !profile.data) {
    return <ErrorState message="This child record is unavailable or you are not authorized to view it." />;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-[#0f2744]">Model trajectory</h1>
          <p className="mt-1 text-sm text-[#64748b]">
            {profile.data.pseudonymous_id}
            {profile.data.facility?.name ? ` · ${profile.data.facility.name}` : ""}
          </p>
        </div>
        <Link
          href={`/children/${profile.data.id}`}
          className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-line bg-white px-3 text-sm font-medium text-[#0f2744] hover:bg-[#f8fafc]"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Progress tracking
        </Link>
      </div>
      <AdvancedAiSummary profile={profile.data} comparable={profile.data.longitudinal_comparable !== false} />
    </div>
  );
}
