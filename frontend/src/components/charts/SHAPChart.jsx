import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export default function SHAPChart({ data = [], height = 280 }) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tick={{ fill: '#0B1F4D', fontSize: 12 }}
          />
          <Tooltip
            formatter={(value) => [`${value}%`, 'Contribution']}
            contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0' }}
          />
          <Bar dataKey="value" radius={[0, 8, 8, 0]} barSize={18} label={{ position: 'right', formatter: (v) => `${v}%`, fill: '#64748b', fontSize: 11 }}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color || '#6C5CE7'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
