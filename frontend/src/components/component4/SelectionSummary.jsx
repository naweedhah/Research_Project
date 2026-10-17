import { useComponent4Selection } from '../../context/Component4SelectionContext';

/** Read-only District + selected month/year from the Forecast-page shared selection. */
export default function SelectionSummary({ className = '' }) {
  const { district, year, month } = useComponent4Selection();

  return (
    <div
      className={`rounded-2xl border border-secondary/15 bg-secondary/5 px-4 py-4 md:px-5 ${className}`}
    >
      <p className="text-sm font-semibold uppercase tracking-wide text-secondary">District</p>
      <p className="mt-1 text-xl font-bold text-primary md:text-2xl">{district}</p>
      <p className="mt-1 text-base text-slate-600">
        Selected month: {month}/{year}
      </p>
    </div>
  );
}
