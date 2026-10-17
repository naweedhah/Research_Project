"use client";

import { Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/common/button";

export function RecordActions({
  onEdit,
  onDelete,
  editLabel,
  deleteLabel,
}: {
  onEdit: () => void;
  onDelete: () => void;
  editLabel: string;
  deleteLabel: string;
}) {
  return (
    <span className="inline-flex items-center gap-0.5">
      <button
        type="button"
        aria-label={editLabel}
        title={editLabel}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onEdit();
        }}
        className="rounded-lg p-1.5 text-[#64748b] hover:bg-[#eef2ff] hover:text-[#2563eb]"
      >
        <Pencil className="h-4 w-4" />
      </button>
      <button
        type="button"
        aria-label={deleteLabel}
        title={deleteLabel}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onDelete();
        }}
        className="rounded-lg p-1.5 text-[#64748b] hover:bg-red-50 hover:text-red-700"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </span>
  );
}

export function ConfirmAction({
  open,
  title,
  message,
  confirmLabel,
  busy,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <button type="button" className="absolute inset-0 bg-[#0A2748]/40" aria-label="Cancel" onClick={onCancel} />
      <div role="dialog" aria-modal="true" className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-[#0f2744]">{title}</h2>
        <p className="mt-2 text-sm text-[#475569]">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button type="button" className="bg-red-700 text-white hover:bg-red-800" onClick={onConfirm} disabled={busy}>
            {busy ? "Removing…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
