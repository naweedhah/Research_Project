"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { IntegrationFlowPanel } from "@/components/component4/integration-flow-panel";

type IntegrationStatus = {
  c3: { status: string; configured: boolean; pending_events: number; failed_events: number; last_success_at?: string | null };
  c4: { status: string; configured: boolean; pending_events: number; failed_events: number; last_success_at?: string | null };
  c2: { status: string; configured: boolean };
  integration_mode: string;
};

export default function SystemPage() {
  const { data } = useQuery({ queryKey: ["system"], queryFn: () => api<Record<string, unknown>>("/admin/system") });
  const integrations = useQuery({
    queryKey: ["integrations-status"],
    queryFn: () => api<IntegrationStatus>("/integrations/status"),
    retry: 1,
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">System health</h1>
        <p className="mt-1 text-sm text-[#64748b]">Service status for the clinic workspace.</p>
      </div>

      <IntegrationFlowPanel />

      <div className="grid gap-4 md:grid-cols-3">
        {["api", "database", "redis"].map((k) => (
          <Card key={k}>
            <CardHeader>
              <CardTitle className="capitalize">{k}</CardTitle>
            </CardHeader>
            <CardBody>{String(data?.[k] ?? "…")}</CardBody>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Inference</CardTitle>
        </CardHeader>
        <CardBody>
          <pre className="overflow-auto text-sm">{JSON.stringify(data?.inference, null, 2)}</pre>
          <p className="mt-2 text-sm">Active model: {JSON.stringify(data?.active_model)}</p>
        </CardBody>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>External component integrations</CardTitle>
        </CardHeader>
        <CardBody>
          <p className="mb-3 text-xs text-[#64748b]">Mode: {integrations.data?.integration_mode ?? "…"}</p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] text-left text-sm">
              <thead>
                <tr className="border-b border-line text-[#64748b]">
                  <th className="py-2 font-medium">Component</th>
                  <th className="py-2 font-medium">Status</th>
                  <th className="py-2 font-medium">Pending</th>
                  <th className="py-2 font-medium">Failed</th>
                  <th className="py-2 font-medium">Last success</th>
                </tr>
              </thead>
              <tbody>
                {(["c3", "c4"] as const).map((key) => {
                  const row = integrations.data?.[key];
                  return (
                    <tr key={key} className="border-b border-line/70">
                      <td className="py-2 font-medium uppercase">{key}</td>
                      <td className="py-2">{row?.status ?? "…"}</td>
                      <td className="py-2 tabular-nums">{row?.pending_events ?? "—"}</td>
                      <td className="py-2 tabular-nums">{row?.failed_events ?? "—"}</td>
                      <td className="py-2 text-xs text-[#64748b]">{row?.last_success_at ?? "—"}</td>
                    </tr>
                  );
                })}
                <tr>
                  <td className="py-2 font-medium">C2</td>
                  <td className="py-2">{integrations.data?.c2?.status ?? "…"}</td>
                  <td className="py-2">—</td>
                  <td className="py-2">—</td>
                  <td className="py-2 text-xs text-[#64748b]">Explainability only</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
