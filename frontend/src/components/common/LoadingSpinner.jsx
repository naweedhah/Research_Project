export default function LoadingSpinner({ message = 'Loading data...' }) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-secondary/20 border-t-secondary" />
      <p className="text-base text-slate-600">{message}</p>
    </div>
  );
}
