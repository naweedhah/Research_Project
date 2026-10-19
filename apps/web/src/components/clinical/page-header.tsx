"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { cn } from "@/utils/utils";

export function PageHeader({ kicker, title, purpose, action }: { kicker: string; title: string; purpose: string; action?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#3E75B8]">{kicker}</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[#102A4C]">{title}</h1>
        <p className="mt-1 max-w-2xl text-sm text-[#5C6E82]">{purpose}</p>
      </div>
      {action}
    </header>
  );
}

const ADMIN_LINKS = [
  ["/admin/system", "System"],
  ["/admin/users", "Users"],
  ["/admin/security", "Security"],
  ["/admin/settings", "Settings"],
] as const;

export function AdminNav() {
  const pathname = usePathname() ?? "";
  return (
    <nav className="inline-flex flex-wrap rounded-full border border-white/70 bg-white/75 p-1 shadow-card backdrop-blur-xl" aria-label="Administration">
      {ADMIN_LINKS.map(([href, label]) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn("rounded-full px-4 py-1.5 text-sm font-medium transition", active ? "bg-[#102A4C] text-white" : "text-[#5C6E82] hover:text-[#102A4C]")}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
