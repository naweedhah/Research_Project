export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—';
  }
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  });
}

export function formatCases(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—';
  }
  return Math.round(Number(value)).toLocaleString();
}

export function priorityColor(level) {
  const key = String(level || '').toUpperCase();
  if (key === 'CRITICAL' || key === 'VERY HIGH') return '#B91C1C';
  if (key === 'HIGH') return '#E74C3C';
  if (key === 'MEDIUM') return '#F39C12';
  if (key === 'LOW') return '#27AE60';
  if (key === 'VERY LOW') return '#0EA5E9';
  return '#94A3B8';
}

export function priorityBadgeClass(level) {
  const key = String(level || '').toUpperCase();
  if (key === 'CRITICAL' || key === 'VERY HIGH') {
    return 'bg-red-100 text-red-800';
  }
  if (key === 'HIGH') return 'bg-orange-100 text-orange-800';
  if (key === 'MEDIUM') return 'bg-amber-100 text-amber-800';
  if (key === 'LOW') return 'bg-emerald-100 text-emerald-800';
  if (key === 'VERY LOW') return 'bg-sky-100 text-sky-800';
  return 'bg-slate-100 text-slate-700';
}

export function monthName(month) {
  const names = [
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
  return names[Number(month)] || String(month);
}

export function shortMonth(targetDateOrMonth) {
  if (!targetDateOrMonth) return '—';
  const raw = String(targetDateOrMonth);
  const date = raw.length <= 7 ? `${raw}-01` : raw;
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
}
