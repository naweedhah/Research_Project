"use client";

import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import type { ChildProfile } from "@/data/child-profile";
import { dataQualityState, measurementChange, predictionLabel, uncertaintyState, whoLabelForVisit } from "@/data/clinical-selectors";
import { cn } from "@/utils/utils";

export function DataQualityIndicator({ profile, className }: { profile: ChildProfile; className?: string }) {
  const state = dataQualityState(profile);
  const Icon = state.tone === "warn" ? AlertTriangle : state.tone === "ok" ? CheckCircle2 : Info;
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-2xl px-4 py-3 text-sm",
        state.tone === "warn" ? "bg-[#FBF3E4] text-[#7A4E0E]" : state.tone === "ok" ? "bg-[#E5F6F1] text-[#0C6B56]" : "bg-[#F4F7FA] text-[#5C6E82]",
        className,
      )}
      role="status"
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em]">Data quality · {state.label}</p>
        <p className="mt-0.5 text-xs leading-relaxed opacity-90">{state.detail}</p>
      </div>
    </div>
  );
}

/** Short structured summary. Every line is read from stored data; nothing is generated. */
export function ClinicalSummaryCard({ profile, visit }: { profile: ChildProfile; visit?: ChildProfile["current"] }) {
  const current = visit ?? profile.current;
  const previous = profile.previous;
  const weightDelta = measurementChange(current?.measurements?.weight_kg, previous?.measurements?.weight_kg, "kg");
  const heightDelta = measurementChange(current?.measurements?.height_cm, previous?.measurements?.height_cm, "cm");
  const uncertainty = uncertaintyState(current?.prediction);
  const rows: { label: string; value: string; tone?: "warn" }[] = [
    { label: "Current assessment", value: whoLabelForVisit(profile, current) },
    { label: "Next 12 months", value: predictionLabel(current?.prediction) },
    {
      label: "Growth since previous visit",
      value: weightDelta || heightDelta
        ? [weightDelta ? `Weight ${weightDelta.text}` : null, heightDelta ? `Height ${heightDelta.text}` : null].filter(Boolean).join(" · ")
        : "No previous visit to compare",
    },
    { label: "Model uncertainty", value: uncertainty.label, tone: uncertainty.flagged ? "warn" : undefined },
  ];
  if (current?.prediction?.ga_rgca?.triage) rows.push({ label: "Review pathway", value: current.prediction.ga_rgca.triage });
  return (
    <section className="rounded-[24px] border border-white/70 bg-white/80 p-5 shadow-card backdrop-blur-xl" aria-labelledby="clinical-summary-title">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#3E75B8]">Clinical summary</p>
      <h2 id="clinical-summary-title" className="mt-1 text-base font-semibold text-[#102A4C]">At a glance</h2>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        {rows.map((row) => (
          <div key={row.label} className="rounded-2xl bg-[#F4F7FA] px-4 py-3">
            <dt className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5C6E82]">{row.label}</dt>
            <dd className={cn("mt-1 text-sm font-semibold text-[#102A4C]", row.tone === "warn" && "text-[#8A5A12]")}>{row.value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-[#5C6E82]">Built from recorded measurements and the stored GA-RGCA-v4-Rolling-RSL output. Research decision-support prototype. Clinician confirmation required.</p>
    </section>
  );
}
