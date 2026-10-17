"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { displayedMalnutritionType, type ChildProfile, type ModalityCount } from "@/data/child-profile";
import { cn, formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";

const MODALITY_LABELS: Record<string, string> = {
  anthropometric: "Anthropometric",
  socioeconomic: "Socioeconomic",
  dietary: "Dietary",
  maternal_child_health: "Maternal / child health",
};

function FieldLabel({ children }: { children: string }) {
  return <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#64748b]">{children}</p>;
}

export function ExplainabilityTrigger({
  profile,
  label = "Explainability",
  className,
}: {
  profile: ChildProfile;
  label?: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        className={cn(
          "shrink-0 rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-medium text-[#0f2744] hover:bg-[#f8fafc]",
          className,
        )}
        onClick={() => setOpen(true)}
      >
        {label}
      </button>
      <ExplainabilityDialog profile={profile} open={open} onClose={() => setOpen(false)} />
    </>
  );
}

export function ExplainabilityDialog({
  profile,
  open,
  onClose,
}: {
  profile: ChildProfile;
  open: boolean;
  onClose: () => void;
}) {
  const prediction = profile.current?.prediction;
  const classes = prediction?.calibrated_status_probabilities ?? null;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  const modalities = profile.modalities
    ? (Object.entries(profile.modalities) as [string, ModalityCount][])
    : [];

  return (
    <div className="fixed inset-0 z-40 overflow-y-auto">
      <button
        type="button"
        className="absolute inset-0 bg-[#0A2748]/40 backdrop-blur-md"
        aria-label="Close explainability dialog"
        onClick={onClose}
      />
      <div className="relative flex min-h-full items-start justify-center px-4 py-10 sm:items-center sm:px-6 sm:py-12">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="explainability-title"
          className="relative w-full max-w-3xl"
        >
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 z-10 rounded-lg p-2 text-[#64748b] hover:bg-white hover:text-[#0A2748]"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="overflow-hidden rounded-2xl border border-[#e4ecf4] bg-white shadow-[0_24px_64px_-28px_rgba(10,39,72,0.45)]">
            <div className="border-b border-[#e4ecf4] bg-[#f7f9fc] px-6 py-5 pr-14">
              <h2 id="explainability-title" className="text-xl font-bold text-[#0f2744]">
                Advanced explainability
              </h2>
              <p className="mt-1 text-sm text-[#64748b]">
                Stored model outputs for this visit. Clinical review required.
              </p>
            </div>

            <div className="max-h-[min(70vh,36rem)] space-y-5 overflow-y-auto px-6 py-5">
              <section>
                <FieldLabel>Prediction being reviewed</FieldLabel>
                <p className="mt-1 text-sm font-medium text-[#0f2744]">
                  {formatNutritionalStatus(displayedMalnutritionType(prediction), prediction?.severity)}
                  {prediction?.risk != null ? ` · ${formatPercent(prediction.risk)}` : ""}
                </p>
                <p className="mt-1 text-xs text-[#64748b]">
                  {prediction?.ga_rgca
                    ? "Task: future nutritional-risk prediction from this visit. Research decision-support model — clinical confirmation required."
                    : "AI-assisted assessment from the measurements recorded at this visit. Clinical review required."}
                </p>
              </section>

              {prediction?.ga_rgca ? (
                <section>
                  <FieldLabel>Acute malnutrition status</FieldLabel>
                  <p className="mt-1 text-sm font-medium text-[#0f2744]">{prediction.ga_rgca.acute_status ?? "—"}</p>
                  <p className="mt-1 text-xs text-[#64748b]">
                    Acute status represents the model&apos;s Normal/MAM/SAM acute-malnutrition output and is separate from Underweight and Stunting prediction.
                  </p>
                </section>
              ) : null}

              <section>
                <FieldLabel>Modality Reliability</FieldLabel>
                {prediction?.ga_rgca?.modality_reliability ? (
                  <>
                    <ul className="mt-2 space-y-1 text-sm text-[#0f2744]">
                      <li>Historical growth {formatPercent(prediction.ga_rgca.modality_reliability.history)}</li>
                      <li>Socioeconomic {formatPercent(prediction.ga_rgca.modality_reliability.socioeconomic)}</li>
                      <li>Feeding {formatPercent(prediction.ga_rgca.modality_reliability.feeding)}</li>
                      <li>Supplementation {formatPercent(prediction.ga_rgca.modality_reliability.supplementation)}</li>
                    </ul>
                    <p className="mt-2 text-xs text-[#64748b]">
                      Modality reliability reflects how the GA-RGCA fusion mechanism weighted the quality and availability of each information source for this prediction. It is not a causal explanation or feature importance measure.
                    </p>
                  </>
                ) : (
                  <p className="mt-1 text-sm text-[#64748b]">No GA-RGCA modality reliability is stored for this visit.</p>
                )}
              </section>

              <section>
                <FieldLabel>Calibrated status probabilities</FieldLabel>
                {classes && Object.keys(classes).length > 0 ? (
                  <ul className="mt-2 space-y-2">
                    {Object.entries(classes).map(([key, value]) => (
                      <li key={key}>
                        <div className="mb-1 flex items-center justify-between text-xs">
                          <span className="text-[#0f2744]">{formatStatus(key)}</span>
                          <span className="tabular-nums text-[#475569]">{formatPercent(value)}</span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-[#e8eef5]">
                          <div
                            className="h-full rounded-full bg-[#0E3A67]"
                            style={{ width: `${Math.max(0, Math.min(100, Math.round(value * 100)))}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-sm text-[#64748b]">Calibrated class probabilities are not stored for this visit.</p>
                )}
                <p className="mt-2 text-xs text-[#64748b]">
                  These are stored model class outputs. They are not feature attributions and do not explain why a class
                  was selected.
                </p>
              </section>

              <section>
                <FieldLabel>Input coverage used by the model</FieldLabel>
                {modalities.length > 0 ? (
                  <ul className="mt-2 grid gap-2 sm:grid-cols-2">
                    {modalities.map(([key, row]) => (
                      <li key={key} className="rounded-xl bg-[#f8fafc] px-3 py-2.5 ring-1 ring-line/70">
                        <p className="text-sm font-medium text-[#0f2744]">{MODALITY_LABELS[key] ?? key}</p>
                        <p className="mt-0.5 text-xs text-[#64748b]">
                          {row.available} of {row.total} fields available
                        </p>
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white ring-1 ring-line/70">
                          <div
                            className="h-full rounded-full bg-[#2563eb]"
                            style={{ width: `${row.total ? Math.round((row.available / row.total) * 100) : 0}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-sm text-[#64748b]">No visit inputs stored.</p>
                )}
                <p className="mt-2 text-xs text-[#64748b]">Unavailable fields are Unknown / Not assessed, not equivalent to No.</p>
              </section>

              <section>
                <FieldLabel>Fusion attention</FieldLabel>
                <p className="mt-1 text-sm text-[#64748b]">Cross-attention weights are not stored for this visit.</p>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
