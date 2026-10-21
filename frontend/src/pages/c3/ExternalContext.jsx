import { useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts';
import { AlertTriangle, CheckCircle2, CloudLightning, ExternalLink, Info, RefreshCw, XCircle } from 'lucide-react';
import { useApi } from '../../lib/useApi';
import { Badge, Button, Card, CardBody, CardHeader, ErrorBox, KeyValues, Loading, PageHeader } from '../../ui';

/* Chart roles (validated: blue/orange pass CVD + contrast on white). Status colours follow GDACS's own levels and are
   always shown with their name. */
const C = { series1: '#2a78d6', series2: '#eb6834', grid: '#eef1f5', axis: '#5b6b7f', ink: '#0f2a3d',
  watch: '#b45309', alert: '#c2410c', window: '#7c3aed' };
const GDACS = { Green: { y: 1, color: '#0ca30c' }, Orange: { y: 2, color: '#ec835a' }, Red: { y: 3, color: '#d03b3b' } };
const axis = { stroke: C.grid, tick: { fill: C.axis, fontSize: 12 }, tickLine: false };

const today = new Date();
const iso = (d) => d.toISOString().slice(0, 10);
const PRESETS = [
  { id: 'recent', label: 'Last 30 days', start: iso(new Date(today.getTime() - 30 * 864e5)), end: iso(today) },
  { id: 'ditwah', label: 'Dec 2025 · Cyclone Ditwah', start: '2025-12-01', end: '2025-12-31' },
  { id: 'prices', label: 'Jun 2025 · food price jump', start: '2025-06-01', end: '2025-06-30' },
];

const pctFmt = (v) => (v == null ? '—' : `${(v * 100).toFixed(1)}%`);
const dayMs = (s) => new Date(`${s}T00:00:00`).getTime();
const fmtDay = (t) => new Date(t).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' });

function TooltipBox({ title, rows }) {
  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-[13px] shadow-card">
      <p className="mb-1 font-semibold text-primary">{title}</p>
      {rows.map(([k, v]) => <p key={k} className="text-muted"><span className="text-primary">{v}</span> {k}</p>)}
    </div>
  );
}

