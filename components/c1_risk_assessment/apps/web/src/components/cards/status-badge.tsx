import { cn, formatStatus } from "@/utils/utils";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CheckCircle2, Minus, ShieldAlert } from "lucide-react";

const styles: Record<string, string> = {
  improving: "bg-emerald-50 text-clinical-ok border-emerald-200",
  stable: "bg-slate-50 text-slate-700 border-slate-200",
  baseline: "bg-slate-50 text-slate-700 border-slate-200",
  stagnating: "bg-amber-50 text-clinical-warning border-amber-200",
  deteriorating: "bg-red-50 text-clinical-danger border-red-200",
  wasting: "bg-red-50 text-clinical-danger border-red-200",
  stunting: "bg-amber-50 text-clinical-warning border-amber-200",
  underweight: "bg-amber-50 text-clinical-warning border-amber-200",
  normal: "bg-emerald-50 text-clinical-ok border-emerald-200",
  mam: "bg-amber-50 text-clinical-warning border-amber-200",
  sam: "bg-red-50 text-clinical-danger border-red-200",
  severe: "bg-red-50 text-clinical-danger border-red-200",
  moderate: "bg-amber-50 text-clinical-warning border-amber-200",
  OPEN: "bg-amber-50 text-clinical-warning border-amber-200",
  HIGH: "bg-red-50 text-clinical-danger border-red-200",
  URGENT: "bg-red-50 text-clinical-danger border-red-200",
};

const icons: Record<string, typeof CheckCircle2> = {
  improving: ArrowUpRight,
  deteriorating: ArrowDownRight,
  stagnating: AlertTriangle,
  stable: Minus,
  severe: ShieldAlert,
};

export function StatusBadge({ value, className }: { value?: string | null; className?: string }) {
  if (!value) return <span className="text-muted">—</span>;
  const key = value.toLowerCase();
  const Icon = icons[key] ?? CheckCircle2;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium", styles[key] || styles[value] || "bg-slate-50 text-slate-700 border-slate-200", className)}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {formatStatus(value)}
    </span>
  );
}
