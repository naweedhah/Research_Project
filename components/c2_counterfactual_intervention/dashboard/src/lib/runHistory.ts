import type { ResearchResult } from './contracts'

export type RunSummary = { method: string; scenario: string; cards: number; rejected: number; source: string; at: string }
const key = 'c2-research-runs-v1'

export function recentRuns(): RunSummary[] {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) ?? '[]')
    return Array.isArray(value) ? value.filter(item => typeof item.method === 'string' && typeof item.source === 'string').slice(0, 5) : []
  } catch { return [] }
}

export function recordRun(result: ResearchResult, scenario: string): void {
  const item: RunSummary = { method: result.method, scenario, cards: result.cards.length,
    rejected: result.rejected_or_unresolved.length, source: result.baseline.prediction_source, at: new Date().toISOString() }
  try { sessionStorage.setItem(key, JSON.stringify([item, ...recentRuns()].slice(0, 5))) } catch { /* Storage is optional. */ }
  window.dispatchEvent(new Event('c2-run-complete'))
}
