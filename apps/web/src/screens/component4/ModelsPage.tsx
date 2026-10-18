"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { EmptyState } from "@/components/common/states";

export default function ModelsPage() {
  const comparison = useQuery({ queryKey: ["model-comparison"], queryFn: () => api<{ message?: string; models?: Record<string, { f1_macro?: number; recall_macro?: number; balanced_accuracy?: number; latency_ms?: number; brier?: number }>; context?: string }>("/research/model-comparison") });
  const models = useQuery({ queryKey: ["models"], queryFn: () => api<{ model_key: string; version: string; architecture: string; status: string; is_demo: boolean }[]>("/models") });
  const ga = useQuery({
    queryKey: ["ga-rgca-status"],
    queryFn: () => api<{ ga_rgca_loaded: boolean; ga_rgca_error?: string | null; ga_rgca_required_files?: string[]; active_model?: string | null; prediction_source?: string | null; model_version?: string; configured_model_mode?: string }>("/runtime/ga-rgca"),
  });
  const data = comparison.data;
  const rows = data?.models ? Object.entries(data.models) : [];
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Model</h1>
      <Card>
        <CardHeader><CardTitle>GA-RGCA v4 Rolling SuperLearner</CardTitle></CardHeader>
        <CardBody className="space-y-2 text-sm">
          {ga.isLoading ? (
            <p>Checking whether GA-RGCA-v4-Rolling-RSL is loaded.</p>
          ) : ga.data?.ga_rgca_loaded ? (
            <dl className="grid gap-2 sm:grid-cols-2">
              <div><dt className="text-xs text-[#64748b]">Version</dt><dd>GA-RGCA-v4-Rolling-RSL</dd></div>
              <div><dt className="text-xs text-[#64748b]">Rolling origin</dt><dd>Yes</dd></div>
              <div><dt className="text-xs text-[#64748b]">Horizon</dt><dd>12 months</dd></div>
              <div><dt className="text-xs text-[#64748b]">Neural ensemble members</dt><dd>3</dd></div>
              <div className="sm:col-span-2"><dt className="text-xs text-[#64748b]">Experts</dt><dd>Logistic Regression, Random Forest, XGBoost, LightGBM, GA-RGCA v4</dd></div>
              <div className="sm:col-span-2"><dt className="text-xs text-[#64748b]">Clinical use</dt><dd>Research decision-support prototype</dd></div>
            </dl>
          ) : (
            <p>{ga.data?.ga_rgca_error ?? "GA-RGCA-v4-Rolling-RSL is not loaded. New visits cannot be scored until the model is available."}</p>
          )}
        </CardBody>
      </Card>
      <p className="text-sm text-muted">{data?.context ?? "Model performance metrics for registered inference versions."}</p>
      <Card>
        <CardHeader><CardTitle>Registered models</CardTitle></CardHeader>
        <CardBody>
          <table className="w-full text-left text-sm">
            <thead><tr><th>Model</th><th>Architecture</th><th>Status</th><th>Notes</th></tr></thead>
            <tbody>
              {(models.data ?? []).filter((m) => !m.is_demo && m.version === "GA-RGCA-v4-Rolling-RSL").map((m) => (
                <tr key={m.model_key + m.version} className="border-t border-line">
                  <td className="py-2">{m.model_key}-{m.version}</td>
                  <td>{m.architecture}</td>
                  <td>
                    {m.status}
                    {m.status === "CANDIDATE" ? (
                      <span className="ml-2 text-xs text-[#b45309]">C4 proposal — activation required</span>
                    ) : null}
                  </td>
                  <td className="max-w-xs truncate text-xs text-[#64748b]">{(m as { notes?: string }).notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-[#64748b]">
            Component 4 may register candidates only. Live model changes require authorized activation in C1 — never automatic.
          </p>
        </CardBody>
      </Card>
      <Card>
        <CardHeader><CardTitle>Historical research comparison</CardTitle></CardHeader>
        <CardBody>
          {rows.length === 0 ? <EmptyState title="No experimental result available" body="Run python -m ml.training.train_baselines to generate metrics. Numbers are never fabricated." /> : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  <th>Model</th><th className="text-right">Macro F1</th><th className="text-right">Recall</th>
                  <th className="text-right">Balanced accuracy</th><th className="text-right">Latency</th>
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
