"use client";

import { useState } from "react";
import { ageMonthsAtVisit, type ChildProfile } from "@/data/child-profile";
import { measurementChange, predictionLabel, whoLabelForVisit } from "@/data/clinical-selectors";
import { formatClinicalDate } from "@/utils/utils";

export function VisitComparison({ profile }: { profile: ChildProfile }) {
  const visits = profile.visits;
  const [leftId, setLeftId] = useState(visits.length > 1 ? visits[visits.length - 2].id : visits[0]?.id ?? "");
  const [rightId, setRightId] = useState(visits[visits.length - 1]?.id ?? "");
  if (visits.length < 2) {
    return <p className="text-sm text-[#5C6E82]">Two recorded visits are needed before a side-by-side comparison is available.</p>;
  }
  const left = visits.find((v) => v.id === leftId) ?? visits[0];
  const right = visits.find((v) => v.id === rightId) ?? visits[visits.length - 1];
  const weight = measurementChange(right.measurements?.weight_kg, left.measurements?.weight_kg, "kg");
  const height = measurementChange(right.measurements?.height_cm, left.measurements?.height_cm, "cm");
  const rows = [
    ["Date", formatClinicalDate(left.visit_date), formatClinicalDate(right.visit_date)],
    ["Age", `${ageMonthsAtVisit(profile.date_of_birth, left.visit_date, profile.age_months)} mo`, `${ageMonthsAtVisit(profile.date_of_birth, right.visit_date, profile.age_months)} mo`],
    ["Weight", left.measurements?.weight_kg != null ? `${left.measurements.weight_kg} kg` : "—", right.measurements?.weight_kg != null ? `${right.measurements.weight_kg} kg${weight ? ` (${weight.text})` : ""}` : "—"],
    ["Height", left.measurements?.height_cm != null ? `${left.measurements.height_cm} cm` : "—", right.measurements?.height_cm != null ? `${right.measurements.height_cm} cm${height ? ` (${height.text})` : ""}` : "—"],
    ["Current WHO assessment", whoLabelForVisit(profile, left), whoLabelForVisit(profile, right)],
    ["12-month prediction at that visit", predictionLabel(left.prediction), predictionLabel(right.prediction)],
  ];
  const selector = (value: string, onChange: (v: string) => void, label: string) => (
    <label className="text-xs text-[#5C6E82]">
      <span className="sr-only">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="rounded-xl border border-[#D7E2EC] bg-white px-3 py-1.5 text-sm text-[#102A4C]">
        {visits.map((v) => (
          <option key={v.id} value={v.id}>
            Visit {v.visit_number} · {formatClinicalDate(v.visit_date)}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        {selector(left.id, setLeftId, "Earlier visit")}
        <span className="text-[#45C4BB]" aria-hidden>→</span>
        {selector(right.id, setRightId, "Later visit")}
      </div>
      <table className="mt-4 w-full text-left text-sm">
        <thead>
          <tr className="text-[11px] uppercase tracking-[0.12em] text-[#5C6E82]">
            <th className="py-2 pr-3 font-semibold">Item</th>
            <th className="py-2 pr-3 font-semibold">Visit {left.visit_number}</th>
            <th className="py-2 font-semibold">Visit {right.visit_number}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, a, b]) => (
            <tr key={label} className="border-t border-[#E8EFF5]">
              <td className="py-2.5 pr-3 text-[#5C6E82]">{label}</td>
              <td className="py-2.5 pr-3 font-medium text-[#102A4C]">{a}</td>
              <td className="py-2.5 font-medium text-[#102A4C]">{b}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-[#5C6E82]">Each prediction stays attached to the visit that produced it. Stored values are not changed by this comparison.</p>
    </div>
  );
}
