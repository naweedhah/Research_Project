import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export default function TrendChart({ data = [], height = 280 }) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6C5CE7" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#6C5CE7" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="mamGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#F39C12" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#F39C12" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="samGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#E74C3C" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#E74C3C" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" />
          <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 11 }} />
          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Area type="monotone" dataKey="total" stroke="#6C5CE7" fill="url(#totalGrad)" name="Total cases" strokeWidth={2} />
          <Area type="monotone" dataKey="mam" stroke="#F39C12" fill="url(#mamGrad)" name="MAM" strokeWidth={2} />
          <Area type="monotone" dataKey="sam" stroke="#E74C3C" fill="url(#samGrad)" name="SAM" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
