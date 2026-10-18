import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

export default function ResourceChart({ data = [], centerLabel = 'Total', centerValue, height = 240 }) {
  return (
    <div className="relative" style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius="62%"
            outerRadius="88%"
            paddingAngle={3}
            stroke="none"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => value.toLocaleString()} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-[10px] uppercase tracking-wide text-slate-400">{centerLabel}</p>
        <p className="text-lg font-bold text-primary">{centerValue}</p>
      </div>
    </div>
  );
}
