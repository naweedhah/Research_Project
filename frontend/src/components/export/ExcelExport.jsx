import { FileSpreadsheet } from 'lucide-react';
import * as XLSX from 'xlsx';
import toast from 'react-hot-toast';

export function downloadExcel(sheets = {}, filename = 'FedNutri-XAI.xlsx') {
  const wb = XLSX.utils.book_new();
  Object.entries(sheets).forEach(([name, rows]) => {
    const ws = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, name.slice(0, 31));
  });
  XLSX.writeFile(wb, filename);
}

export default function ExcelExport({
  label = 'Excel',
  filename = 'FedNutri-XAI.xlsx',
  sheets = {},
  className = '',
}) {
  return (
    <button
      type="button"
      onClick={() => {
        downloadExcel(sheets, filename);
        toast.success('Excel report downloaded');
      }}
      className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 ${className}`}
    >
      <FileSpreadsheet size={14} /> {label}
    </button>
  );
}
