"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ageMonthsAtVisit, type ChildProfile } from "@/data/child-profile";
import { predictionLabel, whoLabelForVisit } from "@/data/clinical-selectors";
import { formatClinicalDate } from "@/utils/utils";
import { motionTokens } from "./motion-tokens";

export function VisitMotionTimeline({ profile }: { profile: ChildProfile }) {
  const reduce = useReducedMotion();
  const visits = profile.visits;
  if (visits.length === 0) return <p className="text-sm text-[#5C6E82]">No recorded visits yet.</p>;
  return (
    <div>
      <ol className="flex gap-3 overflow-x-auto pb-2" aria-label="Recorded visits">
        {visits.map((visit, index) => (
          <motion.li
            key={visit.id}
            className="relative min-w-[220px] flex-1 rounded-[22px] border border-white/80 bg-white/80 p-4 shadow-card backdrop-blur-xl"
            initial={reduce ? false : { opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: motionTokens.card, ease: motionTokens.ease, delay: index * motionTokens.stagger }}
          >
            <span className="absolute -top-1.5 left-5 h-3 w-3 rounded-full bg-[#45C4BB] ring-4 ring-white" aria-hidden />
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#3E75B8]">Visit {visit.visit_number}</p>
            <p className="mt-1 text-sm font-semibold text-[#102A4C]">{formatClinicalDate(visit.visit_date)}</p>
            <p className="text-xs text-[#5C6E82]">{ageMonthsAtVisit(profile.date_of_birth, visit.visit_date, profile.age_months)} months</p>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div>
                <dt className="text-[#5C6E82]">Weight</dt>
                <dd className="font-semibold tabular-nums text-[#102A4C]">{visit.measurements?.weight_kg != null ? `${visit.measurements.weight_kg} kg` : "—"}</dd>
              </div>
              <div>
                <dt className="text-[#5C6E82]">Height</dt>
                <dd className="font-semibold tabular-nums text-[#102A4C]">{visit.measurements?.height_cm != null ? `${visit.measurements.height_cm} cm` : "—"}</dd>
              </div>
            </dl>
            <div className="mt-3 space-y-1.5">
              <p className="rounded-xl bg-[#F4F7FA] px-2.5 py-1.5 text-xs text-[#102A4C]">
                <span className="block text-[10px] uppercase tracking-[0.12em] text-[#5C6E82]">WHO assessment at this visit</span>
                {whoLabelForVisit(profile, visit)}
              </p>
              <p className="rounded-xl bg-[#0E243D] px-2.5 py-1.5 text-xs text-white">
                <span className="block text-[10px] uppercase tracking-[0.12em] text-[#58D3CA]">12-month prediction generated at this visit</span>
                {predictionLabel(visit.prediction)}
              </p>
            </div>
          </motion.li>
        ))}
      </ol>
      <p className="mt-2 text-xs text-[#5C6E82]">Recorded visits only. Earlier forecasts stay attached to the visit that produced them.</p>
    </div>
  );
}
