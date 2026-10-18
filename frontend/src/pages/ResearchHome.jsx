import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Bot,
  Brain,
  CheckCircle2,
  Database,
  LineChart,
  LogOut,
  Map,
  Package,
  Shield,
  Sparkles,
  Stethoscope,
} from 'lucide-react';
import { useApp } from '../context/AppContext';

const components = [
  {
    id: 1,
    active: true,
    icon: LineChart,
    title: 'District-Level Malnutrition Forecasting',
    subtitle: 'Spatio-Temporal Forecasting & Decision Support',
    description:
      'Forecast future childhood malnutrition burden across Sri Lankan districts and support proactive nutrition resource planning.',
    capabilities: [
      'Future Malnutrition Forecasting',
      'District Risk Mapping',
      'District Malnutrition Burden Index',
      'Triposha Resource Demand Estimation',
      'Early Warning Alerts',
      'Explainable AI',
      'GIS Visualization',
    ],
    status: 'ACTIVE',
    action: 'Open Dashboard',
    to: '/dashboard',
  },
  {
    id: 2,
    active: false,
    icon: Brain,
    title: 'Trustworthy Explainable AI',
    subtitle: 'Transparent & Interpretable Predictions',
    description:
      'Provides transparent and interpretable AI predictions to help healthcare professionals understand the factors influencing malnutrition risk.',
    capabilities: [
      'Explainable AI',
      'Model Transparency',
      'Prediction Interpretation',
      'Trust Analysis',
    ],
    status: 'COMING SOON',
    action: 'View Component',
    to: '/component/trustworthy-xai',
  },
  {
    id: 3,
    active: false,
    icon: Stethoscope,
    title: 'Personalized Nutrition Intervention',
    subtitle: 'Child-Level Guidance & Clinical Support',
    description:
      'Provides personalized nutrition intervention recommendations based on child-level nutrition information and predicted risk.',
    capabilities: [
      'Personalized Intervention',
      'Nutrition Recommendations',
      'Risk-Based Guidance',
      'Clinical Decision Support',
    ],
    status: 'COMING SOON',
    action: 'View Component',
    to: '/component/personalized-nutrition',
  },
  {
    id: 4,
    active: false,
    icon: Shield,
    title: 'Privacy-Preserving Model Recalibration',
    subtitle: 'Federated Learning & Drift Monitoring',
    description:
      'Monitors model changes across healthcare nodes and supports privacy-preserving model recalibration under changing data patterns.',
    capabilities: [
      'Federated Learning',
      'Concept Drift',
      'Model Recalibration',
      'Privacy Preservation',
    ],
    status: 'COMING SOON',
    action: 'View Component',
    to: '/component/privacy-recalibration',
  },
];

const workflow = [
  'Data',
  'AI Models',
  'Forecasting',
  'Risk Analysis',
  'Explainability',
  'Intervention',
  'Healthcare Decision Support',
];

