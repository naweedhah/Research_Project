import PDFExport from './PDFExport';
import ExcelExport from './ExcelExport';
import CSVExport from './CSVExport';
import PrintReport from './PrintReport';

export default function ExportToolbar({
  pdfSections = [],
  excelSheets = {},
  csvRows = [],
  pdfName,
  excelName,
  csvName,
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 print:hidden">
      <PDFExport sections={pdfSections} filename={pdfName} />
      <ExcelExport sheets={excelSheets} filename={excelName} />
      <CSVExport rows={csvRows} filename={csvName} />
      <PrintReport />
    </div>
  );
}
