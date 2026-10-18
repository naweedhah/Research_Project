"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Bell,
  LayoutDashboard,
  LogOut,
  UserRound,
  Stethoscope,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, PRODUCT } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { CommandPalette } from "@/components/common/command-palette";
import { cn } from "@/utils/utils";

type User = {
  full_name: string;
  qualifications?: string | null;
  experience?: string | null;
  role: string;
  email: string;
  facility_name?: string;
  facility_code?: string;
  permissions?: string[];
};

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/children", label: "Children", icon: Users },
  { href: "/clinic-board", label: "Clinic board", icon: Stethoscope },
  { href: "/alerts", label: "Alerts", icon: Bell },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const user = useQuery({ queryKey: ["me"], queryFn: () => api<User>("/auth/me") });
  const notes = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api<{ items: { id: string; title: string; severity: string; created_at: string }[] }>("/notifications"),
  });
  const logout = useMutation({
    mutationFn: () => api("/auth/logout", { method: "POST" }),
    onSuccess: () => router.push("/login"),
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (user.isError) router.push("/login");
  }, [user.isError, router]);

  return (
    <div className="min-h-screen bg-canvas">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 bg-white px-3 py-2">
        Skip to content
      </a>
      {mounted ? (
        <header className="sticky top-0 z-30 border-b border-black/20 bg-[#0A2748] text-white">
          <div className="flex h-16 items-center">
            <div className="flex h-full w-60 shrink-0 items-center px-4">
              <p className="whitespace-pre-line text-base font-semibold leading-tight tracking-tight">{PRODUCT.name.replace(" Intelligence", "\nIntelligence")}</p>
            </div>
            <div className="ml-auto flex items-center gap-4 px-4">
            <NotificationMenu items={notes.data?.items ?? []} />
            <ProfileMenu user={user.data} />
            <Button variant="ghost" className="text-white hover:bg-white/10" onClick={() => logout.mutate()} aria-label="Log out">
              <LogOut className="h-4 w-4" />
            </Button>
            </div>
          </div>
        </header>
      ) : (
        <header className="sticky top-0 z-30 border-b border-black/20 bg-[#0A2748]" aria-hidden>
          <div className="h-16" />
        </header>
      )}
      <div className="flex">
        <nav
          className={cn(
            "min-h-[calc(100vh-4rem)] w-60 border-r border-white/10 bg-[#0A2748] p-3",
          )}
          aria-label="Primary"
        >
          <ul className="space-y-1">
            {NAV.map((item) => {
              const href = item.href;
              const active =
                item.href === "/children"
                  ? pathname.startsWith("/children")
                  : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <li key={item.href}>
                  <Link
                    href={href}
                    className={cn(
                      "flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm",
                      active ? "bg-[#EAF2FA] text-[#0A2748] font-medium" : "text-white/80 hover:bg-white/10",
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <main id="main" className="min-w-0 flex-1 overflow-x-auto p-6">
          {children}
        </main>
      </div>
      {mounted ? <CommandPalette /> : null}
    </div>
  );
}

function ProfileMenu({ user }: { user?: User }) {
  const [open, setOpen] = useState(false);
  const name = user?.full_name ?? "…";
  const role = user?.role?.replaceAll("_", " ");
  return (
    <div className="relative flex items-center gap-2">
      <p className="text-sm font-medium">{name}</p>
      <button
        type="button"
        className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
        onClick={() => setOpen((v) => !v)}
        aria-label="Open profile"
        aria-expanded={open}
      >
        <UserRound className="h-5 w-5" />
      </button>
      {open ? (
        <div className="absolute right-0 top-12 w-80 rounded-2xl border border-line bg-white p-4 text-left text-[#0A2748] shadow-card">
          <p className="text-sm font-semibold">{name}</p>
          {role ? <p className="mt-1 text-xs capitalize text-[#64748b]">{role}</p> : null}
          {user?.qualifications ? (
            <div className="mt-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#64748b]">Qualifications</p>
              <p className="mt-1 text-sm">{user.qualifications}</p>
            </div>
          ) : null}
          {user?.experience ? (
            <div className="mt-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[#64748b]">Experience</p>
              <p className="mt-1 text-sm leading-5">{user.experience}</p>
            </div>
          ) : null}
          {user?.email ? <p className="mt-3 text-xs text-[#64748b]">{user.email}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

function notificationTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

function NotificationMenu({ items }: { items: { id: string; title: string; severity: string; created_at: string }[] }) {
  const [open, setOpen] = useState(false);
  const critical = items.filter((i) => i.severity === "HIGH" || i.severity === "URGENT");
  const countLabel = items.length > 9 ? "9+" : String(items.length);
  return (
    <div className="relative">
      <button
        type="button"
        className="relative rounded-lg p-2 text-white/90 hover:bg-white/10"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {items.length > 0 ? (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-clinical-danger px-1 text-[10px] font-semibold leading-none text-white">
            {countLabel}
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="absolute right-0 mt-2 w-[22rem] overflow-hidden rounded-2xl border border-line bg-white text-[#0A2748] shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]">
          <div className="border-b border-line bg-[#f7f9fc] px-4 py-3">
            <p className="text-sm font-semibold">Notifications</p>
          </div>
          <div className="max-h-96 space-y-4 overflow-y-auto p-3">
            <section>
              <p className="px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Critical</p>
              {critical.length === 0 ? (
                <p className="mt-2 rounded-xl bg-[#f8fafc] px-3 py-3 text-sm text-muted">No critical alerts require your attention.</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {critical.slice(0, 4).map((n) => (
                    <li key={`critical-${n.id}`} className="rounded-xl border border-red-100 bg-red-50 px-3 py-2.5">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-clinical-danger">{n.severity}</p>
                      <p className="mt-0.5 text-sm leading-5">{n.title}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section>
              <p className="px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Today</p>
              {items.length === 0 ? (
                <p className="mt-2 rounded-xl bg-[#f8fafc] px-3 py-3 text-sm text-muted">Nothing new today.</p>
              ) : (
                <ul className="mt-2 space-y-1">
                  {items.slice(0, 6).map((n) => (
                    <li key={`today-${n.id}`} className="flex items-start justify-between gap-3 rounded-xl px-3 py-2.5 hover:bg-[#f7f9fc]">
                      <p className="text-sm leading-5">{n.title}</p>
                      <span className="shrink-0 pt-0.5 text-[11px] tabular-nums text-muted">{notificationTime(n.created_at)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      ) : null}
    </div>
  );
}
