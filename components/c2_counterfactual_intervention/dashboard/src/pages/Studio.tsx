import { useState, type ReactNode } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowRight, FlaskConical, LockKeyhole, RotateCcw, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { getStatus, generate, type ApiError } from '../lib/api'
import { diversity, meals, profileSchema, scenarios, type Profile, type ResearchResult } from '../lib/contracts'
import { defaultProfile, mapRequest, profileForScenario } from '../lib/fixtures'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Select } from '../components/ui/select'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/states'
import { ResearchNotice } from '../components/ResearchNotice'
import { recordRun } from '../lib/runHistory'

const methodInfo = [
  { value: 'bounded_search', label: 'Bounded Search', description: 'Explore permitted adjacent changes.' },
  { value: 'dice', label: 'DiCE', description: 'Synthetic classifier method test.' },
  { value: 'face_graph', label: 'FACE-inspired Graph', description: 'Connected candidate exploration.' },
] as const
const scenarioLabels: Record<Profile['scenario'], string> = {
  favorable: 'Favorable fixture', unchanged: 'Unchanged prediction', worsening: 'Worsening prediction', uncertain: 'Uncertain prediction',
  no_solution: 'No solution', unknown_availability: 'Unknown availability', unaffordable: 'Unaffordable', too_young: 'Below age threshold',
}
const featureLabels: Record<string, string> = { meal_frequency: 'Meal frequency', dietary_diversity: 'Dietary diversity' }
const choices = (values: readonly string[]) => values.map(value => ({ value, label: value }))

