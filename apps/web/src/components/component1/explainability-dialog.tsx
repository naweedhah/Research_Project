"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import {
  displayedMalnutritionType,
  formatHighestConditionRisk,
  predictedTypeChipProbability,
  type ChildProfile,
  type ModalityCount,
} from "@/data/child-profile";
import { cn, displayPredictedSeverity, formatNutritionalStatus, formatPercent, formatStatus } from "@/utils/utils";
import { applicabilityState, uncertaintyState } from "@/data/clinical-selectors";

const MODALITY_LABELS: Record<string, string> = {
  anthropometric: "Anthropometric",
  socioeconomic: "Socioeconomic",
  dietary: "Dietary",
  maternal_child_health: "Maternal / child health",
};

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#58D3CA]">{children}</p>;
}

export function ExplainabilityTrigger({
  profile,
  label = "AI Details",
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

  const ga = prediction?.ga_rgca;
  const uncertainty = uncertaintyState(prediction);
  const applicability = applicabilityState(prediction);
  const reliability = ga?.modality_reliability;
  const reliabilityRows = reliability
    ? [
        ["Growth history", reliability.history],
        ["Household / socioeconomic", reliability.socioeconomic],
        ["Feeding", reliability.feeding],
        ["Supplementation", reliability.supplementation],
      ]
    : [];
  const sevProbs = ga?.severity_probabilities;
  const severityLabel = displayPredictedSeverity(displayedMalnutritionType(prediction), ga?.severity ?? prediction?.severity);
  const futureBars: [string, number | undefined][] = ga
    ? [
        ["Underweight", ga.underweight_probability],
        ["Stunting", ga.stunting_probability],
        ["MAM", ga.mam_probability],
        ["SAM", ga.sam_probability],
      ]
    : [];

  return (
    <div className="fixed inset-0 z-40 overflow-y-auto">
      <button
        type="button"
        className="absolute inset-0 bg-[#0A2748]/50 backdrop-blur-md"
        aria-label="Close AI details"
        onClick={onClose}
      />
      <div className="relative flex min-h-full items-start justify-center px-4 py-10 sm:items-center sm:px-6 sm:py-12">
        <div role="dialog" aria-modal="true" aria-labelledby="explainability-title" className="relative w-full max-w-3xl">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 z-10 rounded-lg p-2 text-white/70 hover:bg-white/10 hover:text-white"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="overflow-hidden rounded-[28px] border border-white/10 bg-[#0E243D] text-white shadow-[0_32px_80px_-32px_rgba(4,18,38,0.8)]">
            <div className="border-b border-white/10 px-6 py-5 pr-14">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#58D3CA]">GA-RGCA intelligence</p>
              <h2 id="explainability-title" className="mt-1 text-xl font-semibold">
                AI Details
              </h2>
              <p className="mt-1 text-sm text-white/70">Stored outputs for the selected visit, in clinical language. Nothing here is recalculated.</p>
            </div>

            <div className="max-h-[min(72vh,40rem)] space-y-4 overflow-y-auto px-6 py-5">
              <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <FieldLabel>Prediction · next {ga?.prediction_horizon_months ?? 12} months</FieldLabel>
                <p className="mt-1 text-lg font-semibold">
                  {formatNutritionalStatus(displayedMalnutritionType(prediction), prediction?.severity)}
                  {predictedTypeChipProbability(prediction) != null ? <span className="ml-2 text-sm font-medium text-white/70">{formatPercent(predictedTypeChipProbability(prediction))}</span> : null}
                </p>
                {ga ? <p className="mt-1 text-xs text-white/70">Highest predicted condition risk: {formatHighestConditionRisk(prediction)}</p> : null}
                {futureBars.length ? (
                  <ul className="mt-3 space-y-2">
                    {futureBars.map(([label, value]) => (
                      <li key={label}>
                        <div className="mb-1 flex items-center justify-between text-xs">
                          <span>{label}</span>
                          <span className="tabular-nums text-white/70">{formatPercent(value)}</span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full rounded-full bg-[#45C4BB]" style={{ width: `${Math.max(0, Math.min(100, Math.round((value ?? 0) * 100)))}%` }} />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : null}
                <p className="mt-2 text-xs text-white/60">
                  {ga
                    ? "Stored probabilities for the 12-month horizon from this visit. This is a prediction, not the current WHO assessment."
                    : "AI-assisted assessment from the measurements recorded at this visit. Clinical review required."}
                </p>
              </section>

              {ga && (severityLabel || ga.triage) ? (
                <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  {severityLabel ? (
                    <>
                      <FieldLabel>Severity</FieldLabel>
                      <p className="mt-1 text-sm font-medium">{severityLabel}{ga.acute_status ? <span className="text-white/60"> · acute status {ga.acute_status}</span> : null}</p>
                      {sevProbs ? (
                        <p className="mt-1 text-xs text-white/70">
                          Normal {formatPercent(sevProbs.Normal ?? sevProbs.normal)} · Moderate {formatPercent(sevProbs.Moderate ?? sevProbs.moderate)} · Severe {formatPercent(sevProbs.Severe ?? sevProbs.severe)}
                        </p>
                      ) : null}
                    </>
                  ) : null}
                  {ga.triage ? <p className={severityLabel ? "mt-1 text-xs text-white/70" : "text-xs text-white/70"}>Review pathway: {ga.triage}</p> : null}
                </section>
              ) : null}

              {ga ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <FieldLabel>Model uncertainty</FieldLabel>
                    <p className={cn("mt-1 text-sm font-medium", uncertainty.flagged ? "text-[#F3C97A]" : "text-white")}>{uncertainty.label}</p>
                    <p className="mt-1 text-xs text-white/70">{uncertainty.detail}</p>
                    {ga.ensemble_variance != null ? <p className="mt-2 text-[11px] text-white/50">Ensemble variance {Number(ga.ensemble_variance).toFixed(4)}</p> : null}
                  </section>
                  <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <FieldLabel>Similarity to training population</FieldLabel>
                    <p className={cn("mt-1 text-sm font-medium", applicability.outside ? "text-[#F3C97A]" : "text-white")}>{applicability.label}</p>
                    <p className="mt-1 text-xs text-white/70">{applicability.detail}</p>
                  </section>
                  {ga.acute_conformal_prediction_set ? (
                    <section className="rounded-2xl border border-white/10 bg-white/5 p-4 sm:col-span-2">
                      <FieldLabel>Acute prediction set</FieldLabel>
                      <p className="mt-1 text-sm font-medium">{ga.acute_conformal_prediction_set.join(", ")}</p>
                      <p className="mt-1 text-xs text-white/70">Additional uncertainty information for the acute Normal/MAM/SAM prediction. It does not replace the acute status above.</p>
                    </section>
                  ) : null}
                </div>
              ) : null}

              <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <FieldLabel>Modality reliability</FieldLabel>
                {reliabilityRows.length ? (
                  <>
                    <ul className="mt-2 space-y-2">
                      {reliabilityRows.map(([label, value]) => (
                        <li key={String(label)}>
                          <div className="mb-1 flex items-center justify-between text-xs">
                            <span>{label}</span>
                            <span className="tabular-nums text-white/70">{formatPercent(value as number)}</span>
                          </div>
                          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                            <div className="h-full rounded-full bg-[#58D3CA]" style={{ width: `${Math.max(0, Math.min(100, Math.round(((value as number) ?? 0) * 100)))}%` }} />
                          </div>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-2 text-xs text-white/70" title="Reliability indicates how usable each information group was. It is not feature importance.">
                      Reliability indicates how usable each information group was for this prediction. It is not feature importance and not a causal explanation.
                    </p>
                  </>
                ) : (
                  <p className="mt-1 text-sm text-white/70">No modality reliability is stored for this visit.</p>
                )}
              </section>

              {classes && Object.keys(classes).length > 0 ? (
                <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <FieldLabel>Calibrated status probabilities</FieldLabel>
                  <ul className="mt-2 space-y-2">
                    {Object.entries(classes).map(([key, value]) => (
                      <li key={key}>
                        <div className="mb-1 flex items-center justify-between text-xs">
                          <span>{formatStatus(key)}</span>
                          <span className="tabular-nums text-white/70">{formatPercent(value)}</span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full rounded-full bg-[#3E75B8]" style={{ width: `${Math.max(0, Math.min(100, Math.round(value * 100)))}%` }} />
                        </div>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-white/60">Stored class outputs. They are not feature attributions.</p>
                </section>
              ) : null}

              <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <FieldLabel>Input coverage used by the model</FieldLabel>
                {modalities.length > 0 ? (
                  <ul className="mt-2 grid gap-2 sm:grid-cols-2">
                    {modalities.map(([key, row]) => (
                      <li key={key} className="rounded-xl bg-white/5 px-3 py-2.5">
                        <p className="text-sm font-medium">{MODALITY_LABELS[key] ?? key}</p>
                        <p className="mt-0.5 text-xs text-white/60">{row.available} of {row.total} fields available</p>
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full rounded-full bg-white/70" style={{ width: `${row.total ? Math.round((row.available / row.total) * 100) : 0}%` }} />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-sm text-white/70">No visit inputs stored.</p>
                )}
                <p className="mt-2 text-xs text-white/60">Unavailable fields are Unknown / Not assessed, not equivalent to No.</p>
              </section>

              <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <FieldLabel>Model identity</FieldLabel>
                <p className="mt-1 text-sm font-medium">{ga?.model_version ?? "Not stored"}</p>
                <p className="mt-1 text-xs text-white/70">{ga?.prediction_horizon_months ? `${ga.prediction_horizon_months}-month horizon from this visit. ` : ""}Research decision-support prototype. Clinician confirmation required.</p>
              </section>

              <section className="rounded-2xl border border-[#F3C97A]/30 bg-[#F3C97A]/10 p-4">
                <FieldLabel>Limitations</FieldLabel>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-white/80">
                  <li>One historical 12-month origin validated; repeated rolling-origin and external prospective validation are still required.</li>
                  <li>Incident SAM is underpowered in the study data.</li>
                  <li>The applicability and uncertainty signals are internal and not externally validated.</li>
                  <li>Cross-attention weights are not stored, so no feature-level explanation is shown.</li>
                </ul>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
