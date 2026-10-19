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

const NAV_GROUPS: { title: string; items: { href: string; label: string; icon: typeof Users }[] }[] = [
  { title: "Clinic", items: NAV },
];

function isActive(href: string, currentPath: string) {
  if (href === "/children") return currentPath.startsWith("/children");
  if (href === "/admin/system") return currentPath.startsWith("/admin");
  if (href === "/research/models") return currentPath.startsWith("/research");
  return currentPath.startsWith(href);
}

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

  const currentPath = pathname ?? "";
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 z-50 rounded-xl bg-white px-3 py-2">
        Skip to content
      </a>
      <div className="flex min-h-screen">
        <nav
          className="no-print sticky top-0 hidden h-screen w-[260px] shrink-0 flex-col overflow-y-auto bg-[#0E243D] p-4 text-white md:flex"
          aria-label="Primary"
        >
          <div className="px-2 pb-6 pt-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#45C4BB]">Clinical Intelligence</p>
            <p className="mt-2 text-xl font-bold leading-tight text-white">{PRODUCT.name}</p>
          </div>
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="mb-2">
              <ul className="flex flex-col gap-1.5">
                {group.items.map((item) => {
                  const active = isActive(item.href, currentPath);
                  const Icon = item.icon;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "flex min-h-[52px] items-center gap-4 rounded-2xl px-5 text-[17px] leading-tight transition",
                          active ? "bg-white font-semibold text-[#102A4C] shadow-card" : "text-white/80 hover:bg-white/10",
                        )}
                      >
                        <Icon className="h-5 w-5 shrink-0" />
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
          <div className="mt-auto flex justify-center pb-2 pt-4">
            <Button variant="ghost" className="text-white hover:bg-white/10" onClick={() => logout.mutate()} aria-label="Log out">
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </nav>
        <div className="flex min-w-0 flex-1 flex-col pb-20 md:pb-0">
          <header className="no-print sticky top-0 z-30 flex items-center justify-end gap-3 bg-[#0E243D] px-5 py-3 text-white">
            {mounted ? (
              <div className="flex items-center gap-2">
                <NotificationMenu items={notes.data?.items ?? []} />
                <ProfileMenu user={user.data} />
                <Button variant="ghost" className="text-white hover:bg-white/10 md:hidden" onClick={() => logout.mutate()} aria-label="Log out">
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <span className="h-9 w-24" />
            )}
          </header>
          <main id="main" className="min-w-0 flex-1 overflow-x-auto p-3 sm:p-4">
            {children}
          </main>
        </div>
      </div>
      <nav className="no-print fixed inset-x-0 bottom-0 z-40 border-t border-white/70 bg-white/90 px-2 py-2 backdrop-blur-xl md:hidden" aria-label="Primary mobile">
        <ul className="grid grid-cols-4 gap-1">
          {NAV.map((item) => {
            const active = isActive(item.href, currentPath);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn("flex flex-col items-center gap-1 rounded-2xl px-1 py-2 text-[11px]", active ? "bg-[#102A4C] text-white" : "text-[#5C6E82]")}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
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
      <p className="hidden truncate text-sm font-medium sm:block">{name}</p>
      <button
        type="button"
        className="flex h-9 w-9 items-center justify-center rounded-full bg-white/15 text-white hover:bg-white/25"
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
        className="relative rounded-lg p-2 text-current hover:bg-white/10"
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
