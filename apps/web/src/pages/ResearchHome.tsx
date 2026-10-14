"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { EmptyState } from "@/components/common/states";
import { IntegrationFlowPanel } from "@/components/component4/integration-flow-panel";

export default function ResearchPage() {
  const profile = useQuery({ queryKey: ["dataset"], queryFn: () => api<Record<string, unknown>>("/research/dataset-profile") });
  const ablation = useQuery({ queryKey: ["ablation"], queryFn: () => api<{ message?: string; comparisons?: string[] }>("/research/ablation") });
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Research analytics</h1>
        <p className="mt-1 text-sm text-[#64748b]">
          Component 1 research surface, including live linkage to Shamiq (C3) and Naveed (C4).
        </p>
      </div>

      <IntegrationFlowPanel />

      <Card>
        <CardHeader><CardTitle>Dataset profile</CardTitle></CardHeader>
        <CardBody className="text-sm">
          <pre className="overflow-auto rounded-xl bg-canvas p-3">{JSON.stringify(profile.data, null, 2)}</pre>
        </CardBody>
      </Card>
      <Card>
        <CardHeader><CardTitle>Ablation</CardTitle></CardHeader>
        <CardBody>
          {ablation.data?.message ? <EmptyState title={ablation.data.message} /> : null}
          <ul className="list-disc pl-5 text-sm">
            {(ablation.data?.comparisons ?? []).map((c) => <li key={c}>{c}</li>)}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
