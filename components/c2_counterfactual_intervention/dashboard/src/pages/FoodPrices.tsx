import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ExternalLink, Search } from 'lucide-react'
import { getPriceReferences } from '../lib/api'
import { ResearchNotice } from '../components/ResearchNotice'
import { Card } from '../components/ui/card'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/states'

export function FoodPrices() {
  const query = useQuery({ queryKey: ['price-references'], queryFn: getPriceReferences, retry: false })
  const [search, setSearch] = useState('')
  const [foodId, setFoodId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const records = query.data?.records ?? []
  const filtered = useMemo(() => records.filter(row => `${row.commodity} ${row.market_coverage}`.toLowerCase().includes(search.toLowerCase())), [records, search])
  const selected = records.find(row => row.food_id === foodId) ?? records[0]
  const amount = Number(quantity)
  const baseQuantity = selected ? Number(selected.quantity) : NaN
  const estimate = selected && Number.isFinite(amount) && amount > 0 && Number.isFinite(baseQuantity) && baseQuantity > 0 ? Number(selected.amount_lkr) * amount / baseQuantity : null
  return <div className="space-y-6"><div className="page-title"><div><span className="eyebrow">DCS / published market observations</span><h1>Food Price References</h1><p>Source-checked Sri Lankan retail reference records, with their published geography and observation dates.</p></div></div><ResearchNotice kind="price"/>
    {query.isPending ? <LoadingState label="Loading published price references…"/> : query.isError ? <ErrorState title="Price references unavailable" detail={query.error.message} retry={() => void query.refetch()}/> : <>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(300px,.5fr)]"><section><div className="section-heading"><div><span className="eyebrow">Published data</span><h2>{records.length} checked records</h2></div><span className="text-xs text-[var(--muted)]">Status as of {query.data.as_of}</span></div><Card className="overflow-hidden !p-0"><div className="price-toolbar"><Search size={17}/><input aria-label="Search food prices" placeholder="Search food or market…" value={search} onChange={event => setSearch(event.target.value)}/><span>{filtered.length} shown</span></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Food commodity</th><th>Reference price</th><th>Observed</th><th>Source</th></tr></thead><tbody>{filtered.map(row => <tr key={row.food_id}><td><strong>{row.commodity}</strong><span>{row.market_coverage}</span></td><td className="whitespace-nowrap font-semibold">LKR {row.amount_lkr}<span className="block text-xs font-normal text-[var(--muted)]">per {row.quantity} {row.unit}</span></td><td className="whitespace-nowrap">{row.observation_start}<span className="block text-xs text-[var(--muted)]">to {row.observation_end}</span></td><td><a className="text-link inline-flex items-center gap-1" href={row.source_url} target="_blank" rel="noreferrer">DCS report <ExternalLink size={13}/></a><span>{row.source_locator}</span></td></tr>)}</tbody></table></div>{filtered.length === 0 && <p className="p-6 text-sm text-[var(--muted)]">No records match this search.</p>}</Card></section>
      <aside><div className="section-heading"><div><span className="eyebrow">Reference calculation</span><h2>Quantity calculator</h2></div></div><Card className="p-6"><label><span className="field-label">Commodity</span><select className="field" aria-label="Calculator commodity" value={selected?.food_id ?? ''} onChange={event => setFoodId(event.target.value)}>{records.map(row => <option key={row.food_id} value={row.food_id}>{row.commodity}</option>)}</select></label><label className="mt-5 block"><span className="field-label">Quantity {selected ? `(${selected.unit})` : ''}</span><input className="field" aria-label="Calculator quantity" type="number" min="0.001" step="any" value={quantity} onChange={event => setQuantity(event.target.value)}/></label><div className="calculator-total"><span>Indicative Colombo reference</span><strong>{estimate === null ? 'Enter a positive quantity' : `LKR ${estimate.toFixed(2)}`}</strong><small>{selected ? `${quantity || '—'} ${selected.unit} at LKR ${selected.amount_lkr} per ${selected.quantity} ${selected.unit}` : 'No record selected'}</small></div><p className="mt-4 text-xs leading-5 text-[var(--muted)]">Simple same-unit multiplication only. It does not establish a household food plan or verified local cost.</p></Card></aside></div>
      {selected && <Card className="p-5"><span className="eyebrow">Selected source detail</span><div className="mt-3 grid gap-4 text-sm md:grid-cols-3"><p><strong>Market</strong><span>{selected.market_coverage}</span></p><p><strong>Observation dates</strong><span>{selected.observation_start} to {selected.observation_end}</span></p><p><strong>Publication date</strong><span>{selected.publication_date ?? 'Not separately stated'}</span></p><p><strong>Date basis</strong><span>{selected.period_date_basis.replaceAll('_',' ')}</span></p><p><strong>Reference status</strong><span>{selected.reference_status.replaceAll('_',' ')}</span></p><p><strong>Source locator</strong><span>{selected.source_locator}</span></p></div></Card>}
      <p className="text-sm text-[var(--muted)]">{query.data.limitations} Local availability, household affordability, eligibility and medical suitability: unknown.</p>
      {records.length === 0 && <EmptyState title="No checked price records" detail="The connected backend returned no usable retail observations."/>}
    </>}
  </div>
}
