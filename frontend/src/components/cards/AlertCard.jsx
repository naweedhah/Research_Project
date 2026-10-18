import { Link } from 'react-router-dom';

const riskBadge = {
  Critical: 'bg-danger/10 text-danger',
  High: 'bg-warning/10 text-warning',
  Medium: 'bg-secondary/10 text-secondary',
  Low: 'bg-success/10 text-success',
};

export default function AlertCard({ alerts = [] }) {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="font-bold text-primary">Early Warning Alerts</h3>
          <p className="text-xs text-slate-500">Live district threshold signals</p>
        </div>
        <Link to="/early-warning" className="text-xs font-semibold text-secondary hover:underline">
          Manage
        </Link>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto">
        {alerts.slice(0, 4).map((a) => (
          <div key={a.id} className="rounded-xl border border-slate-100 bg-surface/70 px-3 py-2.5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-primary">{a.district}</p>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${riskBadge[a.risk]}`}>
                {a.risk}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {a.alertType} → +{a.increase}%
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
