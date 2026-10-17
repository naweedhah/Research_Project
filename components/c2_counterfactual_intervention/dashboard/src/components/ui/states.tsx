import { AlertTriangle, CircleHelp, RefreshCw } from 'lucide-react'
import { Button } from './button'
import { Card } from './card'

export function LoadingState({ label = 'Running bounded research evaluation…' }: { label?: string }) {
  return <Card role="status" className="space-y-5 animate-pulse"><div className="h-4 w-40 rounded bg-cyan-400/20"/><div className="h-8 w-3/4 rounded bg-cyan-400/15"/><div className="h-24 rounded bg-cyan-400/10"/><p className="text-sm text-[var(--muted)]">{label}</p></Card>
}
export function ErrorState({ title, detail, retry }: { title: string; detail: string; retry?: () => void }) {
  return <Card role="alert" className="border-rose-400/35"><AlertTriangle className="mb-3 text-rose-300"/><h3 className="text-lg font-semibold">{title}</h3><p className="mt-2 text-sm text-[var(--muted)]">{detail}</p>{retry && <Button className="mt-5" variant="outline" onClick={retry}><RefreshCw size={16}/>Retry</Button>}</Card>
}
export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <Card className="border-dashed text-center"><CircleHelp className="mx-auto mb-3 text-cyan-400"/><h3 className="font-semibold">{title}</h3><p className="mt-2 text-sm text-[var(--muted)]">{detail}</p></Card>
}