export function Studio() {
  const status = useQuery({ queryKey: ['status'], queryFn: getStatus })
  const form = useForm<Profile>({ resolver: zodResolver(profileSchema), defaultValues: defaultProfile(), mode: 'onSubmit' })
  const [submitted, setSubmitted] = useState<Profile | null>(null)
  const [fixtureRetained, setFixtureRetained] = useState(true)
  const mutation = useMutation({ mutationFn: generate })
  const current = form.watch()

  function run(values: Profile) {
    const { request, fixtureAssertionsRetained } = mapRequest(values)
    setFixtureRetained(fixtureAssertionsRetained)
    setSubmitted(values)
    mutation.mutate(request, { onSuccess: result => recordRun(result, values.scenario) })
  }
  function selectScenario(value: string) {
    const scenario = value as Profile['scenario']
    form.reset(profileForScenario(scenario, form.getValues('method')))
    mutation.reset(); setSubmitted(null)
  }
  function reset() { form.reset(defaultProfile()); mutation.reset(); setSubmitted(null); setFixtureRetained(true) }

  return <div className="space-y-7">
    <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between"><div><span className="eyebrow">Research workflow / 02</span><h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Counterfactual Studio</h1><p className="mt-2 text-sm text-[var(--muted)]">Submit synthetic research inputs to the live Component 2 API.</p></div><span className="rounded-full border border-cyan-400/25 bg-cyan-400/8 px-3 py-2 text-xs text-cyan-300">Research test mode</span></div>
    <ResearchNotice/>
    <div className="step-rail"><span><b>01</b> Research profile</span><span><b>02</b> Method & scenario</span><span><b>03</b> Backend results</span></div>
    <div className="grid items-start gap-6 xl:grid-cols-[minmax(350px,.9fr)_minmax(0,1.1fr)]">
      <form onSubmit={form.handleSubmit(run)} noValidate className="space-y-5">
        <Card className="p-6"><div className="mb-6 flex items-start justify-between"><div><span className="eyebrow">Step 01</span><h2 className="mt-1 text-xl font-semibold">Research profile</h2></div><FlaskConical className="text-cyan-300" size={21}/></div>
          <div className="grid gap-4 sm:grid-cols-2"><Field label="Pseudonymous test identifier" error={form.formState.errors.pseudonym?.message} className="sm:col-span-2"><input {...form.register('pseudonym')} className="field" autoComplete="off" aria-label="Pseudonymous test identifier" placeholder="SYNTHETIC-CASE-001"/></Field>
            <Field label="Historical age · months" error={form.formState.errors.age?.message}><input {...form.register('age')} className="field" aria-label="Historical age in months" type="number" min="0" max="59" step="1"/></Field>
            <Field label="Historical height · cm" error={form.formState.errors.height?.message}><input {...form.register('height')} className="field" aria-label="Historical height in cm" type="number" min="0.01" step="0.01"/></Field>
            <Field label="Historical weight · kg" error={form.formState.errors.weight?.message}><input {...form.register('weight')} className="field" aria-label="Historical weight in kg" type="number" min="0.01" step="0.01"/></Field>
            <Field label="Meal frequency" error={form.formState.errors.meal?.message}><Controller control={form.control} name="meal" render={({ field }) => <Select label="Meal frequency" value={field.value} onValueChange={field.onChange} options={choices(meals)}/>} /></Field>
            <Field label="Dietary diversity" error={form.formState.errors.diversity?.message}><Controller control={form.control} name="diversity" render={({ field }) => <Select label="Dietary diversity" value={field.value} onValueChange={field.onChange} options={choices(diversity)}/>} /></Field>
          </div><p className="mt-5 flex items-start gap-2 text-xs leading-5 text-[var(--muted)]"><LockKeyhole size={14} className="mt-0.5 shrink-0"/>Historical and contextual fields stay unchanged during each hypothetical predictor comparison. Enter only invented software-test values.</p>
        </Card>
        <Card className="p-6"><span className="eyebrow">Step 02</span><h2 className="mt-1 text-xl font-semibold">Method & scenario</h2><div className="mt-4 max-w-sm"><Field label="Research-test scenario"><Controller control={form.control} name="scenario" render={({ field }) => <Select label="Research-test scenario" value={field.value} onValueChange={selectScenario} options={scenarios.map(value => ({ value, label: scenarioLabels[value] }))}/>} /></Field></div><div className="mt-5 grid gap-3 sm:grid-cols-3">{methodInfo.map(method => <label key={method.value} className={`method-choice ${current.method === method.value ? 'method-choice-active' : ''}`}><input className="sr-only" type="radio" value={method.value} {...form.register('method')} /><span className="block font-semibold">{method.label}</span><span className="mt-1 block text-xs leading-5 text-[var(--muted)]">{method.description}</span></label>)}</div>
          <p className="mt-5 text-xs leading-5 text-[var(--muted)]">Changing the supplied profile clears fixture approvals and food evidence. The backend can return unresolved candidates; this interface will not invent a feasible card.</p>
          <div className="mt-6 flex flex-wrap gap-3"><Button type="submit" disabled={mutation.isPending || status.isError || status.isPending} className="min-w-52">{mutation.isPending ? 'Evaluating…' : 'Generate Counterfactuals'} <ArrowRight size={16}/></Button><Button type="button" variant="outline" onClick={reset}><RotateCcw size={16}/>Reset fixture</Button></div>
        </Card>
      </form>
      <section aria-label="Counterfactual results" className="space-y-5 xl:sticky xl:top-24">
        <div className="flex items-center justify-between"><div><span className="eyebrow">Step 03</span><h2 className="mt-1 text-xl font-semibold">Baseline & candidates</h2></div><span className="text-xs text-[var(--muted)]">{submitted ? methodInfo.find(m => m.value === submitted.method)?.label : 'Awaiting analysis'}</span></div>
        {status.isPending ? <LoadingState label="Checking backend connection…"/> : status.isError ? <ErrorState title="Backend unavailable" detail={status.error.message} retry={() => void status.refetch()}/> : null}
        {!status.isError && !status.isPending && !submitted && <Card className="flex min-h-78 flex-col items-center justify-center p-8 text-center"><div className="mb-4 flex size-15 items-center justify-center rounded-2xl bg-cyan-400/10 text-cyan-300"><Sparkles size={26}/></div><h3 className="text-xl font-semibold">Ready for a research run</h3><p className="mt-2 max-w-sm text-sm leading-6 text-[var(--muted)]">Select a method and generate results. Baseline, candidates and rejection reasons will come from the backend.</p></Card>}
        {mutation.isPending && <LoadingState label="Waiting for the C2 research API…"/>}
        {mutation.isError && <ErrorState title={errorTitle(mutation.error as ApiError)} detail={mutation.error.message} retry={() => submitted && run(submitted)}/>}
        {mutation.isSuccess && submitted && <Results result={mutation.data} profile={submitted} fixtureRetained={fixtureRetained}/>}
        <Link className="text-link inline-flex items-center gap-2 text-sm" to="/model-validation">Inspect genuine C1 inference separately <ArrowRight size={15}/></Link>
      </section>
    </div>
  </div>
}

