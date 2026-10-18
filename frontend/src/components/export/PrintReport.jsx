import { Printer } from 'lucide-react';
import toast from 'react-hot-toast';

export default function PrintReport({ label = 'Print', className = '', onBeforePrint }) {
  return (
    <button
      type="button"
      onClick={() => {
        onBeforePrint?.();
        toast.success('Opening print dialog');
        setTimeout(() => window.print(), 200);
      }}
      className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 ${className}`}
    >
      <Printer size={14} /> {label}
    </button>
  );
}