function SourceCard({ s }) {
  const modeTone = { live: 'success', offline: 'neutral', file: 'info' }[s.mode];
  const modeLabel = { live: 'Live API', offline: 'Saved sample', file: 'Monthly file' }[s.mode];
  return (
    <Card>
      <CardBody className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-primary">{s.name}</p>
          {s.ok ? <CheckCircle2 size={18} className="text-success" aria-label="fetched" />
            : <XCircle size={18} className="text-danger" aria-label="failed" />}
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone={modeTone}>{modeLabel}</Badge>
          {s.cached && <Badge>cached</Badge>}
        </div>
        {s.ok ? (
          <KeyValues rows={[
            ['Records', s.records?.toLocaleString()],
            ['Latest data', s.latest || '—'],
            ['Fetched', `${s.fetched_at?.slice(11, 19)} UTC · ${s.seconds}s`],
          ]} />
        ) : <p className="text-[13px] text-danger">{s.error}</p>}
        {s.mode === 'live' && (
          <a href={s.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-c3 hover:underline">
            Source <ExternalLink size={12} />
          </a>
        )}
      </CardBody>
    </Card>
  );
}

function DisasterTimeline({ data }) {
  const pts = data.disasters.map((d) => ({ ...d, t: dayMs(d.start), y: GDACS[d.alert_level]?.y || 1 }));
  const lookStart = dayMs(data.window.start) - data.rules.disaster_lookback_days * 864e5;
  const end = dayMs(data.window.end);
  const min = Math.min(lookStart, ...pts.map((p) => p.t)) - 20 * 864e5;
  return (
    <Card>
      <CardHeader title="Disasters in Sri Lanka (GDACS)" icon={CloudLightning}
        subtitle={`Orange/Red anywhere → alert · Green within ${data.rules.disaster_radius_km} km → watch · shaded: ${data.rules.disaster_lookback_days}-day look-back + window`} />
      <CardBody>
        <div className="h-56">
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 10, right: 24, bottom: 4, left: 4 }}>
              <CartesianGrid stroke={C.grid} vertical={false} />
              <ReferenceArea x1={lookStart} x2={end} fill={C.window} fillOpacity={0.07} stroke="none" />
              <XAxis type="number" dataKey="t" domain={[min, end + 20 * 864e5]} tickFormatter={fmtDay} {...axis} />
              <YAxis type="number" dataKey="y" domain={[0.5, 3.5]} ticks={[1, 2, 3]} width={64} {...axis}
                tickFormatter={(v) => ['', 'Green', 'Orange', 'Red'][v]} />
              <Tooltip cursor={false} content={({ payload }) => {
                const d = payload?.[0]?.payload;
                return d ? <TooltipBox title={`${d.type} · ${d.alert_level}`} rows={[
                  ['', d.name], ['', `${d.start} → ${d.end}`],
                  ['km from study area', d.distance_km ?? '—'],
                  ['', d.counts_for_window ? `counts → ${d.signal}` : 'outside window / too far'],
                ]} /> : null;
              }} />
              <Scatter data={pts} shape={(p) => (
                <circle cx={p.cx} cy={p.cy} r={p.payload.counts_for_window ? 8 : 6} fill={GDACS[p.payload.alert_level]?.color || C.axis}
                  stroke="#fff" strokeWidth={2} />
              )} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        {data.disasters.length ? (
          <table className="mt-3 w-full text-[13px]">
            <thead className="text-left text-muted"><tr><th className="pb-1 font-medium">Event</th><th className="pb-1 font-medium">Level</th><th className="pb-1 font-medium">Dates</th><th className="pb-1 font-medium">Distance</th><th className="pb-1 font-medium">For this window</th></tr></thead>
            <tbody>
              {data.disasters.map((d) => (
                <tr key={d.name + d.start} className="border-t border-line">
                  <td className="py-1.5 font-medium">{d.type}: {d.name}</td>
                  <td className="py-1.5"><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: GDACS[d.alert_level]?.color }} />{d.alert_level}</span></td>
                  <td className="tabular py-1.5">{d.start} → {d.end}</td>
                  <td className="tabular py-1.5">{d.distance_km ?? '—'} km</td>
                  <td className="py-1.5">{d.signal ? <Badge tone={d.signal === 'alert' ? 'danger' : 'warning'}>{d.signal}</Badge> : <span className="text-muted">no</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="mt-2 text-sm text-muted">No GDACS events for Sri Lanka in the two years up to this window.</p>}
      </CardBody>
    </Card>
  );
}

function FoodChange({ data }) {
  const f = data.food;
  const rows = f.mom_median.map((r) => ({ ...r, pct: r.value * 100 }));
  return (
    <Card>
      <CardHeader title={`Staple food prices · ${f.districts?.join(' / ') || ''} (WFP)`}
        subtitle={f.latest_month ? `Median month-on-month change across staples · latest published month ${f.latest_month} (${f.months_behind} months before the window end)` : 'No price data'} />
      <CardBody>
        <div className="h-60">
          <ResponsiveContainer>
            <LineChart data={rows} margin={{ top: 12, right: 64, bottom: 4, left: 4 }}>
              <CartesianGrid stroke={C.grid} vertical={false} />
              <XAxis dataKey="month" {...axis} minTickGap={24} />
              <YAxis unit="%" width={48} {...axis} allowDecimals={false}
                domain={[(lo) => Math.floor(Math.min(lo, -5)), (hi) => Math.ceil(Math.max(hi, data.rules.food_mom_alert * 100 + 2))]} />
              <ReferenceLine y={data.rules.food_mom_alert * 100} stroke={C.alert} strokeDasharray="4 4"
                label={{ value: `alert ${data.rules.food_mom_alert * 100}%`, position: 'right', fill: C.alert, fontSize: 12 }} />
              <ReferenceLine y={data.rules.food_mom_watch * 100} stroke={C.watch} strokeDasharray="4 4"
                label={{ value: `watch ${data.rules.food_mom_watch * 100}%`, position: 'right', fill: C.watch, fontSize: 12 }} />
              <ReferenceLine y={0} stroke="#c8d1dd" />
              <Tooltip content={({ payload, label }) => payload?.[0] ? <TooltipBox title={label} rows={[
                ['median change', `${payload[0].payload.pct.toFixed(1)}%`], ['staple items', payload[0].payload.commodities]]} /> : null} />
              <Line dataKey="pct" stroke={C.series1} strokeWidth={2} dot={{ r: 3, fill: C.series1 }} activeDot={{ r: 5 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardBody>
    </Card>
  );
}

function PriceSmallMultiples({ data }) {
  const items = data.food.commodities;
  if (!items.length) return null;
  return (
    <Card>
      <CardHeader title="Market prices by staple (LKR, median across markets)" subtitle="One panel per staple, each on its own scale" />
      <CardBody className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((c) => (
          <div key={c.commodity}>
            <p className="text-sm font-semibold text-primary">{c.commodity} <span className="font-normal text-muted">per {c.unit}</span></p>
            <div className="h-32">
              <ResponsiveContainer>
                <LineChart data={c.points} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="month" {...axis} minTickGap={40} />
                  <YAxis width={44} {...axis} domain={['auto', 'auto']} tickCount={4} allowDecimals={false} />
                  <Tooltip content={({ payload, label }) => payload?.[0] ? <TooltipBox title={label} rows={[['LKR', payload[0].value]]} /> : null} />
                  <Line dataKey="price" stroke={C.series1} strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

function Inflation({ data }) {
  return (
    <Card>
      <CardHeader title="Inflation (CCPI, year-on-year)" subtitle={`Food ≥ ${data.rules.food_inflation_watch}% → watch · ≥ ${data.rules.food_inflation_alert}% → alert · from the monthly CBSL/DCS release`} />
      <CardBody>
        <div className="h-60">
          <ResponsiveContainer>
            <LineChart data={data.ccpi} margin={{ top: 12, right: 64, bottom: 4, left: 4 }}>
              <CartesianGrid stroke={C.grid} vertical={false} />
              <XAxis dataKey="month" {...axis} minTickGap={24} />
              <YAxis unit="%" width={44} {...axis} allowDecimals={false}
                domain={[(lo) => Math.floor(Math.min(lo, 0)), (hi) => Math.ceil(Math.max(hi, data.rules.food_inflation_alert + 2))]} />
              <ReferenceLine y={data.rules.food_inflation_alert} stroke={C.alert} strokeDasharray="4 4"
                label={{ value: 'alert', position: 'right', fill: C.alert, fontSize: 12 }} />
              <ReferenceLine y={data.rules.food_inflation_watch} stroke={C.watch} strokeDasharray="4 4"
                label={{ value: 'watch', position: 'right', fill: C.watch, fontSize: 12 }} />
              <Tooltip content={({ payload, label }) => payload?.length ? <TooltipBox title={label} rows={payload.map((p) => [p.name, p.value == null ? '—' : `${p.value}%`])} /> : null} />
              <Legend iconType="plainline" wrapperStyle={{ fontSize: 13, color: C.ink }} />
              <Line name="Food" dataKey="food" stroke={C.series2} strokeWidth={2} dot={{ r: 4, fill: C.series2 }} connectNulls={false} isAnimationActive={false} />
              <Line name="Headline" dataKey="headline" stroke={C.series1} strokeWidth={2} dot={{ r: 4, fill: C.series1 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardBody>
    </Card>
  );
}

function WorldBank({ data }) {
  return (
    <Card>
      <CardHeader title="Yearly inflation, Sri Lanka (World Bank)" subtitle="Background only: too slow to raise alerts" />
      <CardBody>
        <div className="h-60">
          <ResponsiveContainer>
            <BarChart data={data.worldbank} margin={{ top: 12, right: 8, bottom: 4, left: 4 }}>
              <CartesianGrid stroke={C.grid} vertical={false} />
              <XAxis dataKey="year" {...axis} />
              <YAxis unit="%" width={44} {...axis} />
              <ReferenceLine y={0} stroke="#c8d1dd" />
              <Tooltip cursor={{ fill: '#f4f6f9' }} content={({ payload, label }) => payload?.[0] ? <TooltipBox title={label} rows={[['inflation', `${payload[0].value}%`]]} /> : null} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                {data.worldbank.map((r) => <Cell key={r.year} fill={C.series1} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardBody>
    </Card>
  );
}

export default function ExternalContext() {
  const [win, setWinState] = useState(PRESETS[1]);
  const [offline, setOfflineState] = useState(false);
  const [refresh, setRefresh] = useState(0);        // non-zero only for the fetch a "Fetch now" click asked for
  const setWin = (w) => { setRefresh(0); setWinState(w); };
  const setOffline = (v) => { setRefresh(0); setOfflineState(v); };
  const params = { start: win.start, end: win.end, offline, ...(refresh ? { refresh: true, n: refresh } : {}) };
  const { data, error, loading } = useApi('/maintenance/context/dashboard', params);
  const levelTone = { alert: 'danger', watch: 'warning', none: 'success' };

  return (
    <div className="animate-fade-in space-y-5">
      <PageHeader
        component="c3"
        title="External context monitoring"
        subtitle="Disasters, food prices and inflation for the study area, fetched from public sources. An alert tightens drift detection and is listed as a possible cause; it never triggers maintenance by itself."
      />

      <Card>
        <CardBody className="flex flex-wrap items-end gap-3">
          <div className="inline-flex flex-wrap rounded-lg border border-line bg-white p-1 text-sm">
            {PRESETS.map((p) => (
              <button key={p.id} type="button" onClick={() => setWin(p)}
                className={`rounded-md px-3 py-1.5 font-semibold transition ${win.id === p.id ? 'bg-c3 text-white' : 'text-muted hover:text-primary'}`}>
                {p.label}
              </button>
            ))}
          </div>
          <label className="text-sm text-muted">From
            <input type="date" className="ml-2 rounded-lg border border-line px-2 py-1.5 text-sm text-primary" value={win.start}
              onChange={(e) => setWin({ ...win, id: 'custom', start: e.target.value })} />
          </label>
          <label className="text-sm text-muted">to
            <input type="date" className="ml-2 rounded-lg border border-line px-2 py-1.5 text-sm text-primary" value={win.end}
              onChange={(e) => setWin({ ...win, id: 'custom', end: e.target.value })} />
          </label>
          <label className="flex items-center gap-2 text-sm text-primary">
            <input type="checkbox" className="h-4 w-4 accent-[var(--color-c3)]" checked={offline} onChange={(e) => setOffline(e.target.checked)} />
            Offline (saved real samples)
          </label>
          <Button variant="c3" className="ml-auto" onClick={() => setRefresh((n) => n + 1)} disabled={loading || offline}>
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Fetch now
          </Button>
        </CardBody>
      </Card>

      {error && <ErrorBox error={error} hint="Is the backend running? Live mode needs internet; tick Offline to use saved samples." />}
      {loading && !data && <Card><CardBody><Loading label="Fetching GDACS, WFP and World Bank data… (WFP's price file takes ~10 s)" /></CardBody></Card>}

      {data && (
        <div className={`space-y-5 ${loading ? 'opacity-60' : ''}`}>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {data.sources.map((s) => <SourceCard key={s.name} s={s} />)}
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
            <Card>
              <CardHeader title={`Context level for ${data.window.start} → ${data.window.end}`}
                icon={data.level === 'none' ? CheckCircle2 : AlertTriangle}
                action={<Badge tone={levelTone[data.level]}>{data.level === 'none' ? 'no signal' : data.level}</Badge>} />
              <CardBody className="space-y-2">
                {data.signals.length ? data.signals.map((s, i) => (
                  <p key={i} className="flex items-start gap-2 text-sm">
                    <Badge tone={s.level === 'alert' ? 'danger' : 'warning'}>{s.level}</Badge>
                    <span><span className="font-semibold text-primary">{s.source.replace('_', ' ')}:</span> {s.summary}</span>
                  </p>
                )) : <p className="text-sm text-muted">No disaster, food-price or inflation signal for this window.</p>}
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="What C3 does with it" icon={Info}
                subtitle={data.effect.active ? `Alert active: drift limits × ${data.effect.tighten_factor} for this window` : 'No alert: normal drift limits'} />
              <CardBody>
                <table className="w-full text-sm">
                  <thead className="text-left text-muted"><tr><th className="pb-1 font-medium">Drift limit</th><th className="pb-1 text-right font-medium">Normal</th><th className="pb-1 text-right font-medium">This window</th></tr></thead>
                  <tbody className="tabular">
                    {data.effect.limits.map((l) => (
                      <tr key={l.name} className="border-t border-line">
                        <td className="py-1.5">{l.name}</td>
                        <td className="py-1.5 text-right">{+l.normal.toFixed(4)}</td>
                        <td className={`py-1.5 text-right ${l.now !== l.normal ? 'font-semibold text-c3' : ''}`}>{+l.now.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 text-xs text-muted">Reliability limits and decisions are never changed by context.</p>
              </CardBody>
            </Card>
          </div>

          <DisasterTimeline data={data} />
          <div className="grid gap-5 xl:grid-cols-2">
            <FoodChange data={data} />
            <Inflation data={data} />
          </div>
          <PriceSmallMultiples data={data} />
          <div className="grid gap-5 xl:grid-cols-2">
            <WorldBank data={data} />
            <Card>
              <CardHeader title="Honest limits of these sources" />
              <CardBody className="space-y-2 text-sm text-muted">
                <p><span className="font-semibold text-primary">WFP prices</span> are published with a delay (latest month {data.food.latest_month || '—'}), so they confirm trends rather than give same-week warnings.</p>
                <p><span className="font-semibold text-primary">CCPI</span> has no public API: one line is added to <code className="text-xs">ccpi_monthly.csv</code> each month from the CBSL/DCS release.</p>
                <p><span className="font-semibold text-primary">GDACS</span> is near real-time; national events are often placed at one central point, so Orange/Red events count wherever they are.</p>
                <p><span className="font-semibold text-primary">World Bank</span> values are yearly: background only.</p>
              </CardBody>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
