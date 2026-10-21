import { Activity, HeartPulse, ShieldCheck, Map } from 'lucide-react';

export const BRAND = {
  name: 'Child Nutrition Decision Support',
  short: 'NutriSupport',
  tagline: 'Integrated research system · MOH / PHM',
};

/*
  One entry per research component. Class names are written out in full so Tailwind can see them.
  `status` is the backend endpoint each overview card reads.
*/
export const COMPONENTS = [
  {
    id: 'c1',
    number: 1,
    owner: 'Chanodya',
    title: 'Risk Assessment',
    full: 'Multimodal Early Detection and Risk Assessment',
    question: "What is this child's malnutrition risk?",
    icon: HeartPulse,
    path: '/c1',
    status: '/risk/status',
    text: 'text-c1',
    bg: 'bg-c1',
    soft: 'bg-c1/10',
    ring: 'ring-c1/30',
    border: 'border-c1',
  },
  {
    id: 'c2',
    number: 2,
    owner: 'Shamiq',
    title: 'Interventions',
    full: 'Personalized Counterfactual Intervention Engine',
    question: 'What feasible changes could improve the outlook?',
    icon: Activity,
    path: '/c2',
    status: '/interventions/status',
    text: 'text-c2',
    bg: 'bg-c2',
    soft: 'bg-c2/10',
    ring: 'ring-c2/30',
    border: 'border-c2',
  },
  {
    id: 'c3',
    number: 3,
    owner: 'Naweed',
    title: 'Model Reliability',
    full: 'Adaptive Model Reliability Monitoring and Safe Maintenance',
    question: 'Can the deployed model still be trusted?',
    icon: ShieldCheck,
    path: '/c3',
    status: '/maintenance/status',
    text: 'text-c3',
    bg: 'bg-c3',
    soft: 'bg-c3/10',
    ring: 'ring-c3/30',
    border: 'border-c3',
  },
  {
    id: 'c4',
    number: 4,
    owner: 'Nimshara',
    title: 'Burden Forecasting',
    full: 'Spatio-Temporal Burden Forecasting and Resource Demand',
    question: 'Where and when is burden likely to rise?',
    icon: Map,
    path: '/c4',
    status: '/forecast/status',
    text: 'text-c4',
    bg: 'bg-c4',
    soft: 'bg-c4/10',
    ring: 'ring-c4/30',
    border: 'border-c4',
  },
];

export const componentById = Object.fromEntries(COMPONENTS.map((c) => [c.id, c]));
