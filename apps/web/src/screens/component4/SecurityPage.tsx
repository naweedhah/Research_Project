"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { AdminNav, PageHeader } from "@/components/clinical/page-header";
import { ErrorState, Skeleton } from "@/components/common/states";

export default function SecurityPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["security"],
    queryFn: () =>
      api<{ active_users: number; failed_logins: { email: string; at: string }[]; recent_audit: { action: string; timestamp: string; role?: string }[] }>("/admin/security"),
  });
  return (
    <div className="space-y-5">
      <PageHeader kicker="System" title="Security" purpose="Sign-in activity and the audit trail for this workspace." action={<AdminNav />} />
      {isLoading ? (
        <Skeleton className="h-48 rounded-[24px]" />
      ) : error ? (
        <ErrorState message={error instanceof Error ? error.message : "Security data could not be loaded."} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Active users</CardTitle>
            </CardHeader>
            <CardBody>
              <p className="text-3xl font-semibold tabular-nums text-[#102A4C]">{data?.active_users ?? "—"}</p>
            </CardBody>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Failed logins</CardTitle>
            </CardHeader>
            <CardBody>
              {(data?.failed_logins ?? []).length === 0 ? (
                <p className="text-sm text-[#5C6E82]">No failed sign-ins recorded.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {(data?.failed_logins ?? []).map((f, i) => (
                    <li key={i}>
                      {f.email} · {f.at}
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Recent audit events</CardTitle>
            </CardHeader>
            <CardBody>
              {(data?.recent_audit ?? []).length === 0 ? (
                <p className="text-sm text-[#5C6E82]">No audit events yet.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {(data?.recent_audit ?? []).map((a, i) => (
                    <li key={i}>
                      {a.action} · {a.role} · {a.timestamp}
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  );
}
