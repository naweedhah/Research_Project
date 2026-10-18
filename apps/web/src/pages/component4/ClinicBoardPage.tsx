"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";
import { ClinicBoardScreen } from "@/components/component1/clinic-board/ClinicBoardScreen";
import { classifyClinicBoard, summarizeClinicBoard, type ClinicChildInput } from "@/data/clinic-board";

type ListResponse = {
  items: ClinicChildInput[];
  total: number;
  page: number;
  page_size: number;
};

async function fetchClinicChildren(): Promise<ClinicChildInput[]> {
  const first = await api<ListResponse>("/children?page=1&page_size=100");
  const items = [...first.items];
  const pages = Math.max(1, Math.ceil((first.total || items.length) / (first.page_size || 100)));
  for (let page = 2; page <= pages; page += 1) {
    const next = await api<ListResponse>(`/children?page=${page}&page_size=100`);
    items.push(...next.items);
  }
  return items;
}

export default function ClinicBoardPage() {
  const query = useQuery({
    queryKey: ["children", "clinic-board"],
    queryFn: fetchClinicChildren,
  });

  const children = query.data ?? [];
  const groups = useMemo(() => classifyClinicBoard(children), [children]);
  const picture = useMemo(() => summarizeClinicBoard(children), [children]);

  if (query.isLoading) return <BoardSkeleton />;
  if (query.isError) return <ErrorState message="The clinic board could not be loaded." />;
  if (children.length === 0) {
    return (
      <div className="space-y-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#0E3A67]">Paediatric nutrition intelligence</p>
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-[#0A2748]">Clinic Board</h1>
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
