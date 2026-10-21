import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight, RotateCcw } from 'lucide-react'
import { getManualC1Validation } from '../lib/api'
import { diversity, manualC1InputSchema, meals, type ManualC1Input, type ManualC1Result } from '../lib/contracts'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { ErrorState, LoadingState } from '../components/ui/states'

export const initialInput: ManualC1Input = {
  test_id: 'TEST-0014', age_months: 24, sex: 'Female',
  height_cm: 80, weight_kg: 10, birth_weight_kg: 2.8, household_size: 4,
  maternal_age_years: 28, maternal_education: 'O/L passed',
  household_income_range: 'Rs.20,000 to Rs. 50,000',
  father_occupation: 'Manual worker', mother_occupation: 'Housewife',
  exclusive_breastfeeding: 'Yes', breastfeeding_duration: 'More than 6 months',
  complementary_feeding_timing: 'After 6 months', meal_frequency: '3 meals/day',
  dietary_diversity: '2 to 5 varieties', triposha_supplementation: 'No',
  vitamin_supplementation: 'Yes',
  budget_lkr: '1500', budget_period: 'weekly',
}

const featureNames: Record<string, string> = {
  meal_frequency: 'Meal frequency', dietary_diversity: 'Dietary diversity',
}
const percent = (value: number) => `${(value * 100).toFixed(2)}%`
const points = (value: number) => `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)} pp`

