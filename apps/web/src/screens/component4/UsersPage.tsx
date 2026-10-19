"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { AdminNav, PageHeader } from "@/components/clinical/page-header";
import { EmptyState, ErrorState, Skeleton } from "@/components/common/states";

export default function UsersAdminPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => api<{ items: { email: string; full_name: string; role: string; status: string }[] }>("/admin/users"),
  });
  const items = data?.items ?? [];
  return (
    <div className="space-y-5">
      <PageHeader kicker="System" title="Users" purpose="Clinic staff accounts and their roles." action={<AdminNav />} />
      {isLoading ? (
        <Skeleton className="h-48 rounded-[24px]" />
      ) : error ? (
        <ErrorState message={error instanceof Error ? error.message : "Users could not be loaded."} />
      ) : items.length === 0 ? (
        <EmptyState title="No users found." />
      ) : (
        <div className="overflow-x-auto rounded-[24px] border border-white/80 bg-white/85 shadow-card backdrop-blur-xl">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-[0.12em] text-[#5C6E82]">
              <tr>
                <th className="px-5 py-3">Name</th>
                <th className="py-3">Email</th>
                <th className="py-3">Role</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((u) => (
                <tr key={u.email} className="border-t border-[#E8EFF5]">
                  <td className="px-5 py-3 font-medium text-[#102A4C]">{u.full_name}</td>
                  <td className="py-3">{u.email}</td>
                  <td className="py-3 capitalize">{u.role.replaceAll("_", " ")}</td>
                  <td className="px-5 py-3">{u.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
