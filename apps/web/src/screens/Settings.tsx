"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { AdminNav, PageHeader } from "@/components/clinical/page-header";
import { ErrorState, Skeleton } from "@/components/common/states";

export default function SettingsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api<{ sections: string[]; clinical_policy: Record<string, unknown> }>("/admin/settings"),
  });
  return (
    <div className="max-w-4xl space-y-5">
      <PageHeader kicker="System" title="Settings" purpose="Read-only view of the clinical policy configuration applied by the API." action={<AdminNav />} />
      {isLoading ? (
        <Skeleton className="h-48 rounded-[24px]" />
      ) : error ? (
        <ErrorState message={error instanceof Error ? error.message : "Settings could not be loaded."} />
      ) : (
        <>
          <ul className="flex flex-wrap gap-2">
            {(data?.sections ?? []).map((s) => (
              <li key={s} className="rounded-full border border-white/80 bg-white/85 px-3 py-1 text-sm text-[#102A4C] shadow-card">
                {s}
              </li>
            ))}
          </ul>
          <div className="rounded-[24px] border border-white/80 bg-white/85 p-5 text-sm shadow-card backdrop-blur-xl">
            <p className="font-medium text-[#102A4C]">Clinical policy configuration</p>
            <dl className="mt-3 grid gap-2 sm:grid-cols-2">
              {Object.entries(data?.clinical_policy ?? {}).map(([key, value]) => (
                <div key={key} className="rounded-2xl bg-[#F4F7FA] px-4 py-2.5">
                  <dt className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#5C6E82]">{key.replaceAll("_", " ")}</dt>
                  <dd className="mt-0.5 break-words font-medium text-[#102A4C]">{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        </>
      )}
    </div>
  );
}
