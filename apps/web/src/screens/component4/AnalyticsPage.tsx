"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/component4/httpClient";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/cards/card";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function AnalyticsPage() {
  const { data } = useQuery({ queryKey: ["dashboard"], queryFn: () => api<{ risk_trend: Record<string, number> }>("/dashboard") });
  const chart = Object.entries(data?.risk_trend ?? {}).map(([name, n]) => ({ name, n }));
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Facility analytics</h1>
      <Card>
        <CardHeader><CardTitle>Progress distribution</CardTitle></CardHeader>
        <CardBody className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart}>
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="n" fill="#1D4ED8" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardBody>
      </Card>
    </div>
  );
}
