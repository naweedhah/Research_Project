import { AlertTriangle, Inbox, Loader2 } from 'lucide-react';
import { componentById } from '../config/components';

export function Card({ className = '', children, ...rest }) {
  return (
    <section className={`rounded-xl border border-line bg-white shadow-card ${className}`} {...rest}>
      {children}
    </section>
  );
}

export function CardHeader({ title, subtitle, action, icon: Icon }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-3.5">
      <div className="flex items-center gap-2.5">
        {Icon && <Icon size={17} className="text-muted" />}
        <div>
          <h3 className="text-[15px] font-semibold text-primary">{title}</h3>
          {subtitle && <p className="text-[13px] text-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function CardBody({ className = '', children }) {
  return <div className={`px-5 py-4 ${className}`}>{children}</div>;
}

/** Page title with the owning component's colour bar. */
export function PageHeader({ component, title, subtitle, actions }) {
  const c = component ? componentById[component] : null;
  return (
    <header className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div>
        {c && (
          <p className={`mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider ${c.text}`}>
            <span className={`h-2 w-2 rounded-full ${c.bg}`} />
            Component {c.number} · {c.title}
          </p>
        )}
        <h1 className="text-2xl font-bold tracking-tight text-primary md:text-[28px]">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-[15px] text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

const BADGE_TONES = {
  neutral: 'bg-slate-100 text-slate-700',
  success: 'bg-green-50 text-success ring-1 ring-green-200',
  warning: 'bg-amber-50 text-warning ring-1 ring-amber-200',
  danger: 'bg-orange-50 text-danger ring-1 ring-orange-200',
  info: 'bg-sky-50 text-sky-800 ring-1 ring-sky-200',
  brand: 'bg-teal-50 text-secondary ring-1 ring-teal-200',
  violet: 'bg-violet-50 text-c3 ring-1 ring-violet-200',
};

export function Badge({ tone = 'neutral', children, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${BADGE_TONES[tone]} ${className}`}>
      {children}
    </span>
  );
}

/** Maintenance decision -> badge tone and label. */
export const DECISION = {
  no_action: { tone: 'success', label: 'No action' },
  recalibrate: { tone: 'info', label: 'Recalibrate' },
  retrain: { tone: 'violet', label: 'Retrain' },
  hold: { tone: 'warning', label: 'Hold' },
};

export function DecisionBadge({ decision }) {
  const d = DECISION[decision] || { tone: 'neutral', label: decision || '—' };
  return <Badge tone={d.tone}>{d.label}</Badge>;
}

export function Stat({ label, value, hint, tone }) {
  const color = { success: 'text-success', warning: 'text-warning', danger: 'text-danger' }[tone] || 'text-primary';
  return (
    <div>
      <p className="text-[13px] text-muted">{label}</p>
      <p className={`tabular mt-0.5 text-2xl font-semibold ${color}`}>{value}</p>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function KeyValues({ rows }) {
  return (
    <dl className="grid grid-cols-[minmax(130px,auto)_1fr] gap-x-4 gap-y-2 text-sm">
      {rows.filter(Boolean).map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted">{k}</dt>
          <dd className="tabular font-medium text-primary">{v ?? '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Button({ variant = 'primary', className = '', children, ...rest }) {
  const styles = {
    primary: 'bg-primary text-white hover:bg-primary/90',
    brand: 'bg-secondary text-white hover:bg-secondary/90',
    c3: 'bg-c3 text-white hover:bg-c3/90',
    c2: 'bg-c2 text-white hover:bg-c2/90',
    outline: 'border border-line bg-white text-primary hover:bg-slate-50',
    ghost: 'text-primary hover:bg-slate-100',
    danger: 'border border-orange-200 bg-white text-danger hover:bg-orange-50',
  }[variant];
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-muted">
      <Loader2 size={16} className="animate-spin" /> {label}
    </div>
  );
}

export function ErrorBox({ error, hint }) {
  return (
    <div className="flex gap-3 rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-danger">
      <AlertTriangle size={17} className="mt-0.5 shrink-0" />
      <div>
        <p className="font-semibold">{String(error?.message || error)}</p>
        {hint && <p className="mt-0.5 text-orange-900/80">{hint}</p>}
      </div>
    </div>
  );
}

export function Empty({ children }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center text-sm text-muted">
      <Inbox size={22} className="text-slate-400" />
      {children}
    </div>
  );
}

export const pct = (v, digits = 1) => (v == null || Number.isNaN(v) ? '—' : `${(v * 100).toFixed(digits)}%`);
export const num = (v, digits = 3) => (v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(digits));
