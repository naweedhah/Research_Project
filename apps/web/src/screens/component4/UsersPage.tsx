"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";

export default function UsersAdminPage() {
  const { data } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => api<{ items: { email: string; full_name: string; role: string; status: string }[] }>("/admin/users"),
  });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Users</h1>
      <table className="w-full rounded-2xl border border-line bg-white text-left text-sm">
        <thead className="text-muted">
          <tr>
            <th className="p-3">Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(data?.items ?? []).map((u) => (
            <tr key={u.email} className="border-t border-line">
              <td className="p-3">{u.full_name}</td>
              <td>{u.email}</td>
              <td className="capitalize">{u.role.replaceAll("_", " ")}</td>
              <td>{u.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
