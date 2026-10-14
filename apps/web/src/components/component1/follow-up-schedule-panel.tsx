"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Calendar } from "lucide-react";
import { api } from "@/services/component4/httpClient";
import { Button } from "@/components/common/button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { Input, Label } from "@/components/common/field";
import { formatStatus } from "@/utils/utils";
import { toast } from "sonner";

function followUpStatusLabel(status?: string | null) {
  if (!status) return null;
  if (status === "SUGGESTED") return "Suggested";
  return formatStatus(status);
}

export function FollowUpSchedulePanel({
  childId,
  followUpId,
  nextFollowUp,
  followUpStatus,
  compact = false,
}: {
  childId: string;
  followUpId?: string | null;
  nextFollowUp?: string | null;
  followUpStatus?: string | null;
  compact?: boolean;
}) {
  const qc = useQueryClient();
  const defaultDate = nextFollowUp ?? new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  const [expectedDate, setExpectedDate] = useState(defaultDate);
  const [intervalDays, setIntervalDays] = useState(30);
  const [notes, setNotes] = useState("");
  const [open, setOpen] = useState(false);
  const suggested = followUpStatus === "SUGGESTED";

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["child", childId] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["follow-ups"] });
  };

  const schedule = useMutation({
    mutationFn: () => {
      if (followUpId) {
        return api(`/follow-ups/${followUpId}`, {
          method: "PATCH",
          body: JSON.stringify({ expected_date: expectedDate, notes: notes || null }),
        });
      }
      return api(`/children/${childId}/follow-ups`, {
        method: "POST",
        body: JSON.stringify({ expected_date: expectedDate, interval_days: intervalDays, notes: notes || null }),
      });
    },
    onSuccess: () => {
      toast.success(followUpId ? "Follow-up date updated" : "Follow-up scheduled");
      invalidate();
      setOpen(false);
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Unable to schedule follow-up"),
  });

  const confirm = useMutation({
    mutationFn: () => {
      if (!followUpId) throw new Error("No follow-up to confirm");
      return api(`/follow-ups/${followUpId}/confirm`, { method: "POST", body: JSON.stringify({}) });
    },
    onSuccess: () => {
      toast.success("Follow-up confirmed");
      invalidate();
    },
    onError: (err) => toast.error(err instanceof Error ? err.message : "Unable to confirm follow-up"),
  });

  const formFields = (
    <div className="grid gap-3 rounded-xl border border-line bg-canvas p-4">
      <div>
        <Label htmlFor="fu-date">Expected date</Label>
        <Input id="fu-date" type="date" value={expectedDate} onChange={(e) => setExpectedDate(e.target.value)} />
      </div>
      {!followUpId ? (
        <div>
          <Label htmlFor="fu-interval">Interval (days)</Label>
          <Input
            id="fu-interval"
            type="number"
            min={7}
            max={180}
            value={intervalDays}
            onChange={(e) => setIntervalDays(Number(e.target.value))}
          />
        </div>
      ) : null}
      <div>
        <Label htmlFor="fu-notes">Clinical note (optional)</Label>
        <Input id="fu-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      <div className="flex gap-2">
        <Button onClick={() => schedule.mutate()} disabled={schedule.isPending}>
          {schedule.isPending ? "Saving…" : "Save follow-up"}
        </Button>
        <Button variant="secondary" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </div>
  );

  const actions = open ? (
    formFields
  ) : (
    <div className="flex flex-wrap gap-2">
      {suggested && followUpId ? (
        <Button className="h-9 text-xs" onClick={() => confirm.mutate()} disabled={confirm.isPending}>
          {confirm.isPending ? "Confirming…" : "Confirm Follow-Up"}
        </Button>
      ) : null}
      <Button variant="secondary" className={compact ? "h-9 text-xs" : undefined} onClick={() => setOpen(true)}>
        {nextFollowUp ? "Change Date" : "Schedule follow-up"}
      </Button>
    </div>
  );

  if (compact) {
    return <div className="text-sm">{actions}</div>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="h-4 w-4" aria-hidden />
          Follow-up
        </CardTitle>
        <p className="text-sm text-muted">Schedule the next clinic review. Missed follow-ups generate workflow alerts.</p>
      </CardHeader>
      <CardBody className="space-y-4 pb-6 text-sm">
        <div>
          <p className="text-muted">{suggested ? "Suggested follow-up" : "Next scheduled follow-up"}</p>
          <p className="font-medium">{nextFollowUp ? new Date(nextFollowUp).toLocaleDateString() : "Not scheduled"}</p>
          {followUpStatus ? <p className="mt-1 text-muted">Status: {followUpStatusLabel(followUpStatus)}</p> : null}
        </div>
        {actions}
      </CardBody>
    </Card>
  );
}
