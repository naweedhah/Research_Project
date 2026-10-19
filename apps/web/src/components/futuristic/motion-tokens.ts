export const motionTokens = {
  ease: [0.16, 1, 0.3, 1] as const,
  micro: 0.18,
  card: 0.48,
  hero: 0.85,
  stagger: 0.06,
  spring: { type: "spring" as const, stiffness: 260, damping: 28 },
};