export default function ResearchHome() {
  const { profile, logout } = useApp();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-white shadow-md">
              <Bot size={20} />
            </div>
            <div>
              <p className="text-sm font-bold text-primary">FedNutri-XAI</p>
              <p className="text-[11px] text-slate-500">Research Platform Hub</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-xs font-semibold text-primary">{profile.name}</p>
              <p className="text-[10px] text-slate-500">{profile.role}</p>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-primary transition hover:bg-slate-50"
            >
              <LogOut size={14} /> Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-10 px-4 py-8 md:px-6 md:py-10">
        <section className="animate-fade-in rounded-2xl border border-slate-100 bg-white p-6 shadow-sm md:p-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="max-w-3xl">
              <span className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-secondary/10 px-3 py-1 text-[11px] font-semibold text-secondary">
                <Sparkles size={12} /> Integrated Research Platform
              </span>
              <h1 className="text-3xl font-bold text-primary md:text-4xl">FedNutri-XAI</h1>
              <p className="mt-2 text-base font-medium text-slate-600 md:text-lg">
                AI-Powered Childhood Malnutrition Intelligence Platform
              </p>
              <p className="mt-4 text-sm leading-relaxed text-slate-500">
                FedNutri-XAI is an integrated research platform that brings together four complementary
                research components for childhood malnutrition intelligence in Sri Lanka — covering
                forecasting, explainable AI, personalized intervention, and privacy-preserving model
                recalibration.
              </p>
            </div>
            <div className="shrink-0 rounded-2xl bg-surface px-4 py-3 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Research Prototype
              </p>
              <p className="mt-1 text-sm font-bold text-primary">Demo Session Active</p>
            </div>
          </div>
        </section>

        <section>
          <div className="mb-5">
            <h2 className="text-xl font-bold text-primary">Research Components</h2>
            <p className="text-sm text-slate-500">
              Select a component to open its workspace or view development status.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            {components.map((c) => {
              const Icon = c.icon;
              return (
                <article
                  key={c.id}
                  className={`flex flex-col rounded-2xl border bg-white p-5 shadow-sm transition md:p-6 ${
                    c.active
                      ? 'border-secondary/40 shadow-md shadow-secondary/10 ring-1 ring-secondary/20'
                      : 'border-slate-100'
                  }`}
                >
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <div
                      className={`flex h-11 w-11 items-center justify-center rounded-xl ${
                        c.active ? 'bg-secondary text-white' : 'bg-surface text-primary'
                      }`}
                    >
                      <Icon size={20} />
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-1 text-[10px] font-bold tracking-wide ${
                        c.active
                          ? 'bg-success/10 text-success'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {c.status}
                    </span>
                  </div>

                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    Component 0{c.id}
                  </p>
                  <h3 className="mt-1 text-lg font-bold text-primary">{c.title}</h3>
                  <p className="mt-1 text-xs font-medium text-secondary">{c.subtitle}</p>
                  <p className="mt-3 text-sm leading-relaxed text-slate-500">{c.description}</p>

                  <ul className="mt-4 flex-1 space-y-1.5">
                    {c.capabilities.map((item) => (
                      <li key={item} className="flex items-start gap-2 text-xs text-slate-600">
                        <CheckCircle2
                          size={14}
                          className={`mt-0.5 shrink-0 ${c.active ? 'text-secondary' : 'text-slate-300'}`}
                        />
                        {item}
                      </li>
                    ))}
                  </ul>

                  <Link
                    to={c.to}
                    className={`mt-5 inline-flex items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold transition ${
                      c.active
                        ? 'bg-secondary text-white shadow-md shadow-secondary/25 hover:opacity-95'
                        : 'border border-slate-200 bg-white text-primary hover:bg-slate-50'
                    }`}
                  >
                    {c.action} <ArrowRight size={16} />
                  </Link>
                </article>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
          <h2 className="mb-5 text-xl font-bold text-primary">Research Platform Overview</h2>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[
              { value: '25', label: 'Districts Covered', icon: Map },
              { value: '4', label: 'Research Components', icon: Package },
              { value: 'AI', label: 'Powered Analytics', icon: Brain },
              { value: 'Sri Lanka', label: 'Research Scope', icon: Database },
            ].map((stat) => {
              const Icon = stat.icon;
              return (
                <div key={stat.label} className="rounded-2xl bg-surface p-4 text-center">
                  <div className="mx-auto mb-2 flex h-9 w-9 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
                    <Icon size={16} />
                  </div>
                  <p className="text-xl font-bold text-primary md:text-2xl">{stat.value}</p>
                  <p className="mt-1 text-xs text-slate-500">{stat.label}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm md:p-8">
          <h2 className="text-xl font-bold text-primary">Research Objective</h2>
          <p className="mt-3 max-w-4xl text-sm leading-relaxed text-slate-600">
            FedNutri-XAI aims to support proactive and trustworthy childhood malnutrition management by
            combining predictive analytics, explainable AI, personalized intervention, and
            privacy-preserving healthcare intelligence.
          </p>
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            {[
              {
                title: 'PREDICT',
                text: 'Identify future malnutrition risks.',
                accent: '#6C5CE7',
              },
              {
                title: 'EXPLAIN',
                text: 'Understand why AI models make predictions.',
                accent: '#0B1F4D',
              },
              {
                title: 'ACT',
                text: 'Support proactive nutrition planning and intervention.',
                accent: '#27AE60',
              },
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-2xl border border-slate-100 bg-surface p-5"
                style={{ borderTop: `3px solid ${item.accent}` }}
              >
                <p className="text-xs font-bold tracking-wide" style={{ color: item.accent }}>
                  {item.title}
                </p>
                <p className="mt-2 text-sm text-slate-600">{item.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm md:p-8">
          <h2 className="mb-2 text-xl font-bold text-primary">From Data to Action</h2>
          <p className="mb-6 text-sm text-slate-500">Platform workflow for healthcare decision support</p>
          <div className="flex flex-col items-stretch gap-2 md:flex-row md:flex-wrap md:items-center md:justify-between md:gap-1">
            {workflow.map((step, index) => (
              <div key={step} className="flex items-center gap-2 md:flex-col md:gap-2">
                <div className="flex flex-1 items-center gap-2 md:flex-col">
                  <div className="flex h-10 min-w-[140px] items-center justify-center rounded-xl bg-primary px-3 text-center text-xs font-semibold text-white md:min-w-[110px]">
                    {step}
                  </div>
                  {index < workflow.length - 1 && (
                    <span className="text-secondary md:hidden">↓</span>
                  )}
                </div>
                {index < workflow.length - 1 && (
                  <span className="hidden text-secondary md:inline">→</span>
                )}
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
