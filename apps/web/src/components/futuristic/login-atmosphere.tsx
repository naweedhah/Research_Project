"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { motionTokens } from "./motion-tokens";

const LoginScene = dynamic(() => import("./login-scene"), { ssr: false });

const LABELS = ["Growth", "Nutrition", "WHO assessment", "12-month risk"];

export function LoginAtmosphere() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return (
    <div className="relative h-full w-full bg-[#0E243D] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_20%,rgba(69,196,187,0.22),transparent_55%),radial-gradient(ellipse_at_80%_80%,rgba(62,117,184,0.25),transparent_55%)]" />
      <div className="absolute inset-0">
        <LoginScene reduced={reduced} />
      </div>
      <ul className="pointer-events-none absolute inset-0" aria-hidden>
        {LABELS.map((label, i) => (
          <motion.li
            key={label}
            className="absolute rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[11px] font-medium tracking-wide backdrop-blur-md"
            style={{ left: `${18 + i * 18}%`, top: `${22 + (i % 2) * 48}%` }}
            initial={{ opacity: 0, y: 8 }}
            animate={reduced ? { opacity: 1, y: 0 } : { opacity: 1, y: [0, -6, 0] }}
            transition={reduced ? { duration: 0 } : { duration: 4 + i, repeat: Infinity, ease: "easeInOut", delay: i * 0.3 }}
          >
            {label}
          </motion.li>
        ))}
      </ul>
      <motion.div
        className="absolute bottom-14 left-12 max-w-md"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: motionTokens.hero, ease: motionTokens.ease }}
      >
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#58D3CA]">Paediatric nutrition intelligence</p>
        <p className="mt-3 text-3xl font-semibold leading-tight">Current health, then the next 12 months.</p>
        <p className="mt-2 text-sm text-white/70">Research decision-support prototype. Clinician confirmation required.</p>
      </motion.div>
    </div>
  );
}