function Field({ label, error, children, className = '' }: { label: string; error?: string; children: ReactNode; className?: string }) {
  return <label className={`block ${className}`}><span className="mb-2 block text-xs font-semibold uppercase tracking-[.1em] text-[var(--muted)]">{label}</span>{children}{error && <span className="mt-1 block text-xs text-rose-300">{error}</span>}</label>
}
function errorTitle(error: ApiError) {
  return ({ validation: 'Request rejected (HTTP 422)', unavailable: 'Dependency unavailable (HTTP 503)', timeout: 'Network timeout', invalid: 'Invalid backend response', offline: 'Backend unavailable', http: 'Backend request failed' } as const)[error.kind] ?? 'Request failed'
}
function Changes({ changes, profile }: { changes: Record<string, string>; profile: Profile }) {
  return <div className="space-y-2">{Object.entries(changes).map(([feature, target]) => <div key={feature} className="rounded-lg bg-cyan-400/6 px-3 py-2 text-sm"><span className="block text-xs text-[var(--muted)]">{featureLabels[feature] ?? feature}</span><span className="font-medium">{feature === 'meal_frequency' ? profile.meal : feature === 'dietary_diversity' ? profile.diversity : 'Unknown'} <span className="text-cyan-300">→</span> {target}</span></div>)}</div>
}
function Results({ result, profile, fixtureRetained }: { result: ResearchResult; profile: Profile; fixtureRetained: boolean }) {
  return <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-5" aria-live="polite">
    {!fixtureRetained && <Card className="border-amber-400/30"><p className="text-sm text-amber-200">Profile differs from the reviewed synthetic fixture. Its approval, budget and food-evidence assertions were cleared. Any candidate must remain unresolved until separately reviewed.</p></Card>}
    <Card className="border-cyan-400/25 p-6"><div className="flex flex-wrap items-center justify-between gap-2"><span className="eyebrow">Baseline model output</span><span className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs text-cyan-300">{result.baseline.prediction_source}</span></div><div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3"><Metric label="Type" value={result.baseline.predicted_malnutrition_type}/><Metric label="Acute status" value={result.baseline.acute_status}/><Metric label="Severity" value={result.baseline.severity}/></div><p className="mt-5 text-xs text-[var(--muted)]">Uncertainty: {result.baseline.uncertainty_flag ? 'Flagged for review' : 'Not flagged by test output'} · Model: {result.baseline.model_version}</p></Card>
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-semibold">Intervention cards <span className="ml-1 text-cyan-300">{result.cards.length}</span></h3><span className="text-xs text-[var(--muted)]">C1: {result.c1_integrated ? 'connected' : 'not connected'} · Clinical: {result.clinical_use ? 'ready' : 'not ready'}</span></div>
    {result.cards.length ? result.cards.map((card, index) => <Card key={`${card.rank}-${index}`} className="border-cyan-400/20 p-6"><div className="flex items-center justify-between"><span className="eyebrow">Candidate {String(card.rank).padStart(2,'0')}</span><span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs text-emerald-300">{card.feasibility_status}</span></div><div className="mt-4"><Changes changes={card.changes} profile={profile}/></div><p className="mt-4 text-sm leading-6 text-[var(--muted)]">{card.explanation}</p><div className="mt-4 border-t border-[var(--line)] pt-3 text-xs text-amber-200">{card.professional_review_required ? 'Professional review required' : 'Review status not supplied'}</div></Card>) : <EmptyState title="No eligible counterfactual returned" detail={result.message || 'The backend returned no cards under this policy and evidence.'}/>}
    {result.rejected_or_unresolved.length > 0 && <section><h3 className="mb-3 text-lg font-semibold">Rejected or unresolved <span className="text-amber-300">{result.rejected_or_unresolved.length}</span></h3><div className="space-y-3">{result.rejected_or_unresolved.map((item, index) => <Card key={index} className="p-5"><div className="mb-3 flex items-center justify-between"><span className="text-sm font-semibold">Attempt {index+1}</span><span className="text-xs uppercase tracking-wide text-amber-300">{item.status}</span></div><Changes changes={item.changes} profile={profile}/><ul className="mt-3 list-inside list-disc text-sm leading-6 text-[var(--muted)]">{item.reasons.map((reason,i) => <li key={i}>{reason}</li>)}</ul></Card>)}</div></section>}
    <p className="text-xs leading-5 text-[var(--muted)]">{result.banner}. Results are model comparisons for research testing, not predicted risk reduction or clinical advice.</p>
  </motion.div>
}
function Metric({ label, value }: { label: string; value: string }) { return <div><span className="text-xs text-[var(--muted)]">{label}</span><strong className="mt-1 block text-base md:text-lg">{value}</strong></div> }
