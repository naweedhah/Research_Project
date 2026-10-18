import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from 'recharts';

export default function RiskDistributionChart({ data = [], height = 260 }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  return (
    <div className="relative" style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={3}
            stroke="none"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
          <Legend verticalAlign="bottom" height={36} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center pb-8">
        <p className="text-[10px] uppercase tracking-wide text-slate-400">Total</p>
        <p className="text-xl font-bold text-primary">{total} Districts</p>
      </div>
    </div>
  );
}
