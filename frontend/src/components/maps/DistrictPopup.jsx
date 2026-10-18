export default function DistrictPopup({ district }) {
  if (!district) return null;

  const riskClass =
    district.risk === 'Very High' || district.risk === 'High'
      ? 'text-danger'
      : district.risk === 'Medium'
        ? 'text-warning'
        : 'text-success';

  return (
    <div className="min-w-[200px] text-sm">
      <p className="mb-2 font-bold text-primary">{district.name} District</p>
      <div className="space-y-1 text-xs text-slate-600">
        <p>
          <span className="font-semibold text-slate-800">Predicted Cases:</span> {district.cases}
        </p>
        {(district.lower != null || district.ci) && (
          <p>
            <span className="font-semibold text-slate-800">95% CI:</span>{' '}
            {district.ci || `${district.lower} – ${district.upper}`}
          </p>
        )}
        <p>
          <span className="font-semibold text-slate-800">Risk:</span>{' '}
          <span className={riskClass}>{district.risk}</span>
        </p>
        {district.uncertainty && (
          <p>
            <span className="font-semibold text-slate-800">Uncertainty:</span> {district.uncertainty}
          </p>
        )}
        <p>
          <span className="font-semibold text-slate-800">Triposha:</span>{' '}
          {Number(district.triposha || 0).toLocaleString()} Packs
        </p>
        {district.trend && (
          <p>
            <span className="font-semibold text-slate-800">Trend:</span> {district.trend}
          </p>
        )}
        {district.dmpi != null && (
          <p>
            <span className="font-semibold text-slate-800">DMPI Score:</span> {district.dmpi}
          </p>
        )}
      </div>
    </div>
  );
}
