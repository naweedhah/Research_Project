import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowRight, CircleAlert, ShieldCheck } from 'lucide-react'
import { getValidation } from '../lib/api'
import type { ValidationResult } from '../lib/contracts'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { ErrorState, LoadingState } from '../components/ui/states'
import { ResearchNotice } from '../components/ResearchNotice'

const labels: Record<string, string> = { meal_frequency: 'Meal frequency', dietary_diversity: 'Dietary diversity' }
const percent = (value: number) => `${(value * 100).toFixed(2)}%`
const delta = (value: number) => `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)} percentage points`

export function ModelValidation() {
  const query = useQuery({ queryKey: ['c1-validation'], queryFn: getValidation, retry: false, staleTime: 60000 })
  return <div className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><span className="eyebrow">Genuine model / synthetic fixture</span><h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">C1 Model Validation</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">The fixed C2 synthetic fixture is scored automatically by the loaded GA-RGCA-v3 service. The results below come from the live C1 predictor.</p></div><Button onClick={() => void query.refetch()} disabled={query.isFetching}><Activity size={17}/> {query.isFetching ? 'Running C1 checks…' : 'Rerun genuine model check'}</Button></div>
    <ResearchNotice kind="model"/>
    {query.isFetching && <LoadingState label="Checking loaded C1 model and scoring four hypothetical inputs…"/>}
    {query.isError && <ErrorState title="Genuine model unavailable" detail={query.error.message} retry={() => void query.refetch()}/>}
    {query.data && !query.isError && <Results result={query.data}/>}
  </div>
}

function Results({ result }: { result: ValidationResult }) {
  return <div className="space-y-6">
    <Card className="p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><span className="eyebrow">Live predictor response</span><h2 className="mt-1 text-xl font-semibold">Original feeding profile</h2></div><span className="validation-source rounded-full border border-cyan-400/25 px-3 py-1 text-xs text-cyan-300">{result.baseline.model_version} | live C1 response</span></div><p className="mt-3 text-xs text-[var(--muted)]">{result.fixture_provenance}</p><div className="mt-5 grid gap-3 sm:grid-cols-2">{Object.entries(result.original_feeding).map(([key,value]) => <div key={key} className="rounded-xl border border-[var(--line)] p-3"><span className="text-xs text-[var(--muted)]">{labels[key] ?? key}</span><strong className="mt-1 block">{value}</strong></div>)}</div><Prediction prediction={result.baseline}/></Card>
    <section><div className="section-heading"><div><span className="eyebrow">Bounded hypothetical inputs</span><h2>Actual C1 comparisons</h2></div><span className="text-xs text-[var(--muted)]">{result.variants.length} variants · {result.intervention_cards.length} intervention cards</span></div><div className="grid gap-4 xl:grid-cols-3">{result.variants.map((item,index) => <Card key={index} className="p-6"><span className="eyebrow">Variant {String(index+1).padStart(2,'0')}</span><div className="mt-4 space-y-2">{Object.entries(item.changes).map(([key,change]) => <p key={key} className="text-sm"><span className="text-[var(--muted)]">{labels[key] ?? key}:</span> {change.from} <ArrowRight className="inline" size={14}/> {change.to}</p>)}</div><Prediction prediction={item.prediction}/><div className="mt-4 rounded-xl border border-[var(--line)] p-4 text-sm"><strong>Compared with original</strong><p className="mt-2 text-[var(--muted)]">Type changed: {item.comparison.type_changed ? 'yes' : 'no'} · Severity changed: {item.comparison.severity_changed ? 'yes' : 'no'}</p><p className="mt-1 text-[var(--muted)]">Underweight: {delta(item.comparison.underweight_probability_delta)} · Stunting: {delta(item.comparison.stunting_probability_delta)}</p></div><div className="mt-4 flex items-start gap-2 text-xs text-amber-300"><CircleAlert size={16} className="shrink-0"/><div><strong>Unresolved for intervention</strong><ul className="mt-1 list-inside list-disc space-y-1 text-[var(--muted)]">{item.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></div></div></Card>)}</div></section>
    <Card className="p-5"><div className="flex items-center gap-2 text-sm font-semibold"><ShieldCheck size={18} className="text-cyan-300"/> Research boundary</div><ul className="mt-3 list-inside list-disc space-y-2 text-sm text-[var(--muted)]">{result.limitations.map(item => <li key={item}>{item}</li>)}</ul></Card>
  </div>
}

function Prediction({ prediction }: { prediction: ValidationResult['baseline'] }) {
  return <div className="mt-5 border-t border-[var(--line)] pt-5"><div className="grid gap-3 sm:grid-cols-3"><Metric label="Predicted type" value={prediction.predicted_malnutrition_type}/><Metric label="Severity" value={prediction.severity}/><Metric label="Acute status" value={prediction.acute_status}/></div><div className="mt-5 space-y-3"><Probability label="Underweight model probability" value={prediction.underweight_probability}/><Probability label="Stunting model probability" value={prediction.stunting_probability}/></div><p className="mt-4 text-xs text-[var(--muted)]">Uncertainty: {prediction.uncertainty_flag ? 'Flagged for professional review' : 'Not flagged by model'} | Task: {prediction.prediction_task}</p></div>
}
function Probability({ label, value }: { label: string; value: number }) { return <div className="probability-row"><div><span>{label}</span><strong>{percent(value)}</strong></div><div className="probability-track"><span style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}/></div></div> }
function Metric({ label, value }: { label: string; value: string }) { return <div><span className="text-xs text-[var(--muted)]">{label}</span><strong className="mt-1 block text-sm">{value}</strong></div> }
