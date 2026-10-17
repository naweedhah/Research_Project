import { formatCases, formatNumber, priorityBadgeClass } from './utils';
import { isPresent, targetLabel } from './format';
import { Pill, Stat } from './ui';

export default function ForecastCard({ title, subtitle, data, accent = '#6C5CE7' }) {
  if (!data) return null;

  const hasInterval = isPresent(data.lower_95) && isPresent(data.upper_95);
  const hasTriposhaInterval =
    isPresent(data.triposha_lower_95) && isPresent(data.triposha_upper_95);

  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm transition hover:shadow-md">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="text-lg font-bold" style={{ color: accent }}>
            {title}
          </p>
          {(subtitle || data.target_date) && (
            <p className="text-sm text-slate-500">
              {subtitle || targetLabel(data.target_date)}
            </p>
          )}
        </div>
        {isPresent(data.priority_level) && (
          <Pill className={priorityBadgeClass(data.priority_level)}>
            {data.priority_level}
          </Pill>
        )}
      </div>

      {isPresent(data.predicted_cases) && (
        <div className="mb-4">
          <p className="text-sm text-slate-500">Predicted cases</p>
          <p className="text-3xl font-bold text-primary md:text-4xl">
            {formatCases(data.predicted_cases)}
          </p>
          {hasInterval && (
            <p className="mt-1 text-sm text-slate-500">
              95% interval: {formatCases(data.lower_95)} -{' '}
              {formatCases(data.upper_95)}
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {isPresent(data.priority_rank) && (
          <Stat label="Priority rank" value={`#${data.priority_rank}`} />
        )}
        {isPresent(data.dmbi_score) && (
          <Stat label="DMBI score" value={formatNumber(data.dmbi_score, 1)} />
        )}
        {isPresent(data.triposha_packets) && (
          <Stat
            label="Triposha packets"
            value={formatNumber(data.triposha_packets)}
          />
        )}
        {hasTriposhaInterval && (
          <Stat
            label="Triposha range"
            value={`${formatNumber(data.triposha_lower_95)} - ${formatNumber(
              data.triposha_upper_95
            )}`}
          />
        )}
        {isPresent(data.uncertainty_level) && (
          <Stat label="Uncertainty" value={data.uncertainty_level} />
        )}
        {isPresent(data.confidence_label) && (
          <Stat label="Confidence" value={data.confidence_label} />
        )}
      </div>
    </div>
  );
}
