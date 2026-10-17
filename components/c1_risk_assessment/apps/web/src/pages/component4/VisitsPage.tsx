"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { StatusBadge } from "@/components/cards/status-badge";
import { EmptyState } from "@/components/common/states";
import { Button } from "@/components/common/button";

export default function VisitsPage() {
  const { data } = useQuery({
    queryKey: ["follow-ups"],
    queryFn: () => api<{ items: { id: string; child: string; child_id?: string; expected_date: string; status: string; interval_days?: number }[] }>("/follow-ups"),
  });
  const items = data?.items ?? [];
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Follow-up schedule</h1>
        <p className="text-sm text-muted">Upcoming clinic reviews across your facility. Missed dates trigger workflow alerts.</p>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No follow-ups are scheduled." body="Schedule follow-ups from a child profile after reviewing their assessment." />
      ) : (
        <table className="w-full rounded-2xl border border-line bg-white text-left text-sm">
          <thead className="text-muted">
            <tr>
              <th className="p-3">Child</th>
              <th>Expected date</th>
              <th>Interval</th>
              <th>Status</th>
              <th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.id} className="border-t border-line">
                <td className="p-3 font-medium">
                  {r.child_id ? (
                    <Link href={`/children/${r.child_id}`} className="text-[#0E3A67] hover:underline">{r.child}</Link>
                  ) : (
                    r.child
                  )}
                </td>
                <td>{new Date(r.expected_date).toLocaleDateString()}</td>
                <td>{r.interval_days ? `${r.interval_days} days` : "—"}</td>
                <td><StatusBadge value={r.status} /></td>
                <td className="p-3">
                  {r.child_id ? (
                    <Link href={`/children/${r.child_id}/visits/new`}>
                      <Button variant="secondary" className="min-h-9 px-3 text-xs">Record visit</Button>
                    </Link>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
