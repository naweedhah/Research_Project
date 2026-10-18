"use client";

import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/common/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { api } from "@/services/component4/httpClient";
import { useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type MeUser = { permissions?: string[] };

export default function ReportsPage() {
  const [msg, setMsg] = useState<string | null>(null);
  const { data } = useQuery({ queryKey: ["dashboard"], queryFn: () => api<{ risk_trend: Record<string, number> }>("/dashboard") });
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<MeUser>("/auth/me") });
  const canExport = me.data?.permissions?.includes("report:export") ?? false;
  const chart = Object.entries(data?.risk_trend ?? {}).map(([name, n]) => ({ name, n }));
  async function exportData() {
    const ok = window.confirm("Export de-identified research rows? Direct identity fields will be excluded and the action will be audited.");
    if (!ok) return;
    const data = await api<{ confirmation: string; rows: unknown[] }>("/research/export", { method: "POST" });
    setMsg(`${data.confirmation} (${data.rows.length} rows)`);
  }
  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Facility analytics</h1>
        <Card>
          <CardHeader><CardTitle>Progress distribution</CardTitle></CardHeader>
          <CardBody className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="n" fill="#1D4ED8" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      </div>
      <div className="max-w-2xl space-y-4">
        <h1 className="text-2xl font-semibold">Reports</h1>
        <p className="text-sm text-muted">Health-worker progress summaries are available from each child profile. Dataset export is permissioned and audited.</p>
        {canExport ? (
          <>
            <Button onClick={exportData}>Export de-identified dataset</Button>
            {msg ? <p className="text-sm">{msg}</p> : null}
          </>
        ) : (
          <p className="text-sm text-muted">Research dataset export requires the report:export permission.</p>
        )}
      </div>
    </div>
  );
}
