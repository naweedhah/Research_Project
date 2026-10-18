import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from 'recharts';

export default function ForecastChart({
  data = [],
  height = 320,
  title,
  subtitle,
  showHistorySplit = true,
}) {
  const hasNumericYear = data.some((row) => typeof row.year === 'number' && row.year === 2023);

  return (
    <div className="h-full w-full">
      {(title || subtitle) && (
        <div className="mb-3">
          {title && <h3 className="font-bold text-primary">{title}</h3>}
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
      )}
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" />
            <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 11 }} />
            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: '1px solid #e2e8f0',
                boxShadow: '0 8px 24px rgba(11,31,77,0.08)',
              }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="upper"
              stroke="none"
              fill="#6C5CE7"
              fillOpacity={0.12}
              name="Confidence band"
              legendType="none"
            />
            <Area
              type="monotone"
              dataKey="lower"
              stroke="none"
              fill="#F7F9FC"
              fillOpacity={1}
              name="band-mask"
              legendType="none"
            />
            <Line
              type="monotone"
              dataKey="historical"
              stroke="#0B1F4D"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#0B1F4D' }}
              name="Historical"
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="predicted"
              stroke="#6C5CE7"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              name="Predicted"
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="upper"
              stroke="#E74C3C"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
              name="Upper bound"
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="lower"
              stroke="#27AE60"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
              name="Lower bound"
              connectNulls
            />
            {showHistorySplit && hasNumericYear && (
              <ReferenceLine x={2023} stroke="#94a3b8" strokeDasharray="4 4" />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
