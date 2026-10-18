export default function ResourceCard({
  title,
  value,
  subtitle,
  icon: Icon,
  footer,
  accent = '#6C5CE7',
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
      <div className="p-5">
        <div className="mb-3 flex items-start justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{title}</p>
          {Icon && (
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg"
              style={{ backgroundColor: `${accent}18`, color: accent }}
            >
              <Icon size={16} />
            </div>
          )}
        </div>
        <p className="text-3xl font-bold text-primary">{value}</p>
        {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
      </div>
      {footer}
    </div>
  );
}