export function ManualC1Validation() {
  const [input, setInput] = useState<ManualC1Input>(initialInput)
  const [validationError, setValidationError] = useState('')
  const run = useMutation({ mutationFn: getManualC1Validation })

  function setField<K extends keyof ManualC1Input>(name: K, value: ManualC1Input[K]) {
    setInput(current => ({ ...current, [name]: value }))
    run.reset()
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const checked = manualC1InputSchema.safeParse(input)
    if (!checked.success) {
      setValidationError(checked.error.issues[0]?.message || 'Review the entered values.')
      return
    }
    setValidationError('')
    run.mutate(checked.data)
  }

  return <div className="mx-auto max-w-6xl space-y-7">
    <div className="page-title"><div><span className="eyebrow">Component 2 workflow</span><h1>Counterfactual intervention analysis</h1><p>Enter an invented profile. C1 scores the baseline, C2 changes only permitted feeding fields, and C1 scores each candidate before C2 compares and ranks them.</p></div></div>
    <Card className="overflow-hidden p-0">
      <div className="bg-gradient-to-r from-[#162b46] to-[#36516b] p-6 text-white md:p-8"><span className="text-xs font-bold uppercase tracking-[.2em] text-white/75">Genuine C1 inference</span><h2 className="mt-2 text-2xl font-bold">Manual model comparison</h2><p className="mt-2 max-w-3xl text-base text-white/85">All fields below are invented demonstration inputs. Results show model behavior, not an approved feeding plan.</p></div>
      <form onSubmit={submit}>
        <div className="grid gap-5 p-6 sm:grid-cols-2 lg:grid-cols-3 md:p-8">
          <TextField label="Test case ID" value={input.test_id} onChange={value => setField('test_id', value)}/>
          <NumberField label="Historical age (months)" value={input.age_months} onChange={value => setField('age_months', value)}/>
          <SelectField label="Sex" value={input.sex} options={['Female', 'Male']} onChange={value => setField('sex', value as ManualC1Input['sex'])}/>
          <NumberField label="Historical height (cm)" value={input.height_cm} onChange={value => setField('height_cm', value)}/>
          <NumberField label="Historical weight (kg)" value={input.weight_kg} onChange={value => setField('weight_kg', value)}/>
          <NumberField label="Birth weight (kg)" value={input.birth_weight_kg} onChange={value => setField('birth_weight_kg', value)}/>
          <SelectField label="Meal frequency" value={input.meal_frequency} options={meals} onChange={value => setField('meal_frequency', value as ManualC1Input['meal_frequency'])}/>
          <SelectField label="Dietary diversity" value={input.dietary_diversity} options={diversity} onChange={value => setField('dietary_diversity', value as ManualC1Input['dietary_diversity'])}/>
          <label><span className="field-label">Food budget (LKR)</span><input className="field" aria-label="Food budget (LKR)" inputMode="decimal" value={input.budget_lkr ?? ''} onChange={event => setField('budget_lkr', event.target.value || null)}/></label>
          <SelectField label="Budget period" value={input.budget_period} options={['daily', 'weekly', 'monthly']} onChange={value => setField('budget_period', value as ManualC1Input['budget_period'])}/>
        </div>
        <details className="border-t border-[var(--line)] px-6 py-5 md:px-8"><summary className="cursor-pointer text-base font-semibold">Other C1 input fields (editable)</summary><p className="mt-2 text-sm text-[var(--muted)]">These values are prefilled with an invented example. Review them before presenting a new test case. The historical assessment and twelve-month horizon dates are fixed invented test dates: 1 June 2025 and 1 June 2026.</p>
          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <NumberField label="Household size" value={input.household_size} onChange={value => setField('household_size', value)}/>
            <NumberField label="Maternal age (years)" value={input.maternal_age_years} onChange={value => setField('maternal_age_years', value)}/>
            <SelectField label="Maternal education" value={input.maternal_education} options={['No formal education', 'Below O/ Level', 'O/L passed', 'A/ Level passes', 'Degree/ diploma']} onChange={value => setField('maternal_education', value as ManualC1Input['maternal_education'])}/>
            <SelectField label="Household income range" value={input.household_income_range} options={['Less than Rs. 20,000', 'Rs.20,000 to Rs. 50,000', 'Rs. 50,000 to Rs. 100,000', 'More than Rs. 100,000']} onChange={value => setField('household_income_range', value as ManualC1Input['household_income_range'])}/>
            <SelectField label="Father occupation" value={input.father_occupation} options={['Abroad', 'Government worker', 'Manual worker', 'No job', 'Private sector worker', 'Self-employed']} onChange={value => setField('father_occupation', value as ManualC1Input['father_occupation'])}/>
            <SelectField label="Mother occupation" value={input.mother_occupation} options={['Government worker', 'Housewife', 'Private sector worker', 'Self-employed']} onChange={value => setField('mother_occupation', value as ManualC1Input['mother_occupation'])}/>
            <SelectField label="Exclusive breastfeeding" value={input.exclusive_breastfeeding} options={['Yes', 'No']} onChange={value => setField('exclusive_breastfeeding', value as ManualC1Input['exclusive_breastfeeding'])}/>
            <SelectField label="Breastfeeding duration" value={input.breastfeeding_duration} options={['Less than 6 months', 'More than 6 months']} onChange={value => setField('breastfeeding_duration', value as ManualC1Input['breastfeeding_duration'])}/>
            <SelectField label="Complementary feeding timing" value={input.complementary_feeding_timing} options={['Before 6 months', 'After 6 months']} onChange={value => setField('complementary_feeding_timing', value as ManualC1Input['complementary_feeding_timing'])}/>
            <SelectField label="Triposha supplementation" value={input.triposha_supplementation} options={['No', 'Yes - irregular use', 'Yes - regular use']} onChange={value => setField('triposha_supplementation', value as ManualC1Input['triposha_supplementation'])}/>
            <SelectField label="Vitamin supplementation" value={input.vitamin_supplementation} options={['Yes', 'No']} onChange={value => setField('vitamin_supplementation', value as ManualC1Input['vitamin_supplementation'])}/>
          </div>
        </details>
        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-[var(--line)] px-6 py-5 md:px-8"><p className="max-w-2xl text-sm text-[var(--muted)]">The model scores the original input first. Hypothetical calls change only the two feeding categories.</p><Button type="submit" disabled={run.isPending}>Analyze with C1 and C2 <ArrowRight size={17}/></Button></div>
        {validationError && <p role="alert" className="px-6 pb-5 text-sm text-rose-600">{validationError}</p>}
      </form>
    </Card>
    {run.isPending && <LoadingState label="C1 is scoring the original input and feeding alternatives..."/>}
    {run.isError && <ErrorState title="C1 comparison unavailable" detail={run.error.message} retry={() => run.mutate(input)}/>}
    {run.data && <ManualResults result={run.data}/>}
  </div>
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label><span className="field-label">{label}</span><input className="field" aria-label={label} value={value} onChange={event => onChange(event.target.value)}/></label>
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label><span className="field-label">{label}</span><input className="field" aria-label={label} type="number" min="0" step="any" value={value} onChange={event => onChange(Number(event.target.value))}/></label>
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: readonly string[]; onChange: (value: string) => void }) {
  return <label><span className="field-label">{label}</span><select className="field" aria-label={label} value={value} onChange={event => onChange(event.target.value)}>{options.map(option => <option key={option} value={option}>{option}</option>)}</select></label>
}

