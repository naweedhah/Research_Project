export default function MetricCard({ title, value, subtitle, icon: Icon, accent = '#6C5CE7', trend }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="mb-3 flex items-start justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{title}</p>
        {Icon && (
          <div
            className="flex h-9 w-9 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${accent}18`, color: accent }}
          >
            <Icon size={18} />
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-primary md:text-3xl">{value}</p>
      <div className="mt-1 flex items-center gap-2">
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        {trend != null && (
          <span className={`text-xs font-semibold ${trend >= 0 ? 'text-success' : 'text-danger'}`}>
            {trend >= 0 ? '+' : ''}
            {trend}%
          </span>
        )}
      </div>
    </div>
  );
}
