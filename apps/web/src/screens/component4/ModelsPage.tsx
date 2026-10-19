"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { EmptyState, Skeleton } from "@/components/common/states";

const ARCHITECTURE_FLOW = [
  ["Multimodal child data", "Growth history, feeding, supplementation, household context"],
  ["Rolling 12-month snapshot", "Each visit becomes an origin; the outcome is observed 12 months later"],
  ["Base experts", "Logistic Regression · Random Forest · XGBoost · LightGBM"],
  ["GA-RGCA v4 neural ensemble", "Three members with gated attention over the four modalities"],
  ["SuperLearner fusion", "Weighted combination of expert outputs"],
  ["Calibration", "Probability calibration before display"],
  ["12-month nutritional risk", "Underweight · Stunting · MAM · SAM probabilities, severity and review signal"],
] as const;

const RESEARCH_METRICS: [string, string][] = [
  ["Mean output accuracy", "94.62%"],
  ["Balanced accuracy", "84.91%"],
  ["Sensitivity", "74.15%"],
  ["Specificity", "95.67%"],
  ["Macro PR-AUC", "78.41%"],
  ["Macro ROC-AUC", "97.36%"],
  ["Multilabel exact match", "82.56%"],
  ["Hamming loss", "5.38%"],
  ["Acute classification accuracy", "93.32%"],
  ["Acute macro-F1", "71.02%"],
  ["Severity accuracy", "86.04%"],
  ["Severity balanced accuracy", "73.56%"],
  ["Severity macro-F1", "74.97%"],
  ["Severity log loss", "0.3439"],
];

const LIMITATIONS = [
  "Research decision-support prototype",
  "Clinician confirmation required",
  "One historical 12-month origin validated",
  "Repeated rolling-origin prospective validation required",
  "External prospective validation required",
  "Context timing limitations",
  "Incident SAM underpowered",
  "Applicability/OOD signal not externally validated",
];

