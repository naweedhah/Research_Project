import { useState } from 'react'
import { Activity, ArrowRight, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { generate } from '../lib/api'
import { methods, scenarios, type Profile, type ResearchResult } from '../lib/contracts'
import { fixtureFor } from '../lib/fixtures'
import { recordRun } from '../lib/runHistory'
import { ResearchNotice } from '../components/ResearchNotice'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'

type Outcome = { method: string; result?: ResearchResult; elapsedMs: number; error?: string }
const names: Record<string, string> = { bounded_search: 'Bounded Search', dice: 'DiCE', face_graph: 'FACE-inspired Graph' }

export function AlgorithmComparison() {
  const [scenario, setScenario] = useState<Profile['scenario']>('favorable')
  const [running, setRunning] = useState(false)
  const [outcomes, setOutcomes] = useState<Outcome[]>([])

  async function compare() {
    setRunning(true); setOutcomes([])
    // Sequential calls avoid competing for the single local C2/C1 demo services.
    const next: Outcome[] = []
    for (const method of methods) {
      const request = fixtureFor(scenario)
      request.method = method
      const start = performance.now()
      try {
        const result = await generate(request)
        recordRun(result, scenario)
        next.push({ method, result, elapsedMs: performance.now() - start })
      } catch (error) {
        next.push({ method, elapsedMs: performance.now() - start, error: error instanceof Error ? error.message : 'Unknown API failure' })
      }
      setOutcomes([...next])
    }
    setRunning(false)
  }

  return <div className="space-y-6">
    <div className="page-title"><div><span className="eyebrow">Methods / common fixture</span><h1>Algorithm Comparison</h1><p>Run three C2 research methods against the same backend fixture. Returned outcomes are compared without effectiveness claims.</p></div><Activity className="title-icon" size={30}/></div>
    <ResearchNotice/>
    <Card className="flex flex-wrap items-end gap-4 p-5"><label className="min-w-60 flex-1"><span className="field-label">Research scenario</span><select className="field" value={scenario} disabled={running} onChange={event => { setScenario(event.target.value as Profile['scenario']); setOutcomes([]) }}>{scenarios.map(value => <option value={value} key={value}>{value.replaceAll('_', ' ')}</option>)}</select></label><Button disabled={running} onClick={() => void compare()}><RefreshCw size={16}/>{running ? 'Running methods…' : 'Run all three methods'}</Button><p className="w-full text-xs text-[var(--muted)]">Each method receives the same scenario fixture. Elapsed time is browser-to-API round trip, including transport and server work.</p></Card>
    {outcomes.length === 0 && !running && <div className="empty-compact">No comparison run yet. Choose a scenario and run the three backend methods.</div>}
    <div className="grid gap-4 xl:grid-cols-3">{methods.map((method, index) => {
      const item = outcomes.find(value => value.method === method)
      return <Card key={method} className="comparison-card p-5"><div className="flex items-center justify-between"><span className="eyebrow">Method 0{index + 1}</span><span className="status-dot"/></div><h2 className="mt-2 text-xl font-semibold">{names[method]}</h2>
        {!item && <p className="mt-5 text-sm text-[var(--muted)]">{running ? 'Waiting for backend result…' : 'Awaiting comparison'}</p>}
        {item?.error && <div role="alert" className="mt-5 rounded-xl border border-rose-400/30 p-4 text-sm"><strong>Method unavailable</strong><p className="mt-2 text-[var(--muted)]">{item.error}</p><Button variant="outline" className="mt-4" onClick={() => void compare()} disabled={running}>Retry comparison</Button></div>}
        {item?.result && <><div className="comparison-stats mt-5"><div><span>Returned cards</span><strong>{item.result.cards.length}</strong></div><div><span>Rejected / unresolved</span><strong>{item.result.rejected_or_unresolved.length}</strong></div><div><span>Round trip</span><strong>{Math.round(item.elapsedMs)} ms</strong></div></div><p className="mt-4 text-xs text-[var(--muted)]">Source: {item.result.baseline.prediction_source} · {item.result.baseline.model_version}</p><div className="mt-4 border-t border-[var(--line)] pt-4"><span className="field-label">Backend message</span><p className="mt-2 text-sm leading-6">{item.result.message}</p></div>{item.result.cards.length > 0 && <ul className="mt-4 space-y-2">{item.result.cards.slice(0, 3).map(card => <li key={card.rank} className="rounded-lg bg-[var(--field)] p-3 text-sm"><strong>Candidate {card.rank}</strong><span className="ml-2 text-[var(--muted)]">{Object.entries(card.changes).map(([key, value]) => `${key.replaceAll('_', ' ')} → ${value}`).join(' · ')}</span></li>)}</ul>}{item.result.rejected_or_unresolved.length > 0 && <details className="mt-4 text-sm"><summary className="cursor-pointer text-link">View rejected or unresolved reasons</summary><ul className="mt-2 list-inside list-disc space-y-1 text-[var(--muted)]">{item.result.rejected_or_unresolved.flatMap(value => value.reasons).slice(0, 6).map((reason, i) => <li key={i}>{reason}</li>)}</ul></details>}</>}
      </Card>
    })}</div>
    <div className="text-sm text-[var(--muted)]">Inspect one method in detail in the <Link className="text-link inline-flex items-center gap-1" to="/advanced-testing">Advanced Testing <ArrowRight size={14}/></Link>. These results use a research-test predictor; genuine C1 inference is shown separately.</div>
  </div>
}
