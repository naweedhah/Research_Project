import { Link } from 'react-router-dom';

export default function SelectionRequiredNotice({ className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-slate-100 bg-white p-8 text-center shadow-sm ${className}`}
    >
      <p className="text-lg font-semibold text-primary">
        Please select a district, year, and month from the Forecast page first.
      </p>
      <Link
        to="/forecast"
        className="mt-4 inline-flex rounded-full bg-secondary px-5 py-2.5 text-base font-semibold text-white hover:bg-secondary/90"
      >
        Go to Forecast
      </Link>
    </div>
  );
}
