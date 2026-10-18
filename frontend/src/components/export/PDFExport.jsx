import { FileDown } from 'lucide-react';
import { jsPDF } from 'jspdf';
import toast from 'react-hot-toast';

export function buildPdfReport({ title = 'FedNutri-XAI Report', sections = [] }) {
  const doc = new jsPDF();
  let y = 20;
  doc.setFontSize(16);
  doc.setTextColor(11, 31, 77);
  doc.text(title, 14, y);
  y += 8;
  doc.setFontSize(10);
  doc.setTextColor(100);
  doc.text(`Generated: ${new Date().toLocaleString()} · Simulated research prototype`, 14, y);
  y += 12;

  sections.forEach((section) => {
    if (y > 270) {
      doc.addPage();
      y = 20;
    }
    doc.setFontSize(12);
    doc.setTextColor(11, 31, 77);
    doc.text(section.heading, 14, y);
    y += 7;
    doc.setFontSize(10);
    doc.setTextColor(40);
    (section.lines || []).forEach((line) => {
      if (y > 280) {
        doc.addPage();
        y = 20;
      }
      doc.text(String(line), 14, y);
      y += 6;
    });
    y += 6;
  });

  return doc;
}

export default function PDFExport({
  label = 'PDF',
  filename = 'FedNutri-XAI-Report.pdf',
  sections = [],
  className = '',
}) {
  const handle = () => {
    const doc = buildPdfReport({ sections });
    doc.save(filename);
    toast.success('PDF report downloaded');
  };

  return (
    <button
      type="button"
      onClick={handle}
      className={`inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 ${className}`}
    >
      <FileDown size={14} /> {label}
    </button>
  );
}
