export default function RiskCard({ risk, count, label }) {
  const colors = {
    High: 'bg-danger/10 text-danger border-danger/20',
    Medium: 'bg-warning/10 text-warning border-warning/20',
    Low: 'bg-success/10 text-success border-success/20',
    Critical: 'bg-danger/15 text-danger border-danger/30',
  };
  return (
    <div className={`rounded-2xl border p-4 ${colors[risk] || colors.Medium}`}>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-80">{label || `${risk} Risk`}</p>
      <p className="mt-1 text-2xl font-bold">{count}</p>
    </div>
  );
}
