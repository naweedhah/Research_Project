"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import {
  DEMO_DISPLAY_SEMANTICS,
  getModelOutputDisplayMetadata,
  type ModelDisplaySemantics,
} from "@/data/model-display";
import { cn } from "@/utils/utils";

export function DemoBanner({ compact }: { compact?: boolean }) {
  const { data } = useQuery({
    queryKey: ["runtime-model-display"],
    queryFn: () => api<ModelDisplaySemantics>("/runtime/model-display"),
    staleTime: 60_000,
    retry: 1,
  });
  // Prefer backend semantics; fall back to demo defaults if the route is unavailable.
  const semantics = data ?? getModelOutputDisplayMetadata({ model_is_demo: true });

  if (semantics.clinical_use) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "border-b border-white/15 bg-[#123A5C] text-white",
        compact ? "px-4 py-1.5" : "px-4 py-2",
      )}
      data-testid="research-demo-banner"
    >
      <p className="text-xs font-semibold tracking-wide">{semantics.banner_title}</p>
      <p className="text-[11px] text-white/80">{semantics.banner_subtitle}</p>
    </div>
  );
}

export function ResearchDisclaimer({ semantics }: { semantics?: ModelDisplaySemantics }) {
  const s = semantics ?? DEMO_DISPLAY_SEMANTICS;
  return (
    <p className="text-xs text-muted" data-testid="research-disclaimer">
      {s.report_disclaimer}
    </p>
  );
}
