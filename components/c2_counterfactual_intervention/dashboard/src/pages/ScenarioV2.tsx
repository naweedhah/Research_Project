import { useEffect, useState, type FormEvent } from 'react'
import { ArrowRight } from 'lucide-react'
import { getC1BaselineV2, getDietScenariosV2, getLiveCaseLibraryV2, getLiveCaseValidationV2 } from '../lib/api'
import { manualC1InputSchema, meals, diversity, type C1BaselineV2, type DietScenariosV2, type LiveCaseV2, type LiveCaseValidationV2, type ManualC1Input } from '../lib/contracts'
import { initialInput } from './ManualC1Validation'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { ErrorState, LoadingState } from '../components/ui/states'

const groups = ['rice and cereals', 'vegetables', 'green leafy vegetables', 'pulses', 'eggs', 'fish', 'fruits']
type SearchMethod = 'bounded_search' | 'dice' | 'face_graph' | 'wachter' | 'compare_all'

export function ScenarioV2() {
  const [input, setInput] = useState<ManualC1Input>(initialInput)
  const [currentGroups, setCurrentGroups] = useState<string[]>([])
  const [method, setMethod] = useState<SearchMethod>('compare_all')
  const [baseline, setBaseline] = useState<C1BaselineV2 | null>(null)
  const [baselineKey, setBaselineKey] = useState('')
  const [result, setResult] = useState<DietScenariosV2 | null>(null)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [cases, setCases] = useState<LiveCaseV2[]>([])
  const [caseError, setCaseError] = useState('')
  const [casesLoading, setCasesLoading] = useState(true)
  const [verification, setVerification] = useState<LiveCaseValidationV2 | null>(null)
  const [verifyWorking, setVerifyWorking] = useState(false)
  const [verifyError, setVerifyError] = useState('')

  async function reloadCases() {
    setCasesLoading(true)
    setCaseError('')
    try {
      const data = await getLiveCaseLibraryV2()
      setCases(data.cases)
    } catch (cause) {
      setCaseError(cause instanceof Error ? cause.message : 'Case library unavailable')
    } finally { setCasesLoading(false) }
  }

  useEffect(() => { void reloadCases() }, [])

  async function verifyCases() {
    setVerifyWorking(true)
    setVerifyError('')
    setVerification(null)
    try { setVerification(await getLiveCaseValidationV2()) }
    catch (cause) { setVerifyError(cause instanceof Error ? cause.message : 'Live C1 verification unavailable') }
    finally { setVerifyWorking(false) }
  }

  function loadCase(caseId: string) {
    const chosen = cases.find(item => item.case_id === caseId)
    if (!chosen) return
    setInput(chosen.input)
    setCurrentGroups(chosen.food_groups)
    setBaseline(null)
    setBaselineKey('')
    setResult(null)
    setError('')
  }

  function setField<K extends keyof ManualC1Input>(key: K, value: ManualC1Input[K]) {
    setInput(old => ({ ...old, [key]: value }))
    setResult(null)
    setError('')
  }
  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const parsed = manualC1InputSchema.safeParse(input)
    if (!parsed.success) { setError(parsed.error.issues[0]?.message ?? 'Check the entered values.'); return }
    setError('')
    setWorking(true)
    try {
      // Budget, confirmation and food preferences do not change C1's original
      // model input. Reuse that result until an actual model input changes.
      const { budget_lkr: _budget, budget_period: _period, ...modelInput } = parsed.data
      const key = JSON.stringify(modelInput)
      const original = baseline && baselineKey === key ? baseline : await getC1BaselineV2(parsed.data)
      if (key !== baselineKey) { setBaseline(original); setBaselineKey(key) }
      const next = await getDietScenariosV2({ contract_version: 'c2-diet-scenarios-v2',
        age_months: parsed.data.age_months, original_c1: original.assessment,
        feeding: { meal_frequency: parsed.data.meal_frequency,
          dietary_diversity: parsed.data.dietary_diversity, food_groups: currentGroups,
          provenance: 'unverified' }, method, research_algorithm_demo: true,
        household: { budget_lkr: parsed.data.budget_lkr, budget_period: parsed.data.budget_period,
          budget_provenance: parsed.data.budget_lkr === null ? 'unknown' : 'user_reported',
          allergy_status: 'unknown',
          excluded_food_ids: [],
          preparation: 'unknown', local_availability: {} }, max_candidates: 5 })
      setResult(next)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Analysis unavailable') }
    finally { setWorking(false) }
  }

  return <div className="mx-auto max-w-6xl space-y-7">
    <div className="page-title"><div><span className="eyebrow">Component 2 · research workflow</span><h1>Counterfactual Intervention Engine</h1><p>Original C1 risk is read once. C2 compares food scenarios with the reported feeding baseline, checks available evidence, then ranks only verified feasible alternatives.</p></div></div>
    <Card className="p-6 md:p-8"><div className="flex flex-wrap items-start justify-between gap-4"><div><span className="eyebrow">Live C1 case library</span><h2 className="mt-2 text-xl font-bold">Choose an invented input profile</h2><p className="mt-2 text-sm text-[var(--muted)]">Case names describe inputs. Actual risk categories appear only after C1 responds.</p></div><Button type="button" disabled={verifyWorking || cases.length === 0} onClick={verifyCases}>{verifyWorking ? 'Checking C1 cases...' : 'Verify all cases with live C1'}</Button></div>
      {casesLoading && <p className="mt-4 text-sm">Loading case library from C2...</p>}
      {caseError && <div role="alert" className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950"><strong>Updated cases could not load.</strong><p className="mt-1 text-sm">{caseError} Restart the C2 backend on port 8000, then retry.</p><button type="button" className="mt-2 font-semibold underline" onClick={() => void reloadCases()}>Retry case library</button></div>}
      {cases.length > 0 && <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{cases.map(item => <button key={item.case_id} type="button" onClick={() => loadCase(item.case_id)} className={`rounded-xl border px-4 py-3 text-left text-sm hover:bg-[var(--field)] ${input.test_id === item.case_id ? 'border-cyan-500 bg-cyan-50 text-slate-950' : 'border-[var(--line)]'}`}><strong className="block">{item.name}</strong><span className="text-[var(--muted)]">{item.case_id}</span></button>)}</div>}
      {verifyWorking && <p className="mt-4 text-sm">Calling the genuine C1 model for each profile. This may take several seconds.</p>}
      {verifyError && <p role="alert" className="mt-4 text-sm text-rose-700">{verifyError}</p>}
      {verification && <div className="mt-6 overflow-x-auto"><h3 className="text-lg font-bold">Results from this live C1 run</h3><p className="mt-1 text-sm text-[var(--muted)]">{verification.c1_calls} genuine calls; no demo fallback. Categories absent from this run: {verification.unobserved_categories.join(', ') || 'none'}.</p><table className="mt-3 w-full min-w-[650px] text-left text-sm"><thead><tr className="border-b border-[var(--line)]"><th className="p-2">Case</th><th className="p-2">C1 result</th><th className="p-2">Severity</th><th className="p-2">Review</th><th className="p-2">C2 options</th></tr></thead><tbody>{verification.cases.map(row => <tr key={row.case_id} className="border-b border-[var(--line)]"><td className="p-2"><button type="button" className="font-semibold text-[var(--accent)] underline" onClick={() => loadCase(row.case_id)}>{row.case_id}</button></td><td className="p-2">{row.c1_predicted_category}</td><td className="p-2">{row.c1_severity}</td><td className="p-2">{row.assessment_review_needed ? 'Needed' : 'Not flagged'}</td><td className="p-2">{row.c2_candidate_count} generated</td></tr>)}</tbody></table><p className="mt-3 text-xs text-[var(--muted)]">Invented inputs; model outputs are not diagnoses. C2 options remain research tests until feasibility evidence is verified.</p></div>}
    </Card>
    <form onSubmit={analyze} className="space-y-5">
      <Card className="overflow-hidden p-0"><div className="bg-gradient-to-r from-[#162b46] to-[#36516b] p-6 text-white md:p-8"><span className="text-sm font-bold uppercase tracking-wider text-white/75">Original risk assessment</span><h2 className="mt-2 text-2xl font-bold">Enter an invented research profile</h2><p className="mt-2 text-base text-white/85">C1 is called once to establish the original baseline. Do not enter a real child record here.</p></div>
        <div className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3 md:p-8">
          <Input label="Test case ID" value={input.test_id} onChange={value => setField('test_id', value)}/>
          <NumberInput label="Age (months)" value={input.age_months} onChange={value => setField('age_months', value)}/>
          <Select label="Sex" value={input.sex} options={['Female','Male']} onChange={value => setField('sex', value as ManualC1Input['sex'])}/>
          <NumberInput label="Historical height (cm)" value={input.height_cm} onChange={value => setField('height_cm', value)}/>
          <NumberInput label="Historical weight (kg)" value={input.weight_kg} onChange={value => setField('weight_kg', value)}/>
        </div>
        <details className="border-t border-[var(--line)] px-6 py-5 md:px-8"><summary className="cursor-pointer font-semibold">Review other original C1 inputs</summary><p className="mt-2 text-sm text-[var(--muted)]">The prefilled context and historical dates are invented demonstration values. The fixed assessment and horizon dates are 1 June 2025 and 1 June 2026.</p><div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <NumberInput label="Birth weight (kg)" value={input.birth_weight_kg} onChange={value => setField('birth_weight_kg', value)}/>
          <Select label="Historical MAM flag (invented test)" value={input.historical_mam == null ? '' : input.historical_mam ? 'Yes' : 'No'} options={['', 'No', 'Yes']} onChange={value => setField('historical_mam', value === '' ? null : value === 'Yes')}/>
          <Select label="Historical SAM flag (invented test)" value={input.historical_sam == null ? '' : input.historical_sam ? 'Yes' : 'No'} options={['', 'No', 'Yes']} onChange={value => setField('historical_sam', value === '' ? null : value === 'Yes')}/>
          <Select label="Historical underweight status (invented test)" value={input.historical_underweight ?? ''} options={['', 'Normal', 'Moderate', 'Severe']} onChange={value => setField('historical_underweight', value === '' ? null : value as 'Normal' | 'Moderate' | 'Severe')}/>
          <Select label="Historical stunting status (invented test)" value={input.historical_stunting ?? ''} options={['', 'Normal', 'Moderate', 'Severe']} onChange={value => setField('historical_stunting', value === '' ? null : value as 'Normal' | 'Moderate' | 'Severe')}/>
          <NumberInput label="Household size" value={input.household_size} onChange={value => setField('household_size', value)}/>
          <NumberInput label="Maternal age" value={input.maternal_age_years} onChange={value => setField('maternal_age_years', value)}/>
          <Select label="Maternal education" value={input.maternal_education} options={['No formal education','Below O/ Level','O/L passed','A/ Level passes','Degree/ diploma']} onChange={value => setField('maternal_education', value as ManualC1Input['maternal_education'])}/>
          <Select label="Household income (context only)" value={input.household_income_range} options={['Less than Rs. 20,000','Rs.20,000 to Rs. 50,000','Rs. 50,000 to Rs. 100,000','More than Rs. 100,000']} onChange={value => setField('household_income_range', value as ManualC1Input['household_income_range'])}/>
          <Select label="Father occupation" value={input.father_occupation} options={['Abroad','Government worker','Manual worker','No job','Private sector worker','Self-employed']} onChange={value => setField('father_occupation', value as ManualC1Input['father_occupation'])}/>
          <Select label="Mother occupation" value={input.mother_occupation} options={['Government worker','Housewife','Private sector worker','Self-employed']} onChange={value => setField('mother_occupation', value as ManualC1Input['mother_occupation'])}/>
          <Select label="Exclusive breastfeeding history" value={input.exclusive_breastfeeding} options={['Yes','No']} onChange={value => setField('exclusive_breastfeeding', value as ManualC1Input['exclusive_breastfeeding'])}/>
          <Select label="Breastfeeding duration" value={input.breastfeeding_duration} options={['Less than 6 months','More than 6 months']} onChange={value => setField('breastfeeding_duration', value as ManualC1Input['breastfeeding_duration'])}/>
          <Select label="Complementary feeding timing" value={input.complementary_feeding_timing} options={['Before 6 months','After 6 months']} onChange={value => setField('complementary_feeding_timing', value as ManualC1Input['complementary_feeding_timing'])}/>
          <Select label="Triposha use history" value={input.triposha_supplementation} options={['No','Yes - irregular use','Yes - regular use']} onChange={value => setField('triposha_supplementation', value as ManualC1Input['triposha_supplementation'])}/>
          <Select label="Vitamin use history" value={input.vitamin_supplementation} options={['Yes','No']} onChange={value => setField('vitamin_supplementation', value as ManualC1Input['vitamin_supplementation'])}/>
        </div></details>
      </Card>
      <Card className="p-6 md:p-8"><span className="eyebrow">Feeding baseline · actionable features</span><h2 className="mt-2 text-2xl font-bold">What is currently reported?</h2><div className="mt-5 grid gap-4 md:grid-cols-2">
        <Select label="Current meal frequency" value={input.meal_frequency} options={meals} onChange={value => setField('meal_frequency', value as ManualC1Input['meal_frequency'])}/>
        <Select label="Current dietary diversity category" value={input.dietary_diversity} options={diversity} onChange={value => setField('dietary_diversity', value as ManualC1Input['dietary_diversity'])}/>
      </div><fieldset className="mt-5"><legend className="field-label">Reported current food groups (optional)</legend><div className="flex flex-wrap gap-2">{groups.map(group => <label key={group} className="rounded-full border border-[var(--line)] px-3 py-2 text-sm"><input type="checkbox" checked={currentGroups.includes(group)} onChange={event => { setCurrentGroups(old => event.target.checked ? [...old, group] : old.filter(item => item !== group)); setResult(null) }}/><span className="ml-2">{group}</span></label>)}</div></fieldset></Card>
      <Card className="p-6 md:p-8"><span className="eyebrow">Household context · fixed during scenario generation</span><h2 className="mt-2 text-2xl font-bold">Food budget</h2><div className="mt-5 grid gap-4 md:grid-cols-2"><Input label="Reported food budget (LKR)" value={input.budget_lkr ?? ''} onChange={value => setField('budget_lkr', value || null)}/><Select label="Budget period" value={input.budget_period} options={['daily','weekly','monthly']} onChange={value => setField('budget_period', value as ManualC1Input['budget_period'])}/></div></Card>
      <div className="flex flex-wrap items-end justify-between gap-4"><Select label="Counterfactual method" value={method} options={['compare_all','bounded_search','dice','face_graph','wachter']} onChange={value => { setMethod(value as SearchMethod); setResult(null) }}/><Button type="submit" disabled={working}>Generate dietary scenarios <ArrowRight size={17}/></Button></div>
    </form>
    {working && <LoadingState label="Reading original C1 assessment and checking C2 food scenarios..."/>}
    {error && <ErrorState title="Analysis unavailable" detail={error} retry={() => { setError(''); setResult(null) }}/ >}
    {result && <ScenarioResults result={result}/>}
  </div>
}
function Input({label,value,onChange}: {label:string;value:string;onChange:(value:string)=>void}) { return <label><span className="field-label">{label}</span><input className="field" aria-label={label} value={value} onChange={event => onChange(event.target.value)}/></label> }
function NumberInput({label,value,onChange}: {label:string;value:number;onChange:(value:number)=>void}) { return <label><span className="field-label">{label}</span><input className="field" type="number" step="any" aria-label={label} value={value} onChange={event => onChange(Number(event.target.value))}/></label> }
function Select({label,value,options,onChange}: {label:string;value:string;options:readonly string[];onChange:(value:string)=>void}) { return <label><span className="field-label">{label}</span><select className="field" aria-label={label} value={value} onChange={event => onChange(event.target.value)}>{options.map(item => <option key={item} value={item}>{item.replaceAll('_',' ')}</option>)}</select></label> }

function ScenarioResults({result}: {result:DietScenariosV2}) {
  return <section aria-label="Dietary scenario results" className="space-y-5"><Card className="p-6 md:p-8"><span className="eyebrow">Original C1 assessment · read only</span><h2 className="mt-2 text-2xl font-bold">{result.original_c1.predicted_malnutrition_type} · {result.original_c1.severity}</h2><p className="mt-2">Model: {result.original_c1.model_version} · Source: {result.original_c1.prediction_source} · Uncertainty {result.original_c1.uncertainty_flag ? 'flagged' : 'not flagged'}</p></Card>
    <div><span className="eyebrow">Food alternatives</span><h2 className="mt-2 text-3xl font-bold">Foods and meal pairing ideas</h2>{result.candidate_count === 0 && <p className="mt-2 text-base">The selected method found no compatible food option for this test input.</p>}</div>
    {result.software_test_ranked && result.software_test_ranked.length > 0 && <p className="rounded-xl border border-cyan-300 bg-cyan-50 px-5 py-3 font-semibold text-cyan-950">{result.software_test_ranked.length} research-test options ordered by the smallest compatible shopping list, then reference cost. These ranks are not predicted health improvements or verified feeding recommendations.</p>}
    <div className="grid gap-5 lg:grid-cols-2">{[...result.ranked_cards, ...result.unresolved_or_rejected].sort((a, b) => (result.software_test_ranked?.find(row => row.candidate_id === a.candidate_id)?.rank ?? 999) - (result.software_test_ranked?.find(row => row.candidate_id === b.candidate_id)?.rank ?? 999)).map((card, index) => <ScenarioCard key={card.candidate_id} card={card} position={index} testRank={result.software_test_ranked?.find(row => row.candidate_id === card.candidate_id)?.rank}/>)}</div>
  </section>
}

const cardPalettes = [
  'from-[#164a6e] via-[#246a82] to-[#31969c]',
  'from-[#5b315f] via-[#8a4881] to-[#bf7094]',
  'from-[#765120] via-[#a7772c] to-[#d9a950]',
  'from-[#254b43] via-[#347663] to-[#64a680]',
  'from-[#3f4673] via-[#6474aa] to-[#8ca5c5]',
]

function ScenarioCard({card,position,testRank}: {card:DietScenariosV2['unresolved_or_rejected'][number];position:number;testRank?:number}) {
  const isVerified = card.rank !== null
  const pairings = uniquePairings(card.schedule)
  const budgetStyle = card.reference_budget_fit === 'within_budget' ? 'border-emerald-300 bg-emerald-50 text-emerald-950' : card.reference_budget_fit === 'above_budget' ? 'border-rose-300 bg-rose-50 text-rose-950' : 'border-slate-300 bg-slate-50 text-slate-900'
  return <Card className="overflow-hidden p-0 shadow-lg">
    <div className={`bg-gradient-to-br ${cardPalettes[position % cardPalettes.length]} p-6 text-white md:p-7`}>
      <div className="flex items-start justify-between gap-4">
        <span className="rounded-full bg-white/20 px-3 py-1 text-sm font-bold">{isVerified ? `Rank ${card.rank}` : testRank ? `Research-test rank ${testRank}` : `Option ${String(position + 1).padStart(2, '0')}`}</span>
        {card.status === 'rejected' && <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-semibold">Unavailable for this profile</span>}
      </div>
      <h3 className="mt-8 text-2xl font-bold">{card.title}</h3>
      <p className="mt-2 text-white/90">{card.additional_groups.length ? `Adds ${card.additional_groups.join(', ')}` : 'Food-group change needs review'}</p>
      <p className="mt-3 text-sm font-semibold text-white/90">Generated by: {(card.generator_methods ?? []).map(methodName).join(', ') || 'C2 food-option search'}</p>
    </div>
    <div className="space-y-5 p-6">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-[var(--field)] p-4"><span className="block text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Estimated shopping cost</span><strong className="mt-1 block text-lg">{card.reference_cost_lkr ? `LKR ${card.reference_cost_lkr}` : 'Unknown'}</strong><span className="text-xs">per {card.cost_period}</span></div>
        <div className={`rounded-xl border p-4 ${budgetStyle}`}><span className="block text-xs font-semibold uppercase tracking-wide">Budget comparison</span><strong className="mt-1 block text-lg">{card.reference_budget_fit === 'within_budget' ? 'Within budget' : card.reference_budget_fit === 'above_budget' ? 'Above budget' : 'Budget unknown'}</strong><span className="text-xs">Indicative reference cost</span></div>
      </div>
      <div><h4 className="font-bold">Foods in this option</h4><div className="mt-3 grid gap-2 sm:grid-cols-2">{card.items.map(item => <div key={item.food_id} className="rounded-xl border border-[var(--line)] p-3"><strong className="block">{item.name}</strong><span className="text-sm text-[var(--muted)]">{formatQuantity(item.quantity, item.unit)} to purchase · LKR {item.indicative_cost_lkr}</span></div>)}</div></div>
      {pairings.length > 0 && <details className="border-t border-[var(--line)] pt-4"><summary className="cursor-pointer font-semibold">See food pairing ideas</summary><div className="mt-3 space-y-2">{pairings.map(pairing => <p key={pairing} className="text-sm">{pairing}</p>)}</div><p className="mt-3 text-xs text-[var(--muted)]">Illustrative combinations, not a complete seven-day meal plan or child serving guide.</p></details>}
    </div>
  </Card>
}

function methodName(name: string) { return ({ bounded_search: 'Bounded Search', dice: 'DiCE', face_graph: 'FACE Graph', wachter: 'Wachter' } as Record<string,string>)[name] ?? name.replaceAll('_', ' ') }

function formatQuantity(quantity: string, unit: string) {
  const amount = Number(quantity)
  if (!Number.isFinite(amount)) return `${quantity} ${unit}`
  if (unit === 'kg' && amount > 0 && amount < 1) return `${Number((amount * 1000).toFixed(3))} g`
  return `${amount} ${unit}`
}


function uniquePairings(schedule: DietScenariosV2['unresolved_or_rejected'][number]['schedule']) {
  return [...new Set(schedule.flatMap(day => day.slots.map(slot => `${slot.label}: ${slot.foods.map(food => food.name).join(', ')}`)))]
}