export default function ModelsPage() {
  const comparison = useQuery({
    queryKey: ["model-comparison"],
    queryFn: () =>
      api<{ message?: string; models?: Record<string, { f1_macro?: number; recall_macro?: number; balanced_accuracy?: number; latency_ms?: number; brier?: number }>; context?: string }>(
        "/research/model-comparison",
      ),
  });
  const models = useQuery({
    queryKey: ["models"],
    queryFn: () => api<{ model_key: string; version: string; architecture: string; status: string; is_demo: boolean }[]>("/models"),
  });
  const ga = useQuery({
    queryKey: ["ga-rgca-status"],
    queryFn: () =>
      api<{ ga_rgca_loaded: boolean; ga_rgca_error?: string | null; ga_rgca_required_files?: string[]; active_model?: string | null; prediction_source?: string | null; model_version?: string; configured_model_mode?: string }>(
        "/runtime/ga-rgca",
      ),
  });
  const data = comparison.data;
  const rows = data?.models ? Object.entries(data.models) : [];
  return (
    <div className="space-y-5">
      <header>
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#3E75B8]">Intelligence</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[#102A4C]">Model Intelligence</h1>
        <p className="mt-1 text-sm text-[#5C6E82]">What the 12-month prediction model is, how it was evaluated, and where it must not be over-read.</p>
      </header>

      <section className="rounded-[28px] bg-[#0E243D] p-6 text-white shadow-elevated">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#58D3CA]">Active model</p>
        <h2 className="mt-1 text-xl font-semibold">GA-RGCA v4 Rolling SuperLearner</h2>
        {ga.isLoading ? (
          <p className="mt-3 text-sm text-white/70">Checking whether GA-RGCA-v4-Rolling-RSL is loaded.</p>
        ) : ga.data?.ga_rgca_loaded ? (
          <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Version", "GA-RGCA-v4-Rolling-RSL"],
              ["Rolling origin", "Yes"],
              ["Horizon", "12 months"],
              ["Neural ensemble members", "3"],
              ["Experts", "Logistic Regression, Random Forest, XGBoost, LightGBM, GA-RGCA v4"],
              ["Clinical use", "Research decision-support prototype"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl bg-white/5 px-4 py-3">
                <dt className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/60">{label}</dt>
                <dd className="mt-1 text-sm font-medium">{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-3 text-sm text-[#F3C97A]">{ga.data?.ga_rgca_error ?? "GA-RGCA-v4-Rolling-RSL is not loaded. New visits cannot be scored until the model is available."}</p>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Architecture</CardTitle>
        </CardHeader>
        <CardBody>
          <ol className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {ARCHITECTURE_FLOW.map(([title, detail], i) => (
              <li key={title} className="relative rounded-2xl border border-[#D7E2EC] bg-[#F4F7FA] p-4">
                <span className="absolute right-3 top-3 text-[10px] font-semibold text-[#45C4BB]">{String(i + 1).padStart(2, "0")}</span>
                <p className="pr-6 text-sm font-semibold text-[#102A4C]">{title}</p>
                <p className="mt-1 text-xs text-[#5C6E82]">{detail}</p>
              </li>
            ))}
          </ol>
          <p className="mt-3 text-xs text-[#5C6E82]">Illustration of the stored pipeline. This is not a live trace of any individual prediction.</p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Research evaluation on the study dataset</CardTitle>
        </CardHeader>
        <CardBody>
          <dl className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
            {RESEARCH_METRICS.map(([label, value]) => (
              <div key={label} className="rounded-2xl bg-[#F4F7FA] px-3 py-3">
                <dt className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#5C6E82]">{label}</dt>
                <dd className="mt-1 text-lg font-semibold tabular-nums text-[#102A4C]">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs leading-relaxed text-[#5C6E82]">
            These results come from evaluation on the study dataset. They do not constitute prospective clinical validation, and they are not live clinical accuracy.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Limitations</CardTitle>
        </CardHeader>
        <CardBody>
          <ul className="grid gap-2 sm:grid-cols-2">
            {LIMITATIONS.map((item) => (
              <li key={item} className="flex items-start gap-2 rounded-2xl bg-[#FBF3E4] px-4 py-2.5 text-sm text-[#7A4E0E]">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#E8AE4E]" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Registered models</CardTitle>
        </CardHeader>
        <CardBody>
          {models.isLoading ? (
            <Skeleton className="h-16" />
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-[#5C6E82]">
                  <th className="py-2">Model</th>
                  <th>Architecture</th>
                  <th>Status</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {(models.data ?? [])
                  .filter((m) => !m.is_demo && m.version === "GA-RGCA-v4-Rolling-RSL")
                  .map((m) => (
                    <tr key={m.model_key + m.version} className="border-t border-line">
                      <td className="py-2">{m.model_key}-{m.version}</td>
                      <td>{m.architecture}</td>
                      <td>
                        {m.status}
                        {m.status === "CANDIDATE" ? <span className="ml-2 text-xs text-[#b45309]">C4 proposal — activation required</span> : null}
                      </td>
                      <td className="max-w-xs truncate text-xs text-[#64748b]">{(m as { notes?: string }).notes ?? "—"}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
          <p className="mt-3 text-xs leading-relaxed text-[#64748b]">
            Research evaluation only. These figures are not live clinical accuracy. The deployed model is a decision-support prototype and still requires clinician confirmation.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Historical research comparison</CardTitle>
        </CardHeader>
        <CardBody>
          <p className="mb-3 text-sm text-muted">{data?.context ?? "Model performance metrics for registered inference versions."}</p>
          {rows.length === 0 ? (
            <EmptyState title="No experimental result available" body="Run python -m ml.training.train_baselines to generate metrics. Numbers are never fabricated." />
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  <th>Model</th>
                  <th className="text-right">Macro F1</th>
                  <th className="text-right">Recall</th>
                  <th className="text-right">Balanced accuracy</th>
                  <th className="text-right">Latency</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(([name, m]) => (
                  <tr key={name} className="border-t border-line">
                    <td className="py-2">{name}</td>
                    <td className="text-right">{m.f1_macro?.toFixed(3) ?? "—"}</td>
                    <td className="text-right">{m.recall_macro?.toFixed(3) ?? "—"}</td>
                    <td className="text-right">{m.balanced_accuracy?.toFixed(3) ?? "—"}</td>
                    <td className="text-right">{m.latency_ms ? `${m.latency_ms.toFixed(1)} ms` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
