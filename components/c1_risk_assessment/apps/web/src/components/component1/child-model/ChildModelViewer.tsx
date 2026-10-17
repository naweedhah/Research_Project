"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { ModelErrorBoundary, ModelFallback } from "./ModelFallback";

const ChildModelScene = dynamic(
  () => import("./ChildModelScene").then((m) => m.ChildModelScene),
  {
    ssr: false,
    loading: () => <ModelFallback message="Loading 3D model…" />,
  },
);

function isWebGLAvailable() {
  if (typeof document === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export function ChildModelViewer({
  riskIntensity,
  className = "",
  darkStage = false,
  compact = false,
  neutral = false,
}: {
  riskIntensity?: number | null;
  className?: string;
  darkStage?: boolean;
  compact?: boolean;
  neutral?: boolean;
}) {
  const [webgl, setWebgl] = useState(true);
  const [failed, setFailed] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    setWebgl(isWebGLAvailable());
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReducedMotion(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const risk = riskIntensity ?? 0.5;

  return (
    <section className={`relative flex h-full min-h-0 flex-col ${className}`} aria-hidden>
      <div className={`relative h-full min-h-[inherit] flex-1 overflow-hidden ${compact ? "rounded-xl" : "rounded-2xl"}`}>
        {webgl && !failed ? (
          <ModelErrorBoundary fallback={<ModelFallback dark={darkStage} compact={compact} />} onError={() => setFailed(true)}>
            <ChildModelScene
              riskIntensity={risk}
              reducedMotion={reducedMotion}
              darkStage={darkStage}
              neutral={neutral}
              autoRotate={!compact && !reducedMotion}
              onContextLost={() => setFailed(true)}
            />
          </ModelErrorBoundary>
        ) : (
          <ModelFallback dark={darkStage} compact={compact} />
        )}
      </div>
    </section>
  );
}
