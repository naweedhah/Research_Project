"use client";

import { Component, type ReactNode } from "react";
import { Box } from "lucide-react";

export function ModelFallback({
  message = "3D model unavailable",
  dark = false,
  compact = false,
}: {
  message?: string;
  dark?: boolean;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex h-full w-full flex-col items-center justify-center gap-3 bg-transparent text-center ${
        compact ? "min-h-0 px-2 py-3" : "min-h-[360px] px-6"
      }`}
    >
      <div
        className={
          dark
            ? "flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/15 text-blue-400 ring-1 ring-blue-400/25"
            : "flex h-14 w-14 items-center justify-center rounded-2xl bg-[#eef2ff] text-[#2563eb]"
        }
      >
        <Box className={compact ? "h-5 w-5" : "h-7 w-7"} aria-hidden />
      </div>
      {compact ? null : <p className={dark ? "max-w-xs text-sm text-slate-400" : "max-w-xs text-sm text-[#64748b]"}>{message}</p>}
    </div>
  );
}

type BoundaryProps = { fallback: ReactNode; children: ReactNode; onError?: () => void };

export class ModelErrorBoundary extends Component<BoundaryProps, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch() {
    this.props.onError?.();
  }

  render() {
    if (this.state.failed) return this.props.fallback;
    return this.props.children;
  }
}
