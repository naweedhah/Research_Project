import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { formatNumber } from './utils';
import { axisTick, chartTooltipStyle, humanize, isPresent } from './format';

function toRows(list) {
  return (Array.isArray(list) ? list : [])
    .filter((row) => row && isPresent(row.top_feature_shap))
    .map((row) => ({
      label: humanize(row.top_feature),
      domain: row.domain,
      domainShap: row.domain_shap,
      value: Number(row.top_feature_shap),
    }));
}

function ShapTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-primary">{row.label}</p>
      {row.domain && <p className="text-slate-500">{row.domain}</p>}
      <p className="mt-1 text-slate-700">
        Model contribution: <strong>{formatNumber(row.value, 2)}</strong> cases
      </p>
      {isPresent(row.domainShap) && (
        <p className="text-slate-700">
          Domain total: <strong>{formatNumber(row.domainShap, 2)}</strong> cases
        </p>
      )}
    </div>
  );
}

function ShapGroup({ title, rows, color }) {
  if (!rows.length) {
    return (
      <div>
        <p className="mb-2 text-base font-semibold text-primary">{title}</p>
        <p className="rounded-xl bg-surface px-3 py-4 text-base text-slate-500">
          No components reported by the backend.
        </p>
      </div>
    );
  }

  const height = Math.max(150, rows.length * 56 + 50);

  return (
    <div>
      <p className="mb-2 text-base font-semibold text-primary">{title}</p>
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer>
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#E8EEF7" horizontal={false} />
            <XAxis
              type="number"
              tick={axisTick}
              tickFormatter={(v) => formatNumber(v, 1)}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={190}
              tick={{ fill: '#0B1F4D', fontSize: 14 }}
              interval={0}
            />
            <Tooltip content={<ShapTooltip />} contentStyle={chartTooltipStyle} />
            <ReferenceLine x={0} stroke="#94a3b8" />
            <Bar dataKey="value" radius={4} barSize={22}>
              {rows.map((row, index) => (
                <Cell key={`${row.label}-${index}`} fill={color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/**
 * Horizontal bars for the top model-contribution components of one
 * explainability record (top_increasing / top_decreasing).
 */
export default function ShapChart({ item }) {
  if (!item) return null;
  const increasing = toRows(item.top_increasing);
  const decreasing = toRows(item.top_decreasing);

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <ShapGroup
        title="Components pushing the forecast up"
        rows={increasing}
        color="#E74C3C"
      />
      <ShapGroup
        title="Components pushing the forecast down"
        rows={decreasing}
        color="#27AE60"
      />
      <p className="text-sm text-slate-500 xl:col-span-2">
        Each bar is the strongest feature within a domain group, in model
        contribution units (cases). Hover a bar for the domain.
      </p>
    </div>
  );
}
