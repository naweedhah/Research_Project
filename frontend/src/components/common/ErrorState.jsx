export default function ErrorState({
  title = 'Unable to load data',
  message = 'Please try again.',
  onRetry,
}) {
  return (
    <div className="rounded-2xl border border-red-100 bg-red-50/60 p-6 text-center shadow-sm">
      <p className="text-lg font-semibold text-danger">{title}</p>
      <p className="mt-2 text-base text-slate-600">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-full bg-secondary px-5 py-2 text-base font-semibold text-white hover:bg-secondary/90"
        >
          Retry
        </button>
      )}
    </div>
  );
}
