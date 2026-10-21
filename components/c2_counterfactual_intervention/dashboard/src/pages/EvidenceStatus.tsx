import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight, RefreshCw, ShieldCheck } from 'lucide-react'
import { getPriceReferences, getStatus, getValidation } from '../lib/api'
import { ResearchNotice } from '../components/ResearchNotice'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'

export function EvidenceStatus() {
  const c2 = useQuery({ queryKey: ['status'], queryFn: getStatus, retry: false })
  const c1 = useQuery({ queryKey: ['c1-validation'], queryFn: getValidation, retry: false, staleTime: 60000 })
  const prices = useQuery({ queryKey: ['price-references'], queryFn: getPriceReferences, retry: false })
  const rows = [
    ['C2 research API', c2.isPending ? 'Checking' : c2.isError ? 'Unavailable' : 'Connected', c2.isError ? c2.error.message : 'Status endpoint responded'],
    ['C2 test engine', c2.isPending ? 'Checking' : c2.data?.test_engine_ready ? 'Ready' : 'Unavailable', 'Synthetic research fixture and test predictor'],
    ['Genuine C1 inference', c1.isPending ? 'Checking' : c1.isError ? 'Unavailable' : 'Responding', c1.isError ? c1.error.message : c1.data ? `${c1.data.baseline.model_version} returned ${c1.data.variants.length} hypothetical comparisons` : 'Waiting for response'],
    ['Authorized C2 real mode', c2.isPending ? 'Checking' : c2.data?.c1_integrated && c2.data?.real_model_registered ? 'Configured' : 'Blocked', 'Requires research authorization and verified evidence; genuine C1 validation alone does not approve recommendations'],
    ['Published price references', prices.isPending ? 'Checking' : prices.isError ? 'Unavailable' : `${prices.data?.records.length ?? 0} records`, prices.isError ? prices.error.message : 'DCS published Colombo District observations, not verified Kalmunai prices'],
    ['Clinical readiness', c2.isPending ? 'Checking' : c2.data?.clinical_ready ? 'Ready' : 'Not ready', 'Professional review and validation remain required'],
  ]
  return <div className="space-y-6"><div className="page-title"><div><span className="eyebrow">Provenance / system readiness</span><h1>Evidence & System Status</h1><p>Live service checks and the evidence boundary for this research demonstration.</p></div><ShieldCheck className="title-icon" size={30}/></div><ResearchNotice kind="model"/>
    <div className="flex justify-end"><Button variant="outline" onClick={() => { void c2.refetch(); void c1.refetch(); void prices.refetch() }}><RefreshCw size={16}/>Refresh checks</Button></div>
    <Card className="overflow-hidden !p-0"><div className="table-scroll"><table className="data-table"><thead><tr><th>Check</th><th>Current state</th><th>Evidence / limitation</th></tr></thead><tbody>{rows.map(([label, state, detail]) => <tr key={label}><td className="font-semibold">{label}</td><td><span className="state-pill">{state}</span></td><td className="text-[var(--muted)]">{detail}</td></tr>)}</tbody></table></div></Card>
    <div className="grid gap-4 lg:grid-cols-2"><Card className="p-6"><span className="eyebrow">Established in this environment</span><h2 className="mt-2 text-xl font-semibold">Model and software evidence</h2><p className="mt-3 text-sm leading-6 text-[var(--muted)]">C1 validation uses actual returned GA-RGCA-v3 outputs on synthetic inputs when the service is available. C2 method demonstrations use a synthetic predictor. DCS price records retain their published Colombo scope and dates.</p><Link className="text-link mt-5 inline-flex items-center gap-1" to="/model-validation">Inspect C1 output <ArrowRight size={15}/></Link></Card><Card className="p-6"><span className="eyebrow">Unresolved for real recommendations</span><h2 className="mt-2 text-xl font-semibold">Authorization and local feasibility</h2><p className="mt-3 text-sm leading-6 text-[var(--muted)]">Research approval, clinical suitability, programme eligibility, household affordability, local availability and practical implementation must be verified independently. The dashboard does not infer these from a model response or official Colombo prices.</p><Link className="text-link mt-5 inline-flex items-center gap-1" to="/food-price-explorer">Inspect price provenance <ArrowRight size={15}/></Link></Card></div>
  </div>
}
