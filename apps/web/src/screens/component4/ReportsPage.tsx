"use client";

import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/common/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { api } from "@/services/component4/httpClient";
import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/clinical/page-header";

type MeUser = { permissions?: string[] };

export default function ReportsPage() {
  const [msg, setMsg] = useState<string | null>(null);
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<MeUser>("/auth/me") });
  const canExport = me.data?.permissions?.includes("report:export") ?? false;
  async function exportData() {
    const ok = window.confirm("Export de-identified research rows? Direct identity fields will be excluded and the action will be audited.");
    if (!ok) return;
    const data = await api<{ confirmation: string; rows: unknown[] }>("/research/export", { method: "POST" });
    setMsg(`${data.confirmation} (${data.rows.length} rows)`);
  }
  return (
    <div className="space-y-5">
      <PageHeader kicker="Child care" title="Reports" purpose="Per-child nutrition reports open from each child profile. Facility-level figures live in Analytics." action={<Link href="/children"><Button className="rounded-2xl bg-[#102A4C] hover:bg-[#173D6B]">Open a child report</Button></Link>} />
      <Card>
        <CardHeader><CardTitle>Child nutrition report</CardTitle></CardHeader>
        <CardBody className="text-sm text-[#5C6E82]">
          Each report contains the child and visit details, the current WHO assessment, measurements, the 12-month prediction with probabilities, severity and review state, growth history, clinical context, model information and the research disclaimer. Open a child profile and choose Report.
        </CardBody>
      </Card>
      <div className="max-w-2xl space-y-3">
        <h2 className="text-base font-semibold text-[#102A4C]">Research dataset export</h2>
        <p className="text-sm text-muted">Dataset export is permissioned and audited. Direct identity fields are excluded.</p>
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
