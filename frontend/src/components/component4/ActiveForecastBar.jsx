import { useComponent4Selection } from '../../context/Component4SelectionContext';
import { formatCases, priorityBadgeClass } from './utils';

export default function ActiveForecastBar({ forecast }) {
  const { district, year, monthLabel } = useComponent4Selection();
  const h1 = forecast?.forecasts?.h1;

  return (
    <div className="rounded-2xl border border-secondary/15 bg-secondary/5 px-4 py-4 md:px-5">
      <p className="text-sm font-semibold uppercase tracking-wide text-secondary">
        Active forecast
      </p>
      <p className="mt-1 text-xl font-bold text-primary md:text-2xl">
        {monthLabel} {year} • {district} • Automatic H1 / H3 / H6
      </p>
      {h1 ? (
        <p className="mt-2 text-base text-slate-600">
          Predicted (H1): {formatCases(h1.predicted_cases)}{' '}
          <span
            className={`ml-1 inline-flex rounded-full px-2 py-0.5 text-sm font-semibold ${priorityBadgeClass(
              h1.priority_level
            )}`}
          >
            {h1.priority_level}
          </span>
          {h1.lower_95 != null && h1.upper_95 != null && (
            <>
              {' '}
              • 95% CI {formatCases(h1.lower_95)} – {formatCases(h1.upper_95)}
            </>
          )}
        </p>
      ) : null}
    </div>
  );
}
