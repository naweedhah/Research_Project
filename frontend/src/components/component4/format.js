const MONTH_NAMES = [
  '',
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

export function isPresent(value) {
  return value !== null && value !== undefined && value !== '';
}

function parseYearMonth(value) {
  if (!isPresent(value)) return null;
  const match = String(value).match(/^(\d{4})-(\d{1,2})/);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (!year || month < 1 || month > 12) return null;
  return { year, month };
}

/** "2026-01-01" or "2026-01" -> "January 2026" (no timezone shifting). */
export function targetLabel(value) {
  const ym = parseYearMonth(value);
  if (!ym) return isPresent(value) ? String(value) : '-';
  return `${MONTH_NAMES[ym.month]} ${ym.year}`;
}

/** "2026-01-01" -> "Jan 2026" */
export function targetShort(value) {
  const ym = parseYearMonth(value);
  if (!ym) return isPresent(value) ? String(value) : '-';
  return `${MONTH_NAMES[ym.month].slice(0, 3)} ${ym.year}`;
}

export function yearMonthShort(year, month) {
  if (!year || !month) return '-';
  return `${MONTH_NAMES[Number(month)].slice(0, 3)} ${year}`;
}

export function formatPercent(value, decimals = 1) {
  if (!isPresent(value) || Number.isNaN(Number(value))) return '-';
  const n = Number(value);
  return `${n > 0 ? '+' : ''}${n.toFixed(decimals)}%`;
}

export function humanize(text) {
  if (!isPresent(text)) return '-';
  const s = String(text).replace(/_/g, ' ').trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function directionBadgeClass(direction) {
  const key = String(direction || '').toLowerCase();
  if (key === 'increasing') return 'bg-red-100 text-red-800';
  if (key === 'decreasing') return 'bg-emerald-100 text-emerald-800';
  if (key === 'stable') return 'bg-sky-100 text-sky-800';
  return 'bg-slate-100 text-slate-700';
}

export function severityBadgeClass(severity) {
  const key = String(severity || '').toUpperCase();
  if (key === 'CRITICAL') return 'bg-red-100 text-red-800';
  if (key === 'HIGH') return 'bg-orange-100 text-orange-800';
  if (key === 'MEDIUM') return 'bg-amber-100 text-amber-800';
  return 'bg-slate-100 text-slate-700';
}

export const chartTooltipStyle = {
  borderRadius: 12,
  border: '1px solid #e2e8f0',
  boxShadow: '0 8px 24px rgba(11,31,77,0.08)',
  fontSize: 14,
};

export const axisTick = { fill: '#64748b', fontSize: 13 };

export function normalizeDistrictName(name) {
  return String(name || '')
    .toLowerCase()
    .replace(/\s+district$/, '')
    .trim();
}

export const HORIZON_KEYS = ['h1', 'h3', 'h6'];

export const HORIZON_META = {
  h1: { label: 'H1', long: '1 month ahead', color: '#6C5CE7' },
  h3: { label: 'H3', long: '3 months ahead', color: '#0B1F4D' },
  h6: { label: 'H6', long: '6 months ahead', color: '#F39C12' },
};