function Prediction({ prediction }: { prediction: ManualC1Result['baseline'] }) {
  return <div className="space-y-3"><p className="text-lg font-bold">{prediction.predicted_malnutrition_type} · {prediction.severity}</p><p className="text-sm text-[var(--muted)]">Uncertainty: {prediction.uncertainty_flag ? 'flagged for review' : 'not flagged'}</p><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[
    ['Underweight', prediction.underweight_probability], ['Stunting', prediction.stunting_probability],
    ['Normal', prediction.acute_probabilities.Normal], ['MAM', prediction.acute_probabilities.MAM],
    ['SAM', prediction.acute_probabilities.SAM],
  ].map(([label, value]) => <div key={label} className="rounded-xl bg-[var(--field)] p-3"><span className="text-xs text-[var(--muted)]">{label}</span><strong className="mt-1 block text-base">{percent(Number(value))}</strong></div>)}</div></div>
}

function ManualResults({ result }: { result: ManualC1Result }) {
  return <section aria-label="Manual C1 results" className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><span className="eyebrow">Actual model response</span><h2 className="mt-2 text-3xl font-bold">Original input and C1 output</h2></div><span className="state-pill">{result.model_version} · {result.prediction_task.replaceAll('_', ' ')}</span></div>
    <Card className="p-5 md:p-7"><div className="mb-5 flex flex-wrap gap-3"><span className="state-pill">Genuine GA-RGCA-v3</span><span className="state-pill">Demo fallback disabled</span><span className="state-pill">Model comparison only</span></div><div className="grid gap-5 lg:grid-cols-2"><div><h3 className="text-xl font-bold">What you entered</h3><p className="mt-3 text-base">{result.submitted_input.test_id} · {result.submitted_input.age_months} months · {result.submitted_input.sex}</p><p className="mt-2 text-base">Historical height {result.submitted_input.height_cm} cm · weight {result.submitted_input.weight_kg} kg</p><p className="mt-2 text-base">Meals: {result.submitted_input.meal_frequency}</p><p className="text-base">Diversity: {result.submitted_input.dietary_diversity}</p><details className="mt-4 text-sm text-[var(--muted)]"><summary className="cursor-pointer font-semibold">All submitted context</summary><div className="mt-2 grid gap-2 sm:grid-cols-2">{Object.entries(result.submitted_input).map(([key, value]) => <p key={key}>{key.replaceAll('_', ' ')}: {String(value)}</p>)}</div></details></div><div><h3 className="text-xl font-bold">What C1 returned</h3><div className="mt-3"><Prediction prediction={result.baseline}/></div></div></div></Card>
    <div className="flex items-center gap-2"><RotateCcw size={18} aria-hidden="true"/><h3 className="text-2xl font-bold">C2 candidate search and real C1 re-scoring</h3></div>
    <section aria-label="Ranked model comparisons"><h3 className="mb-4 text-2xl font-bold">Ranked model comparisons ({result.ranked_model_comparisons.length})</h3>{result.ranked_model_comparisons.length ? <div className="space-y-4">{result.ranked_model_comparisons.map(candidate => <Card key={candidate.rank} className="border-l-4 border-l-emerald-600 p-5"><span className="eyebrow">Rank #{candidate.rank} - model rules passed</span><p className="mt-2 text-lg font-bold">{Object.entries(candidate.changes).map(([feature, change]) => `${featureNames[feature] ?? feature}: ${change.from} to ${change.to}`).join(' + ')}</p><p className="mt-2 text-base">C1 result: {candidate.prediction?.predicted_malnutrition_type} / {candidate.prediction?.severity}</p><p className="mt-2 text-sm text-[var(--muted)]">Ranking favors fewer changed feeding fields. Feasibility and research authorization remain unresolved.</p></Card>)}</div> : <Card className="p-5 text-base">No candidate passed the existing model rules for this input. Review the actual C1 outputs and rejection reasons below; no result was manufactured.</Card>}</section>
    {result.ranked_model_comparisons.length > 0 && <details className="panel p-5"><summary className="cursor-pointer text-lg font-bold">Educational food options and 7-day examples</summary><p className="mt-3 text-sm text-[var(--muted)]">These shopping examples use published Colombo reference prices. Budget fit does not establish individual suitability, local availability, or treatment affordability.</p><div className="mt-4 grid gap-4 md:grid-cols-2">{result.food_plans.map(plan => <Card key={plan.title} className="p-4"><h4 className="text-lg font-bold">#{plan.rank} {plan.title}</h4><p className="mt-2">{plan.estimated_total_lkr === null ? 'Cost unknown' : `LKR ${plan.estimated_total_lkr}`} / {plan.cost_period} - {plan.budget_fit.replaceAll('_', ' ')}</p><details className="mt-3"><summary className="cursor-pointer font-semibold">View 7-day pairing example</summary>{plan.schedule.map(day => <p key={day.day} className="mt-2 text-sm"><strong>{day.day}:</strong> {day.slots.map(slot => `${slot.label}: ${slot.foods.map(food => food.name).join(', ')}`).join('; ')}</p>)}</details></Card>)}</div></details>}
    {result.candidates.length ? <div className="grid gap-4 lg:grid-cols-2">{result.candidates.map((candidate, index) => <Card key={index} className="p-5"><div className="flex flex-wrap items-center justify-between gap-2"><strong className="text-lg">Candidate {index + 1}</strong><span className={candidate.model_policy_result === 'rejected' ? 'font-semibold text-rose-600' : 'font-semibold text-amber-700'}>{candidate.model_policy_result === 'rejected' ? 'Model rule rejected' : 'Review required'}</span></div>{Object.entries(candidate.changes).map(([feature, change]) => <p className="mt-2 text-base" key={feature}>{featureNames[feature] ?? feature}: <strong>{change.from} → {change.to}</strong></p>)}{candidate.prediction ? <div className="mt-4"><Prediction prediction={candidate.prediction}/>{candidate.probability_delta && <p className="mt-3 text-sm text-[var(--muted)]">Change from original: Underweight {points(candidate.probability_delta.underweight)} · Stunting {points(candidate.probability_delta.stunting)} · MAM {points(candidate.probability_delta.acute.MAM)} · SAM {points(candidate.probability_delta.acute.SAM)}</p>}</div> : <p className="mt-4 text-sm">C1 did not return this candidate prediction.</p>}<p className="mt-4 text-sm text-[var(--muted)]">{[...candidate.rejected_reasons, ...candidate.unresolved_reasons].join(' ')}</p></Card>)}</div> : <Card className="p-5">No adjacent upward feeding change is available from these starting categories.</Card>}
    <details className="panel p-5"><summary className="cursor-pointer font-semibold">Provenance and research limits</summary><p className="mt-3 text-sm">Input fingerprint: {result.input_fingerprint}. No inputs are saved by this workflow.</p><ul className="mt-3 list-inside list-disc space-y-1 text-sm">{result.limitations.map(limit => <li key={limit}>{limit}</li>)}</ul></details>
  </section>
}
