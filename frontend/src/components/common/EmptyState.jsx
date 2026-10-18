export default function EmptyState({
  title = 'No data available',
  message = 'No data is available for the current selection.',
}) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-8 text-center shadow-sm">
      <p className="text-lg font-semibold text-primary">{title}</p>
      <p className="mt-2 text-base text-slate-600">{message}</p>
    </div>
  );
}
