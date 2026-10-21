export function Card({
  title,
  subtitle,
  action,
  children,
  className = '',
}) {
  return (
    <section
      className={`rounded-2xl border border-slate-100 bg-white p-5 shadow-sm ${className}`}
    >
      {(title || action) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && (
              <h3 className="text-lg font-bold text-primary md:text-xl">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>
            )}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function MetricTile({ label, value, hint, icon: Icon, accent = '#6C5CE7', children }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="mb-3 flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-slate-500">{label}</p>
        {Icon && (
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${accent}18`, color: accent }}
          >
            <Icon size={20} />
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-primary md:text-3xl">{value}</p>
      {children}
      {hint && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
    </div>
  );
}

export function Stat({ label, value }) {
  return (
    <div className="rounded-xl bg-surface px-3 py-2.5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-0.5 text-base font-semibold text-primary">{value}</p>
    </div>
  );
}

export function Tabs({ value, onChange, options }) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-full border border-slate-200 bg-white p-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`rounded-full px-4 py-1.5 text-base font-semibold transition ${
            value === opt.value
              ? 'bg-secondary text-white shadow'
              : 'text-slate-600 hover:bg-slate-50'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export function Pill({ className = '', children }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-semibold ${className}`}
    >
      {children}
    </span>
  );
}