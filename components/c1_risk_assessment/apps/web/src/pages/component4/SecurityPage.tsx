"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";

export default function SecurityPage() {
  const { data } = useQuery({ queryKey: ["security"], queryFn: () => api<{ active_users: number; failed_logins: { email: string; at: string }[]; recent_audit: { action: string; timestamp: string; role?: string }[] }>("/admin/security") });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Security</h1>
      <Card>
        <CardHeader><CardTitle>Active users</CardTitle></CardHeader>
        <CardBody>{data?.active_users ?? "—"}</CardBody>
      </Card>
      <Card>
        <CardHeader><CardTitle>Failed logins</CardTitle></CardHeader>
        <CardBody>
          <ul className="text-sm">{(data?.failed_logins ?? []).map((f, i) => <li key={i}>{f.email} · {f.at}</li>)}</ul>
        </CardBody>
      </Card>
      <Card>
        <CardHeader><CardTitle>Recent audit events</CardTitle></CardHeader>
        <CardBody>
          <ul className="text-sm">{(data?.recent_audit ?? []).map((a, i) => <li key={i}>{a.action} · {a.role} · {a.timestamp}</li>)}</ul>
        </CardBody>
      </Card>
    </div>
  );
}
