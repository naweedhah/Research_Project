"use client";

import { useMemo } from "react";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";
import { ClinicBoardScreen } from "@/components/component1/clinic-board/ClinicBoardScreen";
import { classifyClinicBoard, summarizeClinicBoard } from "@/data/clinic-board";
import { useClinicChildren } from "@/data/use-clinic-children";

export default function ClinicBoardPage() {
  const query = useClinicChildren();

  const children = query.data ?? [];
  const groups = useMemo(() => classifyClinicBoard(children), [children]);
  const picture = useMemo(() => summarizeClinicBoard(children), [children]);

  if (query.isLoading) return <BoardSkeleton />;
  if (query.isError) return <ErrorState message={query.error instanceof Error ? query.error.message : "The clinic board could not be loaded."} />;
  if (children.length === 0) {
    return (
      <div className="space-y-5">
        <h1 className="text-3xl font-semibold tracking-tight text-[#102A4C]">Clinic Board</h1>
        <EmptyState
          title="No child records yet."
          body="Register a child and record a visit. This board compares the latest measurements with the 12-month prediction."
        />
      </div>
    );
  }

  return <ClinicBoardScreen childCount={children.length} groups={groups} picture={picture} />;
}

function BoardSkeleton() {
  return (
    <div className="space-y-4" aria-hidden>
      <Skeleton className="h-24" />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
      <Skeleton className="h-48" />
      <div className="grid gap-3 lg:grid-cols-3">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}
