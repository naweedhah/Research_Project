import { FileText } from 'lucide-react';
import Papa from 'papaparse';
import toast from 'react-hot-toast';

export function downloadCsv(rows = [], filename = 'FedNutri-XAI.csv') {
  const csv = Papa.unparse(rows);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function CSVExport({
  label = 'CSV',
  filename = 'FedNutri-XAI.csv',
  rows = [],
  className = '',
}) {
  return (
    <button
      type="button"
      onClick={() => {
        downloadCsv(rows, filename);
        toast.success('CSV exported');
      }}
      className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 ${className}`}
    >
      <FileText size={14} /> {label}
    </button>
  );
}
